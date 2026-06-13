"""Finite burns + thrust-under-warp (01 §1.9/§1.15/§1.16/§2.9): RKF4(5)
zero-thrust conservation over 10 orbits, the warp max-step and
a_thrust*dt <= 1 m/s caps, high-thrust convergence to the impulsive node,
the low-thrust Edelbaum spiral, exact rocket-equation mass depletion, and
the spec's pinned numbers (g0 = 9.80665 exactly, rel tol 1e-9, centered
ignition, t_b/m_prop worked example)."""

import math

import numpy as np
import pytest

from aphelion.core.units import G0
from aphelion.sim.flight.node_exec import (
    ManeuverNode,
    apply_node_impulsive,
    burn_time,
)
from aphelion.sim.orbits.finite_burn import (
    RKF_REL_TOL,
    WARP_DV_CAP_MPS,
    burn_arc,
    integrate_rkf45,
    node_to_finite,
    specific_ang_momentum,
    specific_energy,
    two_body_thrust,
)
from aphelion.sim.orbits.kepler import elements_to_state, state_to_elements

MU_EARTH = 3.986_004_418e14
R_LEO300 = 6.678e6                       # LEO 300 km radius, m
V_LEO300 = math.sqrt(MU_EARTH / R_LEO300)
M0 = 10_000.0


def _leo_circular():
    return state_to_elements(R_LEO300, 0.0, 0.0, V_LEO300, 0.0, MU_EARTH)


def _sma(samples: np.ndarray) -> np.ndarray:
    """Osculating semi-major axis at each sample row (vis-viva, 01 §2.1)."""
    r = np.hypot(samples[:, 1], samples[:, 2])
    v2 = samples[:, 3] ** 2 + samples[:, 4] ** 2
    return 1.0 / (2.0 / r - v2 / MU_EARTH)


# ---- (a) zero-thrust conservation: the adaptive-step proof -----------------

def test_zero_thrust_conserves_energy_and_h_10_orbits():
    """01 §1.16 RKF4(5): a 10-orbit e = 0.5 coast must hold specific energy
    and angular momentum to 1e-9 rel at EVERY accepted step. The spec's
    1e-9 is the local per-step tolerance; hitting a 1e-9 GLOBAL bar over
    ~5,000 steps needs local 1e-12 (local extrapolation leaves ~4x margin)."""
    rp, e = R_LEO300, 0.5
    a = rp / (1.0 - e)
    vp = math.sqrt(MU_EARTH * (2.0 / rp - 1.0 / a))
    period = 2.0 * math.pi * math.sqrt(a ** 3 / MU_EARTH)

    y0 = np.array([rp, 0.0, 0.0, vp, M0])
    ref = np.array([rp, rp, vp, vp, M0])
    f = two_body_thrust(MU_EARTH, 0.0, 0.0)          # pure two-body
    yf, s = integrate_rkf45(f, 0.0, y0, 10.0 * period, rtol=1e-12, ref=ref)

    e0 = specific_energy(rp, 0.0, 0.0, vp, MU_EARTH)
    h0 = specific_ang_momentum(rp, 0.0, 0.0, vp)
    en = 0.5 * (s[:, 3] ** 2 + s[:, 4] ** 2) - MU_EARTH / np.hypot(s[:, 1], s[:, 2])
    hh = s[:, 1] * s[:, 4] - s[:, 2] * s[:, 3]
    assert np.max(np.abs(en - e0)) / abs(e0) < 1e-9
    assert np.max(np.abs(hh - h0)) / abs(h0) < 1e-9

    # Adaptive proof: steps stretch at apoapsis, shrink at periapsis
    # (r_a/r_p = 3 -> local dynamical time ratio 3^1.5 ~ 5.2).
    dt = np.diff(s[:, 0])
    assert dt.max() / dt.min() > 4.0

    # Endpoint agrees with the exact universal-Kepler propagation.
    el = state_to_elements(rp, 0.0, 0.0, vp, 0.0, MU_EARTH)
    rx, ry, vx, vy = elements_to_state(el, 10.0 * period)
    assert math.hypot(yf[0] - rx, yf[1] - ry) / math.hypot(rx, ry) < 1e-6
    assert yf[4] == M0                                # no flow at zero thrust


