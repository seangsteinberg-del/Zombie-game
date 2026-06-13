"""Finite burns + thrust-under-warp integration (01 §1.9/§1.15/§1.16/§2.9).

RKF4(5) adaptive integrator for the 2D two-body + thrust problem over the
binding 5-state layout [x, y, vx, vy, m] (13 §3.6):

    a_vec = -mu r_vec/|r|^3 + (T/m) u_hat(t),    mdot = -T/(Isp g0)

Spec bindings implemented here:
- 01 §1.16: prediction integrator is RKF4(5) adaptive, rel tol 1e-9
  (RKF_REL_TOL).
- 01 §1.9 thrust warp: dt capped so a_thrust * dt <= 1 m/s
  (WARP_DV_CAP_MPS); max-step parameter for the warp ladder.
- 01 §2.9 Tsiolkovsky: dv = ve ln(m0/m1); ve = Isp * g0, g0 = 9.80665
  exactly; t_b = (m0 ve / F)(1 - e^(-dv/ve)); ignition at t_node - t_b/2
  (centered burn); m_prop = m0 (1 - e^(-dv/ve)).
- 01 §1.15: a node is (t, dv_prograde, dv_radial) — NO normal component
  exists in 2D, so all steering here is planar: "prograde"/"retrograde"
  follow the instantaneous velocity; a float steer is a fixed inertial
  direction angle (rad). node_to_finite covers the prograde channel
  (signed dv); a radial burn is a burn_arc with a fixed-angle steer.

The pair advances the 5th-order solution (local extrapolation) and controls
the step on the 4th/5th difference, so the global error sits well below the
per-step tolerance — proven by the 10-orbit conservation test in
aphelion/tests/test_finite_burn.py. Constant thrust means mdot is constant,
so m(t) is exactly linear and mass depletion matches the rocket equation to
roundoff. Pure functions, deterministic, float64 throughout (01 §1.16).
"""

from __future__ import annotations

import math
from typing import Callable, NamedTuple

import numpy as np

from aphelion.core.units import G0
from aphelion.sim.orbits.kepler import (
    Elements,
    elements_to_state,
    state_to_elements,
)

RKF_REL_TOL = 1e-9      # 01 §1.16: RKF4(5) adaptive, rel tol 1e-9
WARP_DV_CAP_MPS = 1.0   # 01 §1.9: dt capped so a_thrust*dt <= 1 m/s

Derivative = Callable[[float, np.ndarray], np.ndarray]
Steer = "str | float"   # "prograde" | "retrograde" | fixed angle (rad)

# --- Fehlberg 4(5) tableau (classic RKF45 coefficients) ---------------------

_C2, _C3, _C4, _C6 = 0.25, 0.375, 12.0 / 13.0, 0.5
_A21 = 0.25
_A31, _A32 = 3.0 / 32.0, 9.0 / 32.0
_A41, _A42, _A43 = 1932.0 / 2197.0, -7200.0 / 2197.0, 7296.0 / 2197.0
_A51, _A52, _A53, _A54 = 439.0 / 216.0, -8.0, 3680.0 / 513.0, -845.0 / 4104.0
_A61, _A62, _A63, _A64, _A65 = (-8.0 / 27.0, 2.0, -3544.0 / 2565.0,
                                1859.0 / 4104.0, -11.0 / 40.0)
# 5th-order weights (solution advanced with these — local extrapolation).
_B1, _B3, _B4, _B5, _B6 = (16.0 / 135.0, 6656.0 / 12825.0,
                           28561.0 / 56430.0, -9.0 / 50.0, 2.0 / 55.0)
# Error weights = (5th - 4th)-order rows: the embedded 4(5) estimate.
_E1, _E3, _E4, _E5, _E6 = (1.0 / 360.0, -128.0 / 4275.0, -2197.0 / 75240.0,
                           1.0 / 50.0, 2.0 / 55.0)

_SAFETY = 0.9
_FAC_MIN, _FAC_MAX = 0.2, 5.0
_MAX_REJECTS = 60


