"""Vehicle wear V-24a–d (10 §2.9): wheels/tracks per-km, rotors per
flight-hour, hulls per dive-hour, and survival-band thermal cycling —
all returned as positive condition deltas (fractions of C ∈ [0,1])
that the caller subtracts from C and clamps at 0, matching the 05
convention in `sim/industry/wear.py`.

A5 layering (DECISIONS): the wear layers are orthogonal multipliers —
02 per-ignition wear × 11 maturity × 05 condition/MTBF/spares. V-24
feeds ONLY the 05 condition/MTBF/spares layer; it must NOT be combined
with 02 per-ignition wear or the 11 maturity factor (no double
counting), and this module is deliberately separate from — and never
imports — `sim/industry/wear.py` (the 05 base-module layer).

Venus *surface* vehicles skip V-24 entirely: they live on the 09 H-5
endurance clocks instead (`skips_km_wear`)."""

from __future__ import annotations

# ---- multiplier tables (10 §2.9) ---------------------------------------------
# keys cover BOTH the V-24a wear vocabulary and the drive-scene /
# locomotion.TERRAIN vocabulary (ice_plain, earth_road, …) so wheel/track
# wear is not silently overcounted to 1.0 on ice and roads.
TERRAIN_MULT = {"road": 0.5, "regolith": 1.0, "dune": 1.5,
                "chaos": 2.0, "ice": 0.8,
                "ice_plain": 0.8, "ice_plain_studded": 0.8,
                "earth_road": 0.5, "compacted": 0.5,
                "duricrust": 1.0, "titan_shore": 1.2}   # unlisted → 1.0

DUST_MULT = {"moon": 1.5, "mercury": 1.5, "mars": 1.0, "titan": 0.7,
             "venus_cloud": 2.0, "icy_moon": 0.8}   # other → 1.0
# NOTE: Venus-cloud's 2.0 is ACID attack, not dust — same slot in V-24.

# ---- base rates --------------------------------------------------------------
WHEEL_DC_PER_100KM = 0.004      # V-24a: 0.4% per 100 km
TRACK_DC_PER_100KM = 0.006      # V-24a: 0.6% per 100 km
TRACK_TERRAIN_CAP = 1.5         # V-24a: tracks cap terrain_mult at 1.5
ROTOR_DC_PER_10FLH = 0.003      # V-24b: 0.3% per 10 flight-h
HULL_DC_PER_10DIVEH = 0.002     # V-24c: 0.2% per 10 dive-h
EFFERVESCENCE_WEAR_MULT = 1.2   # V-24c: effervescence-active hulls
THERMAL_CYCLE_DC = 0.001        # V-24d: 0.1% per survival-band night

# ---- service costs (10 §2.9) -------------------------------------------------
FIELD_SPARES_MULT = 3.0         # field repair: ×3 spares (weather-gated)
FIELD_TIME_MULT = 2.0           # field repair: ×2 time; garage = full rate


def dc_wheels(km: float, terrain: str = "regolith", body: str = "other",
              tracks: bool = False) -> float:
    """V-24a: ΔC per 100 km = 0.4% wheels / 0.6% tracks × terrain_mult
    × dust_mult; for tracks the terrain_mult is capped at 1.5."""
    t_mult = TERRAIN_MULT.get(terrain, 1.0)
    if tracks:
        t_mult = min(t_mult, TRACK_TERRAIN_CAP)
    base = TRACK_DC_PER_100KM if tracks else WHEEL_DC_PER_100KM
    return base * (km / 100.0) * t_mult * DUST_MULT.get(body, 1.0)


def dc_rotors(flight_h: float, body: str = "other") -> float:
    """V-24b: ΔC per 10 flight-h = 0.3% × dust_mult."""
    return ROTOR_DC_PER_10FLH * (flight_h / 10.0) * DUST_MULT.get(body, 1.0)


def sea_state_mult(sea_state: float) -> float:
    """V-24c multiplier: states 0–2 → ×1.0; state 4 → ×2.0; state 3
    interpolates to ×1.5 (linear 2→4); above 4 clamps at 2.0."""
    if sea_state <= 2.0:
        return 1.0
    if sea_state >= 4.0:
        return 2.0
    return 1.0 + 0.5 * (sea_state - 2.0)


def dc_hull(dive_h: float, sea_state: float = 0,
            effervescence: bool = False) -> float:
    """V-24c: ΔC per 10 dive-h = 0.2% × sea_state_mult; effervescence-
    active multiplies a further ×1.2."""
    eff = EFFERVESCENCE_WEAR_MULT if effervescence else 1.0
    return HULL_DC_PER_10DIVEH * (dive_h / 10.0) * sea_state_mult(sea_state) * eff


def dc_thermal_cycles(n_cycles: float) -> float:
    """V-24d: ΔC += 0.1% per survival-band night cycle — additive and
    independent of the V-24a–c terms."""
    return THERMAL_CYCLE_DC * n_cycles


def skips_km_wear(env: str) -> bool:
    """Venus SURFACE vehicles skip V-24 entirely — they live on the
    09 H-5 endurance clocks instead (10 §2.9)."""
    return env == "venus_surface"


def field_repair_cost(spares: float, time_h: float) -> tuple[float, float]:
    """Field repair vs. garage (10 §2.9): ×3 spares, ×2 time; the
    weather gate is the caller's (13 event layer) problem."""
    return spares * FIELD_SPARES_MULT, time_h * FIELD_TIME_MULT
