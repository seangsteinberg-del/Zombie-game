"""Atmospheric entry, aerobraking, aerocapture (01 §3.11, binding).

Drag from the piecewise-exponential atmospheres; Sutton-Graves stagnation
heating with the [GAME MODEL] radiative augmentation; Allen-Eggers closed
form as the planner's sanity model. Lift ships with the spaceplane content
(Phase 5 UI); v1 entries are ballistic.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from aphelion.sim.environment.atmosphere import density, interface_altitude
from aphelion.sim.orbits.kepler import state_to_elements

SUTTON_GRAVES_K = {          # 01 §3.11 (sqrt(kg/m)/m)
    "air": 1.7415e-4,        # Earth, N2 bodies incl. Titan
    "co2": 1.90e-4,          # Mars, Venus
    "h2he": 1.7415e-4 * 2.0,  # gas giants [GAME MODEL]
}
GAS_BY_BODY = {
    "core:earth": "air", "core:titan": "air",
    "core:mars": "co2", "core:venus": "co2",
    "core:jupiter": "h2he", "core:saturn": "h2he",
}


def radiative_factor(v: float) -> float:
    """f_rad (01 §3.11): 1 below 9 km/s; quadratic stand-in above, capped 8."""
    if v <= 9_000.0:
        return 1.0
    return min(1.0 + ((v - 9_000.0) / 3_000.0) ** 2, 8.0)


def stagnation_heating_w_m2(body_id: str, rho: float, v: float,
                            nose_radius_m: float) -> float:
    k = SUTTON_GRAVES_K[GAS_BY_BODY[body_id]]
    return k * math.sqrt(rho / nose_radius_m) * v ** 3 * radiative_factor(v)


def allen_eggers_peak_g(v_entry: float, gamma_entry_rad: float,
                        scale_height_m: float) -> float:
    """a_max = v_E^2 sin(gamma) / (2 e H), in g (01 §3.11 sanity model)."""
    a = v_entry ** 2 * math.sin(gamma_entry_rad) / (2.0 * math.e * scale_height_m)
    return a / 9.80665


@dataclass(slots=True)
class EntryResult:
    outcome: str                  # "landed" | "captured" | "escaped"
    peak_heating_w_m2: float
    peak_g: float
    exit_apoapsis_m: float        # for captured/escaped outcomes
    v_final: float
    t_atmo_s: float
    log: list[str] = field(default_factory=list)


def fly_entry(body_id: str, mu: float, radius: float,
              r0: float, v0: float, gamma0_rad: float,
              beta_kg_m2: float, nose_radius_m: float = 2.0,
              dt: float = 0.05) -> EntryResult:
    """Integrate a ballistic entry/aeropass from (r0, v0, flight-path angle).

    beta = m/(Cd A), the ballistic coefficient. Starts above the interface;
    ends landed (low altitude+speed), or back above the interface with the
    exit orbit fitted (aerocapture/aerobrake verdict).
    """
    h_int = interface_altitude(body_id)
    # state: planar, start at angle 0
    x, y = r0, 0.0
    vx = v0 * math.sin(gamma0_rad)        # radial component (negative = down)
    vy = v0 * math.cos(gamma0_rad)        # transverse
    if gamma0_rad > 0.0:
        vx = -abs(vx)                      # entries descend
    t = 0.0
    peak_q = peak_g = 0.0
    in_atmo = False
    t_atmo = 0.0

    while t < 3_600.0:
        r = math.hypot(x, y)
        h = r - radius
        v = math.hypot(vx, vy)
        rho = density(body_id, h)
        if rho > 0.0:
            in_atmo = True
            t_atmo += dt
            q_heat = stagnation_heating_w_m2(body_id, rho, v, nose_radius_m)
            decel = 0.5 * rho * v * v / beta_kg_m2
            peak_q = max(peak_q, q_heat)
            peak_g = max(peak_g, decel / 9.80665)
            if v > 0.0:
                vx -= decel * vx / v * dt
                vy -= decel * vy / v * dt
        elif in_atmo and h > h_int:
            # exited the atmosphere: fit the orbit and report
            el = state_to_elements(x, y, vx, vy, t, mu)
            apo = el.apoapsis if el.alpha > 0.0 else math.inf
            outcome = "captured" if el.alpha > 0.0 else "escaped"
            return EntryResult(outcome, peak_q, peak_g, apo, v, t_atmo)

        g = mu / (r * r)
        vx -= g * x / r * dt
        vy -= g * y / r * dt
        x += vx * dt
        y += vy * dt
        t += dt

        if h < 5_000.0 and v < 300.0:
            return EntryResult("landed", peak_q, peak_g, 0.0, v, t_atmo,
                               ["terminal descent reached (chutes per 06/10)"])
        if h <= 0.0:
            return EntryResult("landed", peak_q, peak_g, 0.0, v, t_atmo,
                               ["surface impact regime"])

    return EntryResult("escaped", peak_q, peak_g, math.inf, math.hypot(vx, vy),
                       t_atmo, ["integration horizon"])
