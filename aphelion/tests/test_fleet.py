"""Fleet core: burns drain REAL propellant (Tsiolkovsky-exact), staging
happens mid-burn when a stage runs dry, dv is derived from the rows, and
crewed vessels consume life-support endurance."""

import math
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pytest

from aphelion.content.loader import default_data_dir, load_packs
from aphelion.content.validate import validate
from aphelion.core.units import G0, SECONDS_PER_DAY
from aphelion.game.fleet import FleetVessel
from aphelion.sim.orbits.ephemeris import load_solar_system
from aphelion.sim.orbits.kepler import state_to_elements
from aphelion.sim.orbits import transfers as tr
from aphelion.sim.vessels.vessel import Vessel


@pytest.fixture(scope="module")
def world():
    db, tree = load_solar_system()
    validate(db)
    return db, tree


def _vessel(db, stages: list[list[str]]) -> Vessel:
    rows, plan = [], []
    for stage in stages:
        idxs = []
        for pid in stage:
            idxs.append(len(rows))
            rows.append(Vessel.fueled_row(db, pid))
        plan.append(idxs)
    return Vessel(db, rows, stage_plan=plan, cd_a_m2=3.2)


def _in_leo(db, tree, stages, crew=None) -> FleetVessel:
    mu = tree.body("core:earth").mu
    r = 6.678e6
    el = state_to_elements(r, 0.0, 0.0, tr.circular_speed(mu, r), 0.0, mu)
    return FleetVessel(tree, "core:earth", el, _vessel(db, stages),
                       "Test-1", 1, crew=crew)


def test_burn_drains_exact_tsiolkovsky_mass(world):
    db, tree = world
    fv = _in_leo(db, tree, [["core:engine_mv815", "core:tank_ml_m",
                             "core:payload_2t"]])
    m0 = fv.vessel.total_mass_kg()
    isp = fv.vessel.active_isp(0.0)
    ok = fv.burn(0.0, 500.0, 0.0)
    assert ok
    m1 = fv.vessel.total_mass_kg()
    assert m1 == pytest.approx(m0 / math.exp(500.0 / (isp * G0)), rel=1e-9)


def test_dv_remaining_is_derived_and_shrinks(world):
    db, tree = world
    fv = _in_leo(db, tree, [["core:engine_mv815", "core:tank_ml_m",
                             "core:payload_2t"]])
    dv0 = fv.dv_remaining
    fv.burn(0.0, 800.0, 0.0)
    assert fv.dv_remaining == pytest.approx(dv0 - 800.0, rel=5e-3)


def test_burn_exceeding_total_refused_without_state_change(world):
    db, tree = world
    fv = _in_leo(db, tree, [["core:engine_mv815", "core:tank_ml_s",
                             "core:payload_2t"]])
    el0 = fv.elements
    m0 = fv.vessel.total_mass_kg()
    assert fv.burn(0.0, fv.dv_remaining + 500.0, 0.0) is False
    assert fv.elements is el0
    assert fv.vessel.total_mass_kg() == m0


def test_mid_burn_staging_spans_two_stages(world):
    db, tree = world
    fv = _in_leo(db, tree, [
        ["core:engine_mv815", "core:tank_ml_s"],
        ["core:engine_mv815", "core:tank_ml_m", "core:payload_2t"]])
    stats = fv.vessel.stage_stats()
    s1 = stats[0]["dv_vac"]
    assert len(fv.vessel.stage_plan) == 2
    ok = fv.burn(0.0, s1 + 300.0, 0.0)   # more than stage 1 holds
    assert ok
    assert len(fv.vessel.stage_plan) == 1          # staged mid-burn
    assert fv.dv_remaining > 0.0


def test_orbit_actually_changes_with_burn(world):
    db, tree = world
    fv = _in_leo(db, tree, [["core:engine_mv815", "core:tank_ml_m",
                             "core:payload_2t"]])
    apo0 = fv.elements.apoapsis
    fv.burn(0.0, 1_000.0, 0.0)
    assert fv.elements.apoapsis > apo0 + 1e6


def test_crew_capacity_and_endurance(world):
    db, tree = world
    fv = _in_leo(db, tree,
                 [["core:engine_mv815", "core:tank_ml_m",
                   "core:capsule_vela"]], crew=["A", "B"])
    assert fv.crew_capacity == 2
    assert fv.endurance_days == pytest.approx(40.0)   # 80 crew-days / 2


def test_lss_countdown_and_loss(world):
    db, tree = world
    fv = _in_leo(db, tree,
                 [["core:engine_mv815", "core:tank_ml_m",
                   "core:capsule_vela"]], crew=["A", "B"])
    evs = fv.tick_lss(12.0 * SECONDS_PER_DAY)
    assert any("30 days" in e for e in evs)           # crossed 40 -> 28
    assert fv.lss_margin_days == pytest.approx(28.0)
    evs = fv.tick_lss(36.0 * SECONDS_PER_DAY)
    assert any("SEVEN DAYS" in e for e in evs)        # crossed 28 -> 4
    evs2 = fv.tick_lss(41.0 * SECONDS_PER_DAY)
    assert any("EXHAUSTED" in e for e in evs2)
    assert fv.crew == []


def test_dock_undock_crossfeed_cycle(world):
    """Tanker docks to a station, crossfeed refuels the station's active
    stage, undock releases the (now lighter) tanker."""
    db, tree = world
    station = _in_leo(db, tree, [["core:engine_mv815", "core:tank_ml_m",
                                  "core:capsule_vela"]], crew=["A"])
    station.burn(0.0, 900.0, 0.0)               # spend most of the M tank
    station.elements = _in_leo(db, tree, [["core:payload_2t"]]).elements
    tanker = _in_leo(db, tree, [["core:engine_mv815", "core:tank_ml_m"]])
    dv_before = station.dv_remaining

    cost = tanker.rendezvous_cost(station, 0.0)
    assert cost is not None and cost == pytest.approx(20.0, abs=1.0)
    assert tanker.dock_with(station, 0.0)
    assert station.dock_joints == [3]
    assert len(station.vessel.rows) == 5

    moved = station.crossfeed()
    assert moved > 1_000.0                       # tonnes flowed forward
    assert station.dv_remaining > dv_before

    split = station.undock_last(0.0, new_vid=9)
    assert split is not None
    assert station.dock_joints == []
    assert len(station.vessel.rows) == 3
    assert split.vessel.total_mass_kg() < 30_000.0   # tanker left lighter


def test_rendezvous_refused_across_frames(world):
    db, tree = world
    a = _in_leo(db, tree, [["core:payload_2t"]])
    b = _in_leo(db, tree, [["core:payload_2t"]])
    b.frame_id = "core:moon"
    assert a.rendezvous_cost(b, 0.0) is None


def test_uncrewed_vessel_has_infinite_endurance(world):
    db, tree = world
    fv = _in_leo(db, tree, [["core:engine_mv815", "core:tank_ml_m",
                             "core:payload_2t"]])
    assert fv.lss_margin_days == float("inf")
    assert fv.tick_lss(1e9) == []
