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
        self.lss_bonus = 1.0                  # engineer aboard (game/crew)
        self.prox_ops_dv = self.PROX_OPS_DV   # pilot aboard cuts this
        self.dock_joints: list[int] = []      # row offsets of docked stacks
        self.dock_joint_ports: list[str] = []  # port class at each joint
        self.port_repair_h = 0.0              # docking ring damage backlog
        self.cargo: dict[str, float] = {}     # bulk parts/goods aboard, kg
        self.yard_job: dict | None = None     # an orbital build under way
        self.legs = []
        self._legs_t0 = -1.0

    @property
    def cargo_cap_kg(self) -> float:
        return sum(float(self.vessel.part(r).get("cargo_t", 0.0))
                   for r in self.vessel.rows) * 1_000.0

    @property
    def cargo_kg(self) -> float:
        return sum(self.cargo.values())

    def load_cargo(self, res: str, kg: float) -> float:
        """Put kg of bulk cargo aboard, capped by cargo cells."""
        room = max(0.0, self.cargo_cap_kg - self.cargo_kg)
        take = min(kg, room)
        if take > 0.0:
            self.cargo[res] = self.cargo.get(res, 0.0) + take
        return take

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
        return days * self.lss_bonus / len(self.crew)

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

    # -- surface operations (01 Δv map: landing/ascent paid in propellant) ---

    LANDING_GATE_PERI_M = 300e3   # must be in a LOW orbit to begin descent

    def can_land(self, site: dict, t: float) -> tuple[bool, str]:
        """Landing pre-flight: right body, right hardware, and a REAL
        parking orbit (no more 'landing' off a hyperbolic flyby for the
        same fixed dv — establish low orbit first)."""
        if self.landed_at is not None:
            return False, "already on the surface"
        if self.frame_id != site["body"]:
            return False, f"not in {site['body'].split(':')[1]} orbit"
        need = site.get("requires_part")
        if need and not any(r.part_id == need for r in self.vessel.rows):
            return False, f"requires {need.split(':')[1]} aboard"
        body = self.tree.body(self.frame_id)
        if self.elements.alpha <= 0.0:
            return False, "on an escape trajectory — capture first"
        peri_alt = self.elements.periapsis - body.radius
        if peri_alt > self.LANDING_GATE_PERI_M:
            return False, (f"periapsis {peri_alt / 1e3:,.0f} km — lower it "
                           f"below {self.LANDING_GATE_PERI_M / 1e3:,.0f} km")
        return True, ""

    def land_at(self, site_id: str, site: dict, t: float) -> bool:
        """Descend to a surface site. Pays the site's REAL landing dv from
        the tanks (aero sites pay only the propulsive terminal phase).
        Exotic sites demand their hardware (07): no gondola, no Venus."""
        ok, _ = self.can_land(site, t)
        if not ok:
            return False
        if not self._pay_dv(site["land_dv"]):
            return False
        self.landed_at = site_id
        self._legs_t0 = -1.0
        self.legs = []
        return True

    def finalize_landing(self, site_id: str) -> None:
        """Called by the FLOWN descent on touchdown: the propellant was
        already drained by the live integrator, so just plant the flag."""
        self.landed_at = site_id
        self._legs_t0 = -1.0
        self.legs = []

    def relaunch(self, site: dict, t: float) -> bool:
        """Ascend from the surface back to a 100 km circular parking orbit,
        paying the site's real ascent dv."""
        from aphelion.sim.orbits import transfers as tr
        if self.landed_at is None:
            return False
        if not self._pay_dv(site["ascent_dv"]):
            return False
        body = self.tree.body(self.frame_id)
        r_orb = body.radius + 100e3
        self.elements = state_to_elements(
            r_orb, 0.0, 0.0, tr.circular_speed(body.mu, r_orb), t, body.mu)
        self.landed_at = None
        self._legs_t0 = -1.0
        return True

    # -- rendezvous / docking (06 §3: a docked assembly is ONE entity) -------

    RENDEZVOUS_ENVELOPE_M = 100e3       # below rails resolution: prox-ops
    PROX_OPS_DV = 20.0                  # terminal docking budget, m/s

    def rendezvous_cost(self, other: "FleetVessel", t: float,
                        include_prox: bool = True) -> float | None:
        """The dv this vessel (chaser) pays to match `other` and dock, or
        None when out of the rendezvous envelope (different frame, landed,
        or farther than the prox-ops gameplay radius). With
        include_prox=False, only the velocity-match part is quoted (the
        FLOWN prox-ops approach pays its own terminal RCS)."""
        if (other is self or self.frame_id != other.frame_id
                or self.landed_at is not None or other.landed_at is not None):
            return None
        rx, ry, vx, vy = self.state(t)
        ox, oy, ovx, ovy = other.state(t)
        if math.hypot(rx - ox, ry - oy) > self.RENDEZVOUS_ENVELOPE_M:
            return None
        base = math.hypot(vx - ovx, vy - ovy)
        return base + (self.prox_ops_dv if include_prox else 0.0)

    def dock_join(self, other: "FleetVessel", port_size: str = "S") -> None:
        """Merge this (chaser) into `other` with no further dv charge —
        the approach was already paid (instant dock or flown prox-ops).
        The joint remembers its port class: only a DK-L carries fluid
        lines, and burns load the joint at its rating (06 §3.3).
        The caller removes the chaser from the fleet."""
        from aphelion.sim.vessels.docking import dock
        other.dock_joints.append(len(other.vessel.rows))
        other.dock_joint_ports.append(port_size)
        dock(other.vessel, self.vessel)
        other.crew.extend(self.crew)
        self.crew = []
        # bulk cargo transfers with the hull (yard resupply runs)
        for res, kg in self.cargo.items():
            other.cargo[res] = other.cargo.get(res, 0.0) + kg
        self.cargo = {}
        other._legs_t0 = -1.0

    def dock_with(self, other: "FleetVessel", t: float) -> bool:
        """Chaser docks to `other` (the primary keeps name and orbit).
        Runs the E8 mate-plan (matching port class or no dock), pays the
        rendezvous dv from THIS vessel's tanks, then merges rows; the
        caller removes the chaser from the fleet."""
        from aphelion.sim.stations.ports import mate_plan
        psize, _, _ = mate_plan(self.vessel, other.vessel)
        if psize is None:
            return False
        cost = self.rendezvous_cost(other, t)
        if cost is None or not self._pay_dv(cost):
            return False
        self.dock_join(other, port_size=psize)
        return True

    UNDOCK_SEP_MS = 1.5             # mechanical spring separation, m/s

    def undock_last(self, t: float, new_vid: int) -> "FleetVessel | None":
        """Split the most recent docked stack back off; returns the new
        vessel on a VISIBLY diverging orbit (spring separation imparts a
        real radial impulse — the two icons no longer overlap forever)."""
        from aphelion.sim.vessels.docking import undock
        if not self.dock_joints:
            return None
        joint = self.dock_joints.pop()
        if self.dock_joint_ports:
            self.dock_joint_ports.pop()
        going = list(range(joint, len(self.vessel.rows)))
        if not going:
            return None
        split = undock(self.vessel, going)
        self._legs_t0 = -1.0
        rx, ry, vx, vy = self.state(t)
        r = math.hypot(rx, ry) or 1.0
        body = self.tree.body(self.frame_id)
        el_split = state_to_elements(rx, ry,
                                     vx + self.UNDOCK_SEP_MS * rx / r,
                                     vy + self.UNDOCK_SEP_MS * ry / r,
                                     t, body.mu)
        return FleetVessel(self.tree, self.frame_id, el_split, split,
                           f"{self.name}-B", new_vid, t_now=t)

    def _fluid_blocked_rows(self) -> set[int]:
        """Row indices isolated behind a docking joint with no fluid
        lines: propellant only crosses a DK-L joint (06 §3.3). Joints
        with no recorded class (pre-port saves) are grandfathered as L."""
        blocked: set[int] = set()
        for k, joint in enumerate(self.dock_joints):
            port = (self.dock_joint_ports[k]
                    if k < len(self.dock_joint_ports) else "L")
            if port != "L":
                blocked.update(range(joint, len(self.vessel.rows)))
        return blocked

    def crossfeed(self) -> float:
        """Depot refuel: top the ACTIVE stage's tanks from any other rows
        holding the same resources (a docked tanker's load becomes burnable).
        Rows behind a non-L docking joint cannot feed. Returns kg moved."""
        active = set(self.vessel.active_stage())
        blocked = self._fluid_blocked_rows()
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
                    if j in active or j in blocked or room <= 0.0:
                        continue
                    have = src.fill.get(res, 0.0)
                    take = min(have, room)
                    if take > 0.0:
                        src.fill[res] = have - take
                        row.fill[res] = row.fill.get(res, 0.0) + take
                        room -= take
                        moved += take
        return moved

    def _row_mass_t(self, i: int) -> float:
        r = self.vessel.rows[i]
        return (self.vessel.part(r)["mass_t"]
                + sum(r.fill.values()) / 1_000.0)

    def docked_mass_t(self) -> float:
        """Tonnes riding beyond the FIRST docking joint — the W6 spin
        imbalance a docked visitor puts on a spinning ring."""
        if not self.dock_joints:
            return 0.0
        j0 = min(self.dock_joints)
        return sum(self._row_mass_t(i)
                   for i in range(j0, len(self.vessel.rows)))

    def joint_burn_loads(self, a_ms2: float) -> list[tuple[str, float, float]]:
        """(port_class, payload_t, load_kN) per docking joint under a
        burn at a_ms2 — everything beyond the joint loads it (06 §2.8a)."""
        out = []
        for k, joint in enumerate(self.dock_joints):
            port = (self.dock_joint_ports[k]
                    if k < len(self.dock_joint_ports) else "L")
            payload_t = sum(self._row_mass_t(i)
                            for i in range(joint, len(self.vessel.rows)))
            out.append((port, payload_t, payload_t * a_ms2))
        return out

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
