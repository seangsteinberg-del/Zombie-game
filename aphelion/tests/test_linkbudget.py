"""Doc 16 §1–§2 fixtures (design/extracts/16-comms-buildspec.md):
L-2 gains re-derived from aperture, the L-3 calibration anchors
(MRO 3.0 Mbit/s at 1 AU, Voyager 175 bit/s at 160 AU, DSOC 267 Mbit/s
at 0.21 AU), the L-4 worked rated ranges and the geometric-mean link
existence rule (omni↔DSN-34 ≈ 5.3 AU, OPT-1↔GS-OPT-5 ≈ 160 AU), the
§1.3 proximity rate story, the §1.4 band table, L-5 doctrine data, and
the §2 catalog rows / relay blueprints / DSN lease tiers."""

import math

import pytest

from aphelion.sim.network.linkbudget import (
    ANTENNAS, AVIONICS_ED_FAMILY, BANDS, CONJ_DEGRADED_DEG,
    CONJ_DEGRADED_MULT, CONJ_DOWN_DEG, DSN_TIERS, ELEC_RECIPE,
    GROUND_STATIONS, K_OPT, K_RF, LAMBDA_OPT, LAMBDA_RF, PARTS,
    POINTING_RULES, R_FLOOR_OPT, R_FLOOR_RF, RECORDERS, RELAY_BLUEPRINTS,
    STATIONKEEPING_DV_MS_PER_YR, gain_dbi, gain_optical, gain_rf_dish,
    link_exists, link_rate, rate_bps, rated_range, rated_range_m, to_dbi,
    validate_catalog)

AU = 1.496e11   # m — the spec's own rounding ("d=1 AU=1.496e11 m", §1.2)


# ---- L-2 antenna gain ----------------------------------------------------------------
def test_l2_gain_constants():
    """§1.1: all game RF at X-band class λ=35.7 mm η=0.6; optical 1.55 µm
    diffraction-limited (losses live in K_OPT only)."""
    assert LAMBDA_RF == pytest.approx(0.0357)
    assert LAMBDA_OPT == pytest.approx(1.55e-6)
    assert BANDS["rf"]["eta_aperture"] == pytest.approx(0.6)
    assert BANDS["optical"]["eta_aperture"] == pytest.approx(1.0)


def test_l2_catalog_dish_rows_rederive_from_diameter():
    """§1.1: catalog G values are precomputed from the L-2 rules — every
    dish row must re-derive from its diameter (within 2-sig-fig rounding;
    UT-DISH-L prints 4.6e5 vs derived 4.65e5)."""
    for pid, p in PARTS.items():
        if "dish_d_m" not in p:
            continue
        derive = gain_rf_dish if p["band"] == "rf" else gain_optical
        assert derive(p["dish_d_m"]) == pytest.approx(p["gain"], rel=0.015), pid


def test_l2_omni_and_prox_gains_are_quoted_not_derived():
    """§1.1: omnis G=1 (0 dBi) by definition; CM-PROX G=100 (20 dBi)
    quoted directly — UHF helix/patch array, not a parabola."""
    assert ANTENNAS["CM-OMNI"]["gain"] == pytest.approx(1.0)
    assert to_dbi(ANTENNAS["CM-OMNI"]["gain"]) == pytest.approx(0.0)
    assert ANTENNAS["CM-PROX"]["gain"] == pytest.approx(100.0)
    assert to_dbi(ANTENNAS["CM-PROX"]["gain"]) == pytest.approx(20.0)
    assert "dish_d_m" not in ANTENNAS["CM-OMNI"]
    assert "dish_d_m" not in ANTENNAS["CM-PROX"]


def test_l2_gain_dbi():
    """L-2 in dBi: DSN 34 m X-band ≈ 67.3 dBi; OPT-1 22 cm ≈ 113 dBi."""
    assert gain_dbi(34.0) == pytest.approx(67.3, abs=0.1)
    assert gain_dbi(0.22, "optical") == pytest.approx(113.0, abs=0.1)


