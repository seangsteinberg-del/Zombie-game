"""Production chains (05 §1): the 15 canonical recipes, the 17 fab
modules, and the laws that bind them — F-1 effective throughput, the
F-Y wafer yield ramp, the generated power column (§4.1 and §4.2 cannot
disagree because one is computed from the other), the construction
parts bill, the in-situ derate F-13, the local-electronics ×1.3 penalty
(DECISIONS B12), and the RX-22 recycling split (DECISIONS B16).

All recipes are normalized per 1.00 t of primary output and must close
mass balance within 0.5% — `validate_chains()` is called by the tests
and may be called at load."""

from __future__ import annotations

import math

# new intermediate resources (exact spellings, §1.1)
NEW_RESOURCES = ("MetalStock", "Components", "Wafers")

# ---- recipes (§1.5, complete) -------------------------------------------------
# labor: (crew_h_per_t, robot_h_per_t); min_automation defaults to the
# module's rung; env defaults to the module's env.
RECIPES: dict[str, dict] = {
    "stock_std": {
        "module": "fab_foundry_mill", "tier": "T1",
        "inputs_t": {"IronSteel": 0.68, "Aluminum": 0.22,
                     "Titanium": 0.05, "Copper": 0.05},
        "outputs_t": {"MetalStock": 0.97}, "byproducts_t": {},
        "loss_t": 0.03, "energy_kwh_per_t": 700, "labor": (0.4, 2.4)},
    "stock_lunar": {
        "module": "fab_foundry_mill", "tier": "T2",
        "inputs_t": {"Aluminum": 0.55, "IronSteel": 0.35,
                     "Titanium": 0.10},
        "outputs_t": {"MetalStock": 0.96}, "byproducts_t": {},
        "loss_t": 0.04, "energy_kwh_per_t": 780, "labor": (0.4, 2.4)},
    "stock_nea": {
        "module": "fab_foundry_mill", "tier": "T2",
        "inputs_t": {"IronSteel": 0.92, "Copper": 0.08},
        "outputs_t": {"MetalStock": 0.97}, "byproducts_t": {},
        "loss_t": 0.03, "energy_kwh_per_t": 650, "labor": (0.4, 2.4)},
    "comp_machined": {
        "module": "fab_machine_shop", "tier": "T1",
        "inputs_t": {"MetalStock": 1.04},
        "outputs_t": {"Components": 1.00}, "byproducts_t": {},
        "loss_t": 0.04, "energy_kwh_per_t": 1_500, "labor": (16.0, 32.0)},
    "comp_printed": {
        "module": "fab_printer_lpbf", "tier": "T1",
        "inputs_t": {"MetalStock": 1.06},
        "outputs_t": {"Components": 1.00}, "byproducts_t": {},
        "loss_t": 0.06, "energy_kwh_per_t": 30_000, "labor": (2.0, 12.0)},
    "comp_poly": {
        "module": "fab_printer_poly", "tier": "T0",
        "inputs_t": {"Polymers": 1.05},
        "outputs_t": {"Components": 1.00}, "byproducts_t": {},
        "loss_t": 0.05, "energy_kwh_per_t": 400, "labor": (4.0, 0.0)},
    "struct_waam": {
        "module": "fab_waam", "tier": "T2",
        "inputs_t": {"MetalStock": 1.05, "Polymers": 0.02},
        "outputs_t": {"StructuralParts": 1.00}, "byproducts_t": {},
        "loss_t": 0.07, "energy_kwh_per_t": 6_000, "labor": (1.0, 12.0),
        "min_automation": "A2"},
    "struct_basalt": {
        "module": "fab_waam", "tier": "T2",
        "inputs_t": {"BasaltFiber": 0.60, "Polymers": 0.25,
                     "MetalStock": 0.22},
        "outputs_t": {"StructuralParts": 1.00}, "byproducts_t": {},
        "loss_t": 0.07, "energy_kwh_per_t": 900, "labor": (1.0, 12.0),
        "min_automation": "A2", "surface_only_rating": True},
    "machparts_std": {
        "module": "fab_assembly_hall", "tier": "T2",
        "inputs_t": {"Components": 0.62, "MetalStock": 0.43},
        "outputs_t": {"MachineParts": 1.00}, "byproducts_t": {},
        "loss_t": 0.05, "energy_kwh_per_t": 300, "labor": (4.0, 16.0),
        "min_automation": "A1"},
    "machparts_shop": {
        "module": "fab_machine_shop", "tier": "T1",
        "inputs_t": {"Components": 0.65, "MetalStock": 0.42},
        "outputs_t": {"MachineParts": 1.00}, "byproducts_t": {},
        "loss_t": 0.07, "energy_kwh_per_t": 350, "labor": (12.0, 12.0),
        "rate_mult": 0.25},          # the slow path
    "polymers_mto": {
        "module": "fab_chem_plant", "tier": "T1",
        "inputs_t": {"Methane": 1.20, "Oxygen": 1.20},
        "outputs_t": {"Polymers": 1.00},
        "byproducts_t": {"Water": 1.22, "CO2": 0.16, "Hydrogen": 0.02},
        "loss_t": 0.00, "energy_kwh_per_t": 1_500, "labor": (0.5, 3.0)},
    "wafers_min": {
        "module": "fab_wafer_fab", "tier": "T3",
        "inputs_t": {"Silicon": 1.60, "Polymers": 2.0, "Copper": 0.10,
                     "Nitrogen": 30.0, "Water": 60.0},
        "outputs_t": {"Wafers": 1.00},
        "byproducts_t": {"Nitrogen": 24.0, "Water": 54.0},   # recovered
        "loss_t": 14.7, "energy_kwh_per_t": 8_000_000,
        "labor": (2_000.0, 20_000.0), "min_crew_hour_frac": 0.10},
    "electronics_std": {
        "module": "fab_elec_assy", "tier": "T1",
        "inputs_t": {"Copper": 0.35, "Polymers": 0.30, "Aluminum": 0.19,
                     "Glass": 0.11, "IronSteel": 0.07, "RareEarths": 0.02,
                     "Wafers": 0.01},
        "outputs_t": {"Electronics": 1.00}, "byproducts_t": {},
        "loss_t": 0.05, "energy_kwh_per_t": 3_000, "labor": (40.0, 80.0)},
    "ration_pack": {
        "module": "fab_consumables", "tier": "T1",
        "inputs_t": {"Biomass": 2.10, "Polymers": 0.05},
        "outputs_t": {"FoodRations": 1.00},
        "byproducts_t": {"Water": 1.10},        # recovered to the 08 loop
        "loss_t": 0.05, "energy_kwh_per_t": 1_800, "labor": (2.0, 6.0)},
    "medsupplies_std": {
        "module": "fab_consumables", "tier": "T2",
        "inputs_t": {"Polymers": 0.50, "Electronics": 0.30,
                     "Biomass": 0.20},
        "outputs_t": {"MedSupplies": 1.00}, "byproducts_t": {},
        "loss_t": 0.00, "energy_kwh_per_t": 2_500, "labor": (30.0, 30.0)},
}

