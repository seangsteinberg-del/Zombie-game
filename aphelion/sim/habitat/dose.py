"""Radiation dose v2 (08 §4.2, 03 S-8, DECISIONS A3): per-location ambient
rates from the canon master table, the two-channel shielding law
(f_GCR / f_SPE), and TWO accumulators per crew that must never be equated —
career effective dose (mSv, stochastic cancer) and acute absorbed dose
(mGy, rolling 24 h, deterministic ARS).
"""

from __future__ import annotations

import math
from collections import deque

# unshielded ambient surface/orbit rates, mSv/day EFFECTIVE (03 §4.1).
# Entries marked in _GCR_DRIVEN take the solar-cycle f_cycle(t) modulation
# when a time is supplied (space_env owns the cycle).
AMBIENT_MSV_DAY = {
    "core:earth": 0.01,
    "core:moon": 1.37,
    "core:mars": 0.67,
    "deep_space": 1.8,
    "core:mercury": 1.8,                   # GCR + 6.7x SPE separately
    "core:venus": 0.03,                    # 52 km cloud deck
    "core:phobos": 0.7,                    # Mars shadow share
    "core:deimos": 0.9,
    "core:ceres": 1.8, "core:vesta": 1.8, "core:psyche": 1.8,
    "core:hygiea": 1.8, "core:bennu": 1.8, "core:ryugu": 1.8,
    "core:itokawa": 1.8, "core:eros": 1.8, "core:apophis": 1.8,
    "core:67p": 1.8, "core:halley": 1.8,
    "core:io": 36_000.0,                   # 36 Gy/day [SIMPLIFIED as Sv]
    "core:europa": 5_400.0,
    "core:ganymede": 80.0,                 # own B-field halves the 160
    "core:callisto": 0.14 + 1.8,           # own + full GCR share
    "core:titan": 0.01,                    # 10,900 g/cm2 column
    "core:enceladus": 1.0,
    "core:miranda": 0.5, "core:titania": 0.5, "core:oberon": 0.5,
    "core:triton": 1.8, "core:pluto": 1.8, "core:charon": 1.8,
    "core:eris": 1.8, "core:arrokoth": 1.8,
}

# locations whose ambient is pure (or mostly) galactic cosmic rays — these
# scale with the solar cycle when a time is given
_GCR_DRIVEN = {"deep_space", "core:mercury", "core:moon", "core:mars",
               "core:ceres", "core:vesta", "core:psyche", "core:hygiea",
               "core:bennu", "core:ryugu", "core:itokawa", "core:eros",
               "core:apophis", "core:67p", "core:halley", "core:triton",
               "core:pluto", "core:charon", "core:eris", "core:arrokoth",
               "core:phobos", "core:deimos", "core:enceladus",
               "core:miranda", "core:titania", "core:oberon"}

# trapped charged-particle fields (Jovian belts): these attenuate like SPE
# protons/electrons (f_SPE), NOT like GCR — metres of ice beat them; the
# GCR share underneath survives on its own law
_PARTICLE_FIELD = {"core:io", "core:europa", "core:ganymede"}

# quality factors Q (08 §4.2): effective mSv = absorbed mGy × Q.
# GCR heavy-ion mix Q≈3; SPE protons / trapped fields Q≈1.
Q_GCR = 3.0
Q_SPE = 1.0

GCR_FLOOR = 0.30                 # secondary-shower floor
FLOOR_BREAK_G_CM2 = 1_000.0      # ≈6 m regolith / 11 m ice
FLOOR_EFOLD_G_CM2 = 1_000.0      # DECISIONS A3: e-fold of the deep floor

CAREER_LIMIT_MSV = 600.0         # NASA-STD-3001 anchor (08 §4.2)
CAREER_CAUTION_MSV = 400.0       # "radiation caution" flag
REID_PER_100_MSV = 0.005         # +0.5% lifetime fatal-cancer per 100 mSv

ACUTE_WINDOW_DAYS = 1.0          # D_acute rolls over 24 h

# ARS bands from D_acute (mGy absorbed, rolling 24 h, AFTER shielding):
# (threshold mGy, name, productivity penalty, untreated daily death prob,
#  recovery days). Penalties feed P_health (crew.py) as rad_penalty.
ARS_BANDS = (
    (6_000.0, "lethal",    1.00, 0.50, 9_999.0),
    (4_000.0, "ld50",      1.00, 0.12, 60.0),
    (2_000.0, "severe",    1.00, 0.04, 45.0),
    (1_000.0, "mild",      0.60, 0.0,  12.0),
    (250.0,   "prodromal", 0.30, 0.0,  2.0),
)


def f_gcr(areal_g_cm2: float) -> float:
    """GCR transmitted fraction: 0.30 floor + 0.70·exp(−σ/30); past
    1,000 g/cm² the floor itself decays, e-fold 1,000 (DECISIONS A3)."""
    s = max(0.0, areal_g_cm2)
    if s <= FLOOR_BREAK_G_CM2:
        floor = GCR_FLOOR
    else:
        floor = GCR_FLOOR * math.exp(-(s - FLOOR_BREAK_G_CM2)
                                     / FLOOR_EFOLD_G_CM2)
    return floor + 0.70 * math.exp(-s / 30.0)


