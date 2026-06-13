"""Comms network mechanics (doc 16 §3, via
design/extracts/16-comms-buildspec.md): the comms graph consumed from
13 §3.11's contract (≤300 nodes, injected LOS — 13 owns occlusion and
the vectorized rebuild — Dijkstra to the `core:dsn` root on a
light-time metric with deterministic tie-breaks), bandwidth as a
resource (the L-6 buffer ledger laws, L-14 priority classes, L-10
canonical data volumes), the §3.3 blackout catalog as data rows with
trigger predicates (L-7 conjunction, L-8 SPE, L-9 EDL plasma, 13-canon
occlusion, L-15 optical weather) plus the derived conjunction-season
geometry, the §3.4 light-lag doctrine (L-13 teleop floor, L-11
node-ops, D-2 semantics), the §3.5 constellation coverage math whose
worked examples are BINDING, §3.6 store-and-forward (L-5 bulk + the
F-10 deadline projection at queue time), and the §3.8 anti-softlock
invariants F-3/F-7 as checkable functions (BINDING).

Rates come from linkbudget (L-2/L-3/L-4) — never re-derived here.
Determinism: nothing polls or rolls; weather outages consume
pre-rolled uniforms from the rng("comms") substream (no rerolls on
reload); scheduler order is (class, queue timestamp, uid).

All SI: distance m, rate bit/s, volume bit, time s (days only where
the spec prints days)."""

from __future__ import annotations

import heapq
import math
from dataclasses import dataclass, field

from aphelion.core.units import C_LIGHT
from aphelion.sim.network.linkbudget import (
    BANDS, CONJ_DEGRADED_DEG, CONJ_DEGRADED_MULT, CONJ_DOWN_DEG, PARTS,
    POINTING_RULES, R_FLOOR_RF, RECORDERS, link_exists, rate_bps)

# ---- §3.1 graph contract (13 §3.11, consumed verbatim — do not redefine) -------------
NODE_CAP = 300                      # scale cap is design LAW (13 §4)
ROOT_UID = "core:dsn"               # 13's always-on root node
REBUILD_CADENCE_S = 60.0            # event-driven rebuild + 60 s cadence
FRAME_BUDGET_MS = (0.2, 0.3)        # comms line, confirmed at Phase 4 gate (C22)

# new event types in 13's queue (OCCLUSION_IN/OUT already exists there)
COMMS_EVENTS = ("CONJ_IN", "CONJ_OUT", "LINK_DEGRADED_IN",
                "LINK_DEGRADED_OUT", "PASS_START", "PASS_END",
                "BUFFER_FULL", "BUFFER_EMPTY", "NODE_OPS_HOLD")
SCHEDULER_ORDER = ("class", "queue_timestamp", "uid")   # determinism contract
RNG_SUBSTREAM = "comms"             # weather pre-rolls; no rerolls on reload
COMMS_MAX_ALERT_CLASS = 2           # §3.7: no comms event is Class 1
BUFFER_ALERT_FRAC = 0.80            # Class-3 alert at BUFFER ≥ 80%

# ---- L-14 priority classes (drain strictly by class, FIFO within) --------------------
PRIORITY_CLASSES: dict[str, dict] = {
    "P0": {"order": 0, "traffic": "command / safe-mode / go-no-go",
           "buffered": False, "scheduled": False, "fits_floor_bps": 8.0},
    "P1": {"order": 1, "traffic": "housekeeping telemetry, failure bursts",
           "buffered": True, "scheduled": True, "feeds": "11 ED rules"},
    "P2": {"order": 2, "traffic": "teleop / live-ops reservation",
           "buffered": False, "scheduled": True, "reservation": True},
    "P3": {"order": 3, "traffic": "science data, survey products",
           "buffered": True, "scheduled": True,
           "feeds": "11 transmit-path awards"},
    "P4": {"order": 4, "traffic": "Chronicle media, low-value bulk",
           "buffered": True, "scheduled": True, "first_to_starve": True},
}
BULK_CLASSES = tuple(POINTING_RULES["bulk_classes"])    # ("P1","P3","P4")
LIVE_CLASSES = tuple(POINTING_RULES["live_path_classes"])   # ("P0","P2")

