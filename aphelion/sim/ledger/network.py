"""THE LEDGER (13 §3.9, binding) — the only model for production, life
support stores, and power balance at every time rate. At 1x it advances in
small spans; at tier 7 in ~4.6 h spans per frame. One code path = no
1x-vs-warp divergence bugs by construction.

Model: per site, pooled buffers (one logical buffer per resource — the
binding topology rule), recipe transformers with a state machine, sources/
sinks, piecewise-constant rates between analytically-computed boundaries.
All flows are exact linear segments; the independent test reference is a
brute-force 1 s ticker that exists only in the test suite (13 §3.16).

Power (09 coupling, v1): "Power" is instantaneous kW. f_power =
clamp(supply/demand); a Battery buffer (kWh) bridges deficits while
charged, and its depletion/full instants are boundaries like any other.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

POWER = "Power"          # kW, instantaneous
BATTERY = "Battery"      # kWh buffer

# module state machine (05 §3.2 subset shipped in v1)
OFF = "OFF"
RUNNING = "RUNNING"
STARVED = "STARVED"
BLOCKED = "BLOCKED"
FAILED = "FAILED"

_FIXED_POINT_MAX = 32
_FIXED_POINT_TOL = 1e-9      # kg/s (binding)
_EPS_T = 1e-9


@dataclass(slots=True)
class Buffer:
    level: float            # kg (kWh for Battery)
    capacity: float

    def clamp(self) -> None:
        if self.level < 1e-9:
            self.level = 0.0
        if self.level > self.capacity - 1e-9:
            self.level = self.capacity


@dataclass(slots=True)
class Module:
    """A recipe transformer. Rates derive from the recipe normalized per kg
    of primary output: rate_kgps is the nominal primary-output mass rate."""
    module_id: str
    inputs: dict[str, float]        # kg per kg of primary output
    outputs: dict[str, float]       # includes byproducts; primary first
    rate_kgps: float                # nominal primary output, kg/s
    power_kw: float = 0.0           # +consumes, -produces (solar/reactor)
    state: str = RUNNING
    f_condition: float = 1.0
    f_labor: float = 1.0
    yield_y: float = 1.0
    # failure pre-rolls (13 §3.9): None = never fails; failure_t is the
    # pre-sampled absolute failure instant — drawn once when the module
    # enters RUNNING, consumed from the module's named RNG substream, so
    # warp can neither dodge nor farm risk and reloads do not reroll fate
    mtbf_s: float | None = None
    failure_t: float | None = None
    # thermal slot (09): None = consumers emit their consumed power as heat;
    # explicit positive = declared waste heat (reactors); negative =
    # rejection capacity (radiators)
    heat_kw: float | None = None


@dataclass(slots=True)
class Source:
    """Deposit/sink with finite stock: extraction (rate>0 fills buffer) or
    external drain (rate<0). Crew metabolism is sinks+sources pairs."""
    source_id: str
    resource: str
    rate_kgps: float                # +into buffer, -out of buffer
    remaining: float = math.inf     # kg extractable (deposits)


@dataclass(slots=True)
class LedgerEvent:
    t: float
    kind: str
    subject: str


class LedgerNetwork:
    def __init__(self, rng=None) -> None:
        self.buffers: dict[str, Buffer] = {}
        self.modules: list[Module] = []
        self.sources: list[Source] = []
        self.rng = rng                  # RngRegistry; None = failures off
        self.scheduled: list[tuple[float, str, str]] = []   # (t, kind, subject)

    def schedule(self, t: float, kind: str, subject: str) -> None:
        """Class-c scheduled boundary (13 §3.9): day/night terminator,
        eclipse entry/exit, shift change, logistics arrival..."""
        self.scheduled.append((t, kind, subject))
        self.scheduled.sort()

    # -- failure pre-rolls (13 §3.9) -------------------------------------------

    def roll_failures(self, t: float) -> None:
        """Pre-sample time-to-failure for every RUNNING module with an MTBF
        and no live roll. Deterministic per (campaign seed, module id)."""
        if self.rng is None:
            return
        for m in self.modules:
            if (m.mtbf_s is not None and m.state == RUNNING
                    and m.failure_t is None):
                draw = self.rng.stream("failures", m.module_id).exponential(m.mtbf_s)
                m.failure_t = t + draw

    def repair(self, m: Module, t: float) -> None:
        """Repair completes: back to RUNNING with a fresh pre-roll."""
        m.state = RUNNING
        m.failure_t = None
        self.roll_failures(t)

    # -- construction ---------------------------------------------------------

    def add_buffer(self, resource: str, level: float, capacity: float) -> None:
        # pooling rule: one logical buffer per resource per network
        if resource in self.buffers:
            b = self.buffers[resource]
            b.level += level
            b.capacity += capacity
        else:
            self.buffers[resource] = Buffer(level, capacity)

    def add_module(self, m: Module) -> None:
        self.modules.append(m)

    def add_source(self, s: Source) -> None:
        self.sources.append(s)

    # -- rate solve (the only subtle part; 13 §3.9) -----------------------------

    def solve_rates(self) -> tuple[dict[str, float], dict[str, float], float]:
        """Piecewise-constant rates valid until the next boundary.

        Returns (module_rates {id: primary kg/s}, buffer_rates {res: kg/s},
        f_power). Monotone fixed-point of the throttle map: rates start
        unthrottled and only decrease => converges (cap 32 iterations,
        freeze + warn on non-convergence; never an infinite loop).
        """
        frac: dict[str, float] = {}
        for m in self.modules:
            runnable = m.state not in (OFF, FAILED)
            frac[m.module_id] = (m.f_condition * m.f_labor * m.yield_y
                                 if runnable else 0.0)

        f_power = 1.0
        battery = self.buffers.get(BATTERY)

        for _ in range(_FIXED_POINT_MAX):
            changed = 0.0

            # power coupling (global): demand is taken at the NON-power-
            # limited fractions — throttled demand would oscillate (throttle
            # satisfies demand -> unthrottle -> deficit -> throttle ...)
            demand = sum(m.power_kw * frac[m.module_id]
                         for m in self.modules
                         if m.power_kw > 0.0 and frac[m.module_id] > 0.0)
            supply = sum(-m.power_kw for m in self.modules
                         if m.power_kw < 0.0 and m.state not in (OFF, FAILED))
            if demand > supply and (battery is None or battery.level <= 0.0):
                new_fp = supply / demand if demand > 0.0 else 1.0
            else:
                new_fp = 1.0
            if abs(new_fp - f_power) > 1e-12:
                changed = max(changed, abs(new_fp - f_power))
                f_power = new_fp

            # per-resource net rates at current fractions
            rates = self._buffer_rates(frac, f_power)

            # throttle by empty inputs / full outputs
            for m in self.modules:
                f = frac[m.module_id]
                if f <= 0.0:
                    continue
                # limit stays power-free: f_power is applied by the rate
                # helpers; folding it in here re-creates the oscillation
                limit = m.f_condition * m.f_labor * m.yield_y
                for res, stoich in m.inputs.items():
                    buf = self.buffers.get(res)
                    if buf is None or buf.level > 0.0:
                        continue
                    inflow = max(0.0, self._inflow_excluding(res, m, frac, f_power))
                    cap_f = inflow / (stoich * m.rate_kgps) if stoich * m.rate_kgps > 0 else 0.0
                    limit = min(limit, cap_f)
                for res, stoich in m.outputs.items():
                    buf = self.buffers.get(res)
                    if buf is None or buf.level < buf.capacity:
                        continue
                    drain = max(0.0, -self._inflow_excluding(res, m, frac, f_power))
                    cap_f = drain / (stoich * m.rate_kgps) if stoich * m.rate_kgps > 0 else 0.0
                    limit = min(limit, cap_f)
                new_f = max(0.0, min(f, limit))
                if abs(new_f - f) > _FIXED_POINT_TOL / max(m.rate_kgps, 1e-12):
                    changed = max(changed, abs(new_f - f))
                frac[m.module_id] = new_f

            if changed <= 1e-12:
                break

        rates = self._buffer_rates(frac, f_power)
        module_rates = {
            m.module_id: frac[m.module_id] * m.rate_kgps
            * (f_power if m.power_kw > 0.0 else 1.0)
            for m in self.modules}

        # battery charge/discharge folds into the Battery buffer rate (kWh/s)
        if battery is not None:
            demand = sum(m.power_kw * frac[m.module_id] for m in self.modules
                         if m.power_kw > 0.0)
            supply = sum(-m.power_kw for m in self.modules
                         if m.power_kw < 0.0 and m.state not in (OFF, FAILED))
            rates[BATTERY] = rates.get(BATTERY, 0.0) + (supply - demand) / 3_600.0
            if battery.level >= battery.capacity and rates[BATTERY] > 0.0:
                rates[BATTERY] = 0.0
            if battery.level <= 0.0 and rates[BATTERY] < 0.0:
                rates[BATTERY] = 0.0

        return module_rates, rates, f_power

    def _inflow_excluding(self, resource: str, exclude: Module,
                          frac: dict[str, float], f_power: float) -> float:
        total = 0.0
        for m in self.modules:
            if m is exclude:
                continue
            f = frac[m.module_id]
            if f <= 0.0:
                continue
            if m.power_kw > 0.0:
                f *= f_power
            r = f * m.rate_kgps
            total += m.outputs.get(resource, 0.0) * r
            total -= m.inputs.get(resource, 0.0) * r
        for s in self.sources:
            if s.resource == resource and s.remaining > 0.0:
                total += s.rate_kgps
        return total

    def _buffer_rates(self, frac: dict[str, float],
                      f_power: float) -> dict[str, float]:
        rates: dict[str, float] = {res: 0.0 for res in self.buffers}
        for m in self.modules:
            f = frac[m.module_id]
            if f <= 0.0:
                continue
            if m.power_kw > 0.0:
                f *= f_power
            r = f * m.rate_kgps
            for res, stoich in m.inputs.items():
                rates[res] = rates.get(res, 0.0) - stoich * r
            for res, stoich in m.outputs.items():
                rates[res] = rates.get(res, 0.0) + stoich * r
        for s in self.sources:
            if s.remaining > 0.0:
                rates[s.resource] = rates.get(s.resource, 0.0) + s.rate_kgps
        return rates

    # -- the advance loop (13 §3.9 algorithm, exact) -----------------------------

    def advance(self, t0: float, t1: float) -> list[LedgerEvent]:
        events: list[LedgerEvent] = []
        t = t0
        guard = 0
        self.roll_failures(t0)
        while t < t1 - _EPS_T:
            guard += 1
            if guard > 10_000:
                events.append(LedgerEvent(t, "ledger_warning", "boundary storm"))
                break
            module_rates, rates, f_power = self.solve_rates()

            # next boundary: buffer hit, deposit exhaustion, or pre-rolled
            # module failure (class-c scheduled boundary)
            t_next = t1
            subject = None
            kind = None
            for m in self.modules:
                if (m.failure_t is not None and m.state == RUNNING
                        and t < m.failure_t < t_next):
                    t_next, kind, subject = m.failure_t, "module_failed", m.module_id
            for (ts, k, sub) in self.scheduled:
                if t < ts < t_next:
                    t_next, kind, subject = ts, k, sub
                    break       # list is sorted; first future wins
            for res, buf in self.buffers.items():
                r = rates.get(res, 0.0)
                if r > _FIXED_POINT_TOL and buf.capacity - buf.level > 1e-9:
                    dt_b = (buf.capacity - buf.level) / r
                    if t + dt_b < t_next:
                        t_next, kind, subject = t + dt_b, "buffer_full", res
                elif r < -_FIXED_POINT_TOL and buf.level > 1e-9:
                    dt_b = buf.level / (-r)
                    if t + dt_b < t_next:
                        t_next, kind, subject = t + dt_b, "buffer_empty", res
            for s in self.sources:
                if s.remaining is not math.inf and s.remaining > 1e-9 and s.rate_kgps > 0.0:
                    dt_s = s.remaining / s.rate_kgps
                    if t + dt_s < t_next:
                        t_next, kind, subject = t + dt_s, "deposit_exhausted", s.source_id

            span = t_next - t
            # exact linear update
            for res, buf in self.buffers.items():
                buf.level += rates.get(res, 0.0) * span
                buf.clamp()
            for s in self.sources:
                if s.remaining is not math.inf and s.remaining > 0.0:
                    s.remaining = max(0.0, s.remaining - abs(s.rate_kgps) * span)

            t = t_next
            if kind is not None and t < t1 + _EPS_T:
                events.append(LedgerEvent(t, kind, subject))
                self._apply_boundary(kind, subject)
                fired = (t, kind, subject)
                if fired in self.scheduled:
                    self.scheduled.remove(fired)      # one-shot consumed
        return events

    def _apply_boundary(self, kind: str, subject: str) -> None:
        """State-machine transitions at boundaries; rates re-solve next loop."""
        if kind == "module_failed":
            for m in self.modules:
                if m.module_id == subject:
                    m.state = FAILED
                    m.failure_t = None
        elif kind in ("module_off", "module_on"):
            for m in self.modules:
                if m.module_id == subject and m.state != FAILED:
                    m.state = OFF if kind == "module_off" else RUNNING
        if kind == "buffer_empty":
            for m in self.modules:
                if m.state == RUNNING and subject in m.inputs:
                    m.state = STARVED
        elif kind == "buffer_full":
            for m in self.modules:
                if m.state == RUNNING and subject in m.outputs:
                    m.state = BLOCKED
        elif kind == "deposit_exhausted":
            pass
        # recovery: STARVED/BLOCKED modules re-check each solve
        for m in self.modules:
            if m.state == STARVED:
                if all(self.buffers.get(r) is None or self.buffers[r].level > 0.0
                       or self._has_live_inflow(r) for r in m.inputs):
                    m.state = RUNNING
            elif m.state == BLOCKED:
                if all(self.buffers.get(r) is None
                       or self.buffers[r].level < self.buffers[r].capacity
                       or self._has_live_drain(r) for r in m.outputs):
                    m.state = RUNNING

    def _has_live_inflow(self, resource: str) -> bool:
        return any(s.resource == resource and s.rate_kgps > 0.0 and s.remaining > 0.0
                   for s in self.sources) or \
            any(resource in m.outputs and m.state == RUNNING for m in self.modules)

    def _has_live_drain(self, resource: str) -> bool:
        return any(s.resource == resource and s.rate_kgps < 0.0
                   for s in self.sources) or \
            any(resource in m.inputs and m.state == RUNNING for m in self.modules)

    def next_boundary_after(self, t: float) -> float:
        """Earliest future boundary (for the global event queue / warp guard)."""
        _, rates, _ = self.solve_rates()
        t_next = math.inf
        for res, buf in self.buffers.items():
            r = rates.get(res, 0.0)
            if r > _FIXED_POINT_TOL and buf.capacity - buf.level > 1e-9:
                t_next = min(t_next, t + (buf.capacity - buf.level) / r)
            elif r < -_FIXED_POINT_TOL and buf.level > 1e-9:
                t_next = min(t_next, t + buf.level / (-r))
        for s in self.sources:
            if s.remaining is not math.inf and s.remaining > 1e-9 and s.rate_kgps > 0.0:
                t_next = min(t_next, t + s.remaining / s.rate_kgps)
        return t_next
