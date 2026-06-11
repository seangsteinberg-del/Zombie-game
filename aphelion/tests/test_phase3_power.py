"""Phase 3 power & thermal (09): pinned solar-flux multipliers, the canon
radiator T^4 table, day/night cycling on the ledger, and the lunar-night
solar+battery base scenario."""

import math

import pytest

from aphelion.core.units import AU
from aphelion.sim.habitat.lsc import DAY
from aphelion.sim.ledger.network import LedgerNetwork, Module, OFF, RUNNING
from aphelion.sim.power import (
    radiator_module,
    radiator_rejection_kw,
    schedule_day_night,
    solar_array_module,
    solar_flux,
    thermal_balance_kw,
)

LUNAR_DAY = 29.53 * DAY      # synodic (solar) day on the Moon


# ---- pinned canon values (09 §3.2 / §3.5) -----------------------------------

def test_solar_constant_at_1au():
    assert solar_flux(AU) == pytest.approx(1_361.0)


@pytest.mark.parametrize("a_au, multiplier, tol", [
    (0.387, 6.7, 0.15),      # Mercury
    (0.723, 1.9, 0.05),      # Venus
    (1.524, 0.43, 0.01),     # Mars
    (5.204, 0.037, 0.002),   # Jupiter
    (9.583, 0.011, 0.001),   # Saturn
])
def test_solar_flux_multipliers(a_au, multiplier, tol):
    assert solar_flux(a_au * AU) / 1_361.0 == pytest.approx(multiplier, abs=tol)


def test_radiator_t4_canon_table():
    """09 §3.5: eps=0.90, per side, T_sink~0: 0.41 kW/m2 at 300 K and
    33.5 kW/m2 at 900 K — same panel, 81x the duty."""
    at_300 = radiator_rejection_kw(1.0, 300.0, n_sides=1)
    at_900 = radiator_rejection_kw(1.0, 900.0, n_sides=1)
    assert at_300 == pytest.approx(0.41, abs=0.01)
    assert at_900 == pytest.approx(33.5, abs=0.4)
    assert at_900 / at_300 == pytest.approx(81.0, rel=0.01)


# ---- day/night cycling on the ledger ----------------------------------------

def _solar_base() -> LedgerNetwork:
    net = LedgerNetwork()
    net.add_buffer("Water", 5_000.0, 50_000.0)
    net.add_buffer("Oxygen", 0.0, 1.0e6)
    net.add_buffer("Hydrogen", 0.0, 2.0e5)
    net.add_buffer("Battery", 200.0, 400.0)
    from aphelion.sim.habitat.lsc import oga_electrolysis
    net.add_module(oga_electrolysis(rate_o2_kgps=0.001, power_kw=4.0))
    net.add_module(solar_array_module("array_1", area_m2=40.0,
                                      efficiency=0.30, distance_m=AU))
    return net


def test_solar_array_sizing():
    arr = solar_array_module("a", area_m2=40.0, efficiency=0.30, distance_m=AU)
    assert -arr.power_kw == pytest.approx(40.0 * 0.30 * 1.361, rel=1e-6)


def test_day_night_cycle_toggles_production():
    net = _solar_base()
    # day first: array on at t=0, off at half lunar day...
    schedule_day_night(net, ["array_1"], 0.0, LUNAR_DAY, 2.0 * LUNAR_DAY)
    events = net.advance(0.0, 1.6 * LUNAR_DAY)   # past the next sunrise
    kinds = [(e.kind, e.subject) for e in events
             if e.kind in ("module_on", "module_off")]
    assert ("module_on", "array_1") in kinds
    assert ("module_off", "array_1") in kinds
    # battery cycled: discharged during the night leg
    assert any(e.kind == "buffer_empty" and e.subject == "Battery"
               for e in events) or net.buffers["Battery"].level < 200.0


def test_night_without_battery_halts_production():
    net = _solar_base()
    net.buffers["Battery"].level = 0.5       # nearly flat
    arr = [m for m in net.modules if m.module_id == "array_1"][0]
    arr.state = OFF                           # night
    o2_before = net.buffers["Oxygen"].level
    net.advance(0.0, 1.0 * DAY)
    # battery drained almost immediately; OGA produced ~nothing afterwards
    produced = net.buffers["Oxygen"].level - o2_before
    assert produced < 0.001 * DAY * 0.5       # << full-rate day output


# ---- thermal doctrine --------------------------------------------------------

def test_thermal_balance_habitat_vs_reactor_radiators():
    """The doctrine's worked contrast: ~25 kWt of habitat heat at 290 K
    needs ~35 m2 of double-sided wing; ~33 kWt of reactor heat at 400 K
    needs ~13 m2 (09 §3.5)."""
    hab_area = 25.0 / radiator_rejection_kw(1.0, 290.0)
    reactor_area = 33.0 / radiator_rejection_kw(1.0, 400.0)
    assert hab_area == pytest.approx(35.0, abs=2.0)
    assert reactor_area == pytest.approx(13.0, abs=1.5)


def test_thermal_balance_accounting():
    net = LedgerNetwork()
    net.add_buffer("Water", 100.0, 1_000.0)
    net.add_buffer("Oxygen", 0.0, 1_000.0)
    net.add_buffer("Hydrogen", 0.0, 100.0)
    from aphelion.sim.habitat.lsc import oga_electrolysis
    net.add_module(oga_electrolysis(rate_o2_kgps=0.001, power_kw=4.0))
    net.add_module(Module("reactor", inputs={}, outputs={}, rate_kgps=0.0,
                          power_kw=-10.0))
    net.modules[-1].heat_kw = 30.0            # reactor thermal waste
    net.add_module(radiator_module("rad_1", area_m2=12.0, t_radiator_k=400.0))
    emitted, capacity = thermal_balance_kw(net)
    assert emitted == pytest.approx(4.0 + 30.0)
    assert capacity == pytest.approx(radiator_rejection_kw(12.0, 400.0))
    assert capacity > emitted                  # this base is thermally sound