# ---- L-10 canonical data volumes (doc 16 owns these numbers) -------------------------
HOUSEKEEPING_BPS_PER_NODE = 200.0   # per powered comms node, continuous, P1
FAILURE_BURST_BITS = 2e9            # queued at failure, P1
FAILURE_BURST_DEADLINE_DAYS = 30.0  # delivered ≤ 30 d for the ED bonus
SCI_TRANSMIT_BITS_PER_POINT = 10e9  # 10 Gbit per SCI point, P3
A2_BATCH_UP_BITS = 20e6             # per sol cycle, P2
A2_BATCH_DOWN_BITS = 800e6          # per sol cycle, P2
CHRONICLE_SHOT_BITS = 50e6          # P4

DATA_VOLUMES: dict[str, dict] = {
    "housekeeping": {"pclass": "P1", "rate_bps": HOUSEKEEPING_BPS_PER_NODE,
                     "per": "powered comms node", "continuous": True},
    "failure_burst": {"pclass": "P1", "bits": FAILURE_BURST_BITS,
                      "deadline_days": FAILURE_BURST_DEADLINE_DAYS,
                      "counts_on": "landing",   # not queueing
                      "edl_bent_pipe_tones_count": True},
    "science": {"pclass": "P3", "bits_per_sci": SCI_TRANSMIT_BITS_PER_POINT},
    "survey": {"pclass": "P3", "bits_per_sci": SCI_TRANSMIT_BITS_PER_POINT,
               # 50-SCI Mars survey = 500 Gbit ≈ 17 d at 8 h/day leased
               # 34 m at 1.7 AU (pinned in tests)
               "example": {"sci": 50, "bits": 500e9, "days": 17,
                           "leased_h_per_day": 8.0,
                           "antenna": "core:dsn-34", "distance_au": 1.7}},
    "a2_batch": {"pclass": "P2", "up_bits": A2_BATCH_UP_BITS,
                 "down_bits": A2_BATCH_DOWN_BITS, "per": "cycle"},
    "teleop_session": {"pclass": "P2", "bits": 0.0,
                       "reservation_only": True},
    "chronicle_shot": {"pclass": "P4", "bits": CHRONICLE_SHOT_BITS},
}

# §3.2 science crediting (conforming edit to 11 §9): transmit-path
# awards credit ONLY when the volume lands at Earth or any crewed Lab
# module; pool depletion stays assigned at acquisition.
SCI_CREDIT = {"credit_at": ("earth", "crewed_lab"),
              "pool_depletion": "at_acquisition",
              "sample_return": "mass_carrier_no_downlink",
              "m_analysis_in_situ": 0.40}


def housekeeping_bps(n_powered_nodes: int) -> float:
    """L-10: 200 bit/s of continuous P1 per powered comms node."""
    return HOUSEKEEPING_BPS_PER_NODE * n_powered_nodes


# ---- L-6 buffer ledger (analytic — 13 §3.9 contract, nothing polls) ------------------
def buffer_net_bps(gen_bps: float, drain_bps: float) -> float:
    """L-6: dB/dt = Σ generation − Σ scheduled drain, piecewise-constant
    between events."""
    return gen_bps - drain_bps


def time_to_level(level_bits: float, target_bits: float,
                  net_bps: float) -> float:
    """L-6: analytic time for the buffer ledger to cross a target level
    (BUFFER_FULL when target = cap, BUFFER_EMPTY when target = 0).
    Returns math.inf if the ledger never gets there at this net rate."""
    delta = target_bits - level_bits
    if delta == 0.0:
        return 0.0
    if net_bps == 0.0 or (delta > 0.0) != (net_bps > 0.0):
        return math.inf
    return delta / net_bps


# ---- §3.3 blackout machinery ----------------------------------------------------------
EDL_QDOT_KW_M2 = 50.0       # L-9: blackout while stagnation q̇ > 50 kW/m²
EDL_TONES_BPS = R_FLOOR_RF  # overhead relay receives P0 tones only (8 bit/s)


@dataclass(frozen=True)
class LinkEnv:
    """Environment of one DIRECTED link tx→rx. L-7 is tested per
    endpoint per direction: sep_sun_rx_deg is the angular separation
    (peer vs Sun) seen from the RECEIVING endpoint — uplink can be
    blinded while downlink is clear."""
    los: bool = True                        # 13 occlusion (Brent windows)
    sep_sun_rx_deg: float | None = None     # None = wide open (L-7)
    spe_active: bool = False                # 03 S-8 in progress (L-8)
    outside_magnetosphere: bool = False     # any segment outside (L-8)
    edl_qdot_kw_m2: float = 0.0             # entering endpoint's q̇ (L-9)
    rx_overhead_relay: bool = False         # relay parked over the EDL wake
    weather_out: bool = False               # L-15 pre-rolled ground outage /
                                            # Mars dust storm


