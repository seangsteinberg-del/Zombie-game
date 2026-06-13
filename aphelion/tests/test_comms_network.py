"""Doc 16 §3 fixtures (design/extracts/16-comms-buildspec.md): the
comms graph over 13 §3.11's contract, bandwidth-as-resource (L-6
ledger, L-14 classes, L-10 volumes), the §3.3 blackout catalog (L-7
conjunction + derived season table, L-8 SPE, L-9 EDL plasma, L-15
optical weather), §3.4 doctrine (L-13 teleop floor, L-11 node ops,
D-2), the BINDING §3.5 relay-constellation worked examples re-derived
from the L-2/L-3 laws, §3.6 store-and-forward (L-5 bulk + F-10), the
BINDING §3.8 anti-softlock invariants (F-3, F-7), and the downlink
scheduler (recorder fills, priority drain, oldest-first within class,
P2 reservation, deterministic (class, timestamp, uid) order)."""

import math

import pytest

from aphelion.core.units import C_LIGHT
from aphelion.sim.network.graph import (
    BLACKOUTS, BUFFER_ALERT_FRAC, BULK_CLASSES, CHRONICLE_SHOT_BITS,
    CLEAR_ENV, COMMS_EVENTS, COMMS_MAX_ALERT_CLASS, CONJ_ALERT_LEAD_DAYS,
    CONJUNCTION_SEASONS, CONSTELLATIONS, D2_RTT_BYPASS, DATA_VOLUMES,
    EDL_QDOT_KW_M2, EDL_TONES_BPS, FAILURE_BURST_BITS,
    FAILURE_BURST_DEADLINE_DAYS, HOUSEKEEPING_BPS_PER_NODE, LIVE_CLASSES,
    NODE_CAP, OPS_DOCTRINE, PRIORITY_CLASSES, ROOT_UID, SAFE_MODE,
    SCHEDULER_ORDER, SCI_CREDIT, SCI_TRANSMIT_BITS_PER_POINT,
    TELEOP_MIN_ETA, TELEOP_MIN_LEG_GAIN, TELEOP_MIN_RATE_BPS, CommsGraph,
    CommsNode, LinkEnv, buffer_net_bps, conjunction_mult,
    conjunction_window_days, crosslink_chord_m, deadline_at_risk,
    dispatch_allowed, dsn_root, earth_occlusion_fraction, edl_blackout,
    effective_rate, elongation_sweep_deg_day, horizon_slant_m,
    housekeeping_bps, invariant_f3, node_ops_check, orbit_period_s,
    preroll_outage_days, projected_drain_bits, required_state,
    ring_continuous, spe_mult, stationary_orbit_radius_m, teleop_ok,
    time_to_level, transport_mode, visibility_arc_deg)
from aphelion.sim.network.linkbudget import (
    K_RF, R_FLOOR_RF, RECORDERS, link_rate, rate_bps)
from aphelion.sim.network.scheduler import (
    Delivery, DownlinkScheduler, Packet, PassAssignment, RecorderBuffer,
    Window, assignment_conflicts, drain_key, passes_needed,
    projected_delivery_t)

AU = 1.496e11           # m — the spec's own rounding (§1.2)
DAY_S = 86_400.0
MU_MOON = 4.9048e12     # m³/s² (GM Moon; §3.5.1 inputs)


# ---- §3.1 graph contract ---------------------------------------------------------------
def test_graph_contract_constants():
    """13 §3.11 consumed verbatim: ≤300 nodes (LAW), core:dsn root, the
    new event types, scheduler determinism order, no comms event above
    Class 2."""
    assert NODE_CAP == 300
    assert ROOT_UID == "core:dsn"
    assert COMMS_EVENTS == ("CONJ_IN", "CONJ_OUT", "LINK_DEGRADED_IN",
                            "LINK_DEGRADED_OUT", "PASS_START", "PASS_END",
                            "BUFFER_FULL", "BUFFER_EMPTY", "NODE_OPS_HOLD")
    assert SCHEDULER_ORDER == ("class", "queue_timestamp", "uid")
    assert COMMS_MAX_ALERT_CLASS == 2


