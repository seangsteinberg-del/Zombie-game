"""THE global event queue (13 §3.8, binding).

One heapq of (t_due, seq, EventRecord). seq is a monotonic tiebreaker giving
total deterministic order. Cancellation is lazy: records carry the generation
of their source at post time; on pop, a record whose source has since bumped
its generation is discarded silently. One generation bump = O(1) invalidation
of every prediction that source ever posted.

Contracts (13 §3.8): predict don't poll; events are exact clamps (the warp
loop never advances past peek_time()); handlers are bounded and may not
advance time.
"""

from __future__ import annotations

import heapq
import math
from dataclasses import dataclass, field
from typing import Any, Hashable


@dataclass(frozen=True, slots=True)
class EventRecord:
    kind: str                       # event-type id per 13 §4.4 catalog
    t_due: float                    # sim seconds from epoch
    source: Hashable | None = None  # generation domain; None = uncancellable
    payload: Any = None


@dataclass(slots=True)
class _Entry:
    t_due: float
    seq: int
    generation: int
    record: EventRecord

    def __lt__(self, other: "_Entry") -> bool:
        return (self.t_due, self.seq) < (other.t_due, other.seq)


class EventQueue:
    def __init__(self) -> None:
        self._heap: list[_Entry] = []
        self._seq = 0
        self._generations: dict[Hashable, int] = {}

    def __len__(self) -> int:
        return len(self._heap)

    def generation(self, source: Hashable) -> int:
        return self._generations.get(source, 0)

    def bump(self, source: Hashable) -> None:
        """Invalidate every event previously posted by this source. O(1)."""
        self._generations[source] = self._generations.get(source, 0) + 1

    def post(self, record: EventRecord) -> None:
        gen = self._generations.get(record.source, 0) if record.source is not None else 0
        entry = _Entry(t_due=record.t_due, seq=self._seq, generation=gen, record=record)
        self._seq += 1
        heapq.heappush(self._heap, entry)

    def _discard_stale(self) -> None:
        while self._heap:
            head = self._heap[0]
            src = head.record.source
            if src is not None and head.generation != self._generations.get(src, 0):
                heapq.heappop(self._heap)
            else:
                return

    def peek_time(self) -> float:
        """Due time of the next live event; +inf when empty. The rails warp
        loop clamps to this every frame (13 §3.5) — nothing is ever missed."""
        self._discard_stale()
        return self._heap[0].t_due if self._heap else math.inf

    def pop_due(self, t: float) -> list[EventRecord]:
        """All live events with t_due <= t, in deterministic (t, seq) order."""
        due: list[EventRecord] = []
        while True:
            self._discard_stale()
            if not self._heap or self._heap[0].t_due > t:
                return due
            due.append(heapq.heappop(self._heap).record)
