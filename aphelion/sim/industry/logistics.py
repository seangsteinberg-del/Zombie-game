"""Freighters, depots, and mass drivers (05 §3.2–3.3): F-3 (the ONLY
fuel formula) with its three worked examples as validation targets,
lander lift-loop cycles, the F-6 boiloff ladder (02 §3.12 owns the
rates), and the mass-driver physics F-4/F-5 with the catcher's miss
model and the cargo whitelist."""

from __future__ import annotations

import math
from dataclasses import dataclass

from aphelion.core.units import G0

DV_MARGIN = 1.05            # every map Δv flies with 5% margin
TANK_RESIDUAL = 0.02        # 2% capacity held back as unusable


# ---- F-3 propellant -----------------------------------------------------------
def prop_for_dv_eff(m_dry_t: float, m_cargo_t: float, dv_eff_ms: float,
                    isp_s: float, m_later_t: float = 0.0) -> float:
    """m_prop,i = (m_dry + m_cargo + m_prop,later) × (e^(Δv/ve) − 1);
    dv_eff already includes the ×1.05 margin."""
    ve = isp_s * G0
    return ((m_dry_t + m_cargo_t + m_later_t)
            * (math.exp(dv_eff_ms / ve) - 1.0))


def prop_for_leg(m_dry_t: float, m_cargo_t: float, dv_map_ms: float,
                 isp_s: float, m_later_t: float = 0.0) -> float:
    return prop_for_dv_eff(m_dry_t, m_cargo_t, dv_map_ms * DV_MARGIN,
                           isp_s, m_later_t)


def gear_ratio(cargo_t: float, prop_t: float) -> float:
    """G = cargo delivered / propellant consumed (the UI figure)."""
    return cargo_t / prop_t if prop_t > 0 else float("inf")


def sep_thrust_n(power_kwe: float, isp_s: float,
                 eta: float = 0.65) -> float:
    """F = 2ηP / ve for an electric freighter string."""
    return 2.0 * eta * power_kwe * 1_000.0 / (isp_s * G0)


def sep_trip_days(prop_t: float, thrust_n: float, isp_s: float) -> float:
    """Low-thrust leg duration from the propellant flow ṁ = F/ve."""
    mdot_kgps = thrust_n / (isp_s * G0)
    return prop_t * 1_000.0 / mdot_kgps / 86_400.0


# ---- lander lift-loop cycles (§3.7) ---------------------------------------------
@dataclass(slots=True)
class LanderCycle:
    descent_t: float
    ascent_t: float
    total_t: float
    gear: float


def lander_cycle(dry_t: float, cargo_down_t: float, cargo_up_t: float,
                 dv_desc_map: float, dv_asc_map: float, isp_s: float,
                 surface_refuel: bool = False) -> LanderCycle:
    """Refuel node changes the math. Orbit-refueled (Pelican): descent
    CARRIES the ascent propellant. Surface-refueled (Pelican-M): ascent
    carries the NEXT descent's propellant instead."""
    if not surface_refuel:
        asc = prop_for_leg(dry_t, cargo_up_t, dv_asc_map, isp_s)
        desc = prop_for_leg(dry_t, cargo_down_t, dv_desc_map, isp_s,
                            m_later_t=asc)
    else:
        desc = prop_for_leg(dry_t, cargo_down_t, dv_desc_map, isp_s)
        asc = prop_for_leg(dry_t, cargo_up_t, dv_asc_map, isp_s,
                           m_later_t=desc)
    total = desc + asc
    return LanderCycle(desc, asc, total,
                       gear_ratio(cargo_down_t + cargo_up_t, total))