def test_comms_node_fields_and_cap():
    """§3.1: CommsNode carries parts / buffer_bits / buffer_cap_bits /
    per-class queue; Heliograph buffers = UT-AVS 4 + DR-1 256 Gbit; the
    301st node violates the cap LAW."""
    relay = CommsNode("relay", (0.0, 0.0),
                      ("CM-OMNI", "CM-PROX", "UT-DISH-S"),
                      recorders=("UT-AVS", "DR-1"), kind="relay")
    assert relay.buffer_cap_bits == pytest.approx(4e9 + 256e9)
    assert relay.buffer_bits == 0.0
    assert set(relay.queue) == set(PRIORITY_CLASSES)
    assert transport_mode(relay) == "store_and_forward"
    bare = CommsNode("bare", (0.0, 0.0), ("CM-OMNI",))
    assert transport_mode(bare) == "bent_pipe"      # L-5: bent-pipe only

    g = CommsGraph()
    for i in range(NODE_CAP):
        g.add(CommsNode(f"n{i:03d}", (float(i), 0.0), ("CM-OMNI",)))
    with pytest.raises(ValueError):
        g.add(CommsNode("n300", (300.0, 0.0), ("CM-OMNI",)))


# ---- §3.2 bandwidth as a resource (L-6, L-14, L-10) --------------------------------------
def test_l6_buffer_ledger_analytic():
    """L-6: dB/dt = Σgen − Σdrain, piecewise-constant; BUFFER_FULL/EMPTY
    crossings predicted analytically (DR-1 from empty at 2 Mbit/s fills
    in 128,000 s); wrong-signed net never crosses."""
    assert buffer_net_bps(2e6, 0.5e6) == pytest.approx(1.5e6)
    assert time_to_level(0.0, 256e9, 2e6) == pytest.approx(128_000.0)
    assert time_to_level(7.2e9, 0.0, -2e6) == pytest.approx(3_600.0)
    assert time_to_level(0.0, 256e9, -1.0) == math.inf
    assert time_to_level(5.0, 5.0, 0.0) == 0.0


def test_l14_priority_classes():
    """L-14: P0 command floor always on, never scheduled; P2 a live
    reservation, not buffered; bulk = P1/P3/P4; P4 first to starve."""
    assert [PRIORITY_CLASSES[c]["order"] for c in
            ("P0", "P1", "P2", "P3", "P4")] == [0, 1, 2, 3, 4]
    assert not PRIORITY_CLASSES["P0"]["scheduled"]
    assert not PRIORITY_CLASSES["P0"]["buffered"]
    assert PRIORITY_CLASSES["P0"]["fits_floor_bps"] == pytest.approx(8.0)
    assert not PRIORITY_CLASSES["P2"]["buffered"]
    assert PRIORITY_CLASSES["P2"]["reservation"]
    assert PRIORITY_CLASSES["P4"]["first_to_starve"]
    assert BULK_CLASSES == ("P1", "P3", "P4")
    assert LIVE_CLASSES == ("P0", "P2")


def test_l10_canonical_volumes():
    """L-10 (doc 16 owns these): housekeeping 200 bit/s per powered
    node; failure burst 2 Gbit ≤ 30 d, counts on landing, EDL tones
    count; science 10 Gbit/SCI; A2 BATCH 20 up + 800 Mbit down;
    Chronicle 50 Mbit; crediting at Earth or a crewed Lab."""
    assert HOUSEKEEPING_BPS_PER_NODE == pytest.approx(200.0)
    assert housekeeping_bps(3) == pytest.approx(600.0)
    assert FAILURE_BURST_BITS == pytest.approx(2e9)
    assert FAILURE_BURST_DEADLINE_DAYS == pytest.approx(30.0)
    assert DATA_VOLUMES["failure_burst"]["counts_on"] == "landing"
    assert DATA_VOLUMES["failure_burst"]["edl_bent_pipe_tones_count"]
    assert SCI_TRANSMIT_BITS_PER_POINT == pytest.approx(10e9)
    assert DATA_VOLUMES["a2_batch"]["up_bits"] == pytest.approx(20e6)
    assert DATA_VOLUMES["a2_batch"]["down_bits"] == pytest.approx(800e6)
    assert DATA_VOLUMES["teleop_session"]["reservation_only"]
    assert CHRONICLE_SHOT_BITS == pytest.approx(50e6)
    assert DATA_VOLUMES["chronicle_shot"]["pclass"] == "P4"
    assert SCI_CREDIT["credit_at"] == ("earth", "crewed_lab")
    assert SCI_CREDIT["pool_depletion"] == "at_acquisition"
    assert SCI_CREDIT["m_analysis_in_situ"] == pytest.approx(0.40)


def test_l10_survey_downlink_anchor():
    """L-10 worked example: 50-SCI Mars survey = 500 Gbit ≈ 17 days at
    8 h/day on the leased 34 m at 1.7 AU (rate from the L-3 catalog,
    never re-derived here)."""
    rate = rate_bps("UT-DISH-M", "core:dsn-34", 1.7 * AU)
    assert rate == pytest.approx(1.05e6, rel=0.005)
    daily = Window(0.0, 8 * 3_600.0, rate)
    assert passes_needed(500e9, daily) == 17
    windows = [Window(d * DAY_S, d * DAY_S + 8 * 3_600.0, rate)
               for d in range(20)]
    t = projected_delivery_t(500e9, windows)
    assert 16.0 < t / DAY_S < 17.0      # lands during the 17th day


