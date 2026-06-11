"""Chunk F (depth update): the economy gets teeth — re-offered contracts
(no silent soft-locks), early-delivery bonuses, difficulty multipliers,
crew training, ECLSS/engine tech grants, and the win path's currency
budget actually closing."""

import os

import pytest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from aphelion.content.loader import default_data_dir, load_packs
from aphelion.content.validate import validate
from aphelion.game.campaign import (CONTRACTS, YEAR, act_progress, sweep)
from aphelion.game.crew import CrewMember
from aphelion.sim.economy import Program
from aphelion.sim.research import ResearchState


@pytest.fixture(scope="module")
def db():
    d = load_packs(default_data_dir())
    validate(d)
    return d


def _state(**over):
    S = dict(vessels=[], bases=[], visited=set(), visited_surface=set(),
             milestones=set(), research=ResearchState())
    S.update(over)
    return S


def test_failed_contract_is_renegotiated_not_a_soft_lock():
    program = Program(funds=0.0)
    S = _state()
    sweep(program, S, 0.0)                      # offer Act I
    c = next(c for c in program.contracts if c.contract_id == "c_orbit")
    window = 0.5 * YEAR
    program.expire_overdue(window + 1.0)
    assert c.failed
    # past the grace period the sponsor comes back at a haircut
    sweep(program, S, window + 0.5 * YEAR + 2.0)
    assert not c.failed and c.retries == 1
    assert c.payout == pytest.approx(0.6 * 100e6)
    # and a re-offered contract can still complete (no early bonus)
    S["milestones"].add("orbited")
    sweep(program, S, window + 0.5 * YEAR + 3.0)
    assert c.completed_t is not None
    assert program.funds == pytest.approx(0.6 * 100e6)


def test_renegotiation_caps_at_two():
    program = Program(funds=0.0)
    S = _state()
    sweep(program, S, 0.0)
    c = next(c for c in program.contracts if c.contract_id == "c_orbit")
    t = 0.0
    for _ in range(2):
        program.expire_overdue(c.deadline_s + 1.0)
        t = c.deadline_s + 0.5 * YEAR + 2.0
        sweep(program, S, t)
    assert c.retries == 2
    program.expire_overdue(c.deadline_s + 1.0)
    sweep(program, S, c.deadline_s + YEAR)
    assert c.failed                              # third strike stands


def test_difficulty_multipliers_shape_offers():
    program = Program(funds=0.0)
    S = _state()
    sweep(program, S, 0.0, payout_mult=0.75, deadline_mult=0.8)
    c = next(c for c in program.contracts if c.contract_id == "c_orbit")
    assert c.payout == pytest.approx(75e6)
    assert c.deadline_s == pytest.approx(0.5 * YEAR * 0.8)


def test_act_progress_reads_the_gate():
    program = Program(funds=0.0)
    S = _state(milestones={"orbited"})
    sweep(program, S, 0.0)
    sweep(program, S, 1.0)
    assert act_progress(program).startswith("Act I 1/")


def test_crew_training_fields():
    m = CrewMember("X", "pilot", 1)
    assert m.available(0.0)
    m.busy_until = 100.0
    assert not m.available(50.0) and m.available(100.0)


def test_tech_grants_finally_grant(db):
    assert "core:engine_ntr_k2" in db.tech["core:tech_ntr"]["unlocks"]
    assert ("core:engine_torch_d1"
            in db.tech["core:tech_fusion_torch"]["unlocks"])
    ntr = db.parts["core:engine_ntr_k2"]["engine"]
    torch = db.parts["core:engine_torch_d1"]["engine"]
    assert ntr["isp_s"] == pytest.approx(900.0)
    assert torch["isp_s"] == pytest.approx(8000.0)


def test_win_path_science_budget_closes(db):
    """The audit's blocker: the campaign path must afford the win without
    visiting every rock. Campaign-path firsts at a modest x1.2 average
    multiplier + two field labs over ~3 years must cover the tree's
    win-path closure with slack."""
    win_closure = ("core:tech_isru_large", "core:tech_cryo_depots",
                   "core:tech_fission_100kwe", "core:tech_ntr",
                   "core:tech_wafer_fab", "core:tech_autonomous_factories",
                   "core:tech_fusion_torch", "core:tech_precursor")
    need_sci = sum(db.tech[n].get("cost_sci", 0.0) for n in win_closure)
    need_ed = sum(db.tech[n].get("cost_ed", 0.0) for n in win_closure)
    # campaign-path income: firsts the 21 contracts force you through
    from aphelion.game.sites import SITES
    firsts = (200.0 * 4                 # sun/earth-departure class entries
              + 300.0 + 500.0 + 500.0   # mars/jupiter/saturn-class entries
              + 250.0 + 350.0           # venus, moon class
              + sum(s["science"] for s in SITES.values()))
    income_sci = firsts * 1.2 + 2 * 2.5 * 365 * 3      # + two labs, 3 years
    income_ed = (firsts * 1.2 * 0.27                   # entry/landing ed
                 + 0.8 * 365 * 3 * 8                   # 8 modules online
                 + 2 * 2.5 * 365 * 3)                  # labs
    assert income_sci > need_sci * 1.05, (income_sci, need_sci)
    assert income_ed > need_ed * 1.1, (income_ed, need_ed)
