"""The five-act campaign spine (12 §1.1, G-12/G-13), the 38-row Firsts
ladder (12 §1.5, E-13), Prestige (12 §1.6, E-14…E-16) with the investor
rounds it gates (12 §1.7, E-17…E-19, DECISIONS F33), and the Program
Charter chain (12 §1.11, T-1) — the v2 depth layer over the existing
Program/Contract economy.

Everything is data plus small pure functions over a plain campaign
SNAPSHOT dict; nothing here mutates game state except the explicit
`award_firsts` convenience (which only calls the existing Program API,
so the program save section keeps its shape). The snapshot reuses the
keys the v1 layer already persists ("milestones" with its existing
"orbited"/"docked" flags, "visited", "visited_surface") and adds plain
keys — every predicate defaults missing keys, so minimal dicts work:

    milestones        set[str]   one-shot event flags raised by game
                                 systems (new flags documented per row)
    visited           set[str]   body SOIs reached      ("core:moon")
    landed            set[str]   bodies landed on (robotic counts)
    crewed_landed     set[str]   bodies landed on with crew aboard
    colonized         set[str]   bodies with a founded surface base
    tech_tier         int        world tier reached (0..4)
    industry_online   set[str]   commissioned fab modules (05 §1.6
                                 keys, e.g. "fab_wafer_fab")
    vehicles_operated set[str]   vehicle classes operated ("submarine")
    extracted_t       dict[str, float]  cumulative tonnes mined by
                                 resource (exact spellings, 12 §2.3)
    refined_t         dict[str, float]  cumulative tonnes refined

Acts advance on EXIT MILESTONES (G-13) and are monotonic — pass the
earned-Firsts set and a gutted snapshot can never demote the act. The
v1 contract table (aphelion/game/campaign.py) keeps its 1..4 act gates;
LEGACY_ACT_GATE maps this five-act spine onto that numbering so the
existing CONTRACTS tuple and program save format stay untouched.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Callable

from aphelion.sim.economy import Contract, Program

END_ACT = 6                     # the post-Act-5 endgame ("End" row)
YEAR = 365.0 * 86_400.0


def snapshot(**kw) -> dict:
    """A fully defaulted campaign snapshot (tests build minimal ones)."""
    S: dict = dict(milestones=set(), visited=set(), visited_surface=set(),
                   landed=set(), crewed_landed=set(), colonized=set(),
                   tech_tier=0, industry_online=set(),
                   vehicles_operated=set(), extracted_t={}, refined_t={})
    S.update(kw)
    return S


# ---- predicate factories (pure, default-tolerant) ------------------------

def _flag(name: str) -> Callable[[dict], bool]:
    return lambda S: name in S.get("milestones", ())


def _visited(body: str) -> Callable[[dict], bool]:
    return lambda S: body in S.get("visited", ())


def _landed(body: str) -> Callable[[dict], bool]:
    return lambda S: body in S.get("landed", ())


def _crewed(body: str) -> Callable[[dict], bool]:
    return lambda S: body in S.get("crewed_landed", ())


def _colonized(body: str) -> Callable[[dict], bool]:
    return lambda S: body in S.get("colonized", ())


def _industry(key: str) -> Callable[[dict], bool]:
    return lambda S: key in S.get("industry_online", ())


def _vehicle(cls: str) -> Callable[[dict], bool]:
    return lambda S: cls in S.get("vehicles_operated", ())


def _extracted(resource: str, tonnes: float) -> Callable[[dict], bool]:
    return lambda S: S.get("extracted_t", {}).get(resource, 0.0) >= tonnes


def _refined(resource: str, tonnes: float) -> Callable[[dict], bool]:
    return lambda S: S.get("refined_t", {}).get(resource, 0.0) >= tonnes


def _tier(n: int) -> Callable[[dict], bool]:
    return lambda S: S.get("tech_tier", 0) >= n


def _all(*ps: Callable[[dict], bool]) -> Callable[[dict], bool]:
    return lambda S: all(p(S) for p in ps)


# ---- the Firsts ladder (12 §1.5, E-13): all 38 rows -----------------------
# One-time payments x funding multiplier (D-2); repeats pay nothing; each
# fires a Chronicle FIRST entry. payout_m == 0.0 renders the spec's "—
# (contract)" rows: the paired contract pays, the First only awards
# Prestige. target_h = cumulative pacing target (G-12).

@dataclass(frozen=True)
class First:
    fid: str
    name: str
    act: int                    # ladder act (1..5, END_ACT)
    payout_m: float             # $M (constant-2049); 0.0 = contract pays
    prestige: int
    target_h: float
    check: Callable[[dict], bool]
    crewed_body: str | None = None      # crewed variant pays more …
    crewed_prestige: int = 0            # … (Titan landing: +75 not +50)


FIRSTS: tuple[First, ...] = (
    # -- Act 1: Earth + LEO (8 rows) ---------------------------------------
    First("f_first_launch", "First launch (any)", 1, 5.0, 5, 1.0,
          _flag("launched")),
    First("f_first_orbit", "First orbit", 1, 30.0, 10, 3.0,
          _flag("orbited")),                    # existing v1 save flag
    First("f_first_reflight", "First stage recovered & reflown", 1,
          20.0, 5, 5.0, _flag("stage_reflown")),
    First("f_first_docking", "First docking", 1, 25.0, 10, 7.0,
          _flag("docked")),                     # existing v1 save flag
    First("f_first_crewed_orbit", "First crewed orbit", 1, 60.0, 20, 9.0,
          _flag("crewed_orbit")),
    First("f_abort_demo", "In-flight abort demonstrated", 1, 0.0, 5, 10.0,
          _flag("abort_demo")),                 # pays via CT-10
    First("f_leo_station_core",
          "LEO station core operational (4 crew, 30 d)", 1, 40.0, 10,
          11.0, _flag("station_core_4x30")),
    First("f_cryo_depot_transfer",
          "First cryo depot transfer demo (T1)", 1, 50.0, 10, 12.0,
          _all(_flag("depot_cryo_transfer"), _tier(1))),  # ACT 1 EXIT
    # -- Act 2: Moon (7 rows) ----------------------------------------------
    First("f_lunar_flyby", "First lunar flyby / orbit", 2, 40.0, 10, 14.0,
          _visited("core:moon")),
    First("f_robotic_moon_landing", "First robotic lunar landing", 2,
          80.0, 20, 16.0, _landed("core:moon")),
    First("f_polar_ice", "Polar ice confirmed by drill", 2, 60.0, 10,
          19.0, _flag("polar_ice_drilled")),
    First("f_crewed_moon_landing", "First crewed lunar landing", 2,
          300.0, 50, 22.0, _crewed("core:moon")),
    First("f_lunar_ice_mine",
          "Lunar ice mine online (first 10 t Water extracted)", 2,
          150.0, 30, 28.0, _extracted("Water", 10.0)),
    First("f_lunar_lox_at_depot", "Lunar LOX delivered to orbital depot",
          2, 100.0, 20, 32.0, _flag("lunar_lox_at_depot")),
    First("f_lunar_base_90d",
          "Surface base: 4 crew x 90 d continuous", 2, 120.0, 20, 35.0,
          _flag("base_4crew_90d")),     # ACT 2 EXIT (with LOX-at-depot)
    # -- Act 3: Mars & NEAs (7 rows) -----------------------------------------
    First("f_ntr_burn", "First NTR burn in orbit (cold-launch rule)", 3,
          100.0, 25, 38.0, _flag("ntr_burn_orbit")),
    First("f_robotic_mars_edl", "First robotic Mars EDL", 3, 150.0, 30,
          44.0, _landed("core:mars")),
    First("f_crewed_mars_landing", "First crewed Mars landing", 3,
          500.0, 75, 50.0, _crewed("core:mars")),
    First("f_mars_methalox", "First kg of Mars-made methalox", 3, 80.0,
          30, 55.0, _flag("mars_methalox")),
    First("f_nea_volatiles", "NEA rendezvous + 100 t volatiles extracted",
          3, 120.0, 25, 60.0,
          _all(_flag("nea_rendezvous"), _extracted("Volatiles", 100.0))),
    First("f_mars_sample_return", "Mars sample return delivered", 3, 0.0,
          40, 65.0, _flag("mars_sample_return")),  # pays via CT-17
    First("f_food_harvest", "First off-Earth food harvest", 3, 50.0, 15,
          70.0, _flag("food_harvest")),     # ACT 3 EXIT (with methalox)
    # -- Act 4: Belt & Venus (7 rows) ----------------------------------------
    First("f_belt_arrival", "Main-belt arrival (Ceres-class rendezvous)",
          4, 100.0, 25, 80.0, _visited("core:ceres")),
    First("f_metal_mine",
          "Metallic-asteroid mine online (100 t IronSteel refined)", 4,
          120.0, 25, 86.0, _refined("IronSteel", 100.0)),
    First("f_venus_aerostat", "Venus aerostat deployed (crewed 30 d)", 4,
          250.0, 75, 92.0, _flag("venus_aerostat_30d")),
    First("f_silicon_independence",
          "Silicon Independence (wafer fab online)", 4, 200.0, 50, 100.0,
          _industry("fab_wafer_fab")),                  # ACT 4 EXIT
    First("f_mass_driver", "Mass driver first throw", 4, 100.0, 25,
          105.0, _flag("mass_driver_throw")),
    First("f_food_independence",
          "Food independence at one site (SSI_food = 1.0, 365 d)", 4,
          100.0, 25, 112.0, _flag("ssi_food_365d")),
    First("f_never_earth_ship",
          "First never-Earth ship (built, fueled, crewed off-Earth)", 4,
          150.0, 40, 118.0, _flag("never_earth_ship")),
    # -- Act 5: Jupiter / Saturn (6 rows) ------------------------------------
    First("f_jupiter_arrival",
          "Jupiter system arrival; Callisto base seed", 5, 200.0, 50,
          128.0, _all(_visited("core:jupiter"), _colonized("core:callisto"))),
    First("f_europa_bore",
          "Europa ocean bore relay online (robotic megaproject)", 5,
          150.0, 40, 135.0, _flag("europa_bore_relay")),
    First("f_titan_landing", "Titan landing", 5, 200.0, 50, 140.0,
          _landed("core:titan"),
          crewed_body="core:titan", crewed_prestige=75),
    First("f_titan_submarine", "Titan submarine deployed", 5, 150.0, 50,
          150.0, _vehicle("submarine")),
    First("f_enceladus_plume", "Enceladus plume-water harvest (100 t)",
          5, 100.0, 25, 158.0, _flag("enceladus_plume_100t")),
    First("f_saturn_base",
          "Saturn-system permanent base (12 crew x 2 yr)", 5, 250.0, 50,
          168.0, _flag("saturn_base_12crew_2yr")),      # ACT 5 EXIT
    # -- Endgame (3 rows) ----------------------------------------------------
    First("f_foundation_audit",
          "Foundation Audit passed (Foundation Day)", END_ACT, 0.0, 100,
          180.0, _flag("foundation_audit_passed")),     # E-28 pays itself
    First("f_precursor_launched", "Interstellar Precursor launched",
          END_ACT, 0.0, 100, 190.0, _flag("precursor_launched")),
    First("f_precursor_100au", "Precursor crosses 100 AU (<= 10 yr)",
          END_ACT, 0.0, 100, math.inf, _flag("precursor_100au")),
)

FIRST_BY_ID: dict[str, First] = {f.fid: f for f in FIRSTS}


def check_firsts(S: dict, already_earned: set[str] | frozenset = frozenset()
                 ) -> list[str]:
    """Newly earned First ids in ladder order; one-shot (E-13: repeats
    pay nothing — anything in `already_earned` never re-fires)."""
    return [f.fid for f in FIRSTS
            if f.fid not in already_earned and f.check(S)]


def first_payout(fid: str, funding_mult: float = 1.0) -> float:
    """Payout in $, x the D-2 funding multiplier. 0.0 for the '—
    (contract pays)' rows."""
    return FIRST_BY_ID[fid].payout_m * 1e6 * funding_mult