CLEAR_ENV = LinkEnv()


def conjunction_mult(sep_deg: float | None) -> float:
    """L-7: angular separation (peer vs Sun) < 2° → link down (0.0);
    < 5° → rate ×0.1; else clear. RF AND optical — optical does NOT
    bypass conjunction, only relay geometry does."""
    if sep_deg is None:
        return 1.0
    if sep_deg < CONJ_DOWN_DEG:
        return 0.0
    if sep_deg < CONJ_DEGRADED_DEG:
        return CONJ_DEGRADED_MULT
    return 1.0


def spe_mult(band: str, spe_active: bool,
             outside_magnetosphere: bool) -> float:
    """L-8 [GAME MODEL]: during an SPE every RF link with a segment
    outside a planetary magnetosphere runs ×0.5; optical unaffected
    (the deliberate tuning lever selling GN-06)."""
    if spe_active and outside_magnetosphere:
        return BANDS[band]["spe_rate_mult"]
    return 1.0


def edl_blackout(qdot_kw_m2: float) -> bool:
    """L-9: blackout while 01 §3.11 stagnation heat flux q̇ > 50 kW/m²."""
    return qdot_kw_m2 > EDL_QDOT_KW_M2


def effective_rate(base_bps: float, band: str,
                   env: LinkEnv = CLEAR_ENV) -> tuple[float, bool]:
    """§3.3 stack over the L-3 base rate of one directed link →
    (scheduled bulk rate bit/s, floor_available). Down states kill the
    floor too, EXCEPT the L-9 overhead relay which keeps P0 tones
    through the plasma wake (park-a-relay-before-you-land doctrine)."""
    if not env.los:
        return 0.0, False                   # 13 body occlusion
    mult = conjunction_mult(env.sep_sun_rx_deg)     # L-7
    if mult == 0.0:
        return 0.0, False                   # solar-blinded: link down
    if band == "optical" and env.weather_out:
        return 0.0, False                   # L-15 (RF is weather-immune)
    if edl_blackout(env.edl_qdot_kw_m2):    # L-9
        return (0.0, True) if env.rx_overhead_relay else (0.0, False)
    mult *= spe_mult(band, env.spe_active, env.outside_magnetosphere)  # L-8
    return base_bps * mult, True


# blackout catalog rows as data + trigger predicates (all via 13's queue)
BLACKOUTS: dict[str, dict] = {
    "L-7": {"name": "conjunction", "bands": ("rf", "optical"),
            "events": ("CONJ_IN", "CONJ_OUT"),
            "down_deg": CONJ_DOWN_DEG, "degraded_deg": CONJ_DEGRADED_DEG,
            "degraded_mult": CONJ_DEGRADED_MULT,
            "per_endpoint_per_direction": True,
            "window_solver": "brent_on_separation_minus_threshold",
            "alert_lead_days": 30.0, "alert_class": 3,
            "trigger": lambda env: (env.sep_sun_rx_deg is not None and
                                    env.sep_sun_rx_deg < CONJ_DEGRADED_DEG)},
    "L-8": {"name": "spe", "bands": ("rf",), "rate_mult": 0.5,
            "events": ("LINK_DEGRADED_IN", "LINK_DEGRADED_OUT"),
            "game_model": True,         # honesty-tagged tuning lever
            "trigger": lambda env: (env.spe_active and
                                    env.outside_magnetosphere)},
    "L-9": {"name": "edl_plasma", "bands": ("rf", "optical"),
            "qdot_kw_m2": EDL_QDOT_KW_M2,
            "overhead_relay_floor_bps": EDL_TONES_BPS,
            "doctrine": "park_a_relay_before_you_land",
            "trigger": lambda env: edl_blackout(env.edl_qdot_kw_m2)},
    "occlusion": {"name": "body occlusion", "owner": "13 canon",
                  "events": ("OCCLUSION_IN", "OCCLUSION_OUT"),
                  "trigger": lambda env: not env.los},
    "L-15": {"name": "optical weather", "bands": ("optical",),
             "earth_ground_availability": 0.5,
             "rng_substream": RNG_SUBSTREAM,    # pre-rolled, no rerolls
             "mars_dust_suspends": True, "airless_full_availability": True,
             "events": ("LINK_DEGRADED_IN", "LINK_DEGRADED_OUT"),
             "trigger": lambda env: env.weather_out},
}