# ---- fab modules (§1.6, complete) ----------------------------------------------
# rate_t_day: nominal throughput of the PRIMARY recipe in t/day.
# env: P pressurized, V vacuum-rated, S surface only (or combos).
FAB_MODULES: dict[str, dict] = {
    "fab_printer_poly": {
        "name": "Polymer printer farm", "tier": "T0", "env": "P",
        "mass_t": 0.8, "p_hotel_kwe": 2.6, "rate_t_day": 0.025,
        "recipe": "comp_poly", "small": True, "rung": "A0"},
    "fab_printer_lpbf": {
        "name": "Metal printer cell (LPBF)", "tier": "T1", "env": "P",
        "mass_t": 3.0, "p_hotel_kwe": 2.0, "rate_t_day": 0.020,
        "recipe": "comp_printed", "small": True, "rung": "A1"},
    "fab_machine_shop": {
        "name": "Machine shop", "tier": "T1", "env": "P",
        "mass_t": 8.0, "p_hotel_kwe": 3.75, "rate_t_day": 0.5,
        "recipe": "comp_machined", "rung": "A1"},
    "fab_foundry_mill": {
        "name": "Foundry & mill", "tier": "T1", "env": "S",
        "mass_t": 25.0, "p_hotel_kwe": 14.0, "rate_t_day": 5.0,
        "recipe": "stock_std", "rung": "A1", "warmup_h": 6.0,
        "peak_kwe": 300.0},
    "fab_chem_plant": {
        "name": "Chemical plant", "tier": "T1", "env": "SV",
        "mass_t": 15.0, "p_hotel_kwe": 15.0, "rate_t_day": 2.0,
        "recipe": "polymers_mto", "rung": "A1"},
    "fab_elec_assy": {
        "name": "Electronics assembly line", "tier": "T1", "env": "P",
        "mass_t": 10.0, "p_hotel_kwe": 7.5, "rate_t_day": 0.1,
        "recipe": "electronics_std", "rung": "A1"},
    "fab_consumables": {
        "name": "Consumables line", "tier": "T1", "env": "P",
        "mass_t": 6.0, "p_hotel_kwe": 4.0, "rate_t_day": 0.5,
        "recipe": "ration_pack", "alt_recipe": "medsupplies_std",
        "alt_rate_t_day": 0.05, "rung": "A0"},
    "fab_workshop": {
        "name": "Pressurized workshop", "tier": "T1", "env": "P",
        "mass_t": 13.0, "p_hotel_kwe": 12.0, "rate_t_day": 0.0,
        "recipe": None, "hosts_small": 2, "repair_bonus": 0.25,
        "rung": "A0"},
    "fab_waam": {
        "name": "Large-format WAAM/DED cell", "tier": "T2", "env": "PV",
        "mass_t": 12.0, "p_hotel_kwe": 2.5, "rate_t_day": 0.15,
        "recipe": "struct_waam", "rung": "A2"},
    "fab_assembly_hall": {
        "name": "Parts assembly hall", "tier": "T2", "env": "P",
        "mass_t": 20.0, "p_hotel_kwe": 10.0, "rate_t_day": 2.0,
        "recipe": "machparts_std", "rung": "A1"},
    "fab_sinter_printer": {
        "name": "Regolith sinter printer", "tier": "T2", "env": "S",
        "mass_t": 12.0, "p_hotel_kwe": 5.0, "rate_t_day": 2.0,
        "recipe": None, "process_kwh_per_t": 500.0, "rung": "A2",
        "in_place": True},
    "fab_filament_winder": {
        "name": "Basalt filament winder", "tier": "T2", "env": "S",
        "mass_t": 4.0, "p_hotel_kwe": 2.0, "rate_t_day": 0.5,
        "recipe": None, "process_kwh_per_t": 150.0, "rung": "A2",
        "in_place": True},
    "fab_ice_caster": {
        "name": "Ice casting rig", "tier": "T2", "env": "S",
        "mass_t": 3.0, "p_hotel_kwe": 2.0, "rate_t_day": 4.6,
        "recipe": None, "process_kwh_per_t": 32.6, "rung": "A2",
        "in_place": True},                 # 30 kWh/m³ at 0.92 t/m³
    "yard_drydock": {
        "name": "Orbital dry dock", "tier": "T2", "env": "V",
        "mass_t": 85.0, "p_hotel_kwe": 30.0, "rate_t_day": 0.0,
        "recipe": None, "rung": "A2", "peak_kwe": 180.0,
        "arm_pairs": 2, "gang_slots": 3, "cargo_equipped": True},
    "fab_wafer_fab": {
        "name": "Wafer fab (Minimal-Fab line)", "tier": "T3", "env": "P",
        "mass_t": 45.0, "p_hotel_kwe": 33.0, "rate_t_day": 0.002,
        "recipe": "wafers_min", "rung": "A3", "warmup_h": 72.0,
        "peak_kwe": 900.0, "parts_split": (0.25, 0.25, 0.40, 0.10),
        "no_vibration": True},
    "fab_auto_complex": {
        "name": "Autonomous factory complex", "tier": "T3", "env": "S",
        "mass_t": 120.0, "p_hotel_kwe": 398.0, "rate_t_day": 0.0,
        "recipe": None, "rung": "A3", "chi": 0.90,
        "bundle": {"MetalStock": 5.0, "Components": 0.5,
                   "MachineParts": 2.0},
        "bundle_kwe": 202.0},
    "fab_replicator_seed": {
        "name": "Self-expanding industry seed", "tier": "T4", "env": "S",
        "mass_t": 250.0, "p_hotel_kwe": 0.0, "rate_t_day": 0.0,
        "recipe": None, "rung": "A4", "chi": 0.98, "spec": True,
        "power_kwe_flat": 1_500.0},
}

