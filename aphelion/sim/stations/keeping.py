"""Station economics (06 §3.4 + §2.9): the station-keeping fee law
(01 Table 4.8 canonical), the MMOD penetration roll with Whipple
coverage, and the cryo boiloff clock that makes depots an economy.
"""

from __future__ import annotations

import math

# canonical fee anchors, m/s per year
_LOG_PTS = ((300.0, 25.0), (400.0, 20.0), (500.0, 2.0))


def stationkeeping_ms_yr(body_id: str, alt_km: float | None = None,
                         lpoint: str | None = None) -> float:
    """RCS dv auto-deducted per year. LEO 200–300 km: 25; 300–500
    piecewise log-linear through (300:25)·(400:20)·(500:2); above: 2;
    SE-L1/L2: 4; L4/L5: 0; low lunar / asteroid orbits: 5."""
    if lpoint in ("L1", "L2"):
        return 4.0
    if lpoint in ("L4", "L5"):
        return 0.0
    if body_id == "core:earth" and alt_km is not None:
        if alt_km <= 300.0:
            return 25.0
        if alt_km >= 500.0:
            return 2.0
        pts = _LOG_PTS
        for (a0, f0), (a1, f1) in zip(pts, pts[1:]):
            if a0 <= alt_km <= a1:
                u = (alt_km - a0) / (a1 - a0)
                return math.exp(math.log(f0) * (1 - u)
                                + math.log(f1) * u)
    if body_id == "core:earth":
        return 2.0
    return 5.0                       # low lunar / asteroid class


# ---- MMOD (06 §2.9) -----------------------------------------------------------
def mmod_p_pen(flux_per_m2_yr: float, exposed_m2: float,
               days: float, eta: float = 0.0) -> float:
    """P_pen = 1 − exp(−Φ·A·t·(1−η)), t in years."""
    t_yr = days / 365.25
    return 1.0 - math.exp(-flux_per_m2_yr * exposed_m2 * t_yr
                          * (1.0 - eta))


def whipple_coverage(hull_m2: float,
                     panels: list[dict]) -> tuple[float, float]:
    """(exposed m², effective η over the covered share folded in as a
    reduced exposed area). Each panel covers covers_m2 at its η."""
    covered = 0.0
    leak_through = 0.0
    for p in panels:
        c = float(p.get("covers_m2", 10.0))
        covered += c
        leak_through += c * (1.0 - float(p.get("whipple_eta", 0.9)))
    covered = min(covered, hull_m2)
    bare = max(0.0, hull_m2 - covered)
    return bare + leak_through, covered / hull_m2 if hull_m2 else 0.0


# ---- cryo boiloff (06 §2.7 / 02; GAME MODEL rates) ------------------------------
BOILOFF_FRAC_DAY = {"Hydrogen": 0.005, "Oxygen": 0.0005,
                    "Methane": 0.0005}


def boiloff_kg(resource: str, mass_kg: float, days: float,
               zbo_powered: bool) -> float:
    """Unpowered cryo vents (visible on the resource timeline); a
    powered ZBO cryocooler holds it at zero (06 §2.7)."""
    if zbo_powered:
        return 0.0
    frac = BOILOFF_FRAC_DAY.get(resource, 0.0)
    return mass_kg * (1.0 - (1.0 - frac) ** days)
