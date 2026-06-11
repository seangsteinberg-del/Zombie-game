"""The fleet (13 §3.3 + 06 §3, game layer): persistent campaign vessels
with REAL part rows. Burns drain actual propellant from the active stage
via Tsiolkovsky and stage automatically when a stage runs dry mid-burn;
remaining Δv is always DERIVED from the rows, never stored. Crewed
vessels carry life-support endurance from their crew parts and consume
it in real time.
"""

from __future__ import annotations

import math

from aphelion.core.units import G0, SECONDS_PER_DAY
from aphelion.sim.orbits.kepler import elements_to_state, state_to_elements
from aphelion.sim.orbits.trajectory import predict_trajectory

_PREDICT_HORIZON = 60.0 * SECONDS_PER_DAY


class FleetVessel:
    """One vessel on rails: frame + elements + the real Vessel rows."""

    def __init__(self, tree, frame_id: str, elements, vessel, name: str,
                 vid: int, crew: list[str] | None = None,
                 t_now: float = 0.0) -> None:
        self.tree = tree
        self.frame_id = frame_id
        self.elements = elements
        self.vessel = vessel
        self.name = name
        self.vid = vid
        self.crew = list(crew or [])
        self.landed_at: str | None = None
        self.lss_used_days = 0.0
        self.lss_last_t = t_now
        self.dock_joints: list[int] = []      # row offsets of docked stacks
        self.legs = []
        self._legs_t0 = -1.0

    # -- derived readouts (the rows are the truth) ---------------------------

    @property
    def dv_remaining(self) -> float:
        return sum(s["dv_vac"] for s in self.vessel.stage_stats())

    @property
    def crew_capacity(self) -> int:
        cap = 0
        for row in self.vessel.rows:
            part = self.vessel.part(row)
            if part.get("type") == "crew":
                cap += int(part["crew"]["capacity"])
        return cap

    @property
    def endurance_days(self) -> float:
        """Total crewed-days of consumables divided by heads aboard."""
        days = 0.0
        for row in self.vessel.rows:
            part = self.vessel.part(row)
            if part.get("type") == "crew":
                days += (part["crew"]["endurance_days"]
                         * part["crew"]["capacity"])
        if not self.crew:
            return float("inf")
        return days / len(self.crew)

    @property
    def lss_margin_days(self) -> float:
        return self.endurance_days - self.lss_used_days

    # -- flight --------------------------------------------------------------

    def state(self, t: float):
        return elements_to_state(self.elements, t)

    def _pay_dv(self, cost: float) -> bool:
        """Drain the propellant a burn of `cost` m/s requires, staging
        through the plan as stages run dry. No trajectory change."""
        if cost <= 0.0:
            return True
        if cost > self.dv_remaining + 1e-9:
            return False
        remaining = cost
        guard = 0
        while remaining > 1e-9 and guard < 12:
            guard += 1
            engines = self.vessel.active_engines()
            prop = self.vessel.active_propellant_kg()
            if not engines or prop <= 1e-9:
                if len(self.vessel.stage_plan) > 1:
                    self.vessel.stage()
                    continue
                return False            # pre-check said yes; rows disagree
            isp = self.vessel.active_isp(0.0)
            ve = isp * G0
            m0 = self.vessel.total_mass_kg()
            dv_stage = ve * math.log(m0 / (m0 - prop))
            dv_now = min(remaining, dv_stage)
            burn_kg = m0 * (1.0 - math.exp(-dv_now / ve))
            self.vessel.drain_propellant(burn_kg)
            remaining -= dv_now
            if remaining > 1e-9 and len(self.vessel.stage_plan) > 1:
                self.vessel.stage()
        return remaining <= 1e-6

    def burn(self, t: float, dv_prograde: float, dv_radial: float) -> bool:
        """Impulsive burn paid in REAL propellant. Stages mid-burn when the
        active stage runs dry; refuses (no state change) if the whole stack
        cannot cover the cost."""
        cost = math.hypot(dv_prograde, dv_radial)
        if cost <= 0.0:
            return cost == 0.0
        if not self._pay_dv(cost):
            return False
        rx, ry, vx, vy = self.state(t)
        v = math.hypot(vx, vy)
        r = math.hypot(rx, ry)
        if v == 0.0 or r == 0.0:
            return False
        px, py = vx / v, vy / v
        ux, uy = rx / r, ry / r
        mu = self.tree.body(self.frame_id).mu
        self.elements = state_to_elements(
            rx, ry, vx + dv_prograde * px + dv_radial * ux,
            vy + dv_prograde * py + dv_radial * uy, t, mu)
        self._legs_t0 = -1.0
        return True

    def predict(self, t: float):
        if self.landed_at is not None:
            return []
        if self._legs_t0 < 0.0 or abs(t - self._legs_t0) > 600.0:
            self.legs = predict_trajectory(
                self.tree, self.frame_id, self.elements, t, _PREDICT_HORIZON)
            self._legs_t0 = t
        return self.legs

    def advance_to(self, t: float) -> list[str]:
        """Follow predicted legs through SOI crossings up to time t."""
        if self.landed_at is not None:
            return []
        notes: list[str] = []
        for _ in range(8):
            legs = self.predict(
                max(self._legs_t0, 0.0) if self._legs_t0 >= 0 else t)
            current = None
            for leg in legs:
                if leg.t_start <= t < leg.t_end or leg is legs[-1]:
                    current = leg
                    if leg.t_start <= t:
                        break
            if current is None:
                break
            if (current.frame_id != self.frame_id
                    or current.elements != self.elements):
                if t >= current.t_start:
                    self.frame_id = current.frame_id
                    self.elements = current.elements
                    notes.append(
                        f"{self.name}: frame -> "
                        f"{current.frame_id.split(':')[1]}")
                    self._legs_t0 = -1.0
                    continue
            break
        return notes

    # -- rendezvous / docking (06 §3: a docked assembly is ONE entity) -------

    RENDEZVOUS_ENVELOPE_M = 100e3       # below rails resolution: prox-ops
    PROX_OPS_DV = 20.0                  # terminal docking budget, m/s

    def rendezvous_cost(self, other: "FleetVessel", t: float) -> float | None:
        """The dv this vessel (chaser) pays to match `other` and dock, or
        None when out of the rendezvous envelope (different frame, landed,
        or farther than the prox-ops gameplay radius)."""
        if (other is self or self.frame_id != other.frame_id
                or self.landed_at is not None or other.landed_at is not None):
            return None
        rx, ry, vx, vy = self.state(t)
        ox, oy, ovx, ovy = other.state(t)
        if math.hypot(rx - ox, ry - oy) > self.RENDEZVOUS_ENVELOPE_M:
            return None
        return math.hypot(vx - ovx, vy - ovy) + self.PROX_OPS_DV

    def dock_with(self, other: "FleetVessel", t: float) -> bool:
        """Chaser docks to `other` (the primary keeps name and orbit).
        Pays the rendezvous dv from THIS vessel's tanks, then merges rows;
        the caller removes the chaser from the fleet."""
        from aphelion.sim.vessels.docking import dock
        cost = self.rendezvous_cost(other, t)
        if cost is None or not self._pay_dv(cost):
            return False
        other.dock_joints.append(len(other.vessel.rows))
        dock(other.vessel, self.vessel)
        other.crew.extend(self.crew)
        self.crew = []
        other._legs_t0 = -1.0
        return True

    def undock_last(self, t: float, new_vid: int) -> "FleetVessel | None":
        """Split the most recent docked stack back off; returns the new
        vessel (same orbit, slight phase) or None if nothing is docked."""
        from aphelion.sim.vessels.docking import undock
        if not self.dock_joints:
            return None
        joint = self.dock_joints.pop()
        going = list(range(joint, len(self.vessel.rows)))
        if not going:
            return None
        split = undock(self.vessel, going)
        self._legs_t0 = -1.0
        return FleetVessel(self.tree, self.frame_id, self.elements, split,
                           f"{self.name}-B", new_vid, t_now=t)

    def crossfeed(self) -> float:
        """Depot refuel: top the ACTIVE stage's tanks from any other rows
        holding the same resources (a docked tanker's load becomes burnable).
        Returns kg moved."""
        active = set(self.vessel.active_stage())
        moved = 0.0
        for i, row in enumerate(self.vessel.rows):
            if i not in active:
                continue
            tank = self.vessel.part(row).get("tank")
            if not tank:
                continue
            cap_kg = tank["capacity_t"] * 1_000.0
            for res, share in tank["mixture"].items():
                room = cap_kg * share - row.fill.get(res, 0.0)
                if room <= 0.0:
                    continue
                for j, src in enumerate(self.vessel.rows):
                    if j in active or room <= 0.0:
                        continue
                    have = src.fill.get(res, 0.0)
                    take = min(have, room)
                    if take > 0.0:
                        src.fill[res] = have - take
                        row.fill[res] = row.fill.get(res, 0.0) + take
                        room -= take
                        moved += take
        return moved

    # -- life support (08, vessel-side endurance model) ----------------------

    def tick_lss(self, t: float) -> list[str]:
        """Advance consumable use for crew aboard; returns warning events."""
        events: list[str] = []
        dt_days = (t - self.lss_last_t) / SECONDS_PER_DAY
        self.lss_last_t = t
        if not self.crew or dt_days <= 0.0:
            return events
        before = self.lss_margin_days
        self.lss_used_days += dt_days
        after = self.lss_margin_days
        for threshold, label in ((30.0, "30 days"), (7.0, "SEVEN DAYS")):
            if before > threshold >= after:
                events.append(
                    f"{self.name}: life support {label} remaining")
        if after <= 0.0 and self.crew:
            events.append(
                f"{self.name}: LIFE SUPPORT EXHAUSTED — "
                f"{', '.join(self.crew)} lost")
            self.crew = []
        return events
