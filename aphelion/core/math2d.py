"""Float64 2D math primitives (13 §3.2): Stumpff functions, root helpers, RK4.

The Stumpff series guard at |z| < 1e-6 is binding (13 §3.6 / 01 §3.3): the
closed forms suffer catastrophic cancellation near z = 0.
"""

from __future__ import annotations

import math
from typing import Callable

import numpy as np

_STUMPFF_GUARD = 1e-6


def stumpff_c(z: float) -> float:
    if abs(z) < _STUMPFF_GUARD:
        return 0.5 - z / 24.0 + z * z / 720.0 - z * z * z / 40_320.0
    if z > 0.0:
        return (1.0 - math.cos(math.sqrt(z))) / z
    nz = -z
    return (math.cosh(math.sqrt(nz)) - 1.0) / nz


def stumpff_s(z: float) -> float:
    if abs(z) < _STUMPFF_GUARD:
        return 1.0 / 6.0 - z / 120.0 + z * z / 5_040.0 - z * z * z / 362_880.0
    if z > 0.0:
        sz = math.sqrt(z)
        return (sz - math.sin(sz)) / (sz * z)
    nz = -z
    snz = math.sqrt(nz)
    return (math.sinh(snz) - snz) / (snz * nz)


def stumpff_c_np(z: np.ndarray) -> np.ndarray:
    out = np.empty_like(z)
    small = np.abs(z) < _STUMPFF_GUARD
    pos = (z >= _STUMPFF_GUARD)
    neg = (z <= -_STUMPFF_GUARD)
    zs = z[small]
    out[small] = 0.5 - zs / 24.0 + zs * zs / 720.0 - zs * zs * zs / 40_320.0
    zp = z[pos]
    out[pos] = (1.0 - np.cos(np.sqrt(zp))) / zp
    zn = -z[neg]
    out[neg] = (np.cosh(np.sqrt(zn)) - 1.0) / zn
    return out


def stumpff_s_np(z: np.ndarray) -> np.ndarray:
    out = np.empty_like(z)
    small = np.abs(z) < _STUMPFF_GUARD
    pos = (z >= _STUMPFF_GUARD)
    neg = (z <= -_STUMPFF_GUARD)
    zs = z[small]
    out[small] = 1.0 / 6.0 - zs / 120.0 + zs * zs / 5_040.0 - zs * zs * zs / 362_880.0
    zp = z[pos]
    szp = np.sqrt(zp)
    out[pos] = (szp - np.sin(szp)) / (szp * zp)
    zn = -z[neg]
    snzn = np.sqrt(zn)
    out[neg] = (np.sinh(snzn) - snzn) / (snzn * zn)
    return out


def wrap_pi(angle: float) -> float:
    """Wrap to (-pi, pi]."""
    a = math.fmod(angle + math.pi, 2.0 * math.pi)
    if a <= 0.0:
        a += 2.0 * math.pi
    return a - math.pi


def bisect(f: Callable[[float], float], lo: float, hi: float,
           tol: float, max_iter: int = 200) -> float:
    """Bisection on a bracketing interval; f(lo) and f(hi) must differ in sign."""
    flo = f(lo)
    for _ in range(max_iter):
        mid = 0.5 * (lo + hi)
        fmid = f(mid)
        if abs(fmid) < tol or (hi - lo) < 1e-15 * max(1.0, abs(mid)):
            return mid
        if (flo < 0.0) == (fmid < 0.0):
            lo, flo = mid, fmid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def rk4_step(f: Callable[[float, np.ndarray], np.ndarray],
             t: float, y: np.ndarray, dt: float) -> np.ndarray:
    k1 = f(t, y)
    k2 = f(t + 0.5 * dt, y + 0.5 * dt * k1)
    k3 = f(t + 0.5 * dt, y + 0.5 * dt * k2)
    k4 = f(t + dt, y + dt * k3)
    return y + (dt / 6.0) * (k1 + 2.0 * k2 + 2.0 * k3 + k4)