def f_spe(areal_g_cm2: float) -> float:
    """SPE-proton / trapped-particle transmitted fraction: exp(−σ/12) —
    ~20 g/cm² cuts a storm ~80%; a metre of ice ends it."""
    return math.exp(-max(0.0, areal_g_cm2) / 12.0)


def attenuation(areal_g_cm2: float, material: str = "regolith",
                channel: str = "gcr") -> float:
    """Transmitted dose fraction. Mass is mass — `material` is accepted
    for caller compatibility but the laws key on areal density alone."""
    return f_spe(areal_g_cm2) if channel == "spe" else f_gcr(areal_g_cm2)


def _channel(location: str) -> str:
    return "spe" if location in _PARTICLE_FIELD else "gcr"


def quality_factor(location: str) -> float:
    """Q of the dominant component at this location."""
    return Q_SPE if location in _PARTICLE_FIELD else Q_GCR


def dose_rate_msv_day(location: str, areal_g_cm2: float = 0.0,
                      material: str = "regolith",
                      t: float | None = None) -> float:
    """Effective ambient rate behind shielding. With a sim time the
    GCR-driven locations ride the solar cycle (S-8a); t=None keeps the
    flat legacy rate (pinned tests, previews)."""
    base = AMBIENT_MSV_DAY.get(location, 1.8)
    if t is not None and location in _GCR_DRIVEN:
        from aphelion.sim.environment.space_env import f_cycle
        base = base * f_cycle(t)
    return base * attenuation(areal_g_cm2, material, _channel(location))


def ars_band(acute_mgy: float):
    """(name, productivity_penalty, untreated_daily_death_p, recovery_days)
    for the rolling-24 h absorbed dose; None below 250 mGy."""
    for thresh, name, pen, death_p, rec in ARS_BANDS:
        if acute_mgy >= thresh:
            return name, pen, death_p, rec
    return None


def reid_fraction(career_msv: float) -> float:
    """Lifetime fatal-cancer probability added by this career (REID),
    rolled at career end / Earth return (08 §4.2)."""
    return max(0.0, career_msv) / 100.0 * REID_PER_100_MSV


class CrewDose:
    """Both dose ledgers for one crew member (08 §4.2): career effective
    mSv (forever) and acute absorbed mGy over a rolling 24-h window."""

    def __init__(self, accumulated_msv: float = 0.0,
                 acute_log: list | None = None) -> None:
        self.accumulated_msv = accumulated_msv
        # (t_days, mGy) lumps inside the rolling window
        self.acute_log: deque = deque(
            (float(td), float(mg)) for td, mg in (acute_log or []))

    # -- accrual --------------------------------------------------------------
    def accrue(self, location: str, days: float,
               areal_g_cm2: float = 0.0, material: str = "regolith",
               t: float | None = None) -> float:
        """Chronic ambient exposure for `days` at a location. Returns the
        effective mSv added. Also feeds the acute ledger at absorbed
        rate = effective/Q (GCR rarely matters there; Jovian fields do)."""
        msv = dose_rate_msv_day(location, areal_g_cm2, material, t) * days
        self.accumulated_msv += msv
        t_day = (t or 0.0) / 86_400.0
        self._log_acute(t_day, msv / quality_factor(location))
        return msv

    def accrue_event_msv(self, msv: float,
                         areal_g_cm2: float = 0.0,
                         material: str = "regolith",
                         t: float | None = None) -> float:
        """Acute lump (SPE storms, belt passes) behind shielding —
        proton events: Q≈1, so mGy ≈ mSv."""
        d = msv * f_spe(areal_g_cm2)
        self.accumulated_msv += d
        self._log_acute((t or 0.0) / 86_400.0, d / Q_SPE)
        return d

    def _log_acute(self, t_day: float, mgy: float) -> None:
        if mgy > 0.0:
            self.acute_log.append((t_day, mgy))
        while self.acute_log and \
                self.acute_log[0][0] < t_day - ACUTE_WINDOW_DAYS:
            self.acute_log.popleft()

    # -- readouts -------------------------------------------------------------
    def acute_mgy(self, t: float | None = None) -> float:
        """Absorbed dose inside the rolling 24-h window ending at t."""
        if t is not None:
            self._log_acute(t / 86_400.0, 0.0)
        return sum(mg for _, mg in self.acute_log)

    def ars(self, t: float | None = None):
        return ars_band(self.acute_mgy(t))

    @property
    def career_fraction(self) -> float:
        return self.accumulated_msv / CAREER_LIMIT_MSV

    @property
    def caution(self) -> bool:
        return self.accumulated_msv >= CAREER_CAUTION_MSV

    @property
    def over_limit(self) -> bool:
        return self.accumulated_msv > CAREER_LIMIT_MSV

    def reid(self) -> float:
        return reid_fraction(self.accumulated_msv)
