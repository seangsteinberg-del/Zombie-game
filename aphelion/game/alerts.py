"""The alert bus + Chronicle (12 §3.5 A-1…A-6, §4 C-1…C-4) and the
C19 birth/generation rule (DECISIONS C19, 08 §4.9).

ALERT BUS — ISS-style caution & warning, four classes (A-1). The warp
law (A-2): `warp_max_effective = min(warp_player, min over active
unacknowledged alerts of warp_cap(class))`. Class 1 latches: ack never
releases it — only resolution or an explicit Accept-Risk (covered
switch, logged to the Chronicle forever). Master Alarm (A-6, `Delete`)
silences Class 2–3 audio but leaves every warp cap in place. Toast
budget 3 (A-3) with (source, type) 24-h dedup; >10 Class-2/3 alerts in
60 s at one site collapse into a single CASCADE card (§8.3), root cause
first. Per-type class remap one step up/down — never out of Class 1 —
plus per-type pause override (A-4).

CHRONICLE — the campaign's generated history (C-1 schema: t, type,
class, subjects[], location, numbers{}, autoshot_id, seed). Append-only;
target volume 200–800 entries; hard cap 2,000 with oldest
non-FIRST/DEATH entries degrading to text-only (§8.12, snapshots
≤ 64 kB). `export_text` renders the dry mission-report document
("The Program, 2049–20XX", C-2/C-4); chapter cards carry auto-computed
stats (C-3). Per 13 §1.1 nothing here polls: callers post alerts at
event boundaries and the bus only answers queries.

BIRTHS (C19) — demographic entries for long colonies: settlement policy
+ discovered g_repro gate (11 LS-09→LS-10→LS-11 bracket narrowing) +
≥ 2 adults + continuous occupation ≥ one gestation. Children are
non-working crew with scaled metabolic baselines (08 §4.9); the
new-crew dict matches the save's crew section exactly
(aphelion/save/campaign.py).

Deterministic throughout: naming and g_repro draw from blake2b of the
campaign seed; no wall clock, no global rng.
"""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from aphelion.game.crew import ROLES
from aphelion.sim.habitat.food import BODY_RESERVE_KCAL

YEAR = 365.0 * 86_400.0
DAY = 86_400.0

# ---- A-1: the four alert classes (12 §3.5, colors §3.4) ---------------------
# warp_cap is a multiplier ceiling: 0.0 = tier 0 + pause, inf = no effect.
ALERT_CLASSES: dict[int, dict] = {
    1: {"name": "EMERGENCY", "color": "#E25555", "sound": "klaxon",
        "warp_cap": 0.0, "pause": True, "latching": True},
    2: {"name": "WARNING", "color": "#E8893B", "sound": "tone",
        "warp_cap": 1.0, "pause": False, "latching": False},
    3: {"name": "CAUTION", "color": "#E8C547", "sound": "chime",
        "warp_cap": 1_000.0, "pause": False, "latching": False},
    4: {"name": "ADVISORY", "color": "#E6EDF3", "sound": "silent",
        "warp_cap": math.inf, "pause": False, "latching": False},
}
WARP_CAPS = {c: ALERT_CLASSES[c]["warp_cap"] for c in ALERT_CLASSES}

TOAST_BUDGET = 3                 # A-3
DEDUP_WINDOW_S = 24.0 * 3_600.0  # A-3: identical (source, type) in 24 h
STORM_WINDOW_S = 60.0            # §8.3
STORM_THRESHOLD = 10             # ">10 Class-2/3 alerts within 60 s"
MASTER_ALARM_KEY = "Delete"      # A-6 (`Backspace×2` reserved for abort)

# E-9: deadline alerts at T−90/30/7 d; classes per the §3.5 taxonomy
# (contract T−30 d = Class 3 caution, deadline T−7 d = Class 2 warning).
DEADLINE_ALERT_DAYS: tuple[tuple[float, int], ...] = (
    (90.0, 4), (30.0, 3), (7.0, 2))
# G-9 death spiral: runway < 60 d → Class 3; < 14 d → Class 2.
RUNWAY_ALERT_DAYS: tuple[tuple[float, int], ...] = ((60.0, 3), (14.0, 2))