def integrate_rkf45(f: Derivative, t0: float, y0: np.ndarray, t1: float, *,
                    rtol: float = RKF_REL_TOL,
                    ref: np.ndarray | None = None,
                    max_step: float = math.inf,
                    first_step: float | None = None,
                    record: bool = True) -> tuple[np.ndarray, np.ndarray | None]:
    """Adaptive RKF4(5) from t0 to t1 (01 §1.16: rel tol 1e-9 default).

    f(t, y) -> dy/dt. `ref` is a per-component magnitude floor for the
    relative error norm (defaults to |y0|) so components passing through
    zero (x, y, vx, vy do every orbit) keep an orbit-scale tolerance.
    `max_step` is the warp step cap (01 §1.9). Error norm is the max of
    |err_i| / (rtol * (ref_i + max(|y_i|, |y_i'|))); accept when <= 1.

    Returns (y_final, samples); samples rows are (t, *y) at every accepted
    step including t0 (None when record=False).
    """
    y = np.array(y0, dtype=np.float64)
    span = float(t1) - float(t0)
    if span < 0.0:
        raise ValueError("integrate_rkf45: t1 must be >= t0")
    ref = np.abs(y) if ref is None else np.asarray(ref, dtype=np.float64)
    rows: list[tuple[float, ...]] | None = (
        [(float(t0), *y)] if record else None)
    if span == 0.0:
        return y, (np.asarray(rows, dtype=np.float64) if record else None)

    t = float(t0)
    h = span * 1e-3 if first_step is None else float(first_step)
    h = min(h, max_step, span)
    rejects = 0
    while t < t1:
        h = min(h, max_step, t1 - t)
        last = h == (t1 - t)
        if h <= 1e-14 * max(abs(t), 1.0):
            raise RuntimeError("integrate_rkf45: step size underflow")

        k1 = f(t, y)
        k2 = f(t + _C2 * h, y + h * (_A21 * k1))
        k3 = f(t + _C3 * h, y + h * (_A31 * k1 + _A32 * k2))
        k4 = f(t + _C4 * h, y + h * (_A41 * k1 + _A42 * k2 + _A43 * k3))
        k5 = f(t + h, y + h * (_A51 * k1 + _A52 * k2 + _A53 * k3
                               + _A54 * k4))
        k6 = f(t + _C6 * h, y + h * (_A61 * k1 + _A62 * k2 + _A63 * k3
                                     + _A64 * k4 + _A65 * k5))
        y5 = y + h * (_B1 * k1 + _B3 * k3 + _B4 * k4 + _B5 * k5 + _B6 * k6)
        err = h * (_E1 * k1 + _E3 * k3 + _E4 * k4 + _E5 * k5 + _E6 * k6)

        scale = rtol * (ref + np.maximum(np.abs(y), np.abs(y5)))
        with np.errstate(all="ignore"):
            enorm = float(np.max(np.abs(err) / scale))

        if math.isfinite(enorm) and enorm <= 1.0:
            y = y5
            t = t1 if last else t + h
            if rows is not None:
                rows.append((t, *y))
            fac = _FAC_MAX if enorm == 0.0 else min(
                _FAC_MAX, max(_FAC_MIN, _SAFETY * enorm ** -0.2))
            h *= fac
            rejects = 0
        else:
            h *= (0.2 if not math.isfinite(enorm)
                  else max(0.1, min(0.9, _SAFETY * enorm ** -0.2)))
            rejects += 1
            if rejects > _MAX_REJECTS:
                raise RuntimeError("integrate_rkf45: step persistently rejected")

    return y, (np.asarray(rows, dtype=np.float64) if record else None)


