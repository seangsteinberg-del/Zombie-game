"""Base construction (04/05/07, game layer): the buildable module catalog.
Every module is a ledger transformer with real stoichiometry (recipes per
kg of primary output, RX ids from design/extracts/04-resources-buildspec),
real power, and a real MTBF — built modules join the site's LedgerNetwork
and live or fail by the same machinery the Phase-3 acceptance proved.

Conventions:
- "primary": (resource, kg/s at nameplate) — the bold product of the RX
  row; "inputs"/"outputs" are kg per kg of primary.
- power_kw > 0 draws, < 0 generates; "vented" mass leaves the ledger
  (SOXE CO, flare losses) and is accounted by the mass-balance test.
- Energy figures are the canonical kWh-per-kg column of 04 §3.4; nameplate
  kWe = energy × nominal rate / 24 h.
- Intermediate streams (concentrates, slag, mixed gas) are FOLDED into
  their consumer plants per 04 §3.6's disposal rule — slag and tailings
  return to the Regolith pile; the Fractionator is folded into intakes.
- Cryo liquefaction skids and the boiloff economy land with the depot
  chunk; tanks hold canonical resources directly until then.

kinds gates what a site's geology offers: no ice drill on a methane
shoreline, no lake pump in a polar crater.
"""

from __future__ import annotations

from aphelion.sim.ledger.network import Buffer, LedgerNetwork, Module, Source

DAY = 86_400.0

_ICE = ("psr_ice", "mars_ice", "ice_burrow")
_REG = ("psr_ice", "mars_ice", "ice_burrow", "regolith")

