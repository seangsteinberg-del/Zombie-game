"""Seeded substream registry (13 §3.10, binding).

Campaign seed (uint64, shown to the player) -> named independent PCG64
substreams per domain and entity: rng("failures", module_uid),
rng("terrain", body, sector, slot), ... Burning randomness in one stream
never shifts outcomes in another; stream states serialize into saves.

Python's built-in hash() is forbidden in sim/ (per-process salting breaks
determinism); key->seed derivation here uses blake2b.
"""

from __future__ import annotations

import hashlib
from typing import Hashable

import numpy as np


def _stable_key_hash(key: tuple[Hashable, ...]) -> int:
    """Stable uint64 from a key tuple. Components must be str/int/bytes —
    anything else would smuggle repr()-instability into the derivation."""
    h = hashlib.blake2b(digest_size=8)
    for part in key:
        if isinstance(part, bytes):
            h.update(b"b" + part)
        elif isinstance(part, str):
            h.update(b"s" + part.encode("utf-8"))
        elif isinstance(part, (int, np.integer)):
            h.update(b"i" + int(part).to_bytes(16, "little", signed=True))
        else:
            raise TypeError(f"rng key component must be str/int/bytes, got {type(part)!r}")
        h.update(b"\x00")
    return int.from_bytes(h.digest(), "little")


class RngRegistry:
    def __init__(self, campaign_seed: int) -> None:
        self.campaign_seed = int(campaign_seed) & 0xFFFF_FFFF_FFFF_FFFF
        self._streams: dict[tuple[Hashable, ...], np.random.Generator] = {}

    def stream(self, *key: Hashable) -> np.random.Generator:
        """The named substream for this key, created deterministically on
        first use. rng.stream("failures", 42) is the same stream object for
        the lifetime of the registry."""
        if not key:
            raise ValueError("rng stream key must be non-empty")
        k = tuple(key)
        gen = self._streams.get(k)
        if gen is None:
            ss = np.random.SeedSequence(
                entropy=self.campaign_seed, spawn_key=(_stable_key_hash(k),))
            gen = np.random.Generator(np.random.PCG64(ss))
            self._streams[k] = gen
        return gen

    # -- save support (13 §3.15: stream states serialize) -------------------

    def state(self) -> dict:
        return {
            "campaign_seed": self.campaign_seed,
            "streams": [
                {"key": list(k), "state": g.bit_generator.state}
                for k, g in sorted(self._streams.items(), key=lambda kv: repr(kv[0]))
            ],
        }

    @classmethod
    def from_state(cls, state: dict) -> "RngRegistry":
        reg = cls(state["campaign_seed"])
        for item in state["streams"]:
            key = tuple(item["key"])
            gen = reg.stream(*key)
            gen.bit_generator.state = item["state"]
        return reg