def preroll_outage_days(u01s, availability: float = 0.5) -> tuple[bool, ...]:
    """L-15: scheduled pre-rolled outages from the rng("comms")
    substream — outage on day i iff u[i] ≥ availability. Pure in its
    inputs: reload replays the same uniforms, never rerolls."""
    return tuple(u >= availability for u in u01s)


# ---- §3.3 conjunction season geometry (2D, derived not tuned) -------------------------
CONJ_HARD_WINDOW_DEG = 4.0          # hard window = 4° / sweep rate
CONJ_DEGRADED_WINDOW_DEG = 10.0     # degraded total = 10° / sweep rate
CONJ_ALERT_LEAD_DAYS = 30.0         # Class-3 checklist at T−30 d


def elongation_sweep_deg_day(synodic_days: float, r_au: float,
                             superior: bool = True) -> float:
    """Elongation sweep rate near conjunction: ω_syn·r/(r+1) (superior)
    or ω_syn·r/(1−r) (inferior), ω_syn = 360°/synodic period."""
    omega_syn = 360.0 / synodic_days
    if superior:
        return omega_syn * r_au / (r_au + 1.0)
    return omega_syn * r_au / (1.0 - r_au)


def conjunction_window_days(synodic_days: float, r_au: float,
                            superior: bool = True) -> tuple[float, float]:
    """(hard blackout days, degraded total days) = 4°/rate, 10°/rate."""
    sweep = elongation_sweep_deg_day(synodic_days, r_au, superior)
    return (CONJ_HARD_WINDOW_DEG / sweep, CONJ_DEGRADED_WINDOW_DEG / sweep)


# printed table (vs Earth); tests re-derive every row from the inputs.
# 2D coplanarity makes inferior conjunctions always hit 0° elongation —
# accepted artifact (01 limitations table).
CONJUNCTION_SEASONS: dict[tuple[str, str], dict] = {
    ("mars", "superior"): {"synodic_d": 780.0, "r_au": 1.524,
                           "sweep_deg_day": 0.28, "hard_d": 14.0,
                           "degraded_d": 36.0, "note": "~14 d / 26 mo"},
    ("venus", "superior"): {"synodic_d": 584.0, "r_au": 0.723,
                            "sweep_deg_day": 0.26, "hard_d": 15.5,
                            "degraded_d": 39.0},
    ("venus", "inferior"): {"synodic_d": 584.0, "r_au": 0.723,
                            "sweep_deg_day": 1.61, "hard_d": 2.5,
                            "degraded_d": 6.0},
    ("mercury", "superior"): {"synodic_d": 116.0, "r_au": 0.387,
                              "sweep_deg_day": 0.87, "hard_d": 4.6,
                              "degraded_d": 11.5},
    ("mercury", "inferior"): {"synodic_d": 116.0, "r_au": 0.387,
                              "sweep_deg_day": 1.96, "hard_d": 2.0,
                              "degraded_d": 5.0},
    ("jupiter", "superior"): {"synodic_d": 399.0, "r_au": 5.203,
                              "sweep_deg_day": 0.76, "hard_d": 5.3,
                              "degraded_d": 13.0},
    ("saturn", "superior"): {"synodic_d": 378.0, "r_au": 9.54,
                             "sweep_deg_day": 0.86, "hard_d": 4.6,
                             "degraded_d": 11.5},
}

# ---- §3.4 light-lag doctrine -----------------------------------------------------------
TELEOP_MIN_RATE_BPS = 0.5e6     # L-13 live path floor (METERON anchor), P2
TELEOP_MIN_ETA = 0.2            # 05 F-2 refusal threshold
TELEOP_MIN_LEG_GAIN = 100.0     # CM-PROX class or better; omni legs P0-only
TELEOP_LOSS = {"alert_class": 2, "action": "safe_halt per 10 §3.8",
               "labor": "remaining operator-hours forfeit (F-1)"}


def teleop_ok(path_rate_bps: float, eta: float,
              min_leg_gain: float) -> bool:
    """L-13: live path ≥ 0.5 Mbit/s AND η ≥ 0.2 AND every relay leg
    CM-PROX-class or better (min linear gain over the legs)."""
    return (path_rate_bps >= TELEOP_MIN_RATE_BPS and
            eta >= TELEOP_MIN_ETA and
            min_leg_gain >= TELEOP_MIN_LEG_GAIN)


