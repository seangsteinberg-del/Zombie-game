"""Link budgets & comms hardware (doc 16 §1–§2, via
design/extracts/16-comms-buildspec.md): the L-2 antenna gain law, the
L-3 directed Friis rate law (THE formula), the L-4 rated-range rule
that *derives* 13 §3.11's binary link test d ≤ √(R_a·R_b), the §1.4
two-band table, the L-5 pointing/scheduling doctrine as data, and the
§2 hardware catalog — 7 antennas/terminals, player ground stations +
the `core:dsn` root antennas, data recorders, the four reference relay
blueprints, and the §2.5 DSN lease tiers.

Calibration is LAW (§1.2): K_RF reproduces MRO→DSN-34 at 1 AU =
3.0 Mbit/s; K_OPT reproduces DSOC→5 m ground at 0.21 AU = 267 Mbit/s
class. Optical implementation losses (pointing, photon-counting
detection, sky background) live in K_OPT ONLY — never in the gains.
Rate and latency are independent (L-1): RTT stays 13's 2·path/c.

All SI: distance m, transmit power W of *emitted* RF/optical (the
electrical draw is the separate kWe column), rate bit/s, volume bit.
Catalog masses keep the printed units (antennas/recorders kg, ground
stations t)."""

from __future__ import annotations

import math

# ---- L-2 antenna gain --------------------------------------------------------------
LAMBDA_RF = 0.0357      # m (X-band class, 8.4 GHz — ALL game RF modeled here)
LAMBDA_OPT = 1.55e-6    # m
ETA_AP_RF = 0.6         # parabolic aperture efficiency, RF dishes ONLY
ETA_AP_OPT = 1.0        # diffraction limit — losses live in K_OPT, not here

# ---- L-3 rate-law constants (calibrated, LAW) ---------------------------------------
K_RF = 3.0e15           # bit·m²/(s·W) — calibrated MRO -> DSN-34
K_OPT = 3.2e3           # bit·m²/(s·W) — calibrated DSOC -> Palomar 5 m

# ---- L-4 command floors --------------------------------------------------------------
R_FLOOR_RF = 8.0        # bit/s (DSN 7.8125 bit/s min command rate)
R_FLOOR_OPT = 1000.0    # bit/s (photon-counting acquisition floor — no
                        #        optical "trickle mode")

# ---- L-7 conjunction thresholds (referenced by the §1.4 band table; the
#      Brent window machinery itself is 13/§3.3 territory) ----------------------------
CONJ_DOWN_DEG = 2.0         # angular sep < 2° → link down
CONJ_DEGRADED_DEG = 5.0     # angular sep < 5° → rate ×0.1
CONJ_DEGRADED_MULT = 0.1

# ---- §1.4 band table (the game models exactly TWO physical bands; UHF/S/Ka
#      realism is folded into per-part R_max and K_RF) --------------------------------
BANDS: dict[str, dict] = {
    "rf": {
        "lambda_m": LAMBDA_RF, "k": K_RF, "floor_bps": R_FLOOR_RF,
        "eta_aperture": ETA_AP_RF,
        "spe_rate_mult": 0.5,           # L-8: ×0.5 outside magnetospheres
        "conjunction_bypassed": False,  # L-7 applies
        "weather_immune": True,
    },
    "optical": {
        "lambda_m": LAMBDA_OPT, "k": K_OPT, "floor_bps": R_FLOOR_OPT,
        "eta_aperture": ETA_AP_OPT,
        "spe_rate_mult": 1.0,           # L-8: SPE-immune (GN-06 selling point)
        "conjunction_bypassed": False,  # Sun-avoidance: optical does NOT bypass
        "weather_immune": False,        # L-15 lives below
        "earth_ground_availability": 0.5,   # L-15 pre-rolled scheduled outages
        "mars_dust_suspends": True,         # L-15: suspended in dust storms
    },
}


def gain_rf_dish(d_m: float) -> float:
    """L-2: linear boresight gain of a parabolic RF dish of diameter d."""
    return ETA_AP_RF * (math.pi * d_m / LAMBDA_RF) ** 2


def gain_optical(d_m: float) -> float:
    """L-2: diffraction-limited optical aperture gain (eta = 1.0)."""
    return (math.pi * d_m / LAMBDA_OPT) ** 2


