"""Interactive launch (01 §3.10 physics, flown live): the KSP-style pad
ascent. Same equations as fly_ascent — rotating atmosphere, q, staged
thrust, loss bookkeeping — but stepped one SIM_DT at a time under player
command: ignite, throttle, pitch, stage, circularize. The T0 guidance
program (vertical rise -> anchored sqrt turn -> q-hold) is available as
an autopilot ("PROG"); flying manual hands the player the stick.

v1 honesty notes: exceeding q_limit warns but does not yet break the
vehicle (aero-structural failure arrives with the Phase-5 aero model);
circularization assist executes the impulsive burn at apoapsis exactly
as fly_ascent's auto-circ does.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from aphelion.core.units import G0
from aphelion.sim.environment.atmosphere import density
from aphelion.sim.flight.ascent import AscentParams, _pitch_command
from aphelion.sim.orbits import transfers as tr
from aphelion.sim.orbits.kepler import state_to_elements
from aphelion.sim.vessels.vessel import Vessel


@dataclass(slots=True)
class LiveAscent:
    vessel: Vessel
    body_id: str
    mu: float
    radius: float
    omega: float
    total_dv: float                    # design vac dv, for remaining budget
    params: AscentParams = field(default_factory=AscentParams)

    x: float = 0.0
    y: float = 0.0
    vx: float = 0.0
    vy: float = 0.0
    t: float = 0.0
    ignited: bool = False
    prog: bool = True                  # guidance program autopilot
    throttle_cmd: float = 1.0
    pitch_manual_deg: float = 90.0     # above horizon; 90 = straight up
    h_pitch_anchor: float | None = None
    meco: bool = False
    circ_armed: bool = False
    stages_spent: int = 0
    outcome: str | None = None         # None | "orbit" | "lost"
    dv_int: float = 0.0
    dv_grav: float = 0.0
    dv_drag: float = 0.0
    dv_steer: float = 0.0
    # per-frame telemetry mirrors (for the HUD; updated by step())
    h: float = 0.0
    v_air: float = 0.0
    q: float = 0.0
    twr: float = 0.0
    throttle_eff: float = 0.0
    gamma_deg: float = 90.0
    apo_km: float = 0.0
    peri_km: float = float("-inf")
    events: list[str] = field(default_factory=list)

    @classmethod
    def from_pad(cls, vessel: Vessel, body_id: str, mu: float, radius: float,
                 rotation_period_s: float,
                 params: AscentParams | None = None) -> "LiveAscent":
        omega = 2.0 * math.pi / rotation_period_s
        total = sum(s["dv_vac"] for s in vessel.stage_stats())
        live = cls(vessel=vessel, body_id=body_id, mu=mu, radius=radius,
                   omega=omega, total_dv=total,
                   params=params or AscentParams())
        live.x, live.y = radius, 0.0
        live.vx, live.vy = 0.0, omega * radius
        return live

    # -- commands ------------------------------------------------------------

    def ignite(self) -> None:
        if not self.ignited and self.outcome is None:
            self.ignited = True
            self.events.append("IGNITION — liftoff")

    def stage(self) -> bool:
        if self.outcome is None and self.vessel.stage_plan:
            self.vessel.stage()
            self.stages_spent += 1
            self.events.append(f"t={self.t:6.1f}s  STAGE {self.stages_spent} away")
            return True
        return False

    def arm_circularize(self) -> bool:
        """Post-MECO assist: impulsive circ at apoapsis (01 §3.10 auto-circ)."""
        if (self.outcome is None and self.apo_km * 1e3 > 120e3
                and not self.circ_armed):
            self.circ_armed = True
            self.events.append("CIRCULARIZE armed — executes at apoapsis")
            return True
        return False

    @property
    def dv_remaining(self) -> float:
        return max(0.0, self.total_dv - self.dv_int)

    # -- physics -------------------------------------------------------------

    def step(self, dt: float) -> None:
        if self.outcome is not None:
            return
        p = self.params
        r = math.hypot(self.x, self.y)
        self.h = r - self.radius
        if not self.ignited:
            return                      # clamped to the pad

        m = self.vessel.total_mass_kg()
        rho = density(self.body_id, max(self.h, 0.0))
        atmo_frac = min(1.0, rho / 1.225)
        vax = self.vx - (-self.omega * self.y)
        vay = self.vy - (self.omega * self.x)
        self.v_air = math.hypot(vax, vay)
        self.q = 0.5 * rho * self.v_air * self.v_air
        r_hat = (self.x / r, self.y / r)
        t_hat = (-r_hat[1], r_hat[0])
        g_local = self.mu / (r * r)

        # attitude: vertical through tower clear, then program law or stick
        if self.v_air >= p.v_pitch_start and self.h_pitch_anchor is None:
            self.h_pitch_anchor = self.h
        if self.v_air < p.v_pitch_start and self.h < 2_000.0:
            gamma = math.pi / 2.0
        elif self.prog:
            gamma = _pitch_command(self.h, self.h_pitch_anchor or 0.0, p)
        else:
            gamma = math.radians(self.pitch_manual_deg)
        self.gamma_deg = math.degrees(gamma)
        ux = math.cos(gamma) * t_hat[0] + math.sin(gamma) * r_hat[0]
        uy = math.cos(gamma) * t_hat[1] + math.sin(gamma) * r_hat[1]

        # throttle: player command, program limits stacked on top in PROG
        f_avail = self.vessel.active_thrust_n(atmo_frac)
        throttle = max(0.0, min(1.0, self.throttle_cmd))
        if self.meco:
            throttle = 0.0
        if self.prog and f_avail > 0.0 and throttle > 0.0:
            if self.h < 1_000.0:
                throttle = min(throttle,
                               p.liftoff_twr * m * g_local / f_avail)
            if self.q > p.q_limit:
                throttle = min(throttle, max(
                    0.3, 1.0 - 2.0 * (self.q - p.q_limit) / p.q_limit))
            a_full = f_avail / m
            if a_full > p.a_limit:
                throttle = min(throttle, p.a_limit / a_full)
        if throttle > 0.0 and f_avail > 0.0:
            throttle = max(throttle, self.vessel.min_throttle())

        f = f_avail * throttle
        if f > 0.0:
            isp = self.vessel.active_isp(atmo_frac)
            need = f / (isp * G0) * dt
            drained = self.vessel.drain_propellant(need)
            if drained < need * 0.99:
                f *= drained / need if need > 0.0 else 0.0
                if f <= 0.0 and "FLAMEOUT" not in (self.events[-1:] or [""])[0]:
                    self.events.append(
                        f"t={self.t:6.1f}s  FLAMEOUT — stage empty"
                        + ("" if not self.vessel.stage_plan
                           else " (SPACE to stage)"))
                if self.prog and self.vessel.stage_plan and len(
                        self.vessel.stage_plan) > 1:
                    self.stage()
        self.throttle_eff = throttle if f_avail > 0.0 else 0.0
        self.twr = (f_avail / (m * g_local)) if m > 0.0 else 0.0

        d = self.q * self.vessel.cd_a_m2
        ax = (f / m) * ux - g_local * r_hat[0]
        ay = (f / m) * uy - g_local * r_hat[1]
        if self.v_air > 0.0 and d > 0.0:
            ax -= (d / m) * vax / self.v_air
            ay -= (d / m) * vay / self.v_air

        # loss bookkeeping (01 §3.10, pad/air frame)
        if self.v_air > 0.0:
            sin_g = (vax * r_hat[0] + vay * r_hat[1]) / self.v_air
            self.dv_grav += g_local * sin_g * dt
            cos_a = max(-1.0, min(1.0,
                                  (ux * vax + uy * vay) / self.v_air))
            self.dv_steer += (f / m) * (1.0 - cos_a) * dt
        else:
            self.dv_grav += g_local * dt
        self.dv_drag += (d / m) * dt
        self.dv_int += (f / m) * dt

        self.vx += ax * dt
        self.vy += ay * dt
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.t += dt

        el = state_to_elements(self.x, self.y, self.vx, self.vy, self.t,
                               self.mu)
        if el.alpha > 0.0:
            self.apo_km = (el.apoapsis - self.radius) / 1e3
            self.peri_km = (el.periapsis - self.radius) / 1e3
        else:
            self.apo_km = float("inf")
            self.peri_km = (el.periapsis - self.radius) / 1e3

        # program MECO on target apoapsis. The live coast integrates real
        # drag (unlike fly_ascent's analytic coast), so the apoapsis decays
        # on the way up — the circ assist below handles that by burning at
        # the TRUE apoapsis crossing, wherever drag leaves it.
        if (self.prog and not self.meco and el.alpha > 0.0
                and el.apoapsis - self.radius >= p.target_apo):
            self.meco = True
            self.circ_armed = True
            self.events.append(
                f"t={self.t:6.1f}s  MECO — apo {self.apo_km:,.0f} km; "
                f"coasting to circularize")

        # circ assist executes at the TRUE apoapsis crossing (vr sign flip)
        # once clear of sensible atmosphere
        if self.circ_armed and el.alpha > 0.0:
            vr = (self.vx * r_hat[0] + self.vy * r_hat[1])
            if vr <= 0.0 and self.h > 100e3:
                v_now = math.hypot(self.vx, self.vy)
                v_circ = tr.circular_speed(self.mu, r)
                dv_c = abs(v_circ - v_now)
                self.dv_grav += 0.0     # coast loss already integrated live
                self.dv_int += dv_c
                tx, ty = t_hat
                self.vx, self.vy = v_circ * tx, v_circ * ty
                self.circ_armed = False
                self.events.append(
                    f"t={self.t:6.1f}s  CIRC BURN {dv_c:,.0f} m/s")

        # outcomes
        if self.h > 120e3 and self.peri_km > 120.0:
            self.outcome = "orbit"
            self.events.append(
                f"ORBIT  {self.peri_km:,.0f} x {self.apo_km:,.0f} km — "
                f"{self.dv_int:,.0f} m/s spent, "
                f"{self.dv_remaining:,.0f} m/s remains")
        elif self.h < -5.0:
            self.outcome = "lost"
            self.events.append(f"t={self.t:6.1f}s  GROUND IMPACT — "
                               f"loss of vehicle")
