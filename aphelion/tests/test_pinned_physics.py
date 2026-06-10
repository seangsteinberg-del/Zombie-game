"""Pinned physics CI tests — every row of 13-architecture.md §4.7 that the
orbits modules cover. Constants are NASA fact-sheet values (the bible's
anchors); radii per row conventions (LEO-300 uses r = 6,678 km per 01 §3.8,
the ISS row uses volumetric-mean 6,371 + 400 km).
"""

import math

import numpy as np
import pytest

from aphelion.core.units import AU, SECONDS_PER_DAY
from aphelion.sim.orbits.kepler import (
    Elements,
    elements_to_state,
    propagate,
    propagate_batch,
    state_to_elements,
)
from aphelion.sim.orbits import transfers as tr

MU_SUN = 1.327_124_400_18e20
MU_EARTH = 3.986_004_418e14
MU_MOON = 4.9028e12
MU_MARS = 4.282_837e13
MU_JUPITER = 1.266_865_34e17

R_EARTH = 6.371e6
R_MOON = 1.7374e6
R_MARS = 3.3895e6

R_LEO300 = 6.678e6          # 01 §3.8 canonical parking orbit radius
R_ISS = R_EARTH + 4.00e5    # volumetric-mean + 400 km per pinned row
R_MOON_ORBIT = 3.844e8
GEO_PERIOD = 86_164.1       # sidereal day, s
MARS_A_AU = 1.5237


# ---- escape velocities -------------------------------------------------

def test_earth_escape_velocity():
    assert tr.escape_velocity(MU_EARTH, R_EARTH) == pytest.approx(11_186, abs=1)


def test_moon_escape_velocity():
    assert tr.escape_velocity(MU_MOON, R_MOON) == pytest.approx(2_376, abs=1)


def test_mars_escape_velocity():
    assert tr.escape_velocity(MU_MARS, R_MARS) == pytest.approx(5_027, abs=1)


# ---- circular orbits ---------------------------------------------------

def test_leo300_circular_speed():
    assert tr.circular_speed(MU_EARTH, R_LEO300) == pytest.approx(7_726, abs=1)


def test_leo300_period():
    assert tr.orbital_period(MU_EARTH, R_LEO300) == pytest.approx(5_431, abs=1)


def test_iss_period():
    assert tr.orbital_period(MU_EARTH, R_ISS) == pytest.approx(5_545, abs=5)


def test_geo_semi_major_axis():
    assert tr.sma_from_period(MU_EARTH, GEO_PERIOD) == pytest.approx(4.2164e7, abs=1e3)


# ---- Hohmann LEO -> GEO ------------------------------------------------

def test_hohmann_leo_to_geo_dv():
    r_geo = tr.sma_from_period(MU_EARTH, GEO_PERIOD)
    dv1, dv2, _ = tr.hohmann(MU_EARTH, R_LEO300, r_geo)
    assert dv1 + dv2 == pytest.approx(3_893, abs=5)


def test_hohmann_leo_to_geo_time():
    r_geo = tr.sma_from_period(MU_EARTH, GEO_PERIOD)
    _, _, t = tr.hohmann(MU_EARTH, R_LEO300, r_geo)
    assert t == pytest.approx(18_986, abs=30)


def test_tli_dv():
    dv1, _, _ = tr.hohmann(MU_EARTH, R_LEO300, R_MOON_ORBIT)
    assert dv1 == pytest.approx(3_107, abs=10)


# ---- Earth -> Mars (01 §3.8 worked example) ----------------------------

def test_earth_mars_transfer_time():
    _, _, t = tr.hohmann(MU_SUN, AU, MARS_A_AU * AU)
    assert t / SECONDS_PER_DAY == pytest.approx(258.9, abs=0.5)


def test_earth_mars_departure_vinf():
    vinf = tr.hohmann_departure_vinf(MU_SUN, AU, MARS_A_AU * AU)
    assert vinf == pytest.approx(2_945, abs=10)