OPS_DOCTRINE: dict[str, dict] = {       # L-11
    "uncrewed_t0_t1": {"needs": "floor_path_at_event_time",
                       "on_fail": "NODE_OPS_HOLD", "alert_class": 3,
                       "escalates_class": 2,
                       "escalates_when": "burn_window_expires",
                       "retry": "next_window",
                       "light_lag_irrelevant": True},
    "t2_plus_avionics": {"needs": None},
    "a2_batch": {"up_bits": A2_BATCH_UP_BITS,
                 "down_bits": A2_BATCH_DOWN_BITS, "per": "cycle",
                 "missed_cycle": "robot_idles_that_sol"},
    "autonav_a3": {"needs": "floor_at_dispatch_and_arrival",
                   "exceptions": "page_only_when_path_exists_else_queue",
                   "uncleared_exceptions": "robot_idles"},
    "a4_or_crewed": {"needs": None},
    "edl": {"autonomy_mandatory": True},    # during L-9
}


def node_ops_check(avionics_tier: int, crewed: bool,
                   has_floor_path: bool) -> tuple[bool, str | None]:
    """L-11: uncrewed T0–T1 node ops (dock/undock/burn/cargo-start) need
    a floor path AT EVENT TIME (go/no-go, light-lag irrelevant) — else
    auto-hold and NODE_OPS_HOLD (Class-3, escalating). T2+ avionics and
    crewed nodes need no link."""
    if crewed or avionics_tier >= 2 or has_floor_path:
        return True, None
    return False, "NODE_OPS_HOLD"


# D-2 difficulty toggle bypasses RTT penalties ONLY
D2_RTT_BYPASS = {
    "eta": 1.0, "input_delay_ghost": False, "refusal": False,
    "keeps_on": ("link_existence", "rates", "buffers", "blackouts",
                 "node_ops", "dsn_fees", "a2_speed_cap"),
    "rtt_display": "truthful",
}

# ---- §3.1 nodes / links / graph ---------------------------------------------------------


def _zero_queue() -> dict[str, float]:
    return {c: 0.0 for c in PRIORITY_CLASSES}


@dataclass
class CommsNode:
    """13's CommsNode component with doc 16's fields (save-schema
    versioned): parts (comm part uids), buffer_bits, buffer_cap_bits
    (derived from mounted recorders), queue (per-class volumes).
    Buffers serialize as plain ledger floats."""
    uid: str
    pos_m: tuple[float, float]          # 2D system frame, m
    parts: tuple[str, ...]              # linkbudget.PARTS ids (slots may repeat)
    recorders: tuple[str, ...] = ()     # linkbudget.RECORDERS ids
    kind: str = "vessel"                # vessel | base | relay | ground | root
    powered: bool = True
    buffer_bits: float = 0.0
    queue: dict[str, float] = field(default_factory=_zero_queue)

    @property
    def buffer_cap_bits(self) -> float:
        return sum(RECORDERS[r]["capacity_bits"] for r in self.recorders)


def dsn_root(pos_m: tuple[float, float] = (0.0, 0.0)) -> CommsNode:
    """The `core:dsn` root: three complexes 120° apart abstracted —
    never Earth-rotation occluded, always on."""
    return CommsNode(ROOT_UID, pos_m, ("core:dsn-34", "core:dsn-70"),
                     kind="root")


def transport_mode(node: CommsNode) -> str:
    """L-5/§3.6: a relay with recorder capacity ingests bulk hop-by-hop
    (store-and-forward); no recorder = bent-pipe only (live rules)."""
    return "store_and_forward" if node.buffer_cap_bits > 0.0 else "bent_pipe"


@dataclass(frozen=True)
class DirectedLink:
    """One directed edge tx→rx: best part pair at this distance under
    this environment. rate_bps is the schedulable bulk rate (L-3 base ×
    §3.3 multipliers); the P0 floor is preemptive, never scheduled."""
    tx_uid: str
    rx_uid: str
    tx_part: str
    rx_part: str
    band: str
    d_m: float
    rate_bps: float
    floor_available: bool

    @property
    def light_s(self) -> float:
        return self.d_m / C_LIGHT

    @property
    def floor_bps(self) -> float:
        return BANDS[self.band]["floor_bps"] if self.floor_available else 0.0


