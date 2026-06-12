"""Suborbital hops on airless bodies (10 §2.6): the ballistic-arc
launch speed V-18, the round-cost rule V-19, the it's-a-lander boundary
at Ψ = π/2, the energy-honesty note the planner surfaces, and the C23
plume-scouring rule that makes landing pads non-optional."""

from __future__ import annotations

import math

HOP_MARGIN = 1.10           # boost + propulsive landing + 10%


def v_launch_ms(mu: float, r_p_m: float, d_m: float) -> float:
    """V-18: optimal ballistic arc over ground distance d."""
    psi = d_m / r_p_m
    s = math.sin(psi / 2.0)
    return math.sqrt((mu / r_p_m) * 2.0 * s / (1.0 + s))


def dv_hop_ms(mu: float, r_p_m: float, d_m: float) -> float:
    """V-19: Δv = 2 × v_launch × 1.10."""
    return 2.0 * v_launch_ms(mu, r_p_m, d_m) * HOP_MARGIN


def dv_hop_short_ms(g: float, d_m: float) -> float:
    """V-18a small-arc shortcut: Δv ≈ 2.2·√(g·d)."""
    return 2.2 * math.sqrt(g * d_m)


def is_lander_domain(r_p_m: float, d_m: float) -> bool:
    """Boundary rule: past Ψ = π/2 (a quarter circumference) the
    'hopper' is flying a lander mission — 06's domain, refuse here."""
    return d_m / r_p_m > math.pi / 2.0


# energy honesty (§2.6): the planner's hop-vs-drive comparison
HOP_VS_DRIVE_ENERGY = (700.0, 1_200.0)

# ---- plume ejecta (C23, §2.6.3) -------------------------------------------------
PLUME_ABRADE_M = 200.0          # within: abrasion event
PLUME_ABRADE_COND = 0.02        # condition −2% on exposed equipment
PLUME_ABRADE_SOLAR = 0.01       # solar −1% PERMANENT
PLUME_CLOSE_M = 50.0            # within: unrated parts roll harder
PLUME_CLOSE_P = 0.30
PLUME_CLOSE_COND = 0.15


def plume_effects(dist_m: float, on_pad: bool) -> dict:
    """What an off-pad launch/landing does at this distance. Landing
    pads suppress scouring entirely."""
    if on_pad or dist_m > PLUME_ABRADE_M:
        return {}
    out = {"condition": PLUME_ABRADE_COND, "solar_perm": PLUME_ABRADE_SOLAR,
           "dust_ledger": 1}
    if dist_m <= PLUME_CLOSE_M:
        out["close_roll_p"] = PLUME_CLOSE_P
        out["close_roll_cond"] = PLUME_CLOSE_COND
    return out
