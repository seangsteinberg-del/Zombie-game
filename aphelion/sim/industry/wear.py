"""Spares & maintenance economy (05 §3.4): F-7 wear, F-8 Poisson
failures with severity, F-9 the annual spares budget (THE difficulty
knob), the complete §4.6 maintenance table, dust multipliers,
cannibalization, death-spiral detection, and the blueprint laws
F-10/F-11/F-12. One wear system serves modules, robots, AND vehicles
(DECISIONS A5 — orthogonal multipliers, no double counting)."""

from __future__ import annotations

import math
from dataclasses import dataclass

# ---- F-7 wear ---------------------------------------------------------------------


def wear_dc(u: float, hours: float, l_wear_h: float,
            wear_per_t: float = 1.0, dust: bool = False) -> float:
    """Condition lost over `hours` at utilization u (dust doubles wear)."""
    mult = 2.0 if dust else 1.0
    return (u * wear_per_t * mult / l_wear_h) * hours


PM_RESTORE = 0.25           # PM restores C +0.25, capped at 1.0


def after_pm(c: float) -> float:
    return min(1.0, c + PM_RESTORE)


# ---- F-8 failures ------------------------------------------------------------------
MINOR_P = 0.95
MINOR_LABOR_H = (4.0, 12.0)         # uniform
MINOR_PARTS_FRAC = 0.001            # 0.1% module mass in parts
MAJOR_LABOR_H = (24.0, 40.0)
MAJOR_PARTS_FRAC = 0.010
UNCOMMISSIONED_HAZARD = 3.0         # ×3 for the first 90 days
UNCOMMISSIONED_DAYS = 90.0


def fail_rate_per_h(mtbf_h: float, c: float, dust: bool = False,
                    commissioned: bool = True) -> float:
    """P_fail/op-h = (1/MTBF) × (2 − C); dust cuts MTBF ×0.6;
    skipping commissioning triples the hazard for 90 days."""
    mtbf = mtbf_h * (0.6 if dust else 1.0)
    rate = (1.0 / mtbf) * (2.0 - c)
    return rate * (UNCOMMISSIONED_HAZARD if not commissioned else 1.0)


def roll_failure(rng, module_mass_t: float,
                 split: tuple[float, float, float, float]) -> dict:
    """Severity roll at failure (rng = np.random.Generator). Returns
    labor hours + the parts draw (drawn from STORAGE, never inline)."""
    minor = rng.random() < MINOR_P
    lo, hi = MINOR_LABOR_H if minor else MAJOR_LABOR_H
    frac = MINOR_PARTS_FRAC if minor else MAJOR_PARTS_FRAC
    parts_t = module_mass_t * frac
    keys = ("MachineParts", "Electronics", "StructuralParts", "Polymers")
    return {"severity": "minor" if minor else "major",
            "labor_h": float(rng.uniform(lo, hi)),
            "parts": {k: parts_t * s for k, s in zip(keys, split) if s > 0}}


# ---- F-9 annual spares budget --------------------------------------------------------
K_ENV = {"orbital": 0.02, "dusty": 0.04, "clean": 0.03}


def m_spares_t_yr(module_mass_t: float, env: str) -> float:
    """M_spares = k_env × M_module per year ([PLAYTEST] knob)."""
    return K_ENV[env] * module_mass_t


# ---- §4.6 maintenance table (complete) -------------------------------------------------
# split = (MachineParts, Electronics, StructuralParts, Polymers)
@dataclass(frozen=True, slots=True)
class Maint:
    mtbf_h: float
    l_wear_h: float
    pm_interval_h: float
    pm_cost: dict
    split: tuple[float, float, float, float]


