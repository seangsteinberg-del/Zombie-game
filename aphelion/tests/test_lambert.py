"""01 §2.4 Lambert / Window Finder pins: the Hohmann limit against the
§2.3 oracle (transfers.hohmann), the §2.6 Earth->Mars canon chain
(v_inf 2.95/2.65 km/s, TMI 3,590 m/s, phase 44.3 deg, 259 d), the §1.3
Earth->Venus row (146 d, 2.50/2.71 km/s, -54.0 deg trailing phase),
porkchop minimum vs the Hohmann dv, time-reversal mirroring, and
consistency with the universal-Kepler propagator (01 §2.2)."""

import math

import numpy as np
import pytest

from aphelion.core.units import AU, SECONDS_PER_DAY
from aphelion.sim.orbits import transfers as tr
from aphelion.sim.orbits.kepler import Elements, propagate
from aphelion.sim.orbits.lambert import (
    PorkchopGrid, best_window, dv_arrive, dv_depart, lambert, porkchop,
    transfer_vinfs)

MU_SUN = 1.327_124_400_18e20
MU_EARTH = 3.986_004_418e14

R_LEO300 = 6.678e6           # 01 §3.8 canonical parking orbit radius
GEO_PERIOD = 86_164.1        # sidereal day, s
MARS_A_AU = 1.5237
VENUS_A = 108.21e9           # 01 §1.1 canon table, m


def _circular(mu: float, a: float, theta0: float) -> Elements:
    """Circular prograde Elements with position angle theta0 at t = 0
    (angle(t) = n*(t - tau), 01 §2.1)."""
    n = math.sqrt(mu / a ** 3)
    return Elements(mu=mu, alpha=1.0 / a, e=0.0, varpi=0.0,
                    tau=-theta0 / n, s=1.0)


# ---- (a) Hohmann limit: Lambert at half the transfer period must ----------
# ---- reproduce transfers.hohmann (the §2.3 oracle) ------------------------

def test_hohmann_limit_leo_to_geo():
    """180 deg Lambert at tof = pi*sqrt(a_t^3/mu) == Hohmann (rel 1e-3).
    Exercises the lam = 0 geometry the 2D solver must handle exactly."""
    r_geo = tr.sma_from_period(MU_EARTH, GEO_PERIOD)
    dv1_h, dv2_h, t_h = tr.hohmann(MU_EARTH, R_LEO300, r_geo)
    v1x, v1y, v2x, v2y = lambert(R_LEO300, 0.0, -r_geo, 0.0, t_h, MU_EARTH)
    # departure burn from circular at (r1, 0): v_circ = (0, +v)
    dv1 = math.hypot(v1x, v1y - tr.circular_speed(MU_EARTH, R_LEO300))
    # arrival burn to circular at (-r2, 0): v_circ = (0, -v)
    dv2 = math.hypot(v2x, v2y + tr.circular_speed(MU_EARTH, r_geo))
    assert dv1 == pytest.approx(dv1_h, rel=1e-3)
    assert dv2 == pytest.approx(dv2_h, rel=1e-3)
    assert v1x == pytest.approx(0.0, abs=1e-3)      # tangent burn: no radial


def test_hohmann_limit_sun_earth_mars():
    """Same anchor heliocentric: 1 AU -> 1.5237 AU (01 §2.6 geometry)."""
    dv1_h, dv2_h, t_h = tr.hohmann(MU_SUN, AU, MARS_A_AU * AU)
    v1x, v1y, v2x, v2y = lambert(AU, 0.0, -MARS_A_AU * AU, 0.0, t_h, MU_SUN)
    dv1 = math.hypot(v1x, v1y - tr.circular_speed(MU_SUN, AU))
    dv2 = math.hypot(v2x, v2y + tr.circular_speed(MU_SUN, MARS_A_AU * AU))
    assert dv1 == pytest.approx(dv1_h, rel=1e-3)
    assert dv2 == pytest.approx(dv2_h, rel=1e-3)


# ---- consistency with the universal-Kepler propagator (01 §2.2) -----------