def first_prestige(fid: str, S: dict) -> int:
    """Prestige for the row, honoring crewed variants (Titan landing
    pays +75 instead of +50 when the landing was crewed)."""
    f = FIRST_BY_ID[fid]
    if f.crewed_body and f.crewed_body in S.get("crewed_landed", ()):
        return f.crewed_prestige
    return f.prestige


def award_firsts(program: Program, prestige: "Prestige", t: float,
                 S: dict, earned: set[str],
                 funding_mult: float = 1.0) -> list[str]:
    """Sweep convenience: pay newly earned Firsts through the EXISTING
    Program ledger (history entries "first:<fid>", so the program save
    section keeps its shape), award Prestige, mark them earned. Returns
    toast lines."""
    toasts: list[str] = []
    for fid in check_firsts(S, earned):
        earned.add(fid)
        f = FIRST_BY_ID[fid]
        pay = first_payout(fid, funding_mult)
        if pay > 0.0:
            program.earn(t, pay, f"first:{fid}")
        p = first_prestige(fid, S)
        prestige.add(p)
        money = f" +${pay / 1e6:,.0f}M" if pay > 0.0 else ""
        toasts.append(f"FIRST: {f.name}{money}  PRESTIGE +{p}")
    return toasts


# ---- the five acts + endgame (12 §1.1, G-12/G-13) -------------------------

