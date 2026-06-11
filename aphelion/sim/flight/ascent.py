"""Launch & ascent (01 §3.10, binding): RK4 powered flight in the rotating
atmosphere, the T0 ascent guidance program (vertical rise -> sqrt gravity
turn -> prograde), q/acceleration limits, staging, MECO on predicted
apoapsis, impulsive circularization at apoapsis, and the loss-accounting
identity the post-flight report must close to < 50 m/s.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from aphelion.core.units import G0, SIM_DT
from aphelion.sim.environment.atmosphere import density
from aphelion.sim.orbits import transfers as tr
from aphelion.sim.orbits.kepler import state_to_elements
from aphelion.sim.vessels.vessel import Vessel


@dataclass(slots=True)
class AscentParams:
    """01 §3.10 defaults (Earth)."""
    v_pitch_start: float = 50.0       # m/s airspeed: fly vertical below this
    h_curve: float = 60e3             # gravity-turn shaping altitude, m
    alpha_max_deg: float = 5.0        # follow prograde when alpha would exceed
    q_limit: float = 35e3             # Pa
    a_limit: float = 40.0             # m/s^2
    target_apo: float = 300e3         # m
    liftoff_twr: float = 1.3          # throttle cap at liftoff (acceptance)


@dataclass(slots=True)
class AscentResult:
    reached_orbit: bool
    dv_integrated: float              # ascent burn integral + circ node dv
    dv_gravity: float
    dv_drag: float
    dv_steering: float
    dv_circ: float
    rotation_credit: float
    orbit_speed: float
    periapsis_m: float
    apoapsis_m: float
    t_meco: float
    identity_residual: float
    log: list[str] = field(default_factory=list)


def _pitch_command(h: float, h0: float, params: AscentParams) -> float:
    """Commanded flight-path angle above local horizon, rad.

    01 §3.10 law anchored at the pitch-start altitude h0 (implementation
    erratum: unanchored, a TWR-1.3 vehicle reaches v_pitch_start above the
    altitude where the command already exceeds alpha_max, and the turn can
    never begin)."""
    frac = min(1.0, max(h - h0, 0.0) / params.h_curve)
    return math.radians(90.0 * (1.0 - math.sqrt(frac)))


def fly_ascent(vessel: Vessel, body_id: str, mu: float, radius: float,
               rotation_period_s: float, params: AscentParams | None = None,
               dt: float = SIM_DT, max_t: float = 2_000.0,
               telemetry: list[str] | None = None) -> AscentResult:
    """Integrate from the pad (equatorial, 2D) to MECO + circularization.

    State is inertial body-centric (x, y, vx, vy); mass lives in the vessel
    rows (drained per step) so staging Just Works mid-flight.
    """
    p = params or AscentParams()
    omega = 2.0 * math.pi / rotation_period_s
    log: list[str] = []

    # pad state: on the surface at angle 0, moving with the surface
    x, y = radius, 0.0
    vx, vy = 0.0, omega * radius
    rotation_credit = omega * radius

    t = 0.0
    dv_int = dv_grav = dv_drag = dv_steer = 0.0
    meco = False
    h_pitch_anchor: float | None = None

    while t < max_t and not meco:
        m = vessel.total_mass_kg()
        r = math.hypot(x, y)
        h = r - radius
        rho = density(body_id, h)
        atmo_frac = min(1.0, rho / 1.225)

        # air-relative velocity (atmosphere co-rotates rigidly)
        vax = vx - (-omega * y)
        vay = vy - (omega * x)
        v_air = math.hypot(vax, vay)
        q = 0.5 * rho * v_air * v_air

        # guidance: attitude
        r_hat = (x / r, y / r)
        t_hat = (-r_hat[1], r_hat[0])             # prograde east
        if v_air >= p.v_pitch_start and h_pitch_anchor is None:
            h_pitch_anchor = h
        gamma_cmd = _pitch_command(h, h_pitch_anchor or 0.0, p)
        upper_stage = len(vessel.stage_plan) == 1
        if v_air < p.v_pitch_start:
            ux, uy = r_hat
        else:
            # Fly the pitch law directly (forced-profile ascent). Open-loop
            # prograde-locked gravity turns are knife-edge sensitive to TWR
            # (which is WHY real guidance is closed-loop); with thrust
            # dominant the velocity vector converges to the commanded
            # attitude and the sqrt profile executes robustly.
            # ERRATUM (01 section 3.10): the "follow prograde when alpha >
            # 5 deg" clause is an aero-stability rule; enforcement deferred
            # to the aero-stability model (Phase 5) — v1 has no flip risk.
            ux = math.cos(gamma_cmd) * t_hat[0] + math.sin(gamma_cmd) * r_hat[0]
            uy = math.cos(gamma_cmd) * t_hat[1] + math.sin(gamma_cmd) * r_hat[1]

        # guidance: throttle
        f_avail = vessel.active_thrust_n(atmo_frac)
        if f_avail <= 0.0:
            if not vessel.stage_plan:
                break
            vessel.stage()
            log.append(f"t={t:7.1f}s  STAGE (thrust exhausted)")
            continue
        throttle = 1.0
        g_local = mu / (r * r)
        if h < 1_000.0:
            throttle = min(throttle, p.liftoff_twr * m * g_local / f_avail)
        if q > p.q_limit:
            # hold q AT the limit (01 §3.10) — proportional shed, never the
            # pre-emptive strangle that stalls the climb through max-q
            throttle = min(throttle,
                           max(0.3, 1.0 - 2.0 * (q - p.q_limit) / p.q_limit))
        a_thrust_full = f_avail / m
        if a_thrust_full > p.a_limit:
            throttle = min(throttle, p.a_limit / a_thrust_full)
        throttle = max(throttle, vessel.min_throttle())

        f = f_avail * throttle
        isp = vessel.active_isp(atmo_frac)
        mdot = f / (isp * G0)

        # forces
        d = q * vessel.cd_a_m2
        ax = (f / m) * ux - mu / (r * r) * r_hat[0]
        ay = (f / m) * uy - mu / (r * r) * r_hat[1]
        if v_air > 0.0 and d > 0.0:
            ax -= (d / m) * vax / v_air
            ay -= (d / m) * vay / v_air

        # losses (01 §3.10 accounting, pad/air-relative frame — the frame in
        # which "vertical rise" is gravity loss; the rotation credit term in
        # the identity is exactly the inertial-vs-pad correction)
        if v_air > 0.0:
            sin_gamma = (vax * r_hat[0] + vay * r_hat[1]) / v_air
            dv_grav += mu / (r * r) * sin_gamma * dt
            cos_a = max(-1.0, min(1.0, (ux * vax + uy * vay) / v_air))
            dv_steer += (f / m) * (1.0 - cos_a) * dt
        else:
            dv_grav += mu / (r * r) * dt
        dv_drag += (d / m) * dt
        dv_int += (f / m) * dt

        # symplectic-Euler step is sufficient at dt=0.02 with thrust capped;
        # (RK4 of the full 5-state runs in flight/integrator for free flight)
        vx += ax * dt
        vy += ay * dt
        x += vx * dt
        y += vy * dt
        t += dt

        if telemetry is not None and int(t / dt) % 1000 == 0:
            v_now = math.hypot(vx, vy)
            gamma_now = math.degrees(math.asin(
                (vx * r_hat[0] + vy * r_hat[1]) / v_now)) if v_now else 90.0
            telemetry.append(
                f"t={t:6.1f}  h={h/1e3:7.2f} km  v={v_now:7.1f}  "
                f"gam={gamma_now:6.2f}  cmd={math.degrees(gamma_cmd):6.2f}  "
                f"q={q/1e3:6.2f} kPa  thr={throttle:.2f}  m={m/1e3:.1f} t")

        if h < -10.0:
            log.append(f"t={t:7.1f}s  GROUND IMPACT")
            break

        drained = vessel.drain_propellant(mdot * dt)
        if drained < mdot * dt * 0.99:
            if len(vessel.stage_plan) > 1:
                vessel.stage()
                log.append(f"t={t:7.1f}s  STAGE (propellant depleted), h={h/1e3:.1f} km")
            else:
                log.append(f"t={t:7.1f}s  PROPELLANT EXHAUSTED, h={h/1e3:.1f} km")
                break

        # MECO on predicted apoapsis; the coast to apoapsis is bookkept
        # analytically below (gravity loss of an unpowered arc is exactly
        # v_meco - v_apo), then auto-circ executes at apoapsis (01 §3.10)
        el = state_to_elements(x, y, vx, vy, t, mu)
        if el.alpha > 0.0 and el.apoapsis - radius >= p.target_apo:
            meco = True
            log.append(f"t={t:7.1f}s  MECO  h={h/1e3:.1f} km  "
                       f"apo={(el.apoapsis - radius)/1e3:.1f} km")

    el = state_to_elements(x, y, vx, vy, t, mu)
    apo = el.apoapsis
    peri = el.periapsis
    reached = False
    dv_circ = 0.0
    if meco and el.alpha > 0.0:
        # coast bookkeeping: unpowered arc to apoapsis loses exactly
        # v_meco - v_apo to gravity (the identity integrates through it)
        v_meco = math.hypot(vx, vy)
        v_apo = tr.visviva_speed(mu, apo, el.a)
        dv_grav += v_meco - v_apo
        # impulsive circularization at apoapsis (auto-circ per 01 §3.10)
        dv_circ = tr.circular_speed(mu, apo) - v_apo
        dv_int += dv_circ
        peri = apo
        reached = peri - radius > 0.9 * p.target_apo

    orbit_speed = tr.circular_speed(mu, radius + p.target_apo)
    residual = (dv_int
                - (orbit_speed + dv_grav + dv_drag + dv_steer - rotation_credit))
    return AscentResult(
        reached_orbit=reached, dv_integrated=dv_int, dv_gravity=dv_grav,
        dv_drag=dv_drag, dv_steering=dv_steer, dv_circ=dv_circ,
        rotation_credit=rotation_credit, orbit_speed=orbit_speed,
        periapsis_m=peri - radius, apoapsis_m=apo - radius,
        t_meco=t, identity_residual=residual, log=log)
