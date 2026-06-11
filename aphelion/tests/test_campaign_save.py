"""Campaign save/load round-trip (v2, fleet): vessels with real rows,
program, research, crew, bases — including the failure-fate extras that
make reloads warp-invariant."""

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pytest

from aphelion.content.loader import default_data_dir, load_packs
from aphelion.core.rng import RngRegistry
from aphelion.game.crew import CrewMember
from aphelion.game.fleet import FleetVessel
from aphelion.main import BaseSite
from aphelion.save.campaign import (
    read_campaign, snapshot_campaign, write_campaign,
)
from aphelion.sim.economy import Contract, Program
from aphelion.sim.habitat.dose import CrewDose
from aphelion.sim.orbits.ephemeris import load_solar_system
from aphelion.sim.orbits.kepler import state_to_elements
from aphelion.sim.orbits import transfers as tr
from aphelion.sim.research import ResearchState
from aphelion.sim.vessels.vessel import Vessel


@pytest.fixture(scope="module")
def world():
    return load_solar_system()


def _fleet_vessel(db, tree, vid=1, crew=("A",)) -> FleetVessel:
    rows, plan = [], []
    for stage in (["core:engine_mv815", "core:tank_ml_m",
                   "core:capsule_vela"],):
        idxs = []
        for pid in stage:
            idxs.append(len(rows))
            rows.append(Vessel.fueled_row(db, pid))
        plan.append(idxs)
    mu = tree.body("core:earth").mu
    r = 6.678e6
    el = state_to_elements(r, 0.0, 0.0, tr.circular_speed(mu, r), 0.0, mu)
    fv = FleetVessel(tree, "core:earth", el,
                     Vessel(db, rows, stage_plan=plan, cd_a_m2=3.2),
                     f"Vessel-{vid}", vid, crew=list(crew))
    return fv


def _campaign(db, tree):
    fv = _fleet_vessel(db, tree)
    fv.burn(0.0, 321.0, 0.0)                      # uneven tank fills
    fv.lss_used_days = 5.5
    program = Program(funds=88_000_000.0)
    program.offer(Contract("c1", "Test contract", 1e6, 1e7))
    program.complete(0.0, "c1")
    research = ResearchState(science=512.0, eng_data=64.0)
    crew = {"A": CrewMember("A", "scientist", 3, CrewDose(123.4)),
            "B": CrewMember("B", "engineer", 1, CrewDose(0.5))}
    rng = RngRegistry(99)
    base = BaseSite("Peary Base", 1_000.0, rng)
    base.advance(40.0 * 86_400.0)
    return fv, program, research, crew, base, rng


def test_round_trip_exact(tmp_path, world):
    db, tree = world
    fv, program, research, crew, base, rng = _campaign(db, tree)
    snap = snapshot_campaign(
        t=40.0 * 86_400.0, vessels=[fv], active_idx=0, next_vid=2,
        program=program, research=research, crew=crew,
        visited={"core:earth", "core:moon"}, bases=[base],
        tutorial_done=True, rng=rng)
    path = tmp_path / "quicksave.aph"
    write_campaign(path, snap)
    got = read_campaign(path, db, tree)

    assert got["t"] == 40.0 * 86_400.0
    assert got["active_idx"] == 0 and got["next_vid"] == 2
    nv = got["vessels"][0]
    assert nv.frame_id == "core:earth"
    assert nv.name == "Vessel-1" and nv.crew == ["A"]
    assert nv.lss_used_days == 5.5
    assert nv.dv_remaining == pytest.approx(fv.dv_remaining, rel=1e-12)
    assert nv.elements.alpha == fv.elements.alpha
    # per-row fills survive exactly
    for row_a, row_b in zip(nv.vessel.rows, fv.vessel.rows):
        assert row_a.fill == row_b.fill
    assert got["program"].funds == program.funds
    assert got["research"].science == 512.0
    assert got["crew"]["A"].dose.accumulated_msv == 123.4
    assert got["crew"]["A"].role == "scientist"
    assert got["crew"]["A"].skill == 3
    assert got["visited"] == {"core:earth", "core:moon"}
    assert got["tutorial_done"] is True


def test_base_failure_fates_survive_reload(tmp_path, world):
    db, tree = world
    fv, program, research, crew, base, rng = _campaign(db, tree)
    fates = {m.module_id: m.failure_t for m in base.net.modules}
    snap = snapshot_campaign(
        t=40.0 * 86_400.0, vessels=[], active_idx=0, next_vid=1,
        program=program, research=research, crew=crew, visited=set(),
        bases=[base], tutorial_done=False)
    path = tmp_path / "q.aph"
    write_campaign(path, snap)
    got = read_campaign(path, db, tree)

    nb = got["bases"][0]
    assert nb["name"] == "Peary Base"
    for m in nb["net"].modules:
        assert m.failure_t == fates[m.module_id]


def test_v1_save_rejected_with_clear_error(tmp_path, world):
    db, tree = world
    from aphelion.save.serialize import write_save
    legacy = {"schema_version": 1, "propagator": "patched_conics", "t": 0.0,
              "campaign": {"craft": {}, "program": {"funds": 0,
                                                    "history": [],
                                                    "contracts": []}},
              "rng": None}
    path = tmp_path / "old.aph"
    write_save(path, legacy)
    with pytest.raises(ValueError, match="campaign v1"):
        read_campaign(path, db, tree)