MAINT: dict[str, Maint] = {
    "printer_farm": Maint(1_500, 6_000, 500,
                          {"MachineParts": 0.005, "crew_h": 2},
                          (0.60, 0.25, 0.05, 0.10)),
    "lpbf_cell": Maint(1_200, 5_000, 400,
                       {"MachineParts": 0.008, "crew_h": 3},
                       (0.55, 0.35, 0.0, 0.10)),
    "machine_shop": Maint(1_800, 8_000, 500,
                          {"MachineParts": 0.015, "crew_h": 4},
                          (0.70, 0.20, 0.05, 0.05)),
    "foundry_mill": Maint(2_500, 12_000, 750,
                          {"MachineParts": 0.040, "Polymers": 0.010,
                           "robot_h": 8},
                          (0.60, 0.15, 0.20, 0.05)),
    "chem_plant": Maint(3_500, 15_000, 1_000,
                        {"MachineParts": 0.025, "Polymers": 0.015,
                         "robot_h": 6},
                        (0.50, 0.20, 0.10, 0.20)),
    "elec_assy": Maint(2_000, 10_000, 500,
                       {"MachineParts": 0.005, "Electronics": 0.005,
                        "crew_h": 3},
                       (0.30, 0.60, 0.0, 0.10)),
    "consumables": Maint(2_500, 12_000, 750,
                         {"MachineParts": 0.010, "Polymers": 0.005,
                          "crew_h": 3},
                         (0.50, 0.20, 0.10, 0.20)),
    "surface_builder": Maint(1_800, 8_000, 500,
                             {"MachineParts": 0.010, "robot_h": 4},
                             (0.60, 0.25, 0.10, 0.05)),
    "wafer_fab": Maint(400, 20_000, 168,
                       {"Electronics": 0.002, "Polymers": 0.005,
                        "crew_h": 12},
                       (0.15, 0.65, 0.0, 0.20)),
    "drydock": Maint(5_000, 25_000, 2_000,
                     {"MachineParts": 0.030, "robot_h": 12},
                     (0.65, 0.25, 0.10, 0.0)),
    "robot": Maint(2_000, 2_000, 250,
                   {"MachineParts": 0.003, "crew_h": 1},
                   (0.70, 0.30, 0.0, 0.0)),
    "depot": Maint(8_000, 30_000, 2_000,
                   {"MachineParts": 0.010, "Polymers": 0.005},
                   (0.50, 0.30, 0.05, 0.15)),
    "mass_driver": Maint(900, 10_000, 168,
                         {"MachineParts": 0.050, "Electronics": 0.010},
                         (0.55, 0.30, 0.10, 0.05)),
    "assembly_hall": Maint(2_000, 10_000, 500,
                           {"MachineParts": 0.010, "crew_h": 4},
                           (0.60, 0.20, 0.10, 0.10)),
    "workshop": Maint(5_000, 20_000, 1_000,
                      {"MachineParts": 0.005, "crew_h": 2},
                      (0.50, 0.20, 0.10, 0.20)),
    "catcher": Maint(4_000, 20_000, 1_000,
                     {"MachineParts": 0.010, "robot_h": 8},
                     (0.60, 0.30, 0.10, 0.0)),
    "skyhook": Maint(10_000, 50_000, 2_000,
                     {"StructuralParts": 0.050, "robot_h": 20},
                     (0.30, 0.20, 0.50, 0.0)),
}

# which §1.6 fab module uses which maintenance row
MAINT_OF_MODULE = {
    "fab_printer_poly": "printer_farm", "fab_printer_lpbf": "lpbf_cell",
    "fab_machine_shop": "machine_shop", "fab_foundry_mill": "foundry_mill",
    "fab_chem_plant": "chem_plant", "fab_elec_assy": "elec_assy",
    "fab_consumables": "consumables", "fab_workshop": "workshop",
    "fab_waam": "surface_builder", "fab_assembly_hall": "assembly_hall",
    "fab_sinter_printer": "surface_builder",
    "fab_filament_winder": "surface_builder",
    "fab_ice_caster": "surface_builder", "yard_drydock": "drydock",
    "fab_wafer_fab": "wafer_fab",
}


# ---- failure-mode rules (§8) -----------------------------------------------------------
def death_spiral(projected_burn_t_yr: float, stock_t: float,
                 manufacturing_t_yr: float, imports_t_yr: float) -> bool:
    """Spares death spiral: projected parts burn exceeds stock plus all
    replacement streams — the UI raises the alarm."""
    return projected_burn_t_yr > (stock_t + manufacturing_t_yr
                                  + imports_t_yr)


CANNIBALIZE_MASS_FRAC = 0.01
CANNIBALIZE_DONOR_DC = 0.30


def cannibalize(donor_mass_t: float, donor_c: float,
                split: tuple[float, float, float, float]) -> tuple[dict, float]:
    """Strip 1% of donor mass as parts; donor condition drops 0.3."""
    parts_t = donor_mass_t * CANNIBALIZE_MASS_FRAC
    keys = ("MachineParts", "Electronics", "StructuralParts", "Polymers")
    return ({k: parts_t * s for k, s in zip(keys, split) if s > 0},
            max(0.0, donor_c - CANNIBALIZE_DONOR_DC))


# ---- blueprints (§3.11) ------------------------------------------------------------------
WRIGHT_EXP = -0.234         # 85% learning curve
WRIGHT_FLOOR = 0.4
FIRST_ARTICLE_LABOR = 1.5
FIRST_ARTICLE_MATERIALS = 1.1


def e_design_h(m_dry_t: float) -> float:
    """F-10: E_design = 40 × M^0.6 engineering-hours."""
    return 40.0 * m_dry_t ** 0.6


def labor_mult(n: int) -> float:
    """F-11: labor(N) = N^(−0.234), floored at 0.4×."""
    return max(WRIGHT_FLOOR, float(n) ** WRIGHT_EXP)


def fleet_spares_mult(n: int, c_bp: float) -> float:
    """F-12: S(N)/S_1 = N × [(1 − C_bp) + C_bp/√N]. Five identical
    ships pool to √5 ≈ 2.24×; five one-offs pay 5×."""
    return n * ((1.0 - c_bp) + c_bp / math.sqrt(n))