@dataclass(frozen=True)
class Route:
    """L-5 multi-hop: path rate = min over hops of the directed hop
    rate; RTT = 2 × the summed hop light times (rate and latency are
    independent, L-1)."""
    path: tuple[str, ...]
    hops: tuple[DirectedLink, ...]
    rate_bps: float
    rtt_s: float


class CommsGraph:
    """Doc 16 §3.1 over 13 §3.11's contract. LOS and per-direction
    environments are injected (13 owns occlusion/Brent; 03 owns the
    geometry feeding LinkEnv); this class is the pure mechanics the
    vectorized rebuild calls. ≤ 300 nodes (LAW)."""

    def __init__(self, los=None, env=None, root_uid: str = ROOT_UID):
        self._nodes: dict[str, CommsNode] = {}
        self._los = los                 # callable (a_uid, b_uid) -> bool
        self._env = env or {}           # callable or {(tx,rx): LinkEnv}
        self.root_uid = root_uid

    # -- nodes --
    def add(self, node: CommsNode) -> CommsNode:
        if node.uid in self._nodes:
            raise ValueError(f"duplicate comms node {node.uid}")
        if len(self._nodes) >= NODE_CAP:
            raise ValueError(f"comms node cap {NODE_CAP} is design LAW")
        self._nodes[node.uid] = node
        return node

    def node(self, uid: str) -> CommsNode:
        return self._nodes[uid]

    def uids(self) -> tuple[str, ...]:
        return tuple(sorted(self._nodes))

    def distance_m(self, a_uid: str, b_uid: str) -> float:
        ax, ay = self._nodes[a_uid].pos_m
        bx, by = self._nodes[b_uid].pos_m
        return math.hypot(ax - bx, ay - by)

    def _los_ok(self, a_uid: str, b_uid: str) -> bool:
        return True if self._los is None else bool(self._los(a_uid, b_uid))

    def _env_for(self, tx_uid: str, rx_uid: str) -> LinkEnv:
        if callable(self._env):
            return self._env(tx_uid, rx_uid)
        return self._env.get((tx_uid, rx_uid), CLEAR_ENV)

    # -- links --
    def directed_link(self, tx_uid: str, rx_uid: str) -> DirectedLink | None:
        """Best directed tx→rx part pairing: L-4 existence per pair,
        L-3 rate via linkbudget, §3.3 environment on top. Deterministic:
        parts scanned in slot order, strictly-better replaces."""
        if tx_uid == rx_uid:
            return None
        a, b = self._nodes[tx_uid], self._nodes[rx_uid]
        if not a.powered or not b.powered:
            return None
        d = self.distance_m(tx_uid, rx_uid)
        los = self._los_ok(tx_uid, rx_uid)
        env = self._env_for(tx_uid, rx_uid)
        best, best_key = None, (-1.0, -1)
        for tx_part in a.parts:
            for rx_part in b.parts:
                if not link_exists(tx_part, rx_part, d, los):
                    continue
                band = PARTS[tx_part]["band"]
                rate, floor_ok = effective_rate(
                    rate_bps(tx_part, rx_part, d), band, env)
                if rate <= 0.0 and not floor_ok:
                    continue
                key = (rate, 1 if floor_ok else 0)
                if key > best_key:
                    best_key = key
                    best = DirectedLink(tx_uid, rx_uid, tx_part, rx_part,
                                        band, d, rate, floor_ok)
        return best

    def links(self) -> dict[tuple[str, str], DirectedLink]:
        """All live directed edges (the per-frame vectorized numpy pass
        is 13's layer; this is the reference semantics)."""
        out: dict[tuple[str, str], DirectedLink] = {}
        for a in self.uids():
            for b in self.uids():
                ln = self.directed_link(a, b) if a != b else None
                if ln is not None:
                    out[(a, b)] = ln
        return out

    # -- routing (13: Dijkstra, core:dsn root) --
    def route_to_root(self, uid: str,
                      floor_only: bool = False) -> Route | None:
        """Dijkstra from `uid` to the science-delivery root on summed
        hop light time. floor_only routes over any link whose P0 floor
        is up (commandability); otherwise over schedulable rate > 0.
        Deterministic: heap keyed (light time, uid), strict relaxation."""
        if uid not in self._nodes or self.root_uid not in self._nodes:
            return None
        if uid == self.root_uid:
            return Route((uid,), (), math.inf, 0.0)
        links = self.links()
        usable: dict[str, list[tuple[str, DirectedLink]]] = {}
        for (a, b), ln in sorted(links.items()):
            if ln.floor_available if floor_only else ln.rate_bps > 0.0:
                usable.setdefault(a, []).append((b, ln))
        dist: dict[str, float] = {uid: 0.0}
        prev: dict[str, tuple[str, DirectedLink]] = {}
        heap: list[tuple[float, str]] = [(0.0, uid)]
        seen: set[str] = set()
        while heap:
            d, u = heapq.heappop(heap)
            if u in seen:
                continue
            seen.add(u)
            if u == self.root_uid:
                break
            for v, ln in usable.get(u, ()):
                nd = d + ln.light_s
                if v not in dist or nd < dist[v]:
                    dist[v] = nd
                    prev[v] = (u, ln)
                    heapq.heappush(heap, (nd, v))
        if self.root_uid not in prev:
            return None
        hops: list[DirectedLink] = []
        path: list[str] = [self.root_uid]
        u = self.root_uid
        while u != uid:
            u, ln = prev[u]
            hops.append(ln)
            path.append(u)
        hops.reverse()
        path.reverse()
        return Route(tuple(path), tuple(hops),
                     min(h.rate_bps for h in hops),           # L-5
                     2.0 * dist[self.root_uid])               # L-1/L-5

    def commandable(self, uid: str) -> bool:
        """F-3: a path whose P0 floor is up exists to the root."""
        return self.route_to_root(uid, floor_only=True) is not None

    def total_housekeeping_bps(self) -> float:
        """L-10: 200 bit/s per powered comms node, continuous P1."""
        return housekeeping_bps(
            sum(1 for n in self._nodes.values() if n.powered))


