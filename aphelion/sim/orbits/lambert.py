"""Planar Lambert solver + porkchop transfer-window scan (01 §2.4 Window
Finder T1, §2.3 windows/synodic, DECISIONS C25; canon anchors §1.3/§2.6).

Izzo-style Lancaster–Blanchard iteration (Izzo 2015, "Revisiting
Lambert's problem"): nondimensional variables lambda = ±sqrt(1 - c/s)
and x; T(x) evaluated with the Lancaster–Blanchard form away from x = 1
and the Battin hypergeometric series near it; Householder 3rd-order
iteration with a guaranteed bisection fallback (T(x) is strictly
monotonic on the 0-rev branch) — same converge-or-bisect contract as the
universal Kepler propagator (01 §3.3).

2D planar adaptation (the whole game is coplanar): the orbit plane is
fixed, so the classical 180-degree normal-vector singularity disappears
(01 §2.4: "no 180° singularity (plane fixed)") — the radial/tangential
velocity reconstruction stays finite at exactly pi. The only remaining
branch choice is the sense of motion: prograde (CCW, s = +1, the C25
default) sweeps the geometric CCW angle; the complementary arc — the
classical "long way" — is the retrograde solution (prograde=False).
Ill-posed only at a swept angle of exactly 0/360 deg (ValueError),
exactly as the spec states.

Multi-revolution branches (M >= 1) are NOT implemented (0-rev only):
the Window Finder scans departure dates x times of flight, not
revolution counts.

All SI (m, m/s, s, m^3/s^2); pure functions; deterministic.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from aphelion.core.math2d import bisect
from aphelion.sim.orbits.kepler import Elements, elements_to_state

_HOUSEHOLDER_TOL = 1e-13     # |x_new - x| convergence (nondimensional)
_HOUSEHOLDER_MAX = 20
_BISECT_TOL = 1e-12          # |T(x) - T_target| for the fallback
_BATTIN_ZONE = 0.01          # |x - 1| below this -> Battin series
_HYP_SERIES_TOL = 1e-11


def _hyp2f1b(z: float) -> float:
    """Gauss hypergeometric 2F1(3, 1, 5/2, z), |z| < 1 (Battin series
    kernel for the near-parabolic time-of-flight)."""
    sj = 1.0
    cj = 1.0
    j = 0
    while True:
        cj = cj * (3.0 + j) * (1.0 + j) / (2.5 + j) * z / (j + 1.0)
        sj += cj
        if abs(cj) < _HYP_SERIES_TOL:
            return sj
        j += 1
        if j > 10_000:           # |z| -> 1 pathologies; never hit in domain
            return sj


def _x2tof(x: float, lam: float) -> float:
    """Nondimensional time of flight T(x) for the 0-rev branch.

    Lancaster–Blanchard form away from x = 1; Battin series inside
    |x - 1| < 0.01 where the closed form cancels catastrophically."""
    e = x * x - 1.0
    if abs(x - 1.0) < _BATTIN_ZONE:
        z = math.sqrt(1.0 + lam * lam * e)
        eta = z - lam * x
        s1 = 0.5 * (1.0 - lam - x * eta)
        q = (4.0 / 3.0) * _hyp2f1b(s1)
        return 0.5 * (eta ** 3 * q + 4.0 * lam * eta)
    rho = abs(e)
    y = math.sqrt(rho)
    z = math.sqrt(1.0 + lam * lam * e)
    g = x * z - lam * e
    if e < 0.0:                                   # elliptic
        d = math.acos(max(-1.0, min(1.0, g)))
    else:                                         # hyperbolic
        f = y * (z - lam * x)
        d = math.log(max(f + g, 1e-300))
    return (x - lam * z - d / y) / e


def _dtdx(x: float, lam: float, t: float) -> tuple[float, float, float]:
    """(T', T'', T''') at x (Izzo 2015 eq. 22); caller guards x = +/-1."""
    l2 = lam * lam
    l3 = l2 * lam
    umx2 = 1.0 - x * x
    y = math.sqrt(1.0 - l2 * umx2)
    y3 = y * y * y
    y5 = y3 * y * y
    dt = (3.0 * t * x - 2.0 + 2.0 * l3 * x / y) / umx2
    ddt = (3.0 * t + 5.0 * x * dt + 2.0 * (1.0 - l2) * l3 / y3) / umx2
    dddt = (7.0 * x * ddt + 8.0 * dt
            - 6.0 * (1.0 - l2) * l2 * l3 * x / y5) / umx2
    return dt, ddt, dddt


def _find_x(t_nd: float, lam: float) -> float:
    """Solve T(x) = t_nd on the 0-rev branch, x in (-1, inf).

    Izzo initial guess + Householder 3rd order; T(x) is strictly
    decreasing in x, so a bisection fallback is guaranteed to converge
    (mirrors the kepler.py Newton-then-bisect contract)."""
    t0 = math.acos(max(-1.0, min(1.0, lam))) + lam * math.sqrt(
        max(1.0 - lam * lam, 0.0))                    # T(x=0)
    t1 = (2.0 / 3.0) * (1.0 - lam ** 3)               # T(x=1), parabolic
    if t_nd >= t0:
        x = -(t_nd - t0) / (t_nd - t0 + 4.0)
    elif t_nd <= t1:
        x = t1 * (t1 - t_nd) / (0.4 * (1.0 - lam ** 5) * t_nd) + 1.0
    else:
        x = (t_nd / t0) ** (math.log(2.0) / math.log(t1 / t0)) - 1.0

    converged = False
    for _ in range(_HOUSEHOLDER_MAX):
        umx2 = 1.0 - x * x
        if umx2 == 0.0:                # exactly parabolic guess: fall back
            break
        t = _x2tof(x, lam)
        dt, ddt, dddt = _dtdx(x, lam, t)
        delta = t - t_nd
        dt2 = dt * dt
        denom = dt * (dt2 - delta * ddt) + dddt * delta * delta / 6.0
        if denom == 0.0:
            break
        x_new = x - delta * (dt2 - delta * ddt / 2.0) / denom
        if not math.isfinite(x_new) or x_new <= -1.0:
            break
        if abs(x_new - x) < _HOUSEHOLDER_TOL:
            x = x_new
            converged = True
            break
        x = x_new

    if converged:
        return x

    # Bisection fallback: T -> inf as x -> -1+ and T -> 0 as x -> inf.
    lo = -1.0 + 1e-9
    hi = max(x, 1.0) if (math.isfinite(x) and x > -1.0) else 1.0
    for _ in range(200):
        if _x2tof(hi, lam) < t_nd:
            break
        hi = hi * 2.0 + 1.0
    return bisect(lambda xx: _x2tof(xx, lam) - t_nd, lo, hi, tol=_BISECT_TOL)


def lambert(r1x: float, r1y: float, r2x: float, r2y: float,
            tof: float, mu: float,
            prograde: bool = True) -> tuple[float, float, float, float]:
    """Planar Lambert (01 §2.4): velocities of the unique 0-rev conic from
    r1_vec to r2_vec in exactly tof seconds. Returns (v1x, v1y, v2x, v2y).

    prograde=True (default, C25) sweeps the CCW angle from r1 to r2;
    prograde=False solves the complementary CW arc (the classical "long
    way" — in 2D the plane is fixed, so long-way = retrograde). Raises
    ValueError for tof <= 0 or a swept angle of exactly 0/360 deg.
    Multi-rev (M >= 1) branches are not implemented."""
    if tof <= 0.0:
        raise ValueError("lambert: tof must be > 0")
    if mu <= 0.0:
        raise ValueError("lambert: mu must be > 0")
    r1 = math.hypot(r1x, r1y)
    r2 = math.hypot(r2x, r2y)
    if r1 == 0.0 or r2 == 0.0:
        raise ValueError("lambert: position vector is zero")

    c = math.hypot(r2x - r1x, r2y - r1y)
    s = 0.5 * (r1 + r2 + c)
    cross = r1x * r2y - r1y * r2x
    dot = r1x * r2x + r1y * r2y
    if abs(cross) <= 1e-12 * r1 * r2 and dot > 0.0:
        # 01 §2.4: well-conditioned everywhere EXCEPT exactly 0/360 deg.
        raise ValueError("lambert: swept angle is 0/360 deg (ill-posed)")

    sense = 1.0 if prograde else -1.0
    # lambda > 0 for a swept angle < pi in the sense of motion, < 0 above
    # (sense*cross is sin(theta_swept) scaled by r1*r2).
    lam = math.sqrt(max(1.0 - c / s, 0.0))
    if sense * cross < 0.0:
        lam = -lam

    t_nd = tof * math.sqrt(2.0 * mu / s ** 3)
    x = _find_x(t_nd, lam)
    y = math.sqrt(max(1.0 - lam * lam * (1.0 - x * x), 0.0))

    # Izzo 2015 eq. 16 radial/tangential reconstruction — finite at a
    # 180 deg swept angle (lam = 0), which is why the planar solver has
    # no Hohmann-geometry singularity.
    gamma = math.sqrt(0.5 * mu * s)
    rho = (r1 - r2) / c
    sigma = math.sqrt(max(1.0 - rho * rho, 0.0))
    vr1 = gamma * ((lam * y - x) - rho * (lam * y + x)) / r1
    vr2 = -gamma * ((lam * y - x) + rho * (lam * y + x)) / r2
    vt = gamma * sigma * (y + lam * x)
    vt1 = vt / r1
    vt2 = vt / r2

    # 2D tangential unit vector: t_hat = h_hat x r_hat with h_hat =
    # sense * z_hat (planar adaptation of the 3D triad).
    v1x = vr1 * (r1x / r1) + vt1 * (-sense * r1y / r1)
    v1y = vr1 * (r1y / r1) + vt1 * (sense * r1x / r1)
    v2x = vr2 * (r2x / r2) + vt2 * (-sense * r2y / r2)
    v2y = vr2 * (r2y / r2) + vt2 * (sense * r2x / r2)
    return (v1x, v1y, v2x, v2y)


# ---------------------------------------------------------------------------
# Transfer-window scan (porkchop) over two on-rails bodies (01 §2.4, C25:
# 1D window bar default in UI, 2-axis porkchop behind "Advanced" toggle).
# ---------------------------------------------------------------------------

def transfer_vinfs(mu_sun: float, body1: Elements, body2: Elements,
                   t_depart: float, tof: float,
                   prograde: bool = True) -> tuple[float, float]:
    """(v_inf departure, v_inf arrival), m/s, for the Lambert leg leaving
    body1 at t_depart and reaching body2 at t_depart + tof. Both Elements
    must be in the same primary-centric frame (mu_sun). The UI maps the
    departure v_inf to C3 = vinf**2 or to an injection dv from a parking
    orbit via transfers.departure_dv (Oberth, 01 §2.3)."""
    r1x, r1y, b1vx, b1vy = elements_to_state(body1, t_depart)
    r2x, r2y, b2vx, b2vy = elements_to_state(body2, t_depart + tof)
    v1x, v1y, v2x, v2y = lambert(r1x, r1y, r2x, r2y, tof, mu_sun,
                                 prograde=prograde)
    return (math.hypot(v1x - b1vx, v1y - b1vy),
            math.hypot(b2vx - v2x, b2vy - v2y))


def dv_depart(mu_sun: float, body1: Elements, body2: Elements,
              t_depart: float, tof: float, prograde: bool = True) -> float:
    """Departure hyperbolic excess speed (v_inf, m/s) — the quantity the
    porkchop/window-bar UI colors (C3 = dv_depart**2)."""
    return transfer_vinfs(mu_sun, body1, body2, t_depart, tof,
                          prograde=prograde)[0]


def dv_arrive(mu_sun: float, body1: Elements, body2: Elements,
              t_depart: float, tof: float, prograde: bool = True) -> float:
    """Arrival v_inf (m/s); insertion dv from it via transfers.departure_dv
    at the capture periapsis, or ~50 m/s aerocapture trim (01 §1.2)."""
    return transfer_vinfs(mu_sun, body1, body2, t_depart, tof,
                          prograde=prograde)[1]


@dataclass(frozen=True, slots=True)
class PorkchopGrid:
    """Departure-date x time-of-flight scan. dv arrays are indexed
    [i, j] <-> (t_depart[i], tof[j]); inf marks ill-posed cells."""

    t_depart: np.ndarray     # (n_t,) departure epochs, s since t=0
    tof: np.ndarray          # (n_tof,) times of flight, s
    dv_depart: np.ndarray    # (n_t, n_tof) departure v_inf, m/s
    dv_arrive: np.ndarray    # (n_t, n_tof) arrival v_inf, m/s
    dv_total: np.ndarray     # (n_t, n_tof) dv_depart + dv_arrive, m/s


def porkchop(mu_sun: float, body1_elements: Elements,
             body2_elements: Elements,
             t0_window: tuple[float, float],
             tof_window: tuple[float, float],
             n_grid: int | tuple[int, int] = 32,
             prograde: bool = True) -> PorkchopGrid:
    """Scan total transfer dv (departure v_inf + arrival v_inf) over a
    departure-date x time-of-flight grid (01 §2.4 Window Finder; C25:
    this 2-axis grid is the "Advanced" porkchop; the default UI reduces
    it to the per-departure-date column minimum as a 1D window bar).

    n_grid: points per axis, int (both) or (n_t, n_tof). Cells where the
    geometry is ill-posed (swept angle exactly 0/360 deg) come back inf."""
    if isinstance(n_grid, tuple):
        n_t, n_tof = n_grid
    else:
        n_t = n_tof = int(n_grid)
    if n_t < 2 or n_tof < 2:
        raise ValueError("porkchop: n_grid must be >= 2 per axis")
    t_dep = np.linspace(t0_window[0], t0_window[1], n_t)
    tofs = np.linspace(tof_window[0], tof_window[1], n_tof)
    dvd = np.full((n_t, n_tof), np.inf)
    dva = np.full((n_t, n_tof), np.inf)
    for i in range(n_t):
        for j in range(n_tof):
            try:
                d, a = transfer_vinfs(mu_sun, body1_elements,
                                      body2_elements, float(t_dep[i]),
                                      float(tofs[j]), prograde=prograde)
            except ValueError:
                continue
            dvd[i, j] = d
            dva[i, j] = a
    return PorkchopGrid(t_depart=t_dep, tof=tofs, dv_depart=dvd,
                        dv_arrive=dva, dv_total=dvd + dva)


def best_window(mu_sun: float, body1_elements: Elements,
                body2_elements: Elements,
                t0_window: tuple[float, float],
                tof_window: tuple[float, float],
                n_grid: int | tuple[int, int] = 32,
                prograde: bool = True) -> tuple[float, float, float]:
    """Convenience scan: build the porkchop and return its minimum cell as
    (t_depart, tof, dv_total) — the row the planner auto-creates a node
    chain from (01 §2.4)."""
    grid = porkchop(mu_sun, body1_elements, body2_elements, t0_window,
                    tof_window, n_grid, prograde=prograde)
    k = int(np.argmin(grid.dv_total))
    i, j = divmod(k, grid.tof.size)
    if not math.isfinite(grid.dv_total[i, j]):
        raise ValueError("best_window: no feasible transfer in window")
    return (float(grid.t_depart[i]), float(grid.tof[j]),
            float(grid.dv_total[i, j]))