def _roundtrip(r0x, r0y, v0x, v0y, dt, mu, prograde=True):
    """propagate an arc, re-solve it with Lambert, demand both endpoint
    velocities back (rel 1e-6) and that the Lambert v1 re-propagates onto
    the arrival state."""
    r2x, r2y, v2x, v2y = propagate(r0x, r0y, v0x, v0y, dt, mu)
    w1x, w1y, w2x, w2y = lambert(r0x, r0y, r2x, r2y, dt, mu,
                                 prograde=prograde)
    assert w1x == pytest.approx(v0x, rel=1e-6, abs=1e-3)
    assert w1y == pytest.approx(v0y, rel=1e-6, abs=1e-3)
    assert w2x == pytest.approx(v2x, rel=1e-6, abs=1e-3)
    assert w2y == pytest.approx(v2y, rel=1e-6, abs=1e-3)
    px, py, qx, qy = propagate(r0x, r0y, w1x, w1y, dt, mu)
    assert px == pytest.approx(r2x, rel=1e-6, abs=1.0)
    assert py == pytest.approx(r2y, rel=1e-6, abs=1.0)
    assert qx == pytest.approx(v2x, rel=1e-6, abs=1e-3)
    assert qy == pytest.approx(v2y, rel=1e-6, abs=1e-3)


def test_recovers_elliptic_short_way():
    """Sweep < pi (lam > 0 branch) on an e = 0.3 ellipse."""
    a, e = 8.0e6, 0.3
    rp = a * (1.0 - e)
    vp = math.sqrt(MU_EARTH * (2.0 / rp - 1.0 / a))
    period = tr.orbital_period(MU_EARTH, a)
    _roundtrip(rp, 0.0, 0.0, vp, 0.2 * period, MU_EARTH)


def test_recovers_elliptic_long_way():
    """Sweep > pi (lam < 0 branch), still prograde: dt = 0.75 T."""
    a, e = 8.0e6, 0.3
    rp = a * (1.0 - e)
    vp = math.sqrt(MU_EARTH * (2.0 / rp - 1.0 / a))
    period = tr.orbital_period(MU_EARTH, a)
    _roundtrip(rp, 0.0, 0.0, vp, 0.75 * period, MU_EARTH)


def test_recovers_exact_pi_sweep():
    """Periapsis -> apoapsis is exactly 180 deg: the planar solver must be
    finite there (01 §2.4: no 180-deg singularity, plane fixed)."""
    a, e = 8.0e6, 0.3
    rp = a * (1.0 - e)
    vp = math.sqrt(MU_EARTH * (2.0 / rp - 1.0 / a))
    period = tr.orbital_period(MU_EARTH, a)
    _roundtrip(rp, 0.0, 0.0, vp, 0.5 * period, MU_EARTH)


def test_recovers_near_pi_off_apsis():
    """Half a period starting OFF the apse line: a 180-deg-class transfer
    with nonzero radial velocity at both ends."""
    a, e = 8.0e6, 0.3
    rp = a * (1.0 - e)
    vp = math.sqrt(MU_EARTH * (2.0 / rp - 1.0 / a))
    period = tr.orbital_period(MU_EARTH, a)
    r0x, r0y, v0x, v0y = propagate(rp, 0.0, 0.0, vp, 0.11 * period, MU_EARTH)
    _roundtrip(r0x, r0y, v0x, v0y, 0.5 * period, MU_EARTH)


def test_recovers_hyperbolic():
    """x > 1 (Lancaster log branch): 1.3x escape speed flyby leg."""
    r = 7.0e6
    v = 1.3 * tr.escape_velocity(MU_EARTH, r)
    _roundtrip(r, 0.0, 0.0, v, 5_000.0, MU_EARTH)


def test_recovers_parabolic_battin_zone():
    """|v| exactly escape -> x = 1 transfer (Battin-series zone)."""
    r = 7.0e6
    vesc = tr.escape_velocity(MU_EARTH, r)
    _roundtrip(r, 0.0, 0.5 * vesc, math.sqrt(0.75) * vesc, 2_000.0,
               MU_EARTH)


def test_recovers_retrograde():
    """Clockwise orbit (s = -1) needs prograde=False — the classical
    'long way' is the retrograde solution in 2D."""
    a, e = 8.0e6, 0.3
    rp = a * (1.0 - e)
    vp = math.sqrt(MU_EARTH * (2.0 / rp - 1.0 / a))
    period = tr.orbital_period(MU_EARTH, a)
    _roundtrip(rp, 0.0, 0.0, -vp, 0.2 * period, MU_EARTH, prograde=False)


def test_sense_of_angular_momentum():
    """prograde=True gives h > 0, prograde=False gives h < 0."""
    r1x, r1y = 7.0e6, 0.0
    r2x, r2y = 0.0, 9.0e6
    v1x, v1y, _, _ = lambert(r1x, r1y, r2x, r2y, 2_500.0, MU_EARTH)
    assert r1x * v1y - r1y * v1x > 0.0
    u1x, u1y, _, _ = lambert(r1x, r1y, r2x, r2y, 2_500.0, MU_EARTH,
                             prograde=False)
    assert r1x * u1y - r1y * u1x < 0.0