def test_max_step_parameter_caps_warp_steps():
    """The warp ladder hands the integrator a max-step (01 §1.9): every
    accepted step obeys it and accuracy is unharmed."""
    y0 = np.array([R_LEO300, 0.0, 0.0, V_LEO300, M0])
    ref = np.array([R_LEO300, R_LEO300, V_LEO300, V_LEO300, M0])
    period = 2.0 * math.pi * math.sqrt(R_LEO300 ** 3 / MU_EARTH)
    f = two_body_thrust(MU_EARTH, 0.0, 0.0)
    yf, s = integrate_rkf45(f, 0.0, y0, period, max_step=10.0, ref=ref)
    assert np.diff(s[:, 0]).max() <= 10.0 * (1.0 + 1e-12)
    # One full circular period returns to the start.
    assert math.hypot(yf[0] - R_LEO300, yf[1]) / R_LEO300 < 1e-6


# ---- (b) high thrust converges to the impulsive node -----------------------

def test_high_thrust_burn_converges_to_impulsive():
    """500 kN on 10 t (t_b ~ 2 s << T/6): the centered finite burn must
    reproduce the impulsive plan — dv within 0.1%, post-burn elements
    within 0.5% of apply_node_impulsive (01 §1.15)."""
    el = _leo_circular()
    t_node = el.period / 4.0
    dv = 100.0
    fn = node_to_finite(el, MU_EARTH, dv, 500e3, 300.0, M0, t_node)

    # Duration from the rocket equation, parity with flight.node_exec.
    assert fn.duration_s == pytest.approx(
        burn_time(M0, 500e3, 300.0, dv), rel=1e-12)
    assert fn.t_ignite == pytest.approx(t_node - 0.5 * fn.duration_s)
    assert fn.lead_s == pytest.approx(0.5 * fn.duration_s)

    # Achieved dv (Tsiolkovsky from integrated mass) within 0.1%.
    ve = 300.0 * G0
    assert ve * math.log(M0 / fn.m_final) == pytest.approx(dv, rel=1e-3)
    # Burnout velocity within the executor trim threshold (01 §1.15
    # "trims to +/-0.1 m/s") of the impulsive target = 0.1% of 100 m/s.
    assert fn.residual_dv_mps < 0.1

    imp = apply_node_impulsive(el, ManeuverNode(t_node, dv))
    assert fn.elements.a == pytest.approx(imp.a, rel=5e-3)
    assert fn.elements.e == pytest.approx(imp.e, rel=5e-3)
    assert fn.elements.apoapsis == pytest.approx(imp.apoapsis, rel=5e-3)
    # The module's inline impulsive target is exactly node_exec's.
    assert fn.target.a == pytest.approx(imp.a, rel=1e-12)
    assert fn.target.e == pytest.approx(imp.e, rel=1e-12, abs=1e-15)
    assert fn.target.varpi == pytest.approx(imp.varpi, rel=1e-12)


def test_retrograde_node_lowers_orbit():
    """Signed prograde channel: dv < 0 steers retrograde and sheds energy."""
    el = _leo_circular()
    fn = node_to_finite(el, MU_EARTH, -50.0, 500e3, 300.0, M0,
                        el.period / 3.0)
    assert fn.elements.a < el.a
    assert fn.residual_dv_mps < 0.1
    imp = apply_node_impulsive(el, ManeuverNode(el.period / 3.0, -50.0))
    assert fn.elements.a == pytest.approx(imp.a, rel=5e-3)


# ---- (c) low-thrust spiral (T/W ~ 1e-4) ------------------------------------

def test_low_thrust_spiral_monotonic_and_edelbaum():
    """20-orbit ion spiral, T/W = 1e-4: the orbit rises monotonically and
    the circular-speed drop equals the Tsiolkovsky dv = Isp g0 ln(m0/m1)
    within 1% (Edelbaum, 01 §2.5: dv = |v_c1 - v_c2|)."""
    el = _leo_circular()
    g_local = MU_EARTH / R_LEO300 ** 2          # 01 §1.9 Edelbaum gate term
    thrust = 1e-4 * M0 * g_local                # T/W = 1e-4 (~8.9 N)
    isp = 3000.0
    arc = burn_arc(el, MU_EARTH, 0.0, 20.0 * el.period, thrust, isp, M0,
                   "prograde")

    sma = _sma(arc.samples)
    assert np.all(np.diff(sma) > 0.0)           # monotonic raise
    assert arc.elements.e < 5e-3                # stays near-circular

    dv_spent = isp * G0 * math.log(M0 / arc.m_final)
    v_c1 = math.sqrt(MU_EARTH / el.a)
    v_c2 = math.sqrt(MU_EARTH / arc.elements.a)
    assert v_c1 - v_c2 == pytest.approx(dv_spent, rel=1e-2)
    assert dv_spent > 50.0                      # a real spiral, not a no-op


# ---- (d) mass depletion exact vs rocket equation ---------------------------

