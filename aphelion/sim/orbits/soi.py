"""Spheres of influence: Laplace radius, floor rule, hysteresis, and the
on-rails crossing predictor (01 §3.4, 13 §3.8).

Crossings are found before they happen: coarse sampling per the binding step
rules, then Brent refinement of |r_craft(t) - r_body(t)| - r_SOI to ±1 s.
Predicted crossings feed the global event queue, which the warp loop treats
as exact clamps — that is the entire anti-tunneling story.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from aphelion.core.math2d import brent
from aphelion.sim.orbits.kepler import Elements, elements_to_state

# 01 §3.4 (binding)
SOI_FLOOR_FACTOR = 1.5        # r_SOI < 1.5 R_body -> no SOI ("rendezvous object")
HYSTERESIS_EXIT = 1.01        # exit requires r > 1.01 r_SOI
HYSTERESIS_ENTRY = 0.99       # entry requires r < 0.99 r_SOI
REFINE_TOL_S = 1.0            # Brent refinement tolerance, s
_SAMPLES = 64                 # coarse sampling divisor (binding: span/64)


def soi_radius(a_orbit: float, m_body: float, m_parent: float) -> float:
    """Laplace SOI: r_SOI = a (m/M)^(2/5)."""
    return a_orbit * (m_body / m_parent) ** 0.4


def effective_soi(a_orbit: float, m_body: float, m_parent: float,
                  r_body: float) -> float:
    """SOI radius after the floor rule: 0.0 means the body exerts no gravity
    and is a rendezvous object (Phobos, Deimos)."""
    r = soi_radius(a_orbit, m_body, m_parent)
    return r if r >= SOI_FLOOR_FACTOR * r_body else 0.0


def time_to_radius(el: Elements, r_target: float, t_from: float) -> float | None:
    """Earliest t > t_from at which the conic's radius equals r_target;
    None if the conic never reaches it. Used for the unbound-craft sampling
    span (01 §3.4) and warp guards."""
    p = el.p
    if el.e < 1e-12:
        return None   # circular: radius is constant
    cos_nu = (p / r_target - 1.0) / el.e
    if cos_nu > 1.0 or cos_nu < -1.0:
        return None
    nu_t = math.acos(cos_nu)

    def time_at_nu(nu: float) -> float:
        """Absolute time of true anomaly nu (nearest passage; elliptic shifted
        into the future below)."""
        if el.alpha > 0.0:
            ecc_e = 2.0 * math.atan2(math.sqrt(max(1.0 - el.e, 0.0)) * math.sin(0.5 * nu),
                                     math.sqrt(1.0 + el.e) * math.cos(0.5 * nu))
            m_anom = ecc_e - el.e * math.sin(ecc_e)
            n = math.sqrt(el.mu * el.alpha ** 3)
            return el.tau + m_anom / n
        arg = math.sqrt((el.e - 1.0) / (el.e + 1.0)) * math.tan(0.5 * nu)
        if abs(arg) >= 1.0:
            return math.inf
        h_anom = 2.0 * math.atanh(arg)
        m_anom = el.e * math.sinh(h_anom) - h_anom
        n = math.sqrt(el.mu * (-el.alpha) ** 3)
        return el.tau + m_anom / n

    candidates = []
    for nu in (nu_t, -nu_t):
        t_c = time_at_nu(nu)
        if not math.isfinite(t_c):
            continue
        if el.alpha > 0.0:
            period = el.period
            # shift into the first occurrence strictly after t_from
            k = math.ceil((t_from - t_c) / period)
            t_c += max(k, 0) * period
            if t_c <= t_from:
                t_c += period
        if t_c > t_from:
            candidates.append(t_c)
    return min(candidates) if candidates else None


@dataclass(frozen=True, slots=True)
class SoiCrossing:
    t_cross: float
    body_id: str
    entering: bool        # True: into the body's SOI; False: out of current frame


def _sampling_step(craft: Elements, body_period: float, t0: float,
                   r_limit: float) -> float:
    """01 §3.4 binding step rules."""
    if craft.e < 1.0 and craft.alpha > 0.0:
        return min(craft.period, body_period) / _SAMPLES
    t_exit = time_to_radius(craft, r_limit, t0)
    if t_exit is None:
        rx, ry, _, _ = elements_to_state(craft, t0)
        t_exit = time_to_radius(craft, 2.0 * math.hypot(rx, ry), t0)
        if t_exit is None:
            return body_period / _SAMPLES
    span = max(t_exit - t0, 1.0)
    return min(span / _SAMPLES, body_period / _SAMPLES)


def predict_entry(craft: Elements, body: Elements, r_soi: float,
                  body_id: str, t0: float, horizon: float) -> SoiCrossing | None:
    """First entry of the craft (elements in the shared parent frame) into a
    child body's SOI within [t0, t0+horizon]; refined to ±1 s."""
    if r_soi <= 0.0:
        return None

    def gap(t: float) -> float:
        crx, cry, _, _ = elements_to_state(craft, t)
        brx, bry, _, _ = elements_to_state(body, t)
        return math.hypot(crx - brx, cry - bry) - r_soi

    step = _sampling_step(craft, body.period, t0, r_soi * 1e6)
    t_prev, g_prev = t0, gap(t0)
    t = t0
    t_end = t0 + horizon
    while t < t_end:
        t = min(t + step, t_end)
        g = gap(t)
        if g_prev > 0.0 and g <= 0.0:
            t_cross = brent(gap, t_prev, t, tol=REFINE_TOL_S)
            return SoiCrossing(t_cross=t_cross, body_id=body_id, entering=True)
        t_prev, g_prev = t, g
    return None


def predict_exit(craft: Elements, r_soi_frame: float, frame_id: str,
                 t0: float, horizon: float) -> SoiCrossing | None:
    """First exit of the craft from its current frame's SOI within the
    horizon (rays out of the frame body's influence); refined to ±1 s."""
    if not math.isfinite(r_soi_frame):
        return None
    t_exit = time_to_radius(craft, r_soi_frame, t0)
    if t_exit is None or t_exit > t0 + horizon:
        return None

    def gap(t: float) -> float:
        rx, ry, _, _ = elements_to_state(craft, t)
        return math.hypot(rx, ry) - r_soi_frame

    # bracket around the analytic root (it is exact up to anomaly wrapping;
    # Brent keeps the contract uniform with entry prediction)
    lo, hi = t_exit - 2.0, t_exit + 2.0
    if gap(lo) * gap(hi) > 0.0:
        return SoiCrossing(t_cross=t_exit, body_id=frame_id, entering=False)
    t_cross = brent(gap, lo, hi, tol=REFINE_TOL_S)
    return SoiCrossing(t_cross=t_cross, body_id=frame_id, entering=False)
