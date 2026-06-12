"""Atmospheric flight (10 §2.4): one formula set, all bodies —
differences emerge from ρ and g. Ingenuity at 335 W is the calibration
fixture; Titan at hover-index 0.025 is the primary logistics layer; and
there is deliberately NO Mars cargo aviation, ever."""

from __future__ import annotations

import math

CL_MAX_T2 = 1.4
CL_MAX_T3 = 1.8
ETA_HOVER_T1 = 0.29
ETA_HOVER_T2 = 0.42
ETA_PROP = 0.75
LD_BY_TIER = {"T0": 10.0, "T1": 10.0, "T2": 15.0, "T3": 20.0}
P_FIX_INTEGRATED_W = 25.0
P_FIX_GRID_W = 60.0


def v_stall_ms(m_kg: float, g: float, rho: float, s_m2: float,
               cl_max: float = CL_MAX_T2) -> float:
    """V-13."""
    return math.sqrt(2.0 * m_kg * g / (rho * s_m2 * cl_max))


def p_hover_w(m_kg: float, g: float, rho: float, a_disk_m2: float,
              eta_h: float = ETA_HOVER_T1,
              p_fix_w: float = P_FIX_INTEGRATED_W) -> float:
    """V-14: ideal induced power / η_h + fixed avionics."""
    return ((m_kg * g) ** 1.5 / (eta_h * math.sqrt(2.0 * rho * a_disk_m2))
            + p_fix_w)


def p_cruise_w(m_kg: float, g: float, v_ms: float,
               l_over_d: float = 15.0,
               eta_prop: float = ETA_PROP) -> float:
    """V-15."""
    return m_kg * g * v_ms / (l_over_d * eta_prop)


def v_tip_max_ms(a_sound_ms: float) -> float:
    """V-16: ω·R ≤ 0.75·a_sound — Mars (a≈240) demands big slow rotors."""
    return 0.75 * a_sound_ms


def hover_index(g: float, rho: float) -> float:
    """Per-body feasibility vs Earth SL: (g^1.5/√ρ) normalized."""
    earth = 9.81 ** 1.5 / math.sqrt(1.225)
    return (g ** 1.5 / math.sqrt(rho)) / earth


def stall_index(g: float, rho: float) -> float:
    earth = math.sqrt(9.81 / 1.225)
    return math.sqrt(g / rho) / earth


# planner bands per body: (alt ceilings m); Venus floor rules in 10 §3.4
ALT_BANDS = {"core:mars": (200.0, 1_000.0),
             "core:titan": (200.0, 1_000.0, 8_000.0),
             "core:venus": (56_000.0, 62_000.0)}
VENUS_FLOOR_M = 45_000.0        # clamp; 42-45 km = 2%/min; below = lost