@dataclass(frozen=True)
class Act:
    act: int
    theater: str
    tiers: str
    regime: str                 # economic regime (one line)
    center: str                 # gameplay center
    exit_fids: tuple[str, ...]  # ALL earned -> next act begins (G-13)
    hours: tuple[float, float]  # target cumulative hours


ACTS: tuple[Act, ...] = (
    Act(1, "Earth + LEO", "T0-T1",
        "Pure $: contracts, Firsts, Seed->Series A; every kg hurts",
        "Pilot + Engineer: launcher design, reuse, depots",
        ("f_cryo_depot_transfer",), (0.0, 12.0)),
    Act(2, "Moon", "T1-T2",
        "$ still king; CLPS-style rates; Series B; first SSI pixels",
        "Base mode; first ISRU chain, surface ops",
        ("f_lunar_base_90d", "f_lunar_lox_at_depot"), (12.0, 35.0)),
    Act(3, "Mars & NEAs", "T2",
        "The hinge: money big but logistics dominates",
        "Planner ascendant; NTR logistics, windows, Mars ISRU closure",
        ("f_food_harvest", "f_mars_methalox"), (35.0, 75.0)),
    Act(4, "Belt & Venus", "T2-T3",
        "Money fades (E-19); Earth manifests thin out",
        "Base + Planner; multi-site industry, aerostat ops",
        ("f_silicon_independence",), (75.0, 120.0)),
    Act(5, "Jupiter/Saturn", "T3-T4",
        "Mass economy; $ ledger a side-tab; Prestige is the score",
        "Megaproject staging, MW-class EP fleets, Titan volatiles",
        ("f_saturn_base",), (120.0, 170.0)),
    Act(END_ACT, "-", "T4",
        "None - audits",
        "Foundation Audit (E-28) and/or Interstellar Precursor (E-29)",
        (), (170.0, 220.0)),
)

