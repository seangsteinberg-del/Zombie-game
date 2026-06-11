"""Cabin atmosphere + ECLSS ladder (08 §1–2): partial-pressure physics,
leaks/breaches, the health clock, closure fractions, water pools."""

import pytest

from aphelion.sim.habitat.atmosphere import (
    ATMOSPHERES, CabinAtm, prebreathe_hours)
from aphelion.sim.habitat.eclss import (
    OGA_H2O_PER_O2, SAB_H2O_PER_CO2, WaterLoop, capacities_kgph, closure,
    daily_resupply)


def test_ideal_gas_sanity_anchor():
    """V=106 m³, T=294 K, ppO2=21.2 → ~29.4 kg O2 resident (08 §1.4)."""
    c = CabinAtm(106.0, 294.0, "sea_level")
    assert c.m["O2"] == pytest.approx(29.4, abs=0.5)
    assert c.pp("O2") == pytest.approx(21.3, abs=0.2)
    assert c.p_total == pytest.approx(101.3, abs=2.5)


def test_presets_and_prebreathe():
    """Sea-level cabin → EMU needs hours; Exploration atm → walk out."""
    sea = CabinAtm(100.0, preset="sea_level")
    exp = CabinAtm(100.0, preset="exploration")
    assert prebreathe_hours(sea.pp("N2")) >= 3.0
    assert prebreathe_hours(exp.pp("N2")) == 0.0
    assert ATMOSPHERES["exploration"]["P"] == 56.5


def test_crew_burn_down_and_scrubbing():
    """Four crew, no ECLSS: O2 falls, CO2 climbs into the caution band;
    with a CDRA-class scrubber the CO2 stays nominal and accumulates in
    the store (never vented from air twice)."""
    c = CabinAtm(106.0, preset="sea_level")
    for _ in range(48):
        c.step_hours(1.0, crew_n=4, scrub_kgph=0.0, chx_kgph=2.0)
    assert c.bands()["ppCO2"] != "nominal"
    c2 = CabinAtm(106.0, preset="sea_level")
    for _ in range(48):
        c2.step_hours(1.0, crew_n=4, scrub_kgph=0.5, chx_kgph=2.0)
    assert c2.bands()["ppCO2"] == "nominal"
    assert c2.co2_store_kg > 7.0          # ~2 days × 4 kg/day captured


def test_o2_setpoint_holds_with_store():
    c = CabinAtm(106.0, preset="exploration")
    used = 0.0
    for _ in range(72):
        used += c.step_hours(1.0, crew_n=4, o2_avail_kg=1.0,
                             scrub_kgph=0.5, chx_kgph=2.0)["o2_used"]
    assert c.bands()["ppO2"] == "nominal"
    assert used == pytest.approx(3 * 4 * 0.84, rel=0.1)


def test_breach_is_an_emergency():
    """1 cm² hole at ~101 kPa leaks ~51 kg/h: pressure visibly collapsing
    within the hour; 10 cm² is minutes (08 §1.7)."""
    c = CabinAtm(106.0, preset="sea_level")
    c.hole_cm2 = 1.0
    p0 = c.p_total
    flows = c.step_hours(1.0, crew_n=0)
    assert flows["air_lost"] == pytest.approx(48.0, abs=8.0)
    assert c.p_total < p0 * 0.75
    c.hole_cm2 = 10.0
    for _ in range(4):
        c.step_hours(0.25, crew_n=0)
    assert c.p_total < 12.0
    assert c.bands()["P"] == "critical"


def test_hypoxia_clock_incapacitates_then_kills():
    c = CabinAtm(20.0, preset="exploration")
    c.m["O2"] = c._m_at(11.0, "O2")      # thin air: t_inc ≈ 11 min
    assert c.hazard_t_inc_min() == pytest.approx(11.25, abs=0.5)
    c._tick_health_clock(12.0)
    assert c.crew_status() == "incapacitated"
    c._tick_health_clock(60.0)
    assert c.crew_status() == "dead"
    # recovery path: fix the air before the clock runs out
    c2 = CabinAtm(20.0, preset="exploration")
    c2.m["O2"] = c2._m_at(15.0, "O2")
    c2._tick_health_clock(10.0)
    c2.m["O2"] = c2._m_at(19.0, "O2")
    c2._tick_health_clock(30.0)
    assert c2.crew_status() == "ok" and c2.exposure_min == 0.0


def test_fire_multiplier_flags_pure_o2():
    sea = CabinAtm(50.0, preset="sea_level")
    assert sea.fire_multiplier() == pytest.approx(1.0, abs=0.05)
    sea.m["N2"] = 0.0                     # pure-O2 leftover
    assert sea.fire_multiplier() > 5.0


def test_airlock_loss_worked_example():
    """4 m³ airlock at exploration atm: ~2.7 kg/cycle without a pump,
    ~0.54 with the scavenge pump (08 §4.7)."""
    c = CabinAtm(100.0, preset="exploration")
    loss = c.airlock_loss_kg(4.0, has_pump=False)
    assert loss["N2"] + loss["O2"] == pytest.approx(2.7, abs=0.3)
    pumped = c.airlock_loss_kg(4.0, has_pump=True)
    assert pumped["N2"] + pumped["O2"] == pytest.approx(0.54, abs=0.08)


def test_closure_ladder_and_resupply():
    """Open loop → ISS loop → the numbers that drive the 180-day worked
    comparison (08 §2.7): closure slashes consumables ~5×."""
    open_units = {"LS-OPEN": 1}
    iss = {"LS-CDRA": 1, "LS-OGA": 1, "LS-SAB": 1, "LS-WRS": 1,
           "LS-CHX": 1, "LS-N2": 1}
    assert closure(open_units)["o2"] == 0.0
    assert closure(iss) == {"co2rm": 1.0, "o2": 0.42, "h2o": 0.90}
    iss_bpa = dict(iss, **{"LS-BPA": 1, "LS-BOSCH": 1})
    assert closure(iss_bpa)["h2o"] == 0.98
    assert closure(iss_bpa)["o2"] == 0.50
    open_need = daily_resupply(open_units, 4)
    iss_need = daily_resupply(iss, 4)
    open_180 = (open_need["o2"] + open_need["water"]
                + open_need["food_dry"]) * 180
    assert open_180 == pytest.approx(3_571.0, rel=0.02)
    # the ISS loop runs its O2 line on water via the OGA
    assert iss_need["o2"] == 0.0
    assert iss_need["water_for_o2"] == pytest.approx(
        0.58 * 4 * 0.84 * OGA_H2O_PER_O2, rel=0.01)
    assert iss_need["water"] == pytest.approx(0.10 * 4 * 3.5, rel=0.01)
    cap = capacities_kgph(iss)
    assert cap["scrub"] * 24 >= 4 * 1.0   # CDRA keeps up with 4 crew


def test_water_three_pools():
    """WRS+BPA closes the loop to a trickle; no WRS drains potable fast."""
    loop = WaterLoop(potable=500.0)
    units = {"LS-WRS": 1, "LS-BPA": 1, "LS-CHX": 1}
    for _ in range(30):
        loop.step_day(4, units, condensate_kg=4 * 2.3)
    # 30 days × 4 crew × 3.5 = 420 kg demand; stores barely move
    assert loop.potable > 430.0
    bare = WaterLoop(potable=500.0)
    for _ in range(30):
        bare.step_day(4, {}, condensate_kg=0.0)
    assert bare.potable < 100.0
    assert SAB_H2O_PER_CO2 == pytest.approx(0.818)
