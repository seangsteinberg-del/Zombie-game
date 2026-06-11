"""Float64 2D math primitives (13 §3.2): Stumpff functions, root helpers, RK4.

The Stumpff series guard at |z| < 1e-6 is binding (13 §3.6 / 01 §3.3): the
closed forms suffer catastrophic cancellation near z = 0.
"""

from __future__ import annotations

import math
from typing import Callable

import numpy as np

_STUMPFF_GUARD = 1e-6
# cosh/sinh overflow past sqrt(-z) ~ 710; clamping keeps root-finder probes
# finite with correct sign/monotonicity (values there are ~1e298 anyway).
_STUMPFF_NEG_CLAMP = 4.9e5


def stumpff_c(z: float) -> float:
    if abs(z) < _STUMPFF_GUARD:
        return 0.5 - z / 24.0 + z * z / 720.0 - z * z * z / 40_320.0
    if z > 0.0:
        return (1.0 - math.cos(math.sqrt(z))) / z
    nz = min(-z, _STUMPFF_NEG_CLAMP)
    return (math.cosh(math.sqrt(nz)) - 1.0) / nz


def stumpff_s(z: float) -> float:
    if abs(z) < _STUMPFF_GUARD:
        return 1.0 / 6.0 - z / 120.0 + z * z / 5_040.0 - z * z * z / 362_880.0
    if z > 0.0:
        sz = math.sqrt(z)
        return (sz - math.sin(sz)) / (sz * z)
    nz = min(-z, _STUMPFF_NEG_CLAMP)
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
    zn = np.minimum(-z[neg], _STUMPFF_NEG_CLAMP)
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
    zn = np.minimum(-z[neg], _STUMPFF_NEG_CLAMP)
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


def brent(f: Callable[[float], float], a: float, b: float,
          tol: float, max_iter: int = 100) -> float:
    """Brent's method on a bracketing interval [a, b]; f(a), f(b) must differ
    in sign. Used by the SOI crossing predictor (13 §3.8: refine to ±1 s)."""
    fa, fb = f(a), f(b)
    if fa == 0.0:
        return a
    if fb == 0.0:
        return b
    if (fa < 0.0) == (fb < 0.0):
        raise ValueError("brent: root not bracketed")
    if abs(fa) < abs(fb):
        a, b, fa, fb = b, a, fb, fa
    c, fc = a, fa
    d = e = b - a
    for _ in range(max_iter):
        if (fb < 0.0) == (fc < 0.0):
            c, fc = a, fa
            d = e = b - a
        if abs(fc) < abs(fb):
            a, b, c = b, c, b
            fa, fb, fc = fb, fc, fb
        tol1 = 2.0 * 1e-16 * abs(b) + 0.5 * tol
        xm = 0.5 * (c - b)
        if abs(xm) <= tol1 or fb == 0.0:
            return b
        if abs(e) >= tol1 and abs(fa) > abs(fb):
            s = fb / fa
            if a == c:
                p, q = 2.0 * xm * s, 1.0 - s
            else:
                q, r = fa / fc, fb / fc
                p = s * (2.0 * xm * q * (q - r) - (b - a) * (r - 1.0))
                q = (q - 1.0) * (r - 1.0) * (s - 1.0)
            if p > 0.0:
                q = -q
            p = abs(p)
            if 2.0 * p < min(3.0 * xm * q - abs(tol1 * q), abs(e * q)):
                e, d = d, p / q
            else:
                d = e = xm
        else:
            d = e = xm
        a, fa = b, fb
        b += d if abs(d) > tol1 else math.copysign(tol1, xm)
        fb = f(b)
    return b


def rk4_step(f: Callable[[float, np.ndarray], np.ndarray],
             t: float, y: np.ndarray, dt: float) -> np.ndarray:
    k1 = f(t, y)
    k2 = f(t + 0.5 * dt, y + 0.5 * dt * k1)
    k3 = f(t + 0.5 * dt, y + 0.5 * dt * k2)
    k4 = f(t + dt, y + dt * k3)
    return y + (dt / 6.0) * (k1 + 2.0 * k2 + 2.0 * k3 + k4)
