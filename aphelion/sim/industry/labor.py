"""Labor & the automation ladder (05 §2): one convention for every
recipe — all labor entries required simultaneously, f_labor is the min
of the clamped ratios, crew may substitute for robots (never the
reverse), A1 charges supervision, A2 pays light-lag through F-2, A3
runs 0.35× around the clock and pages humans for exceptions, A4 closes
kit fraction χ and imports the rest."""

from __future__ import annotations

from dataclasses import dataclass

LADDER = ("A0", "A1", "A2", "A3", "A4")

# ---- f_labor (the one rule) -----------------------------------------------------


def f_labor(crew_req_h: float, robot_req_h: float, crew_sup_h: float,
            robot_sup_h: float, sub_rate: float = 1.0,
            min_crew_frac: float = 0.0) -> float:
    """Crew hours first cover the crew entry (judgment/QA — robots never
    can); leftover crew substitutes robot-h at sub_rate. Wafer-fab floor:
    crew must supply at least min_crew_frac of TOTAL required hours."""
    fc = 1.0 if crew_req_h <= 0 else min(1.0, crew_sup_h / crew_req_h)
    crew_left = max(0.0, crew_sup_h - crew_req_h)
    rob_eff = robot_sup_h + crew_left * sub_rate
    fr = 1.0 if robot_req_h <= 0 else min(1.0, rob_eff / robot_req_h)
    f = min(fc, fr)
    total_req = crew_req_h + robot_req_h
    if min_crew_frac > 0.0 and total_req > 0.0:
        f = min(f, crew_sup_h / (min_crew_frac * total_req))
    return max(0.0, f)


def supervision_crew_h(robot_h_worked: float, rung: str) -> float:
    """A1: +0.1 crew-h per robot-h, same job. A2: the operator shift IS
    the cost. A3+: the exception rule instead."""
    return 0.1 * robot_h_worked if rung == "A1" else 0.0


# ---- A0: EVA cost rule ------------------------------------------------------------
EVA_CREW_H_PER_SORTIE = 25.0        # 2 crew × 6.5 h outside + 12 prep/post
EVA_PRODUCTIVE_H = 13.0
ETA_EVA = EVA_PRODUCTIVE_H / EVA_CREW_H_PER_SORTIE          # 0.52
EVA_O2_KG_PER_SUIT_SORTIE = 0.59    # 0.09 kg/h × 6.5
EVA_H2O_KG_PER_SUIT_SORTIE = 2.6    # 0.40 kg/h × 6.5
SUIT_OVERHAUL_SORTIES = 25
SUIT_OVERHAUL = {"MachineParts": 0.050, "Polymers": 0.010, "crew_h": 40.0}


def eva_sortie_cost() -> dict:
    """One sortie: 2 suits outside, the whole crew-time bill."""
    return {"crew_h": EVA_CREW_H_PER_SORTIE,
            "productive_h": EVA_PRODUCTIVE_H,
            "Oxygen_kg": 2 * EVA_O2_KG_PER_SUIT_SORTIE,
            "Water_kg": 2 * EVA_H2O_KG_PER_SUIT_SORTIE,
            "suit_wear": 2}


# ---- A2: teleop (F-2) ---------------------------------------------------------------
T_ATOM_DEXTEROUS_S = 25.0
T_ATOM_DRIVING_S = 60.0
TELEOP_REFUSE_ETA = 0.2     # below this the UI refuses standing orders
TELEOP_OVERRIDE_DAMAGE_PER_H = 0.05
OPERATOR_SHIFT_H = 8.0


def teleop_eta(rtt_s: float, t_atom_s: float = T_ATOM_DEXTEROUS_S) -> float:
    return 1.0 / (1.0 + rtt_s / t_atom_s)


def teleop_output_h_day(rtt_s: float, rate_class: float = 1.0,
                        t_atom_s: float = T_ATOM_DEXTEROUS_S) -> float:
    """One operator drives one robot up to 8 h/shift."""
    return OPERATOR_SHIFT_H * teleop_eta(rtt_s, t_atom_s) * rate_class


# ---- A3: supervised autonomy ----------------------------------------------------------
A3_RATE = 0.35              # × human rate, 24 h/day, latency-free
A3_EXCEPTIONS_PER_ROBOT_DAY = 0.5
A3_CLEAR_CREW_H = 0.2       # per exception (crew or teleop); uncleared idles
A3_TASK_CLASSES = ("hauling", "mating_connectors", "welding",
                   "inspection", "repair_swap")


def a3_output_h_day(rate_class: float = 1.0) -> float:
    return 24.0 * A3_RATE * rate_class


# ---- A4: kit closure χ ------------------------------------------------------------------
def chi_import_t_yr(chi: float, m_module_t: float, k_env: float,
                    expansion_bill_t_yr: float = 0.0) -> float:
    """Import dependency [t/yr] = (1−χ) × (M_spares + expansion bill);
    M_spares = k_env × module mass (F-9)."""
    return (1.0 - chi) * (k_env * m_module_t + expansion_bill_t_yr)


# ---- robot catalog (§4.3) -----------------------------------------------------------------
@dataclass(frozen=True, slots=True)
class Robot:
    name: str
    tier: str
    mass_t: float
    power_kw: float
    rate_class: float       # × human, before automation/teleop factors
    note: str = ""


ROBOTS: dict[str, Robot] = {
    "bot_arm_berth": Robot("Berthing arm (Canadarm2)", "T1", 1.8, 0.44,
                           0.0, "handles to 116 t; 17.6 m reach; BERTH"),
    "bot_arm_dex": Robot("Dexterous unit (Dextre)", "T1", 1.6, 0.6,
                         0.5, "ORU swap to 600 kg; rides arm/rail"),
    "bot_worker": Robot("GP worker 'Wrench'", "T2", 0.16, 0.4, 1.0,
                        "tools/welding/mating; EVA-rated"),
    "bot_mule": Robot("Rover-manipulator 'Mule'", "T2", 0.45, 1.2, 1.0,
                      "hauls 1 t; 60 s T_atom class (DECISIONS A9)"),
    "bot_trusselator": Robot("Truss-fab robot", "T3", 0.35, 2.0, 0.0,
                             "TRUSS-FAB 120 kg/day from spool"),
}

ROBOT_L_WEAR_H = 2_000.0    # ×0.6 in dust
ROBOT_SPARES_SPLIT = {"MachineParts": 0.70, "Electronics": 0.30}
