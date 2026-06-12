"""10 §3.2–§3.4 fixtures: the mode table, the F-2 driving-atom teleop
law with its worked η anchors (Moon 0.96 / Mars 0.14 refused / Saturn
A3-only), failure rows 6 (link loss) and 13 (walkback), suitport vs
airlock cycle costs, and the §3.4 freight-link constants published
to 05."""

import pytest

from aphelion.sim.industry import labor
from aphelion.sim.vehicles.control import (
    A2_BATCH_CAP_KM_SOL, AIRLOCK, AUTONAV_VMAX_MULT, CONVOY_RATIO,
    FREIGHT_KWH_PER_GROSS_T_KM, HOP_VS_ROAD_MULT, MODES,
    MOVE_AND_WAIT_RTT_S, PAYLOAD_BASIS, PAYLOAD_FRACTION, SUITPORT,
    TELEOP_REFUSE_ETA, TELEOP_TAU_DRIVING_S, convoy_max_followers,
    link_loss_behavior, move_and_wait, refuses_bvr_dispatch,
    refuses_teleop, refuses_walkback, teleop_eta_driving,
    walkback_radius_km)


def test_mode_table():
    """§3.2: six modes; CREWED needs no link at full v_max; A2 BATCH is
    F-2-exempt with the 0.35 km/sol cap; AUTONAV is 0.5× v_max 24/7;
    A4 is ledger-only; CONVOY 1:5."""
    assert set(MODES) == {"crewed", "teleop", "a2_batch", "autonav",
                          "a4", "convoy"}
    assert not MODES["crewed"]["needs_link"]
    assert MODES["crewed"]["v_max_mult"] == pytest.approx(1.0)
    assert MODES["teleop"]["needs_link"]
    assert not MODES["teleop"]["f2_exempt"]
    assert MODES["a2_batch"]["f2_exempt"]
    assert MODES["a2_batch"]["drive_cap_km_sol"] == \
        pytest.approx(A2_BATCH_CAP_KM_SOL)
    assert A2_BATCH_CAP_KM_SOL == pytest.approx(0.35)
    assert MODES["autonav"]["v_max_mult"] == pytest.approx(0.5)
    assert AUTONAV_VMAX_MULT == pytest.approx(0.5)
    assert MODES["a4"]["ledger_only"]
    assert MODES["convoy"]["followers_per_leader"] == 5
    assert CONVOY_RATIO == 5
    assert convoy_max_followers(2) == 10


def test_teleop_driving_law_reuses_f2():
    """05 F-2 with T_atom 60 s: the canon law is labor.teleop_eta —
    control.py imports it rather than re-deriving."""
    assert TELEOP_TAU_DRIVING_S == pytest.approx(60.0)
    assert TELEOP_TAU_DRIVING_S == pytest.approx(labor.T_ATOM_DRIVING_S)
    assert TELEOP_REFUSE_ETA == pytest.approx(labor.TELEOP_REFUSE_ETA)
    assert teleop_eta_driving(120.0) == \
        pytest.approx(labor.teleop_eta(120.0, t_atom_s=60.0))


def test_teleop_eta_anchors():
    """§3.2 worked η: Moon RTT 2.56 s → 0.96 (Lunokhod); Mars best
    6.2 min → 0.139, BELOW the refusal line; Saturn ~160 min →
    A3/crewed only."""
    assert teleop_eta_driving(2.56) == pytest.approx(0.96, abs=0.005)
    assert not refuses_teleop(2.56)
    assert teleop_eta_driving(372.0) == pytest.approx(0.139, abs=0.005)
    assert refuses_teleop(372.0)            # Earth joystick at Mars never works
    assert refuses_teleop(160.0 * 60.0)     # Saturn
    assert teleop_eta_driving(0.0) == pytest.approx(1.0)


def test_teleop_refusal_boundary():
    """§3.2: refusal is strictly below η 0.2 — RTT 240 s gives exactly
    0.2 and is still allowed."""
    assert teleop_eta_driving(240.0) == pytest.approx(0.2)
    assert not refuses_teleop(240.0)
    assert refuses_teleop(241.0)


