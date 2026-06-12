"""Ground locomotion (10 §2.1): the one body-agnostic formula set
V-1…V-8 plus the terrain table that is the data half of the model —
calibrated so the Apollo LRV reproduces ~88 km on its silver-zinc
batteries. Driving is terrain-class/slope, NOT per-wheel physics
(DECISIONS D28)."""

from __future__ import annotations

import math
from dataclasses import dataclass

ETA_DRIVE_T1 = 0.65         # T0–T1 drivetrains
ETA_DRIVE_T2 = 0.72         # T2+
USABLE_PACK = 0.85          # rechargeable packs
USABLE_PRIMARY = 0.90       # primary cells (LRV AgZn)

AVIONICS_W_GRID = 60.0      # V-5a idle loads
AVIONICS_W_INTEGRATED = 25.0
CAB_ECLSS_W_PER_2CREW = 1_500.0


# ---- terrain table (10 §2.1) ---------------------------------------------------
@dataclass(frozen=True, slots=True)
class Terrain:
    crr: float
    mu: float
    bearing_kpa: float
    speed_mult: float = 1.0
    wear_mult: float = 1.0


TERRAIN = {
    "regolith": Terrain(0.15, 0.60, 25.0),          # lunar/asteroid default
    "duricrust": Terrain(0.10, 0.60, 80.0),         # Mars default
    "dune": Terrain(0.20, 0.40, 7.0, speed_mult=0.5, wear_mult=1.5),
    "ice_plain": Terrain(0.04, 0.25, 500.0, wear_mult=0.8),
    "ice_plain_studded": Terrain(0.04, 0.45, 500.0, wear_mult=0.8),
    "chaos": Terrain(0.25, 0.60, 200.0, speed_mult=0.3, wear_mult=2.0),
    "titan_shore": Terrain(0.12, 0.50, 40.0),
    "venus_basalt": Terrain(0.12, 0.50, 300.0),
    "compacted": Terrain(0.06, 0.70, 150.0, wear_mult=0.5),
    "road": Terrain(0.02, 0.80, 600.0, wear_mult=0.5),  # sintered: 5-7x range
    "earth_road": Terrain(0.008, 0.9, 5_000.0, wear_mult=0.5),
}


# ---- V-1 … V-8 -------------------------------------------------------------------
def f_roll_n(crr: float, m_kg: float, g: float,
             slope_deg: float = 0.0) -> float:
    """V-1: F_roll = Crr·m·g (·cosθ on a slope)."""
    return crr * m_kg * g * math.cos(math.radians(slope_deg))


def p_ground_pa(m_kg: float, g: float, n_sets: int,
                a_contact_m2: float) -> float:
    """V-1a: ground pressure per locomotion set."""
    return (m_kg * g / n_sets) / a_contact_m2


def f_aero_n(rho: float, cd: float, a_front_m2: float, v_ms: float) -> float:
    """V-2: skip when ρ < 0.1 (vacuum worlds)."""
    if rho < 0.1:
        return 0.0
    return 0.5 * rho * cd * a_front_m2 * v_ms ** 2


def f_grade_n(m_kg: float, g: float, slope_deg: float) -> float:
    """V-3: downhill negative; regen recovers at η 0.5."""
    return m_kg * g * math.sin(math.radians(slope_deg))


def p_drive_w(f_total_n: float, v_ms: float,
              eta_drive: float = ETA_DRIVE_T2) -> float:
    """V-4."""
    return f_total_n * v_ms / eta_drive


def e_km_kwh(f_total_n: float, p_hotel_w: float, v_kmh: float,
             eta_drive: float = ETA_DRIVE_T2) -> float:
    """V-5: traction term + hotel term (hotel burns clock time)."""
    return (f_total_n / (3_600.0 * eta_drive)
            + p_hotel_w / 1_000.0 / v_kmh)


def theta_max_deg(mu: float, crr: float) -> float:
    """V-6: traction slope limit."""
    return math.degrees(math.atan(mu - crr))


def d_stop_m(v_ms: float, mu: float, g: float) -> float:
    """V-7: mass cancels; low g = long stops."""
    return v_ms ** 2 / (2.0 * mu * g)


K_T = {"raw": 2.8, "compacted": 4.5, "road": 8.0}


def v_max_ms(g: float, surface: str = "raw") -> float:
    """V-8: v_max = k_t·√g."""
    return K_T[surface] * math.sqrt(g)


def range_km(pack_kwh: float, e_km: float, primary: bool = False) -> float:
    usable = USABLE_PRIMARY if primary else USABLE_PACK
    return pack_kwh * usable / e_km


def rtg_cruise_ms(p_net_w: float, f_roll: float,
                  eta_drive: float = ETA_DRIVE_T1) -> float:
    """RTG vehicles: range ∞, speed bounded by continuous power."""
    return p_net_w * eta_drive / f_roll


# ---- hazards (10 §3.5 rows 2 and 5) -----------------------------------------------
EMBED_ROLL_PER_KM = 0.05        # DUNE/soft when p_ground > bearing
EMBED_ESCAPE_ENERGY_MULT = 3.0
EMBED_ESCAPE_P = 0.30
PUNCTURE_SPEED_FRAC = 0.3       # CHAOS above 0.3 × v_max rolls punctures
WHEEL_DEAD_SPEED = 0.3          # limp factor
WHEEL_DEAD_E_MULT = 1.5


def embedding_risk(terrain_key: str, p_ground: float) -> bool:
    t = TERRAIN[terrain_key]
    return p_ground > t.bearing_kpa * 1_000.0


# ---- duty-cycle caps (10 §3.1, Mars RTG rover canon) --------------------------------
KM_PER_SOL = {"a2_batch": 0.35, "a2_local": 2.0, "a3_autonav": 7.5}
