"""ECLSS closure ladder (08 §2): the LS-* hardware catalog with canon
mass/power/capacity/spares, the per-subsystem closure fractions η that
EMERGE from what's installed, the ISS-loop stoichiometry (OGA/Sabatier/
Bosch), the three-pool water loop, and net daily resupply per crew.
"""

from __future__ import annotations

# ISS physico-chemical loop stoichiometry (08 §2.3)
OGA_H2O_PER_O2 = 1.125           # kg water electrolyzed per kg O2
OGA_H2_PER_O2 = 0.125            # kg H2 byproduct per kg O2
SAB_H2_PER_CO2 = 0.182           # Sabatier: kg H2 per kg CO2 reduced
SAB_CH4_PER_CO2 = 0.364          # kg CH4 made (vented or stored)
SAB_H2O_PER_CO2 = 0.818          # kg water recovered
BOSCH_C_PER_CO2 = 0.273          # Bosch deposits solid carbon

# metabolic resupply baselines (08 §2.2); A scales O2 only
O2_KG_DAY = 0.84
WATER_KG_DAY = 3.5               # 2.5 drink+prep + 1.0 hygiene (canon)
FOOD_DRY_KG_DAY = 0.62

# LS hardware catalog (08 §2.6) — canonical numbers
# capacity_crew: crew served per unit; spares feed on MedSupplies kg/yr
CATALOG = {
    "LS-OPEN":  {"name": "Stored-consumables rack", "tier": 0,
                 "mass_t": 0.3, "power_kw": 0.3, "crew": 4,
                 "spares_kg_yr": 0.0},   # LiOH burn handled as 0.55/crew/d
    "LS-CDRA":  {"name": "CO2 removal (CDRA)", "tier": 1,
                 "mass_t": 0.7, "power_kw": 1.0, "crew": 6,
                 "spares_kg_yr": 8.0},
    "LS-OGA":   {"name": "O2 generation (electrolysis)", "tier": 1,
                 "mass_t": 0.7, "power_kw": 3.6, "crew": 6,
                 "spares_kg_yr": 10.0},
    "LS-SAB":   {"name": "Sabatier CO2 reducer", "tier": 2,
                 "mass_t": 0.4, "power_kw": 0.5, "crew": 6,
                 "spares_kg_yr": 6.0},
    "LS-BOSCH": {"name": "Bosch CO2 reducer", "tier": 2,
                 "mass_t": 0.6, "power_kw": 1.2, "crew": 6,
                 "spares_kg_yr": 12.0},
    "LS-WRS":   {"name": "Water recovery (UPA+WPA)", "tier": 1,
                 "mass_t": 1.5, "power_kw": 1.3, "crew": 6,
                 "spares_kg_yr": 15.0},
    "LS-BPA":   {"name": "Brine processor add-on", "tier": 2,
                 "mass_t": 0.3, "power_kw": 0.4, "crew": 6,
                 "spares_kg_yr": 4.0},
    "LS-CHX":   {"name": "Condensing heat exchanger", "tier": 0,
                 "mass_t": 0.2, "power_kw": 0.4, "crew": 6,
                 "spares_kg_yr": 3.0},
    "LS-ALGAE": {"name": "Algae photobioreactor", "tier": 3,
                 "mass_t": 2.0, "power_kw": 19.0, "crew": 4,
                 "spares_kg_yr": 5.0},   # 32 m² × 0.60 kW/m² light
    "LS-N2":    {"name": "Buffer-gas regulator", "tier": 0,
                 "mass_t": 0.1, "power_kw": 0.1, "crew": 99,
                 "spares_kg_yr": 0.0},
}

LIOH_KG_CREW_DAY = 0.55          # open-loop CO2 cartridge burn (LS-OPEN)

# EVA suit consumables (08 §4.7, EMU anchor)
SUIT_O2_KGPH = 0.09
SUIT_COOLING_KGPH = 0.40         # sublimator water, lost to space
SUIT_ENDURANCE_H = 8.0