# ---- §3.6 store-and-forward deadline projection (F-10) --------------------------------
def projected_drain_bits(windows, until_t_s: float) -> float:
    """Bits the known drain windows [(t0, t1, rate_bps), ...] can move
    before until_t_s — the scheduler's analytic projection."""
    total = 0.0
    for t0, t1, rate in windows:
        hi = min(t1, until_t_s)
        if hi > t0 and rate > 0.0:
            total += (hi - t0) * rate
    return total


def deadline_at_risk(bits: float, deadline_t_s: float, windows,
                     queued_ahead_bits: float = 0.0) -> bool:
    """F-10: data whose next drain windows cannot move it (plus
    everything queued ahead of it) before the deadline counts
    undelivered — flagged Class-3 AT QUEUE TIME, not at the deadline."""
    return (projected_drain_bits(windows, deadline_t_s)
            < bits + queued_ahead_bits)


# ---- §3.8 anti-softlock invariants (F-3, F-7 — BINDING) --------------------------------
SAFE_MODE = {"attitude": "sun_pointed",
             "beacon": "floor_when_path_next_exists",
             "recovery": ("build_the_link", "fly_there")}


def invariant_f3(graph: CommsGraph) -> list[str]:
    """F-3 (BINDING): bandwidth can stall progress, never strand the
    campaign. Checks (a) every directed link with schedulable rate also
    carries the preemptive P0 floor (the floor exists on any link by
    construction and is never scheduled away), and (b) every node with
    a bulk route to root is commandable over the floor — a commandable
    asset can always be told to point home / deorbit / rendezvous.
    (The ledger side — buffer-full pauses generators, data never
    silently lost — is enforced by scheduler.RecorderBuffer.)
    Returns violations; empty list = invariant holds."""
    bad: list[str] = []
    for (a, b), ln in sorted(graph.links().items()):
        if ln.rate_bps > 0.0 and not ln.floor_available:
            bad.append(f"{a}->{b}: scheduled rate without P0 floor")
    for uid in graph.uids():
        if uid == graph.root_uid:
            continue
        if (graph.route_to_root(uid) is not None
                and not graph.commandable(uid)):
            bad.append(f"{uid}: bulk route exists but not commandable")
    return bad


def required_state(commandable: bool, has_autonomy: bool) -> str:
    """F-7 (BINDING): no-link + no-autonomy assets enter SAFE
    (sun-pointed, beacon at floor when a path next exists); recovery =
    build the link or fly there."""
    return "OPERATING" if (commandable or has_autonomy) else "SAFE"


def dispatch_allowed(required_windows_exist_at_plan_time: bool,
                     signed_override: bool = False) -> bool:
    """F-7 (BINDING): the UI refuses dispatch plans whose required link
    windows don't exist at plan time; stranding requires a signed
    override."""
    return required_windows_exist_at_plan_time or signed_override


