"""Docking through REAL ports (06 §3.3, chunk T): the E8 mate-plan read
off actual part rows, fluid lines only through a DK-L berth, joint burn
loads on a docked assembly, and port state surviving the campaign save."""

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pytest

from aphelion.game.fleet import FleetVessel
from aphelion.sim.orbits import transfers as tr
from aphelion.sim.orbits.ephemeris import load_solar_system
from aphelion.sim.orbits.kepler import state_to_elements
from aphelion.sim.stations.ports import mate_plan, stack_ports
from aphelion.sim.vessels.vessel import Vessel


@pytest.fixture(scope="module")
def world():
    return load_solar_system()


def _vessel(db, pids):
    rows = [Vessel.fueled_row(db, p) for p in pids]
    return Vessel(db, rows, stage_plan=[list(range(len(rows)))],
                  cd_a_m2=3.2)


def _in_leo(db, tree, pids, vid=1, crew=None):
    mu = tree.body("core:earth").mu
    r = 6.678e6
    el = state_to_elements(r, 0.0, 0.0, tr.circular_speed(mu, r), 0.0, mu)
    return FleetVessel(tree, "core:earth", el, _vessel(db, pids),
                       f"T-{vid}", vid, crew=crew)


def test_mate_plan_e8(world):
    db, tree = world
    s_only = _vessel(db, ["core:payload_2t", "core:dk_s"])
    l_only = _vessel(db, ["core:payload_2t", "core:dk_l"])
    both = _vessel(db, ["core:payload_2t", "core:dk_s", "core:dk_l"])
    bare = _vessel(db, ["core:payload_2t"])
    b_only = _vessel(db, ["core:payload_2t", "core:dk_b"])
    armed_b = _vessel(db, ["core:payload_2t", "core:dk_b", "core:dk_arm"])

    assert stack_ports(both) == {"S", "L"}
    assert mate_plan(s_only, s_only)[0] == "S"
    assert mate_plan(both, l_only)[0] == "L"        # biggest passage wins
    size, _, why = mate_plan(s_only, l_only)
    assert size is None and "E8" in why
    # no DK part at all: the integral probe-and-drogue keeps early
    # capsules docking
    assert mate_plan(bare, s_only)[0] == "S"
    assert mate_plan(bare, bare)[0] == "S"
    # CBM berthing needs the robot arm; an arm anywhere also doubles
    # capture tolerances
    size_b, _, why_b = mate_plan(b_only, b_only)
    assert size_b is None and "arm" in why_b
    size_ab, soft, _ = mate_plan(armed_b, b_only)
    assert size_ab == "B" and soft


def test_crossfeed_needs_fluid_lines(world):
    """A DK-S joint moves crew, not propellant — the depot economy runs
    on DK-L berths (06 §3.3)."""
    db, tree = world
    station = _in_leo(db, tree, ["core:engine_mv815", "core:tank_ml_m",
                                 "core:capsule_vela", "core:dk_s"], vid=1,
                      crew=["A"])
    station.burn(0.0, 900.0, 0.0)               # room in the tank now
    station.elements = _in_leo(db, tree, ["core:payload_2t"],
                               vid=9).elements
    tanker = _in_leo(db, tree, ["core:engine_mv815", "core:tank_ml_m",
                                "core:dk_s"], vid=2)
    assert tanker.dock_with(station, 0.0)       # S-S mates fine (E8)
    assert station.dock_joint_ports == ["S"]
    assert station.crossfeed() == 0.0           # but nothing flows


def test_joint_burn_loads_match_docked_mass(world):
    """06 §2.8a across the joint: everything beyond it times the burn
    acceleration, and docked_mass_t agrees row for row."""
    db, tree = world
    station = _in_leo(db, tree, ["core:engine_mv815", "core:tank_ml_m",
                                 "core:capsule_vela", "core:dk_s"], vid=1)
    station.elements = _in_leo(db, tree, ["core:payload_2t"],
                               vid=9).elements
    tanker = _in_leo(db, tree, ["core:engine_mv815", "core:tank_ml_m",
                                "core:dk_s"], vid=2)
    assert tanker.dock_with(station, 0.0)
    loads = station.joint_burn_loads(3.0)
    assert len(loads) == 1
    port, payload_t, load_kn = loads[0]
    assert port == "S"
    assert payload_t == pytest.approx(station.docked_mass_t())
    assert payload_t > 10.0                     # a near-full M tank rides
    assert load_kn == pytest.approx(payload_t * 3.0)


def test_port_state_survives_save(tmp_path, world):
    db, tree = world
    from aphelion.game.crew import CrewMember
    from aphelion.save.campaign import (
        read_campaign, restore_campaign, snapshot_campaign, write_campaign)
    from aphelion.sim.economy import Program
    from aphelion.sim.habitat.dose import CrewDose
    from aphelion.sim.research import ResearchState

    fv = _in_leo(db, tree, ["core:engine_mv815", "core:tank_ml_m",
                            "core:capsule_vela", "core:dk_l"], crew=["A"])
    tanker = _in_leo(db, tree, ["core:engine_mv815", "core:tank_ml_m",
                                "core:dk_l"], vid=2)
    assert tanker.dock_with(fv, 0.0)
    fv.port_repair_h = 13.5
    crew = {"A": CrewMember("A", "pilot", 1, CrewDose(0.0))}
    snap = snapshot_campaign(
        t=0.0, vessels=[fv], active_idx=0, next_vid=3,
        program=Program(funds=1.0), research=ResearchState(), crew=crew,
        visited=set(), bases=[], tutorial_done=True)
    path = tmp_path / "ports.aph"
    write_campaign(path, snap)
    nv = read_campaign(path, db, tree)["vessels"][0]
    assert nv.dock_joints == [4]
    assert nv.dock_joint_ports == ["L"]
    assert nv.port_repair_h == 13.5

    # pre-port saves: joints with no recorded class restore as L berths
    # (fluid-capable), so old depot assemblies keep working
    snap["campaign"]["vessels"][0].pop("dock_joint_ports")
    legacy = restore_campaign(snap, db, tree)["vessels"][0]
    assert legacy.dock_joint_ports == ["L"]