def test_link_loss_row6_matrix():
    """Row 6: ground safe-halts (brake + beacon); aircraft RTB at A2+,
    crash at A1; balloons keep drifting at any autonomy."""
    assert link_loss_behavior("ground", 2) == "safe_halt"
    assert link_loss_behavior("ground", 1) == "safe_halt"
    assert link_loss_behavior("aircraft", 1) == "crash"
    assert link_loss_behavior("aircraft", 2) == "rtb"
    assert link_loss_behavior("aircraft", 3) == "rtb"
    for level in (1, 2, 3, 4):
        assert link_loss_behavior("balloon", level) == "drift"


def test_bvr_dispatch_gate():
    """Row 6 UI: refuses beyond-visual-range dispatch at A1; one signed
    override allowed; A2+ dispatches freely."""
    assert refuses_bvr_dispatch(1)
    assert not refuses_bvr_dispatch(1, signed_override=True)
    assert not refuses_bvr_dispatch(2)


def test_walkback_row13():
    """§3.3 / row 13: radius = (endurance − 3 h) × 2 km/h; EMU 8 h =
    10 km; planner hard-refuses beyond it."""
    assert walkback_radius_km(8.0) == pytest.approx(10.0)
    assert walkback_radius_km(6.0) == pytest.approx(6.0)
    assert not refuses_walkback(10.0, 8.0)
    assert refuses_walkback(10.1, 8.0)


def test_suitport_vs_airlock():
    """§3.3: suitport 0.1 kg gas + 0.1 D dust per cycle vs airlock
    0.5 kg + 1.0 D — 5× gas, 10× dust."""
    assert SUITPORT["gas_kg"] == pytest.approx(0.1)
    assert SUITPORT["dust_d"] == pytest.approx(0.1)
    assert AIRLOCK["gas_kg"] == pytest.approx(0.5)
    assert AIRLOCK["dust_d"] == pytest.approx(1.0)
    assert AIRLOCK["gas_kg"] / SUITPORT["gas_kg"] == pytest.approx(5.0)
    assert AIRLOCK["dust_d"] / SUITPORT["dust_d"] == pytest.approx(10.0)


def test_move_and_wait():
    """§3.3 direct drive: TELEOP ghost goes move-and-wait above 5 s RTT."""
    assert MOVE_AND_WAIT_RTT_S == pytest.approx(5.0)
    assert not move_and_wait(5.0)
    assert move_and_wait(5.1)


def test_freight_link_costs():
    """§3.4 published to 05 (kWh per gross t·km): road 0.012–0.034,
    dirigible 0.027, barge 0.028, plane 0.04 payload, hop ~10³× road."""
    assert FREIGHT_KWH_PER_GROSS_T_KM["road"] == \
        (pytest.approx(0.012), pytest.approx(0.034))
    assert FREIGHT_KWH_PER_GROSS_T_KM["dirigible"] == pytest.approx(0.027)
    assert FREIGHT_KWH_PER_GROSS_T_KM["barge"] == pytest.approx(0.028)
    assert FREIGHT_KWH_PER_GROSS_T_KM["plane_payload"] == \
        pytest.approx(0.04)
    assert HOP_VS_ROAD_MULT == pytest.approx(1e3)


def test_payload_basis():
    """§3.4 payload-basis at 0.55 fraction: Moon road 0.025 / Mars road
    0.057 / Titan road 0.021 / Moon regolith 0.19 / Mars duricrust
    0.29; Mars road ~2.3× Moon road."""
    assert PAYLOAD_FRACTION == pytest.approx(0.55)
    assert PAYLOAD_BASIS["moon_road"] == pytest.approx(0.025)
    assert PAYLOAD_BASIS["mars_road"] == pytest.approx(0.057)
    assert PAYLOAD_BASIS["titan_road"] == pytest.approx(0.021)
    assert PAYLOAD_BASIS["moon_regolith"] == pytest.approx(0.19)
    assert PAYLOAD_BASIS["mars_duricrust"] == pytest.approx(0.29)
    assert PAYLOAD_BASIS["mars_road"] / PAYLOAD_BASIS["moon_road"] == \
        pytest.approx(2.3, abs=0.05)
