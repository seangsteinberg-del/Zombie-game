"""Tests for frames/SOI/flight/nodes — 01 §3.4/3.5/3.7 + 13 §3.6/3.7/3.8,
including the pinned RK4 energy-drift row from 13 §4.7."""

import math

import numpy as np
import pytest

from aphelion.core.units import AU, G0, SIM_DT
from aphelion.sim.flight.integrator import (
    COAST,
    FlightIntegrator,
    fixed_direction_guidance,
)
from aphelion.sim.flight.node_exec import (
    ManeuverNode,
    apply_node_impulsive,
    burn_time,
    exhaust_velocity,
    ignition_time,
    impulsive_warning,
)
from aphelion.sim.orbits import transfers as tr
from aphelion.sim.orbits.frames import Body, FrameTree
from aphelion.sim.orbits.kepler import Elements, elements_to_state, state_to_elements
from aphelion.sim.orbits.soi import (
    effective_soi,
    predict_entry,
    predict_exit,
    soi_radius,
    time_to_radius,
)

MU_SUN = 1.327_124_400_18e20
MU_EARTH = 3.986_004_418e14
MU_MOON = 4.9028e12

M_SUN = 1.989e30
M_EARTH = 5.972e24
M_MOON = 7.346e22

R_LEO300 = 6.678e6
R_MOON_ORBIT = 3.844e8
EARTH_SOI = soi_radius(AU, M_EARTH, M_SUN)


# ---- SOI radii (01 §3.4) -------------------------------------------------

def test_earth_soi_radius():
    assert EARTH_SOI == pytest.approx(9.24e8, rel=0.01)


def test_moon_soi_radius():
    assert soi_radius(R_MOON_ORBIT, M_MOON, M_EARTH) == pytest.approx(6.62e7, rel=0.01)


def test_soi_floor_rule_phobos():
    # Phobos: a = 9,376 km, m = 1.0659e16 kg, R = 11.08 km -> no SOI
    assert effective_soi(9.376e6, 1.0659e16, 6.4171e23, 1.108e4) == 0.0


# ---- time_to_radius -------------------------------------------------------

def _tli_ellipse() -> Elements:
    """Periapsis 6,678 km, apoapsis 384,400 km, periapsis at t=0, varpi=0."""
    a = 0.5 * (R_LEO300 + R_MOON_ORBIT)
    vp = math.sqrt(MU_EARTH * (2.0 / R_LEO300 - 1.0 / a))
    return state_to_elements(R_LEO300, 0.0, 0.0, vp, 0.0, MU_EARTH)


def test_time_to_radius_outbound():
    el = _tli_ellipse()
    t = time_to_radius(el, 3.0e8, 0.0)
    assert t is not None
    rx, ry, _, _ = elements_to_state(el, t)
    assert math.hypot(rx, ry) == pytest.approx(3.0e8, rel=1e-9)


def test_time_to_radius_unreachable_and_circular():
    el = _tli_ellipse()
    assert time_to_radius(el, 5.0e8, 0.0) is None        # beyond apoapsis
    circ = state_to_elements(R_LEO300, 0.0, 0.0, tr.circular_speed(MU_EARTH, R_LEO300),
                             0.0, MU_EARTH)
    assert time_to_radius(circ, 1.0e7, 0.0) is None


# ---- SOI crossing prediction (01 §3.4, 13 §3.8) ---------------------------