ACT_BY_NO: dict[int, Act] = {a.act: a for a in ACTS}

# per-act cumulative spend envelope, $B (12 §1.1; money decouples after 3)
SPEND_ENVELOPE_B: dict[int, float] = {1: 0.45, 2: 1.6, 3: 4.0}

ACT_ROMAN = {1: "I", 2: "II", 3: "III", 4: "IV", 5: "V", END_ACT: "END"}


def act_entered(act_no: int, S: dict,
                earned: set[str] | frozenset = frozenset()) -> bool:
    """G-13 entry condition: every exit First of the previous act is
    earned (monotonic — earned set wins) or live-satisfied by S."""
    if act_no <= 1:
        return True
    prev = ACT_BY_NO[5 if act_no == END_ACT else act_no - 1]
    return all(fid in earned or FIRST_BY_ID[fid].check(S)
               for fid in prev.exit_fids)


def current_act(S: dict,
                earned: set[str] | frozenset = frozenset()) -> int:
    """Highest act entered, walking the spine in order (acts never
    revert: pass the earned-Firsts set and an empty snapshot holds)."""
    act = 1
    for a in ACTS[1:]:
        if not act_entered(a.act, S, earned):
            break
        act = a.act
    return act


# ---- legacy act-gate bridge -----------------------------------------------
# The v1 contract table (aphelion/game/campaign.py) gates on acts 1..4
# (LEO+Luna / inner / outer / way-out). This maps the five-act spine onto
# that numbering so the existing CONTRACTS tuple, Program, and save
# format keep working while the 60% gate is replaced by exit milestones.

LEGACY_ACT_GATE: dict[int, int] = {1: 1, 2: 1, 3: 2, 4: 2, 5: 3,
                                   END_ACT: 4}


def legacy_act(v2_act: int) -> int:
    return LEGACY_ACT_GATE[v2_act]


def legacy_act_unlocked(gate: int, S: dict,
                        earned: set[str] | frozenset = frozenset()) -> bool:
    """Drop-in for campaign.act_unlocked under the v2 spine: a v1 act
    gate opens once the campaign reaches a v2 act that maps to it."""
    return legacy_act(current_act(S, earned)) >= gate


# ---- act-gated content keys (12 §1.4 act column) ---------------------------
# (first_act, last_act) inclusive; "A2+" reads (2, 5). The endgame keeps
# act-5 availability (the board never empties during the audits).

