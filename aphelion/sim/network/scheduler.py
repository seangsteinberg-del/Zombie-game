"""Bandwidth buffers & the downlink scheduler (doc 16 §3.2 + §3.6, via
design/extracts/16-comms-buildspec.md).

L-6 recorder ledger: dB/dt = Σ generation − Σ scheduled drain,
piecewise-constant between events (13 §3.9 analytic-ledger contract —
nothing polls); BUFFER_FULL/EMPTY crossings are predicted analytically.
At full the GENERATORS pause (instruments idle): data is never silently
lost — the F-3 flag, enforced by RecorderBuffer.enqueue refusing what
would overflow. L-14 drain: strictly by priority class, oldest queue
timestamp first within a class, uid tie-break — 13's determinism
contract (class, queue timestamp, uid). P0 is never scheduled (the
preemptive command floor); P2 is a live reservation carved off the
window's rate, never buffered; only bulk (P1/P3/P4) lives in the
recorder (L-5). F-10: a deadline the analytic projection through the
known windows cannot meet is flagged Class-3 AT QUEUE TIME, not at the
deadline. §2.5: a DSN lease converts into PASS_START/PASS_END events —
a Window here. L-5: one antenna part = one directed link at a time
(assignment_conflicts); a relay running prox + Earth trunk
simultaneously is legal — two parts."""

from __future__ import annotations

import math
from dataclasses import dataclass

from aphelion.sim.network.graph import (
    BUFFER_ALERT_FRAC, BULK_CLASSES, PRIORITY_CLASSES, deadline_at_risk)

_EPS_BITS = 1e-9


@dataclass(frozen=True)
class Window:
    """One drain opportunity: a scheduled pass (PASS_START/PASS_END) at
    a piecewise-constant path rate, minus any P2 live reservation
    (L-13/L-14: teleop reserves rate during a shift, never buffered)."""
    t0_s: float
    t1_s: float
    rate_bps: float
    p2_reserved_bps: float = 0.0

    @property
    def duration_s(self) -> float:
        return self.t1_s - self.t0_s

    @property
    def bulk_rate_bps(self) -> float:
        """Rate left for buffered bulk after the P2 reservation."""
        return max(0.0, self.rate_bps - self.p2_reserved_bps)

    @property
    def capacity_bits(self) -> float:
        return self.bulk_rate_bps * self.duration_s

    def as_triple(self) -> tuple[float, float, float]:
        return (self.t0_s, self.t1_s, self.bulk_rate_bps)


@dataclass
class Packet:
    """One queued bulk volume (volumes are plain ledger floats, bits).
    deadline_t_s feeds F-10 (e.g. the L-10 failure burst's 30 days)."""
    uid: str
    pclass: str             # P1 | P3 | P4 only (BULK_CLASSES)
    bits: float
    queued_t_s: float
    deadline_t_s: float | None = None
    delivered_bits: float = 0.0
    at_risk: bool = False   # F-10 Class-3 flag, set at queue time

    @property
    def remaining_bits(self) -> float:
        return max(0.0, self.bits - self.delivered_bits)

    @property
    def delivered(self) -> bool:
        return self.remaining_bits <= _EPS_BITS


def drain_key(p: Packet) -> tuple[int, float, str]:
    """13 determinism contract: (class, queue timestamp, uid)."""
    return (PRIORITY_CLASSES[p.pclass]["order"], p.queued_t_s, p.uid)


@dataclass(frozen=True)
class Delivery:
    """bits of one packet moved during [t0_s, t1_s) of a window."""
    packet_uid: str
    pclass: str
    bits: float
    t0_s: float
    t1_s: float


class RecorderBuffer:
    """L-6 recorder ledger over a §2.3 capacity (UT-AV/UT-AVS/DR-1/DR-2
    sum). Fills as instruments generate; refuses overflow so the caller
    pauses the generator — data is never silently lost (F-3)."""

    def __init__(self, cap_bits: float):
        self.cap_bits = float(cap_bits)
        self.packets: list[Packet] = []

    @property
    def used_bits(self) -> float:
        return sum(p.remaining_bits for p in self.packets)

    @property
    def free_bits(self) -> float:
        return max(0.0, self.cap_bits - self.used_bits)

    @property
    def empty(self) -> bool:
        return self.used_bits <= _EPS_BITS

    @property
    def full(self) -> bool:
        return self.free_bits <= _EPS_BITS

    @property
    def generators_paused(self) -> bool:
        """F-3: at BUFFER_FULL generators pause (instruments idle)."""
        return self.full

    @property
    def alert(self) -> bool:
        """§3.7: Class-3 alert at BUFFER ≥ 80%."""
        return self.cap_bits > 0.0 and \
            self.used_bits >= BUFFER_ALERT_FRAC * self.cap_bits

    def enqueue(self, packet: Packet, windows=()) -> bool:
        """Accept a bulk packet if it fits; False = generator pauses
        (the volume stays at the source, never truncated). P0 is
        preemptive and P2 is a live reservation — neither is buffered
        (L-14): enqueueing them is a programming error. With known
        windows and a deadline, runs the F-10 projection AT QUEUE TIME,
        counting everything that drains ahead of this packet."""
        if packet.pclass not in BULK_CLASSES:
            raise ValueError(
                f"{packet.pclass} is never buffered (bulk = {BULK_CLASSES})")
        if packet.bits > self.free_bits + _EPS_BITS:
            return False
        if packet.deadline_t_s is not None and windows:
            ahead = sum(p.remaining_bits for p in self.packets
                        if drain_key(p) < drain_key(packet))
            packet.at_risk = deadline_at_risk(
                packet.bits, packet.deadline_t_s,
                [w.as_triple() for w in windows], ahead)
        self.packets.append(packet)
        return True

    # -- L-6 analytic crossings (nothing polls) --
    def time_to_full(self, gen_bps: float) -> float:
        """Analytic BUFFER_FULL prediction at a net ingest rate."""
        if gen_bps <= 0.0:
            return math.inf
        return self.free_bits / gen_bps

    def time_to_empty(self, drain_bps: float) -> float:
        """Analytic BUFFER_EMPTY prediction at a net drain rate."""
        if drain_bps <= 0.0:
            return math.inf
        return self.used_bits / drain_bps


