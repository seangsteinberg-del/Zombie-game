"""Power & thermal v2 (09): P-1 priority dispatch (survival loads keep
running while bulk industry sheds), environment sink temperatures (H-2),
and the night-storage hardware."""

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pytest

from aphelion.game.basebuild import CATALOG
from aphelion.sim.ledger.network import Buffer, LedgerNetwork, Module
from aphelion.sim.power import RADIATOR_T_K, SINK_K, sink_factor


def _net_with_loads():
    """60 kW supply; 40 kW survival hab (p1) + 80 kW smelter (p5)."""
    net = LedgerNetwork()
    net.buffers["Water"] = Buffer(level=0.0, capacity=1e9)
    net.add_module(Module("gen", inputs={}, outputs={}, rate_kgps=0.0,
                          power_kw=-60.0))
    net.add_module(Module("hab", inputs={}, outputs={"Water": 1.0},
                          rate_kgps=1.0, power_kw=40.0, priority=1))
    net.add_module(Module("smelter", inputs={}, outputs={"Water": 1.0},
                          rate_kgps=1.0, power_kw=80.0, priority=5))
    return net


def test_priority_shedding_protects_survival_loads():
    net = _net_with_loads()
    module_rates, _, f_power = net.solve_rates()
    # survival load fully served; smelter gets the 20 kW remainder
    assert module_rates["hab"] == pytest.approx(1.0)
    assert module_rates["smelter"] == pytest.approx(20.0 / 80.0)
    assert f_power == pytest.approx(60.0 / 120.0)


def test_charged_battery_defers_shedding():
    net = _net_with_loads()
    net.buffers["Battery"] = Buffer(level=100.0, capacity=400.0)
    module_rates, rates, f_power = net.solve_rates()
    assert module_rates["smelter"] == pytest.approx(1.0)   # battery bridges
    assert f_power == 1.0
    assert rates["Battery"] < 0.0                          # draining


def test_equal_priorities_pro_rate_uniformly():
    net = LedgerNetwork()
    net.buffers["Water"] = Buffer(level=0.0, capacity=1e9)
    net.add_module(Module("gen", inputs={}, outputs={}, rate_kgps=0.0,
                          power_kw=-50.0))
    for i in range(2):
        net.add_module(Module(f"m{i}", inputs={}, outputs={"Water": 1.0},
                              rate_kgps=1.0, power_kw=50.0, priority=3))
    module_rates, _, f_power = net.solve_rates()
    assert module_rates["m0"] == pytest.approx(0.5)
    assert module_rates["m1"] == pytest.approx(0.5)
    assert f_power == pytest.approx(0.5)


def test_sink_factor_lunar_noon_trap():
    """09 H-2: airless noon (330 K) costs nearly half your radiator;
    Titan's 94 K sink costs nothing; PSR is always cold."""
    noon = sink_factor("regolith", daylight=True)
    night = sink_factor("regolith", daylight=False)
    assert noon == pytest.approx(1.0 - (330.0 / RADIATOR_T_K) ** 4, rel=1e-6)
    assert noon < 0.55 < 0.99 < night
    assert sink_factor("methane_lake", True) > 0.99
    assert sink_factor("psr_ice", True) == sink_factor("psr_ice", False)
    assert set(SINK_K) >= {"psr_ice", "regolith", "mars_ice", "aerostat",
                           "methane_lake", "ice_burrow"}


def test_night_storage_hardware():
    assert CATALOG["rfc_unit"]["cap_add"]["Battery"] == 1_200.0
    assert CATALOG["rfc_unit"]["tech"] == "core:tech_pw02_regen_fuel_cells"
    assert CATALOG["thermal_battery"]["cap_add"]["Battery"] == 800.0
    assert CATALOG["radiator_high"]["heat_kw"] == -400.0
    assert CATALOG["radiator_high"]["radiator"] is True
    assert CATALOG["solar_blanket"]["solar_scaled"] is True


def test_catalog_priorities_make_sense():
    assert CATALOG["hab_module"]["prio"] == 1
    assert CATALOG["greenhouse"]["prio"] == 2
    assert CATALOG["machine_shop"]["prio"] == 3
    assert CATALOG["electrolyzer"]["prio"] == 4
    assert CATALOG["bucket_wheel"]["prio"] == 5
