"""Research v2 (11, full build): tree integrity against the bible's
economy targets, fog of research, OR-prereqs, Discovery discounts,
per-family ED with damping/novelty/caps, prototyping & maturation
(the spec's worked acceptance examples), milestones and sample pools."""

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pytest

from aphelion.content.loader import default_data_dir, load_packs
from aphelion.content.validate import validate
from aphelion.sim.research import (
    BODY_X, FAMILIES, MILESTONE_K, ResearchState, badge, cryo_decay,
    m_unit, maturity, sample_award,
)


@pytest.fixture(scope="module")
def db():
    d = load_packs(default_data_dir())
    validate(d)
    return d


# ---- tree integrity (11 §1) -------------------------------------------------

def test_tree_shape_matches_canon(db):
    nodes = db.tech
    assert len(nodes) == 132
    by_branch: dict[str, int] = {}
    by_tier: dict[str, int] = {}
    sci: dict[str, float] = {}
    for nd in nodes.values():
        by_branch[nd["category"]] = by_branch.get(nd["category"], 0) + 1
        by_tier[nd["tier"]] = by_tier.get(nd["tier"], 0) + 1
        sci[nd["tier"]] = sci.get(nd["tier"], 0.0) + nd.get("cost_sci", 0.0)
    assert by_branch == {"PR": 23, "GN": 8, "PW": 13, "IS": 23, "IN": 15,
                         "SH": 10, "HB": 9, "LS": 12, "VH": 11, "SC": 8}
    assert by_tier == {"T0": 9, "T1": 34, "T2": 44, "T3": 35, "T4": 10}
    # economy targets (11 §1.3): T4 exactly 77,000; others near canon
    assert sci["T4"] == 77_000.0
    assert abs(sci["T1"] - 5_100) < 600
    assert abs(sci["T2"] - 22_300) < 2_500
    assert sci["T3"] == 54_000.0
    assert sum(1 for nd in nodes.values() if nd.get("era")) == 10
    assert all(nd.get("speculative") for nd in nodes.values()
               if nd["tier"] == "T4")
    assert len(db.by_type("discoveries")) == 18


def test_t0_nodes_are_free_starts(db):
    rs = ResearchState()
    rs.bootstrap(db)
    assert len(rs.unlocked) == 9
    for nid in rs.unlocked:
        assert db.tech[nid]["tier"] == "T0"
        assert db.tech[nid].get("cost_sci", 0.0) == 0.0
        assert db.tech[nid]["prereqs"] == []


# ---- fog of research (11 §1.5) -----------------------------------------------

def test_fog_rules(db):
    rs = ResearchState()
    rs.bootstrap(db)
    # T1: always visible
    assert rs.visible(db, "core:tech_pr02_reusable_methalox")
    # T2 with unresearched T1 prereq chain: hidden (distance > 1)
    assert not rs.visible(db, "core:tech_is05_polar_ice_mining")
    # researching the neighbor reveals it
    rs.earn_science(1_000.0)
    rs.earn_eng_data(1_000.0)
    assert rs.unlock(db, "core:tech_is01_surface_survey_coring")
    assert rs.unlock(db, "core:tech_is02_regolith_excavation")
    assert rs.visible(db, "core:tech_is05_polar_ice_mining")
    # the gating Discovery also reveals (even with no research nearby)
    rs2 = ResearchState()
    rs2.bootstrap(db)
    assert not rs2.visible(db, "core:tech_vh07_titan_submarine")
    rs2.discoveries.add("core:dsc13_titan_lake_composition")
    assert rs2.visible(db, "core:tech_vh07_titan_submarine")