def test_continuity_through_180_deg():
    """The solution must vary smoothly across a pi sweep (the planar
    no-singularity claim of 01 §2.4): velocities at 180 deg +/- 0.0057 deg
    bracket the exact-pi solution."""
    r1, r2 = 7.0e6, 9.1e6
    t_h = tr.hohmann(MU_EARTH, r1, r2)[2]
    sols = []
    for th in (math.pi - 1e-4, math.pi, math.pi + 1e-4):
        v = lambert(r1, 0.0, r2 * math.cos(th), r2 * math.sin(th),
                    t_h, MU_EARTH)
        sols.append(v)
    for k in range(4):
        assert abs(sols[0][k] - sols[1][k]) < 20.0
        assert abs(sols[1][k] - sols[2][k]) < 20.0


# ---- (c) round-trip mirror ------------------------------------------------

def test_time_reversal_mirror():
    """Solving 1->2 then 2->1 over the same tof mirrors the velocities:
    v1' = -v2, v2' = -v1 (time reversal flips the orbital sense, so the
    return solve is the retrograde branch)."""
    r1x, r1y = 7.0e6, 1.0e6
    r2x, r2y = -2.0e6, 9.0e6
    tof = 3_000.0
    v1x, v1y, v2x, v2y = lambert(r1x, r1y, r2x, r2y, tof, MU_EARTH)
    u1x, u1y, u2x, u2y = lambert(r2x, r2y, r1x, r1y, tof, MU_EARTH,
                                 prograde=False)
    assert u1x == pytest.approx(-v2x, rel=1e-9, abs=1e-6)
    assert u1y == pytest.approx(-v2y, rel=1e-9, abs=1e-6)
    assert u2x == pytest.approx(-v1x, rel=1e-9, abs=1e-6)
    assert u2y == pytest.approx(-v1y, rel=1e-9, abs=1e-6)
    assert math.hypot(u1x, u1y) == pytest.approx(math.hypot(v2x, v2y),
                                                 rel=1e-9)


# ---- (b) Earth -> Mars canon chain (01 §2.6 / §1.3, MUST reproduce) -------

def test_earth_mars_canon_chain():
    """§2.6 worked example via the Lambert/window helpers: transfer 259 d,
    departure phase 44.3 deg, v_inf 2.95/2.65 km/s, TMI from LEO-300 =
    3,590 m/s (Oberth chain through transfers.departure_dv)."""
    a_m = MARS_A_AU * AU
    _, _, t_h = tr.hohmann(MU_SUN, AU, a_m)
    assert t_h / SECONDS_PER_DAY == pytest.approx(258.9, abs=0.5)

    n_m = math.sqrt(MU_SUN / a_m ** 3)
    phase_req = math.pi - n_m * t_h          # §2.3 departure phase formula
    assert math.degrees(phase_req) == pytest.approx(44.3, abs=0.5)

    earth = _circular(MU_SUN, AU, 0.0)
    mars = _circular(MU_SUN, a_m, phase_req)  # arrival lands at exactly pi
    vinf_dep, vinf_arr = transfer_vinfs(MU_SUN, earth, mars, 0.0, t_h)
    assert vinf_dep == pytest.approx(2_945, abs=15)     # canon 2.95 km/s
    assert vinf_arr == pytest.approx(2_650, abs=15)     # canon 2.65 km/s
    dv_tmi = tr.departure_dv(MU_EARTH, R_LEO300, vinf_dep)
    assert dv_tmi == pytest.approx(3_591, abs=15)       # canon R1 3,590


def test_earth_venus_canon_row():
    """§1.3 Venus row: 146 d transfer, v_inf 2.50 dep / 2.71 arr km/s,
    departure phase -54.0 deg (Venus trails)."""
    _, _, t_h = tr.hohmann(MU_SUN, AU, VENUS_A)
    assert t_h / SECONDS_PER_DAY == pytest.approx(146.0, abs=1.0)

    n_v = math.sqrt(MU_SUN / VENUS_A ** 3)
    phase_req = math.pi - n_v * t_h
    assert math.degrees(phase_req) == pytest.approx(-54.0, abs=0.5)

    earth = _circular(MU_SUN, AU, 0.0)
    venus = _circular(MU_SUN, VENUS_A, phase_req)
    vinf_dep, vinf_arr = transfer_vinfs(MU_SUN, earth, venus, 0.0, t_h)
    assert vinf_dep == pytest.approx(2_500, abs=20)
    assert vinf_arr == pytest.approx(2_710, abs=20)