CONTENT_GATES: dict[str, tuple[int, int]] = {
    "CT-01": (1, 1), "CT-02": (1, 1), "CT-03": (1, 2), "CT-04": (1, 2),
    "CT-05": (1, 2), "CT-06": (1, 2), "CT-07": (1, 3), "CT-08": (1, 2),
    "CT-09": (1, 2), "CT-10": (1, 1), "CT-11": (2, 2), "CT-12": (2, 2),
    "CT-13": (2, 2), "CT-14": (2, 4), "CT-15": (2, 2), "CT-16": (3, 3),
    "CT-17": (3, 3), "CT-18": (3, 3), "CT-19": (3, 5), "CT-20": (4, 4),
    "CT-21": (4, 5), "CT-22": (5, 5), "CT-23": (2, 5), "CT-24": (2, 5),
    "CT-25": (1, 2),
}


def content_available(key: str, act: int) -> bool:
    lo, hi = CONTENT_GATES[key]
    return lo <= min(act, 5) <= hi


# ---- Prestige (12 §1.6, E-14…E-16) -----------------------------------------

P_MIN, P_MAX = 0, 1000
PRESTIGE_GATES = (50, 150, 300, 500)        # investor gates = tiers

# E-14 named deltas. anomaly_visit is +5 x the anomaly's listed
# multiplier (pass mult=); stand_down_month is the E-23 decay per month.
PRESTIGE_EVENTS: dict[str, int] = {
    "contract_bonus_ct09": 25,      # Hubble reboost (unique)
    "contract_bonus_ct21": 50,      # Venera 13 recovery (unique)
    "anomaly_visit": 5,             # x listed multiplier
    "rescue": 50,                   # F-2
    "safety_year": 5,               # consecutive crewed year, 0 deaths
    "crew_fatality": -100,
    "founder_fatality": -150,
    "contract_failure": -10,        # E-10
    "heritage_violation": -50,      # E-16
    "agency_assist": -100,          # F-3
    "stand_down_month": -5,         # E-23
    "failed_promise": -100,         # E-17
}

# E-16 heritage zones
HERITAGE_RADIUS_KM = 10.0
HERITAGE_FINE = 100e6
HERITAGE_LOCKOUT_YR = 1


