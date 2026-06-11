"""PHASE 4: docking/merge, propellant transfer, the standing LEO<->LLO
freighter route running one sim-year (13 §6 DoD), and the program economy."""

import math

import pytest

from aphelion.content.loader import default_data_dir, load_packs
from aphelion.content.validate import validate
from aphelion.sim.economy import Contract, Program
from aphelion.sim.habitat.lsc import DAY
from aphelion.sim.industry.routes import (
    FreighterRoute,
    plan_leo_llo_leg,
    plan_llo_leo_aero_leg,
    propellant_for_leg,
)
from aphelion.sim.ledger.network import LedgerNetwork, Module, Source
from aphelion.sim.vessels.docking import dock, transfer_resource, undock
from aphelion.sim.vessels.vessel import Vessel

MU_EARTH = 3.986_004_418e14
MU_MOON = 4.9028e12
R_LEO = 6.678e6
R_LLO = 1.8374e6          # 100 km LLO
A_MOON = 3.844e8
YEAR = 365.25 * DAY


@pytest.fixture(scope="module")
def db():
    d = load_packs(default_data_dir())
    validate(d)
    return d


# ---- docking ----------------------------------------------------------------

def test_dock_merges_mass_and_rows(db):
    station = Vessel(db, [Vessel.fueled_row(db, "core:tank_ml_xl")],
                     stage_plan=[[0]])
    tug = Vessel(db, [Vessel.fueled_row(db, "core:engine_ml111"),
                      Vessel.fueled_row(db, "core:tank_ml_s")],
                 stage_plan=[[0, 1]])
    m_before = station.total_mass_kg() + tug.total_mass_kg()
    dock(station, tug)
    assert len(station.rows) == 3
    assert station.total_mass_kg() == pytest.approx(m_before, rel=1e-12)


def test_undock_splits_back(db):
    station = Vessel(db, [Vessel.fueled_row(db, "core:tank_ml_xl")],
                     stage_plan=[[0]])
    tug = Vessel(db, [Vessel.fueled_row(db, "core:engine_ml111"),
                      Vessel.fueled_row(db, "core:tank_ml_s")],
                 stage_plan=[[0, 1]])
    dock(station, tug)
    m_total = station.total_mass_kg()
    departed = undock(station, [1, 2])
    assert len(station.rows) == 1 and len(departed.rows) == 2
    assert station.total_mass_kg() + departed.total_mass_kg() == \
        pytest.approx(m_total, rel=1e-12)
    assert departed.active_thrust_vac_n() > 0.0        # the tug kept its engine


def test_depot_propellant_transfer(db):
    depot = Vessel(db, [Vessel.fueled_row(db, "core:tank_ml_xl")],
                   stage_plan=[[0]])
    customer = Vessel(db, [Vessel.fueled_row(db, "core:engine_ml111"),
                           Vessel.fueled_row(db, "core:tank_ml_s")],
                      stage_plan=[[0, 1]])
    customer.rows[1].fill = {"Oxygen": 0.0, "Methane": 0.0}    # arrives dry
    moved = transfer_resource(depot, customer, "Oxygen", 10_000.0)
    # tank S holds 4.5 t total, 78.3% oxygen share = 3,523.5 kg of room
    assert moved == pytest.approx(4_500.0 * 0.783, rel=1e-9)
    total_o2 = sum(r.fill.get("Oxygen", 0.0) for r in depot.rows) + \
        sum(r.fill.get("Oxygen", 0.0) for r in customer.rows)
    assert total_o2 == pytest.approx(80_000.0 * 0.783, rel=1e-9)  # conserved


# ---- the standing route (Phase 4 DoD) -----------------------------------------

def _lunar_factory() -> LedgerNetwork:
    net = LedgerNetwork()
    net.add_buffer("Water", 1_000.0, 100_000.0)
    net.add_buffer("Oxygen", 20_000.0, 500_000.0)
    net.add_buffer("Hydrogen", 0.0, 60_000.0)
    net.add_source(Source("psr_ice", "Water", 0.05, remaining=5.0e6))
    from aphelion.sim.habitat.lsc import oga_electrolysis
    net.add_module(oga_electrolysis(rate_o2_kgps=0.04, power_kw=160.0))
    net.add_module(Module("reactor", inputs={}, outputs={}, rate_kgps=0.0,
                          power_kw=-250.0))
    # documented vent (13 §3.9): without it the H2 co-product fills its
    # buffer in ~139 days and BLOCKS the electrolyzer — found by the sim
    net.add_source(Source("h2_vent", "Hydrogen", -0.01))
    return net