def test_porkchop_minimum_earth_mars():
    """Porkchop minimum for circular-coplanar Earth/Mars must land within
    15% of the Hohmann dv and ~259 d ToF (the _transfer_window canon in
    main.py), and can never beat the Hohmann optimum."""
    a_m = MARS_A_AU * AU
    dv1_h, dv2_h, t_h = tr.hohmann(MU_SUN, AU, a_m)
    hohmann_sum = dv1_h + dv2_h

    earth = _circular(MU_SUN, AU, 0.0)
    mars = _circular(MU_SUN, a_m, math.radians(60.0))   # 60 deg ahead
    # phase decays at n_M - n_E toward the 44.3 deg window -> ~34 d wait
    n_e = math.sqrt(MU_SUN / AU ** 3)
    n_m = math.sqrt(MU_SUN / a_m ** 3)
    wait_pred = (math.radians(60.0) - (math.pi - n_m * t_h)) / (n_e - n_m)

    t_dep, tof, dv_tot = best_window(
        MU_SUN, earth, mars,
        (0.0, 120.0 * SECONDS_PER_DAY),
        (170.0 * SECONDS_PER_DAY, 350.0 * SECONDS_PER_DAY),
        n_grid=(41, 31))
    assert dv_tot <= 1.15 * hohmann_sum                 # within ~15%
    assert dv_tot >= 0.999 * hohmann_sum                # Hohmann is optimal
    assert tof == pytest.approx(t_h, rel=0.15)          # ~259 d canon
    assert tof / SECONDS_PER_DAY == pytest.approx(258.9, rel=0.15)
    assert t_dep == pytest.approx(wait_pred, abs=10.0 * SECONDS_PER_DAY)


def test_porkchop_grid_shape_and_helpers():
    """Grid layout contract: [i, j] <-> (t_depart[i], tof[j]); dv_total =
    dv_depart + dv_arrive; cells match the scalar UI helpers."""
    earth = _circular(MU_SUN, AU, 0.0)
    mars = _circular(MU_SUN, MARS_A_AU * AU, math.radians(60.0))
    grid = porkchop(MU_SUN, earth, mars,
                    (0.0, 60.0 * SECONDS_PER_DAY),
                    (200.0 * SECONDS_PER_DAY, 300.0 * SECONDS_PER_DAY),
                    n_grid=(5, 4))
    assert isinstance(grid, PorkchopGrid)
    assert grid.t_depart.shape == (5,)
    assert grid.tof.shape == (4,)
    assert grid.dv_depart.shape == (5, 4)
    assert grid.dv_arrive.shape == (5, 4)
    assert np.all(np.isfinite(grid.dv_total))
    assert np.allclose(grid.dv_total, grid.dv_depart + grid.dv_arrive)
    t0, tf = float(grid.t_depart[2]), float(grid.tof[1])
    assert grid.dv_depart[2, 1] == pytest.approx(
        dv_depart(MU_SUN, earth, mars, t0, tf), rel=1e-12)
    assert grid.dv_arrive[2, 1] == pytest.approx(
        dv_arrive(MU_SUN, earth, mars, t0, tf), rel=1e-12)
    # best_window agrees with a manual argmin of the same grid
    t_dep, tof, dv_tot = best_window(
        MU_SUN, earth, mars,
        (0.0, 60.0 * SECONDS_PER_DAY),
        (200.0 * SECONDS_PER_DAY, 300.0 * SECONDS_PER_DAY),
        n_grid=(5, 4))
    k = int(np.argmin(grid.dv_total))
    i, j = divmod(k, grid.tof.size)
    assert t_dep == float(grid.t_depart[i])
    assert tof == float(grid.tof[j])
    assert dv_tot == pytest.approx(float(grid.dv_total[i, j]), rel=1e-12)


# ---- ill-posed inputs (01 §2.4: exactly 0/360 deg only) -------------------

def test_zero_sweep_and_bad_args_raise():
    with pytest.raises(ValueError):
        lambert(7.0e6, 0.0, 1.4e7, 0.0, 1_000.0, MU_EARTH)   # 0 deg sweep
    with pytest.raises(ValueError):
        lambert(7.0e6, 0.0, 7.0e6, 0.0, 1_000.0, MU_EARTH)   # same point
    with pytest.raises(ValueError):
        lambert(7.0e6, 0.0, -7.0e6, 1.0e6, -10.0, MU_EARTH)  # tof <= 0
    with pytest.raises(ValueError):
        lambert(7.0e6, 0.0, -7.0e6, 1.0e6, 1_000.0, 0.0)     # mu <= 0