# ---- L-3 calibration anchors (§1.2 mandatory) ----------------------------------------
def test_l3_mro_calibration():
    """MRO: P=100 W, G_t=4.2e4 (3 m), G_r=5.4e6 (DSN 34 m), 1 AU →
    3.0 Mbit/s; 22 Mbit/s raw at 0.37 AU clipped by R_max=6 Mbit/s;
    0.42 Mbit/s at 2.68 AU."""
    assert K_RF == pytest.approx(3.0e15)
    raw = link_rate(100.0, 4.2e4, 5.4e6, AU, K_RF)
    assert raw == pytest.approx(3.0e6, rel=0.015)
    # the catalog pair reproduces the anchor (UT-DISH-M IS the MRO HGA class)
    assert rate_bps("UT-DISH-M", "core:dsn-34", AU) == \
        pytest.approx(3.0e6, rel=0.015)
    assert link_rate(100.0, 4.2e4, 5.4e6, 0.37 * AU, K_RF) == \
        pytest.approx(22e6, rel=0.015)
    assert rate_bps("UT-DISH-M", "core:dsn-34", 0.37 * AU) == \
        pytest.approx(6.0e6)            # R_max clips the close end
    assert rate_bps("UT-DISH-M", "core:dsn-34", 2.68 * AU) == \
        pytest.approx(0.42e6, rel=0.01)


def test_l3_voyager_calibration():
    """Voyager: P=23 W, G_t=6.4e4 (3.7 m), G_r=2.28e7 (DSN 70 m),
    160 AU → 175 bit/s (real: ~160); 5.0 kbit/s at 30 AU."""
    assert link_rate(23.0, 6.4e4, 2.28e7, 160.0 * AU, K_RF) == \
        pytest.approx(175.0, rel=0.005)
    assert link_rate(23.0, 6.4e4, 2.28e7, 30.0 * AU, K_RF) == \
        pytest.approx(5.0e3, rel=0.001)


def test_l3_dsoc_calibration():
    """DSOC: P=4 W, G_t=1.99e11 (22 cm), G_r=1.03e14 (5 m), 0.21 AU →
    267 Mbit/s (raw Friis 265.8 Mbit/s, within 0.5% of the anchor = the
    OPT-1 R_max); 5.2 Mbit/s at 1.5 AU. From catalog gains as printed —
    optical losses live in K_OPT only."""
    assert K_OPT == pytest.approx(3.2e3)
    assert link_rate(4.0, 1.99e11, 1.03e14, 0.21 * AU, K_OPT) == \
        pytest.approx(267e6, rel=0.005)
    assert rate_bps("OPT-1", "GS-OPT-5", 0.21 * AU) == \
        pytest.approx(267e6, rel=0.005)
    assert rate_bps("OPT-1", "GS-OPT-5", 1.5 * AU) == \
        pytest.approx(5.2e6, rel=0.005)


def test_l3_rmax_and_band_pairing():
    """L-3: rate = min(rmax_t, rmax_r, Friis); RF pairs only with RF,
    optical only with optical; d=0 degenerates to the modem cap."""
    assert link_rate(100.0, 4.2e4, 5.4e6, 1.0, K_RF, 6.0e6, 150e6) == \
        pytest.approx(6.0e6)
    assert rate_bps("UT-DISH-M", "OPT-1", 1.0e9) == 0.0
    assert rate_bps("OPT-1", "core:dsn-34", 1.0e9) == 0.0
    assert link_rate(5.0, 1.0, 1.0, 0.0, K_RF, 256e3, 256e3) == \
        pytest.approx(256e3)


# ---- L-4 rated range / link existence ------------------------------------------------
def test_l4_worked_rated_ranges():
    """§1.3 fixtures: CM-OMNI 4.3e7 m; CM-PROX 6.1e9; UT-DISH-M 8.1e12
    (54 AU); DSN-34 1.5e16. Floors: RF 8 bit/s, optical 1 kbit/s."""
    assert R_FLOOR_RF == pytest.approx(8.0)
    assert R_FLOOR_OPT == pytest.approx(1000.0)
    assert rated_range_m("CM-OMNI") == pytest.approx(4.3e7, rel=0.01)
    assert rated_range_m("CM-PROX") == pytest.approx(6.1e9, rel=0.005)
    assert rated_range_m("UT-DISH-M") == pytest.approx(8.1e12, rel=0.005)
    assert rated_range_m("UT-DISH-M") / AU == pytest.approx(54.0, rel=0.01)
    assert rated_range_m("core:dsn-34") == pytest.approx(1.5e16, rel=0.015)
    # raw form: rated_range(P, G, K, floor)
    assert rated_range(5.0, 1.0, K_RF, R_FLOOR_RF) == \
        pytest.approx(4.33e7, rel=0.001)