WARMUP_DEFAULT_H = 0.5


def warmup_h(module_id: str) -> float:
    return FAB_MODULES[module_id].get("warmup_h", WARMUP_DEFAULT_H)


def power_kwe(module_id: str) -> float:
    """The generated §4.1 Power column: P_hotel + kWh/t × rate / 24 —
    §4.1 and §4.2 cannot disagree because this is the only source."""
    m = FAB_MODULES[module_id]
    if "power_kwe_flat" in m:
        return m["power_kwe_flat"]
    p = m["p_hotel_kwe"]
    if m.get("recipe"):
        p += RECIPES[m["recipe"]]["energy_kwh_per_t"] * m["rate_t_day"] / 24.0
    elif m.get("process_kwh_per_t"):
        p += m["process_kwh_per_t"] * m["rate_t_day"] / 24.0
    elif m.get("bundle_kwe"):
        p += m["bundle_kwe"]
    return p


def alt_power_kwe(module_id: str) -> float:
    """Power on the alternate recipe (consumables line making meds)."""
    m = FAB_MODULES[module_id]
    r = RECIPES[m["alt_recipe"]]
    return m["p_hotel_kwe"] + r["energy_kwh_per_t"] * m["alt_rate_t_day"] / 24.0


HEAT_FRACTION_DEFAULT = 0.95