def two_body_thrust(mu: float, thrust_n: float, isp_s: float,
                    steer: str | float = "prograde") -> Derivative:
    """dy/dt for y = [x, y, vx, vy, m]: point-mass gravity of the current
    SOI body only (01 §1.16) plus planar thrust steering.

    steer: "prograde" / "retrograde" (velocity-following, planar — no
    normal channel exists in 2D, 01 §1.15) or a fixed inertial direction
    angle in radians. mdot = -T/(Isp g0), g0 = 9.80665 exactly (01 §2.9).
    thrust_n = 0 gives the pure two-body coast derivative.
    """
    if thrust_n < 0.0:
        raise ValueError("thrust_n must be >= 0")
    mdot = 0.0
    if thrust_n > 0.0:
        if isp_s <= 0.0:
            raise ValueError("isp_s must be > 0 when thrusting")
        mdot = thrust_n / (isp_s * G0)

    fixed: tuple[float, float] | None = None
    sgn = 1.0
    if isinstance(steer, str):
        if steer == "retrograde":
            sgn = -1.0
        elif steer != "prograde":
            raise ValueError(f"unknown steer law: {steer!r}")
    else:
        fixed = (math.cos(float(steer)), math.sin(float(steer)))

    def f(t: float, y: np.ndarray) -> np.ndarray:
        x, yy, vx, vy, m = y
        r2 = x * x + yy * yy
        g = -mu / (r2 * math.sqrt(r2))
        ax = g * x
        ay = g * yy
        dm = 0.0
        if thrust_n > 0.0:
            a_t = thrust_n / m
            if fixed is not None:
                ax += a_t * fixed[0]
                ay += a_t * fixed[1]
                dm = -mdot
            else:
                v = math.hypot(vx, vy)
                if v > 0.0:    # undefined prograde at rest -> coast (idiom
                    ax += sgn * a_t * vx / v   # of integrator.py guidance)
                    ay += sgn * a_t * vy / v
                    dm = -mdot
        return np.array([vx, vy, ax, ay, dm])

    return f


class BurnArc(NamedTuple):
    """Finite-burn result: post-burn osculating elements (conic refit at
    burnout — 01 §1.16 'thrust ends -> immediately refit conic'), final
    mass, and the trajectory samples (t, x, y, vx, vy, m) at every accepted
    RKF45 step."""

    elements: Elements
    m_final: float
    samples: np.ndarray


def burn_arc(elements: Elements, mu: float, t_ignite: float,
             duration_s: float, thrust_n: float, isp_s: float,
             m0_kg: float, steer: str | float = "prograde", *,
             rtol: float = RKF_REL_TOL,
             max_step: float = math.inf) -> BurnArc:
    """Integrate a constant-thrust finite burn from the on-rails state at
    t_ignite for duration_s ("always executed as finite burns by the
    integrator", 01 §1.15).

    The thrust-warp cap of 01 §1.9 — dt such that a_thrust*dt <= 1 m/s —
    is applied on top of max_step using the burn's worst (final, lightest)
    mass; mdot is constant so m_end = m0 - (T/ve) * duration exactly.
    Exhaustion mid-burn (m_end <= 0) raises ValueError (01 §1.15 abort).
    """
    if duration_s < 0.0:
        raise ValueError("duration_s must be >= 0")
    if m0_kg <= 0.0:
        raise ValueError("m0_kg must be > 0")

    rx, ry, vx, vy = elements_to_state(elements, t_ignite)
    t_end = t_ignite + duration_s

    cap = max_step
    if thrust_n > 0.0 and duration_s > 0.0:
        m_end = m0_kg - (thrust_n / (isp_s * G0)) * duration_s
        if m_end <= 0.0:
            raise ValueError(
                "propellant exhaustion mid-burn — abort (01 §1.15)")
        cap = min(cap, WARP_DV_CAP_MPS * m_end / thrust_n)   # 01 §1.9

    r0 = math.hypot(rx, ry)
    v0 = math.hypot(vx, vy)
    y0 = np.array([rx, ry, vx, vy, m0_kg])
    ref = np.array([r0, r0, v0, v0, m0_kg])   # orbit-scale error floors

    f = two_body_thrust(mu, thrust_n, isp_s, steer)
    yf, samples = integrate_rkf45(f, t_ignite, y0, t_end, rtol=rtol,
                                  ref=ref, max_step=cap, record=True)
    el = state_to_elements(float(yf[0]), float(yf[1]), float(yf[2]),
                           float(yf[3]), t_end, mu)
    assert samples is not None
    return BurnArc(el, float(yf[4]), samples)