CATALOG: dict[str, dict] = {
    # ---- water & regolith extraction (04 §3.3) ----------------------------
    "ice_corer": {
        "name": "Thermal ice corer (T1)", "price_m": 4.0, "power_kw": 3.0,
        "primary": ("Water", 20.0 / DAY), "inputs": {},
        "outputs": {"Water": 1.0},
        "mtbf_d": 70.0, "kinds": _ICE, "tech": "core:tech_is01_surface_survey_coring",
    },
    "drill_ice": {            # key kept for save compat: Sublimation Tent
        "name": "Sublimation tent miner (T2)", "price_m": 14.0,
        "power_kw": 86.0,     # 80 kWt + 6 kWe; 2.58 kWh/kg at g=5%
        "primary": ("Water", 800.0 / DAY), "inputs": {},
        "outputs": {"Water": 1.0},
        "mtbf_d": 60.0, "kinds": _ICE,
        "tech": "core:tech_is05_polar_ice_mining",
    },
    "ice_strip_miner": {
        "name": "Ice strip miner (T3)", "price_m": 55.0, "power_kw": 870.0,
        "primary": ("Water", 10_000.0 / DAY), "inputs": {},
        "outputs": {"Water": 1.0},
        "mtbf_d": 55.0, "kinds": _ICE,
        "tech": "core:tech_is17_strip_optical_mining",
    },
    "rodwell": {
        "name": "Rodwell rig (massive ice, T2)", "price_m": 8.0,
        "power_kw": 27.0,     # 0.54 kWh/kg: melts, no vacuum sublimation
        "primary": ("Water", 1_200.0 / DAY), "inputs": {},
        "outputs": {"Water": 1.0},
        "mtbf_d": 80.0, "kinds": ("mars_ice",),
        "tech": "core:tech_is05_polar_ice_mining",
    },
    "drum_excavator": {
        "name": "Drum excavator (T1)", "price_m": 2.0, "power_kw": 0.4,
        "primary": ("Regolith", 2_500.0 / DAY), "inputs": {},
        "outputs": {"Regolith": 1.0},
        "mtbf_d": 75.0, "kinds": _REG,
        "tech": "core:tech_is02_regolith_excavation",
    },
    "bucket_wheel": {
        "name": "Bucket-wheel excavator (T2)", "price_m": 16.0,
        "power_kw": 12.0,
        "primary": ("Regolith", 100_000.0 / DAY), "inputs": {},
        "outputs": {"Regolith": 1.0},
        "mtbf_d": 60.0, "kinds": _REG,
        "tech": "core:tech_is05_polar_ice_mining",
    },
    "volatile_oven": {
        "name": "Volatile bake oven (T2)", "price_m": 12.0, "power_kw": 40.0,
        # C-type rubble at g~8%, R 0.85: per kg water also bakes out CO2/N2
        "primary": ("Water", 680.0 / DAY),
        "inputs": {"Regolith": 14.7},
        "outputs": {"Water": 1.0, "CO2": 0.37, "Nitrogen": 0.04,
                    "Regolith": 13.29},
        "mtbf_d": 65.0, "kinds": ("regolith",),
        "tech": "core:tech_is10_nea_volatile_capture",
    },
    # ---- atmosphere & sea intakes (04 §3.2, fractionation folded) ---------
    "co2_intake": {           # key kept: Mars Atmospheric Intake II
        "name": "Mars atmospheric intake II (T2)", "price_m": 9.0,
        "power_kw": 18.0,     # 0.4 kWh/kg + folded fractionation
        "primary": ("CO2", 960.0 / DAY), "inputs": {},
        "outputs": {"CO2": 1.0, "Nitrogen": 0.0197, "Argon": 0.0201},
        "mtbf_d": 90.0, "kinds": ("mars_ice", "regolith"),
        "tech": "core:tech_is06_mars_atmo_processing",
    },
    "venus_intake": {
        "name": "Venus aerostat intake (T3)", "price_m": 10.0,
        "power_kw": 6.0,
        "primary": ("CO2", 1_930.0 / DAY), "inputs": {},
        "outputs": {"CO2": 1.0, "Nitrogen": 0.0363,
                    "Water": 0.001},          # cloud harvester: honestly tiny
        "mtbf_d": 45.0,       # H2SO4 doubles upkeep (F-9)
        "kinds": ("aerostat",), "tech": "core:tech_is18_venus_aerostat_intake",
    },
    "titan_intake": {
        "name": "Titan atmospheric intake (T3)", "price_m": 6.0,
        "power_kw": 2.0,
        "primary": ("Nitrogen", 4_725.0 / DAY), "inputs": {},
        "outputs": {"Nitrogen": 1.0, "Methane": 0.0529},
        "mtbf_d": 85.0, "kinds": ("methane_lake",),
        "tech": "core:tech_is19_titan_hydrocarbons",
    },
    "lake_pump": {            # key kept: Titan Sea Pump (Ligeia mix)
        "name": "Titan sea pump (T3)", "price_m": 8.0, "power_kw": 4.0,
        # 20 t/day liquid; ethane lumps to Methane at 0.93 (B14)
        "primary": ("Methane", 16_440.0 / DAY), "inputs": {},
        "outputs": {"Methane": 1.0, "Nitrogen": 0.207},
        "mtbf_d": 80.0, "kinds": ("methane_lake",),
        "tech": "core:tech_hb07_titan_outpost",
    },
    # ---- chemistry: RX plants (04 §3.4) ------------------------------------
    "electrolyzer": {         # RX-01 PEM
        "name": "PEM electrolyzer RX-01 (T1)", "price_m": 12.0,
        "power_kw": 58.0,     # 5.6 kWh/kg H2O × 250 kg/day
        "primary": ("Oxygen", 222.0 / DAY),
        "inputs": {"Water": 1.126},
        "outputs": {"Oxygen": 1.0, "Hydrogen": 0.126},
        "mtbf_d": 45.0, "kinds": _ICE,
        "tech": "core:tech_is03_water_electrolysis",
    },
    "electrolyzer_soec": {    # RX-02
        "name": "SOEC electrolyzer RX-02 (T2)", "price_m": 30.0,
        "power_kw": 200.0,
        "primary": ("Oxygen", 888.0 / DAY),
        "inputs": {"Water": 1.126},
        "outputs": {"Oxygen": 1.0, "Hydrogen": 0.126},
        "mtbf_d": 40.0, "kinds": _ICE,
        "tech": "core:tech_is03_water_electrolysis",
    },
    "sabatier": {             # RX-03
        "name": "Sabatier reactor RX-03 (T1)", "price_m": 10.0,
        "power_kw": 0.8,
        "primary": ("Methane", 91.0 / DAY),
        "inputs": {"CO2": 2.75, "Hydrogen": 0.50},
        "outputs": {"Methane": 1.0, "Water": 2.25},
        "mtbf_d": 50.0, "kinds": ("mars_ice", "aerostat", "regolith"),
        "tech": "core:tech_is04_sabatier",
        "heat_kw": -6.8,      # net exotherm (canonical, 09 H-0 ledger)
    },
    "soxe": {                 # RX-05 plant (MOXIE scaled)
        "name": "SOXE CO2 electrolyzer RX-05 (T2)", "price_m": 14.0,
        "power_kw": 35.0,
        "primary": ("Oxygen", 100.0 / DAY),
        "inputs": {"CO2": 2.75},
        "outputs": {"Oxygen": 1.0},
        "vented": {"CO": 1.75},
        "mtbf_d": 55.0, "kinds": ("mars_ice", "aerostat", "regolith"),
        "tech": "core:tech_is06_mars_atmo_processing",
    },
    "bosch": {                # RX-06
        "name": "Bosch reactor RX-06 (T2)", "price_m": 8.0, "power_kw": 3.1,
        "primary": ("Carbon", 50.0 / DAY),
        "inputs": {"CO2": 3.67, "Hydrogen": 0.333},
        "outputs": {"Carbon": 1.0, "Water": 3.0},
        "mtbf_d": 60.0, "kinds": ("mars_ice", "aerostat", "regolith"),
        "tech": "core:tech_is09b_materials_chem",
    },
    "ilmenite_line": {        # RX-07 (beneficiation folded)
        "name": "Ilmenite H2-reduction line RX-07 (T2)", "price_m": 24.0,
        "power_kw": 58.0,
        # H2 loop recycled internally, 2% makeup folded into MachineParts
        # upkeep (canon: "H2 recycled, 2% makeup")
        "primary": ("Oxygen", 100.0 / DAY),
        "inputs": {"Regolith": 11.9},
        "outputs": {"Oxygen": 1.0, "IronSteel": 3.5, "Regolith": 7.40},
        "mtbf_d": 50.0, "kinds": ("regolith", "psr_ice"),
        "tech": "core:tech_is08_ilmenite_reduction",
    },
    "carbothermal": {         # RX-08
        "name": "Carbothermal reactor RX-08 (T2)", "price_m": 18.0,
        "power_kw": 65.0,     # 20 kWe + 45 kWt
        "primary": ("Oxygen", 50.0 / DAY),
        "inputs": {"Regolith": 6.7, "Methane": 0.02},
        "outputs": {"Oxygen": 1.0, "IronSteel": 0.175, "Silicon": 0.175,
                    "Regolith": 5.37},
        "mtbf_d": 55.0, "kinds": _REG,
        "tech": "core:tech_is12_carbothermal",
    },
    "mre_cell": {             # RX-09
        "name": "Molten regolith electrolysis RX-09 (T3)", "price_m": 48.0,
        "power_kw": 365.0,
        "primary": ("Oxygen", 250.0 / DAY),
        "inputs": {"Regolith": 4.0},
        "outputs": {"Oxygen": 1.0, "IronSteel": 0.7, "Regolith": 2.3},
        "mtbf_d": 35.0,       # anode burn = MachineParts-hungry ×3
        "kinds": _REG, "tech": "core:tech_is13_molten_regolith",
    },
    "mond_refinery": {        # RX-10 (NiFe feed via folded beneficiation)
        "name": "Mond carbonyl refinery RX-10 (T3)", "price_m": 26.0,
        "power_kw": 42.0,
        "primary": ("IronSteel", 500.0 / DAY),
        "inputs": {"Regolith": 1.30, "Carbon": 0.05},
        "outputs": {"IronSteel": 1.0, "RareEarths": 0.0001,
                    "Regolith": 0.3499},
        "mtbf_d": 60.0, "kinds": ("regolith",),
        "tech": "core:tech_is14_carbonyl_refining",
    },
    "aluminum_line": {        # RX-11
        "name": "Anorthite aluminum line RX-11 (T3)", "price_m": 40.0,
        "power_kw": 145.0,
        "primary": ("Aluminum", 100.0 / DAY),
        "inputs": {"Regolith": 6.4},
        "outputs": {"Aluminum": 1.0, "Silicon": 0.6, "Oxygen": 1.5,
                    "Regolith": 3.3},
        "mtbf_d": 45.0, "kinds": _REG,
        "tech": "core:tech_is15_light_metals",
    },
    "dri_steel": {            # RX-12 (magnetic concentration folded)
        "name": "H2-DRI steel plant RX-12 (T2)", "price_m": 20.0,
        "power_kw": 39.0,
        "primary": ("IronSteel", 250.0 / DAY),
        "inputs": {"Regolith": 1.53, "Hydrogen": 0.03},
        "outputs": {"IronSteel": 1.0, "Water": 0.27, "Regolith": 0.29},
        "mtbf_d": 55.0, "kinds": ("mars_ice", "regolith"),
        "tech": "core:tech_is09b_materials_chem",
    },
    "haber_loop": {           # RX-14
        "name": "Haber ammonia loop RX-14 (T2)", "price_m": 6.0,
        "power_kw": 2.1,
        "primary": ("Ammonia", 50.0 / DAY),
        "inputs": {"Nitrogen": 0.824, "Hydrogen": 0.176},
        "outputs": {"Ammonia": 1.0},
        "mtbf_d": 70.0, "kinds": _REG + ("aerostat", "methane_lake"),
        "tech": "core:tech_is09a_gas_volatile_chem",
    },
    "polymer_plant": {        # RX-15 (= 05 polymers_mto)
        "name": "Polymer plant RX-15 (T1 build)", "price_m": 12.0,
        "power_kw": 12.5,
        "primary": ("Polymers", 200.0 / DAY),
        "inputs": {"Methane": 1.20, "Oxygen": 1.20},
        "outputs": {"Polymers": 1.0, "Water": 1.22, "CO2": 0.16,
                    "Hydrogen": 0.02},
        "mtbf_d": 60.0, "kinds": _REG + ("aerostat", "methane_lake"),
        "tech": "core:tech_is09a_gas_volatile_chem",
    },
    "basalt_furnace": {       # RX-17 (fiber line)
        "name": "Basalt fiber furnace RX-17 (T2)", "price_m": 10.0,
        "power_kw": 31.0,
        "primary": ("BasaltFiber", 500.0 / DAY),
        "inputs": {"Regolith": 1.05},
        "outputs": {"BasaltFiber": 1.0},
        "vented": {"offgas": 0.05},
        "mtbf_d": 65.0, "kinds": _REG,
        "tech": "core:tech_is09b_materials_chem",
    },
    "glass_furnace": {        # RX-17 (glass line)
        "name": "Glass furnace RX-17 (T2)", "price_m": 10.0,
        "power_kw": 31.0,
        "primary": ("Glass", 500.0 / DAY),
        "inputs": {"Regolith": 1.05},
        "outputs": {"Glass": 1.0},
        "vented": {"offgas": 0.05},
        "mtbf_d": 65.0, "kinds": _REG,
        "tech": "core:tech_is09b_materials_chem",
    },
    "ffc_titanium": {         # RX-18 (TiO2 slag feed folded)
        "name": "FFC titanium cell RX-18 (T3)", "price_m": 22.0,
        "power_kw": 47.0,
        "primary": ("Titanium", 25.0 / DAY),
        "inputs": {"Regolith": 1.67},
        "outputs": {"Titanium": 1.0, "Oxygen": 0.30, "Regolith": 0.37},
        "mtbf_d": 50.0, "kinds": _REG,
        "tech": "core:tech_is15_light_metals",
    },
    "mmh_loop": {             # RX-20 (DECISIONS B11)
        "name": "MMH synthesis loop RX-20 (T3)", "price_m": 14.0,
        "power_kw": 8.3,
        "primary": ("MMH", 25.0 / DAY),
        "inputs": {"Ammonia": 0.74, "Methane": 0.35},
        "outputs": {"MMH": 1.0, "Hydrogen": 0.09},
        "mtbf_d": 55.0, "kinds": _REG + ("aerostat", "methane_lake"),
        "tech": "core:tech_is09a_gas_volatile_chem",
    },
    "nto_plant": {            # RX-21 (DECISIONS B11)
        "name": "NTO arc synthesis RX-21 (T3)", "price_m": 16.0,
        "power_kw": 31.0,
        "primary": ("NTO", 50.0 / DAY),
        "inputs": {"Nitrogen": 0.30, "Oxygen": 0.70},
        "outputs": {"NTO": 1.0},
        "mtbf_d": 55.0, "kinds": _REG + ("aerostat", "methane_lake"),
        "tech": "core:tech_is09a_gas_volatile_chem",
    },
    "he3_kiln": {             # T4 [SPECULATIVE] — byproducts ARE the point
        "name": "He3 volatile kiln (T4)", "price_m": 220.0,
        "power_kw": 2_000.0,
        "primary": ("He3", 0.014 / DAY),
        "inputs": {"Regolith": 142_857.0},
        "outputs": {"He3": 1.0, "Hydrogen": 7_143.0, "Nitrogen": 14_286.0,
                    "Carbon": 21_428.0, "Water": 4_286.0,
                    "Regolith": 95_932.0},
        "mtbf_d": 40.0, "kinds": ("regolith",),
        "tech": "core:tech_is20_he3_kiln",
    },
    # ---- power, storage, people (09/07/08 — deepened in later chunks) ------
    "solar_array": {
        "name": "Solar array wing", "price_m": 6.0, "power_kw": -40.0,
        "primary": None, "inputs": {}, "outputs": {},
        "mtbf_d": None, "kinds": "*", "tech": None,
        "solar_scaled": True,        # generation scales with site sunlight
    },
    "reactor_100": {
        "name": "Fission reactor (100 kWe)", "price_m": 40.0,
        "power_kw": -100.0, "primary": None, "inputs": {}, "outputs": {},
        "mtbf_d": None, "kinds": "*", "tech": "core:tech_pw05_fission_surface",
        "heat_kw": 233.0,           # NUK-FSP canon thermal waste (09)
    },
    "reactor_kilo": {
        "name": "Kilopower unit (10 kWe)", "price_m": 9.0,
        "power_kw": -10.0, "primary": None, "inputs": {}, "outputs": {},
        "mtbf_d": None, "kinds": "*", "tech": "core:tech_pw04_kilopower",
        "heat_kw": 30.0,
    },
    "battery_pack": {
        "name": "Battery pack (400 kWh)", "price_m": 5.0, "power_kw": 0.0,
        "primary": None, "inputs": {}, "outputs": {},
        "mtbf_d": None, "kinds": "*", "tech": None,
        "cap_add": {"Battery": 400.0},
    },
    "radiator_wing": {
        "name": "Radiator wing", "price_m": 4.0, "power_kw": 0.0,
        "primary": None, "inputs": {}, "outputs": {},
        "mtbf_d": None, "kinds": "*", "tech": None,
        "heat_kw": -160.0,          # rejection capacity
    },
    "science_lab": {
        "name": "Field science lab", "price_m": 22.0, "power_kw": 15.0,
        "primary": None, "inputs": {}, "outputs": {},
        "mtbf_d": 70.0, "kinds": "*", "tech": None,
        "sci_per_day": 2.5,
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
                    "CO2": 40_000.0, "Nitrogen": 20_000.0,
                    "Ammonia": 10_000.0, "Argon": 5_000.0},
    },
    "yard_extension": {
        "name": "Bulk storage yard", "price_m": 5.0, "power_kw": 0.0,
        "primary": None, "inputs": {}, "outputs": {},
        "mtbf_d": None, "kinds": "*", "tech": None,
        "cap_add": {"Regolith": 2_000_000.0, "IronSteel": 200_000.0,
                    "Aluminum": 100_000.0, "Titanium": 50_000.0,
                    "Silicon": 100_000.0, "Carbon": 100_000.0,
                    "Polymers": 100_000.0, "BasaltFiber": 100_000.0,
                    "Glass": 100_000.0},
    },
}

