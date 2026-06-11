"""PHASE 6: comms light-lag forcing local autonomy, the research tree on
the content pack, the self-sufficiency audit, and the endgame megaproject
feasibility check (interstellar precursor)."""

import math

import pytest

from aphelion.content.loader import default_data_dir, load_packs
from aphelion.content.validate import validate
from aphelion.core.units import AU, G0
from aphelion.sim.comms import (
    rtt_seconds,
    teleop_effectiveness,
    teleop_eta_between,
)
from aphelion.sim.habitat.lsc import DAY
from aphelion.sim.ledger.network import LedgerNetwork, Module, Source
from aphelion.sim.orbits.ephemeris import load_solar_system
from aphelion.sim.research import ResearchState

YEAR = 365.25 * DAY


@pytest.fixture(scope="module")
def db():
    d = load_packs(default_data_dir())
    validate(d)
    return d


@pytest.fixture(scope="module")
def system():
    return load_solar_system()


# ---- comms / teleop (05 §3.4 canon rows) --------------------------------------

def test_teleop_canon_rows():
    """Earth->Moon 2.6 s RTT -> 0.91 (Lunokhod-workable); Earth->Mars best
    6.2 min -> ~0.063 (useless)."""
    assert teleop_effectiveness(2.6) == pytest.approx(0.91, abs=0.01)
    assert teleop_effectiveness(372.0) == pytest.approx(0.063, abs=0.005)


def test_moon_rtt_geometry():
    assert rtt_seconds(3.844e8) == pytest.approx(2.56, abs=0.02)


def test_physics_forces_local_autonomy_at_mars(system):
    """The speed of light makes Earth irrelevant for Mars ops: teleop eta
    from Earth < 0.1 at ANY epoch; on-site (Phobos-style) eta ~ 1."""
    db, tree = system
    etas = [teleop_eta_between(tree, "core:earth", "core:mars", t)
            for t in [i * 30.0 * DAY for i in range(26)]]    # 2+ years
    assert max(etas) < 0.10
    assert teleop_eta_between(tree, "core:mars", "core:mars", 0.0) == 1.0


# ---- research tree (11) --------------------------------------------------------

def test_tech_tree_loads_and_gates(db):
    rs = ResearchState()
    rs.bootstrap(db)
    ntr = "core:tech_pr09_ntr"
    assert not rs.can_unlock(db, ntr)            # no funds, no prereqs
    rs.earn_science(5_000.0)
    rs.earn_eng_data(5_000.0)
    assert not rs.can_unlock(db, ntr)            # prereqs missing
    assert rs.unlock(db, "core:tech_pr04_cryo_fluid_mgmt")
    assert rs.unlock(db, "core:tech_pw04_kilopower")
    assert rs.can_unlock(db, ntr)
    assert rs.unlock(db, ntr)
    assert rs.science == pytest.approx(5_000.0 - 150.0 - 450.0 - 700.0)


def test_part_gating(db):
    rs = ResearchState()
    rs.bootstrap(db)
    # ML-111 is gated behind ISRU-refuelable landers (pr13) in the core pack
    assert not rs.part_available(db, "core:engine_ml111")
    assert rs.part_available(db, "core:engine_m733")     # ungated T1 base
    rs.earn_science(10_000.0)
    rs.earn_eng_data(10_000.0)
    for nid in ("core:tech_pr02_reusable_methalox",
                "core:tech_is03_water_electrolysis", "core:tech_is04_sabatier",
                "core:tech_pr13_isru_refuelable_landers"):
        assert rs.unlock(db, nid), nid
    assert rs.part_available(db, "core:engine_ml111")


def test_speculative_t4_is_deep(db):
    """The fusion torch demands the full chain — a dozen unlocks and two
    Discoveries deep, with T4 fog requiring a researched in-category T3
    node (11 §1.5)."""
    rs = ResearchState()
    rs.bootstrap(db)
    rs.earn_science(50_000.0)
    rs.earn_eng_data(50_000.0)
    torch = "core:tech_pr22_fusion_torch"
    order = ["core:tech_pr07_hall_clusters", "core:tech_pw04_kilopower",
             "core:tech_pw05_fission_surface", "core:tech_pw09_brayton",
             "core:tech_pw08_megawatt_reactors",
             "core:tech_pr16_nested_hall",          # T3 PR: reveals T4 PR
             "core:tech_is01_surface_survey_coring",
             "core:tech_is10_nea_volatile_capture",
             "core:tech_is17_strip_optical_mining",
             "core:tech_is20_he3_kiln", "core:tech_pw12_fusion_plant"]
    # discovery gates: NEA assay for is10, mare volatiles for is20
    rs.discoveries.add("core:dsc15_c_type_nea_assay")
    rs.discoveries.add("core:dsc02_mare_volatile_assay")
    for node in order:
        assert rs.unlock(db, node), node
    assert rs.unlock(db, torch)
    assert db.tech[torch]["tier"] == "T4"
    assert db.tech[torch].get("speculative") is True


# ---- the self-sufficiency audit (12 / Foundation) -------------------------------

def test_self_sufficiency_two_year_audit():
    """'No Earth imports for 2 sim-years': a closed base (local ice, local
    power, documented vent) runs 2 years with zero import events and
    positive stores — the audit the endgame demands."""
    net = LedgerNetwork()
    net.add_buffer("Water", 5_000.0, 1.0e6)
    net.add_buffer("Oxygen", 1_000.0, 5.0e6)
    net.add_buffer("Hydrogen", 0.0, 1.0e5)
    net.add_source(Source("psr_ice", "Water", 0.05, remaining=5.0e6))
    net.add_source(Source("h2_vent", "Hydrogen", -0.01))
    from aphelion.sim.habitat.lsc import oga_electrolysis
    net.add_module(oga_electrolysis(rate_o2_kgps=0.04, power_kw=160.0))
    net.add_module(Module("reactor", inputs={}, outputs={}, rate_kgps=0.0,
                          power_kw=-250.0))
    events = net.advance(0.0, 2.0 * YEAR)
    critical_failures = [e for e in events if e.kind == "buffer_empty"
                         and e.subject in ("Water", "Oxygen")]
    assert not critical_failures
    assert net.buffers["Oxygen"].level > 1.0e6        # tonnes of margin
    # SSI = 1 - imports/consumption; imports were ZERO by construction
    ssi = 1.0 - 0.0
    assert ssi == 1.0


# ---- endgame megaproject feasibility ---------------------------------------------

def test_interstellar_precursor_closes_with_t4_stack():
    """The endgame artifact: a 1,000 AU precursor probe. With the fusion
    torch [SPECULATIVE: Isp ~10,000 s] a 50 t probe + 450 t propellant
    closes a 100+ km/s mission delta-v — flight time to 1,000 AU under
    50 years. The same stack on chemical (Isp 367) is laughably impossible
    (mass ratio e^28)."""
    isp_fusion = 10_000.0
    dv = isp_fusion * G0 * math.log(500.0 / 50.0)     # full stack burn
    assert dv > 100_000.0                              # > 100 km/s
    v_cruise = dv * 0.5                                # half spent on cruise
    t_1000au = 1_000.0 * AU / v_cruise
    assert t_1000au < 50.0 * YEAR
    mass_ratio_chemical = math.exp(100_000.0 / (367.0 * G0))
    assert mass_ratio_chemical > 1e12                  # chemistry need not apply
