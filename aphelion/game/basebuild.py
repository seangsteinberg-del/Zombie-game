"""Base construction (05/07, game layer): the buildable module catalog.
Every module is a ledger transformer with real stoichiometry (recipes per
kg of primary output), real power, and a real MTBF — built modules join
the site's LedgerNetwork and live or fail by the same machinery the
Phase-3 acceptance proved. Prices are delivered-hardware placeholders
($/t to the surface) pending the full economy pass.

kinds gates what a site's geology offers: no ice drill on a methane
shoreline, no lake pump in a polar crater.
"""

from __future__ import annotations

from aphelion.sim.ledger.network import Buffer, LedgerNetwork, Module, Source

DAY = 86_400.0

CATALOG: dict[str, dict] = {
    "drill_ice": {
        "name": "Regolith ice drill", "price_m": 14.0, "power_kw": 25.0,
        "primary": ("Water", 0.03), "inputs": {}, "outputs": {"Water": 1.0},
        "mtbf_d": 60.0, "kinds": ("psr_ice", "mars_ice", "ice_burrow"),
        "tech": None,
    },
    "electrolyzer": {
        "name": "Electrolysis plant", "price_m": 12.0, "power_kw": 80.0,
        "primary": ("Oxygen", 0.02),
        "inputs": {"Water": 1.125},
        "outputs": {"Oxygen": 1.0, "Hydrogen": 0.125},
        "mtbf_d": 45.0, "kinds": ("psr_ice", "mars_ice", "ice_burrow"),
        "tech": None,
    },
    "sabatier": {
        "name": "Sabatier methanator", "price_m": 18.0, "power_kw": 30.0,
        "primary": ("Methane", 0.01),
        "inputs": {"CO2": 2.75, "Hydrogen": 0.5},
        "outputs": {"Methane": 1.0, "Water": 2.25},
        "mtbf_d": 50.0, "kinds": ("mars_ice", "aerostat"),
        "tech": None,
    },
    "co2_intake": {
        "name": "Atmospheric CO2 intake", "price_m": 6.0, "power_kw": 12.0,
        "primary": ("CO2", 0.05), "inputs": {}, "outputs": {"CO2": 1.0},
        "mtbf_d": 90.0, "kinds": ("mars_ice", "aerostat"),
        "tech": None,
    },
    "lake_pump": {
        "name": "Hydrocarbon lake pump", "price_m": 8.0, "power_kw": 6.0,
        "primary": ("Methane", 0.05), "inputs": {},
        "outputs": {"Methane": 1.0},
        "mtbf_d": 80.0, "kinds": ("methane_lake",),
        "tech": "core:tech_titan_ops",
    },
    "solar_array": {
        "name": "Solar array wing", "price_m": 6.0, "power_kw": -40.0,
        "primary": None, "inputs": {}, "outputs": {},
        "mtbf_d": None, "kinds": "*", "tech": None,
        "solar_scaled": True,        # generation scales with site sunlight
    },
    "reactor_100": {
        "name": "Fission reactor (100 kWe)", "price_m": 40.0,
        "power_kw": -100.0, "primary": None, "inputs": {}, "outputs": {},
        "mtbf_d": None, "kinds": "*", "tech": "core:tech_fission_100kwe",
    },
    "hab_module": {
        "name": "Habitat module (4 beds)", "price_m": 25.0, "power_kw": 5.0,
        "primary": None, "inputs": {}, "outputs": {},
        "mtbf_d": None, "kinds": "*", "tech": None, "beds": 4,
    },
    "tank_farm": {
        "name": "Storage tank farm", "price_m": 8.0, "power_kw": 0.0,
        "primary": None, "inputs": {}, "outputs": {},
        "mtbf_d": None, "kinds": "*", "tech": None,
        "cap_add": {"Water": 40_000.0, "Oxygen": 40_000.0,
                    "Hydrogen": 10_000.0, "Methane": 40_000.0,
                    "CO2": 40_000.0},
    },
}


def catalog_for_kind(kind: str) -> list[str]:
    return [k for k, m in CATALOG.items()
            if m["kinds"] == "*" or kind in m["kinds"]]


def starter_network(site: dict, rng=None) -> LedgerNetwork:
    """A freshly founded base: empty pools, one free solar wing, and the
    hydrogen relief vent (the co-product lesson from Phase 3)."""
    net = LedgerNetwork(rng=rng)
    for res, cap in (("Water", 30_000.0), ("Oxygen", 60_000.0),
                     ("Hydrogen", 8_000.0), ("Methane", 30_000.0),
                     ("CO2", 30_000.0)):
        net.buffers[res] = Buffer(level=0.0, capacity=cap)
    net.buffers["Water"].level = 2_000.0          # founding reserve
    # relief vent BELOW one electrolyzer's H2 co-product (0.0025 kg/s):
    # consumers (sabatier) get first call; without one the tank still
    # blocks eventually — build storage or burn it (the Phase-3 lesson)
    net.add_source(Source("h2_vent", "Hydrogen", -0.001))
    add_module(net, "solar_array", site, serial=0)
    return net


def add_module(net: LedgerNetwork, key: str, site: dict,
               serial: int) -> Module:
    spec = CATALOG[key]
    power = spec["power_kw"]
    if power < 0.0 and spec.get("solar_scaled"):
        power *= site.get("solar", 1.0)
    rate = spec["primary"][1] if spec["primary"] else 0.0
    mod = Module(
        module_id=f"{key}_{serial}",
        inputs=dict(spec["inputs"]),
        outputs=dict(spec["outputs"]),
        rate_kgps=rate,
        power_kw=power,
    )
    if spec["mtbf_d"]:
        mod.mtbf_s = spec["mtbf_d"] * DAY
    net.add_module(mod)
    for res, extra in spec.get("cap_add", {}).items():
        if res in net.buffers:
            net.buffers[res].capacity += extra
    return mod