def test_l4_catalog_column_matches_derivation():
    """§2: the printed rated-range column is the L-4 derivation rounded —
    every part within 4% (UT-DISH-L 1.3e14 vs derived 1.26e14)."""
    for pid, p in PARTS.items():
        assert rated_range_m(pid) == \
            pytest.approx(p["rated_range_m"], rel=0.04), pid
    assert validate_catalog() == []


def test_l4_mixed_link_existence_geometric_mean():
    """§1.3: omni↔DSN-34 closes at √(4.3e7·1.5e16) ≈ 8.0e11 m ≈ 5.3 AU —
    directed asymmetry is real (20 kW DSN uplink reaches an omni far
    beyond the omni's useful downlink)."""
    edge = math.sqrt(rated_range_m("CM-OMNI") * rated_range_m("core:dsn-34"))
    assert edge == pytest.approx(8.0e11, rel=0.005)
    assert edge / AU == pytest.approx(5.3, rel=0.01)
    assert link_exists("CM-OMNI", "core:dsn-34", 7.9e11)
    assert not link_exists("CM-OMNI", "core:dsn-34", 8.1e11)
    assert not link_exists("CM-OMNI", "core:dsn-34", 7.9e11, los=False)
    # band mismatch never closes, whatever the ranges
    assert not link_exists("OPT-1", "core:dsn-34", 1.0e6)


def test_l4_optical_reach_from_ground_aperture():
    """§2.1 †: OPT-1 self-pair rated range is only 7.1e11 m; the real
    reach is the ground aperture — OPT-1↔GS-OPT-5 closes at ≈ 2.4e13 m
    ≈ 160 AU."""
    assert rated_range_m("OPT-1") == pytest.approx(7.1e11, rel=0.005)
    assert rated_range_m("GS-OPT-5") == pytest.approx(8.2e14, rel=0.005)
    edge = math.sqrt(rated_range_m("OPT-1") * rated_range_m("GS-OPT-5"))
    assert edge == pytest.approx(2.4e13, rel=0.01)
    assert edge / AU == pytest.approx(160.0, rel=0.015)
    assert link_exists("OPT-1", "GS-OPT-5", 2.4e13)
    assert not link_exists("OPT-1", "GS-OPT-5", 2.5e13)


def test_l4_proximity_legs_are_a_rate_story():
    """§1.3: rover omni → areo relay omni at 17,000 km EXISTS but carries
    ~52 bit/s (P0 only); CM-PROX↔CM-PROX at the same range ≈ 1.0 Mbit/s,
    R_max-capped 2 Mbit/s inside ~12,000 km — the Electra envelope."""
    d = 17_000e3
    assert link_exists("CM-OMNI", "CM-OMNI", d)
    assert rate_bps("CM-OMNI", "CM-OMNI", d) == pytest.approx(52.0, rel=0.01)
    assert rate_bps("CM-PROX", "CM-PROX", d) == pytest.approx(1.0e6, rel=0.04)
    assert rate_bps("CM-PROX", "CM-PROX", 12_000e3) == pytest.approx(2.0e6)
    # cap crossover distance ≈ 12,000 km
    assert math.sqrt(K_RF * 10.0 * 100.0 * 100.0 / 2.0e6) == \
        pytest.approx(12_000e3, rel=0.025)


