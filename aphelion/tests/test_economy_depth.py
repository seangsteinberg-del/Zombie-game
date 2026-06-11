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
    assert "core:engine_ntr_k2" in db.tech["core:tech_pr09_ntr"]["unlocks"]
    assert ("core:engine_torch_d1"
            in db.tech["core:tech_pr22_fusion_torch"]["unlocks"])
    ntr = db.parts["core:engine_ntr_k2"]["engine"]
    torch = db.parts["core:engine_torch_d1"]["engine"]
    assert ntr["isp_s"] == pytest.approx(900.0)
    assert torch["isp_s"] == pytest.approx(8000.0)


# §1.7 victory-path guarantee: SH-09 via the fission-fragment chain, no
# fusion, no Discovery gates. Order respects prereqs AND fog (a T4 node
# needs a researched in-category T3 node before it is even visible).
WIN_PATH = (
    "core:tech_gn01_rendezvous_prox_ops", "core:tech_pr04_cryo_fluid_mgmt",
    "core:tech_pw04_kilopower", "core:tech_pw05_fission_surface",
    "core:tech_pw09_brayton", "core:tech_pw08_megawatt_reactors",
    "core:tech_pr07_hall_clusters", "core:tech_pr16_nested_hall",
    "core:tech_pr17_mpd", "core:tech_pr21_fission_fragment",
    "core:tech_sh01_station_modules", "core:tech_in01_workshop",
    "core:tech_gn03_relay_constellations", "core:tech_in04_robotic_manipulation",
    "core:tech_in07_teleop_robots", "core:tech_in05_orbital_assembly_waam",
    "core:tech_in09_supervised_autonomy", "core:tech_in10_autonomous_factory",
    "core:tech_is01_surface_survey_coring", "core:tech_is02_regolith_excavation",
    "core:tech_is07_beneficiation", "core:tech_is08_ilmenite_reduction",
    "core:tech_is12_carbothermal", "core:tech_is13_molten_regolith",
    "core:tech_is16_solar_silicon", "core:tech_in11_wafer_fab",
    "core:tech_in14_industry_seed", "core:tech_gn05_low_thrust_planning",
    "core:tech_gn07_tour_planning", "core:tech_hb06_spin_centrifuge",
    "core:tech_sh07_cycler", "core:tech_sh09_interstellar_precursor",
)


def test_win_path_unlocks_in_order_without_discoveries(db):
    """The audited chain must be researchable with zero Discoveries
    (F-9 / §1.7) — fog, prereqs and ED thresholds all satisfied in order."""
    from aphelion.sim.research import ResearchState
    rs = ResearchState()
    rs.bootstrap(db)
    rs.earn_science(1e9)
    rs.earn_eng_data(1e9)
    for nid in WIN_PATH:
        assert rs.unlock(db, nid), nid
    assert not rs.discoveries                  # truly none required


def test_win_path_science_budget_closes(db):
    """The campaign path must afford the win without visiting every rock.
    Income model (mechanics that exist today): milestone firsts (k·X) over
    the campaign-path bodies, one-shot site science, and three field labs
    over 20 of the campaign's ~30 years."""
    from aphelion.game.sites import SITES
    from aphelion.sim.research import BODY_X, MILESTONE_K

    need_sci = sum(db.tech[n].get("cost_sci", 0.0) for n in WIN_PATH)

    full = ("flyby", "orbit", "landing", "crewed_landing", "crewed_30d")
    path_milestones = {
        "core:earth": ("orbit",), "core:moon": full, "core:mars": full,
        "core:venus": ("flyby", "orbit"), "core:jupiter": ("flyby", "orbit"),
        "core:saturn": ("flyby", "orbit"),
        "core:europa": ("flyby", "orbit", "landing"),
        "core:titan": ("flyby", "orbit", "landing", "crewed_landing"),
    }
    milestone_sci = sum(MILESTONE_K[m] * BODY_X[b]
                        for b, ms in path_milestones.items() for m in ms)
    site_sci = sum(s["science"] for s in SITES.values())
    labs_sci = 3 * 2.5 * 365.0 * 20.0
    income_sci = milestone_sci + site_sci + labs_sci
    assert income_sci > need_sci * 1.05, (income_sci, need_sci)


def test_win_path_ed_thresholds_reachable(db):
    """ED is per-family and checked, never spent — so the binding number
    per family is the MAX threshold on the win path. A modest modeled
    fleet over 20 years out-accrues every one of them."""
    from aphelion.sim.research import ResearchState

    need: dict[str, float] = {}
    for nid in WIN_PATH:
        for th in db.tech[nid].get("ed_thresholds", []):
            need[th["family"]] = max(need.get(th["family"], 0.0),
                                     float(th["value"]))
    assert need["RoboticsAutonomy"] == 3500.0      # the in14 long pole

    rs = ResearchState()
    HOURS_15Y = 15 * 365 * 24.0
    # 9 worker robots at half duty, 4 reactors, 4 fab cells, 4 SEP strings
    # thrusting 30% of the time, 2 crewed modules, ISRU/mining/thermal
    # plants, plus avionics program executions over ~200 SOI legs.
    rs.accrue_hours(None, "RoboticsAutonomy", HOURS_15Y * 0.5, n_units=9)
    rs.accrue_hours(None, "FissionSystems", HOURS_15Y, n_units=4)
    rs.accrue_hours(None, "FabricationMachines", HOURS_15Y * 0.6, n_units=4)
    rs.accrue_hours(None, "EPThrusters", HOURS_15Y * 0.3, n_units=4)
    rs.accrue_hours(None, "PressureStructures", HOURS_15Y, n_units=2)
    rs.accrue_hours(None, "ISRU-Chem", HOURS_15Y * 0.7, n_units=3)
    rs.accrue_hours(None, "MiningMachines", HOURS_15Y * 0.7, n_units=3)
    rs.accrue_hours(None, "ThermalControl", HOURS_15Y, n_units=2)
    rs.accrue_hours(None, "CryoFluidMgmt", HOURS_15Y, n_units=2)
    for leg in range(200):
        rs.accrue_event(None, "Avionics", "program_exec",
                        vessel_id=f"v{leg}")
    for fam, threshold in need.items():
        assert rs.d_f(fam) >= threshold, (fam, rs.d_f(fam), threshold)
