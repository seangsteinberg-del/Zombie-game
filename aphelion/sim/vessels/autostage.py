"""Drydock auto-staging + live-readout math (06 §2.2/§2.3/§2.6): split
the grid into stages at the decouplers (bottom-up), turn each into a
buildermath StageDef (O/F-burnable prop, unburnable surplus rides as
inert), wet/dry COM, the thrust-torque control badge, and the bridge
that flattens a grid design into the 1D Vessel's stage plan so grid
ships actually FLY.
"""

from __future__ import annotations

import math

from aphelion.sim.vessels.buildermath import (
    StageDef, burnable_prop_t)
from aphelion.sim.vessels.grid import GridVessel


def _tank_loads(spec: dict) -> dict[str, float]:
    tank = spec.get("tank")
    if not tank:
        return {}
    cap = float(tank.get("capacity_t", 0.0))
    mix = tank.get("mixture", {})
    if not mix:
        return {}
    return {res: cap * float(frac) for res, frac in mix.items()}


def part_wet_t(spec: dict) -> float:
    """Dry + default fill (tank capacity, solid grain, water fill)."""
    m = float(spec.get("mass_t", 0.0))
    tank = spec.get("tank")
    if tank:
        m += float(tank.get("capacity_t", 0.0))
    eng = spec.get("engine")
    if eng and eng.get("solid"):
        m += float(eng.get("solid_prop_t", 0.0))
    m += float(spec.get("water_fill_t", 0.0))
    return m


def stage_components(v: GridVessel) -> list[list[int]]:
    """Connected components after cutting every decoupler, each WITH the
    decoupler that rides down on its top face; ordered bottom-up by mean
    centroid height. A vessel with no decouplers is one stage."""
    dec = {i for i, p in enumerate(v.parts) if p.spec.get("decoupler")}
    comps = v._components(skip=dec)
    # a decoupler is jettisoned with the stage BELOW it: attach each to
    # the component whose top face it sits on
    for d in dec:
        dp = v.parts[d]
        best, best_cy = None, None
        for ci, comp in enumerate(comps):
            for i in comp:
                p = v.parts[i]
                if p.y + p.h == dp.y \
                        and min(p.x + p.w, dp.x + dp.w) > max(p.x, dp.x):
                    cy = p.centroid()[1]
                    if best_cy is None or cy > best_cy:
                        best, best_cy = ci, cy
        if best is None and comps:
            best = min(range(len(comps)),
                       key=lambda ci: min(abs(v.parts[i].centroid()[1]
                                              - dp.centroid()[1])
                                          for i in comps[ci]))
        if best is not None:
            comps[best].add(d)
    def mean_y(comp):
        return sum(v.parts[i].centroid()[1] for i in comp) / len(comp)
    return [sorted(c) for c in sorted(comps, key=mean_y)]


def to_stage_defs(v: GridVessel) -> list[StageDef]:
    """One StageDef per component, bottom-up. Prop is min-limited at the
    stage's engine O/F; the stranded surplus rides as inert mass."""
    out = []
    for comp in stage_components(v):
        engines = []
        loads: dict[str, float] = {}
        dry = 0.0
        solid_prop = 0.0
        for i in comp:
            spec = v.parts[i].spec
            dry += float(spec.get("mass_t", 0.0))
            dry += float(spec.get("water_fill_t", 0.0))
            eng = spec.get("engine")
            if eng and not eng.get("rcs"):
                engines.append(eng)
                if eng.get("solid"):
                    solid_prop += float(eng.get("solid_prop_t", 0.0))
            for res, t in _tank_loads(spec).items():
                loads[res] = loads.get(res, 0.0) + t
        mix = {}
        for eng in engines:
            if not eng.get("solid") and eng.get("propellant"):
                mix = eng["propellant"]
                break
        prop = burnable_prop_t(loads, mix) if mix else 0.0
        stranded = sum(loads.values()) - prop
        out.append(StageDef(engines=engines,
                            inert_t=dry + max(0.0, stranded),
                            prop_t=prop + solid_prop))
    return out


def wet_com(v: GridVessel) -> tuple[float, float]:
    m = sx = sy = 0.0
    for p in v.parts:
        pm = part_wet_t(p.spec)
        cx, cy = p.centroid()
        m += pm
        sx += pm * cx
        sy += pm * cy
    if m <= 0.0:
        return 0.0, 0.0
    return sx / m, sy / m


def torque_badge(v: GridVessel) -> dict:
    """Bottom-stage thrust-line balance at wet AND dry COM (06 §2.3):
    τ_net = Σ F_i·(x_i − x_COM); authority τ_ctl = Σ F_i·sin(δ_i)·L_i.
    GREEN ≤ 0.5·τ_ctl, YELLOW ≤ 0.9, RED above."""
    comps = stage_components(v)
    if not comps:
        return {"badge": "GREEN", "tau_net": 0.0, "tau_ctl": 0.0}
    engines = [(v.parts[i], v.parts[i].spec["engine"])
               for i in comps[0]
               if v.parts[i].spec.get("engine")
               and not v.parts[i].spec["engine"].get("rcs")]
    worst = "GREEN"
    tau_net_w = tau_ctl_w = 0.0
    for com in (wet_com(v), v.com()):
        cx, cy = com
        tau_net = sum(float(e["thrust_kN"]) * (p.centroid()[0] - cx)
                      for p, e in engines)
        tau_ctl = sum(
            float(e["thrust_kN"])
            * math.sin(math.radians(float(e.get("gimbal_deg", 0.0))))
            * math.hypot(p.centroid()[0] - cx, p.centroid()[1] - cy)
            for p, e in engines)
        if abs(tau_net) <= 0.5 * tau_ctl + 1e-9:
            badge = "GREEN"
        elif abs(tau_net) <= 0.9 * tau_ctl + 1e-9:
            badge = "YELLOW"
        else:
            badge = "RED"
        rank = ["GREEN", "YELLOW", "RED"]
        if rank.index(badge) > rank.index(worst):
            worst = badge
            tau_net_w, tau_ctl_w = tau_net, tau_ctl
        elif worst == "GREEN":
            tau_net_w, tau_ctl_w = tau_net, tau_ctl
    return {"badge": worst, "tau_net": tau_net_w, "tau_ctl": tau_ctl_w}


def cost_musd(v: GridVessel) -> float:
    return sum(float(p.spec.get("cost_musd", 0.0)) for p in v.parts)


def flyable_stack(v: GridVessel) -> list[list[str]]:
    """The bridge to the 1D flight Vessel: stage plan bottom-up, parts
    the flight layer understands (engine/tank/crew rows), ordered
    bottom-to-top within each stage. Decouplers/structure carry their
    mass in the grid readouts but the flight stack flies the
    engine/tank/crew skeleton."""
    plan = []
    for comp in stage_components(v):
        rows = [i for i in comp
                if v.parts[i].spec.get("type") in
                ("engine", "tank", "crew")]
        rows.sort(key=lambda i: v.parts[i].y)
        plan.append([v.parts[i].pid for i in rows])
    return [st for st in plan if st]
