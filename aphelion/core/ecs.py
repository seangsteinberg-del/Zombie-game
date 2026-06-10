"""ECS-lite (13 §3.3, binding): entities are opaque int64 ids; components are
frozen dataclasses in per-type dict stores; systems are plain functions run in
a fixed explicit order. No archetypes, no query DSL.

Aggregation rule: parts are NOT entities — a vessel is one entity whose parts
are rows inside its Vessel component. Campaign-wide entity budget ~2,000.

Determinism: id 0 is reserved/invalid; ids are never reused (monotonic
counter, serialized); iteration is insertion-ordered (CPython dict guarantee)
— fixed order is a 13 §3.10 requirement.
"""

from __future__ import annotations

from typing import Iterator, Type, TypeVar

EntityId = int
C = TypeVar("C")


class ComponentStore(dict[EntityId, C]):
    """dict[EntityId, Component] with insertion-ordered, deterministic
    iteration. Plain dict semantics are the API — systems iterate directly."""


class EntityRegistry:
    def __init__(self, next_id: int = 1) -> None:
        if next_id < 1:
            raise ValueError("entity ids start at 1; 0 is reserved/invalid")
        self._next_id = next_id
        self._stores: dict[type, ComponentStore] = {}
        self._alive: set[EntityId] = set()

    @property
    def next_id(self) -> int:
        """Serialized into saves so ids are never reused within a campaign."""
        return self._next_id

    def new_entity(self) -> EntityId:
        eid = self._next_id
        self._next_id += 1
        self._alive.add(eid)
        return eid

    def is_alive(self, eid: EntityId) -> bool:
        return eid in self._alive

    def add(self, eid: EntityId, component: object) -> None:
        if eid not in self._alive:
            raise KeyError(f"entity {eid} is not alive")
        self.store(type(component))[eid] = component

    def get(self, eid: EntityId, ctype: Type[C]) -> C | None:
        return self._stores.get(ctype, {}).get(eid)

    def remove(self, eid: EntityId, ctype: type) -> None:
        self._stores.get(ctype, ComponentStore()).pop(eid, None)

    def destroy(self, eid: EntityId) -> None:
        self._alive.discard(eid)
        for store in self._stores.values():
            store.pop(eid, None)

    def store(self, ctype: Type[C]) -> ComponentStore[C]:
        store = self._stores.get(ctype)
        if store is None:
            store = ComponentStore()
            self._stores[ctype] = store
        return store

    def entities_with(self, *ctypes: type) -> Iterator[EntityId]:
        """Entities holding all of the given component types, in the first
        store's insertion order (deterministic)."""
        if not ctypes:
            return iter(())
        first = self.store(ctypes[0])
        rest = [self.store(t) for t in ctypes[1:]]
        return (eid for eid in first if all(eid in s for s in rest))
