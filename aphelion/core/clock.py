"""Sim time and the warp controller (13 §3.5; ladder owned by 01 §3.6).

Drift-free time: during numeric flight t = t_anchor + n_steps*SIM_DT with an
int64 step counter; t_anchor re-bases on every mode switch (a float64
accumulator would wander after ~1e7 adds; the counter never does).

The rails warp loop never advances past EventQueue.peek_time() — events are
exact clamps, there is no missed-event code path anywhere.
"""

from __future__ import annotations

import math
from enum import Enum

from aphelion.core.units import SIM_DT

# 01 §3.6 ladder (binding). Rails tiers 1-7; physics warp P2-P4 are RK4
# substeps, not rails rates.
RAILS_RATES: tuple[float, ...] = (5.0, 25.0, 100.0, 1_000.0, 10_000.0, 100_000.0, 1_000_000.0)
PHYSICS_SUBSTEPS: tuple[int, ...] = (2, 3, 4)

# Event guard (01 §3.6): no event may occur within this many real seconds at
# the current rate; the controller lands at 1x 10 sim-seconds before node
# ignition (the ignition event is posted at t_ignition - 10).
EVENT_GUARD_REAL_S = 5.0


class WarpMode(Enum):
    PAUSE = "pause"
    NUMERIC = "numeric"      # 1x and physics warp P2-P4
    RAILS = "rails"          # tiers 1-7


class SimClock:
    """Owns sim time t (float64 s from epoch 2049-01-01 00:00 UTC)."""

    def __init__(self, t0: float = 0.0) -> None:
        self._t_anchor = float(t0)
        self._n_steps = 0          # int64 steps of SIM_DT since anchor

    @property
    def t(self) -> float:
        return self._t_anchor + self._n_steps * SIM_DT

    def step_numeric(self, n: int = 1) -> None:
        self._n_steps += n

    def rebase(self, t: float | None = None) -> None:
        """Re-anchor (every mode switch, and after analytic advances)."""
        self._t_anchor = self.t if t is None else float(t)
        self._n_steps = 0

    def advance_analytic(self, t1: float) -> None:
        if t1 < self.t:
            raise ValueError("analytic advance must not move time backwards")
        self.rebase(t1)


class WarpController:
    """Tier selection + the event guard. Gameplay code requests, never forces
    (13 §3.5); the sim loop reads mode/rate/substeps each frame."""

    def __init__(self) -> None:
        self.mode = WarpMode.NUMERIC
        self.rails_tier = 0          # 0 = not in rails; 1-7 per ladder
        self.physics_level = 0       # 0 = 1x; 1-3 -> P2-P4

    # -- queries -------------------------------------------------------------

    @property
    def rate(self) -> float:
        if self.mode is WarpMode.PAUSE:
            return 0.0
        if self.mode is WarpMode.RAILS:
            return RAILS_RATES[self.rails_tier - 1]
        return float(self.substeps)

    @property
    def substeps(self) -> int:
        if self.mode is WarpMode.NUMERIC and self.physics_level > 0:
            return PHYSICS_SUBSTEPS[self.physics_level - 1]
        return 1

    # -- the event guard -----------------------------------------------------

    @staticmethod
    def max_guarded_tier(t_now: float, t_next_event: float) -> int:
        """Highest rails tier such that the next event stays at least
        EVENT_GUARD_REAL_S real seconds away. 0 means rails not allowed
        (event imminent: be at 1x when it lands)."""
        margin = t_next_event - t_now
        if not math.isfinite(margin):
            return len(RAILS_RATES)
        if margin <= 0.0:
            return 0
        for tier in range(len(RAILS_RATES), 0, -1):
            if margin / RAILS_RATES[tier - 1] >= EVENT_GUARD_REAL_S:
                return tier
        return 0

    def apply_guard(self, t_now: float, t_next_event: float) -> None:
        if self.mode is not WarpMode.RAILS:
            return
        allowed = self.max_guarded_tier(t_now, t_next_event)
        if self.rails_tier > allowed:
            if allowed == 0:
                self.mode = WarpMode.NUMERIC
                self.rails_tier = 0
                self.physics_level = 0
            else:
                self.rails_tier = allowed

    # -- player/gameplay requests ---------------------------------------------

    def request_rails(self, tier: int, *, coasting: bool, in_atmosphere: bool,
                      t_now: float, t_next_event: float) -> bool:
        """Rails warp is forbidden under thrust and below the atmosphere
        interface (01 §3.6). Returns True if granted (possibly at a lower
        guarded tier)."""
        if not coasting or in_atmosphere:
            return False
        tier = max(1, min(tier, len(RAILS_RATES)))
        allowed = self.max_guarded_tier(t_now, t_next_event)
        if allowed == 0:
            return False
        self.mode = WarpMode.RAILS
        self.rails_tier = min(tier, allowed)
        self.physics_level = 0
        return True

    def request_physics_warp(self, level: int, *, q_pa: float,
                             a_thrust: float) -> bool:
        """P2-P4 blocked if q > 20 kPa or |a_thrust| > 30 m/s^2 (01 §3.6)."""
        if q_pa > 20_000.0 or abs(a_thrust) > 30.0:
            return False
        level = max(1, min(level, len(PHYSICS_SUBSTEPS)))
        self.mode = WarpMode.NUMERIC
        self.rails_tier = 0
        self.physics_level = level
        return True

    def drop_to_realtime(self) -> None:
        self.mode = WarpMode.NUMERIC
        self.rails_tier = 0
        self.physics_level = 0

    def pause(self) -> None:
        self.mode = WarpMode.PAUSE

    def unpause(self) -> None:
        if self.mode is WarpMode.PAUSE:
            self.mode = WarpMode.NUMERIC