def test_l10_a2_batch_session_anchor():
    """L-11/L-10: one A2 BATCH cycle (20 up + 800 Mbit down) ≈ 13 min
    per sol on a 1 Mbit/s areo prox leg."""
    session_s = (DATA_VOLUMES["a2_batch"]["up_bits"] +
                 DATA_VOLUMES["a2_batch"]["down_bits"]) / 1.0e6
    assert session_s == pytest.approx(820.0)
    assert session_s / 60.0 == pytest.approx(13.7, abs=0.05)
    assert OPS_DOCTRINE["a2_batch"]["missed_cycle"] == \
        "robot_idles_that_sol"


# ---- §3.3 blackout catalog ---------------------------------------------------------------
def test_l7_conjunction_thresholds():
    """L-7: sep < 2° → link down; < 5° → ×0.1; tested per endpoint per
    direction; RF AND optical (no optical bypass); T−30 d Class-3."""
    assert conjunction_mult(1.9) == 0.0
    assert conjunction_mult(2.0) == pytest.approx(0.1)
    assert conjunction_mult(4.9) == pytest.approx(0.1)
    assert conjunction_mult(5.0) == 1.0
    assert conjunction_mult(None) == 1.0
    row = BLACKOUTS["L-7"]
    assert row["bands"] == ("rf", "optical")
    assert row["per_endpoint_per_direction"]
    assert row["events"] == ("CONJ_IN", "CONJ_OUT")
    assert row["trigger"](LinkEnv(sep_sun_rx_deg=3.0))
    assert not row["trigger"](CLEAR_ENV)
    assert CONJ_ALERT_LEAD_DAYS == pytest.approx(30.0)
    # degraded directed rate: ×0.1 between 2° and 5°
    r, floor = effective_rate(1e6, "rf", LinkEnv(sep_sun_rx_deg=3.0))
    assert r == pytest.approx(1e5) and floor
    r, floor = effective_rate(1e6, "rf", LinkEnv(sep_sun_rx_deg=1.0))
    assert r == 0.0 and not floor       # solar-blinded: even the floor

def test_l8_spe_game_model():
    """L-8 [GAME MODEL]: SPE ×0.5 on RF with a segment outside a
    magnetosphere; optical immune; inside a magnetosphere immune."""
    assert spe_mult("rf", True, True) == pytest.approx(0.5)
    assert spe_mult("rf", True, False) == 1.0
    assert spe_mult("rf", False, True) == 1.0
    assert spe_mult("optical", True, True) == 1.0
    env = LinkEnv(spe_active=True, outside_magnetosphere=True)
    assert effective_rate(2e6, "rf", env) == (pytest.approx(1e6), True)
    assert effective_rate(2e6, "optical", env) == (pytest.approx(2e6), True)
    assert BLACKOUTS["L-8"]["trigger"](env)
    assert BLACKOUTS["L-8"]["game_model"]   # honesty-tagged lever


def test_l9_edl_plasma():
    """L-9: q̇ > 50 kW/m² → entering craft's direct links down; an
    overhead relay receives P0 tones only (8 bit/s) through the wake —
    park-a-relay-before-you-land; autonomy mandatory during L-9."""
    assert EDL_QDOT_KW_M2 == pytest.approx(50.0)
    assert not edl_blackout(50.0)       # strictly greater-than
    assert edl_blackout(50.1)
    hot = LinkEnv(edl_qdot_kw_m2=60.0)
    assert effective_rate(1e6, "rf", hot) == (0.0, False)
    relay = LinkEnv(edl_qdot_kw_m2=60.0, rx_overhead_relay=True)
    assert effective_rate(1e6, "rf", relay) == (0.0, True)
    assert EDL_TONES_BPS == pytest.approx(R_FLOOR_RF)
    assert BLACKOUTS["L-9"]["overhead_relay_floor_bps"] == \
        pytest.approx(8.0)
    assert OPS_DOCTRINE["edl"]["autonomy_mandatory"]