class FiniteNode(NamedTuple):
    """Finite-burn realization of an impulsive node (01 §1.15/§2.9).

    lead_s = t_b/2 (ignition at t_node - t_b/2, centered burn);
    duration_s = t_b from the rocket equation; residuals are measured at
    burnout against the impulsive post-burn conic propagated to the same
    instant."""

    t_ignite: float
    lead_s: float
    duration_s: float
    m_final: float
    elements: Elements        # finite-burn post-burn conic
    target: Elements          # impulsive post-burn conic (the plan)
    residual_dv_mps: float    # |v_finite - v_impulsive| at burnout
    residual_pos_m: float     # |r_finite - r_impulsive| at burnout


def node_to_finite(elements: Elements, mu: float, node_dv_mps: float,
                   thrust_n: float, isp_s: float, m0_kg: float,
                   t_node: float, *, rtol: float = RKF_REL_TOL,
                   max_step: float = math.inf) -> FiniteNode:
    """Execute an impulsive prograde node as the centered finite burn the
    integrator actually flies (01 §1.15).

    node_dv_mps is the signed prograde channel (positive = prograde,
    negative = retrograde; the 2D node has no normal component).
    t_b = (m0 ve / F)(1 - e^(-|dv|/ve)) and ignition at t_node - t_b/2
    (01 §2.9). The impulsive target conic matches
    node_exec.apply_node_impulsive (parity pinned in tests).
    """
    if thrust_n <= 0.0:
        raise ValueError("thrust_n must be > 0 to execute a node")
    dv = abs(node_dv_mps)
    ve = isp_s * G0
    t_b = (m0_kg * ve / thrust_n) * (1.0 - math.exp(-dv / ve))  # 01 §2.9
    t_ignite = t_node - 0.5 * t_b                               # centered

    steer = "prograde" if node_dv_mps >= 0.0 else "retrograde"
    arc = burn_arc(elements, mu, t_ignite, t_b, thrust_n, isp_s, m0_kg,
                   steer, rtol=rtol, max_step=max_step)

    # Impulsive target: instantaneous signed-prograde dv at t_node (same
    # construction as flight.node_exec.apply_node_impulsive, kept local so
    # orbits/ stays below flight/ in the layering).
    rx, ry, vx, vy = elements_to_state(elements, t_node)
    v = math.hypot(vx, vy)
    if v == 0.0:
        raise ValueError("undefined prograde direction at zero velocity")
    target = state_to_elements(rx, ry,
                               vx + node_dv_mps * vx / v,
                               vy + node_dv_mps * vy / v,
                               t_node, mu)

    t_end = t_ignite + t_b
    trx, try_, tvx, tvy = elements_to_state(target, t_end)
    frow = arc.samples[-1]   # (t, x, y, vx, vy, m) at burnout
    residual_dv = math.hypot(frow[3] - tvx, frow[4] - tvy)
    residual_pos = math.hypot(frow[1] - trx, frow[2] - try_)
    return FiniteNode(t_ignite, 0.5 * t_b, t_b, arc.m_final,
                      arc.elements, target, residual_dv, residual_pos)


# --- conserved-quantity helpers (test instrumentation) ----------------------

def specific_energy(x: float, y: float, vx: float, vy: float,
                    mu: float) -> float:
    """eps = v^2/2 - mu/r (01 §2.1); conserved on a zero-thrust arc."""
    return 0.5 * (vx * vx + vy * vy) - mu / math.hypot(x, y)


def specific_ang_momentum(x: float, y: float, vx: float, vy: float) -> float:
    """h = x*vy - y*vx (01 §2.1, planar scalar); conserved at zero thrust."""
    return x * vy - y * vx
