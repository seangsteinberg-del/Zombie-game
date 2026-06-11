"""Universal-variable Kepler propagation and 2D element conversions.

Implements 01-orbital-mechanics.md §3.2/§3.3 exactly (binding, restated in
13-architecture.md §3.6): one propagator for all conics, float64, Stumpff
series guard, Newton with bisection fallback. Element set (mu, alpha, e,
varpi, tau, s); alpha = 1/a so near-parabolic states stay representable.

Sign convention: s = +1 prograde (CCW, h = x*vy - y*vx > 0), -1 retrograde.
True anomaly nu = s*(theta - varpi) increases with time for both senses.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from aphelion.core.math2d import (
    bisect,
    stumpff_c,
    stumpff_c_np,
    stumpff_s,
    stumpff_s_np,
    wrap_pi,
)

# Dimensionless near-parabolic classification: |alpha*r0| below this uses the
# Barker seed (01 §3.3). alpha itself is 1/m so an absolute test would
# misclassify outer-planet orbits.
_PARABOLIC_XI = 1e-12

# 01 §8.6: radial orbits (h ~ 0) are clamped to a near-parabolic conic.
_ECC_CLAMP_ELLIPTIC = 0.999999
_ECC_CLAMP_HYPERBOLIC = 1.000001

_NEWTON_TOL = 1e-8      # convergence: |F|/sqrt(mu) < 1e-8 s (01 §3.3)
_NEWTON_MAX = 100


def _kepler_tol(dt: float) -> float:
    """Convergence tolerance in seconds. The spec's 1e-8 s plus a float64
    floor: F is evaluated through ~|sqrt(mu)*dt|-magnitude cancellations, so
    residuals below ~|dt|*1e-13 are rounding noise, not non-convergence."""
    return _NEWTON_TOL + 1e-13 * abs(dt)


def _kepler_f(chi: float, r0: float, vr0: float, alpha: float,
              sqrt_mu: float, dt: float) -> float:
    z = alpha * chi * chi
    c = stumpff_c(z)
    s = stumpff_s(z)
    return ((r0 * vr0 / sqrt_mu) * chi * chi * c
            + (1.0 - alpha * r0) * chi * chi * chi * s
            + r0 * chi - sqrt_mu * dt)


def _initial_chi(r0x: float, r0y: float, v0x: float, v0y: float,
                 r0: float, rv: float, alpha: float, mu: float,
                 dt: float) -> float:
    sqrt_mu = math.sqrt(mu)
    xi = alpha * r0
    if abs(xi) < _PARABOLIC_XI:
        # Barker seed (Vallado Alg. 8); any failure falls through to a simple
        # guess — Newton+bisection still converges, the seed is only speed.
        try:
            h = abs(r0x * v0y - r0y * v0x)
            p = h * h / mu
            cot2s = 3.0 * math.sqrt(mu / (p * p * p)) * dt
            two_s = math.atan2(1.0, cot2s)
            w = math.atan(math.copysign(abs(math.tan(0.5 * two_s)) ** (1.0 / 3.0),
                                        math.tan(0.5 * two_s)))
            return math.sqrt(p) * 2.0 / math.tan(2.0 * w)
        except (ValueError, ZeroDivisionError, OverflowError):
            return sqrt_mu * dt / r0
    if alpha > 0.0:
        return sqrt_mu * alpha * dt
    # hyperbolic
    a = 1.0 / alpha
    sgn = 1.0 if dt >= 0.0 else -1.0
    num = -2.0 * mu * alpha * dt
    den = rv + sgn * math.sqrt(-mu * a) * (1.0 - r0 * alpha)
    if den == 0.0 or num / den <= 0.0:
        return sqrt_mu * dt / r0
    return sgn * math.sqrt(-a) * math.log(num / den)


def propagate(r0x: float, r0y: float, v0x: float, v0y: float,
              dt: float, mu: float) -> tuple[float, float, float, float]:
    """Exact conic propagation by dt seconds. Returns (rx, ry, vx, vy)."""
    if dt == 0.0:
        return (r0x, r0y, v0x, v0y)

    r0 = math.hypot(r0x, r0y)
    v02 = v0x * v0x + v0y * v0y
    rv = r0x * v0x + r0y * v0y
    vr0 = rv / r0
    alpha = 2.0 / r0 - v02 / mu
    sqrt_mu = math.sqrt(mu)

    chi = _initial_chi(r0x, r0y, v0x, v0y, r0, rv, alpha, mu, dt)
    tol = _kepler_tol(dt)

    converged = False
    for _ in range(_NEWTON_MAX):
        z = alpha * chi * chi
        c = stumpff_c(z)
        s = stumpff_s(z)
        f_val = ((r0 * vr0 / sqrt_mu) * chi * chi * c
                 + (1.0 - alpha * r0) * chi * chi * chi * s
                 + r0 * chi - sqrt_mu * dt)
        if abs(f_val) / sqrt_mu < tol:
            converged = True
            break
        fp = ((r0 * vr0 / sqrt_mu) * chi * (1.0 - z * s)
              + (1.0 - alpha * r0) * chi * chi * c + r0)
        if fp == 0.0:
            break
        chi -= f_val / fp

    if not converged:
        # F is monotonic in chi: bracket by doubling expansion, then bisect.
        step = max(abs(chi), sqrt_mu * abs(dt) / r0, 1.0)
        lo, hi = chi - step, chi + step
        f = lambda x: _kepler_f(x, r0, vr0, alpha, sqrt_mu, dt)
        for _ in range(200):
            if f(lo) * f(hi) <= 0.0:
                break
            step *= 2.0
            lo -= step
            hi += step
        chi = bisect(f, lo, hi, tol=tol * sqrt_mu)

    z = alpha * chi * chi
    c = stumpff_c(z)
    s = stumpff_s(z)
    f_l = 1.0 - (chi * chi / r0) * c
    g_l = dt - (chi * chi * chi / sqrt_mu) * s
    rx = f_l * r0x + g_l * v0x
    ry = f_l * r0y + g_l * v0y
    r = math.hypot(rx, ry)
    fdot = (sqrt_mu / (r * r0)) * chi * (z * s - 1.0)
    gdot = 1.0 - (chi * chi / r) * c
    vx = fdot * r0x + gdot * v0x
    vy = fdot * r0y + gdot * v0y
    return (rx, ry, vx, vy)


def propagate_batch(r0: np.ndarray, v0: np.ndarray, dt: np.ndarray | float,
                    mu: np.ndarray | float) -> tuple[np.ndarray, np.ndarray]:
    """Vectorized universal-Kepler over N objects (13 §3.6 call shape 2).

    r0, v0: (N, 2) float64. dt, mu: scalar or (N,). Returns (r, v) each (N, 2).
    Newton runs vectorized with a convergence mask; rare stragglers fall back
    to the scalar path (which carries the bisection guarantee).
    """
    r0 = np.asarray(r0, dtype=np.float64)
    v0 = np.asarray(v0, dtype=np.float64)
    n = r0.shape[0]
    dt = np.broadcast_to(np.asarray(dt, dtype=np.float64), (n,)).copy()
    mu = np.broadcast_to(np.asarray(mu, dtype=np.float64), (n,)).copy()

    r0n = np.hypot(r0[:, 0], r0[:, 1])
    v02 = v0[:, 0] ** 2 + v0[:, 1] ** 2
    rv = r0[:, 0] * v0[:, 0] + r0[:, 1] * v0[:, 1]
    vr0 = rv / r0n
    alpha = 2.0 / r0n - v02 / mu
    sqrt_mu = np.sqrt(mu)

    # Initial guess: elliptic everywhere, hyperbolic where valid (near-parabolic
    # rows keep the simple guess; Newton/bisection-fallback absorbs them).
    chi = sqrt_mu * alpha * dt
    hyp = alpha < 0.0
    if np.any(hyp):
        with np.errstate(all="ignore"):
            a_h = 1.0 / alpha
            sgn = np.where(dt >= 0.0, 1.0, -1.0)
            num = -2.0 * mu * alpha * dt
            den = rv + sgn * np.sqrt(np.where(hyp, -mu * a_h, 1.0)) * (1.0 - r0n * alpha)
            ratio = num / den
            guess_h = sgn * np.sqrt(np.where(hyp, -a_h, 1.0)) * np.log(np.where(ratio > 0.0, ratio, 1.0))
        ok = hyp & np.isfinite(guess_h) & (ratio > 0.0)
        chi = np.where(ok, guess_h, chi)
    simple = ~np.isfinite(chi) | (np.abs(alpha * r0n) < _PARABOLIC_XI)
    chi = np.where(simple, sqrt_mu * dt / r0n, chi)

    # Loop invariants hoisted: the Newton iteration must stay allocation-lean
    # to hold the 13 §4.6 budget (2,000 objects < 0.5 ms).
    a_coef = r0n * vr0 / sqrt_mu
    b_coef = 1.0 - alpha * r0n
    sqrt_mu_dt = sqrt_mu * dt

    tol = _NEWTON_TOL + 1e-13 * np.abs(dt)
    active = dt != 0.0
    for _ in range(60):
        z = alpha * chi * chi
        c = stumpff_c_np(z)
        s = stumpff_s_np(z)
        chi2 = chi * chi
        f_val = a_coef * chi2 * c + b_coef * chi2 * chi * s + r0n * chi - sqrt_mu_dt
        conv = np.abs(f_val) < tol * sqrt_mu
        active = active & ~conv
        if not np.any(active):
            break
        fp = a_coef * chi * (1.0 - z * s) + b_coef * chi2 * c + r0n
        with np.errstate(all="ignore"):
            step = np.where(fp != 0.0, f_val / fp, 0.0)
        chi = np.where(active, chi - step, chi)

    rx = np.empty(n)
    ry = np.empty(n)
    vx = np.empty(n)
    vy = np.empty(n)

    z = alpha * chi * chi
    c = stumpff_c_np(z)
    s = stumpff_s_np(z)
    f_l = 1.0 - (chi * chi / r0n) * c
    g_l = dt - (chi ** 3 / sqrt_mu) * s
    rx = f_l * r0[:, 0] + g_l * v0[:, 0]
    ry = f_l * r0[:, 1] + g_l * v0[:, 1]
    rn = np.hypot(rx, ry)
    fdot = (sqrt_mu / (rn * r0n)) * chi * (z * s - 1.0)
    gdot = 1.0 - (chi * chi / rn) * c
    vx = fdot * r0[:, 0] + gdot * v0[:, 0]
    vy = fdot * r0[:, 1] + gdot * v0[:, 1]

    # Stragglers (or rows that drifted): re-do via the guaranteed scalar path.
    f_chk = ((r0n * vr0 / sqrt_mu) * chi * chi * c
             + (1.0 - alpha * r0n) * chi ** 3 * s
             + r0n * chi - sqrt_mu * dt)
    bad = (np.abs(f_chk) / sqrt_mu >= tol) & (dt != 0.0)
    bad |= ~np.isfinite(rx) | ~np.isfinite(ry) | ~np.isfinite(vx) | ~np.isfinite(vy)
    for i in np.nonzero(bad)[0]:
        rx[i], ry[i], vx[i], vy[i] = propagate(
            r0[i, 0], r0[i, 1], v0[i, 0], v0[i, 1], float(dt[i]), float(mu[i]))

    zero = dt == 0.0
    if np.any(zero):
        rx[zero] = r0[zero, 0]
        ry[zero] = r0[zero, 1]
        vx[zero] = v0[zero, 0]
        vy[zero] = v0[zero, 1]

    return (np.stack([rx, ry], axis=1), np.stack([vx, vy], axis=1))


@dataclass(frozen=True, slots=True)
class Elements:
    """On-rails element set (01 §3.2): (mu, alpha=1/a, e, varpi, tau, s)."""

    mu: float
    alpha: float
    e: float
    varpi: float
    tau: float
    s: float

    @property
    def a(self) -> float:
        return 1.0 / self.alpha if self.alpha != 0.0 else math.inf

    @property
    def p(self) -> float:
        return (1.0 - self.e * self.e) / self.alpha if self.alpha != 0.0 else math.nan

    @property
    def period(self) -> float:
        """Orbital period, s (elliptic only)."""
        if self.alpha <= 0.0:
            return math.inf
        n = math.sqrt(self.mu * self.alpha ** 3)
        return 2.0 * math.pi / n

    @property
    def periapsis(self) -> float:
        if self.alpha != 0.0:
            return (1.0 - self.e) / self.alpha if self.e < 1.0 else self.a * (1.0 - self.e)
        return math.nan

    @property
    def apoapsis(self) -> float:
        return (1.0 + self.e) / self.alpha if self.alpha > 0.0 else math.inf


def state_to_elements(rx: float, ry: float, vx: float, vy: float,
                      t: float, mu: float) -> Elements:
    r = math.hypot(rx, ry)
    v2 = vx * vx + vy * vy
    rv = rx * vx + ry * vy
    h = rx * vy - ry * vx
    s = 1.0 if h >= 0.0 else -1.0
    alpha = 2.0 / r - v2 / mu

    evx = ((v2 - mu / r) * rx - rv * vx) / mu
    evy = ((v2 - mu / r) * ry - rv * vy) / mu
    e = math.hypot(evx, evy)

    if abs(h) < 1e-6 * math.sqrt(mu * r):
        # Degenerate radial orbit (01 §8.6): clamp eccentricity, periapsis
        # direction toward the body.
        e = _ECC_CLAMP_ELLIPTIC if alpha > 0.0 else _ECC_CLAMP_HYPERBOLIC
        varpi = wrap_pi(math.atan2(-ry, -rx))
        nu = math.pi - 1e-6
    elif e < 1e-12:
        varpi = 0.0
        nu = wrap_pi(s * math.atan2(ry, rx))
    else:
        varpi = math.atan2(evy, evx)
        theta = math.atan2(ry, rx)
        nu = wrap_pi(s * (theta - varpi))

    # Time of periapsis passage from nu.
    if alpha * r > _PARABOLIC_XI:        # elliptic
        ecc_e = 2.0 * math.atan2(math.sqrt(max(1.0 - e, 0.0)) * math.sin(0.5 * nu),
                                 math.sqrt(1.0 + e) * math.cos(0.5 * nu))
        m_anom = ecc_e - e * math.sin(ecc_e)
        n = math.sqrt(mu * alpha ** 3)
        tau = t - m_anom / n
    elif alpha * r < -_PARABOLIC_XI:     # hyperbolic
        arg = math.sqrt((e - 1.0) / (e + 1.0)) * math.tan(0.5 * nu)
        arg = max(min(arg, 1.0 - 1e-15), -(1.0 - 1e-15))
        h_anom = 2.0 * math.atanh(arg)
        m_anom = e * math.sinh(h_anom) - h_anom
        n = math.sqrt(mu * (-alpha) ** 3)
        tau = t - m_anom / n
    else:                                 # parabolic: Barker's equation
        p = h * h / mu
        d = math.tan(0.5 * nu)
        tau = t - 0.5 * math.sqrt(p ** 3 / mu) * (d + d ** 3 / 3.0)

    return Elements(mu=mu, alpha=alpha, e=e, varpi=varpi, tau=tau, s=s)


def elements_to_state(el: Elements, t: float) -> tuple[float, float, float, float]:
    """Exact state at time t: build the periapsis state, propagate by t - tau."""
    dt = t - el.tau
    if el.alpha > 0.0:
        dt = math.fmod(dt, el.period)
    p = el.p
    rp = p / (1.0 + el.e)
    cw, sw = math.cos(el.varpi), math.sin(el.varpi)
    rpx, rpy = rp * cw, rp * sw
    vp = math.sqrt(el.mu / p) * (1.0 + el.e)
    vpx, vpy = el.s * (-sw) * vp, el.s * cw * vp
    return propagate(rpx, rpy, vpx, vpy, dt, el.mu)
