"""PHASE 0 ACCEPTANCE (13 §6, binding DoD): fly a node-planned Earth->Mars
transfer reproducing 01 §3.8 within 1% — TMI 3,591 ± 36 m/s, 259 ± 3 d —
through the real patched-conic machinery: canon ephemeris, maneuver node,
SOI exit, heliocentric leg. Plus trajectory-chain unit tests and the
determinism gate.
"""

import math

import pytest

from aphelion.core.units import AU, SECONDS_PER_DAY
from aphelion.sim.flight.node_exec import ManeuverNode, apply_node_impulsive
from aphelion.sim.orbits import transfers as tr
from aphelion.sim.orbits.ephemeris import load_solar_system
from aphelion.sim.orbits.kepler import Elements, elements_to_state, state_to_elements
from aphelion.sim.orbits.trajectory import predict_trajectory

R_LEO300 = 6.678e6
DAY = SECONDS_PER_DAY


@pytest.fixture(scope="module")
def system():
    return load_solar_system()


def _angle_of(tree, body_id: str, t: float) -> float:
    rx, ry, _, _ = tree.state_in_parent(body_id, t)
    return math.atan2(ry, rx)


def _wrap(a: float) -> float:
    return (a + math.pi) % (2.0 * math.pi) - math.pi


def _plan_window(tree, t_search_start: float, years: float = 30.0):
    """Scan departure windows (phase-angle condition, 01 §3.8) and return the
    one whose geometry best reproduces the canonical 1.000 -> 1.5237 AU
    example: (t_dep, v_inf, predicted dv, predicted transfer time)."""
    mu_sun = tree.body("core:sun").mu
    mu_earth = tree.body("core:earth").mu
    a_mars = 1.5237 * AU

    def window_error(t: float):
        ex, ey, evx, evy = tree.state_in_parent("core:earth", t)
        r1 = math.hypot(ex, ey)
        # two-pass arrival radius refinement
        r2 = a_mars
        for _ in range(2):
            t_tr = math.pi * math.sqrt(((r1 + r2) / 2.0) ** 3 / mu_sun)
            mx, my, _, _ = tree.state_in_parent("core:mars", t + t_tr)
            r2 = math.hypot(mx, my)
        phase_target = math.pi - 2.0 * math.pi * t_tr / tr.orbital_period(mu_sun, 1.5237 * AU)
        phase_now = _wrap(_angle_of(tree, "core:mars", t) - math.atan2(ey, ex))
        return _wrap(phase_now - phase_target), r1, r2, t_tr

    best = None
    step = 0.5 * DAY
    t = t_search_start
    t_end = t_search_start + years * 365.25 * DAY
    prev_err = window_error(t)[0]
    while t < t_end:
        t_next = t + step
        err = window_error(t_next)[0]
        if prev_err < 0.0 <= err or prev_err > 0.0 >= err:
            if abs(err - prev_err) < math.pi:        # genuine crossing, not wrap
                lo, hi = t, t_next
                for _ in range(40):
                    mid = 0.5 * (lo + hi)
                    if (window_error(mid)[0] < 0.0) == (prev_err < 0.0):
                        lo = mid
                    else:
                        hi = mid
                t_dep = 0.5 * (lo + hi)
                _, r1, r2, t_tr = window_error(t_dep)
                # The needed v-infinity is a VECTOR: required heliocentric
                # departure velocity (transfer-perihelion speed, tangential)
                # minus Earth's ACTUAL velocity (Earth is eccentric — near
                # perihelion it runs ~225 m/s faster than circular).
                ex, ey, evx, evy = tree.state_in_parent("core:earth", t_dep)
                tx, ty = -ey / r1, ex / r1          # prograde tangential unit
                a_t = 0.5 * (r1 + r2)
                v_dep = tr.visviva_speed(mu_sun, r1, a_t)
                dvx, dvy = v_dep * tx - evx, v_dep * ty - evy
                v_excess_needed = math.hypot(dvx, dvy)
                phi_asym = math.atan2(dvy, dvx)
                # SOI-edge compensation (pure patched conics): the craft
                # leaves the SOI at sqrt(vinf^2 + 2 mu/r_soi), not vinf —
                # solve for the vinf whose SOI-EXIT speed is the needed one.
                r_soi = tree.body("core:earth").soi_radius
                vinf = math.sqrt(max(v_excess_needed ** 2
                                     - 2.0 * mu_earth / r_soi, 0.0))
                dv = tr.departure_dv(mu_earth, R_LEO300, vinf)
                cand = (t_dep, vinf, dv, t_tr, r1, r2, phi_asym)
                score = abs(dv - 3_591.0) / 36.0 + abs(t_tr / DAY - 258.9) / 3.0
                if best is None or score < best[0]:
                    best = (score, cand)
        prev_err = err
        t = t_next
    assert best is not None, "no departure window found in scan range"
    return best[1]


def _fly_tmi(tree, t_dep: float, vinf: float, phi_asym: float,
             dv_override: float | None = None):
    """Set up the LEO craft so its TMI burn point puts the escape asymptote
    along the planned v-infinity direction, apply the node, chain the legs."""
    mu_earth = tree.body("core:earth").mu

    e_h = 1.0 + R_LEO300 * vinf * vinf / mu_earth
    nu_inf = math.acos(-1.0 / e_h)
    theta_burn = (phi_asym - nu_inf) % (2.0 * math.pi)

    n_leo = math.sqrt(mu_earth / R_LEO300 ** 3)
    leo = Elements(mu=mu_earth, alpha=1.0 / R_LEO300, e=0.0, varpi=0.0,
                   tau=t_dep - theta_burn / n_leo, s=1.0)
    dv = dv_override if dv_override is not None else tr.departure_dv(
        mu_earth, R_LEO300, vinf)
    after = apply_node_impulsive(leo, ManeuverNode(t_node=t_dep, dv_prograde=dv))
    legs = predict_trajectory(tree, "core:earth", after, t_dep,
                              horizon=400.0 * DAY)
    return dv, legs