# ---- §1.4 band table -----------------------------------------------------------------
def test_band_table():
    """Two physical bands only; UHF/S/Ka folded into per-part R_max and
    K_RF. RF: SPE ×0.5 outside magnetospheres, weather-immune. Optical:
    SPE-immune, Earth ground availability ×0.5, Mars dust suspends,
    conjunction NOT bypassed (<2° down, <5° ×0.1, both bands)."""
    assert set(BANDS) == {"rf", "optical"}
    assert BANDS["rf"]["k"] == pytest.approx(3.0e15)
    assert BANDS["rf"]["floor_bps"] == pytest.approx(8.0)
    assert BANDS["rf"]["spe_rate_mult"] == pytest.approx(0.5)
    assert BANDS["rf"]["weather_immune"]
    assert BANDS["optical"]["k"] == pytest.approx(3.2e3)
    assert BANDS["optical"]["floor_bps"] == pytest.approx(1000.0)
    assert BANDS["optical"]["spe_rate_mult"] == pytest.approx(1.0)
    assert not BANDS["optical"]["weather_immune"]
    assert BANDS["optical"]["earth_ground_availability"] == pytest.approx(0.5)
    assert BANDS["optical"]["mars_dust_suspends"]
    assert not BANDS["rf"]["conjunction_bypassed"]
    assert not BANDS["optical"]["conjunction_bypassed"]
    assert CONJ_DOWN_DEG == pytest.approx(2.0)
    assert CONJ_DEGRADED_DEG == pytest.approx(5.0)
    assert CONJ_DEGRADED_MULT == pytest.approx(0.1)


# ---- L-5 pointing / scheduling doctrine ----------------------------------------------
def test_l5_pointing_rules_data():
    """L-5: one directed link per antenna; P0 preemptive, never
    scheduled; path rate = min over hops, RTT = sum of hop light times;
    live classes need the whole path, bulk store-and-forwards only with
    recorder capacity (no recorder = bent pipe)."""
    assert POINTING_RULES["links_per_antenna"] == 1
    assert POINTING_RULES["p0_floor_preemptive"] is True
    assert POINTING_RULES["multihop_path_rate"] == "min_over_hops"
    assert POINTING_RULES["multihop_rtt"] == "sum_of_hop_light_times"
    assert POINTING_RULES["live_path_classes"] == ("P0", "P2")
    assert POINTING_RULES["bulk_classes"] == ("P1", "P3", "P4")
    assert POINTING_RULES["no_recorder"] == "bent_pipe_only"


# ---- §2 catalog rows -----------------------------------------------------------------
def test_antenna_catalog_rows():
    """§2.1 columns: mass / draw / P_tx / R_max / price as printed."""
    a = ANTENNAS
    assert set(a) == {"CM-OMNI", "CM-PROX", "UT-DISH-S", "UT-DISH-M",
                      "UT-DISH-L", "OPT-1", "OPT-2"}
    assert (a["CM-OMNI"]["mass_kg"], a["CM-OMNI"]["p_tx_w"],
            a["CM-OMNI"]["rmax_bps"], a["CM-OMNI"]["price_musd"]) == \
        (5.0, 5.0, 256e3, 0.05)
    assert a["CM-OMNI"]["integrated_in"] == ("UT-AV", "UT-AVS")
    assert a["CM-PROX"]["never_integrated"] and \
        a["CM-PROX"]["mandatory_on_teleop"]
    assert (a["UT-DISH-S"]["dish_d_m"], a["UT-DISH-S"]["p_tx_w"],
            a["UT-DISH-S"]["rmax_bps"]) == (0.5, 10.0, 2.0e6)
    assert (a["UT-DISH-M"]["mass_kg"], a["UT-DISH-M"]["draw_kwe"],
            a["UT-DISH-M"]["rmax_bps"]) == (90.0, 0.35, 6.0e6)
    assert (a["UT-DISH-L"]["tier"], a["UT-DISH-L"]["rmax_bps"],
            a["UT-DISH-L"]["price_musd"]) == ("T2", 50.0e6, 8.0)
    assert (a["OPT-1"]["band"], a["OPT-1"]["p_tx_w"], a["OPT-1"]["rmax_bps"],
            a["OPT-1"]["unlock"]) == ("optical", 4.0, 267e6, "GN-06")
    assert (a["OPT-2"]["tier"], a["OPT-2"]["rmax_bps"],
            a["OPT-2"]["price_musd"]) == ("T3", 1.2e9, 25.0)


