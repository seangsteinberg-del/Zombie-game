"""Interactive proximity operations (depth update): docking, FLOWN.

Once the chaser has paid the rendezvous velocity-match into the 100 km
envelope, the terminal approach is a Clohessy-Wiltshire mini-scene in the
target's LVLH frame (x radial-out, y along-track):

    x'' = 3 n^2 x + 2 n y' + a_x
    y'' =        -2 n x' + a_y

Arrow keys fire discrete RCS pulses charged against a REAL dv budget.
The 50 m sphere is only the approach gate; CONTACT happens at 4 m and
runs the port-capture ladder (06 §3.3): under the port's closing limit
you soft-capture, over it you bounce off the adapter, over 0.5 m/s you
damage the docking ring. 'A' engages the approach autopilot when a
pilot is aboard — which is also exactly how the pilot's prox-ops skill
becomes visible.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from aphelion.sim.stations.ports import PORTS, capture

CAPTURE_RANGE_M = 50.0          # the approach gate (HUD ring)
CAPTURE_SPEED_MS = 2.0          # gate speed advisory (HUD color only)
CONTACT_RANGE_M = 4.0           # adapter touch: the port ladder decides
PULSE_MS = 0.5
PULSE_FINE_MS = 0.05            # vernier taps inside the gate


@dataclass(slots=True)
class ProxOps:
    n: float                       # target orbit mean motion, rad/s
    budget_dv: float               # RCS allowance, m/s (pilot skill shrinks need)
    x: float = -380.0              # start: below and behind, drifting
    y: float = -240.0
    vx: float = 0.15
    vy: float = 0.45
    used_dv: float = 0.0
    t: float = 0.0
    auto: bool = False
    bounces: int = 0
    outcome: str | None = None     # None | "captured" | "damage" | "aborted"
    port_size: str = "S"           # the mated class (E8 already checked)
    magnetic: bool = False         # soft-capture assist: tolerances double
    events: list[str] = field(default_factory=list)

    @property
    def capture_limit_ms(self) -> float:
        return PORTS[self.port_size]["close_ms"] * (
            2.0 if self.magnetic else 1.0)

    @property
    def range_m(self) -> float:
        return math.hypot(self.x, self.y)

    @property
    def speed_ms(self) -> float:
        return math.hypot(self.vx, self.vy)

    @property
    def closing_ms(self) -> float:
        r = self.range_m or 1.0
        return -(self.x * self.vx + self.y * self.vy) / r

    @property
    def dv_left(self) -> float:
        return max(0.0, self.budget_dv - self.used_dv)

    def pulse(self, dx: float, dy: float, mag: float = PULSE_MS) -> bool:
        """One RCS squirt along (dx, dy) — costs real budget."""
        if self.outcome is not None or self.dv_left < mag:
            return False
        norm = math.hypot(dx, dy) or 1.0
        self.vx += mag * dx / norm
        self.vy += mag * dy / norm
        self.used_dv += mag
        return True

    def engage_auto(self) -> None:
        if self.outcome is None and not self.auto:
            self.auto = True
            self.events.append("APPROACH AUTOPILOT — pilot has the stick")

    def step(self, dt: float) -> None:
        if self.outcome is not None:
            return
        if self.auto:
            # PD approach: close along -r at a range-scheduled speed that
            # arrives UNDER the port's capture limit (the pilot knows it)
            r = self.range_m or 1.0
            want = min(3.0, max(0.8 * self.capture_limit_ms, r / 100.0))
            des_vx = -self.x / r * want
            des_vy = -self.y / r * want
            ax = 0.6 * (des_vx - self.vx)
            ay = 0.6 * (des_vy - self.vy)
            a_mag = math.hypot(ax, ay)
            cap = 0.5                                 # RCS accel limit m/s^2
            if a_mag > cap:
                ax *= cap / a_mag
                ay *= cap / a_mag
                a_mag = cap
            cost = a_mag * dt
            if cost <= self.dv_left:
                self.vx += ax * dt
                self.vy += ay * dt
                self.used_dv += cost
            else:
                self.auto = False
                self.events.append("AUTOPILOT OFF — RCS budget exhausted")
        # Clohessy–Wiltshire relative dynamics
        ax_cw = 3.0 * self.n * self.n * self.x + 2.0 * self.n * self.vy
        ay_cw = -2.0 * self.n * self.vx
        self.vx += ax_cw * dt
        self.vy += ay_cw * dt
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.t += dt

        if self.range_m < CONTACT_RANGE_M:
            verdict = capture(self.port_size, self.speed_ms,
                              magnetic=self.magnetic)
            if verdict == "captured":
                self.outcome = "captured"
                self.events.append(
                    f"SOFT CAPTURE at {self.speed_ms:,.2f} m/s — "
                    f"{self.used_dv:,.1f} m/s RCS spent")
            elif verdict == "damage":
                self.outcome = "damage"
                self.events.append(
                    f"HARD IMPACT at {self.speed_ms:,.2f} m/s — "
                    f"docking ring DAMAGED (limit 0.50)")
            else:
                # bounce off the docking adapter: reflect and bleed energy
                r = self.range_m or 1.0
                v_r = (self.x * self.vx + self.y * self.vy) / r
                self.vx -= 1.4 * v_r * self.x / r
                self.vy -= 1.4 * v_r * self.y / r
                self.x *= (CONTACT_RANGE_M + 3.0) / r
                self.y *= (CONTACT_RANGE_M + 3.0) / r
                self.bounces += 1
                self.events.append(
                    f"CONTACT at {self.speed_ms:,.2f} m/s — BOUNCED "
                    f"(DK-{self.port_size} captures at "
                    f"≤ {self.capture_limit_ms:.2f} m/s)")