def heat_kw(module_id: str) -> float:
    """heat_fraction of total consumed electrical energy must be
    radiator-rejected at the site (§1.8)."""
    return power_kwe(module_id) * HEAT_FRACTION_DEFAULT


def heat_cascade_credit(foundry_heat_kw: float,
                        receiver_demand_kw: float) -> float:
    """Foundry co-sited with 04 thermal-ISRU: receiver demand drops by
    min(0.20 × foundry heat, 0.15 × receiver demand); radiator load
    drops the same amount (§1.8)."""
    return min(0.20 * foundry_heat_kw, 0.15 * receiver_demand_kw)


# ---- F-1 effective throughput ---------------------------------------------------
def f_power(p_supplied_kw: float, p_required_kw: float) -> float:
    if p_required_kw <= 0.0:
        return 1.0
    return max(0.0, min(1.0, p_supplied_kw / p_required_kw))


POWER_TRIP_OFF = 0.3        # module trips OFF below this f_power
FOUNDRY_FREEZE_F = 0.8      # f_power < 0.8 continuously > 1 h => freeze
FOUNDRY_FREEZE_H = 1.0


def f_condition(c: float) -> float:
    """Full rate while C >= 0.5, then linear to zero (F-1)."""
    return 1.0 if c >= 0.5 else max(0.0, c / 0.5)


def r_eff(r_nom_t_day: float, fp: float, fl: float, fc: float,
          y: float = 1.0) -> float:
    return r_nom_t_day * fp * fl * fc * y


def y_wafer(days_since_ramp: float) -> float:
    """F-Y yield ramp: 0.2 on day 0 climbing to 0.9; restarts after
    commissioning or any major fault (the 72 h requal precedes it)."""
    return 0.9 - 0.7 * math.exp(-days_since_ramp / 60.0)


# ---- construction parts bill (§1.6) ---------------------------------------------
# (StructuralParts, MachineParts, Electronics, Polymers)
PARTS_SPLIT_DEFAULT = (0.55, 0.30, 0.08, 0.07)
PARTS_SPLIT = {
    "fab_wafer_fab": (0.25, 0.25, 0.40, 0.10),
    "robot": (0.25, 0.45, 0.25, 0.05),
    "depot": (0.70, 0.20, 0.05, 0.05),
    "log_massdriver": (0.60, 0.30, 0.08, 0.02),
}
PARTS_KEYS = ("StructuralParts", "MachineParts", "Electronics", "Polymers")


def parts_bill(mass_t: float, kind: str = "") -> dict[str, float]:
    split = PARTS_SPLIT.get(kind, PARTS_SPLIT_DEFAULT)
    return {k: mass_t * s for k, s in zip(PARTS_KEYS, split)}


# ---- DECISIONS B12 + F-13 -------------------------------------------------------
LOCAL_ELECTRONICS_MULT = 1.3    # micron-class wafers: ×1.3 at install,
                                # retires at T3+ fab maturity

K_INSITU = {"T2": 4.0, "T3": 3.0, "T4": 2.0}    # F-13 derate


def insitu_mass_t(catalog_mass_t: float, tier: str) -> float:
    """Locally built stand-ins for imported precision hardware install
    at k_insitu × catalog mass (F-13)."""
    return K_INSITU.get(tier, 1.0) * catalog_mass_t


# ---- RX-22 recycling (DECISIONS B16) ---------------------------------------------
RECYCLE_RECLAIM = 0.80


def recycle(loss_t: float) -> tuple[float, float]:
    """(reclaimed resources, Regolith residue). Without a co-sited
    Recycler the loss stream is destroyed."""
    return loss_t * RECYCLE_RECLAIM, loss_t * (1.0 - RECYCLE_RECLAIM)


# ---- progression (§3.5) ----------------------------------------------------------
EARTH_IMPORT_FRACTION = {"T0": 1.00, "T1": 0.60, "T2": 0.25, "T3": 0.05,
                         "T4": 0.0}


# ---- validation -------------------------------------------------------------------
def validate_chains(tol: float = 0.005) -> list[str]:
    """Mass balance must close within 0.5% on every recipe; the parts
    splits must sum to 1. Returns a list of violations (empty = clean)."""
    bad = []
    for rid, r in RECIPES.items():
        m_in = sum(r["inputs_t"].values())
        m_out = (sum(r["outputs_t"].values())
                 + sum(r["byproducts_t"].values()) + r["loss_t"])
        if m_in <= 0 or abs(m_in - m_out) / m_in > tol:
            bad.append(f"{rid}: in {m_in:.3f} t vs out {m_out:.3f} t")
    for kind, split in list(PARTS_SPLIT.items()) + [("", PARTS_SPLIT_DEFAULT)]:
        if abs(sum(split) - 1.0) > 1e-9:
            bad.append(f"parts split {kind or 'default'} sums {sum(split)}")
    return bad
