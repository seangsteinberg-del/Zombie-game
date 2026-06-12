"""Orbital shipyards (05 §3.1): job-class rates, the build plan with
the 0.65× orbital structural multiplier and F-11 learning, cargo cells
on real rows, and cargo riding through dock/undock."""

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pytest

from aphelion.game.fleet import FleetVessel
from aphelion.sim.industry.yard import (
    ORBITAL_STRUCT_MULT, cargo_capacity_kg, has_dockyard, plan_build,
    sanity_t_per_day)
from aphelion.sim.orbits import transfers as tr
from aphelion.sim.orbits.ephemeris import load_solar_system
from aphelion.sim.orbits.kepler import state_to_elements
from aphelion.sim.vessels.vessel import Vessel


@pytest.fixture(scope="module")
def world():
    return load_solar_system()


def _in_leo(db, tree, pids, vid=1, crew=None):
    rows = [Vessel.fueled_row(db, p) for p in pids]
    v = Vessel(db, rows, stage_plan=[list(range(len(rows)))], cd_a_m2=3.2)
    mu = tree.body("core:earth").mu
    r = 6.778e6
    el = state_to_elements(r, 0.0, 0.0, tr.circular_speed(mu, r), 0.0, mu)
    return FleetVessel(tree, "core:earth", el, v, f"Y-{vid}", vid,
                       crew=crew)


def test_job_rates_sanity():
    """§3.1 sanity row: a T2 dock with 3 gangs sustains ~3 t/day fab."""
    assert sanity_t_per_day(3) == pytest.approx(3.0)
    assert sanity_t_per_day(3, a3=True) == pytest.approx(2.1)


def test_plan_build_bill_and_learning():
    p1 = plan_build(40.0, 12, gangs=3, a3=False, n_built_before=0)
    # orbital hull: 55% struct × 0.65, 30/8/7 untouched
    assert p1.bill_kg["StructuralParts"] == pytest.approx(
        40.0 * 0.55 * ORBITAL_STRUCT_MULT * 1_000.0)
    assert p1.bill_kg["MachineParts"] == pytest.approx(12_000.0)
    assert p1.bill_kg["Electronics"] == pytest.approx(3_200.0)
    # phases all present and the commission tail is real
    assert p1.phase_days["COMMISSION"] == pytest.approx(2.0)
    assert p1.days > 15.0
    # second hull of the same design: Wright 85% on the labor phases
    p2 = plan_build(40.0, 12, gangs=3, a3=False, n_built_before=1)
    assert p2.learning == pytest.approx(0.850, abs=0.003)
    assert p2.days < p1.days
    assert p2.phase_days["COMMISSION"] == p1.phase_days["COMMISSION"]


def test_cargo_cells_and_dockyard_flag(world):
    db, tree = world
    yard = _in_leo(db, tree, ["core:hb_dockyard", "core:cg_bay",
                              "core:cg_bay", "core:dk_l"], vid=1,
                   crew=["A"])
    assert has_dockyard(yard.vessel)
    assert cargo_capacity_kg(yard.vessel) == pytest.approx(16_000.0)
    assert yard.cargo_cap_kg == pytest.approx(16_000.0)
    took = yard.load_cargo("StructuralParts", 20_000.0)
    assert took == pytest.approx(16_000.0)         # capped by the bays
    assert yard.load_cargo("MachineParts", 1.0) == 0.0


def test_cargo_rides_the_dock(world):
    db, tree = world
    yard = _in_leo(db, tree, ["core:hb_dockyard", "core:cg_bay",
                              "core:dk_l"], vid=1, crew=["A"])
    hauler = _in_leo(db, tree, ["core:engine_mv815", "core:tank_ml_m",
                                "core:cg_bay", "core:dk_l"], vid=2)
    hauler.load_cargo("StructuralParts", 5_000.0)
    assert hauler.dock_with(yard, 0.0)
    assert yard.cargo.get("StructuralParts") == pytest.approx(5_000.0)
    assert hauler.cargo == {}