def gain_linear(d_m: float, band: str = "rf") -> float:
    """L-2 dispatch: aperture gain for either band. Omnis (G = 1) and the
    CM-PROX helix/patch array (G = 100 quoted) are NOT aperture-derived —
    their gains are catalog data."""
    b = BANDS[band]
    return b["eta_aperture"] * (math.pi * d_m / b["lambda_m"]) ** 2


def gain_dbi(d_m: float, band: str = "rf") -> float:
    """L-2 in dBi: 10·log10 of the linear aperture gain."""
    return 10.0 * math.log10(gain_linear(d_m, band))


def to_dbi(g_linear: float) -> float:
    """Convenience: linear gain → dBi (omni 1 → 0 dBi, CM-PROX 100 → 20)."""
    return 10.0 * math.log10(g_linear)


# ---- L-3 directed link rate — THE formula -------------------------------------------
def link_rate(p_t_w: float, g_t: float, g_r: float, d_m: float, k: float,
              rmax_t: float = math.inf, rmax_r: float = math.inf) -> float:
    """L-3: directed rate (bit/s) for transmitter (P_t, G_t, cap rmax_t)
    into receiver (G_r, cap rmax_r) at distance d. K absorbs noise temp,
    coding and margins. P_t is *emitted* power, not electrical draw."""
    cap = min(rmax_t, rmax_r)
    if d_m <= 0.0:                      # co-located: pure modem limit
        return cap
    return min(cap, k * p_t_w * g_t * g_r / d_m ** 2)


def rate_bps(tx_id: str, rx_id: str, d_m: float) -> float:
    """L-3 over the catalog: directed rate tx → rx at distance d. RF parts
    pair only with RF, optical only with optical (else 0.0 — no link)."""
    t, r = PARTS[tx_id], PARTS[rx_id]
    if t["band"] != r["band"]:
        return 0.0
    return link_rate(t["p_tx_w"], t["gain"], r["gain"], d_m,
                     BANDS[t["band"]]["k"], t["rmax_bps"], r["rmax_bps"])


# ---- L-4 rated range / link existence ------------------------------------------------
def rated_range(p_w: float, g: float, k: float, r_floor: float) -> float:
    """L-4: per-part rated range (m) — the distance at which the part's
    self-pair directed rate hits the band command floor."""
    return math.sqrt(k * p_w * g ** 2 / r_floor)


def rated_range_m(part_id: str) -> float:
    """L-4 over the catalog. The catalog's printed `rated_range_m` column
    is this value rounded to 2 sig figs; this derivation is the authority
    feeding 13 §3.11 so existence stays exactly consistent with the rate
    floor (geometric-mean sense)."""
    p = PARTS[part_id]
    band = BANDS[p["band"]]
    return rated_range(p["p_tx_w"], p["gain"], band["k"], band["floor_bps"])


def link_exists(a_id: str, b_id: str, d_m: float, los: bool = True) -> bool:
    """L-4: link a<->b EXISTS iff LOS (13's test, passed in) and
    d ≤ √(R_a·R_b) — the geometric mean of the two directed floor
    distances. Any existing link carries ≥ its band's command floor in
    the geometric-mean sense; directed asymmetry is real and displayed."""
    if not los or PARTS[a_id]["band"] != PARTS[b_id]["band"]:
        return False
    return d_m <= math.sqrt(rated_range_m(a_id) * rated_range_m(b_id))


# ---- L-5 pointing / scheduling doctrine (data; scheduler is part 2) ------------------
POINTING_RULES: dict[str, object] = {
    "links_per_antenna": 1,             # one directed link at a time, per part
    "p0_floor_preemptive": True,        # command floor never scheduled
    "multihop_path_rate": "min_over_hops",
    "multihop_rtt": "sum_of_hop_light_times",
    "live_path_classes": ("P0", "P2"),  # need the whole path up simultaneously
    "bulk_classes": ("P1", "P3", "P4"),
    "bulk_transport": "store_and_forward_if_recorder",
    "no_recorder": "bent_pipe_only",
}

# ---- §2 hardware catalog --------------------------------------------------------------
# All parts build-class ELEC; prices are 2049 baselines in $M (12 owns
# evolution). RF electrical draw stems from TWTA efficiency 0.3, optical
# heads ~5% — the printed kWe column wins (it includes pointing/facility).
ELEC_RECIPE = {"Electronics": 0.40, "Aluminum": 0.30, "Copper": 0.20,
               "MachineParts": 0.10}