# default buffer capacity by resource when a module first touches it
_DEFAULT_CAP = {
    "Regolith": 1_000_000.0, "IronSteel": 50_000.0, "Aluminum": 25_000.0,
    "Titanium": 10_000.0, "Silicon": 25_000.0, "Carbon": 25_000.0,
    "Polymers": 25_000.0, "BasaltFiber": 25_000.0, "Glass": 25_000.0,
    "RareEarths": 2_000.0, "Ammonia": 10_000.0, "Nitrogen": 20_000.0,
    "Argon": 5_000.0, "MMH": 5_000.0, "NTO": 10_000.0, "He3": 50.0,
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
    # founding battery: 50 kWh rides down with the lander (09 §3.2)
    net.buffers["Battery"] = Buffer(level=50.0, capacity=50.0)
    # relief vent BELOW one electrolyzer's H2 co-product (28 kg/day at
    # canon RX-01 rates): consumers (sabatier) get first call; without one
    # the tank still blocks eventually — build storage or burn it (the
    # Phase-3 lesson)
    net.add_source(Source("h2_vent", "Hydrogen", -0.0001))
    add_module(net, "solar_array", site, serial=0)
    return net


def ensure_buffers(net: LedgerNetwork, spec: dict) -> None:
    """Every resource a module touches gets a pool (04's one-buffer-per-
    resource rule); capacities from the class table."""
    for res in list(spec["inputs"]) + list(spec["outputs"]):
        if res not in net.buffers:
            net.buffers[res] = Buffer(
                level=0.0, capacity=_DEFAULT_CAP.get(res, 20_000.0))


def add_module(net: LedgerNetwork, key: str, site: dict,
               serial: int) -> Module:
    spec = CATALOG[key]
    power = spec["power_kw"]
    if power < 0.0 and spec.get("solar_scaled"):
        power *= site.get("solar", 1.0)
    rate = spec["primary"][1] if spec["primary"] else 0.0
    ensure_buffers(net, spec)
    mod = Module(
        module_id=f"{key}_{serial}",
        inputs=dict(spec["inputs"]),
        outputs=dict(spec["outputs"]),
        rate_kgps=rate,
        power_kw=power,
        heat_kw=spec.get("heat_kw", 0.0),
    )
    if spec["mtbf_d"]:
        mod.mtbf_s = spec["mtbf_d"] * DAY
    net.add_module(mod)
    for res, extra in spec.get("cap_add", {}).items():
        if res in net.buffers:
            net.buffers[res].capacity += extra
        else:
            net.buffers[res] = Buffer(level=0.0, capacity=extra)
    return mod
