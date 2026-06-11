"""Interactive powered descent (depth update): the landing, FLOWN.

Same physics as fly_landing — deorbit, rails coast to periapsis, then the
braking phase integrated at SIM_DT — but the braking phase runs under
player command: throttle against a retro-locked attitude, a suicide-burn
ladder on the HUD, and a touchdown that is only as soft as you make it.
'A' hands the stick to fly_landing's own control law (autoland) when a
qualified pilot is aboard. Crashing loses the vehicle and everyone on it.

Aero worlds skip the orbital braking (the atmosphere did it — fly_entry
adjudicates heating separately) and start the flown phase subsonic.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from aphelion.core.units import G0
from aphelion.sim.flight.landing import SAFETY_MARGIN, TOUCHDOWN_LIMIT
from aphelion.sim.orbits import transfers as tr
from aphelion.sim.orbits.kepler import elements_to_state, state_to_elements
from aphelion.sim.vessels.vessel import Vessel


@dataclass(slots=True)
class LiveDescent:
    vessel: Vessel
    mu: float
    radius: float
    site_id: str
    x: float
    y: float
    vx: float
    vy: float
    coast_s: float = 0.0            # rails time spent reaching periapsis
    dv_used: float = 0.0
    downrange: float = 0.0          # ground-track distance flown, m
    t: float = 0.0
    throttle_cmd: float = 0.0
    auto: bool = False
    outcome: str | None = None      # None | "landed" | "crash"
    td_speed: float = float("inf")
    # HUD telemetry mirrors
    h: float = 0.0
    v: float = 0.0
    v_up: float = 0.0
    twr: float = 0.0
    stop_dist: float = float("inf")
    burn_ratio: float = 0.0         # >=1.0 means BURN NOW
    throttle_eff: float = 0.0
    events: list[str] = field(default_factory=list)

    # -- constructors ---------------------------------------------------------

    @classmethod
    def from_orbit(cls, vessel: Vessel, mu: float, radius: float,
                   site_id: str, rx: float, ry: float, vxx: float,
                   vyy: float, t0: float,
                   periapsis_alt: float = 15e3) -> "LiveDescent":
        """Vacuum profile: impulsive deorbit from the CURRENT state to a
        low periapsis, exact rails coast there, hand over the stick."""
        r0 = math.hypot(rx, ry)
        v0 = math.hypot(vxx, vyy)
        a_deorbit = 0.5 * (r0 + radius + periapsis_alt)
        v_after = tr.visviva_speed(mu, r0, a_deorbit)
        dv_deorbit = max(0.0, v0 - v_after)
        isp = max(vessel.active_isp(), 1.0)
        vessel.drain_propellant(
            vessel.total_mass_kg()
            * (1.0 - math.exp(-dv_deorbit / (isp * G0))))
        scale = v_after / v0 if v0 > 0.0 else 1.0
        el = state_to_elements(rx, ry, vxx * scale, vyy * scale, t0, mu)
        t_peri = el.tau
        period = el.period if math.isfinite(el.period) else 0.0
        while t_peri <= t0 and period > 0.0:
            t_peri += period
        x, y, vx, vy = elements_to_state(el, t_peri)
        live = cls(vessel=vessel, mu=mu, radius=radius, site_id=site_id,
                   x=x, y=y, vx=vx, vy=vy, coast_s=max(0.0, t_peri - t0),
                   dv_used=dv_deorbit)
        live.events.append(
            f"DEORBIT {dv_deorbit:,.0f} m/s — coast "
            f"{live.coast_s / 60.0:,.0f} min to periapsis. Throttle is yours.")
        live._telemetry()
        return live

    @classmethod
    def from_entry(cls, vessel: Vessel, mu: float, radius: float,
                   site_id: str, h0: float = 8e3, v_h: float = 160.0,
                   v_v: float = -110.0) -> "LiveDescent":
        """Aero profile: the atmosphere already shed orbital speed (entry
        is adjudicated by fly_entry); fly the subsonic terminal phase."""
        r = radius + h0
        live = cls(vessel=vessel, mu=mu, radius=radius, site_id=site_id,
                   x=r, y=0.0, vx=v_v, vy=v_h)
        live.events.append(
            f"ENTRY COMPLETE at {h0 / 1e3:,.0f} km — "
            f"powered terminal descent. Throttle is yours.")
        live._telemetry()
        return live

    # -- commands -------------------------------------------------------------

    def stage(self) -> bool:
        if self.outcome is None and len(self.vessel.stage_plan) > 1:
            self.vessel.stage()
            self.events.append(f"t={self.t:5.1f}s  STAGE away")
            return True
        return False

    def engage_autoland(self) -> None:
        if self.outcome is None and not self.auto:
            self.auto = True
            self.events.append("AUTOLAND engaged — pilot has the stick")

    # -- physics --------------------------------------------------------------

    def _telemetry(self) -> None:
        r = math.hypot(self.x, self.y)
        self.h = r - self.radius
        self.v = math.hypot(self.vx, self.vy)
        r_hat = (self.x / r, self.y / r)
        self.v_up = self.vx * r_hat[0] + self.vy * r_hat[1]
        m = self.vessel.total_mass_kg()
        g = self.mu / (r * r)
        f_max = self.vessel.active_thrust_n()
        self.twr = f_max / (m * g) if m > 0.0 else 0.0
        a_net = max(f_max / m - g if m > 0.0 else 0.0, 0.1)
        self.stop_dist = self.v * self.v / (2.0 * a_net)
        self.burn_ratio = (self.stop_dist * SAFETY_MARGIN
                           / max(self.h - 150.0, 1.0))

    def step(self, dt: float) -> None:
        if self.outcome is not None:
            return
        m = self.vessel.total_mass_kg()
        if m <= 0.0:
            self.outcome = "crash"
            self.events.append("VEHICLE BREAKUP")
            return
        r = math.hypot(self.x, self.y)
        h = r - self.radius
        v = math.hypot(self.vx, self.vy)
        r_hat = (self.x / r, self.y / r)
        v_up = self.vx * r_hat[0] + self.vy * r_hat[1]
        g = self.mu / (r * r)

        if h <= 1.0:
            self.td_speed = v
            if v <= TOUCHDOWN_LIMIT:
                self.outcome = "landed"
                self.events.append(
                    f"TOUCHDOWN at {v:,.2f} m/s — "
                    f"{self.vessel.active_propellant_kg():,.0f} kg remains")
            else:
                self.outcome = "crash"
                self.events.append(
                    f"SURFACE IMPACT at {v:,.1f} m/s — loss of vehicle")
            self._telemetry()
            return

        f_max = self.vessel.active_thrust_n()
        thrust = 0.0
        ux = uy = 0.0
        if self.auto and f_max > 0.0:
            # fly_landing's own law: suicide trigger, then LM terminal sink
            a_net = max(f_max / m - g, 0.1)
            stop_dist = v * v / (2.0 * a_net)
            if v > 25.0:
                if stop_dist * SAFETY_MARGIN >= h - 150.0:
                    thrust = f_max
                    ux, uy = -self.vx / v, -self.vy / v
            else:
                target_vs = -min(60.0, max(2.0, h / 15.0))
                err = target_vs - v_up
                a_up = g + 1.5 * err
                hvx = self.vx - v_up * r_hat[0]
                hvy = self.vy - v_up * r_hat[1]
                a_cx = a_up * r_hat[0] - 1.0 * hvx
                a_cy = a_up * r_hat[1] - 1.0 * hvy
                a_mag = math.hypot(a_cx, a_cy)
                if a_mag > 0.05:
                    thrust = min(f_max, max(self.vessel.min_throttle() * f_max,
                                            m * a_mag))
                    ux, uy = a_cx / a_mag, a_cy / a_mag
        elif f_max > 0.0 and self.throttle_cmd > 0.0:
            # manual: retro-locked above 25 m/s; near the ground the lock
            # blends toward 'up' so the final meters are a hover, not a dive
            throttle = max(self.vessel.min_throttle(),
                           min(1.0, self.throttle_cmd))
            thrust = f_max * throttle
            if v > 1.0:
                blend = min(1.0, v / 25.0)
                ux = -self.vx / v * blend + r_hat[0] * (1.0 - blend)
                uy = -self.vy / v * blend + r_hat[1] * (1.0 - blend)
                un = math.hypot(ux, uy) or 1.0
                ux, uy = ux / un, uy / un
            else:
                ux, uy = r_hat

        if thrust > 0.0:
            isp = self.vessel.active_isp()
            mdot = thrust / (isp * G0)
            drained = self.vessel.drain_propellant(mdot * dt)
            if drained < mdot * dt * 0.99:
                thrust *= drained / (mdot * dt) if mdot * dt > 0.0 else 0.0
                if (thrust <= 0.0 and self.events
                        and "FLAMEOUT" not in self.events[-1]):
                    self.events.append(
                        f"t={self.t:5.1f}s  FLAMEOUT — tanks dry"
                        + (" (SPACE to stage)"
                           if len(self.vessel.stage_plan) > 1 else ""))
            self.dv_used += thrust / m * dt
        self.throttle_eff = thrust / f_max if f_max > 0.0 else 0.0

        ax = (thrust / m) * ux - g * r_hat[0]
        ay = (thrust / m) * uy - g * r_hat[1]
        self.vx += ax * dt
        self.vy += ay * dt
        self.x += self.vx * dt
        self.y += self.vy * dt
        v_h = math.sqrt(max(v * v - v_up * v_up, 0.0))
        self.downrange += v_h * dt
        self.t += dt
        self._telemetry()