TWTA_EFFICIENCY = 0.30
OPT_HEAD_EFFICIENCY = 0.05
AVIONICS_ED_FAMILY = 22             # 11 family 22 (Avionics)
STATIONKEEPING_DV_MS_PER_YR = 2.0   # all relays, 01 Table 4.8 flat class

# ---- §2.1 antennas & terminals (vessel/vehicle mounts) -------------------------------
# gain: catalog values precomputed from the L-2 rules (dish rows carry
# dish_d_m so tests re-derive them); rated_range_m: printed column,
# rounded from L-4 (the derivation is rated_range_m()).
ANTENNAS: dict[str, dict] = {
    "CM-OMNI": {
        "name": "Omni", "tier": "T0", "mass_kg": 5.0, "draw_kwe": 0.02,
        "band": "rf", "p_tx_w": 5.0, "gain": 1.0,       # 0 dBi by definition
        "rmax_bps": 256e3, "rated_range_m": 4.3e7, "price_musd": 0.05,
        "integrated_in": ("UT-AV", "UT-AVS")},          # standalone for
                                                        # vehicles/relays
    "CM-PROX": {
        "name": "Proximity medium-gain (UHF helix/patch)", "tier": "T0",
        "mass_kg": 8.0, "draw_kwe": 0.04,
        "band": "rf", "p_tx_w": 10.0, "gain": 100.0,    # 20 dBi quoted —
        "rmax_bps": 2.0e6, "rated_range_m": 6.1e9,      # NOT aperture-derived
        "price_musd": 0.15, "never_integrated": True,
        "mandatory_on_teleop": True},   # every TELEOP/A2 vehicle & relay bus
    "UT-DISH-S": {
        "name": "High-gain dish 0.5 m", "tier": "T0",
        "mass_kg": 20.0, "draw_kwe": 0.05,
        "band": "rf", "p_tx_w": 10.0, "dish_d_m": 0.5, "gain": 1.16e3,
        "rmax_bps": 2.0e6, "rated_range_m": 7.1e10, "price_musd": 0.4},
    "UT-DISH-M": {
        "name": "High-gain dish 3 m (MRO HGA class)", "tier": "T0",
        "mass_kg": 90.0, "draw_kwe": 0.35,
        "band": "rf", "p_tx_w": 100.0, "dish_d_m": 3.0, "gain": 4.2e4,
        "rmax_bps": 6.0e6, "rated_range_m": 8.1e12, "price_musd": 2.0},
    "UT-DISH-L": {
        "name": "Deployable mesh dish 10 m", "tier": "T2",
        "mass_kg": 400.0, "draw_kwe": 0.70,
        "band": "rf", "p_tx_w": 200.0, "dish_d_m": 10.0, "gain": 4.6e5,
        "rmax_bps": 50.0e6, "rated_range_m": 1.3e14, "price_musd": 8.0,
        # one-time deployment failure roll (F-2): jam → Galileo mode;
        # ship validator posts the W-class "Galileo check" warning.
        "deploy_failure": {"jam_gain": 100.0, "repair_crew_h_eva": 8.0,
                           "repair_machineparts_t": 0.1}},
    "OPT-1": {
        "name": "Optical terminal 22 cm (DSOC class)", "tier": "T2",
        "unlock": "GN-06", "mass_kg": 30.0, "draw_kwe": 0.10,
        "band": "optical", "p_tx_w": 4.0, "dish_d_m": 0.22, "gain": 1.99e11,
        "rmax_bps": 267e6, "rated_range_m": 7.1e11, "price_musd": 12.0},
        # rated range is the self-pair acquisition-floor value; real reach
        # comes from ground apertures (OPT-1↔GS-OPT-5 ≈ 2.4e13 m ≈ 160 AU)
    "OPT-2": {
        "name": "Optical terminal 50 cm", "tier": "T3",
        "mass_kg": 80.0, "draw_kwe": 0.25,
        "band": "optical", "p_tx_w": 10.0, "dish_d_m": 0.5, "gain": 1.03e12,
        "rmax_bps": 1.2e9, "rated_range_m": 5.8e12, "price_musd": 25.0},
}