def closure(units: dict[str, int], agronomist: bool = False) -> dict:
    """Closure fractions η from the installed unit counts (08 §2.1).
    Food closure lives in food.py (greenhouses); this reports the
    physico-chemical air/water ladder."""
    has = {uid for uid, n in units.items() if n > 0}
    eta_co2 = 1.0 if ("LS-CDRA" in has or "LS-ALGAE" in has) else 0.0
    if "LS-ALGAE" in has:
        eta_o2 = 0.95
    elif "LS-BOSCH" in has and "LS-OGA" in has:
        eta_o2 = 0.50
    elif "LS-SAB" in has and "LS-OGA" in has:
        eta_o2 = 0.42
    else:
        eta_o2 = 0.0
    if "LS-WRS" in has:
        eta_h2o = 0.98 if "LS-BPA" in has else 0.90
    else:
        eta_h2o = 0.0
    return {"co2rm": eta_co2, "o2": eta_o2, "h2o": eta_h2o}


def capacities_kgph(units: dict[str, int]) -> dict:
    """Hardware throughput for the cabin ODE: CO2 scrub kg/h, O2 generation
    kg/h (water-fed), CHX condensate kg/h. Sized from per-unit crew
    ratings × metabolic canon."""
    n = lambda uid: units.get(uid, 0)
    scrub = (n("LS-CDRA") * 6 * 1.0 / 24.0     # CDRA: 6 crew × 1 kg/day
             + n("LS-ALGAE") * 4 * 1.0 / 24.0)
    o2gen = n("LS-OGA") * 6 * O2_KG_DAY * 2.0 / 24.0   # ×2 design margin
    chx = (n("LS-CHX") + n("LS-CDRA")) * 6 * 2.3 * 2.0 / 24.0
    return {"scrub": scrub, "o2_gen": o2gen, "chx": chx}


def power_kw(units: dict[str, int]) -> float:
    return sum(CATALOG[uid]["power_kw"] * n for uid, n in units.items()
               if uid in CATALOG)


def spares_kg_day(units: dict[str, int]) -> float:
    """MedSupplies draw for filters/cartridges/maintenance (08 §2.6)."""
    return sum(CATALOG[uid]["spares_kg_yr"] * n / 365.0
               for uid, n in units.items() if uid in CATALOG)


def daily_resupply(units: dict[str, int], crew_n: int,
                   activity: float = 1.0) -> dict:
    """Net kg/day the loop CANNOT close (08 §2.2) — what stores or ISRU
    must cover. O2 line assumes a water-fed OGA when present (the Act-2
    play: local water → breathing O2, debited as water instead)."""
    eta = closure(units)
    o2_short = (1.0 - eta["o2"]) * O2_KG_DAY * activity * crew_n
    has_oga = units.get("LS-OGA", 0) > 0
    return {
        "o2": 0.0 if has_oga else o2_short,
        "water_for_o2": o2_short * OGA_H2O_PER_O2 if has_oga else 0.0,
        "water": (1.0 - eta["h2o"]) * WATER_KG_DAY * crew_n,
        "food_dry": FOOD_DRY_KG_DAY * crew_n,    # food.py closes this
        "lioh": (LIOH_KG_CREW_DAY * crew_n
                 if eta["co2rm"] == 0.0 else 0.0),
        "spares": spares_kg_day(units),
    }


class WaterLoop:
    """Three pools (08 §2.5): Potable, Grey/condensate, Urine/brine.
    step_day moves crew flows through WPA/UPA(/BPA) and returns the
    potable makeup still owed (draw it from stores or ISRU)."""

    def __init__(self, potable: float = 0.0, grey: float = 0.0,
                 urine: float = 0.0) -> None:
        self.potable = potable
        self.grey = grey
        self.urine = urine
        self.brine_lost = 0.0

    def step_day(self, crew_n: int, units: dict[str, int],
                 condensate_kg: float = 0.0, days: float = 1.0,
                 activity: float = 1.0) -> dict:
        has_wrs = units.get("LS-WRS", 0) > 0
        has_bpa = units.get("LS-BPA", 0) > 0
        drink = 2.5 * crew_n * days
        hyg = 1.0 * crew_n * days
        self.potable -= drink + hyg
        self.grey += hyg + condensate_kg
        self.urine += 1.6 * crew_n * days
        if has_wrs:
            # UPA: urine → grey at 0.85 (brine), BPA recovers the brine
            recovered = self.urine * (0.95 if has_bpa else 0.85)
            self.brine_lost += self.urine - recovered
            self.grey += recovered
            self.urine = 0.0
            # WPA: grey → potable at 0.93
            self.potable += self.grey * 0.93
            self.brine_lost += self.grey * 0.07
            self.grey = 0.0
        shortfall = max(0.0, -self.potable)
        self.potable = max(0.0, self.potable)
        return {"shortfall": shortfall, "brine_lost": self.brine_lost}