def test_predict_moon_entry_on_tli():
    craft = _tli_ellipse()
    t_apo = craft.period / 2.0
    n_moon = math.sqrt(MU_EARTH / R_MOON_ORBIT ** 3)
    v_moon = math.sqrt(MU_EARTH / R_MOON_ORBIT)
    # Moon circular, phased to sit at angle pi when the craft reaches apoapsis
    tau_moon = t_apo - math.pi / n_moon
    moon = state_to_elements(R_MOON_ORBIT, 0.0, 0.0, v_moon, tau_moon, MU_EARTH)
    r_soi = soi_radius(R_MOON_ORBIT, M_MOON, M_EARTH)

    crossing = predict_entry(craft, moon, r_soi, "moon", 0.0, craft.period)
    assert crossing is not None and crossing.entering
    assert crossing.t_cross < t_apo
    crx, cry, _, _ = elements_to_state(craft, crossing.t_cross)
    mrx, mry, _, _ = elements_to_state(moon, crossing.t_cross)
    gap = math.hypot(crx - mrx, cry - mry) - r_soi
    assert abs(gap) < 5_000.0     # ±1 s refinement at ~km/s closing speed


def test_predict_exit_on_escape_hyperbola():
    v_esc = tr.escape_velocity(MU_EARTH, R_LEO300)
    craft = state_to_elements(R_LEO300, 0.0, 0.0, 1.1 * v_esc, 0.0, MU_EARTH)
    crossing = predict_exit(craft, EARTH_SOI, "earth", 0.0, 1.0e7)
    assert crossing is not None and not crossing.entering
    rx, ry, _, _ = elements_to_state(craft, crossing.t_cross)
    assert math.hypot(rx, ry) == pytest.approx(EARTH_SOI, rel=1e-6)


def test_predict_entry_no_encounter():
    craft = state_to_elements(R_LEO300, 0.0, 0.0, tr.circular_speed(MU_EARTH, R_LEO300),
                              0.0, MU_EARTH)   # stays in LEO
    v_moon = math.sqrt(MU_EARTH / R_MOON_ORBIT)
    moon = state_to_elements(R_MOON_ORBIT, 0.0, 0.0, v_moon, 0.0, MU_EARTH)
    r_soi = soi_radius(R_MOON_ORBIT, M_MOON, M_EARTH)
    assert predict_entry(craft, moon, r_soi, "moon", 0.0, 30.0 * 86_400.0) is None


# ---- frame tree (13 §3.7) -------------------------------------------------

def _mini_system() -> FrameTree:
    tree = FrameTree()
    tree.add(Body("sun", MU_SUN, 6.957e8, None, None, math.inf))
    v_e = math.sqrt(MU_SUN / AU)
    earth_el = state_to_elements(AU, 0.0, 0.0, v_e, 0.0, MU_SUN)
    tree.add(Body("earth", MU_EARTH, 6.371e6, "sun", earth_el, EARTH_SOI))
    v_m = math.sqrt(MU_EARTH / R_MOON_ORBIT)
    moon_el = state_to_elements(R_MOON_ORBIT, 0.0, 0.0, v_m, 0.0, MU_EARTH)
    tree.add(Body("moon", MU_MOON, 1.7374e6, "earth", moon_el,
                  soi_radius(R_MOON_ORBIT, M_MOON, M_EARTH)))
    return tree


def test_frame_chain_and_composition():
    tree = _mini_system()
    assert tree.chain("moon") == ["sun", "earth", "moon"]
    t = 1.0e6
    erx, ery, evx, evy = tree.state_in_parent("earth", t)
    mrx, mry, mvx, mvy = tree.state_in_parent("moon", t)
    rx, ry, vx, vy = tree.state_in_root("moon", t)
    assert rx == pytest.approx(erx + mrx) and ry == pytest.approx(ery + mry)
    assert vx == pytest.approx(evx + mvx) and vy == pytest.approx(evy + mvy)


def test_frame_soi_reexpression_roundtrip():
    tree = _mini_system()
    t = 5.0e5
    state = (1.0e8, -2.0e7, 500.0, 900.0)   # craft in Earth frame
    in_moon = tree.to_child_frame(state, "moon", t)
    back = tree.to_parent_frame(in_moon, "moon", t)
    for got, want in zip(back, state):
        assert got == pytest.approx(want, rel=1e-12)


