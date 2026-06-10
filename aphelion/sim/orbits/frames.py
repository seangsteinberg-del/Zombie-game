"""Body registry and the SOI frame tree (13 §3.7, 01 §3.1).

Every dynamic state is body-centric float64 in its SOI frame; the SOI tree
(Sun -> planets -> moons) is the only path to absolute positions, composed on
demand (at most 3 hops). Bodies are permanently on rails from their epoch
elements; positions are evaluated lazily and memoized per query time
(13 §3.6: every consumer reads the cache, nothing recomputes).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from aphelion.sim.orbits.kepler import Elements, elements_to_state


@dataclass(frozen=True, slots=True)
class Body:
    body_id: str
    mu: float                      # m^3/s^2
    radius: float                  # mean radius, m
    parent: str | None             # None = root (Sun)
    elements: Elements | None      # orbit in parent frame; None for root
    soi_radius: float              # m; math.inf for root; 0.0 = no SOI (floor rule)

    @property
    def has_soi(self) -> bool:
        return self.soi_radius > 0.0


class FrameTree:
    """Registry of bodies + frame composition. Root frame is the body with
    parent=None (exactly one)."""

    def __init__(self) -> None:
        self._bodies: dict[str, Body] = {}
        self._children: dict[str, list[str]] = {}
        self._root: str | None = None
        self._cache_t: float = math.nan
        self._cache: dict[str, tuple[float, float, float, float]] = {}

    def add(self, body: Body) -> None:
        if body.body_id in self._bodies:
            raise ValueError(f"duplicate body {body.body_id!r}")
        if body.parent is None:
            if self._root is not None:
                raise ValueError("frame tree already has a root")
            self._root = body.body_id
        else:
            if body.parent not in self._bodies:
                raise KeyError(f"parent {body.parent!r} not registered before child")
            if body.elements is None:
                raise ValueError(f"non-root body {body.body_id!r} needs elements")
            self._children.setdefault(body.parent, []).append(body.body_id)
        self._bodies[body.body_id] = body

    def body(self, body_id: str) -> Body:
        return self._bodies[body_id]

    @property
    def root(self) -> str:
        if self._root is None:
            raise ValueError("frame tree has no root")
        return self._root

    def children(self, body_id: str) -> list[str]:
        return self._children.get(body_id, [])

    def chain(self, body_id: str) -> list[str]:
        """Frame chain root -> ... -> body_id."""
        chain = [body_id]
        b = self._bodies[body_id]
        while b.parent is not None:
            chain.append(b.parent)
            b = self._bodies[b.parent]
        chain.reverse()
        return chain

    # -- state evaluation ----------------------------------------------------

    def state_in_parent(self, body_id: str, t: float) -> tuple[float, float, float, float]:
        """(rx, ry, vx, vy) of the body in its parent's frame, memoized per t."""
        if t != self._cache_t:
            self._cache_t = t
            self._cache = {}
        cached = self._cache.get(body_id)
        if cached is not None:
            return cached
        body = self._bodies[body_id]
        if body.elements is None:
            state = (0.0, 0.0, 0.0, 0.0)
        else:
            state = elements_to_state(body.elements, t)
        self._cache[body_id] = state
        return state

    def state_in_root(self, body_id: str, t: float) -> tuple[float, float, float, float]:
        rx = ry = vx = vy = 0.0
        for hop in self.chain(body_id):
            hrx, hry, hvx, hvy = self.state_in_parent(hop, t)
            rx += hrx
            ry += hry
            vx += hvx
            vy += hvy
        return (rx, ry, vx, vy)

    # -- SOI transition re-expression (01 §3.4) -------------------------------

    def to_child_frame(self, state: tuple[float, float, float, float],
                       child_id: str, t: float) -> tuple[float, float, float, float]:
        """Re-express a state from the child's parent frame into the child's
        frame (SOI entry: subtract the body's state at the crossing instant)."""
        bx, by, bvx, bvy = self.state_in_parent(child_id, t)
        rx, ry, vx, vy = state
        return (rx - bx, ry - by, vx - bvx, vy - bvy)

    def to_parent_frame(self, state: tuple[float, float, float, float],
                        child_id: str, t: float) -> tuple[float, float, float, float]:
        """Re-express a state from the child's frame into its parent's frame
        (SOI exit: add the body's state)."""
        bx, by, bvx, bvy = self.state_in_parent(child_id, t)
        rx, ry, vx, vy = state
        return (rx + bx, ry + by, vx + bvx, vy + bvy)