def test_l15_optical_weather():
    """L-15: Earth ground optical availability 0.5 as pre-rolled
    scheduled outages from rng("comms") — deterministic, no rerolls;
    Mars dust suspends; RF weather-immune."""
    row = BLACKOUTS["L-15"]
    assert row["earth_ground_availability"] == pytest.approx(0.5)
    assert row["mars_dust_suspends"] and row["airless_full_availability"]
    assert row["rng_substream"] == "comms"
    out = LinkEnv(weather_out=True)
    assert effective_rate(1e9, "optical", out) == (0.0, False)
    assert effective_rate(1e6, "rf", out) == (pytest.approx(1e6), True)
    rolls = (0.49, 0.5, 0.99, 0.0)
    assert preroll_outage_days(rolls) == (False, True, True, False)
    assert preroll_outage_days(rolls) == preroll_outage_days(rolls)
    assert BLACKOUTS["occlusion"]["owner"] == "13 canon"
    assert not effective_rate(1e6, "rf", LinkEnv(los=False))[1]


def test_conjunction_season_table_rederives():
    """§3.3 geometry (derived, not tuned): sweep = ω_syn·r/(r+1) or
    ·r/(1−r); hard = 4°/sweep, degraded = 10°/sweep — every printed row
    re-derives; Mars ~14 d hard every ~26 months (the Act-3 beat)."""
    for (body, kind), row in CONJUNCTION_SEASONS.items():
        superior = kind == "superior"
        sweep = elongation_sweep_deg_day(row["synodic_d"], row["r_au"],
                                         superior)
        assert sweep == pytest.approx(row["sweep_deg_day"], rel=0.02), body
        hard, degraded = conjunction_window_days(row["synodic_d"],
                                                 row["r_au"], superior)
        assert hard == pytest.approx(row["hard_d"], rel=0.04), body
        assert degraded == pytest.approx(row["degraded_d"], rel=0.04), body
    mars = CONJUNCTION_SEASONS[("mars", "superior")]
    assert mars["synodic_d"] / 30.4375 == pytest.approx(26.0, rel=0.02)


# ---- §3.4 doctrine (L-13, L-11, D-2) -------------------------------------------------------
def test_l13_teleop_requirement():
    """L-13: live path ≥ 0.5 Mbit/s (METERON anchor) AND η ≥ 0.2 AND
    relay legs CM-PROX-class (G ≥ 100) or better — omni legs P0-only;
    loss = Class-2 alert, operator-hours forfeit."""
    assert TELEOP_MIN_RATE_BPS == pytest.approx(0.5e6)
    assert TELEOP_MIN_ETA == pytest.approx(0.2)
    assert TELEOP_MIN_LEG_GAIN == pytest.approx(100.0)
    assert teleop_ok(0.5e6, 0.2, 100.0)
    assert not teleop_ok(0.49e6, 0.91, 100.0)
    assert not teleop_ok(2e6, 0.19, 100.0)
    assert not teleop_ok(2e6, 0.91, 1.0)        # omni leg: P0 only


def test_l11_node_ops_doctrine():
    """L-11: uncrewed T0–T1 node ops need a floor path AT EVENT TIME
    (light-lag irrelevant) else NODE_OPS_HOLD (Class-3 escalating);
    T2+ avionics and crewed need no link."""
    assert node_ops_check(0, False, True) == (True, None)
    assert node_ops_check(1, False, False) == (False, "NODE_OPS_HOLD")
    assert node_ops_check(2, False, False) == (True, None)
    assert node_ops_check(0, True, False) == (True, None)
    row = OPS_DOCTRINE["uncrewed_t0_t1"]
    assert row["alert_class"] == 3 and row["escalates_class"] == 2
    assert row["light_lag_irrelevant"]
    assert OPS_DOCTRINE["t2_plus_avionics"]["needs"] is None
    assert OPS_DOCTRINE["a4_or_crewed"]["needs"] is None
    assert OPS_DOCTRINE["autonav_a3"]["needs"] == \
        "floor_at_dispatch_and_arrival"


def test_d2_difficulty_toggle_semantics():
    """D-2: bypasses RTT penalties ONLY (η ≡ 1, no ghost, no refusal);
    link existence, rates, buffers, blackouts, node-ops, DSN fees and
    the A2 speed cap stay on in every preset; RTT displayed truthfully."""
    assert D2_RTT_BYPASS["eta"] == 1.0
    assert not D2_RTT_BYPASS["input_delay_ghost"]
    assert not D2_RTT_BYPASS["refusal"]
    assert set(D2_RTT_BYPASS["keeps_on"]) == {
        "link_existence", "rates", "buffers", "blackouts", "node_ops",
        "dsn_fees", "a2_speed_cap"}
    assert D2_RTT_BYPASS["rtt_display"] == "truthful"