@dataclass
class Alert:
    """One alert card. (t, class, source, text) plus expiry/ack state;
    payload-safe (plain scalars only, 13 §1.1)."""
    aid: int
    t: float
    cls: int
    source_id: str
    text: str
    kind: str = ""               # event type, the A-3/A-4 dedup/remap key
    site: str = ""               # storm-rule grouping (defaults source)
    expires_s: float | None = None
    pause: bool = False
    acked: bool = False
    audio_acked: bool = False
    accepted_risk: bool = False
    resolved: bool = False
    collapsed: bool = False      # folded into a CASCADE card
    count: int = 1               # ×N dedup counter
    t_last: float = 0.0
    children: list[int] = field(default_factory=list)

    @property
    def latching(self) -> bool:
        return ALERT_CLASSES[self.cls]["latching"]

    @property
    def warp_cap(self) -> float:
        return ALERT_CLASSES[self.cls]["warp_cap"]

    def released(self) -> bool:
        """Has this alert's warp cap been lifted? (A-2)"""
        if self.resolved:
            return True
        if self.latching:                    # Class 1 latches
            return self.accepted_risk
        return self.acked

    def to_dict(self) -> dict:
        return {
            "aid": self.aid, "t": self.t, "cls": self.cls,
            "source_id": self.source_id, "text": self.text,
            "kind": self.kind, "site": self.site,
            "expires_s": self.expires_s, "pause": self.pause,
            "acked": self.acked, "audio_acked": self.audio_acked,
            "accepted_risk": self.accepted_risk,
            "resolved": self.resolved, "collapsed": self.collapsed,
            "count": self.count, "t_last": self.t_last,
            "children": list(self.children),
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Alert":
        return cls(**d)


class AlertBus:
    """The single program-wide alert registry (A-1…A-6). Optionally
    wired to a Chronicle so Accept-Risk events log forever (A-2)."""

    def __init__(self, chronicle: "Chronicle | None" = None):
        self.alerts: list[Alert] = []
        self.overrides: dict[str, dict] = {}    # kind -> {delta, pause}
        self.chronicle = chronicle
        self._next_aid = 1

    # -- A-4 overrides --------------------------------------------------------
    def set_override(self, kind: str, delta: int = 0,
                     pause: bool | None = None) -> None:
        """Remap an event type one class up/down (delta ∈ {-1, 0, +1};
        lower class number = more severe) and/or force pause on/off.
        Class-1 events never leave Class 1."""
        self.overrides[kind] = {"delta": max(-1, min(1, int(delta))),
                                "pause": pause}

    def _effective(self, cls: int, kind: str) -> tuple[int, bool]:
        ov = self.overrides.get(kind)
        eff = cls
        if ov and cls != 1:                      # never out of Class 1
            eff = max(1, min(4, cls + ov["delta"]))
        pause = ALERT_CLASSES[eff]["pause"]
        if ov and ov["pause"] is not None:
            pause = ov["pause"]
        return eff, pause

    # -- posting ----------------------------------------------------------------
    def post(self, t: float, cls: int, source_id: str, text: str, *,
             kind: str = "", expires_s: float | None = None,
             site: str = "") -> Alert:
        """Register an alert. Identical (source, type) within 24 h merge
        with a ×N counter (A-3); the storm rule (§8.3) may collapse
        Class-2/3 bursts into one CASCADE card."""
        eff, pause = self._effective(cls, kind)
        key = kind or text
        for a in self.alerts:
            if (a.source_id == source_id and (a.kind or a.text) == key
                    and not a.resolved
                    and t - a.t_last <= DEDUP_WINDOW_S):
                a.count += 1
                a.t_last = t
                a.acked = a.audio_acked = False      # new event re-raises
                return a
        a = Alert(self._next_aid, t, eff, source_id, text, kind=kind,
                  site=site or source_id, expires_s=expires_s,
                  pause=pause, t_last=t)
        self._next_aid += 1
        self.alerts.append(a)
        if eff in (2, 3) and kind != "CASCADE":
            self._storm_check(t, a.site)
        return a

    def _storm_check(self, t: float, site: str) -> None:
        burst = [a for a in self.alerts
                 if a.cls in (2, 3) and a.kind != "CASCADE"
                 and not a.resolved and not a.collapsed
                 and a.site == site and t - a.t_last <= STORM_WINDOW_S]
        if len(burst) <= STORM_THRESHOLD:
            return
        burst.sort(key=lambda a: (a.t, a.aid))       # root cause first
        cascade = next((a for a in self.alerts
                        if a.kind == "CASCADE" and a.site == site
                        and not a.resolved), None)
        if cascade is None:
            cascade = self.post(t, 2, site, f"CASCADE at {site}",
                                kind="CASCADE", site=site)
        for a in burst:
            a.collapsed = True
            if a.aid not in cascade.children:
                cascade.children.append(a.aid)
        cascade.count = len(cascade.children)

    # -- queries ---------------------------------------------------------------
    def get(self, aid: int) -> Alert | None:
        for a in self.alerts:
            if a.aid == aid:
                return a
        return None

    def find(self, source_id: str, kind: str) -> Alert | None:
        """Any alert ever posted with this (source, type) — the Alert
        Center history view (S-15) and once-only sweeps use this."""
        for a in self.alerts:
            if a.source_id == source_id and a.kind == kind:
                return a
        return None

    def active(self, t: float) -> list[Alert]:
        return [a for a in self.alerts
                if not a.resolved and not a.collapsed
                and (a.expires_s is None or t < a.expires_s)]

    def toasts(self, t: float) -> list[Alert]:
        """Top-right stack, newest on top, max 3 (A-3)."""
        live = sorted(self.active(t), key=lambda a: (-a.t_last, -a.aid))
        return live[:TOAST_BUDGET]

    def overflow(self, t: float) -> int:
        """Alerts beyond the toast budget → Alert Center badge (A-3)."""
        return max(0, len(self.active(t)) - TOAST_BUDGET)

    # -- the warp law (A-2) ------------------------------------------------------
    def highest_warp_cap(self, t: float) -> float:
        cap = math.inf
        for a in self.active(t):
            if not a.released():
                cap = min(cap, a.warp_cap)
        return cap

    def warp_max_effective(self, warp_player: float, t: float) -> float:
        return min(warp_player, self.highest_warp_cap(t))

    def should_pause(self, t: float) -> bool:
        return any(a.pause and not a.released() for a in self.active(t))

    # -- acknowledgement ---------------------------------------------------------
    def acknowledge(self, aid: int, t: float | None = None) -> bool:
        """Click / `Enter` on the focused toast. Returns True if the
        warp cap was released (always False for live Class 1)."""
        a = self.get(aid)
        if a is None:
            return False
        a.acked = a.audio_acked = True
        return a.released()

    def master_alarm(self, t: float) -> int:
        """A-6: silence ALL Class 2–3 audio at once; every warp cap
        stays until individually acknowledged. Returns alerts hushed."""
        n = 0
        for a in self.active(t):
            if a.cls in (2, 3) and not a.audio_acked:
                a.audio_acked = True
                n += 1
        return n

    def accept_risk(self, aid: int, t: float,
                    justification: str = "") -> bool:
        """The covered switch for Class 1 — logged to the Chronicle
        forever (A-2), optional one-line justification."""
        a = self.get(aid)
        if a is None or a.cls != 1:
            return False
        a.accepted_risk = True
        a.acked = a.audio_acked = True
        if self.chronicle is not None:
            text = (f"Class-1 risk accepted at {a.source_id}: {a.text}")
            if justification:
                text += f" — “{justification}”"
            self.chronicle.add(t, "RISK_ACCEPTED", text,
                               subjects=(a.source_id,), location=a.site,
                               cls=1)
        return True

    def resolve(self, aid: int) -> bool:
        a = self.get(aid)
        if a is None:
            return False
        a.resolved = True
        return True

    # -- persistence (additive save section) ---------------------------------------
    def to_dict(self) -> dict:
        return {"next_aid": self._next_aid,
                "overrides": {k: dict(v) for k, v in self.overrides.items()},
                "alerts": [a.to_dict() for a in self.alerts]}

    @classmethod
    def from_dict(cls, d: dict,
                  chronicle: "Chronicle | None" = None) -> "AlertBus":
        bus = cls(chronicle)
        bus._next_aid = d.get("next_aid", 1)
        bus.overrides = {k: dict(v)
                         for k, v in d.get("overrides", {}).items()}
        bus.alerts = [Alert.from_dict(ad) for ad in d.get("alerts", [])]
        return bus


# ---- contract glue (E-9; wraps the existing Program contract shape) ----------

def _cfield(c, key: str, default=None):
    """Contracts arrive as sim.economy.Contract objects OR as the save
    dicts {contract_id, description, payout, deadline_s, ...}."""
    if isinstance(c, dict):
        return c.get(key, default)
    return getattr(c, key, default)


def deadline_sweep(bus: AlertBus, contracts, t: float) -> list[Alert]:
    """E-9: deadline alerts at T−90 (Advisory) / T−30 (Caution) /
    T−7 d (Warning). Each threshold fires once per contract; cards
    expire at the deadline itself."""
    posted = []
    for c in contracts:
        if (_cfield(c, "completed_t") is not None
                or _cfield(c, "failed", False)):
            continue
        cid = _cfield(c, "contract_id")
        desc = _cfield(c, "description", cid)
        deadline = float(_cfield(c, "deadline_s"))
        if t > deadline:
            continue
        for days, cls in DEADLINE_ALERT_DAYS:
            if deadline - t <= days * DAY:
                kind = f"deadline_T-{int(days)}d"
                if bus.find(cid, kind) is None:
                    posted.append(bus.post(
                        t, cls, cid,
                        f"Contract deadline T−{int(days)} d: {desc}",
                        kind=kind, expires_s=deadline))
    return posted


def runway_sweep(bus: AlertBus, t: float, runway_d: float) -> list[Alert]:
    """G-9 death spiral: runway < 60 d → Class 3; < 14 d → Class 2."""
    posted = []
    for days, cls in RUNWAY_ALERT_DAYS:
        if runway_d < days:
            posted.append(bus.post(
                t, cls, "program:ledger",
                f"Runway {runway_d:.0f} d (below {days:.0f} d)",
                kind=f"runway_{int(days)}d"))
    return posted


# ---- THE CHRONICLE (12 §4) ----------------------------------------------------

# §4.2 complete list: FIRST_* counts as one type (the Firsts ladder),
# plus the C19 demographic addition (BIRTH).
ENTRY_KINDS: tuple[str, ...] = (
    "FIRST_*", "LAUNCH", "LANDING", "DOCKING", "SOI_ARRIVAL",
    "CONTRACT_WON", "CONTRACT_DONE", "CONTRACT_FAILED", "ROUND_RAISED",
    "DEATH", "RESCUE", "DISASTER", "RISK_ACCEPTED", "STANDDOWN",
    "ANOMALY", "WONDER", "HERITAGE_VIOLATION", "BANKRUPTCY_NEAR",
    "AUDIT_PASS", "AUDIT_FAIL", "ACT_CHAPTER", "SETTINGS_CHANGED",
    "PHOTO", "RIVAL_NEWS", "EPILOGUE",
    "BIRTH",                                   # DECISIONS C19
)
_CHAPTER_KINDS = ("ACT_CHAPTER", "AUDIT_PASS", "AUDIT_FAIL", "EPILOGUE")

CHRONICLE_TARGET_VOLUME = (200, 800)   # entries per campaign (C-1)
ENTRY_CAP = 2_000                      # §8.12 memory cap
SNAPSHOT_CAP_BYTES = 65_536            # §8.12: snapshots ≤ 64 kB each

_EPOCH = datetime(2049, 1, 1)          # G-7: t = 0 at 2049-01-01 00:00 UTC


def sim_date(t: float) -> str:
    """Sim seconds since epoch → 'YYYY-MM-DD' (UTC, deterministic)."""
    return (_EPOCH + timedelta(seconds=t)).strftime("%Y-%m-%d")


@dataclass
class Entry:
    """C-1 record: (t_sim, type, class, subjects[], location, numbers{},
    autoshot_id, seed). `refs` aliases subjects for callers that think
    in jump-links."""
    seq: int
    t: float
    kind: str
    text: str
    cls: int = 4
    subjects: tuple = ()
    location: str = ""
    numbers: dict = field(default_factory=dict)
    autoshot_id: str | None = None
    seed: int = 0
    degraded: bool = False         # §8.12: snapshot dropped, text kept

    @property
    def refs(self) -> tuple:
        return self.subjects

    def to_dict(self) -> dict:
        return {"seq": self.seq, "t": self.t, "kind": self.kind,
                "text": self.text, "cls": self.cls,
                "subjects": list(self.subjects),
                "location": self.location, "numbers": dict(self.numbers),
                "autoshot_id": self.autoshot_id, "seed": self.seed,
                "degraded": self.degraded}

    @classmethod
    def from_dict(cls, d: dict) -> "Entry":
        d = dict(d)
        d["subjects"] = tuple(d.get("subjects", ()))
        return cls(**d)


def _valid_kind(kind: str) -> bool:
    return kind.startswith("FIRST_") or (kind in ENTRY_KINDS
                                         and kind != "FIRST_*")


class Chronicle:
    """Append-only campaign history (C-1…C-4). Entries are never
    deleted; past the §8.12 cap the oldest non-FIRST/DEATH entries
    degrade to text-only (snapshot dropped, prose kept)."""

    def __init__(self):
        self.entries: list[Entry] = []
        self._next_seq = 1

    def add(self, t: float, kind: str, text: str, *, subjects=(),
            location: str = "", numbers: dict | None = None,
            autoshot_id: str | None = None, seed: int = 0,
            cls: int = 4) -> Entry:
        if not _valid_kind(kind):
            raise ValueError(f"unknown Chronicle entry kind: {kind!r}")
        e = Entry(self._next_seq, t, kind, text, cls=cls,
                  subjects=tuple(subjects), location=location,
                  numbers=dict(numbers or {}), autoshot_id=autoshot_id,
                  seed=seed)
        self._next_seq += 1
        self.entries.append(e)
        self._enforce_cap()
        return e

    def _enforce_cap(self) -> None:
        over = len(self.entries) - ENTRY_CAP
        if over <= 0:
            return
        degraded = sum(1 for e in self.entries if e.degraded)
        for e in self.entries:                       # oldest first
            if degraded >= over:
                break
            if e.degraded or e.kind == "DEATH" or e.kind.startswith("FIRST_"):
                continue
            e.degraded = True
            e.autoshot_id = None
            degraded += 1

    # -- queries -------------------------------------------------------------
    def by_kind(self, kind: str) -> list[Entry]:
        return [e for e in self.entries if e.kind == kind]

    def in_range(self, t0: float, t1: float) -> list[Entry]:
        return [e for e in self.entries if t0 <= e.t <= t1]

    def query(self, kind: str | None = None, t0: float = -math.inf,
              t1: float = math.inf) -> list[Entry]:
        return [e for e in self.entries
                if (kind is None or e.kind == kind) and t0 <= e.t <= t1]

    # -- C-3 chapter cards -----------------------------------------------------
    def chapter(self, t: float, text: str, *,
                kind: str = "ACT_CHAPTER",
                stats: dict | None = None) -> Entry:
        """Act transitions and audits generate chapter cards with
        auto-computed stats; stats default to everything so far."""
        if kind not in _CHAPTER_KINDS:
            raise ValueError(f"not a chapter kind: {kind!r}")
        return self.add(t, kind, text,
                        numbers=stats if stats is not None
                        else chapter_stats(self.entries))

    # -- persistence (additive save section) --------------------------------------
    def to_dict(self) -> dict:
        return {"next_seq": self._next_seq,
                "entries": [e.to_dict() for e in self.entries]}

    @classmethod
    def from_dict(cls, d: dict) -> "Chronicle":
        ch = cls()
        ch._next_seq = d.get("next_seq", 1)
        ch.entries = [Entry.from_dict(ed) for ed in d.get("entries", [])]
        return ch


def chapter_stats(entries: list[Entry]) -> dict:
    """C-3: launches, tonnage to orbit, fatalities, $ flow, firsts —
    auto-computed from the record (per-entry numbers feed the sums)."""
    return {
        "launches": sum(1 for e in entries if e.kind == "LAUNCH"),
        "fatalities": sum(1 for e in entries if e.kind == "DEATH"),
        "firsts": sum(1 for e in entries if e.kind.startswith("FIRST_")),
        "tonnage_to_orbit_t": sum(e.numbers.get("tonnage_t", 0.0)
                                  for e in entries),
        "usd_flow": sum(e.numbers.get("usd", 0.0) for e in entries),
    }


def chronicle_contract(chron: Chronicle, t: float, contract,
                       outcome: str) -> Entry:
    """Contract landmarks (C-1 auto-write) from the existing Program
    contract shape (object or save dict)."""
    kind = {"won": "CONTRACT_WON", "done": "CONTRACT_DONE",
            "failed": "CONTRACT_FAILED"}[outcome]
    cid = _cfield(contract, "contract_id")
    desc = _cfield(contract, "description", cid)
    payout = float(_cfield(contract, "payout", 0.0))
    verb = {"won": "accepted", "done": "completed",
            "failed": "failed"}[outcome]
    usd = payout if outcome == "done" else 0.0
    return chron.add(t, kind, f"Contract {verb}: {desc}.",
                     subjects=(cid,),
                     numbers={"payout_usd": payout, "usd": usd})


def export_text(entries: list[Entry], title: str | None = None) -> str:
    """The mission-log document (C-2 tone, C-4 trophy): one dated line
    per entry, chapter cards set off with their stats. The HTML+PNG
    poster render (F-chunk) consumes this same ordering."""
    ordered = sorted(entries, key=lambda e: (e.t, e.seq))
    if title is None:
        last = sim_date(ordered[-1].t)[:4] if ordered else "20XX"
        title = f"The Program, 2049–{last}"
    lines = [title, "=" * len(title), ""]
    for e in ordered:
        stamp = sim_date(e.t)
        if e.kind in _CHAPTER_KINDS:
            lines += ["", f"==== {stamp} — {e.text} ===="]
            for k in sorted(e.numbers):
                v = e.numbers[k]
                lines.append(f"  {k}: {v:g}" if isinstance(v, (int, float))
                             else f"  {k}: {v}")
            lines.append("")
        else:
            lines.append(f"{stamp} — {e.text}")
    return "\n".join(lines)


# ---- BIRTHS & GENERATIONS (DECISIONS C19, 08 §4.9) -----------------------------

GESTATION_D = 270.0              # continuous-occupation gate, conception→birth
MIN_PARENT_CREW = 2              # at least two adults at the settlement
ADULT_AGE_YR = 18.0              # children are non-working until adulthood
CHILD_METABOLIC_SCALE = 0.5      # 08 §4.9: scaled metabolic baselines
CHILD_ENERGY_KCAL = CHILD_METABOLIC_SCALE * BODY_RESERVE_KCAL

# g_repro is drawn per save from a deterministic seed within defensible
# bounds (08 §4.9); LS-10 narrows the bracket, LS-11 reveals the value.
G_REPRO_BOUNDS = (0.30, 0.90)    # in g
LS10_HALF_WIDTH_G = 0.05

_GIVEN_NAMES = (
    "Aria", "Bowen", "Caleb", "Dara", "Esther", "Felix", "Grace",
    "Hale", "Ida", "Joon", "Kira", "Leo", "Mireille", "Nadia",
    "Oskar", "Priya", "Quinn", "Rosa", "Soren", "Tessa", "Umar",
    "Vera", "Wren", "Yusuf",
)
_SUFFIXES = ("", " II", " III", " IV", " V", " VI", " VII", " VIII",
             " IX", " X")


def _hash(s: str) -> int:
    return int.from_bytes(
        hashlib.blake2b(s.encode(), digest_size=8).digest(), "big")


def draw_g_repro(campaign_seed) -> float:
    """The save's true gravity threshold, uniform in G_REPRO_BOUNDS,
    quantized to 0.01 g. Deterministic per campaign seed."""
    lo, hi = G_REPRO_BOUNDS
    frac = (_hash(f"g_repro:{campaign_seed}") % 10_000) / 10_000.0
    return round(lo + frac * (hi - lo), 2)


def g_repro_bracket(campaign_seed, stage: int) -> tuple[float, float]:
    """What the program KNOWS: stage 0–1 (pre/LS-09 centrifuge) = full
    defensible bounds; stage 2 (LS-10 mammalian trials) = narrowed
    bracket; stage 3 (LS-11 human protocols) = exact threshold."""
    truth = draw_g_repro(campaign_seed)
    if stage >= 3:
        return (truth, truth)
    if stage == 2:
        lo, hi = G_REPRO_BOUNDS
        return (round(max(lo, truth - LS10_HALF_WIDTH_G), 2),
                round(min(hi, truth + LS10_HALF_WIDTH_G), 2))
    return G_REPRO_BOUNDS


def births_eligible(*, policy_on: bool, g_local_g: float,
                    g_repro_g: float | None, adults: int,
                    occupied_d: float) -> tuple[bool, str]:
    """C19 trigger gates, in order: settlement policy ON (the sim never
    forces outcomes), g_repro discovered (LS-11), local gravity meets
    it, ≥ 2 adult crew, continuous occupation ≥ one gestation."""
    if not policy_on:
        return False, "policy_off"
    if g_repro_g is None:
        return False, "g_repro_undiscovered"
    if g_local_g < g_repro_g:
        return False, "gravity_below_threshold"
    if adults < MIN_PARENT_CREW:
        return False, "needs_two_adults"
    if occupied_d < GESTATION_D:
        return False, "occupation_below_gestation"
    return True, "eligible"


def child_name(site_id: str, index: int, surname: str,
               taken=()) -> str:
    """Deterministic naming: given name from the pool keyed by
    (site, birth index), family name from a parent; numeral suffixes
    break collisions."""
    given = _GIVEN_NAMES[_hash(f"birth:{site_id}:{index}")
                         % len(_GIVEN_NAMES)]
    base = f"{given} {surname}"
    for suffix in _SUFFIXES:
        name = base + suffix
        if name not in taken:
            return name
    return f"{base} {index}"                 # pathological fallback


def new_crew_dict(name: str, t_birth: float,
                  role: str | None = None) -> dict:
    """The newborn's roster record in the EXACT save crew shape
    (aphelion/save/campaign.py): non-working (busy until adulthood),
    all skills 0, scaled metabolic baseline."""
    if role is None:
        role = ROLES[_hash(f"role:{name}") % len(ROLES)]
    return {
        "msv": 0.0,
        "role": role,
        "skill": 0,
        "acute": [],
        "busy": t_birth + ADULT_AGE_YR * YEAR,
        "skills": {r: 0 for r in ROLES},
        "morale": 70.0,
        "cond": 100.0,
        "energy": CHILD_ENERGY_KCAL,
        "traits": [],
        "conditions": [],
        "xp": {},
    }


def make_birth(site_id: str, t: float, parents, index: int, *,
               existing_names=(), parent_generations=()) -> dict:
    """One birth event: deterministic child name + generation + the
    save-shape crew dict. Generation = max(parent generations) + 1
    (Earth-born crew are generation 0)."""
    parents = sorted(parents)
    surname_src = parents[_hash(f"parent:{site_id}:{index}")
                          % len(parents)]
    surname = surname_src.split()[-1]
    name = child_name(site_id, index, surname, taken=existing_names)
    generation = max(parent_generations, default=0) + 1
    return {
        "name": name,
        "crew": new_crew_dict(name, t),
        "generation": generation,
        "site_id": site_id,
        "parents": tuple(parents),
        "t": t,
    }


def record_birth(chron: Chronicle, birth: dict) -> Entry:
    """The BIRTH Chronicle entry (C19 demographic ladder entry)."""
    return chron.add(
        birth["t"], "BIRTH",
        f"{birth['name']} born at {birth['site_id']}. Generation "
        f"{birth['generation']} of the program.",
        subjects=(birth["name"], *birth["parents"]),
        location=birth["site_id"],
        numbers={"generation": birth["generation"]})


def birth_count(chron: Chronicle) -> int:
    """E-28(g) demographic pillar input."""
    return len(chron.by_kind("BIRTH"))


def generations_reached(chron: Chronicle) -> int:
    return max((int(e.numbers.get("generation", 0))
                for e in chron.by_kind("BIRTH")), default=0)
