"""Radiation dose tracking (03 §3.7 S-8, 08 §3.6): per-location ambient
rates from the canon master table, exponential shielding attenuation with
the decaying GCR floor (DECISIONS A3), career-dose accounting.
"""

from __future__ import annotations

import math

# unshielded ambient surface/orbit rates, mSv/day (03 §4.1 master table).
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

# shielding halving thicknesses, g/cm2 (07 §3.6; water/regolith/poly classes)
HALVING_G_CM2 = {"water": 18.0, "regolith": 22.0, "polyethylene": 15.0}

# the decaying GCR floor (08 §3.6 + DECISIONS A3): attenuation cannot drop
# the dose below floor_fraction of ambient until areal mass exceeds
# FLOOR_BREAK, after which the floor itself decays with depth
GCR_FLOOR_FRACTION = 0.30
FLOOR_BREAK_G_CM2 = 1_000.0
FLOOR_DECAY_HALVING = 120.0      # g/cm2 per halving of the residual floor
                                 # [GAME MODEL placeholder: tuned so Titan's
                                 # 10,900 g/cm2 column reads Earth-quiet and
                                 # Europa burrows win at ~14 m of ice]

CAREER_LIMIT_MSV = 1_000.0       # NASA-class career bound (08)


def attenuation(areal_g_cm2: float, material: str = "regolith") -> float:
    """Dose fraction passing the shield, with the decaying GCR floor."""
    halving = HALVING_G_CM2[material]
    direct = 0.5 ** (areal_g_cm2 / halving)
    if areal_g_cm2 <= FLOOR_BREAK_G_CM2:
        floor = GCR_FLOOR_FRACTION
    else:
        floor = GCR_FLOOR_FRACTION * 0.5 ** (
            (areal_g_cm2 - FLOOR_BREAK_G_CM2) / FLOOR_DECAY_HALVING)
    return max(direct, floor)


def dose_rate_msv_day(location: str, areal_g_cm2: float = 0.0,
                      material: str = "regolith",
                      t: float | None = None) -> float:
    """Ambient rate behind shielding. With a sim time the GCR-driven
    locations ride the solar cycle (S-8a); t=None keeps the flat legacy
    rate (pinned tests, previews)."""
    base = AMBIENT_MSV_DAY.get(location, 1.8)
    if t is not None and location in _GCR_DRIVEN:
        from aphelion.sim.environment.space_env import f_cycle
        base = base * f_cycle(t)
    return base * attenuation(areal_g_cm2, material)


class CrewDose:
    """Career dose accounting for one crew member (08 §3.6)."""

    def __init__(self, accumulated_msv: float = 0.0) -> None:
        self.accumulated_msv = accumulated_msv

    def accrue(self, location: str, days: float,
               areal_g_cm2: float = 0.0, material: str = "regolith",
               t: float | None = None) -> float:
        d = dose_rate_msv_day(location, areal_g_cm2, material, t) * days
        self.accumulated_msv += d
        return d

    def accrue_event_msv(self, msv: float,
                         areal_g_cm2: float = 0.0,
                         material: str = "regolith") -> float:
        """Acute lump (SPE storms, belt passes) behind shielding."""
        d = msv * attenuation(areal_g_cm2, material)
        self.accumulated_msv += d
        return d

    @property
    def career_fraction(self) -> float:
        return self.accumulated_msv / CAREER_LIMIT_MSV

    @property
    def over_limit(self) -> bool:
        return self.accumulated_msv > CAREER_LIMIT_MSV
