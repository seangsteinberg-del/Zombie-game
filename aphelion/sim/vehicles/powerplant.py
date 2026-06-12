"""Vehicle energy sources (10 §2.2): the 09 storage catalog mounted
unmodified, the V-9 methalox ICE/turbine and V-10 Titan O2-breather
combustion laws, the per-kg-carried UI ladder, recharge paths
(umbilical / swap pallet), the Li-pack 273 K charge gate, and the
V-0d power-closure check that validates a chassis at its destination
body's insolation."""

from __future__ import annotations

# ---- storage catalog (09 rows, mounted unmodified) -------------------------------
STORAGE = {
    "STO-LI": {"wh_kg": 150.0, "tier": 0, "surge": False},
    "STO-SS": {"wh_kg": 250.0, "tier": 1, "surge": False},
    "STO-LS": {"wh_kg": 350.0, "tier": 2, "surge": True},
    # STO-RFC is fuel-keyed, not Wh/kg-keyed: 2.0 kWh_e per kg reactants.
    "STO-RFC": {"kwh_e_per_kg_reactants": 2.0, "tier": 2, "surge": False},
}
RFC_KWH_E_PER_KG = 2.0          # STO-RFC reactant energy density

USABLE_PACK = 0.85              # rechargeable packs (mirrors locomotion.py)
USABLE_PRIMARY = 0.90           # primary cells


def usable_kwh(pack_kwh: float, rechargeable: bool = True) -> float:
    """Usable fraction: 0.85 rechargeable, 0.9 primary cells."""
    return pack_kwh * (USABLE_PACK if rechargeable else USABLE_PRIMARY)


# ---- V-9 methalox ICE/turbine (T2) -----------------------------------------------
# Canon: 1 kg CH4 + 4 kg O2 → 0.83 kWh_mech per kg of reactants (η 0.30).
# Internal consistency: 0.2 kg CH4/kg reactants × 50 MJ/kg LHV × 0.30 / 3.6
# = 0.833 kWh/kg; the stated 0.83 canon constant wins.
ETA_COMBUSTION = 0.30
OF_RATIO = 4.0                  # kg O2 per kg CH4
METHALOX_KWH_PER_KG = 0.83      # kWh_mech per kg of reactants


def methalox_kwh(reactants_kg: float) -> float:
    """V-9: mechanical energy from a mixed CH4+O2 reactant mass."""
    return reactants_kg * METHALOX_KWH_PER_KG


def reactants_for_kwh(kwh: float) -> float:
    """V-9 inverse: reactant mass to deliver kWh_mech."""
    return kwh / METHALOX_KWH_PER_KG


def methalox_split(reactants_kg: float) -> tuple[float, float]:
    """V-9 stoichiometry: (CH4 kg, O2 kg) at O/F 4.0."""
    ch4 = reactants_kg / (1.0 + OF_RATIO)
    return ch4, ch4 * OF_RATIO


# ---- V-10 Titan O2-breather (T4 SPECULATIVE) --------------------------------------
# Carry ONLY O2; ingest ambient CH4 from Titan air (0.25 kg CH4 per kg O2,
# never ledgered in). Exhaust vents as snow and is NOT ledgered either.
BREATHER_KWH_PER_KG_O2 = 1.04   # kWh_mech per kg O2 carried (η 0.30)
BREATHER_CH4_PER_KG_O2 = 0.25   # ambient ingest, informational only


def breather_kwh(o2_kg: float) -> float:
    """V-10: mechanical energy from carried O2 alone."""
    return o2_kg * BREATHER_KWH_PER_KG_O2


def o2_for_kwh(kwh: float) -> float:
    """V-10 inverse: O2 mass to deliver kWh_mech."""
    return kwh / BREATHER_KWH_PER_KG_O2


# ---- per-kg-carried UI ladder (10 §2.2) -------------------------------------------
PER_KG_KWH = {
    "battery_t1": 0.25,         # STO-SS
    "rfc": 2.0,                 # STO-RFC reactants
    "methalox": 0.83,           # V-9
    "titan_o2": 1.04,           # V-10
}


# ---- recharge paths ---------------------------------------------------------------
# Onboard solar recharge uses the 09 f_atm hook (sim/power.py; Titan ≈
# decoration) — out of scope for this module.
def umbilical_hours(pack_kwh: float, rate_kw: float) -> float:
    """Base umbilical charges at the pack's max rate."""
    return pack_kwh / rate_kw


SWAP_PALLET = {                 # T2: 300 kWh STO-SS module, 10 min at a garage
    "kwh": 300.0,
    "mass_t": 1.2,
    "minutes": 10.0,
    "where": "garage",
}

LI_CHARGE_MIN_K = 273.0         # heater is P0; brick rules live in thermal.py


def can_charge(t_k: float) -> bool:
    """Li packs cannot charge below 273 K — just the gate, not the brick."""
    return t_k >= LI_CHARGE_MIN_K


# ---- V-0d power closure (chassis validation) --------------------------------------
def power_closure(drive_w: float, hotel_w: float,
                  source_w: float) -> tuple[bool, float]:
    """V-0d: continuous drive + hotel must fit within source output at
    the destination body's insolation. Returns (ok, margin_w)."""
    margin_w = source_w - (drive_w + hotel_w)
    return margin_w >= 0.0, margin_w
