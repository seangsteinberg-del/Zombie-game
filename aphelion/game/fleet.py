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

    def burn(self, t: float, dv_prograde: float, dv_radial: float) -> bool:
        """Impulsive burn paid in REAL propellant. Stages mid-burn when the
        active stage runs dry; refuses (no state change) if the whole stack
        cannot cover the cost."""
        cost = math.hypot(dv_prograde, dv_radial)
        if cost <= 0.0 or cost > self.dv_remaining + 1e-9:
            return cost <= 0.0
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
        if remaining > 1e-6:
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
