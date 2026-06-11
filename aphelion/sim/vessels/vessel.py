"""Vessel model (13 §3.3 binding aggregation rule: parts are NOT entities —
a vessel is one entity whose parts are rows; aggregates are cached and
recomputed only on structural change).

Part-row shape (binding, save-format-relevant): (part_id, fill {resource:
kg} on containers, condition, attach links). stage_plan is an ordered list
of part-row-index sets; index 0 fires first; staging pops the leading set.

v1 plumbing rule (06 §3 simplified until the builder ships reachability):
stack staging — the active stage's engines drain the active stage's tanks.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from aphelion.core.units import G0


@dataclass(slots=True)
class PartRow:
    part_id: str
    fill: dict[str, float] = field(default_factory=dict)   # resource -> kg
    condition: str = "OK"
    attach: list[tuple[int, str]] = field(default_factory=list)


class Vessel:
    def __init__(self, db, rows: list[PartRow],
                 stage_plan: list[list[int]], cd_a_m2: float = 3.2) -> None:
        self._db = db
        self.rows = rows
        self.stage_plan = [list(s) for s in stage_plan]
        self.cd_a_m2 = cd_a_m2

    # -- content access -----------------------------------------------------

    def part(self, row: PartRow) -> dict:
        return self._db.parts[row.part_id]

    @classmethod
    def fueled_row(cls, db, part_id: str) -> PartRow:
        """A row with tanks topped off to capacity per their mixture."""
        raw = db.parts[part_id]
        fill: dict[str, float] = {}
        tank = raw.get("tank")
        if tank:
            cap_kg = tank["capacity_t"] * 1_000.0
            for res, frac in tank["mixture"].items():
                fill[res] = cap_kg * frac
        return PartRow(part_id=part_id, fill=fill)

    # -- aggregates (recomputed on demand; cheap at <=600 rows) ---------------

    def total_mass_kg(self) -> float:
        m = 0.0
        for row in self.rows:
            m += self.part(row)["mass_t"] * 1_000.0
            m += sum(row.fill.values())
        return m

    def dry_mass_kg(self) -> float:
        return sum(self.part(r)["mass_t"] * 1_000.0 for r in self.rows)

    def active_stage(self) -> list[int]:
        return self.stage_plan[0] if self.stage_plan else []

    def active_engines(self) -> list[PartRow]:
        idx = set(self.active_stage())
        return [r for i, r in enumerate(self.rows)
                if i in idx and "engine" in self.part(r)
                and r.condition == "OK"]

    def active_tanks(self) -> list[PartRow]:
        idx = set(self.active_stage())
        return [r for i, r in enumerate(self.rows)
                if i in idx and "tank" in self.part(r)]

    def active_propellant_kg(self) -> float:
        return sum(sum(r.fill.values()) for r in self.active_tanks())

    def active_thrust_vac_n(self) -> float:
        return sum(self.part(r)["engine"]["thrust_kN"] * 1_000.0
                   for r in self.active_engines())

    def active_isp(self, atmosphere_frac: float = 0.0) -> float:
        """Thrust-weighted Isp; atmosphere_frac 0 = vacuum, 1 = sea level.
        F_SL is derived from Isp_SL per 02 §3.3."""
        num = den = 0.0
        for r in self.active_engines():
            e = self.part(r)["engine"]
            isp = (e["isp_s"] * (1.0 - atmosphere_frac)
                   + e.get("isp_sl_s", e["isp_s"]) * atmosphere_frac)
            f = e["thrust_kN"] * 1_000.0 * isp / e["isp_s"]
            num += f * isp
            den += f
        return num / den if den else 0.0

    def active_thrust_n(self, atmosphere_frac: float = 0.0) -> float:
        """Available thrust; scales with Isp ratio off-design (02 §3.3:
        constant mdot, F = mdot * g0 * Isp(h))."""
        total = 0.0
        for r in self.active_engines():
            e = self.part(r)["engine"]
            isp = (e["isp_s"] * (1.0 - atmosphere_frac)
                   + e.get("isp_sl_s", e["isp_s"]) * atmosphere_frac)
            total += e["thrust_kN"] * 1_000.0 * isp / e["isp_s"]
        return total

    def min_throttle(self) -> float:
        engines = self.active_engines()
        if not engines:
            return 0.0
        return max(self.part(r)["engine"].get("throttle", [0.0, 1.0])[0]
                   for r in engines)

    def drain_propellant(self, kg: float) -> float:
        """Drain from active tanks proportionally; returns kg actually
        drained (less than requested when running dry)."""
        tanks = self.active_tanks()
        avail = sum(sum(r.fill.values()) for r in tanks)
        if avail <= 0.0:
            return 0.0
        take = min(kg, avail)
        for r in tanks:
            tank_total = sum(r.fill.values())
            if tank_total <= 0.0:
                continue
            share = take * tank_total / avail
            scale = max(0.0, 1.0 - share / tank_total)
            for res in r.fill:
                r.fill[res] *= scale
        return take

    def stage(self) -> list[int]:
        """Pop the leading stage set, dropping those rows. Returns dropped
        row indices (caller owns debris bookkeeping)."""
        if not self.stage_plan:
            return []
        dropped = self.stage_plan.pop(0)
        dropped_set = set(dropped)
        keep = [r for i, r in enumerate(self.rows) if i not in dropped_set]
        remap = {}
        new_i = 0
        for i in range(len(self.rows)):
            if i not in dropped_set:
                remap[i] = new_i
                new_i += 1
        self.rows = keep
        self.stage_plan = [[remap[i] for i in s if i in remap]
                           for s in self.stage_plan]
        return dropped

    # -- builder readouts (06 §3: live dv/TWR per stage) ----------------------

    def stage_stats(self, g_surface: float = 9.80665) -> list[dict]:
        """Per-stage (Tsiolkovsky vac dv, liftoff TWR) walking the plan."""
        stats = []
        remaining = self.total_mass_kg()
        for stage in self.stage_plan:
            idx = set(stage)
            engines = [self.rows[i] for i in idx
                       if "engine" in self.part(self.rows[i])]
            tanks = [self.rows[i] for i in idx
                     if "tank" in self.part(self.rows[i])]
            prop = sum(sum(r.fill.values()) for r in tanks)
            thrust = sum(self.part(r)["engine"]["thrust_kN"] * 1_000.0
                         for r in engines)
            if engines:
                isp = sum(self.part(r)["engine"]["isp_s"] for r in engines) / len(engines)
                ve = isp * G0
                dv = ve * (0.0 if remaining <= prop else
                           math.log(remaining / (remaining - prop)))
            else:
                dv = 0.0
            stats.append({
                "dv_vac": dv,
                "twr": thrust / (remaining * g_surface) if remaining else 0.0,
                "prop_kg": prop,
                "stage_mass_kg": remaining,
            })
            stage_mass = sum(self.part(self.rows[i])["mass_t"] * 1_000.0
                             for i in idx) + prop
            remaining -= stage_mass
        return stats