class DownlinkScheduler:
    """The downlink scheduler: the recorder fills between passes; when
    a window opens it drains strictly by class, oldest-first within a
    class (L-14), at the window's bulk rate (rate minus the P2
    reservation). Emits the §3.1 event rows it owns."""

    def __init__(self, buffer: RecorderBuffer):
        self.buffer = buffer

    def drain(self, window: Window
              ) -> tuple[list[Delivery], list[tuple[str, float]]]:
        """Drain one pass window. Returns (deliveries, events); events
        are (name, t_s) rows for 13's queue: PASS_START/PASS_END always,
        BUFFER_EMPTY at the analytic crossing when the queue runs dry."""
        events: list[tuple[str, float]] = [("PASS_START", window.t0_s)]
        deliveries: list[Delivery] = []
        rate = window.bulk_rate_bps
        was_empty = self.buffer.empty
        t = window.t0_s
        if rate > 0.0:
            for p in sorted(self.buffer.packets, key=drain_key):
                if t >= window.t1_s:
                    break
                if p.delivered:
                    continue
                dt = min(p.remaining_bits / rate, window.t1_s - t)
                bits = dt * rate
                p.delivered_bits = min(p.bits, p.delivered_bits + bits)
                deliveries.append(Delivery(p.uid, p.pclass, bits, t, t + dt))
                t += dt
        self.buffer.packets = [p for p in sorted(self.buffer.packets,
                                                 key=drain_key)
                               if not p.delivered]
        if not was_empty and self.buffer.empty:
            events.append(("BUFFER_EMPTY", t))
        events.append(("PASS_END", window.t1_s))
        return deliveries, events


# ---- analytic projections over pass windows --------------------------------------------
def projected_delivery_t(bits: float, windows) -> float | None:
    """When a volume finishes draining through the known windows
    (sorted by start), or None if they cannot move it — the L-10
    survey-downlink arithmetic and the F-10 projection's inverse."""
    remaining = float(bits)
    for w in sorted(windows, key=lambda w: (w.t0_s, w.t1_s)):
        cap = w.capacity_bits
        if cap <= 0.0:
            continue
        if remaining <= cap + _EPS_BITS:
            return w.t0_s + remaining / w.bulk_rate_bps
        remaining -= cap
    return None


def passes_needed(bits: float, window: Window) -> int:
    """Whole identical passes to move a volume (L-10 worked example:
    500 Gbit at 8 h/day on the leased 34 m at 1.7 AU ≈ 17 days)."""
    return math.ceil(bits / window.capacity_bits)


# ---- L-5 antenna assignment (one directed link at a time per part) ----------------------
@dataclass(frozen=True)
class PassAssignment:
    """The scheduler's claim of one antenna part slot for one peer over
    one window."""
    node_uid: str
    part_slot: int          # index into CommsNode.parts (slots may repeat)
    peer_uid: str
    window: Window


def assignment_conflicts(assignments) -> list[tuple[PassAssignment,
                                                    PassAssignment]]:
    """L-5: one antenna part = one directed link at a time. Two
    assignments conflict iff same (node, part slot) and overlapping
    windows. Multi-antenna nodes run one link per antenna — the relay
    pattern (prox omni + Earth trunk simultaneously) is legal."""
    bad: list[tuple[PassAssignment, PassAssignment]] = []
    rows = sorted(assignments, key=lambda a: (a.node_uid, a.part_slot,
                                              a.window.t0_s, a.peer_uid))
    for i, a in enumerate(rows):
        for b in rows[i + 1:]:
            if (b.node_uid, b.part_slot) != (a.node_uid, a.part_slot):
                break
            if b.window.t0_s < a.window.t1_s:       # overlap
                bad.append((a, b))
    return bad