def test_t4_hidden_until_in_category_t3(db):
    rs = ResearchState()
    rs.bootstrap(db)
    rs.earn_science(100_000.0)
    rs.earn_eng_data(100_000.0)
    sh09 = "core:tech_sh09_interstellar_precursor"
    # unlock its hard prereqs but no T3 SH node
    for nid in ("core:tech_pr07_hall_clusters", "core:tech_pw04_kilopower",
                "core:tech_pw05_fission_surface", "core:tech_pw09_brayton",
                "core:tech_pw08_megawatt_reactors",
                "core:tech_pr16_nested_hall", "core:tech_pr17_mpd",
                "core:tech_pr21_fission_fragment",
                "core:tech_gn01_rendezvous_prox_ops",
                "core:tech_sh01_station_modules", "core:tech_in01_workshop",
                "core:tech_gn03_relay_constellations",
                "core:tech_in04_robotic_manipulation",
                "core:tech_in07_teleop_robots",
                "core:tech_in05_orbital_assembly_waam",
                "core:tech_in09_supervised_autonomy",
                "core:tech_in10_autonomous_factory",
                "core:tech_is01_surface_survey_coring",
                "core:tech_is02_regolith_excavation",
                "core:tech_is07_beneficiation",
                "core:tech_is08_ilmenite_reduction",
                "core:tech_is12_carbothermal",
                "core:tech_is13_molten_regolith",
                "core:tech_is16_solar_silicon", "core:tech_in11_wafer_fab",
                "core:tech_in14_industry_seed"):
        assert rs.unlock(db, nid), nid
    assert not rs.visible(db, sh09)              # no T3 SH researched yet
    assert not rs.can_unlock(db, sh09)
    for nid in ("core:tech_gn05_low_thrust_planning",
                "core:tech_gn07_tour_planning",
                "core:tech_hb06_spin_centrifuge", "core:tech_sh07_cycler"):
        assert rs.unlock(db, nid), nid
    assert rs.visible(db, sh09)
    assert rs.unlock(db, sh09)


def test_or_prereqs(db):
    """gn05 needs pr06 OR pr07 (| binds tighter than +)."""
    rs = ResearchState()
    rs.bootstrap(db)
    rs.earn_science(5_000.0)
    rs.earn_eng_data(5_000.0)
    assert not rs.can_unlock(db, "core:tech_gn05_low_thrust_planning")
    assert rs.unlock(db, "core:tech_pr06_gridded_ion")
    assert rs.unlock(db, "core:tech_gn05_low_thrust_planning")


# ---- discoveries & discounts (11 §5, F-13) ------------------------------------

def test_discovery_award_and_discount(db):
    rs = ResearchState()
    rs.bootstrap(db)
    got = rs.acquire_discovery(db, "core:dsc01_lunar_psr_ice")
    assert got == 300.0 and rs.science == 300.0
    assert rs.acquire_discovery(db, "core:dsc01_lunar_psr_ice") == 0.0
    # -20% on is03 (water electrolysis): 130 -> 104
    assert rs.discounted_cost(db, "core:tech_is03_water_electrolysis") \
        == pytest.approx(104.0)


def test_staged_biology_tranches(db):
    """dsc11: 40% on acquisition, 30% tranches, SC-07 ×1.5 on tranches 2-3
    only — max total = listed × 1.3 (11 §5)."""
    rs = ResearchState()
    rs.bootstrap(db)
    total = rs.acquire_discovery(db, "core:dsc11_europa_ocean_water")
    assert total == pytest.approx(0.4 * 2500.0)
    total += rs.discovery_tranche(db, "core:dsc11_europa_ocean_water",
                                  organics_bonus=True)
    total += rs.discovery_tranche(db, "core:dsc11_europa_ocean_water",
                                  organics_bonus=True)
    assert total == pytest.approx(2500.0 * 1.3)
    # tranche 3 was the last: further calls pay nothing
    assert rs.discovery_tranche(db, "core:dsc11_europa_ocean_water") == 0.0


# ---- ED: checked never spent, damping, novelty, caps (11 §3.5) -----------------

def test_ed_thresholds_checked_not_spent(db):
    rs = ResearchState()
    rs.bootstrap(db)
    rs.earn_science(5_000.0)
    rs.earn_eng_data(5_000.0)
    assert rs.unlock(db, "core:tech_pr04_cryo_fluid_mgmt")
    assert rs.unlock(db, "core:tech_pw04_kilopower")
    before = (rs.d_f("HydroloxEngines"), rs.d_f("FissionSystems"))
    assert rs.unlock(db, "core:tech_pr09_ntr")
    assert (rs.d_f("HydroloxEngines"), rs.d_f("FissionSystems")) == before