# UT-AV avionics core integrates 1× CM-OMNI + 16 Gbit buffer; UT-AVS
# integrates CM-OMNI + 4 Gbit (recorder rows below).

# ---- §2.2 ground / base stations (07 surface-grid modules) ---------------------------
# Player stations on Earth rotate with it → 13's LOS occludes ~50%/day;
# core:dsn abstracts three complexes 120° apart: never rotation-occluded.
GROUND_STATIONS: dict[str, dict] = {
    "GS-12": {
        "name": "Ground station, 12 m dish", "tier": "T1",
        "mass_t": 25.0, "draw_kwe": 15.0,
        "band": "rf", "p_tx_w": 2.0e3, "dish_d_m": 12.0, "gain": 6.7e5,
        "rmax_bps": 200e6, "rated_range_m": 5.8e14, "price_musd": 20.0,
        "rotates_with_body": True},
    "GS-OPT-5": {
        "name": "Optical ground terminal, 5 m", "tier": "T2",
        "unlock": "GN-06", "mass_t": 40.0, "draw_kwe": 25.0,
        "band": "optical", "p_tx_w": 20.0, "dish_d_m": 5.0, "gain": 1.03e14,
        "rmax_bps": 1.2e9, "rated_range_m": 8.2e14, "price_musd": 45.0,
        "rotates_with_body": True},
    "core:dsn-34": {
        "name": "DSN 34 m (lease only)", "lease_only": True,
        "node": "core:dsn", "always_on_root": True,
        "band": "rf", "p_tx_w": 20.0e3, "dish_d_m": 34.0, "gain": 5.4e6,
        "rmax_bps": 150e6, "rated_range_m": 1.5e16,
        "rotates_with_body": False},    # three complexes 120° apart
    "core:dsn-70": {
        "name": "DSN 70 m (lease only)", "lease_only": True,
        "node": "core:dsn", "always_on_root": True,
        "band": "rf", "p_tx_w": 20.0e3, "dish_d_m": 70.0, "gain": 2.28e7,
        "rmax_bps": 150e6, "rated_range_m": 6.2e16,
        "rotates_with_body": False,
        # the 70 m's edge is aperture, not power: the real 400 kW emergency
        # uplink is a P0-floor-only state, never in scheduled rates.
        "emergency_uplink_w": 400.0e3, "emergency_uplink_p0_only": True},
}

# unified part index for rate_bps / rated_range_m / link_exists (part 2's
# graph layer keys on this)
PARTS: dict[str, dict] = {**ANTENNAS, **GROUND_STATIONS}

# ---- §2.3 data recorders (buffers; volumes in bits) ----------------------------------
RECORDERS: dict[str, dict] = {
    "UT-AV": {"name": "Avionics core buffer (integrated)", "tier": "T0",
              "mass_kg": 0.0, "draw_kwe": 0.0, "capacity_bits": 16e9,
              "price_musd": 0.0, "integrated": True},
    "UT-AVS": {"name": "Small avionics core buffer (integrated)",
               "tier": "T0", "mass_kg": 0.0, "draw_kwe": 0.0,
               "capacity_bits": 4e9, "price_musd": 0.0, "integrated": True},
    "DR-1": {"name": "Solid-state recorder", "tier": "T0",
             "mass_kg": 5.0, "draw_kwe": 0.05, "capacity_bits": 256e9,
             "price_musd": 0.5},
    "DR-2": {"name": "Bulk archive recorder", "tier": "T2",
             "mass_kg": 20.0, "draw_kwe": 0.10, "capacity_bits": 4e12,
             "price_musd": 1.5},
}