def test_phase4_leo_llo_route_one_year():
    """A standing LLO -> LEO oxygen route self-runs for a sim year: the
    lunar factory keeps the depot fed; deliveries are deterministic."""
    llo = _lunar_factory()
    leo = LedgerNetwork()
    leo.add_buffer("Oxygen", 0.0, 1.0e6)

    out_leg = plan_llo_leo_aero_leg(MU_EARTH, MU_MOON, R_LEO, R_LLO, A_MOON)
    back_leg = plan_leo_llo_leg(MU_EARTH, MU_MOON, R_LEO, R_LLO, A_MOON)
    assert 800.0 < out_leg.dv_ms < 1_100.0        # TEI ~870 + 50 aero trim
    assert 3_800.0 < back_leg.dv_ms < 4_400.0     # TLI ~3.1 + LOI ~0.8-0.9
    assert 3.5 * DAY < out_leg.transfer_time_s < 6.0 * DAY

    route = FreighterRoute(
        name="oxygen-run", net_a=llo, net_b=leo,
        cargo_resource="Oxygen", cargo_kg=20_000.0, leg=out_leg,
        isp_s=355.0, freighter_dry_kg=8_000.0, return_leg=back_leg)

    # interleave production and route cycles month by month (deterministic)
    t = 0.0
    deliveries = 0
    while t < YEAR:
        t_next = min(t + 30.0 * DAY, YEAR)
        llo.advance(t, t_next)
        deliveries += route.run(t, t_next)
        t = t_next

    assert deliveries >= 10                       # ~2-week cycles, year-long
    assert leo.buffers["Oxygen"].level == pytest.approx(
        deliveries * 20_000.0, rel=1e-9)
    skipped = [e for e in route.log if "skipped" in e[1]]
    assert len(skipped) <= 2                      # production kept pace


def test_route_propellant_cost_is_rocket_equation():
    leg = plan_leo_llo_leg(MU_EARTH, MU_MOON, R_LEO, R_LLO, A_MOON)
    prop = propellant_for_leg(28_000.0, leg.dv_ms, 355.0)
    expected = 28_000.0 * (math.exp(leg.dv_ms / (355.0 * 9.80665)) - 1.0)
    assert prop == pytest.approx(expected, rel=1e-12)


def test_aero_leg_is_what_makes_lunar_export_pay():
    """The famous economics: propulsive return costs ~3x the delivered
    cargo in propellant; aerocapture cuts the outbound leg under 30%."""
    aero = plan_llo_leo_aero_leg(MU_EARTH, MU_MOON, R_LEO, R_LLO, A_MOON)
    prop_aero = propellant_for_leg(28_000.0, aero.dv_ms, 355.0)
    propulsive = plan_leo_llo_leg(MU_EARTH, MU_MOON, R_LEO, R_LLO, A_MOON)
    prop_full = propellant_for_leg(28_000.0, propulsive.dv_ms, 355.0)
    assert prop_aero < 0.45 * 20_000.0            # affordable
    assert prop_full > 2.5 * prop_aero            # the asymmetry is real


# ---- economy -----------------------------------------------------------------

def test_program_contracts_and_funds():
    p = Program(funds=150_000_000.0)
    p.offer(Contract("c1", "Deliver 20 t LOX to LEO", payout=40_000_000.0,
                     deadline_s=90.0 * DAY))
    assert p.spend(0.0, 60_000_000.0, "launch: freighter")
    assert not p.spend(0.0, 999_000_000.0, "over budget")
    assert p.complete(45.0 * DAY, "c1")
    assert p.funds == pytest.approx(150e6 - 60e6 + 40e6)
    p.offer(Contract("c2", "Crew rotation", payout=10e6, deadline_s=30 * DAY))
    assert p.expire_overdue(31.0 * DAY) == ["c2"]
    assert not p.complete(32.0 * DAY, "c2")       # too late
