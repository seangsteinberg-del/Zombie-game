"""PHASE 2 life-support acceptance (13 §6 / 08 §3.0): a crew survives the
14-day lunar night on stored power and water — the canonical numbers, run
entirely on the ledger (one code path at any warp)."""

import pytest

from aphelion.sim.habitat.lsc import (
    CO2_KG_DAY,
    DAY,
    FOOD_KG_DAY,
    O2_KG_DAY,
    WASTE_WATER,
    WATER_KG_DAY,
    build_iss_grade_hab,
    crew_module,
)
from aphelion.sim.ledger.network import LedgerNetwork, Module


def test_crew_module_mass_balance():
    m = crew_module(crew=2)
    mass_in = sum(m.inputs.values())
    mass_out = sum(m.outputs.values())
    assert mass_in == pytest.approx(mass_out, rel=1e-12)
    # per-day totals at nominal rate
    co2_per_day = m.rate_kgps * DAY
    assert co2_per_day == pytest.approx(2 * CO2_KG_DAY)


def test_open_loop_hab_consumes_baselines():
    """No recycling: stores deplete at exactly the BVAD rates."""
    net = LedgerNetwork()
    net.add_buffer("Oxygen", 100.0, 200.0)
    net.add_buffer("Water", 500.0, 1_000.0)
    net.add_buffer("FoodRations", 100.0, 200.0)
    net.add_buffer("CO2", 0.0, 1_000.0)
    net.add_buffer(WASTE_WATER, 0.0, 10_000.0)
    net.add_module(crew_module(crew=2))
    net.advance(0.0, 10.0 * DAY)
    assert net.buffers["Oxygen"].level == pytest.approx(100.0 - 2 * 10 * O2_KG_DAY, rel=1e-9)
    assert net.buffers["Water"].level == pytest.approx(500.0 - 2 * 10 * WATER_KG_DAY, rel=1e-9)
    assert net.buffers["FoodRations"].level == pytest.approx(100.0 - 2 * 10 * FOOD_KG_DAY, rel=1e-9)
    assert net.buffers["CO2"].level == pytest.approx(2 * 10 * CO2_KG_DAY, rel=1e-9)


def test_phase2_acceptance_lunar_night_14_days():
    """Crew of 2, ISS-grade closure, 14-day lunar night on RTG + battery:
    everyone alive, stores positive, loop closure visibly working."""
    crew = 2
    night = 14.0 * DAY
    net = build_iss_grade_hab(
        crew=crew,
        water_store=120.0,        # kg — loop-closure makes this ample
        o2_store=40.0,
        food_store=2 * FOOD_KG_DAY * 16,
        battery_kwh=60.0,
        supply_kw=2.5,            # RTG/fission night supply (09)
    )
    events = net.advance(0.0, night)

    # Nobody starved: no exhaustion of any life-critical store
    critical = {"Oxygen", "Water", "FoodRations"}
    fatal = [e for e in events if e.kind == "buffer_empty" and e.subject in critical]
    assert not fatal, fatal
    assert net.buffers["Oxygen"].level > 0.0
    assert net.buffers["Water"].level > 0.0
    assert net.buffers["FoodRations"].level > 0.0

    # The loop actually closed most of the water: net water burn far below
    # the open-loop 3.0 kg/p/d
    water_used = 120.0 - net.buffers["Water"].level
    open_loop_use = crew * WATER_KG_DAY * 14
    assert water_used < 0.45 * open_loop_use

    # Food has no recycler: consumed at exactly the baseline
    food_used = (2 * FOOD_KG_DAY * 16) - net.buffers["FoodRations"].level
    assert food_used == pytest.approx(crew * FOOD_KG_DAY * 14, rel=1e-6)


def test_power_loss_cascades_to_lsc():
    """Kill the supply: battery bridges, then the OGA/processor throttle and
    O2 stores begin draining — the cascade the design doc promises."""
    crew = 2
    net = build_iss_grade_hab(crew=crew, water_store=200.0, o2_store=10.0,
                              food_store=50.0, battery_kwh=5.0, supply_kw=2.5)
    supply = [m for m in net.modules if m.module_id == "power_supply"][0]
    supply.power_kw = 0.0     # blackout at t=0; battery only
    events = net.advance(0.0, 14.0 * DAY)
    assert any(e.kind == "buffer_empty" and e.subject == "Battery" for e in events)
    # with the OGA dead, O2 eventually runs out -> the alarm event exists
    assert any(e.kind == "buffer_empty" and e.subject == "Oxygen" for e in events)