def test_mass_depletion_exact_rocket_equation():
    """01 §2.9: t_b makes m_final = m0 e^(-dv/ve) algebraically identical
    to m0 - mdot t_b; the integrator must reproduce it to roundoff (mdot is
    constant, m(t) exactly linear)."""
    el = _leo_circular()
    dv, isp, thrust = 500.0, 320.0, 200e3
    ve = isp * G0
    fn = node_to_finite(el, MU_EARTH, dv, thrust, isp, M0, el.period / 2.0)
    assert fn.m_final == pytest.approx(M0 * math.exp(-dv / ve), rel=1e-12)

    arc = burn_arc(el, MU_EARTH, 0.0, 60.0, thrust, isp, M0)
    assert arc.m_final == pytest.approx(M0 - (thrust / ve) * 60.0, rel=1e-12)


def test_exhaustion_mid_burn_aborts():
    """01 §1.15: exhaustion mid-burn -> abort (duration that would drive
    m <= 0 is refused up front; mdot is constant so m_end is exact)."""
    el = _leo_circular()
    ve = 300.0 * G0
    t_empty = M0 * ve / 500e3                   # m hits zero exactly here
    with pytest.raises(ValueError, match="exhaustion"):
        burn_arc(el, MU_EARTH, 0.0, 1.01 * t_empty, 500e3, 300.0, M0)


# ---- (e) pinned spec numbers (01 §1.9/§1.16/§2.9) --------------------------

def test_pinned_spec_constants_and_worked_burn():
    """g0 = 9.80665 exactly; RKF4(5) rel tol 1e-9; thrust-warp cap
    a_thrust*dt <= 1 m/s; §2.9 worked: 10 t, 50 kN, Isp 300, dv 1,000 ->
    ve = 2,941.995 m/s, t_b = 169.55 s, m_prop = 2,881.6 kg, ignition at
    t_node - t_b/2."""
    assert G0 == 9.80665                        # exactly (01 §2.9)
    assert RKF_REL_TOL == 1e-9                  # 01 §1.16
    assert WARP_DV_CAP_MPS == 1.0               # 01 §1.9

    el = _leo_circular()
    t_node = el.period / 2.0
    fn = node_to_finite(el, MU_EARTH, 1000.0, 50e3, 300.0, M0, t_node)
    assert 300.0 * G0 == pytest.approx(2941.995)
    assert fn.duration_s == pytest.approx(169.5544348467743, rel=1e-12)
    assert M0 - fn.m_final == pytest.approx(2881.6234365927594, rel=1e-9)
    assert fn.t_ignite == pytest.approx(t_node - 0.5 * 169.5544348467743)


def test_thrust_warp_dt_cap_enforced():
    """01 §1.9: dt capped so a_thrust*dt <= 1 m/s, using the burn's worst
    (lightest) mass. 500 kN on ~9.67 t burnout -> dt <= ~0.0193 s."""
    el = _leo_circular()
    dur = burn_time(M0, 500e3, 300.0, 100.0)
    arc = burn_arc(el, MU_EARTH, 0.0, dur, 500e3, 300.0, M0)
    m_end = M0 - (500e3 / (300.0 * G0)) * dur
    cap = WARP_DV_CAP_MPS * m_end / 500e3
    dt = np.diff(arc.samples[:, 0])
    assert dt.max() <= cap * (1.0 + 1e-12)
    # The cap actually bit: far more steps than the error control needs.
    assert len(dt) >= int(dur / cap)


# ---- steering laws ---------------------------------------------------------

def test_fixed_angle_steer_matches_prograde_over_short_arc():
    """A float steer is a fixed inertial angle (planar, 01 §1.15 — no
    normal channel in 2D). At t = 0 the circular-orbit velocity points
    along +y, so steer = pi/2 must track the prograde law to within the
    ~2 mrad the velocity rotates during a 2 s burn (~0.12 m/s)."""
    el = _leo_circular()
    dur = 2.0
    pro = burn_arc(el, MU_EARTH, 0.0, dur, 500e3, 300.0, M0, "prograde")
    fix = burn_arc(el, MU_EARTH, 0.0, dur, 500e3, 300.0, M0, math.pi / 2.0)
    p, q = pro.samples[-1], fix.samples[-1]
    assert math.hypot(p[3] - q[3], p[4] - q[4]) < 0.2     # m/s
    assert math.hypot(p[1] - q[1], p[2] - q[2]) < 1.0     # m
    assert fix.m_final == pytest.approx(pro.m_final, rel=1e-12)


def test_zero_duration_burn_is_identity():
    el = _leo_circular()
    arc = burn_arc(el, MU_EARTH, 123.0, 0.0, 500e3, 300.0, M0)
    assert arc.m_final == M0
    assert arc.elements.a == pytest.approx(el.a, rel=1e-12)
    assert arc.samples.shape[0] == 1