def test_tmi_dv_from_leo300():
    vinf = tr.hohmann_departure_vinf(MU_SUN, AU, MARS_A_AU * AU)
    dv = tr.departure_dv(MU_EARTH, R_LEO300, vinf)
    assert dv == pytest.approx(3_591, abs=10)


def test_earth_mars_synodic_period():
    t_e = tr.orbital_period(MU_SUN, AU)
    t_m = tr.orbital_period(MU_SUN, MARS_A_AU * AU)
    syn = tr.synodic_period(t_e, t_m)
    assert syn / SECONDS_PER_DAY == pytest.approx(779.9, abs=0.5)


# ---- flyby (01 §3.9 worked example) ------------------------------------

def test_jupiter_flyby_deflection():
    delta = tr.flyby_deflection(MU_JUPITER, 5_640.0, 2.0e8)
    assert math.degrees(delta) == pytest.approx(144.0, abs=1.0)


# ---- universal-variable propagator -------------------------------------

def test_kepler_closure_100_periods_e09():
    """Pinned: propagate 100 periods of an e=0.9 ellipse, return to start
    within 1e-3 m — closed form, error must not grow with dt."""
    a = 7.0e7
    e = 0.9
    rp = a * (1.0 - e)
    vp = math.sqrt(MU_EARTH * (2.0 / rp - 1.0 / a))
    period = tr.orbital_period(MU_EARTH, a)
    rx, ry, vx, vy = propagate(rp, 0.0, 0.0, vp, 100.0 * period, MU_EARTH)
    assert math.hypot(rx - rp, ry - 0.0) < 1e-3
    assert math.hypot(vx - 0.0, vy - vp) < 1e-6


def test_propagate_quarter_period_circular():
    r = R_LEO300
    v = tr.circular_speed(MU_EARTH, r)
    t_quarter = tr.orbital_period(MU_EARTH, r) / 4.0
    rx, ry, vx, vy = propagate(r, 0.0, 0.0, v, t_quarter, MU_EARTH)
    assert rx == pytest.approx(0.0, abs=1e-3)
    assert ry == pytest.approx(r, abs=1e-3)
    assert vx == pytest.approx(-v, abs=1e-6)
    assert vy == pytest.approx(0.0, abs=1e-6)


def test_propagate_hyperbolic_energy_conserved():
    r0 = 1.0e7
    v0 = 1.2 * tr.escape_velocity(MU_EARTH, r0)
    v0x, v0y = 0.3 * v0, 0.954 * v0
    eps0 = 0.5 * (v0x * v0x + v0y * v0y) - MU_EARTH / r0
    rx, ry, vx, vy = propagate(r0, 0.0, v0x, v0y, 5.0e5, MU_EARTH)
    r = math.hypot(rx, ry)
    v2 = vx * vx + vy * vy
    eps = 0.5 * v2 - MU_EARTH / r
    assert eps == pytest.approx(eps0, rel=1e-12)


def test_propagate_negative_dt_inverts():
    r = R_LEO300
    v = tr.circular_speed(MU_EARTH, r)
    rx, ry, vx, vy = propagate(r, 0.0, 0.0, v, 1234.5, MU_EARTH)
    bx, by, bvx, bvy = propagate(rx, ry, vx, vy, -1234.5, MU_EARTH)
    assert bx == pytest.approx(r, abs=1e-6)
    assert by == pytest.approx(0.0, abs=1e-6)
    assert bvx == pytest.approx(0.0, abs=1e-9)
    assert bvy == pytest.approx(v, abs=1e-9)


# ---- batch propagator consistency --------------------------------------

