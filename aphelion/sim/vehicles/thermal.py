"""Vehicle thermal survival (10 §2.3): the V-11 conduction law with
its MLI-shorts-in-atmosphere rule, hibernation survival power (V-11 +
the V-5a 25 W avionics floor), the four lunar-night (354 h) strategies
— RTG waste heat, hibernation on the pack, the STO-WADI thermal wadi,
garage — plus the 273/233 K battery brick rules (failure table row 3)
and the 09 H-5 endurance clocks for Venus surface / Mercury noon
(Venera-13 127 min anchor; Mercury twilight outruns sunrise)."""

from __future__ import annotations

import math

# ---- V-11 conduction --------------------------------------------------------------
U_VALUES = {                # W/m²·K
    "mli": 0.3,             # multilayer insulation — VACUUM ONLY
    "aerogel": 1.0,         # aerogel + gas barrier (Titan/Mars)
    "bare": 2.5,            # bare metal in atmosphere
}


def q_loss_w(insulation: str, area_m2: float, t_in_k: float,
             t_out_k: float, in_atmosphere: bool = False) -> float:
    """V-11: Q = U·A_surface·(T_in − T_out). MLI works by radiative
    decoupling; in any atmosphere gas conduction shorts the layers, so
    MLI degrades to bare metal (U 0.3 → 2.5)."""
    u = U_VALUES[insulation]
    if insulation == "mli" and in_atmosphere:
        u = U_VALUES["bare"]
    return u * area_m2 * (t_in_k - t_out_k)


# Titan anchor (ΔT ≈ 200 K): a 30 m² cab loses ~6 kW aerogel / ~15 kW
# bare. SUB-T cross-check: ~12 m² hull, aerogel → ~2.4 kW, covered by
# the 3× RTG-S units' ~6 kWt waste heat. RTG/Stirling/combustion
# vehicles self-heat from waste kWt; battery vehicles pay V-11 from
# the pack.

AVIONICS_FLOOR_W = 25.0     # V-5a integrated-avionics hibernation floor


def p_survival_w(insulation: str, area_m2: float, t_in_k: float,
                 t_out_k: float, in_atmosphere: bool = False) -> float:
    """Hibernation survival power: P_surv = V-11 loss + 25 W floor."""
    return (q_loss_w(insulation, area_m2, t_in_k, t_out_k, in_atmosphere)
            + AVIONICS_FLOOR_W)


# ---- lunar night (354 h) strategies (10 §2.3) ---------------------------------------
LUNAR_NIGHT_H = 354.0
NIGHT_STRATEGIES = (
    "rtg_waste_heat",       # (a) waste kWt keeps the cab warm for free
    "hibernation_pack",     # (b) pay P_surv from the pack — see lunar_night_kwh
    "thermal_wadi",         # (c) STO-WADI berth
    "garage",               # (d) no exposure
)

# (c) thermal wadi: holds ≥ ~245 K on ~2.0 kWt bleed — clears the
# 233 K damage line; the pack trickle-heats the last 30 K up to the
# 273 K charge threshold.
WADI_HOLD_K = 245.0
WADI_BLEED_KWT = 2.0
WADI_TRICKLE_BAND_K = 30.0


def lunar_night_kwh(p_surv_w: float) -> float:
    """(b) pack energy to hibernate through the 354 h lunar night."""
    return p_surv_w * LUNAR_NIGHT_H / 1_000.0


# ---- battery brick rules (10 §2.3 + failure table row 3) -----------------------------
CHARGE_MIN_K = 273.0        # no charge/discharge attempt below this
DAMAGE_K = 233.0            # cold-soak damage line
BRICK_FRAC = 0.30           # −30% capacity per event
HEATER_GRACE_H = 6.0        # cold soak only bites after >6 h unpowered


def battery_brick_events(t_k: float, heater_unpowered_h: float,
                         attempted_transfer: bool = False) -> float:
    """Capacity multiplier per event: 0.70 if the pack sits < 233 K
    with the heater unpowered > 6 h, OR any charge/discharge attempt
    is made < 273 K; else 1.0. Pre-dusk alarm is mandatory UI."""
    cold_soak = t_k < DAMAGE_K and heater_unpowered_h > HEATER_GRACE_H
    bad_transfer = attempted_transfer and t_k < CHARGE_MIN_K
    if cold_soak or bad_transfer:
        return 1.0 - BRICK_FRAC
    return 1.0


# ---- 09 H-5 endurance clocks (Venus surface / Mercury noon) --------------------------
# Clock-limited, not steady-state: tier 0 = 2.1 h (Venera-13 127 min
# anchor), pre-T3 = 2–8 h, T3 SiC = 60-day clocks.
ENDURANCE_CLOCK_BY_TIER_H = {0: 2.1, 1: 4.0, 2: 8.0, 3: 1_440.0}
CLOCKED_ENVS = ("venus_surface", "mercury_noon")
MERCURY_TERMINATOR_KMH = 3.6    # equatorial terminator advance rate


def endurance_clock_h(env: str, tier: int = 0) -> float:
    """09 H-5: hours on the clock before retreat. Mercury twilight has
    no clock — a crawler outruns the 3.6 km/h terminator forever; any
    other env is steady-state and V-11 governs instead."""
    if env in CLOCKED_ENVS:
        return ENDURANCE_CLOCK_BY_TIER_H[min(tier, 3)]
    return math.inf