# ---- §3.5 constellation worked examples (BINDING) ------------------------------------------
def test_lunar_farside_ring_binding():
    """§3.5.1: 3 Heliographs, 5,000 km circular lunar orbit, 120°
    phased (8.8 h): arc 2·acos(1737/5000) = 139° > 120° → continuous;
    prox legs 14–28 Mbit/s computed, capped 2 Mbit/s ≥ teleop floor;
    11.3 % Earth-occluded per orbit; 8,660 km omni crosslinks carry
    ~200 bit/s = P0 only; ≤1 h occluded buffers 7.2 Gbit ≪ DR-1."""
    c = CONSTELLATIONS["lunar_farside_ring"]
    R, r, n = c["body_radius_m"], c["orbit_radius_m"], c["n"]
    arc = visibility_arc_deg(R, r)
    assert arc == pytest.approx(139.0, abs=0.5)
    assert ring_continuous(arc, n) and arc > c["phase_deg"]
    assert orbit_period_s(MU_MOON, r) / 3_600.0 == \
        pytest.approx(c["period_h"], abs=0.05)
    # prox legs re-derived from L-3 (uncapped Friis, then the R_max cap)
    nadir, horizon = r - R, horizon_slant_m(R, r)
    assert link_rate(10.0, 100.0, 100.0, nadir, K_RF) == \
        pytest.approx(28e6, rel=0.01)
    assert link_rate(10.0, 100.0, 100.0, horizon, K_RF) == \
        pytest.approx(14e6, rel=0.03)
    assert rate_bps("CM-PROX", "CM-PROX", nadir) == pytest.approx(2.0e6)
    assert c["prox_leg_bps_capped"] >= TELEOP_MIN_RATE_BPS
    assert earth_occlusion_fraction(R, r) == pytest.approx(0.113, rel=0.005)
    chord = crosslink_chord_m(r, n)
    assert chord == pytest.approx(8.66e6, rel=0.001)
    omni = rate_bps("CM-OMNI", "CM-OMNI", chord)
    assert omni == pytest.approx(200.0, rel=0.005)
    assert R_FLOOR_RF <= omni < TELEOP_MIN_RATE_BPS    # P0 continuity only
    assert 3_600.0 * 2e6 == pytest.approx(c["occluded_buffer_bits"])
    assert c["occluded_buffer_bits"] < RECORDERS["DR-1"]["capacity_bits"]
    assert c["blueprint"] == "Heliograph" and c["mass_to_llo_t"] == 1.1


def test_lunar_ring_route_and_store_and_forward():
    """§3.5.1 in the graph: a farside rover (no Earth LOS) routes
    rover → relay → core:dsn at the 2 Mbit/s prox cap; RTT = 2·path/c;
    the DR-1 relay store-and-forwards bulk (§3.6)."""
    d_moon = 3.844e8
    g = CommsGraph(los=lambda a, b: {a, b} != {"rover", ROOT_UID})
    g.add(CommsNode("rover", (0.0, 0.0), ("CM-PROX",), kind="vessel"))
    g.add(CommsNode("relay", (3.263e6, 0.0),
                    ("CM-OMNI", "CM-PROX", "UT-DISH-S"),
                    recorders=("UT-AVS", "DR-1"), kind="relay"))
    g.add(dsn_root((3.263e6 + d_moon, 0.0)))
    route = g.route_to_root("rover")
    assert route.path == ("rover", "relay", ROOT_UID)
    assert route.rate_bps == pytest.approx(2.0e6)   # min over hops (L-5)
    assert route.rtt_s == \
        pytest.approx(2.0 * (3.263e6 + d_moon) / C_LIGHT)
    assert transport_mode(g.node("relay")) == "store_and_forward"
    assert g.commandable("rover") and invariant_f3(g) == []


