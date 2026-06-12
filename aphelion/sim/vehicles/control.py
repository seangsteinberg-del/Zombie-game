"""Control modes, crew rules, and freight-link constants (10 §3.2–§3.4
plus failure rows 6 and 13). Vehicles add NO new comms model: the
teleop law is 05 F-2 (η = 1/(1 + RTT/τ)) imported from industry/labor
with the DRIVING time-atom τ = 60 s. Worked anchors: Moon RTT 2.56 s
→ η 0.96 (Lunokhod); Mars best 6.2 min → η ~0.14, below the 0.2
refusal line (Earth joystick at Mars never works — the misery driving
the Act-3 A3 push); Saturn ~160 min → A3/crewed only."""

from __future__ import annotations

from aphelion.sim.industry.labor import teleop_eta

# ---- §3.2 control modes (table as data) -------------------------------------------
MODES = {
    "crewed": {
        "requires": "crew aboard",
        "capability": "full v_max, all tasks, no link",
        "needs_link": False,
        "v_max_mult": 1.0,
    },
    "teleop": {
        "requires": "link + operator (CTL-A2 kit)",
        "capability": ("speed/work × η = 1/(1 + RTT/60 s) (05 F-2, "
                       "T_atom 60 s driving); refuse standing ops "
                       "below η 0.2"),
        "needs_link": True,
        "f2_exempt": False,
    },
    "a2_batch": {
        "requires": "link at uplink/downlink only",
        "capability": ("sol-plan supervised autonomy; exempt from F-2; "
                       "drive cap 0.35 km/sol"),
        "f2_exempt": True,
        "drive_cap_km_sol": 0.35,
    },
    "autonav": {
        "requires": "link at dispatch/arrival (CTL-A3)",
        "capability": "0.5× v_max, 24/7; exceptions halt and page (05 queue)",
        "v_max_mult": 0.5,
        "duty_24_7": True,
    },
    "a4": {
        "requires": "05 autonomous-complex node",
        "capability": "ledger-mode only; no per-vehicle events",
        "ledger_only": True,
    },
    "convoy": {
        "requires": "leader any mode",
        "capability": "followers at leader's speed, 1:5",
        "followers_per_leader": 5,
    },
}

TELEOP_TAU_DRIVING_S = 60.0     # F-2 driving time-atom (labor τ=26 s is dexterous)
TELEOP_REFUSE_ETA = 0.2         # UI refuses STANDING teleop ops strictly below
A2_BATCH_CAP_KM_SOL = 0.35      # Mars RTG rover canon (§3.1 duty cycle)
AUTONAV_VMAX_MULT = 0.5         # CTL-A3 runs 24/7 at half v_max
CONVOY_RATIO = 5                # followers per leader


def teleop_eta_driving(rtt_s: float) -> float:
    """05 F-2 with the driving atom: η = 1/(1 + RTT/60 s)."""
    return teleop_eta(rtt_s, t_atom_s=TELEOP_TAU_DRIVING_S)


def refuses_teleop(rtt_s: float) -> bool:
    """§3.2: refuse standing teleop ops below η 0.2 (η = 0.2 is allowed)."""
    return teleop_eta_driving(rtt_s) < TELEOP_REFUSE_ETA


def convoy_max_followers(leaders: int) -> int:
    """§3.2 CONVOY: followers ride at the leader's speed, 1:5."""
    return leaders * CONVOY_RATIO


# ---- failure row 6: TELEOP link loss ----------------------------------------------
# Ground safe-halts (brake + beacon); aircraft RTB at A2+ and CRASH at
# A1 (the UI refuses beyond-visual-range dispatch at A1 — one signed
# override allowed); balloons keep drifting and recovery becomes an
# intercept problem.
def link_loss_behavior(vehicle_domain: str, autonomy_level: int) -> str:
    """Row 6 → "safe_halt" | "rtb" | "crash" | "drift"."""
    if vehicle_domain == "balloon":
        return "drift"
    if vehicle_domain == "aircraft":
        return "rtb" if autonomy_level >= 2 else "crash"
    return "safe_halt"          # ground vehicles: brake + beacon


def refuses_bvr_dispatch(autonomy_level: int,
                         signed_override: bool = False) -> bool:
    """Row 6 UI gate: no beyond-visual-range aircraft dispatch at A1;
    one signed override is allowed."""
    return autonomy_level < 2 and not signed_override


# ---- §3.3 crew rules ----------------------------------------------------------------
WALKBACK_RESERVE_H = 3.0        # suit reserve held back from the sortie
WALKBACK_SPEED_KMH = 2.0        # suited walking pace
SUITPORT = {"gas_kg": 0.1, "dust_d": 0.1}       # per cycle
AIRLOCK = {"gas_kg": 0.5, "dust_d": 1.0}        # per cycle
MOVE_AND_WAIT_RTT_S = 5.0       # TELEOP ghost goes move-and-wait above this


def walkback_radius_km(suit_endurance_h: float) -> float:
    """§3.3: (endurance − 3 h reserve) × 2 km/h → EMU 8 h = 10 km.
    Pressurized rovers are their own refuge and skip this rule."""
    return (suit_endurance_h - WALKBACK_RESERVE_H) * WALKBACK_SPEED_KMH


def refuses_walkback(range_km: float, suit_endurance_h: float) -> bool:
    """Failure row 13: planner HARD-refuses unpressurized crewed sorties
    beyond walkback; override → unsurvivable suit failure by design."""
    return range_km > walkback_radius_km(suit_endurance_h)


def move_and_wait(rtt_s: float) -> bool:
    """§3.3 direct drive: TELEOP shows an RTT-delayed ghost; above 5 s
    RTT control degrades to move-and-wait."""
    return rtt_s > MOVE_AND_WAIT_RTT_S


# ---- §3.4 freight link costs (published to 05) --------------------------------------
# kWh per GROSS t·km; road is a (best, worst) span across bodies/terrain.
FREIGHT_KWH_PER_GROSS_T_KM = {
    "road": (0.012, 0.034),
    "dirigible": 0.027,
    "barge": 0.028,
    "plane_payload": 0.04,      # plane figure is already payload-basis
}
HOP_VS_ROAD_MULT = 1e3          # hops cost ~1000× road per t·km

PAYLOAD_FRACTION = 0.55         # payload-basis conversion fraction
PAYLOAD_BASIS = {               # kWh per PAYLOAD t·km at 0.55 fraction
    "moon_road": 0.025,
    "mars_road": 0.057,
    "titan_road": 0.021,
    "moon_regolith": 0.19,
    "mars_duricrust": 0.29,
}