def test_utdishl_galileo_failure_mode():
    """§2.1: UT-DISH-L one-time deployment roll — jam → G=100 (Galileo
    mode); repair 8 crew-h EVA + 0.1 t MachineParts. Jammed Earth trunk
    at 1 AU collapses from 50 Mbit/s capped to ~14 kbit/s."""
    f = ANTENNAS["UT-DISH-L"]["deploy_failure"]
    assert f["jam_gain"] == pytest.approx(100.0)
    assert f["repair_crew_h_eva"] == pytest.approx(8.0)
    assert f["repair_machineparts_t"] == pytest.approx(0.1)
    jammed = link_rate(200.0, f["jam_gain"], 5.4e6, AU, K_RF)
    healthy = rate_bps("UT-DISH-L", "core:dsn-34", AU)
    assert jammed < 0.001 * healthy     # that is WHY the validator warns


def test_ground_station_catalog_rows():
    """§2.2: GS-12 / GS-OPT-5 player stations rotate with their body;
    core:dsn is the always-on root (3 complexes, never rotation-occluded);
    the 70 m 400 kW emergency uplink is P0-floor-only."""
    g = GROUND_STATIONS
    assert (g["GS-12"]["mass_t"], g["GS-12"]["draw_kwe"], g["GS-12"]["p_tx_w"],
            g["GS-12"]["rmax_bps"], g["GS-12"]["price_musd"]) == \
        (25.0, 15.0, 2.0e3, 200e6, 20.0)
    assert g["GS-12"]["rotates_with_body"]
    assert (g["GS-OPT-5"]["band"], g["GS-OPT-5"]["p_tx_w"],
            g["GS-OPT-5"]["rmax_bps"], g["GS-OPT-5"]["unlock"]) == \
        ("optical", 20.0, 1.2e9, "GN-06")
    for dsn in ("core:dsn-34", "core:dsn-70"):
        assert g[dsn]["lease_only"] and g[dsn]["always_on_root"]
        assert g[dsn]["node"] == "core:dsn"
        assert not g[dsn]["rotates_with_body"]
        assert g[dsn]["p_tx_w"] == pytest.approx(20.0e3)
        assert g[dsn]["rmax_bps"] == pytest.approx(150e6)
    assert g["core:dsn-70"]["emergency_uplink_w"] == pytest.approx(400.0e3)
    assert g["core:dsn-70"]["emergency_uplink_p0_only"]


def test_recorder_catalog_rows():
    """§2.3: integrated UT-AV 16 Gbit / UT-AVS 4 Gbit; DR-1 256 Gbit at
    5 kg / $0.5M; DR-2 4 Tbit at 20 kg / $1.5M (volumes in bits)."""
    r = RECORDERS
    assert r["UT-AV"]["capacity_bits"] == pytest.approx(16e9)
    assert r["UT-AVS"]["capacity_bits"] == pytest.approx(4e9)
    assert r["UT-AV"]["integrated"] and r["UT-AVS"]["integrated"]
    assert (r["DR-1"]["tier"], r["DR-1"]["mass_kg"],
            r["DR-1"]["capacity_bits"], r["DR-1"]["price_musd"]) == \
        ("T0", 5.0, 256e9, 0.5)
    assert (r["DR-2"]["tier"], r["DR-2"]["mass_kg"],
            r["DR-2"]["capacity_bits"], r["DR-2"]["price_musd"]) == \
        ("T2", 20.0, 4e12, 1.5)


