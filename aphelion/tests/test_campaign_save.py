"""Campaign save/load round-trip: craft, program, research, crew, bases —
including the failure-fate extras that make reloads warp-invariant."""

import math
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from aphelion.core.rng import RngRegistry
from aphelion.main import BaseSite, Craft
from aphelion.save.campaign import (
    read_campaign, restore_campaign, snapshot_campaign, write_campaign,
)
from aphelion.sim.economy import Contract, Program
from aphelion.sim.habitat.dose import CrewDose
from aphelion.sim.orbits.ephemeris import load_solar_system
from aphelion.sim.orbits.kepler import state_to_elements
from aphelion.sim.orbits import transfers as tr
from aphelion.sim.research import ResearchState


def _campaign():
    db, tree = load_solar_system()
    mu = tree.body("core:earth").mu
    r = 6.678e6
    craft = Craft(tree, "core:earth",
                  state_to_elements(r, 0.0, 0.0, tr.circular_speed(mu, r),
                                    0.0, mu), dv_budget=4_321.0)
    program = Program(funds=88_000_000.0)
    program.offer(Contract("c1", "Test contract", 1e6, 1e7))
    program.complete(0.0, "c1")
    research = ResearchState(science=512.0, eng_data=64.0)
    crew = {"A": CrewDose(123.4), "B": CrewDose(0.5)}
    rng = RngRegistry(99)
    base = BaseSite("Peary Base", 1_000.0, rng)
    base.advance(40.0 * 86_400.0)
    return db, tree, craft, program, research, crew, base, rng


def test_round_trip_exact(tmp_path):
    db, tree, craft, program, research, crew, base, rng = _campaign()
    snap = snapshot_campaign(
        t=40.0 * 86_400.0, craft_frame=craft.frame_id,
        craft_elements=craft.elements, craft_dv=craft.dv_remaining,
        craft_name=craft.name, program=program, research=research,
        crew=crew, visited={"core:earth", "core:moon"}, bases=[base],
        tutorial_done=True, rng=rng)
    path = tmp_path / "quicksave.aph"
    write_campaign(path, snap)
    got = read_campaign(path)

    assert got["t"] == 40.0 * 86_400.0
    assert got["craft_frame"] == "core:earth"
    assert got["craft_dv"] == 4_321.0
    assert got["craft_elements"].alpha == craft.elements.alpha
    assert got["program"].funds == program.funds
    assert got["program"].contracts[0].completed_t == 0.0
    assert got["research"].science == 512.0
    assert got["crew"]["A"].accumulated_msv == 123.4
    assert got["visited"] == {"core:earth", "core:moon"}
    assert got["tutorial_done"] is True


def test_base_failure_fates_survive_reload(tmp_path):
    db, tree, craft, program, research, crew, base, rng = _campaign()
    fates = {m.module_id: m.failure_t for m in base.net.modules}
    levels = {r: b.level for r, b in base.net.buffers.items()}
    snap = snapshot_campaign(
        t=40.0 * 86_400.0, craft_frame=craft.frame_id,
        craft_elements=craft.elements, craft_dv=craft.dv_remaining,
        craft_name=craft.name, program=program, research=research,
        crew=crew, visited=set(), bases=[base], tutorial_done=False)
    path = tmp_path / "q.aph"
    write_campaign(path, snap)
    got = read_campaign(path)

    nb = got["bases"][0]
    assert nb["name"] == "Peary Base"
    assert nb["last_t"] == base.last_t
    for m in nb["net"].modules:
        assert m.failure_t == fates[m.module_id]
    for res, lvl in levels.items():
        assert nb["net"].buffers[res].level == lvl


def test_restore_without_rng_ok():
    db, tree, craft, program, research, crew, base, rng = _campaign()
    snap = snapshot_campaign(
        t=0.0, craft_frame=craft.frame_id, craft_elements=craft.elements,
        craft_dv=craft.dv_remaining, craft_name=craft.name, program=program,
        research=research, crew=crew, visited=set(), bases=[],
        tutorial_done=False, rng=None)
    got = restore_campaign(snap)
    assert got["rng_state"] is None
    assert got["bases"] == []