def _orbit_zoo() -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(42)
    n = 256
    r0 = np.empty((n, 2))
    v0 = np.empty((n, 2))
    for i in range(n):
        r = 10 ** rng.uniform(6.9, 9.0)
        ang = rng.uniform(0.0, 2.0 * math.pi)
        v_circ = math.sqrt(MU_EARTH / r)
        speed = v_circ * rng.uniform(0.7, 1.45)   # ellipses through hyperbolas
        flight_path = rng.uniform(-0.5, 0.5)
        sense = 1.0 if rng.uniform() < 0.8 else -1.0
        r0[i] = (r * math.cos(ang), r * math.sin(ang))
        tx, ty = -math.sin(ang) * sense, math.cos(ang) * sense
        rx_hat, ry_hat = math.cos(ang), math.sin(ang)
        v0[i] = (speed * (tx * math.cos(flight_path) + rx_hat * math.sin(flight_path)),
                 speed * (ty * math.cos(flight_path) + ry_hat * math.sin(flight_path)))
    return r0, v0


def test_batch_matches_scalar():
    r0, v0 = _orbit_zoo()
    dt = 7_200.0
    r_b, v_b = propagate_batch(r0, v0, dt, MU_EARTH)
    for i in range(r0.shape[0]):
        rx, ry, vx, vy = propagate(r0[i, 0], r0[i, 1], v0[i, 0], v0[i, 1], dt, MU_EARTH)
        assert r_b[i, 0] == pytest.approx(rx, rel=1e-10, abs=1e-3)
        assert r_b[i, 1] == pytest.approx(ry, rel=1e-10, abs=1e-3)
        assert v_b[i, 0] == pytest.approx(vx, rel=1e-10, abs=1e-6)
        assert v_b[i, 1] == pytest.approx(vy, rel=1e-10, abs=1e-6)


def test_batch_2000_objects_perf_budget():
    """13 §4.6: 2,000 rails objects in < 0.5 ms; CI asserts x3 slack (1.5 ms).
    Measured as best-of-5 to dodge scheduler noise."""
    import time

    rng = np.random.default_rng(7)
    n = 2_000
    r = 10 ** rng.uniform(6.9, 8.5, n)
    ang = rng.uniform(0.0, 2.0 * math.pi, n)
    v_circ = np.sqrt(MU_EARTH / r)
    speed = v_circ * rng.uniform(0.8, 1.2, n)
    r0 = np.stack([r * np.cos(ang), r * np.sin(ang)], axis=1)
    v0 = np.stack([-speed * np.sin(ang), speed * np.cos(ang)], axis=1)

    propagate_batch(r0, v0, 60.0, MU_EARTH)   # warm-up
    best = math.inf
    for _ in range(5):
        t0 = time.perf_counter()
        propagate_batch(r0, v0, 3_600.0, MU_EARTH)
        best = min(best, time.perf_counter() - t0)
    assert best < 1.5e-3


# ---- element conversions ------------------------------------------------

def test_elements_roundtrip_zoo():
    r0, v0 = _orbit_zoo()
    t0 = 1.0e6
    for i in range(0, r0.shape[0], 7):
        el = state_to_elements(r0[i, 0], r0[i, 1], v0[i, 0], v0[i, 1], t0, MU_EARTH)
        rx, ry, vx, vy = elements_to_state(el, t0)
        scale_r = math.hypot(r0[i, 0], r0[i, 1])
        scale_v = math.hypot(v0[i, 0], v0[i, 1])
        assert math.hypot(rx - r0[i, 0], ry - r0[i, 1]) < 1e-6 * scale_r
        assert math.hypot(vx - v0[i, 0], vy - v0[i, 1]) < 1e-6 * scale_v


def test_elements_period_property():
    el = state_to_elements(R_LEO300, 0.0, 0.0, tr.circular_speed(MU_EARTH, R_LEO300),
                           0.0, MU_EARTH)
    assert el.period == pytest.approx(5_431, abs=1)
    assert el.e == pytest.approx(0.0, abs=1e-10)
    assert el.s == 1.0


def test_elements_retrograde_sense():
    el = state_to_elements(R_LEO300, 0.0, 0.0, -tr.circular_speed(MU_EARTH, R_LEO300),
                           0.0, MU_EARTH)
    assert el.s == -1.0
    rx, ry, vx, vy = elements_to_state(el, 100.0)
    # Retrograde: y goes negative as time advances from +x axis.
    assert ry < 0.0
