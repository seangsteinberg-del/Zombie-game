"""The Act table: offers gate on previous-act completion, checks fire
from real state, the precursor contract is the win condition."""

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pytest

from aphelion.content.loader import default_data_dir, load_packs
from aphelion.content.validate import validate
from aphelion.game.campaign import CONTRACTS, act_unlocked, sweep
from aphelion.game.fleet import FleetVessel
from aphelion.sim.economy import Program
from aphelion.sim.orbits.ephemeris import load_solar_system
from aphelion.sim.orbits.kepler import state_to_elements
from aphelion.sim.research import ResearchState
from aphelion.sim.vessels.vessel import Vessel


@pytest.fixture(scope="module")
def world():
    db, tree = load_solar_system()
    validate(db)
    return db, tree


def _state(**kw) -> dict:
    base = dict(vessels=[], bases=[], visited=set(), visited_surface=set(),
                milestones=set(), research=ResearchState())
    base.update(kw)
    return base


def test_act1_offers_immediately_act2_gated():
    program = Program(funds=0.0)
    toasts, won = sweep(program, _state(), 0.0)
    offered = {c.contract_id for c in program.contracts}
    assert "c_orbit" in offered and "c_moon" in offered
    assert "c_mars" not in offered            # Act II locked
    assert not won


def test_act2_unlocks_after_60pct_of_act1():
    program = Program(funds=0.0)
    S = _state(milestones={"orbited", "docked"},
               visited={"core:moon"},
               visited_surface={"site:peary"})
    sweep(program, S, 0.0)                    # offer act 1
    toasts, _ = sweep(program, S, 1.0)        # complete 4 of them
    done = [c for c in program.contracts if c.completed_t is not None]
    assert len(done) >= 4
    assert act_unlocked(2, program) is False  # 4/7 < 60% needs 5
    # crewed-orbit + a lunar base close the act
    from aphelion.main import BaseSite
    from aphelion.core.rng import RngRegistry
    S["bases"] = [BaseSite("Peary", 0.0, RngRegistry(1))]
    sweep(program, S, 2.0)
    assert act_unlocked(2, program)
    sweep(program, S, 3.0)
    offered = {c.contract_id for c in program.contracts}
    assert "c_mars" in offered


def test_contract_payout_flows_to_funds():
    program = Program(funds=0.0)
    S = _state(milestones={"orbited"})
    sweep(program, S, 0.0)
    sweep(program, S, 1.0)
    # base $100M plus the +25% early-delivery bonus (depth update)
    assert program.funds == pytest.approx(125e6)


def test_precursor_win_condition(world):
    db, tree = world
    rows = [Vessel.fueled_row(db, "core:probe_longshot"),
            Vessel.fueled_row(db, "core:engine_mv815")]
    vsl = Vessel(db, rows, stage_plan=[[0, 1]], cd_a_m2=1.0)
    mu_s = tree.body("core:sun").mu
    r = 1.6e11
    # hyperbolic: speed above solar escape at r
    v_esc = (2.0 * mu_s / r) ** 0.5
    el = state_to_elements(r, 0.0, 0.0, v_esc * 1.1, 0.0, mu_s)
    fv = FleetVessel(tree, "core:sun", el, vsl, "Longshot", 1)
    assert el.alpha < 0.0

    program = Program(funds=0.0)
    for spec in CONTRACTS:                    # force-offer everything
        from aphelion.sim.economy import Contract
        program.offer(Contract(spec.cid, spec.desc, spec.payout_m * 1e6,
                               deadline_s=1e12))
    S = _state(vessels=[fv])
    toasts, won = sweep(program, S, 5.0)
    assert won
    assert any("PRECURSOR" in t.upper() for t in toasts)


def test_all_contract_ids_unique_and_tech_refs_valid(world):
    db, _ = world
    ids = [s.cid for s in CONTRACTS]
    assert len(ids) == len(set(ids))
    assert "core:tech_pr22_fusion_torch" in db.tech
    assert "core:probe_longshot" in db.parts
    assert "core:tech_sh09_interstellar_precursor" in db.tech