@dataclass(slots=True)
class Prestige:
    """Scalar P in [floor, 1000]. Floor = max(0, highest investor gate
    ever crossed - 100): history can't be fully erased (E-14)."""
    value: float = 0.0
    highest_gate: int = 0

    @property
    def floor(self) -> float:
        return max(0.0, self.highest_gate - 100.0)

    def add(self, delta: float) -> float:
        v = min(float(P_MAX), self.value + delta)
        for g in PRESTIGE_GATES:
            if v >= g:
                self.highest_gate = max(self.highest_gate, g)
        self.value = max(self.floor, v)
        return self.value

    def event(self, name: str, mult: float = 1.0) -> float:
        return self.add(PRESTIGE_EVENTS[name] * mult)

    # E-15 effects: what Prestige buys ------------------------------------
    @property
    def board_slots(self) -> int:
        """E-8 contract-board size: N = 3 + floor(P/100), max 12."""
        return min(12, 3 + int(self.value) // 100)

    @property
    def recruit_bonus(self) -> int:
        """Recruitment archetype quality roll +1 per 200 P."""
        return int(self.value) // 200

    @property
    def tourism_mult(self) -> float:
        """Tourism pricing x (1 + P/1000)."""
        return 1.0 + self.value / 1000.0

    # persistence (additive save section; missing dict -> E-1 start P=0)
    def to_dict(self) -> dict:
        return {"value": self.value, "highest_gate": self.highest_gate}

    @classmethod
    def from_dict(cls, d: dict | None) -> "Prestige":
        d = d or {}
        return cls(value=float(d.get("value", 0.0)),
                   highest_gate=int(d.get("highest_gate", 0)))


# ---- investors & debt (12 §1.7, E-17…E-19; DECISIONS F33) -------------------

@dataclass(frozen=True)
class Round:
    rid: str
    gate: int                       # Prestige gate (E-17)
    cash_m: float                   # grant, $M
    promise_mo: int | None          # promise deadline; None = the
                                    # tutorial charter chain (Seed)


ROUNDS: tuple[Round, ...] = (
    Round("seed", 0, 300.0, None),          # pre-banked at start (E-1)
    Round("series_a", 50, 250.0, 36),
    Round("series_b", 150, 600.0, 36),
    Round("series_c", 300, 1500.0, 36),
    Round("series_d", 500, 4000.0, 48),
)

ROUND_BY_ID: dict[str, Round] = {r.rid: r for r in ROUNDS}

# fail a promise: Prestige -100, no rounds 5 yr, overhead +10% for 2 yr
PROMISE_FAIL = {"prestige": -100, "round_lockout_yr": 5,
                "overhead_add": 0.10, "overhead_yr": 2}

# E-18 bridge loan: one revolving instrument, auto-drawn at Cash < 0;
# bullet at 24 mo; auto-repaid early when Cash > 2 x principal.
BRIDGE_LOAN = {"revenue_frac": 0.25, "term_mo": 24, "apr": 0.12,
               "monthly_rate": 0.01, "repay_cash_mult": 2.0}

# E-19 money-fade trigger: SSI_program >= 0.8 sustained 730 d.
MONEY_FADE = {"ssi_program": 0.8, "sustain_days": 730.0}


def rounds_available(prestige_value: float,
                     raised: set[str] | frozenset = frozenset()
                     ) -> list[Round]:
    """Raisable rounds (Seed is pre-banked, never re-raised). Raising
    additionally requires choosing a promise — one Firsts milestone
    delivered within Round.promise_mo (E-17)."""
    return [r for r in ROUNDS[1:]
            if r.rid not in raised and prestige_value >= r.gate]


def money_faded(ssi_program: float, sustained_days: float) -> bool:
    return (ssi_program >= MONEY_FADE["ssi_program"]
            and sustained_days >= MONEY_FADE["sustain_days"])


# ---- the Program Charter chain (12 §1.11, T-1) ------------------------------
# Charters are contracts from a patient seed investor: deadline-free and
# penalty-free (E-9/E-10 do not apply; a failed charter re-offers).

CHARTER_DEADLINE_S = 1e18       # finite "never" — JSON-safe, ~31 Gyr


@dataclass(frozen=True)
class Charter:
    cid: str
    desc: str
    payout_m: float
    teaches: str
    unlocks: str


CHARTERS: tuple[Charter, ...] = (
    Charter("charter_recovery", "Charter 1: recover the capsule", 5.0,
            "aborts, recovery value", "Finance tab"),
    Charter("charter_launcher",
            "Charter 2: assemble the provided orbital launcher", 10.0,
            "Engineer mode, dv/TWR, paid sims", "Designer full palette"),
    Charter("charter_orbit", "Charter 3: first orbit", 20.0,
            "Planner basics, nodes, event-guard warp", "Transfer dialog"),
    Charter("charter_docking",
            "Charter 4: rendezvous + first docking", 15.0,
            "phasing, target markers, RCS", "station assembly"),
)

CHARTER_BY_ID: dict[str, Charter] = {c.cid: c for c in CHARTERS}

# veteran skip grants the summed charter payouts as starting capital
VETERAN_SKIP_M = 50.0


def is_charter(contract_id: str) -> bool:
    return contract_id.startswith("charter_")


def charter_contract(ch: Charter) -> Contract:
    """The charter as a plain v1 Contract — drops straight into
    Program.contracts and the existing program save section."""
    return Contract(ch.cid, ch.desc, payout=ch.payout_m * 1e6,
                    deadline_s=CHARTER_DEADLINE_S)


# ---- integrity (called by the tests; cheap enough to call at load) ----------

def validate_acts() -> None:
    assert len(FIRSTS) == 38, "the Firsts ladder is 38 rows (12 §1.5)"
    assert len(FIRST_BY_ID) == 38, "First ids must be unique"
    per_act = {a: sum(1 for f in FIRSTS if f.act == a)
               for a in (1, 2, 3, 4, 5, END_ACT)}
    assert per_act == {1: 8, 2: 7, 3: 7, 4: 7, 5: 6, END_ACT: 3}
    assert len(ACTS) == 6 and [a.act for a in ACTS] == [1, 2, 3, 4, 5,
                                                        END_ACT]
    for a in ACTS:
        for fid in a.exit_fids:
            assert fid in FIRST_BY_ID and FIRST_BY_ID[fid].act == a.act
    assert len(CONTENT_GATES) == 25, "CT-01..CT-25 (12 §1.4)"
    assert abs(VETERAN_SKIP_M - sum(c.payout_m for c in CHARTERS)) < 1e-9