# ---- the acceptance flight --------------------------------------------------

def test_phase0_earth_mars_acceptance(system):
    db, tree = system
    t_dep, vinf, dv_pred, t_tr_pred, r1, r2, phi_asym = _plan_window(tree, 0.0)

    # The bible's DoD band: TMI 3,591 +/- 36 m/s
    dv, legs = _fly_tmi(tree, t_dep, vinf, phi_asym)
    assert 3_591.0 - 36.0 <= dv <= 3_591.0 + 36.0

    # Leg structure: Earth hyperbola -> SOI exit -> heliocentric ellipse
    assert legs[0].frame_id == "core:earth"
    assert legs[0].end_reason == "soi_exit"
    assert legs[0].t_end - t_dep < 7.0 * DAY
    helio = legs[1]
    assert helio.frame_id == "core:sun"

    # Transfer geometry: perihelion ~ departure radius, aphelion ~ Mars orbit
    assert helio.elements.periapsis == pytest.approx(r1, rel=0.015)
    assert helio.elements.apoapsis == pytest.approx(r2, rel=0.01)

    # Arrival: Hohmann arrival is AT APHELION (01 §3.8's 259 d is the
    # half-period). First-crossing of r2 is near-tangent and numerically
    # ill-conditioned, so aphelion passage is the binding metric.
    period = helio.elements.period
    t_apo = helio.elements.tau + period / 2.0
    while t_apo < helio.t_start:
        t_apo += period
    t_transfer_days = (t_apo - t_dep) / DAY
    assert t_transfer_days == pytest.approx(258.9, abs=3.0)

    # And the realized trajectory matches its own analytic plan to < 1%
    assert t_transfer_days == pytest.approx(t_tr_pred / DAY, rel=0.01)


def test_phase0_determinism(system):
    """Same inputs -> bit-identical trajectory, twice (13 §3.10)."""
    db, tree = system
    t_dep, vinf, _dv, _t, _r1, _r2, phi_asym = _plan_window(tree, 0.0, years=5.0)
    dv_a, legs_a = _fly_tmi(tree, t_dep, vinf, phi_asym)
    dv_b, legs_b = _fly_tmi(tree, t_dep, vinf, phi_asym)
    assert dv_a == dv_b
    assert len(legs_a) == len(legs_b)
    for la, lb in zip(legs_a, legs_b):
        assert la.t_end == lb.t_end
        assert la.elements == lb.elements


# ---- trajectory chain unit tests --------------------------------------------

def test_chain_escape_two_legs(system):
    db, tree = system
    mu_e = tree.body("core:earth").mu
    v_esc = tr.escape_velocity(mu_e, R_LEO300)
    el = state_to_elements(R_LEO300, 0.0, 0.0, 1.15 * v_esc, 1_000.0, mu_e)
    legs = predict_trajectory(tree, "core:earth", el, 1_000.0,
                              horizon=120.0 * DAY)
    assert legs[0].end_reason == "soi_exit"
    assert legs[1].frame_id == "core:sun"


def test_chain_tli_moon_entry(system):
    """Phase a TLI so apoapsis meets the real Moon: the chain must produce a
    soi_entry:core:moon leg in the Moon's frame."""
    db, tree = system
    mu_e = tree.body("core:earth").mu
    moon = tree.body("core:moon")
    a_moon = moon.elements.a
    a_tli = 0.5 * (R_LEO300 + a_moon)
    t_c = tr.orbital_period(mu_e, a_tli)
    n_m = 2.0 * math.pi / moon.elements.period

    # search a burn time within one Moon period so that Moon reaches the
    # craft's apoapsis longitude when the craft does
    t0 = None
    t = 0.0
    while t < 2.0 * moon.elements.period:
        target = math.pi - n_m * (t_c / 2.0)
        err = _wrap(_angle_of(tree, "core:moon", t) - target)
        if abs(err) < 0.01:
            t0 = t
            break
        t += abs(err) / n_m * 0.5 if abs(err) > 0.02 else 60.0
    assert t0 is not None

    vp = tr.visviva_speed(mu_e, R_LEO300, a_tli)
    el = state_to_elements(R_LEO300, 0.0, 0.0, vp, t0, mu_e)
    legs = predict_trajectory(tree, "core:earth", el, t0, horizon=t_c)
    reasons = [leg.end_reason for leg in legs]
    assert any(r == "soi_entry:core:moon" for r in reasons), reasons
    moon_leg = legs[[i for i, r in enumerate(reasons)
                     if r == "soi_entry:core:moon"][0] + 1]
    assert moon_leg.frame_id == "core:moon"


def test_chain_circular_orbit_no_transitions(system):
    db, tree = system
    mu_e = tree.body("core:earth").mu
    el = state_to_elements(R_LEO300, 0.0, 0.0,
                           tr.circular_speed(mu_e, R_LEO300), 0.0, mu_e)
    legs = predict_trajectory(tree, "core:earth", el, 0.0, horizon=30.0 * DAY)
    assert len(legs) == 1
    assert legs[0].end_reason == "horizon"