def test_areostationary_trio_binding():
    """§3.5.2: r_areo = (μT²/4π²)^(1/3) = 20,430 km (T 24.623 h,
    μ 4.2828e13); arc 161° > 120°; prox ~1.0 Mbit/s nadir, 0.74 at the
    horizon slant (above the teleop floor); 35,400 km omni crosslinks
    ≈ 12 bit/s = P0 only; Earth occlusion ≤ 5.3 %/sol; UT-DISH-M trunk
    0.42–6 Mbit/s by season."""
    c = CONSTELLATIONS["areostationary_trio"]
    r = stationary_orbit_radius_m(c["mu_m3_s2"], c["period_h"] * 3_600.0)
    assert r == pytest.approx(20_430e3, rel=0.001)
    R, n = c["body_radius_m"], c["n"]
    arc = visibility_arc_deg(R, c["orbit_radius_m"])
    assert arc == pytest.approx(161.0, abs=0.5)
    assert ring_continuous(arc, n)
    nadir = c["orbit_radius_m"] - R
    assert rate_bps("CM-PROX", "CM-PROX", nadir) == \
        pytest.approx(1.0e6, rel=0.04)
    horizon = horizon_slant_m(R, c["orbit_radius_m"])
    slant_rate = rate_bps("CM-PROX", "CM-PROX", horizon)
    assert slant_rate == pytest.approx(0.74e6, rel=0.005)
    assert slant_rate > TELEOP_MIN_RATE_BPS
    chord = crosslink_chord_m(c["orbit_radius_m"], n)
    assert chord == pytest.approx(35_400e3, rel=0.001)
    omni = rate_bps("CM-OMNI", "CM-OMNI", chord)
    assert omni == pytest.approx(12.0, rel=0.01)
    assert omni >= R_FLOOR_RF                       # P0 only, but alive
    assert earth_occlusion_fraction(R, c["orbit_radius_m"]) == \
        pytest.approx(0.053, rel=0.005)
    assert rate_bps("UT-DISH-M", "core:dsn-34", 2.68 * AU) == \
        pytest.approx(0.42e6, rel=0.01)             # season worst
    assert rate_bps("UT-DISH-M", "core:dsn-34", 0.37 * AU) == \
        pytest.approx(6.0e6)                        # season best, capped


def _pharos_graph(mars_parts, env):
    g = CommsGraph(env=env)
    g.add(CommsNode("mars", (-1.524 * AU, 0.0), mars_parts, kind="relay"))
    g.add(CommsNode("pharos", (0.5 * AU, math.sin(math.radians(60.0)) * AU),
                    ("UT-DISH-L", "UT-DISH-L"), recorders=("DR-2",),
                    kind="relay"))
    g.add(dsn_root((1.0 * AU, 0.0)))
    return g


def test_pharos_conjunction_bypass_binding():
    """§3.5.3: Pharos at 1.0 AU ±60° from Earth. At Mars superior
    conjunction the direct link is solar-blinded (L-7, both directions);
    Mars→relay = 2.20 AU ≈ 1.17 Mbit/s, relay→Earth 1.0 AU capped
    50 Mbit/s → path ≈ 1.2 Mbit/s THROUGH the blackout; with a stock
    UT-DISH-M on the Mars end only ~54 kbit/s."""
    blinded = {("mars", ROOT_UID): LinkEnv(sep_sun_rx_deg=0.5),
               (ROOT_UID, "mars"): LinkEnv(sep_sun_rx_deg=0.5)}
    g = _pharos_graph(("UT-DISH-L",), blinded)
    assert g.directed_link("mars", ROOT_UID) is None    # blacked out
    assert g.distance_m("mars", "pharos") / AU == \
        pytest.approx(2.20, rel=0.001)
    route = g.route_to_root("mars")
    assert route.path == ("mars", "pharos", ROOT_UID)
    assert route.hops[0].rate_bps == pytest.approx(1.17e6, rel=0.005)
    assert route.hops[1].rate_bps == pytest.approx(50e6)    # R_max cap
    assert route.rate_bps == pytest.approx(1.2e6, rel=0.03)
    assert route.rtt_s == pytest.approx(
        2.0 * (g.distance_m("mars", "pharos") +
               g.distance_m("pharos", ROOT_UID)) / C_LIGHT)
    # stock Mars-end dish through the same relay: ~54 kbit/s
    g_stock = _pharos_graph(("UT-DISH-M",), blinded)
    assert g_stock.route_to_root("mars").rate_bps == \
        pytest.approx(54e3, rel=0.02)
    # clear sky: Dijkstra takes the shorter direct hop (2.524 AU)
    g_clear = _pharos_graph(("UT-DISH-L",), {})
    assert g_clear.route_to_root("mars").path == ("mars", ROOT_UID)
    c = CONSTELLATIONS["pharos_pair"]
    assert (c["n"], c["phase_from_earth_deg"]) == (2, 60.0)
    assert c["sun_clearance_au"] == pytest.approx(0.6)


def test_l7_per_endpoint_per_direction():
    """L-7 directionality: only the receiving endpoint's solar
    separation gates a direction — uplink blinded while downlink runs
    degraded."""
    env = {(ROOT_UID, "mars"): LinkEnv(sep_sun_rx_deg=1.0),   # rx blinded
           ("mars", ROOT_UID): LinkEnv(sep_sun_rx_deg=3.0)}   # rx degraded
    g = _pharos_graph(("UT-DISH-L",), env)
    assert g.directed_link(ROOT_UID, "mars") is None
    down = g.directed_link("mars", ROOT_UID)
    clear = _pharos_graph(("UT-DISH-L",), {}).directed_link(
        "mars", ROOT_UID)
    assert down.rate_bps == pytest.approx(0.1 * clear.rate_bps)


