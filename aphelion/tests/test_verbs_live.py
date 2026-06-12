"""Chunk D (depth update): the verbs, flown — LiveDescent (powered landing
with a real crash state), ProxOps (CW docking approach), the low-orbit
landing gate, and undock spring separation."""

import math
import os

import pytest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from aphelion.game.fleet import FleetVessel
from aphelion.sim.flight.descent_live import LiveDescent
from aphelion.sim.flight.proxops_live import (CAPTURE_SPEED_MS,
                                              CONTACT_RANGE_M, ProxOps)
from aphelion.sim.orbits import transfers as tr
from aphelion.sim.orbits.ephemeris import load_solar_system
from aphelion.sim.orbits.kepler import state_to_elements
from aphelion.sim.vessels.vessel import Vessel


@pytest.fixture(scope="module")
def world():
    return load_solar_system()


def _lander(db):
    # the canonical Phase-2 lander (high TWR — descent demands it)
    rows = [Vessel.fueled_row(db, p) for p in
            ("core:engine_ml111", "core:tank_ml_s", "core:payload_2t")]
    return Vessel(db, rows, stage_plan=[[0, 1, 2]], cd_a_m2=0.0)


def _moon_descent(db, tree):
    moon = tree.body("core:moon")
    r0 = moon.radius + 100e3
    v0 = tr.circular_speed(moon.mu, r0)
    return LiveDescent.from_orbit(_lander(db), moon.mu, moon.radius,
                                  "site:peary", r0, 0.0, 0.0, v0, 0.0)


def test_autoland_touches_down_softly(world):
    db, tree = world
    live = _moon_descent(db, tree)
    live.engage_autoland()
    for _ in range(400_000):
        live.step(0.02)
        if live.outcome is not None:
            break
    assert live.outcome == "landed"
    assert live.td_speed <= 3.0
    assert live.dv_used > 1_500.0          # a real braking burn was paid
    assert live.vessel.active_propellant_kg() > 0.0


def test_freefall_is_a_crash(world):
    db, tree = world
    mars = tree.body("core:mars")
    live = LiveDescent.from_entry(_lander(db), mars.mu, mars.radius,
                                  "site:jezero", h0=8e3, v_h=160.0,
                                  v_v=-110.0)
    for _ in range(40_000):               # nobody touches the throttle
        live.step(0.02)
        if live.outcome is not None:
            break
    assert live.outcome == "crash"
    assert live.td_speed > 50.0


def test_descent_telemetry_sane(world):
    db, tree = world
    live = _moon_descent(db, tree)
    assert live.coast_s > 0.0              # rails coast to periapsis
    assert live.h > 5e3
    assert live.stop_dist > 0.0
    live.step(0.02)
    assert live.downrange > 0.0            # orbital speed is ground track


def test_proxops_autopilot_captures(world):
    n = math.sqrt(3.986e14 / (6_771e3) ** 3)
    prox = ProxOps(n=n, budget_dv=60.0)
    prox.engage_auto()
    for _ in range(240_000):
        prox.step(0.05)
        if prox.outcome is not None:
            break
    assert prox.outcome == "captured"
    assert prox.speed_ms <= CAPTURE_SPEED_MS
    assert prox.used_dv <= 60.0


def test_proxops_contact_ladder(world):
    """06 §3.3 at the adapter: over 0.5 m/s bends the ring (damage), over
    the port's closing limit bounces, under it with a magnetic assist
    captures."""
    hot = ProxOps(n=1e-3, budget_dv=60.0, x=-80.0, y=0.0, vx=6.0, vy=0.0)
    for _ in range(4_000):
        hot.step(0.02)
        if hot.outcome is not None:
            break
    assert hot.outcome == "damage"

    warm = ProxOps(n=1e-3, budget_dv=60.0, x=-8.0, y=0.0, vx=0.3, vy=0.0)
    for _ in range(4_000):
        warm.step(0.02)
        if warm.bounces:
            break
    assert warm.bounces >= 1
    assert warm.outcome is None            # bounced off, not captured
    assert warm.range_m > CONTACT_RANGE_M

    soft = ProxOps(n=1e-3, budget_dv=60.0, x=-8.0, y=0.0, vx=0.08, vy=0.0,
                   port_size="L", magnetic=True)   # limit 0.05 -> 0.10
    for _ in range(4_000):
        soft.step(0.02)
        if soft.outcome is not None:
            break
    assert soft.outcome == "captured"


def test_landing_gate_demands_low_orbit(world):
    db, tree = world
    from aphelion.game.sites import SITES
    moon = tree.body("core:moon")
    r_high = moon.radius + 5_000e3
    el = state_to_elements(r_high, 0.0, 0.0,
                           tr.circular_speed(moon.mu, r_high), 0.0, moon.mu)
    fv = FleetVessel(tree, "core:moon", el, _lander(db), "HI", 1)
    ok, why = fv.can_land(SITES["site:peary"], 0.0)
    assert not ok and "periapsis" in why
    # hyperbolic flyby is refused outright
    v_esc = math.sqrt(2.0 * moon.mu / r_high) * 1.2
    fv.elements = state_to_elements(r_high, 0.0, 0.0, v_esc, 0.0, moon.mu)
    ok, why = fv.can_land(SITES["site:peary"], 0.0)
    assert not ok and "escape" in why


def test_undock_imparts_real_separation(world):
    db, tree = world
    earth = tree.body("core:earth")
    r0 = earth.radius + 400e3
    el = state_to_elements(r0, 0.0, 0.0, tr.circular_speed(earth.mu, r0),
                           0.0, earth.mu)
    a = FleetVessel(tree, "core:earth", el, _lander(db), "A", 1)
    b = FleetVessel(tree, "core:earth", el, _lander(db), "B", 2)
    assert a.dock_with(b, 0.0) or b.dock_with(a, 0.0)
    host = b if b.dock_joints else a
    split = host.undock_last(0.0, 9)
    assert split is not None
    hx, hy, hvx, hvy = host.state(0.0)
    sx, sy, svx, svy = split.state(0.0)
    rel_v = math.hypot(svx - hvx, svy - hvy)
    assert rel_v == pytest.approx(FleetVessel.UNDOCK_SEP_MS, rel=0.2)
    # and the orbits genuinely diverge within an hour
    hx2, hy2, _, _ = host.state(3_600.0)
    sx2, sy2, _, _ = split.state(3_600.0)
    assert math.hypot(sx2 - hx2, sy2 - hy2) > 1_000.0
