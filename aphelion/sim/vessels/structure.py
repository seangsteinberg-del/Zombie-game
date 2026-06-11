"""Drydock structural integrity (06 §2.8): no FEA — three live checks.
(a) joint axial loads at the limiter-clamped acceleration (E6), checked
at burnout, limiter-engage and on-pad; (b) max-Q per part via the
pre-flight ascent q-sim (E7); (c) vessel-wide q·α ≤ 170 kPa·deg with
the ST-FIN bonus. The acceleration limiter is SAVED WITH THE DESIGN and
E6 always evaluates at it.
"""

from __future__ import annotations

import math

from aphelion.sim.vessels.buildermath import G0
from aphelion.sim.vessels.grid import GridVessel

QALPHA_LIMIT = 170.0             # kPa·deg vessel-wide
QALPHA_FIN_BONUS = 40.0          # per ST-FIN, max 2 counted
Q_TARGET_KPA = 35.0              # autopilot throttle-bucket target
RHO0 = 1.225                     # Earth SL, kg/m³
H_SCALE = 8_500.0                # exponential atmosphere, m

# default q_max by part state (06 §1 defaults)
Q_MAX_STACK_KPA = 50.0
Q_MAX_RADIAL_KPA = 35.0


def part_q_max_kpa(spec: dict) -> float:
    if "q_max_kpa" in spec:
        return float(spec["q_max_kpa"])
    eng = spec.get("engine")
    if (eng and eng.get("rcs")) or spec.get("leg_rating_t"):
        return Q_MAX_RADIAL_KPA
    return Q_MAX_STACK_KPA


def limiter_clamped_accel(thrust_kn: float, m_t: float,
                          limiter_g: float) -> float:
    """Proper acceleration under the design's saved limiter, m/s²."""
    if m_t <= 0.0:
        return 0.0
    return min(thrust_kn / m_t, limiter_g * G0)


def joint_load_kn(m_above_t: float, a_ms2: float) -> float:
    """L_j = m_above · a (06 §2.8a)."""
    return m_above_t * a_ms2


def stack_joint_loads(vessel: GridVessel, a_ms2: float) -> list[dict]:
    """Per stack/interior joint: cut it, weigh the component on the
    nose side, load it at a. Radial joints carry their own rating but
    the same law. Returns [{joint, m_above_t, load_kn, rating_kn, ok}]."""
    out = []
    joints = vessel.joints()
    for k, jt in enumerate(joints):
        adj: dict[int, set[int]] = {i: set()
                                    for i in range(len(vessel.parts))}
        for j2 in joints:
            if j2 is jt:
                continue
            adj[j2.a].add(j2.b)
            adj[j2.b].add(j2.a)
        # component reachable from jt's higher-side part without jt
        a_cy = vessel.parts[jt.a].centroid()[1]
        b_cy = vessel.parts[jt.b].centroid()[1]
        top = jt.a if a_cy >= b_cy else jt.b
        comp, stack = set(), [top]
        while stack:
            n = stack.pop()
            if n in comp:
                continue
            comp.add(n)
            stack.extend(adj[n] - comp)
        m_above = sum(float(vessel.parts[i].spec.get("mass_t", 0.0))
                      for i in comp)
        load = joint_load_kn(m_above, a_ms2)
        out.append({"joint": jt, "m_above_t": m_above,
                    "load_kn": load, "rating_kn": jt.rating_kn,
                    "ok": load <= jt.rating_kn})
    return out


def validate_e6(vessel: GridVessel, thrust_kn: float, m_burnout_t: float,
                limiter_g: float, g_pad_ms2: float = G0) -> list[dict]:
    """E6 cases (06 §2.8a): stage burnout at the saved limiter, plus the
    on-pad/landed case at local gravity. Returns failing joints."""
    bad = []
    for a in (limiter_clamped_accel(thrust_kn, m_burnout_t, limiter_g),
              g_pad_ms2):
        bad += [r for r in stack_joint_loads(vessel, a) if not r["ok"]]
    return bad


# ---- pre-flight ascent q-sim (E7 + q·α) ----------------------------------------
def ascent_qsim(thrust_kn: float, mdot_kgps: float, m0_t: float,
                prop_t: float, frontal_m2: float, cd: float = 2.2,
                q_target_kpa: float = Q_TARGET_KPA,
                dt: float = 0.5) -> dict:
    """1-D vertical ascent with the autopilot's throttle bucket holding
    q ≤ target (06 §2.8b) and the guidance α profile (≤3° below 30 km).
    Same physics family as the flight scene; returns the q/q·α/accel
    traces and their peaks for E7 and the q·α check."""
    m = m0_t * 1e3
    prop = prop_t * 1e3
    h = v = t = 0.0
    peak_q = peak_qalpha = peak_a = 0.0
    trace = []
    while prop > 0.0 and t < 1_200.0:
        rho = RHO0 * math.exp(-h / H_SCALE)
        q_kpa = 0.5 * rho * v * v / 1e3
        throttle = 1.0
        if q_kpa > q_target_kpa:
            throttle = max(0.4, 1.0 - 0.08 * (q_kpa - q_target_kpa))
        f = thrust_kn * 1e3 * throttle
        drag = q_kpa * 1e3 * cd * frontal_m2
        a = (f - drag) / m - G0 * max(0.0, 1.0 - h / 6.371e6) ** 2
        v += a * dt
        h += v * dt
        burn = mdot_kgps * throttle * dt
        m -= burn
        prop -= burn
        t += dt
        alpha = 3.0 if h < 30_000.0 else 0.0
        peak_q = max(peak_q, q_kpa)
        peak_qalpha = max(peak_qalpha, q_kpa * alpha)
        peak_a = max(peak_a, (f / m) / G0)
        trace.append((t, q_kpa, q_kpa * alpha, throttle))
    return {"peak_q_kpa": peak_q, "peak_qalpha": peak_qalpha,
            "peak_a_g": peak_a, "burnout_h_m": h, "burnout_v_ms": v,
            "trace": trace}


def qalpha_limit_kpadeg(vessel: GridVessel) -> float:
    fins = sum(1 for p in vessel.parts
               if p.spec.get("qalpha_bonus_kpadeg"))
    return QALPHA_LIMIT + QALPHA_FIN_BONUS * min(2, fins)


def validate_e7(vessel: GridVessel, peak_q_kpa: float) -> list[int]:
    """Part indices whose q_max the simmed peak q exceeds."""
    return [i for i, p in enumerate(vessel.parts)
            if peak_q_kpa > part_q_max_kpa(p.spec)]
