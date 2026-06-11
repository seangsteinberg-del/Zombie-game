"""Autonomous freighter routes (05 §3.6): the route planner consumes the
delta-v map (computed live from canon mu/radii via the transfer utilities),
prices each leg's propellant with the rocket equation, and runs scheduled
round trips between two ledger networks as deterministic arrival events.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from aphelion.core.units import G0
from aphelion.sim.ledger.network import LedgerNetwork
from aphelion.sim.orbits import transfers as tr


@dataclass(slots=True)
class RouteLeg:
    dv_ms: float
    transfer_time_s: float


def plan_leo_llo_leg(mu_earth: float, mu_moon: float, r_leo: float,
                     r_llo: float, a_moon: float) -> RouteLeg:
    """LEO -> LLO one-way: TLI from LEO + LOI at the Moon (patched conics,
    canonical map values; aerobraking not used on this leg)."""
    dv_tli, _, t_transfer = tr.hohmann(mu_earth, r_leo, a_moon)
    # arrival v-infinity relative to the Moon ~ difference of apoapsis speed
    # and the Moon's circular speed; capture to LLO via Oberth at periapsis
    a_t = 0.5 * (r_leo + a_moon)
    v_apo = tr.visviva_speed(mu_earth, a_moon, a_t)
    v_moon = tr.circular_speed(mu_earth, a_moon)
    vinf = abs(v_moon - v_apo)
    dv_loi = tr.departure_dv(mu_moon, r_llo, vinf)
    return RouteLeg(dv_ms=dv_tli + dv_loi, transfer_time_s=t_transfer)


def plan_llo_leo_aero_leg(mu_earth: float, mu_moon: float, r_leo: float,
                          r_llo: float, a_moon: float,
                          aero_trim_ms: float = 50.0) -> RouteLeg:
    """LLO -> LEO with aerocapture at Earth (01 delta-v map M5: TEI ~830
    plus ~50 m/s trim). THIS is what makes lunar-propellant export pay:
    the propulsive alternative costs ~3.2 km/s more (rocket equation
    verdict: ~81 t of propellant to deliver 20 t)."""
    a_t = 0.5 * (r_leo + a_moon)
    v_apo = tr.visviva_speed(mu_earth, a_moon, a_t)
    v_moon = tr.circular_speed(mu_earth, a_moon)
    vinf = abs(v_moon - v_apo)
    dv_tei = tr.departure_dv(mu_moon, r_llo, vinf)
    _, _, t_transfer = tr.hohmann(mu_earth, r_leo, a_moon)
    return RouteLeg(dv_ms=dv_tei + aero_trim_ms, transfer_time_s=t_transfer)


def propellant_for_leg(dry_plus_payload_kg: float, dv_ms: float,
                       isp_s: float) -> float:
    """Rocket-equation propellant for one leg."""
    return dry_plus_payload_kg * (math.exp(dv_ms / (isp_s * G0)) - 1.0)


@dataclass(slots=True)
class FreighterRoute:
    """A standing A<->B cargo route. Cargo flows A->B; the freighter refuels
    at A each cycle (propellant drawn from A's stores too)."""
    name: str
    net_a: LedgerNetwork
    net_b: LedgerNetwork
    cargo_resource: str
    cargo_kg: float
    leg: RouteLeg
    isp_s: float
    freighter_dry_kg: float
    propellant_resource: str = "Oxygen"     # simplified single-resource cost
    turnaround_s: float = 2.0 * 86_400.0
    log: list[tuple[float, str]] = field(default_factory=list)

    def cycle_period_s(self) -> float:
        return 2.0 * self.leg.transfer_time_s + 2.0 * self.turnaround_s

    return_leg: "RouteLeg | None" = None

    def propellant_per_cycle_kg(self) -> float:
        back_leg = self.return_leg or self.leg
        out = propellant_for_leg(self.freighter_dry_kg + self.cargo_kg,
                                 self.leg.dv_ms, self.isp_s)
        back = propellant_for_leg(self.freighter_dry_kg,
                                  back_leg.dv_ms, self.isp_s)
        return out + back

    def run(self, t0: float, t1: float) -> int:
        """Execute every complete cycle in [t0, t1): withdraw cargo +
        propellant at A at departure, deliver cargo at B one leg later.
        Deterministic; skips a cycle (logged) when stocks are short."""
        deliveries = 0
        period = self.cycle_period_s()
        n0 = math.ceil(t0 / period - 1e-9)
        k = int(n0)
        while True:
            t_depart = k * period
            if t_depart >= t1:
                break
            if t_depart >= t0:
                need_prop = self.propellant_per_cycle_kg()
                a_cargo = self.net_a.buffers.get(self.cargo_resource)
                a_prop = self.net_a.buffers.get(self.propellant_resource)
                if (a_cargo is None or a_cargo.level < self.cargo_kg
                        or a_prop is None or a_prop.level < need_prop):
                    self.log.append((t_depart, "cycle skipped: insufficient stock"))
                else:
                    a_cargo.level -= self.cargo_kg
                    a_prop.level -= need_prop
                    t_arrive = t_depart + self.leg.transfer_time_s
                    b = self.net_b.buffers.get(self.cargo_resource)
                    if b is not None:
                        b.level = min(b.capacity, b.level + self.cargo_kg)
                    self.log.append((t_arrive, f"delivered {self.cargo_kg:.0f} kg"))
                    deliveries += 1
            k += 1
        return deliveries