# ---- flight integrator (pinned row: RK4 energy drift) ----------------------

def test_rk4_circular_orbit_energy_drift_per_orbit():
    """13 §4.7: RK4 circular-orbit energy drift @ dt=0.02 < 1e-10 rel/orbit."""
    r = R_LEO300
    v = tr.circular_speed(MU_EARTH, r)
    period = tr.orbital_period(MU_EARTH, r)
    y = np.array([r, 0.0, 0.0, v, 1_000.0])
    eps0 = 0.5 * v * v - MU_EARTH / r
    integ = FlightIntegrator(MU_EARTH, COAST)
    _, y = integ.run_for(0.0, y, period)
    rn = math.hypot(y[0], y[1])
    eps = 0.5 * (y[2] ** 2 + y[3] ** 2) - MU_EARTH / rn
    assert abs((eps - eps0) / eps0) < 1e-10


def test_integrated_burn_matches_tsiolkovsky():
    m0, thrust, isp = 1_000.0, 1_000.0, 300.0
    ve = exhaust_velocity(isp)
    y = np.array([1.0e12, 0.0, 0.0, 0.0, m0])
    integ = FlightIntegrator(1.0, fixed_direction_guidance(thrust, isp, 0.0, 1.0))
    _, y = integ.run_for(0.0, y, 100.0)
    m1 = y[4]
    assert m1 == pytest.approx(m0 - thrust / ve * 100.0, rel=1e-12)
    dv_expected = ve * math.log(m0 / m1)
    assert math.hypot(y[2], y[3]) == pytest.approx(dv_expected, rel=1e-9)


# ---- maneuver nodes (01 §3.7) ----------------------------------------------

def test_node_prograde_burn_reaches_geo_apoapsis():
    r_geo = tr.sma_from_period(MU_EARTH, 86_164.1)
    dv1, _, _ = tr.hohmann(MU_EARTH, R_LEO300, r_geo)
    circ = state_to_elements(R_LEO300, 0.0, 0.0, tr.circular_speed(MU_EARTH, R_LEO300),
                             0.0, MU_EARTH)
    after = apply_node_impulsive(circ, ManeuverNode(t_node=0.0, dv_prograde=dv1))
    assert after.apoapsis == pytest.approx(r_geo, rel=1e-9)
    assert after.periapsis == pytest.approx(R_LEO300, rel=1e-9)


def test_node_retrograde_lowers_orbit():
    circ = state_to_elements(R_LEO300, 0.0, 0.0, tr.circular_speed(MU_EARTH, R_LEO300),
                             0.0, MU_EARTH)
    after = apply_node_impulsive(circ, ManeuverNode(t_node=100.0, dv_prograde=-50.0))
    assert after.periapsis < R_LEO300
    assert after.apoapsis == pytest.approx(R_LEO300, rel=1e-6)


def test_burn_time_tsiolkovsky_identity():
    m0, thrust, isp, dv = 10_000.0, 100_000.0, 300.0, 100.0
    ve = exhaust_velocity(isp)
    t_b = burn_time(m0, thrust, isp, dv)
    m1 = m0 - (thrust / ve) * t_b
    assert ve * math.log(m0 / m1) == pytest.approx(dv, rel=1e-12)


def test_ignition_centered_and_impulsive_warning():
    node = ManeuverNode(t_node=1_000.0, dv_prograde=100.0)
    m0, thrust, isp = 10_000.0, 100_000.0, 300.0
    t_b = burn_time(m0, thrust, isp, node.dv_total)
    assert ignition_time(node, m0, thrust, isp) == pytest.approx(1_000.0 - t_b / 2.0)
    # 9.8 s burn: fine on a 5,431 s orbit, "breaking down" on a 50 s orbit
    assert not impulsive_warning(node, m0, thrust, isp, orbit_period=5_431.0)
    assert impulsive_warning(node, m0, thrust, isp, orbit_period=50.0)
