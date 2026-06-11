"""Crew system: candidate pool, hiring economics, and the real
mechanical effects of skills (prox-ops, LSS endurance, science)."""

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pytest

from aphelion.content.loader import default_data_dir, load_packs
from aphelion.game.crew import (
    CrewMember, apply_crew_bonuses, best_skill, candidates,
    science_multiplier,
)
from aphelion.game.fleet import FleetVessel
from aphelion.sim.orbits.ephemeris import load_solar_system
from aphelion.sim.orbits.kepler import state_to_elements
from aphelion.sim.orbits import transfers as tr
from aphelion.sim.vessels.vessel import Vessel


@pytest.fixture(scope="module")
def world():
    return load_solar_system()


def _vessel_with_crew(db, tree, crew_names):
    rows = [Vessel.fueled_row(db, p) for p in
            ("core:engine_mv815", "core:tank_ml_m", "core:capsule_vela")]
    mu = tree.body("core:earth").mu
    r = 6.678e6
    el = state_to_elements(r, 0.0, 0.0, tr.circular_speed(mu, r), 0.0, mu)
    return FleetVessel(tree, "core:earth", el,
                       Vessel(db, rows, stage_plan=[[0, 1, 2]]),
                       "T", 1, crew=crew_names)


def test_candidates_skip_existing_names():
    crew = {"M. Reyes": CrewMember("M. Reyes", "pilot", 1)}
    cands = candidates(crew)
    names = [c.name for c in cands]
    assert "M. Reyes" not in names and len(names) == 3


def test_hire_cost_scales_with_skill():
    assert CrewMember("X", "pilot", 1).hire_cost == pytest.approx(8e6)
    assert CrewMember("X", "pilot", 3).hire_cost == pytest.approx(16e6)


def test_pilot_cuts_prox_ops(world):
    db, tree = world
    crew = {"P": CrewMember("P", "pilot", 3)}
    fv = _vessel_with_crew(db, tree, ["P"])
    apply_crew_bonuses(fv, crew)
    assert fv.prox_ops_dv == pytest.approx(5.0)
    other = _vessel_with_crew(db, tree, [])
    cost = fv.rendezvous_cost(other, 0.0)
    assert cost == pytest.approx(5.0, abs=1.0)


def test_engineer_stretches_endurance(world):
    db, tree = world
    crew = {"E": CrewMember("E", "engineer", 2)}
    fv = _vessel_with_crew(db, tree, ["E"])
    base_days = fv.endurance_days
    apply_crew_bonuses(fv, crew)
    assert fv.endurance_days == pytest.approx(base_days * 1.30)


def test_reap_over_limit_removes_everywhere(world):
    db, tree = world
    from aphelion.game.crew import reap_over_limit
    from aphelion.sim.habitat.dose import CrewDose
    crew = {"Doomed": CrewMember("Doomed", "pilot", 1, CrewDose(1_200.0)),
            "Fine": CrewMember("Fine", "pilot", 1, CrewDose(10.0))}
    fv = _vessel_with_crew(db, tree, ["Doomed", "Fine"])
    lost = reap_over_limit(crew, [fv])
    assert lost == ["Doomed"]
    assert "Doomed" not in crew and "Doomed" not in fv.crew
    assert "Fine" in crew and "Fine" in fv.crew


def test_venus_demands_the_gondola(world):
    db, tree = world
    from aphelion.game.sites import SITES
    from aphelion.sim.orbits import transfers as tr
    from aphelion.sim.orbits.kepler import state_to_elements
    site = SITES["site:venus_cloud"]
    fv = _vessel_with_crew(db, tree, [])
    fv.frame_id = "core:venus"
    venus = tree.body("core:venus")
    r_park = venus.radius + 150e3          # the landing gate wants LOW orbit
    fv.elements = state_to_elements(r_park, 0.0, 0.0,
                                    tr.circular_speed(venus.mu, r_park),
                                    0.0, venus.mu)
    assert fv.land_at("site:venus_cloud", site, 0.0) is False  # no gondola
    ok, why = fv.can_land(site, 0.0)
    assert not ok and "gondola" in why
    fv.vessel.rows.append(Vessel.fueled_row(db, "core:gondola_havoc"))
    fv.vessel.stage_plan[-1].append(len(fv.vessel.rows) - 1)
    assert fv.land_at("site:venus_cloud", site, 0.0) is True


def test_scientist_multiplies_science(world):
    db, tree = world
    crew = {"S": CrewMember("S", "scientist", 3),
            "P": CrewMember("P", "pilot", 1)}
    fv = _vessel_with_crew(db, tree, ["S", "P"])
    assert science_multiplier(fv, crew) == pytest.approx(1.6)
    assert best_skill(fv, crew, "engineer") == 0
