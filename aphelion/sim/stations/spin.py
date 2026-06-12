"""Spin gravity (06 §3.1/§3.2): ω/a_spin/v_rim/gradient, the seven
comfort rules (E9 above 6 rpm crewed), rotor balance (W6 wobble at
0.02·r, forced despin at 0.10·r), and the spin-up propellant quote —
the 200 t ring worked example lands at 1,595 kg of storables.
"""

from __future__ import annotations

import math

G0 = 9.80665

E9_RPM = 6.0                     # crewed hard ceiling
WOBBLE_FRAC = 0.02               # COM offset > 0.02·r → W6 wobble
DESPIN_FRAC = 0.10               # > 0.10·r → forced emergency despin
COMFORT_R_M = 25.0               # rule 5: full comfort needs r ≥ 25 m
COMFORT_VRIM_MS = 6.0            # rule 6: v_rim ≥ 6 m/s else −5%


def omega(rpm: float) -> float:
    return rpm * 2.0 * math.pi / 60.0


def a_spin(rpm: float, r_m: float) -> float:
    return omega(rpm) ** 2 * r_m


def v_rim(rpm: float, r_m: float) -> float:
    return omega(rpm) * r_m


def gradient(r_m: float, h_m: float = 2.0) -> float:
    """Δa/a across a standing body."""
    return h_m / r_m if r_m > 0 else 1.0


def r_for(a_ms2: float, rpm: float) -> float:
    """Radius delivering a at this spin rate (the design table)."""
    w = omega(rpm)
    return a_ms2 / (w * w) if w > 0 else float("inf")


def comfort(rpm: float, r_m: float) -> dict:
    """The seven comfort rules (08 consumes the penalties).
    Returns adaptation days, productivity multiplier, E9 flag, and the
    deconditioning regime of the delivered gravity."""
    a = a_spin(rpm, r_m)
    prod = 1.0
    adapt_days = 0.0
    if rpm > 4.0:
        prod -= 0.15                      # rule 3: permanent penalty
    elif rpm > 2.0:
        adapt_days = 7.0                  # rule 2
    if r_m < COMFORT_R_M and gradient(r_m) > 0.08:
        prod -= 0.05                      # rule 5: gradient discomfort
    if 0.0 < v_rim(rpm, r_m) < COMFORT_VRIM_MS:
        prod -= 0.05                      # rule 6 (stacks)
    return {
        "a_ms2": a,
        "e9": rpm > E9_RPM,               # crewed = validation error
        "adapt_days": adapt_days,
        "productivity": max(0.5, prod),
        # rule 7 → 08 §4.3 thresholds
        "decon_regime": ("none" if a >= 3.71 else
                         "half" if a >= 1.62 else
                         "freefall" if a < 1.0 else "slow"),
    }


def balance(com_offset_m: float, r_m: float) -> str:
    """ok | wobble (W6: −50% port ratings, comfort penalty) | despin."""
    if r_m <= 0:
        return "ok"
    if com_offset_m > DESPIN_FRAC * r_m:
        return "despin"
    if com_offset_m > WOBBLE_FRAC * r_m:
        return "wobble"
    return "ok"


def moment_of_inertia(masses_radii: list[tuple[float, float]]) -> float:
    """I = Σ m·r² (kg, m)."""
    return sum(m * r * r for m, r in masses_radii)


def spinup_prop_kg(i_kgm2: float, rpm: float, thruster_r_m: float,
                   isp_s: float) -> float:
    """m_prop = I·ω / (r_t · Isp · g0) (06 §3.2)."""
    return i_kgm2 * omega(rpm) / (thruster_r_m * isp_s * G0)


def spinup_time_s(i_kgm2: float, rpm: float, torque_nm: float) -> float:
    """t = I·ω / τ — the SP-HUB motor does it propellant-free, slower."""
    return i_kgm2 * omega(rpm) / torque_nm if torque_nm > 0 else \
        float("inf")