def test_sqrt_n_damping():
    rs = ResearchState()
    rs.ed_novel["ISRU-Chem|leo_microgravity"] = 200.0     # exhaust novelty
    one = rs.accrue_hours(None, "ISRU-Chem", 100.0, n_units=1)
    rs2 = ResearchState()
    rs2.ed_novel["ISRU-Chem|leo_microgravity"] = 200.0
    nine = rs2.accrue_hours(None, "ISRU-Chem", 100.0, n_units=9)
    assert nine == pytest.approx(3.0 * one)               # √9 not 9


def test_novel_environment_window():
    """First 200 h in a new environment class accrue at ×3."""
    rs = ResearchState()
    a = rs.accrue_hours(None, "ISRU-Chem", 200.0)         # all boosted
    b = rs.accrue_hours(None, "ISRU-Chem", 200.0)         # window consumed
    assert a == pytest.approx(3.0 * b)
    # a different environment class re-opens the window
    c = rs.accrue_hours(None, "ISRU-Chem", 200.0,
                        env_class="vacuum_dusty_surface")
    assert c == pytest.approx(a)


def test_ed_cap_rises_with_visibility(db):
    """C_f = max(1.5·max visible threshold, 6·D_half) — F-7."""
    rs = ResearchState()
    rs.bootstrap(db)
    # FissionSystems: pw04 (T2, threshold 200) is visible from pw00
    cap0 = rs.ed_cap(db, "FissionSystems")
    assert cap0 == pytest.approx(6 * 400.0)               # floor dominates
    rs.earn_science(20_000.0)
    rs.earn_eng_data(20_000.0)
    for nid in ("core:tech_pw04_kilopower", "core:tech_pw05_fission_surface",
                "core:tech_pw09_brayton", "core:tech_pw08_megawatt_reactors",
                "core:tech_pr07_hall_clusters", "core:tech_pr16_nested_hall",
                "core:tech_pr17_mpd"):
        assert rs.unlock(db, nid), nid
    # researching pw08 (T3 PW) reveals pw12 (FissionSystems 4000) via the
    # distance-1 rule, so the visible max is 4000: cap = 1.5 × 4000
    assert rs.ed_cap(db, "FissionSystems") == pytest.approx(6_000.0)


def test_avionics_leg_cap():
    rs = ResearchState()
    rs.ed_novel["Avionics|leo_microgravity"] = 200.0
    for _ in range(8):
        rs.accrue_event(None, "Avionics", "program_exec", vessel_id="v1")
    assert rs.d_f("Avionics") == pytest.approx(10.0)      # capped per leg
    rs.reset_avionics_leg("v1")
    rs.accrue_event(None, "Avionics", "program_exec", vessel_id="v1")
    assert rs.d_f("Avionics") == pytest.approx(12.0)


# ---- prototyping & maturation: the spec's worked examples (11 §4.2) ------------

def test_worked_example_1_pump_fed_engine():
    """Mature p 0.0005; new type D=0 -> ×4; at ~625 ED m≈1.35; badge ≥600."""
    p_min = 0.0005
    assert p_min * maturity(0.0, "MethaloxEngines") == pytest.approx(0.002)
    m_625 = maturity(625.0, "MethaloxEngines")            # D_half 200
    assert m_625 == pytest.approx(1.35, abs=0.02)
    assert p_min * m_625 == pytest.approx(0.00068, abs=0.00002)
    assert badge(625.0) == "MATURE"
    assert badge(599.0) is None


