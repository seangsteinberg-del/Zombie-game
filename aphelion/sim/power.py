"""Power & thermal (09, binding): real inverse-square solar flux, day/night
cycling as scheduled ledger boundaries, and THE RADIATOR DOCTRINE —
Stefan-Boltzmann heat rejection as a first-class constraint.

Solar: 1361 W/m^2 at 1 AU scaling with 1/d^2 (09 §3.2).
Radiators: Q = eps * sigma * A * N_sides * (T_r^4 - T_sink^4) (09 §3.5).
The canon worked numbers (eps=0.90, per side, T_sink~0): 0.41 kW/m^2 at
300 K, 33.5 kW/m^2 at 900 K — habitats get sails, reactors get fins.
"""

from __future__ import annotations

import math

from aphelion.core.units import AU
from aphelion.sim.ledger.network import LedgerNetwork, Module

SOLAR_CONSTANT_1AU = 1_361.0      # W/m^2 (09 canon)
SIGMA = 5.670374419e-8            # Stefan-Boltzmann, W/m^2 K^4


def solar_flux(distance_m: float) -> float:
    """W/m^2 at heliocentric distance (inverse square)."""
    return SOLAR_CONSTANT_1AU * (AU / distance_m) ** 2


def radiator_rejection_kw(area_m2: float, t_radiator_k: float,
                          t_sink_k: float = 0.0, emissivity: float = 0.90,
                          n_sides: int = 2) -> float:
    """Heat rejected by a radiator panel (09 §3.5 H-1), kW."""
    q = (emissivity * SIGMA * area_m2 * n_sides
         * (t_radiator_k ** 4 - t_sink_k ** 4))
    return q / 1_000.0


def solar_array_module(module_id: str, area_m2: float, efficiency: float,
                       distance_m: float) -> Module:
    """A solar array as a ledger power producer (panel efficiency tiers per
    09 §4.1; flux fixed at build time — re-derive on transfer arrival)."""
    kw = solar_flux(distance_m) * area_m2 * efficiency / 1_000.0
    return Module(module_id=module_id, inputs={}, outputs={},
                  rate_kgps=0.0, power_kw=-kw)


def radiator_module(module_id: str, area_m2: float,
                    t_radiator_k: float, t_sink_k: float = 0.0) -> Module:
    """A radiator as a ledger module: negative heat_kw = rejection capacity.
    (Heat bookkeeping uses the same global-coupling slot as power.)"""
    return Module(module_id=module_id, inputs={}, outputs={}, rate_kgps=0.0,
                  power_kw=0.0,
                  heat_kw=-radiator_rejection_kw(area_m2, t_radiator_k, t_sink_k))


def schedule_day_night(net: LedgerNetwork, array_ids: list[str],
                       t0: float, day_length_s: float, horizon_s: float,
                       sunrise_first: bool = True) -> None:
    """Post the day/night terminator boundaries for a synchronous-rotator
    site (09 §3.2 / 13 §3.9 class-c): arrays toggle OFF at sunset, ON at
    sunrise. Half-period each; t0 is a terminator instant."""
    half = day_length_s / 2.0
    t = t0
    on = sunrise_first
    while t <= t0 + horizon_s:
        kind = "module_on" if on else "module_off"
        for mid in array_ids:
            net.schedule(t, kind, mid)
        t += half
        on = not on


# environment sink temperatures, K (09 H-2): what your radiators stare at.
# Two entries per site kind: (day, night). The lunar-noon 330 K trap and
# Titan's gorgeous 94 K sink are the gameplay extremes.
SINK_K: dict[str, tuple[float, float]] = {
    "psr_ice": (100.0, 100.0),       # crater shadow: always cold
    "regolith": (330.0, 100.0),      # airless noon trap / cold night
    "mars_ice": (235.0, 180.0),
    "aerostat": (310.0, 310.0),      # Venus cloud deck: warm, convective
    "methane_lake": (94.0, 94.0),    # Titan: the best sink in the system
    "ice_burrow": (110.0, 90.0),
}
RADIATOR_T_K = 400.0                 # habitat-loop panel temperature (H-1)


def sink_factor(kind: str, daylight: bool) -> float:
    """Radiator effectiveness vs its rated cold-sink capacity:
    (T_r^4 − T_sink^4)/T_r^4, floored at 15% (heat pumps exist)."""
    day, night = SINK_K.get(kind, (200.0, 150.0))
    t_sink = day if daylight else night
    f = 1.0 - (t_sink / RADIATOR_T_K) ** 4
    return max(0.15, f)


def thermal_balance_kw(net: LedgerNetwork) -> tuple[float, float]:
    """(heat emitted, rejection capacity), kW. v1 rule: every powered
    consumer emits its consumed power as heat (09 H-0: 'there is no fourth
    option'); producers/reactors declare explicit heat_kw; radiators carry
    negative heat_kw (capacity)."""
    emitted = 0.0
    capacity = 0.0
    for m in net.modules:
        if m.state in ("OFF", "FAILED"):
            continue
        h = m.heat_kw
        if h is None:
            h = m.power_kw if m.power_kw > 0.0 else 0.0
        if h >= 0.0:
            emitted += h
        else:
            capacity += -h
    return emitted, capacity
