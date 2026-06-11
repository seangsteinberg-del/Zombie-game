"""Radiation dose tracking (03 §3.7 S-8, 08 §3.6): per-location ambient
rates from the canon master table, exponential shielding attenuation with
the decaying GCR floor (DECISIONS A3), career-dose accounting.
"""

from __future__ import annotations

import math

# unshielded ambient surface/orbit rates, mSv/day (03 §4.1 master table)
AMBIENT_MSV_DAY = {
    "core:earth": 0.01,
    "core:moon": 1.37,
    "core:mars": 0.67,
    "deep_space": 1.8,
    "core:europa": 5_400.0,
    "core:ganymede": 80.0,
    "core:callisto": 0.14 + 1.8 * 0.5,    # own + GCR share (03)
    "core:titan": 0.01,                    # 10,900 g/cm2 column: ~Earth-like
}

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
                      material: str = "regolith") -> float:
    return AMBIENT_MSV_DAY[location] * attenuation(areal_g_cm2, material)


class CrewDose:
    """Career dose accounting for one crew member (08 §3.6)."""

    def __init__(self, accumulated_msv: float = 0.0) -> None:
        self.accumulated_msv = accumulated_msv

    def accrue(self, location: str, days: float,
               areal_g_cm2: float = 0.0, material: str = "regolith") -> float:
        d = dose_rate_msv_day(location, areal_g_cm2, material) * days
        self.accumulated_msv += d
        return d

    @property
    def career_fraction(self) -> float:
        return self.accumulated_msv / CAREER_LIMIT_MSV

    @property
    def over_limit(self) -> bool:
        return self.accumulated_msv > CAREER_LIMIT_MSV