# ---- §2.4 reference relay blueprints (06 blueprint format) ---------------------------
# All relays pay stationkeeping (STATIONKEEPING_DV_MS_PER_YR); all comms
# parts accrue Avionics-family ED (AVIONICS_ED_FAMILY) and ride 06's
# part-event failure machinery.
RELAY_BLUEPRINTS: dict[str, dict] = {
    "Heliograph": {
        "tier": "T1", "unlock": "GN-03", "wet_mass_t": 0.36,
        "parts": {"UT-AVS": 1, "CM-OMNI": 1, "CM-PROX": 1,
                  "UT-DISH-S": 1, "DR-1": 1},
        "solar_kwe": 1.0, "rcs": True,
        "role": ("Lunar ring unit cell: 2 Mbit/s prox legs; UT-DISH-S "
                 "Earth trunk (capped 2 Mbit/s in Earth SOI, ~8.4 kbit/s "
                 "at 1 AU — not interplanetary); DR-1 store-and-forward; "
                 "omni P0 crosslinks")},
    "Heliograph-A": {
        "tier": "T1", "unlock": "GN-03", "wet_mass_t": 0.50,
        "parts": {"UT-AVS": 1, "CM-OMNI": 1, "CM-PROX": 1,
                  "UT-DISH-M": 1, "DR-1": 1},
        "solar_kwe": 2.0, "rcs": True,
        "role": ("Areostationary trio cell: ~1 Mbit/s prox legs; "
                 "UT-DISH-M Earth trunk 0.42–6 Mbit/s by season")},
    "Pharos": {
        "tier": "T2", "wet_mass_t": 2.4,
        "parts": {"UT-AV": 1, "UT-DISH-L": 2, "DR-2": 1},
        "solar_kwe": 3.0, "rcs": True,
        "role": ("Conjunction-bypass deep relay: ~1.2 Mbit/s per leg at "
                 "2.2 AU, both directions simultaneously (two dishes)")},
    "Lighthouse": {
        "tier": "T3", "unlock": "GN-06", "wet_mass_t": 2.0,
        "parts": {"UT-AV": 1, "OPT-2": 2, "UT-DISH-S": 1, "DR-2": 2},
        "solar_kwe": 5.0, "rcs": False,     # not in the printed parts list;
                                            # stationkeeping budget still applies
        "role": ("0.2–40 Mbit/s optical backbone legs between planets; "
                 "always carries the UT-DISH-S RF fallback — Galileo lesson")},
}

# ---- §2.5 DSN lease tiers (stats here; pricing evolution/contracts → 12) -------------
# Leases buy antenna-hours via the Planner; the scheduler converts a
# lease into PASS_START/END events.
DSN_TIERS: dict[str, dict] = {
    "dsn-34-hour": {
        "name": "34 m antenna-hour", "price_usd_per_h": 1100.0,
        "antenna": "core:dsn-34",
        "anchor": "NASA aperture fee ~$1,057/h FY2015"},
    "dsn-70-hour": {
        "name": "70 m antenna-hour", "price_usd_per_h": 4400.0,
        "antenna": "core:dsn-70", "note": "aperture weighting x4"},
    "optical-ground-hour": {
        "name": "Optical ground network hour", "price_usd_per_h": 2500.0,
        "tier": "T2", "requires": "GN-06"},     # appears once GN-06 exists
    "hq-allocation": {
        "name": "HQ allocation (sponsored-mission status)",
        "price_usd_per_h": 0.0, "hours_per_day": 2.0,
        "antenna": "core:dsn-34", "acts": "1-2"},
    "standing-lease": {
        "name": "Standing lease", "contract": "12 E-12",
        "note": "auto-scheduled passes"},
}


# ---- validation ----------------------------------------------------------------------
def validate_catalog(tol: float = 0.04) -> list[str]:
    """Catalog sanity: bands resolve, transmit chains are positive, the
    printed rated-range column matches the L-4 derivation within rounding
    (UT-DISH-L prints 1.3e14 vs derived 1.26e14 → 4%), blueprints
    reference known part ids, and the ELEC recipe sums to 1. Returns a
    list of violations (empty = clean)."""
    bad = []
    for pid, p in PARTS.items():
        if p["band"] not in BANDS:
            bad.append(f"{pid}: unknown band {p['band']}")
            continue
        if p["p_tx_w"] <= 0 or p["gain"] <= 0 or p["rmax_bps"] <= 0:
            bad.append(f"{pid}: non-positive transmit chain")
        derived = rated_range_m(pid)
        printed = p["rated_range_m"]
        if abs(derived - printed) / printed > tol:
            bad.append(f"{pid}: rated range {printed:.3g} m vs "
                       f"derived {derived:.3g} m")
    known = set(PARTS) | set(RECORDERS)
    for bid, b in RELAY_BLUEPRINTS.items():
        for part in b["parts"]:
            if part not in known:
                bad.append(f"{bid}: unknown part {part}")
    if abs(sum(ELEC_RECIPE.values()) - 1.0) > 1e-9:
        bad.append(f"ELEC recipe sums {sum(ELEC_RECIPE.values())}")
    return bad