def test_worked_example_2_eclss_unit():
    """Catalog MTBF 5,000 h (λ 0.2/1000h): prototype past unit burn-in
    0.2·4·4 = 3.2; at D=500 (D_half 250) m=1.75 -> 0.35 in FLIGHT."""
    rs = ResearchState()
    lam_min = 0.2
    rs.type_built.add("core:part_cdra")                   # PROTOTYPE state
    lam = lam_min * rs.live_failure_multiplier(
        "ECLSS-PhysChem", "core:part_cdra", unit_hours=100.0,
        unit_ignitions=99)
    assert lam == pytest.approx(3.2)
    rs.record_full_duration_success("core:part_cdra")
    rs.ed["ECLSS-PhysChem"] = 500.0
    lam2 = lam_min * rs.live_failure_multiplier(
        "ECLSS-PhysChem", "core:part_cdra", unit_hours=100.0,
        unit_ignitions=99)
    assert lam2 == pytest.approx(0.35)


def test_worked_example_3_ntr_first_article():
    """p_base 0.003 mature: prototype after burn-in 4.8%/ignition;
    skipping burn-in adds m_unit 2.5 -> 12%."""
    rs = ResearchState()
    rs.type_built.add("core:engine_ntr_k2")
    p = 0.003 * rs.live_failure_multiplier(
        "NTRCores", "core:engine_ntr_k2", unit_hours=60.0, unit_ignitions=4)
    assert p == pytest.approx(0.048)
    p_no_burnin = 0.003 * rs.live_failure_multiplier(
        "NTRCores", "core:engine_ntr_k2", unit_hours=0.0, unit_ignitions=0)
    assert p_no_burnin == pytest.approx(0.12)
    # burn-in clears via EITHER criterion: 50 h reached or 3 ignitions
    assert m_unit(49.0, 2) == 2.5
    assert m_unit(50.0, 2) == 1.0 and m_unit(10.0, 3) == 1.0


def test_prototype_build_cost_multipliers():
    """F-6: first article ×3, parallel prototypes ×1.5, after success ×1."""
    rs = ResearchState()
    assert rs.record_build("core:part_x") == 3.0
    assert rs.record_build("core:part_x") == 1.5
    assert rs.m_state("core:part_x") == 4.0
    rs.record_full_duration_success("core:part_x")
    assert rs.record_build("core:part_x") == 1.0
    assert rs.m_state("core:part_x") == 1.0


# ---- SCI sources: milestones, samples (11 §3.3-3.4) -----------------------------

def test_milestone_lumps():
    rs = ResearchState()
    assert rs.award_milestone("landing", "core:moon") \
        == MILESTONE_K["landing"] * BODY_X["core:moon"]
    assert rs.award_milestone("landing", "core:moon") == 0.0   # once
    assert rs.award_milestone("crewed_30d", "core:titan") \
        == pytest.approx(100.0 * 11.0)


def test_sample_pool_diminishing_returns():
    """S_n = 0.6·0.4^(n−1)·P, depleted at analysis in analysis order."""
    x = 5.0                                               # Mars surface
    p = 40.0 * x                                          # regolith pool
    assert sample_award("regolith_scoop", x, 1) == pytest.approx(0.6 * p)
    assert sample_award("regolith_scoop", x, 2) == pytest.approx(0.24 * p)
    rs = ResearchState()
    a1 = rs.analyze_sample("regolith_scoop", "mars_site", x, "earth_lab")
    assert a1 == pytest.approx(0.6 * p * 1.25)
    a2 = rs.analyze_sample("regolith_scoop", "mars_site", x, "insitu")
    assert a2 == pytest.approx(0.24 * p * 0.40)
    # a sample destroyed in transit is simply never drawn (F-3): the pool
    # counter only advanced twice
    assert rs.pools["regolith_scoop|mars_site"] == 2


def test_cryo_decay_floor():
    assert cryo_decay(0.0) == 1.0
    assert cryo_decay(10.0) == pytest.approx(0.8)
    assert cryo_decay(1_000.0) == 0.2                     # F-4 floor


def test_family_table_complete():
    assert len(FAMILIES) == 22
    rs = ResearchState()
    rs.earn_eng_data(5.0)                                 # all-family shim
    assert all(rs.d_f(f) == 5.0 for f in FAMILIES)
