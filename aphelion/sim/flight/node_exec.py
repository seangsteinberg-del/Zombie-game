"""Maneuver nodes (01 §3.7, binding).

A node is (t_node, dv_prograde, dv_radial) — no normal component exists in
2D. The node's frame is the craft's prograde/radial directions at t_node on
the predicted trajectory. The node is the plan; reality is always a finite
burn executed by the integrator. The impulsive application below is what the
Planner draws and what acceptance tests measure against.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from aphelion.core.units import G0
from aphelion.sim.orbits.kepler import Elements, elements_to_state, state_to_elements


@dataclass(frozen=True, slots=True)
class ManeuverNode:
    t_node: float
    dv_prograde: float     # m/s, along velocity at t_node
    dv_radial: float = 0.0  # m/s, along outward radial at t_node

    @property
    def dv_total(self) -> float:
        return math.hypot(self.dv_prograde, self.dv_radial)


def apply_node_impulsive(el: Elements, node: ManeuverNode) -> Elements:
    """The planned post-burn conic: instantaneous dv at t_node."""
    rx, ry, vx, vy = elements_to_state(el, node.t_node)
    v = math.hypot(vx, vy)
    if v == 0.0:
        raise ValueError("undefined prograde direction at zero velocity")
    px, py = vx / v, vy / v                      # prograde unit
    r = math.hypot(rx, ry)
    ux, uy = rx / r, ry / r                      # outward radial unit
    nvx = vx + node.dv_prograde * px + node.dv_radial * ux
    nvy = vy + node.dv_prograde * py + node.dv_radial * uy
    return state_to_elements(rx, ry, nvx, nvy, node.t_node, el.mu)


def exhaust_velocity(isp_s: float) -> float:
    return isp_s * G0


def burn_time(m0: float, thrust_n: float, isp_s: float, dv: float) -> float:
    """t_b = (m0 ve / F)(1 - e^(-dv/ve)) — finite burn duration (01 §3.7)."""
    ve = exhaust_velocity(isp_s)
    return (m0 * ve / thrust_n) * (1.0 - math.exp(-dv / ve))


def ignition_time(node: ManeuverNode, m0: float, thrust_n: float,
                  isp_s: float) -> float:
    """Execution splits the burn centered on the node: ignition at
    t_node - t_b/2."""
    return node.t_node - 0.5 * burn_time(m0, thrust_n, isp_s, node.dv_total)


def impulsive_warning(node: ManeuverNode, m0: float, thrust_n: float,
                      isp_s: float, orbit_period: float) -> bool:
    """True when t_b > period/6 — 'impulsive approximation breaking down,
    consider splitting the burn' (01 §3.7 UI rule)."""
    if not math.isfinite(orbit_period):
        return False
    return burn_time(m0, thrust_n, isp_s, node.dv_total) > orbit_period / 6.0


def propellant_used(m0: float, isp_s: float, dv: float) -> float:
    """Tsiolkovsky: m_prop = m0 (1 - e^(-dv/ve))."""
    return m0 * (1.0 - math.exp(-dv / exhaust_velocity(isp_s)))