# ---- §3.6 store-and-forward (F-10) + §3.8 invariants (F-3, F-7) -----------------------------
def test_f10_deadline_projection_at_queue_time():
    """F-10: the analytic projection flags an unmeetable deadline at
    QUEUE time (Class-3). A 2 Gbit failure burst over floor-only
    windows can never land in 30 d; one fat pass clears it; volume
    queued ahead pushes a later packet over its deadline."""
    deadline = 30.0 * DAY_S
    floor_windows = [(d * DAY_S, d * DAY_S + 8 * 3_600.0, 8.0)
                     for d in range(30)]
    assert projected_drain_bits(floor_windows, deadline) == \
        pytest.approx(30 * 8 * 3_600.0 * 8.0)
    assert deadline_at_risk(2e9, deadline, floor_windows)
    fat = [(0.0, 3_600.0, 1e6)]
    assert not deadline_at_risk(2e9, deadline, fat)     # 3.6 Gbit ≥ 2
    assert deadline_at_risk(2e9, deadline, fat, queued_ahead_bits=2e9)

    buf = RecorderBuffer(256e9)
    wins = [Window(0.0, 3_600.0, 1e6)]
    burst = Packet("burst", "P1", FAILURE_BURST_BITS, 0.0,
                   deadline_t_s=deadline)
    assert buf.enqueue(burst, wins)
    assert not burst.at_risk
    late = Packet("late", "P3", 10e9, 1.0, deadline_t_s=deadline)
    assert buf.enqueue(late, wins)
    assert late.at_risk         # 2 Gbit of P1 drains first; pipe too thin


def test_f3_invariant_binding():
    """F-3 (BINDING): every link with schedulable rate carries the
    preemptive floor; bulk route ⇒ commandable; an EDL wake leaves only
    the overhead relay's P0 tones — still commandable, bulk stalled."""
    env = {("lander", "relay"): LinkEnv(edl_qdot_kw_m2=80.0,
                                        rx_overhead_relay=True),
           ("relay", "lander"): LinkEnv(edl_qdot_kw_m2=80.0,
                                        rx_overhead_relay=True),
           # direct links of the entering craft are simply down (L-9)
           ("lander", ROOT_UID): LinkEnv(edl_qdot_kw_m2=80.0),
           (ROOT_UID, "lander"): LinkEnv(edl_qdot_kw_m2=80.0)}
    g = CommsGraph(env=env)
    g.add(CommsNode("lander", (0.0, 0.0), ("CM-PROX",)))
    g.add(CommsNode("relay", (8e6, 0.0), ("CM-PROX", "UT-DISH-M"),
                    recorders=("DR-1",), kind="relay"))
    g.add(dsn_root((1.5 * AU, 0.0)))
    assert invariant_f3(g) == []
    assert g.route_to_root("lander") is None            # no bulk path
    assert g.commandable("lander")                      # P0 tones survive
    tones = g.directed_link("lander", "relay")
    assert tones.rate_bps == 0.0 and tones.floor_available
    assert tones.floor_bps == pytest.approx(8.0)


def test_f7_invariant_binding():
    """F-7 (BINDING): no-link + no-autonomy → SAFE (sun-pointed, beacon
    at floor when a path next exists); dispatch refused without plan-time
    windows unless signed override."""
    assert required_state(commandable=True, has_autonomy=False) == \
        "OPERATING"
    assert required_state(commandable=False, has_autonomy=True) == \
        "OPERATING"
    assert required_state(commandable=False, has_autonomy=False) == "SAFE"
    assert SAFE_MODE["attitude"] == "sun_pointed"
    assert SAFE_MODE["beacon"] == "floor_when_path_next_exists"
    assert set(SAFE_MODE["recovery"]) == {"build_the_link", "fly_there"}
    assert dispatch_allowed(True)
    assert not dispatch_allowed(False)
    assert dispatch_allowed(False, signed_override=True)