def test_relay_blueprints():
    """§2.4: the four reference relays, parts lists and wet masses as
    printed; all pay the flat 2 m/s/yr stationkeeping; Avionics ED
    family 22."""
    b = RELAY_BLUEPRINTS
    assert b["Heliograph"]["parts"] == {"UT-AVS": 1, "CM-OMNI": 1,
                                        "CM-PROX": 1, "UT-DISH-S": 1,
                                        "DR-1": 1}
    assert (b["Heliograph"]["wet_mass_t"], b["Heliograph"]["solar_kwe"],
            b["Heliograph"]["unlock"]) == (0.36, 1.0, "GN-03")
    assert b["Heliograph-A"]["parts"]["UT-DISH-M"] == 1
    assert (b["Heliograph-A"]["wet_mass_t"],
            b["Heliograph-A"]["solar_kwe"]) == (0.50, 2.0)
    assert b["Pharos"]["parts"] == {"UT-AV": 1, "UT-DISH-L": 2, "DR-2": 1}
    assert (b["Pharos"]["tier"], b["Pharos"]["wet_mass_t"]) == ("T2", 2.4)
    assert b["Lighthouse"]["parts"] == {"UT-AV": 1, "OPT-2": 2,
                                        "UT-DISH-S": 1, "DR-2": 2}
    assert (b["Lighthouse"]["tier"], b["Lighthouse"]["unlock"],
            b["Lighthouse"]["wet_mass_t"]) == ("T3", "GN-06", 2.0)
    assert STATIONKEEPING_DV_MS_PER_YR == pytest.approx(2.0)
    assert AVIONICS_ED_FAMILY == 22


def test_blueprint_role_rate_anchors():
    """§2.4 role numbers from the catalog: Heliograph UT-DISH-S Earth
    trunk ~8.4 kbit/s at 1 AU (not interplanetary); Pharos legs at 2.2 AU
    ≈ 1.17 Mbit/s dish-to-dish, relay→Earth 67 Mbit/s raw → capped
    50 Mbit/s; against stock UT-DISH-M only ~54 kbit/s."""
    assert rate_bps("UT-DISH-S", "core:dsn-34", AU) == \
        pytest.approx(8.4e3, rel=0.005)
    assert rate_bps("UT-DISH-L", "UT-DISH-L", 2.2 * AU) == \
        pytest.approx(1.17e6, rel=0.005)
    assert link_rate(200.0, 4.6e5, 5.4e6, AU, K_RF) == \
        pytest.approx(67e6, rel=0.01)
    assert rate_bps("UT-DISH-L", "core:dsn-34", AU) == pytest.approx(50e6)
    assert rate_bps("UT-DISH-M", "UT-DISH-L", 2.2 * AU) == \
        pytest.approx(54e3, rel=0.015)


def test_act1_rmax_invisibility_anchor():
    """§4 / DECISIONS C22: inside Earth SOI nearly every link is
    R_max-capped — Moon UT-DISH-M → DSN-34 computes 4.6e11 bit/s,
    capped 6 Mbit/s (the green status light)."""
    d_moon = 3.844e8
    assert link_rate(100.0, 4.2e4, 5.4e6, d_moon, K_RF) == \
        pytest.approx(4.6e11, rel=0.005)
    assert rate_bps("UT-DISH-M", "core:dsn-34", d_moon) == pytest.approx(6.0e6)


def test_dsn_lease_tiers():
    """§2.5: 34 m $1,100/h; 70 m $4,400/h (×4 aperture weighting);
    optical $2,500/h gated on GN-06; HQ allocation 2 h/day on the 34 m,
    FREE; standing lease per 12 E-12."""
    t = DSN_TIERS
    assert t["dsn-34-hour"]["price_usd_per_h"] == pytest.approx(1100.0)
    assert t["dsn-70-hour"]["price_usd_per_h"] == pytest.approx(4400.0)
    assert t["dsn-70-hour"]["price_usd_per_h"] == \
        pytest.approx(4.0 * t["dsn-34-hour"]["price_usd_per_h"])
    assert t["optical-ground-hour"]["price_usd_per_h"] == \
        pytest.approx(2500.0)
    assert t["optical-ground-hour"]["requires"] == "GN-06"
    assert t["hq-allocation"]["price_usd_per_h"] == 0.0
    assert t["hq-allocation"]["hours_per_day"] == pytest.approx(2.0)
    assert t["hq-allocation"]["antenna"] == "core:dsn-34"
    assert t["standing-lease"]["contract"] == "12 E-12"


def test_elec_build_class():
    """§2: all parts build-class ELEC — 0.40 Electronics + 0.30 Aluminum
    + 0.20 Copper + 0.10 MachineParts (sums to 1)."""
    assert ELEC_RECIPE == {"Electronics": 0.40, "Aluminum": 0.30,
                           "Copper": 0.20, "MachineParts": 0.10}
    assert sum(ELEC_RECIPE.values()) == pytest.approx(1.0)
