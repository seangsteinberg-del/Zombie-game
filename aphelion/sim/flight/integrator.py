"""Numeric flight integration (01 §3.5, 13 §3.6): RK4 at fixed dt = 0.02 s,
5-state (x, y, vx, vy, m). Gravity from the current SOI body only (patched
conics); thrust via a guidance callable; mass flow integrated inside the
state vector. Atmospheric forces arrive with the 03 atmosphere tables.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Protocol

import numpy as np

from aphelion.core.math2d import rk4_step
from aphelion.core.units import G0, SIM_DT


@dataclass(frozen=True, slots=True)
class ThrustCommand:
    """Guidance output for one evaluation instant."""
    fx: float = 0.0     # N, in the current SOI frame
    fy: float = 0.0
    mdot: float = 0.0   # kg/s, >= 0 (propellant consumption)


Guidance = Callable[[float, np.ndarray], ThrustCommand]
# (t, state[x, y, vx, vy, m]) -> ThrustCommand


COAST: Guidance = lambda t, y: ThrustCommand()


def prograde_guidance(thrust_n: float, isp_s: float) -> Guidance:
    """Constant-magnitude thrust along the velocity vector."""
    ve = isp_s * G0
    mdot = thrust_n / ve

    def guide(t: float, y: np.ndarray) -> ThrustCommand:
        v = float(np.hypot(y[2], y[3]))
        if v == 0.0:
            return ThrustCommand(0.0, 0.0, 0.0)
        return ThrustCommand(thrust_n * y[2] / v, thrust_n * y[3] / v, mdot)

    return guide


def fixed_direction_guidance(thrust_n: float, isp_s: float,
                             ux: float, uy: float) -> Guidance:
    ve = isp_s * G0
    mdot = thrust_n / ve
    norm = float(np.hypot(ux, uy))
    ux, uy = ux / norm, uy / norm
    return lambda t, y: ThrustCommand(thrust_n * ux, thrust_n * uy, mdot)


def _derivative(mu: float, guidance: Guidance) -> Callable[[float, np.ndarray], np.ndarray]:
    def f(t: float, y: np.ndarray) -> np.ndarray:
        x, yy, vx, vy, m = y
        r2 = x * x + yy * yy
        r = np.sqrt(r2)
        g = -mu / (r2 * r)
        cmd = guidance(t, y)
        inv_m = 1.0 / m
        return np.array([
            vx,
            vy,
            g * x + cmd.fx * inv_m,
            g * yy + cmd.fy * inv_m,
            -cmd.mdot,
        ])
    return f


class FlightIntegrator:
    """Fixed-step RK4 propagation of one craft in its SOI frame.

    State layout (binding, 13 §3.6): [x, y, vx, vy, m] float64.
    """

    def __init__(self, mu: float, guidance: Guidance = COAST,
                 dt: float = SIM_DT) -> None:
        self.mu = mu
        self.guidance = guidance
        self.dt = dt
        self._f = _derivative(mu, guidance)

    def step(self, t: float, state: np.ndarray, n_steps: int = 1) -> tuple[float, np.ndarray]:
        y = state
        for _ in range(n_steps):
            y = rk4_step(self._f, t, y, self.dt)
            t += self.dt
        return t, y

    def run_for(self, t: float, state: np.ndarray,
                duration: float) -> tuple[float, np.ndarray]:
        """Integrate a whole span; duration is rounded to whole steps (the
        sim loop owns exact step accounting via SimClock)."""
        n = int(round(duration / self.dt))
        return self.step(t, state, n)