# ---- scheduler: recorder fills, priority drain ----------------------------------------------
def test_scheduler_priority_drain_oldest_first():
    """L-14: drain strictly by class, oldest queue timestamp first
    within a class; P4 starves first. A 1 Mbit/s 5,000 s window moves
    the P1 burst (2 Gbit) then 3 Gbit of the older P3 packet."""
    buf = RecorderBuffer(256e9)
    sched = DownlinkScheduler(buf)
    assert buf.enqueue(Packet("chronicle", "P4", 50e6, 0.0))
    assert buf.enqueue(Packet("sci-b", "P3", 10e9, 100.0))
    assert buf.enqueue(Packet("sci-a", "P3", 10e9, 50.0))
    assert buf.enqueue(Packet("burst", "P1", 2e9, 200.0))
    deliveries, events = sched.drain(Window(1_000.0, 6_000.0, 1e6))
    assert [d.packet_uid for d in deliveries] == ["burst", "sci-a"]
    assert deliveries[0].bits == pytest.approx(2e9)
    assert deliveries[0].t1_s == pytest.approx(3_000.0)
    assert deliveries[1].bits == pytest.approx(3e9)     # partial, oldest P3
    assert buf.used_bits == pytest.approx(7e9 + 10e9 + 50e6)
    assert events[0] == ("PASS_START", 1_000.0)
    assert events[-1] == ("PASS_END", 6_000.0)
    # next window finishes sci-a before sci-b; chronicle still starves
    deliveries2, _ = sched.drain(Window(10_000.0, 25_000.0, 1e6))
    assert [d.packet_uid for d in deliveries2] == ["sci-a", "sci-b"]
    assert deliveries2[0].bits == pytest.approx(7e9)


def test_scheduler_determinism_and_classes():
    """13 determinism: order = (class, queue timestamp, uid) — equal
    timestamps fall back to uid; P0/P2 are never buffered (L-14)."""
    a = Packet("b-pkt", "P3", 1e6, 5.0)
    b = Packet("a-pkt", "P3", 1e6, 5.0)
    c = Packet("z-pkt", "P1", 1e6, 9.0)
    assert sorted([a, b, c], key=drain_key) == [c, b, a]
    buf = RecorderBuffer(1e9)
    with pytest.raises(ValueError):
        buf.enqueue(Packet("cmd", "P0", 1e3, 0.0))
    with pytest.raises(ValueError):
        buf.enqueue(Packet("shift", "P2", 1e6, 0.0))


def test_scheduler_p2_reservation_and_events():
    """L-13/L-14: the P2 teleop reservation is carved off the window's
    rate before bulk drains; BUFFER_EMPTY fires at the analytic
    crossing."""
    w = Window(0.0, 1_000.0, 1.5e6, p2_reserved_bps=TELEOP_MIN_RATE_BPS)
    assert w.bulk_rate_bps == pytest.approx(1.0e6)
    assert w.capacity_bits == pytest.approx(1e9)
    buf = RecorderBuffer(16e9)
    sched = DownlinkScheduler(buf)
    assert buf.enqueue(Packet("hk", "P1", 5e8, 0.0))
    deliveries, events = sched.drain(w)
    assert deliveries == [Delivery("hk", "P1", pytest.approx(5e8),
                                   0.0, pytest.approx(500.0))]
    assert ("BUFFER_EMPTY", pytest.approx(500.0)) in events
    assert buf.empty


def test_buffer_full_pauses_generators():
    """L-6/F-3: at full, generators pause — an offer that would
    overflow is refused, nothing is silently lost; Class-3 alert at
    ≥ 80 %; analytic time-to-full (UT-AVS 4 Gbit)."""
    buf = RecorderBuffer(RECORDERS["UT-AVS"]["capacity_bits"])
    assert buf.time_to_full(2e6) == pytest.approx(2_000.0)
    assert buf.enqueue(Packet("s1", "P3", 3.5e9, 0.0))
    assert BUFFER_ALERT_FRAC == pytest.approx(0.80)
    assert buf.alert and not buf.full
    assert not buf.enqueue(Packet("s2", "P3", 1e9, 1.0))    # pause, no loss
    assert buf.used_bits == pytest.approx(3.5e9)
    assert buf.enqueue(Packet("s3", "P3", 0.5e9, 2.0))
    assert buf.full and buf.generators_paused
    assert buf.time_to_full(2e6) == pytest.approx(0.0)
    assert buf.time_to_empty(2e6) == pytest.approx(2_000.0)


def test_l5_one_link_per_antenna():
    """L-5: one antenna part = one directed link at a time — same part
    slot overlapping in time conflicts; prox + Earth trunk on two parts
    simultaneously is the legal relay pattern."""
    w1 = Window(0.0, 100.0, 2e6)
    w2 = Window(50.0, 150.0, 2e6)
    w3 = Window(100.0, 200.0, 2e6)
    clash = [PassAssignment("relay", 0, "rover", w1),
             PassAssignment("relay", 0, ROOT_UID, w2)]
    assert len(assignment_conflicts(clash)) == 1
    legal = [PassAssignment("relay", 0, "rover", w1),       # prox leg
             PassAssignment("relay", 2, ROOT_UID, w1),      # Earth trunk
             PassAssignment("relay", 0, "rover2", w3)]      # back-to-back
    assert assignment_conflicts(legal) == []
