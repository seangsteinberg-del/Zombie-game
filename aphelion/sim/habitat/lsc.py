"""Life-support chains on the ledger (08 §3.0/§3.1; NASA BVAD anchors).

Canonical per-person-per-day baselines (binding across the bible):
O2 0.84 kg, dry FoodRations 0.62 kg, potable+hygiene Water 3.0 kg,
CO2 exhaled 1.00 kg, metabolic heat 100 Wt (09 consumes).

ECLSS closure is modeled as ledger modules, not magic percentages:
- Crew metabolism is a transformer: O2+Food+Water in, CO2+WasteWater out.
- A water processor recovers WasteWater -> Water at its tier's recovery
  fraction (ISS anchor ~0.90 water-loop closure).
- OGA electrolysis: Water -> O2 + Hydrogen (0.889 kg O2 + 0.111 kg H2 per
  kg water, 4.5 kWh/kg-O2 class power draw; ISS OGA anchor).
- CDRA scrubber concentrates CO2 (power only, v1: CO2 to stores/vent).
Closure percentages then EMERGE from which modules you build and power —
exactly the 08 design intent.
"""

from __future__ import annotations

from aphelion.sim.ledger.network import LedgerNetwork, Module

DAY = 86_400.0

# canonical baselines, kg per person per day (08 §3.0)
O2_KG_DAY = 0.84
FOOD_KG_DAY = 0.62
WATER_KG_DAY = 3.5               # 2.5 drink+prep + 1.0 hygiene (08 §1.1)
CO2_KG_DAY = 1.00
CREW_HEAT_WT = 100.0

# "WasteWater" is the in-loop carrier between crew and the processor; it is
# registered as a ledger-internal resource (08 owns it; not tradeable).
WASTE_WATER = "WasteWater"


def crew_module(crew: int) -> Module:
    """Crew metabolism as a transformer (primary output = CO2). Mass balance:
    in 0.84 O2 + 0.62 Food + 3.5 Water = 4.96; out 1.0 CO2 + 3.96 WasteWater
    (respiration + urine + hygiene reclaim stream; BVAD-consistent lumping)."""
    rate = CO2_KG_DAY * crew / DAY      # kg CO2 / s
    return Module(
        module_id=f"crew_x{crew}",
        inputs={
            "Oxygen": O2_KG_DAY / CO2_KG_DAY,
            "FoodRations": FOOD_KG_DAY / CO2_KG_DAY,
            "Water": WATER_KG_DAY / CO2_KG_DAY,
        },
        outputs={
            "CO2": 1.0,
            WASTE_WATER: (O2_KG_DAY + FOOD_KG_DAY + WATER_KG_DAY - CO2_KG_DAY)
            / CO2_KG_DAY,
        },
        rate_kgps=rate,
        power_kw=0.0,
    )


def water_processor(recovery: float = 0.90, rate_kgps: float = 0.001,
                    power_kw: float = 0.5) -> Module:
    """WasteWater -> Water at the tier's recovery fraction (ISS WRS ~0.90+;
    losses leave the loop as brine, accounted as loss mass)."""
    return Module(
        module_id="water_processor",
        inputs={WASTE_WATER: 1.0},
        outputs={"Water": recovery},
        rate_kgps=rate_kgps,
        power_kw=power_kw,
    )


def oga_electrolysis(rate_o2_kgps: float = 2e-5, power_kw: float = 1.5) -> Module:
    """Water -> O2 + H2 (stoichiometric 8:1 by mass through the primary O2
    output; ISS OGA anchor ~4.5 kWh/kg O2 at nominal rate)."""
    return Module(
        module_id="oga",
        inputs={"Water": 1.0 / 0.889},
        outputs={"Oxygen": 1.0, "Hydrogen": 0.111 / 0.889},
        rate_kgps=rate_o2_kgps,
        power_kw=power_kw,
    )


def build_iss_grade_hab(crew: int, *, water_store: float, o2_store: float,
                        food_store: float, battery_kwh: float,
                        supply_kw: float) -> LedgerNetwork:
    """An ISS-grade partial-closure habitat: crew + water recovery + OGA,
    stores sized by the caller, powered by a constant source (RTG/reactor)
    plus battery."""
    net = LedgerNetwork()
    # O2 capacity is barely above the store: the OGA hitting BLOCKED at the
    # ceiling IS the v1 ppO2 setpoint controller (a real OGA throttles to a
    # partial-pressure setpoint; without this, it converts precious water
    # into surplus oxygen all night)
    net.add_buffer("Oxygen", o2_store, o2_store + 2.0)
    net.add_buffer("Water", water_store, max(water_store * 2.0, 1_000.0))
    net.add_buffer("FoodRations", food_store, max(food_store * 2.0, 1_000.0))
    net.add_buffer("CO2", 0.0, 10_000.0)
    net.add_buffer(WASTE_WATER, 0.0, 10_000.0)
    net.add_buffer("Hydrogen", 0.0, 1_000.0)
    net.add_buffer("Battery", battery_kwh, max(battery_kwh, 1.0))

    net.add_module(crew_module(crew))
    # processor sized to keep up with crew wastewater (3.96 kg/p/d)
    net.add_module(water_processor(
        rate_kgps=2.0 * crew * 3.96 / DAY))
    # OGA sized to crew O2 demand x2 margin
    net.add_module(oga_electrolysis(
        rate_o2_kgps=2.0 * crew * O2_KG_DAY / DAY,
        power_kw=0.35 * crew))
    net.add_module(Module(
        module_id="power_supply", inputs={}, outputs={}, rate_kgps=0.0,
        power_kw=-supply_kw))
    return net
