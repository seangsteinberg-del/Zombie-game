"""Vacuum landing autopilot (Phase 2 DoD: crewed Moon landing).

Profile: from low circular orbit — deorbit burn (impulsive node to a low
periapsis), analytic coast on rails, then the powered braking phase
integrated at SIM_DT: retrograde thrust with a suicide-burn trigger
(start when remaining altitude ~ stopping distance with margin), final
vertical descent capped at v_touch. Touchdown success = contact under the
landing-gear limit (06: < 2 m/s docking class; legs tolerate 3 m/s).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from aphelion.core.units import G0, SIM_DT
from aphelion.sim.orbits import transfers as tr
from aphelion.sim.orbits.kepler import elements_to_state, state_to_elements
from aphelion.sim.vessels.vessel import Vessel

TOUCHDOWN_LIMIT = 3.0      # m/s, landing legs
SAFETY_MARGIN = 1.15       # suicide-burn stopping-distance margin


@dataclass(slots=True)
class LandingResult:
    landed: bool
    touchdown_speed: float
    dv_used: float
    propellant_left_kg: float
    t_touchdown: float
    log: list[str] = field(default_factory=list)


def fly_landing(vessel: Vessel, mu: float, radius: float,
                orbit_alt: float, t0: float = 0.0,
                periapsis_alt: float = 15e3,
                telemetry: list[str] | None = None) -> LandingResult:
    """Full descent from a circular orbit at orbit_alt. Vacuum only."""
    log: list[str] = []
    dv_used = 0.0

    # 1. deorbit: drop periapsis to periapsis_alt (impulsive, retrograde)
    r0 = radius + orbit_alt
    v_circ = tr.circular_speed(mu, r0)
    a_deorbit = 0.5 * (r0 + radius + periapsis_alt)
    v_after = tr.visviva_speed(mu, r0, a_deorbit)
    dv_deorbit = v_circ - v_after
    dv_used += dv_deorbit
    vessel.drain_propellant(
        vessel.total_mass_kg() * (1.0 - math.exp(-dv_deorbit / (vessel.active_isp() * G0))))
    log.append(f"deorbit burn {dv_deorbit:.1f} m/s -> periapsis {periapsis_alt/1e3:.0f} km")

    # 2. coast to periapsis on rails (exact)
    el = state_to_elements(r0, 0.0, 0.0, v_after, t0, mu)
    t_peri = el.tau + el.period            # next periapsis passage
    while t_peri < t0:
        t_peri += el.period
    x, y, vx, vy = elements_to_state(el, t_peri)
    t = t_peri
    log.append(f"coast to periapsis, t={t - t0:.0f} s")

    # 3. powered braking, integrated
    dt = SIM_DT
    touchdown = False
    td_speed = math.inf
    while t - t_peri < 4_000.0:
        m = vessel.total_mass_kg()
        r = math.hypot(x, y)
        h = r - radius
        v = math.hypot(vx, vy)
        r_hat = (x / r, y / r)
        v_up = vx * r_hat[0] + vy * r_hat[1]
        g = mu / (r * r)

        if h <= 1.0:
            touchdown = True
            td_speed = v
            log.append(f"TOUCHDOWN at {v:.2f} m/s, t={t - t_peri:.1f} s after peri")
            break

        f_max = vessel.active_thrust_n()
        if f_max <= 0.0:
            log.append("propellant exhausted in descent")
            break
        a_net = f_max / m - g
        if a_net <= 0.1:
            a_net = 0.1
        stop_dist = v * v / (2.0 * a_net)

        thrust = 0.0
        ux = uy = 0.0
        if v > 25.0:
            # suicide-burn phase: retrograde at full thrust once the
            # stopping distance (with margin) reaches the altitude-to-go;
            # engine OFF otherwise (free coast/fall — landers reignite)
            if stop_dist * SAFETY_MARGIN >= h - 150.0:
                thrust = f_max
                ux, uy = -vx / v, -vy / v
        else:
            # terminal phase: LM-style sink-rate target ramping from -60 to
            # -2 m/s near the ground, PLUS horizontal-drift nulling (the
            # touchdown limit is on TOTAL contact speed); engine off when
            # the commanded vector vanishes
            target_vs = -min(60.0, max(2.0, h / 15.0))
            err = target_vs - v_up           # >0 when falling too fast
            a_up = g + 1.5 * err
            hvx = vx - v_up * r_hat[0]       # horizontal velocity component
            hvy = vy - v_up * r_hat[1]
            a_cx = a_up * r_hat[0] - 1.0 * hvx
            a_cy = a_up * r_hat[1] - 1.0 * hvy
            a_mag = math.hypot(a_cx, a_cy)
            if a_mag > 0.05:
                thrust = min(f_max,
                             max(vessel.min_throttle() * f_max, m * a_mag))
                ux, uy = a_cx / a_mag, a_cy / a_mag

        isp = vessel.active_isp()
        if thrust > 0.0:
            mdot = thrust / (isp * G0)
            drained = vessel.drain_propellant(mdot * dt)
            if drained < mdot * dt * 0.99:
                thrust = 0.0
            dv_used += thrust / m * dt

        ax = (thrust / m) * ux - g * r_hat[0]
        ay = (thrust / m) * uy - g * r_hat[1]
        vx += ax * dt
        vy += ay * dt
        x += vx * dt
        y += vy * dt
        t += dt

        if telemetry is not None and int((t - t_peri) / dt) % 250 == 0:
            telemetry.append(
                f"t={t - t_peri:7.1f}  h={h:9.1f}  v={v:7.2f}  vup={v_up:7.2f}"
                f"  thr={thrust / 1e3:6.1f} kN  stop={stop_dist:9.1f}")

    return LandingResult(
        landed=touchdown and td_speed <= TOUCHDOWN_LIMIT,
        touchdown_speed=td_speed,
        dv_used=dv_used,
        propellant_left_kg=vessel.active_propellant_kg(),
        t_touchdown=t,
        log=log)