# ---- §3.5 relay constellation design loop (2D coverage math) ---------------------------
# Relays are ordinary 06 vessels on 01 conics; coverage falls out of
# 13's occlusion machinery — NO new solver. These are the design-time
# formulas; the worked examples below are BINDING (tests re-derive).


def visibility_arc_deg(body_radius_m: float, orbit_radius_m: float) -> float:
    """Surface visibility arc per relay: 2·arccos(R/r)."""
    return 2.0 * math.degrees(math.acos(body_radius_m / orbit_radius_m))


def ring_continuous(arc_deg: float, n: int) -> bool:
    """Continuous ring coverage needs arc > 360°/N."""
    return arc_deg > 360.0 / n


def earth_occlusion_fraction(body_radius_m: float,
                             orbit_radius_m: float) -> float:
    """Earth-occlusion fraction per orbit: arcsin(R/r)/π."""
    return math.asin(body_radius_m / orbit_radius_m) / math.pi


def orbit_period_s(mu_m3_s2: float, orbit_radius_m: float) -> float:
    """Circular period 2π·√(r³/μ) (01 canon, restated for the loop)."""
    return 2.0 * math.pi * math.sqrt(orbit_radius_m ** 3 / mu_m3_s2)


def stationary_orbit_radius_m(mu_m3_s2: float, period_s: float) -> float:
    """Synchronous radius (μ·T²/4π²)^(1/3) — r_areo = 20,430 km."""
    return (mu_m3_s2 * period_s ** 2 / (4.0 * math.pi ** 2)) ** (1.0 / 3.0)


def horizon_slant_m(body_radius_m: float, orbit_radius_m: float) -> float:
    """Slant range to a surface user at the relay's horizon: √(r²−R²)."""
    return math.sqrt(orbit_radius_m ** 2 - body_radius_m ** 2)


def crosslink_chord_m(orbit_radius_m: float, n: int) -> float:
    """Chord between adjacent ring relays: 2·r·sin(π/N)."""
    return 2.0 * orbit_radius_m * math.sin(math.pi / n)


CONSTELLATIONS: dict[str, dict] = {
    "lunar_farside_ring": {     # §3.5.1 (Act 2) — the Queqiao moment
        "act": 2, "blueprint": "Heliograph", "n": 3, "phase_deg": 120.0,
        "orbit_radius_m": 5.000e6, "body_radius_m": 1.737e6,
        "period_h": 8.8, "visibility_arc_deg": 139.0,
        "prox_leg_bps_computed": (14e6, 28e6), "prox_leg_bps_capped": 2.0e6,
        "earth_occlusion_frac": 0.113, "crosslink_m": 8.66e6,
        "crosslink_bps": 200.0,         # P0 continuity only
        "occluded_buffer_bits": 7.2e9,  # ≤1 h at 2 Mbit/s ingest ≪ DR-1
        "mass_to_llo_t": 1.1,
        "note": "no EML-2 halo in 2D — the collinear point sits exactly "
                "behind the Moon; the honest solution is the ring"},
    "areostationary_trio": {    # §3.5.2 (Act 3)
        "act": 3, "blueprint": "Heliograph-A", "n": 3, "phase_deg": 120.0,
        "mu_m3_s2": 4.2828e13, "period_h": 24.623,
        "orbit_radius_m": 2.043e7, "body_radius_m": 3.396e6,
        "visibility_arc_deg": 161.0,
        "prox_leg_bps_nadir": 1.0e6, "prox_leg_bps_horizon": 0.74e6,
        "crosslink_m": 3.54e7, "crosslink_bps": 12.0,   # P0 only
        "earth_occlusion_frac": 0.053,
        "trunk_bps_by_season": (0.42e6, 6.0e6)},
    "pharos_pair": {            # §3.5.3 (Acts 3–4)
        "act": "3-4", "blueprint": "Pharos", "n": 2,
        "helio_radius_au": 1.0, "phase_from_earth_deg": 60.0,
        "mars_leg_au": 2.20, "earth_leg_au": 1.0,
        "sun_clearance_au": 0.6,
        "mars_leg_bps": 1.17e6, "earth_leg_bps": 50e6,
        "path_bps_through_blackout": 1.2e6, "stock_dish_m_bps": 54e3,
        "note": "two relays at ±60° cover every superior conjunction of "
                "every body forever"},
}
