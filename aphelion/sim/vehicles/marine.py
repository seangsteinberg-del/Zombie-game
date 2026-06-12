"""Marine craft (10 §2.7) + the cryobot melt law (§2.8): Titan seas at
94 K where the hull's enemy is cold, not pressure; N2 effervescence
that blinds sonar; and the SLUSH-anchored melt descent at 100 m/day."""

from __future__ import annotations

CD_MARINE = {"sub": 0.10, "boat": 0.15, "barge": 0.40}
ETA_PROP_MARINE_T2 = 0.60
ETA_PROP_MARINE_T3 = 0.65
FLOAT_MARGIN = 0.95             # V-0c: m_gross ≤ 0.95·ρ_sea·V_hull
TITAN_P_SURF_PA = 146_700.0
TITAN_PA_PER_M = 740.0          # ρ_sea·g ≈ 550 × 1.35

# hull classes (MPa): the Titan driver is 94 K, not pressure
HULL_RATING_MPA = {"H1": 0.5, "H2": 5.0, "H3": 40.0, "H4": 100.0}
OVERPRESSURE_LEAK_PER_MIN = 0.01    # per 10% over rating

EFFERVESCENCE_FLUX_KW_M2 = 0.5      # wetted-skin limit (SUB-FIN fixes)
EFFERVESCENCE_SONAR_MULT = 0.5
EFFERVESCENCE_DRAG_MULT = 1.2
SEAL_CRACK_PER_DIVE = 0.10          # elastomers at 94 K (T3 metal fixes)


def floats(m_gross_kg: float, v_hull_m3: float, rho_sea: float) -> bool:
    """V-0c / V-20."""
    return m_gross_kg <= FLOAT_MARGIN * rho_sea * v_hull_m3


def pressure_pa(depth_m: float, p_surf_pa: float = TITAN_P_SURF_PA,
                pa_per_m: float = TITAN_PA_PER_M) -> float:
    """V-21: Titan 300 m ≈ 3.7 atm — trivial."""
    return p_surf_pa + pa_per_m * depth_m


def drag_n(rho_sea: float, cd: float, a_front_m2: float,
           v_ms: float) -> float:
    return 0.5 * rho_sea * cd * a_front_m2 * v_ms ** 2


def p_prop_w(drag_force_n: float, v_ms: float,
             eta: float = ETA_PROP_MARINE_T2) -> float:
    return drag_force_n * v_ms / eta


# ---- cryobot (V-22/V-23) -----------------------------------------------------
RHO_ICE = 920.0
CP_MEAN_J_KGK = 1_500.0         # 100→273 K mean
DT_K = 173.0
LF_J_KG = 334_000.0
K_LOSS = 3.0                    # lateral conduction + tether refreeze


def e_melt_j_m3(k_loss: float = K_LOSS) -> float:
    """V-22: 546 MJ/m³ ideal, ×3 effective."""
    return RHO_ICE * (CP_MEAN_J_KGK * DT_K + LF_J_KG) * k_loss


def cryobot_descent_m_day(p_thermal_w: float, a_probe_m2: float) -> float:
    """V-23."""
    return p_thermal_w / (a_probe_m2 * e_melt_j_m3()) * 86_400.0


CRYOBOT_REFREEZE_HALT_H = 48.0  # halt longer with < 20 kWt = entombed
CRYOBOT_REFREEZE_MIN_KWT = 20.0
REPEATER_SPACING_M = 500.0      # no teleop through ice — A3 only
