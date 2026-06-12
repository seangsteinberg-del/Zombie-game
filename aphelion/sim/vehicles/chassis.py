"""Chassis classes + V-0 build validation (10 §1.0 head, §1.1 worked
checks): the Motor Pool grid/cap table VC-1…VC-5, the integrated-item
cutoffs (sub-100 kg; zero-g drones to 300 kg), V-0a clearance, V-0b
tip-over (θ_tip = atan(0.5·track/h_COM) ≥ 2σ_slope, live tilt icon at
θ_tip − 5° per hazard row 1), V-0c float, V-0d power closure (shared
law, delegated to powerplant), the one cost rule 10 owns (overhaul =
MachineParts 3% + Electronics 0.5% of dry mass), and the §1.4
UTL-CRANE lift law m_max = 12 t·(1.62/g)."""

from __future__ import annotations

import math
from dataclasses import dataclass

# V-0d is shared law owned by powerplant.py — import, never duplicate.
from aphelion.sim.vehicles.powerplant import power_closure as v0d_power_closure

__all__ = [
    "CHASSIS", "Chassis", "is_integrated",
    "v0a_clearance", "v0a_rock_warn",
    "v0b_theta_tip_rad", "v0b_ok", "tilt_warn_rad", "h_com_loaded",
    "v0c_ok", "v0d_power_closure",
    "overhaul_bill_t", "crane_lift_t",
]


# ---- chassis classes (10 §1.0: root part of a vehicle = chassis frame) ------------
@dataclass(frozen=True, slots=True)
class Chassis:
    grid: tuple[int, int]       # Motor Pool cells, travel-axis-horizontal, 1 m × 1 m
    gross_cap_t: float
    label: str


CHASSIS = {
    "VC-1": Chassis((2, 2), 0.8, "cart"),           # LRV, mule, drill cart
    "VC-2": Chassis((4, 2), 3.0, "light"),          # science rover, light hauler
    "VC-3": Chassis((6, 3), 12.0, "medium"),        # pressurized rover, excavator
    "VC-4": Chassis((10, 4), 60.0, "heavy"),        # 20 t haulers, cranes, barge tug
    "VC-5": Chassis((16, 5), 300.0, "platform"),    # Mercury crawler, module transporter
}

# Integrated catalog items skip the grid build and ride as 1-cell cargo.
INTEGRATED_MAX_KG = 100.0       # sub-100 kg: strictly below
ZERO_G_DRONE_MAX_KG = 300.0     # UTL-CDRONE exception: zero-g drones to 300 kg


def is_integrated(mass_kg: float, zero_g_drone: bool = False) -> bool:
    """10 §1.0: sub-100 kg vehicles are integrated (no grid build);
    zero-g assembly drones to 300 kg are also integrated."""
    if zero_g_drone:
        return mass_kg <= ZERO_G_DRONE_MAX_KG
    return mass_kg < INTEGRATED_MAX_KG


# ---- V-0a clearance ----------------------------------------------------------------
def v0a_clearance(lowest_cell_m: float, set_clearance_m: float) -> bool:
    """V-0a: lowest non-locomotion cell ≥ locomotion set's clearance."""
    return lowest_cell_m >= set_clearance_m


ROCK_WARN_ABUNDANCE = 0.10      # UI default; canon mandates warn-not-refuse
                                # vs sector rock_abundance but states no number
                                # (03 owns sector data — not yet in code).


def v0a_rock_warn(rock_abundance: float,
                  warn_threshold: float = ROCK_WARN_ABUNDANCE) -> bool:
    """V-0a rider: warn (never refuse) against sector rock_abundance."""
    return rock_abundance >= warn_threshold


# ---- V-0b tip-over -----------------------------------------------------------------
V0B_SIGMA_MULT = 2.0            # θ_tip must cover 2σ of coarsest allowed sector
TILT_WARN_OFFSET_RAD = math.radians(5.0)    # hazard table row 1: icon past θ_tip − 5°


def v0b_theta_tip_rad(track_width_m: float, h_com_m: float) -> float:
    """V-0b: θ_tip = atan(0.5·track_width / h_COM)."""
    return math.atan(0.5 * track_width_m / h_com_m)


def v0b_ok(theta_tip_rad: float, slope_sigma_rad: float) -> bool:
    """V-0b: θ_tip ≥ 2.0 × slope_sigma of the coarsest allowed sector."""
    return theta_tip_rad >= V0B_SIGMA_MULT * slope_sigma_rad


def tilt_warn_rad(theta_tip_rad: float) -> float:
    """Hazard row 1: live tilt warning icon shows past θ_tip − 5°."""
    return theta_tip_rad - TILT_WARN_OFFSET_RAD


def h_com_loaded(m_vehicle_kg: float, h_vehicle_m: float,
                 m_cargo_kg: float, h_cargo_m: float) -> float:
    """V-0b rider: recompute h_COM live on cargo load (mass-weighted).
    Also the §1.4 crane tip check: V-0b with the load at the boom tip."""
    return ((m_vehicle_kg * h_vehicle_m + m_cargo_kg * h_cargo_m)
            / (m_vehicle_kg + m_cargo_kg))


# ---- V-0c float --------------------------------------------------------------------
FLOAT_MARGIN = 0.95             # mirrors floats() in sim/vehicles/marine.py
                                # (V-0c == V-20); kept local so chassis stays
                                # self-contained — do NOT import marine.


def v0c_ok(m_gross_kg: float, v_disp_m3: float, rho_sea: float) -> bool:
    """V-0c: m_gross / V_displacement ≤ 0.95 · ρ_sea."""
    return m_gross_kg <= FLOAT_MARGIN * rho_sea * v_disp_m3


# ---- overhaul cost rule (the ONLY cost rule 10 owns) -------------------------------
OVERHAUL_MACHINEPARTS_FRAC = 0.03   # of dry mass
OVERHAUL_ELECTRONICS_FRAC = 0.005   # of dry mass
FIELD_REPAIR_SPARES_MULT = 3.0      # field repair ×3 spares, ×2 time
FIELD_REPAIR_TIME_MULT = 2.0


def overhaul_bill_t(dry_t: float) -> dict[str, float]:
    """10 §1.0 cost note: full overhaul = MachineParts 3% + Electronics
    0.5% of dry mass (prices are 12 §4.3; recipes are 05)."""
    return {
        "MachineParts": OVERHAUL_MACHINEPARTS_FRAC * dry_t,
        "Electronics": OVERHAUL_ELECTRONICS_FRAC * dry_t,
    }


# ---- §1.4 UTL-CRANE lift law -------------------------------------------------------
CRANE_BASE_LIFT_T = 12.0        # LSMS rating at lunar g
CRANE_REF_G = 1.62              # Moon


def crane_lift_t(g_local: float) -> float:
    """§1.4 UTL-CRANE: m_max = 12 t · (1.62 / g_local); tip check =
    V-0b with the load at the boom tip (see h_com_loaded)."""
    return CRANE_BASE_LIFT_T * (CRANE_REF_G / g_local)
