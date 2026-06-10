"""Vis-viva transfer utilities (01 §3.8/§3.9): Hohmann, flyby, synodic.

These feed the Planner UI and the canonical delta-v map; every formula is
pinned by tests against 13 §4.7.
"""

from __future__ import annotations

import math


def circular_speed(mu: float, r: float) -> float:
    return math.sqrt(mu / r)


def escape_velocity(mu: float, r: float) -> float:
    return math.sqrt(2.0 * mu / r)


def visviva_speed(mu: float, r: float, a: float) -> float:
    return math.sqrt(mu * (2.0 / r - 1.0 / a))


def orbital_period(mu: float, a: float) -> float:
    return 2.0 * math.pi * math.sqrt(a ** 3 / mu)


def sma_from_period(mu: float, period: float) -> float:
    return (mu * (period / (2.0 * math.pi)) ** 2) ** (1.0 / 3.0)


def hohmann(mu: float, r1: float, r2: float) -> tuple[float, float, float]:
    """Coplanar circular-to-circular Hohmann. Returns (dv1, dv2, transfer_time).

    dv values are signed-positive magnitudes; works for r2 < r1 as well.
    """
    a_t = 0.5 * (r1 + r2)
    dv1 = abs(visviva_speed(mu, r1, a_t) - circular_speed(mu, r1))
    dv2 = abs(circular_speed(mu, r2) - visviva_speed(mu, r2, a_t))
    t = math.pi * math.sqrt(a_t ** 3 / mu)
    return (dv1, dv2, t)


def hohmann_departure_vinf(mu_primary: float, r1: float, r2: float) -> float:
    """Hyperbolic excess speed for the interplanetary Hohmann leg from r1."""
    a_t = 0.5 * (r1 + r2)
    return abs(visviva_speed(mu_primary, r1, a_t) - circular_speed(mu_primary, r1))


def departure_dv(mu_body: float, r_park: float, vinf: float) -> float:
    """Injection dv from a circular parking orbit onto an escape hyperbola
    with the given v-infinity (Oberth at periapsis)."""
    v_peri = math.sqrt(vinf * vinf + 2.0 * mu_body / r_park)
    return v_peri - circular_speed(mu_body, r_park)


def synodic_period(t1: float, t2: float) -> float:
    return 1.0 / abs(1.0 / t1 - 1.0 / t2)


def flyby_deflection(mu: float, vinf: float, r_p: float) -> float:
    """Patched-conic flyby turning angle delta, rad (01 §3.9):
    e = 1 + r_p*vinf^2/mu; delta = 2*asin(1/e)."""
    e = 1.0 + r_p * vinf * vinf / mu
    return 2.0 * math.asin(1.0 / e)