# ---- F-6 boiloff ladder (02 §3.12 owns; byte-identical here) -----------------------
# fraction of stored mass per day
BOILOFF_LADDER = {
    ("storable", False): 0.0,
    ("storable", True): 0.0,
    ("o2ch4_shielded", False): 0.0003,
    ("o2ch4_shielded", True): 0.0,          # 90 K ZBO, 4.5 kW per 200 t
    ("h2_depot", False): 0.0001,            # adv MLI + sunshield
    ("h2_bare", False): 0.0015,             # standard MLI, no sunshield
    ("h2_depot", True): 0.0,                # 12 kW per 200 t at 20 K
    ("h2_bare", True): 0.0,
}


def boiloff_frac(grade: str, days: float, zbo: bool = False) -> float:
    rate = BOILOFF_LADDER[(grade, zbo)]
    return 1.0 - (1.0 - rate) ** days


# ---- freighter reference catalog (§4.4) -------------------------------------------
FREIGHTERS = {
    "frt_capsule": {"name": "Carrack", "tier": "T0", "dry_t": 6.0,
                    "prop_t": 2.0, "isp_s": 300, "payload_t": 6.0},
    "frt_pallet": {"name": "Pallet", "tier": "T1", "dry_t": 4.5,
                   "prop_t": 24.0, "isp_s": 380, "payload_t": 14.0},
    "frt_drayage": {"name": "Drayage", "tier": "T2", "dry_t": 8.0,
                    "prop_t": 12.0, "isp_s": 2_800, "payload_t": 20.0,
                    "power_kwe": 300.0, "ep": True},
    "frt_longhaul": {"name": "Longhaul", "tier": "T2", "dry_t": 22.0,
                     "prop_t": 60.0, "isp_s": 900, "payload_t": 40.0,
                     "zbo": True, "grade": "h2_depot"},
    "lndr_pelican": {"name": "Pelican", "tier": "T2", "dry_t": 9.0,
                     "prop_t": 39.0, "isp_s": 320, "payload_t": 6.0},
    "lndr_pelican_h": {"name": "Pelican-H", "tier": "T2", "dry_t": 9.0,
                       "prop_t": 28.0, "isp_s": 445, "payload_t": 6.0,
                       "grade": "h2_bare"},
    "lndr_pelican_m": {"name": "Pelican-M", "tier": "T2", "dry_t": 10.0,
                       "prop_t": 52.0, "isp_s": 320, "payload_t": 6.0,
                       "surface_refuel": True},
}


# ---- mass drivers (§3.2) ------------------------------------------------------------
MD_ETA = 0.6


def md_track_length_m(v_ms: float, a_g: float) -> float:
    """F-4: L = v² / (2a)."""
    return v_ms ** 2 / (2.0 * a_g * G0)


def md_energy_kwh_per_kg(v_ms: float) -> float:
    """F-5: E = v² / (2η), end-to-end η = 0.6."""
    return v_ms ** 2 / (2.0 * MD_ETA) / 3.6e6


def md_shot_mj(slug_kg: float, v_ms: float) -> float:
    return slug_kg * md_energy_kwh_per_kg(v_ms) * 3.6


def md_duty_avg_mw(slug_kg: float, v_ms: float,
                   period_s: float = 20.0) -> float:
    return md_shot_mj(slug_kg, v_ms) / period_s


def md_muzzle_peak_mw(slug_kg: float, v_ms: float,
                      a_g: float = 100.0) -> float:
    """Instantaneous F·v/η at the muzzle."""
    f_n = slug_kg * a_g * G0
    return f_n * v_ms / MD_ETA / 1e6


MD_THROUGHPUT_T_DAY = 43.2          # 10 kg slugs every 20 s
MD_MISS_FRAC = 0.02                 # catcher baseline; 10% degraded
MD_MISS_DEGRADED = 0.10
MD_XENON_KG_PER_T = 0.2             # catcher station-keeping per slug-t

# mass-driver-safe bulk (everything else FORBIDDEN until g-rated)
MD_WHITELIST = ("MetalStock", "IronSteel", "Aluminum", "Titanium",
                "Copper", "Glass", "BasaltFiber", "Water", "Regolith")
