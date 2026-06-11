"""Content pack discovery and loading (13 §3.4, binding).

Packs are directories under data/; load order is core first, then mods
alphabetically. TOML (tomllib) for hand-authored content, JSON for bulk;
both normalize to the same dicts. Ids are "<pack>:<name>". A later pack may
add new ids or patch existing ones (shallow key override) only with an
explicit "patch": true flag — silent collisions are a load error.
"""

from __future__ import annotations

import json
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from aphelion.content.schema import TYPE_SCHEMAS


class ContentError(Exception):
    """Load/validation failure: file, key, expected/got. Fatal at launch."""


@dataclass(slots=True)
class ContentDB:
    """All loaded content, by type then id."""
    items: dict[str, dict[str, dict]] = field(default_factory=dict)
    sources: dict[str, str] = field(default_factory=dict)   # id -> file path

    def by_type(self, type_name: str) -> dict[str, dict]:
        return self.items.get(type_name, {})

    @property
    def bodies(self) -> dict[str, dict]:
        return self.by_type("bodies")

    @property
    def parts(self) -> dict[str, dict]:
        return self.by_type("parts")

    @property
    def recipes(self) -> dict[str, dict]:
        return self.by_type("recipes")

    @property
    def tech(self) -> dict[str, dict]:
        return self.by_type("tech")


def _read_file(path: Path) -> dict:
    if path.suffix == ".toml":
        with open(path, "rb") as fh:
            return tomllib.load(fh)
    if path.suffix == ".json":
        with open(path, "rb") as fh:
            return json.load(fh)
    raise ContentError(f"{path}: unsupported content extension {path.suffix!r}")


def _pack_order(data_dir: Path) -> list[Path]:
    packs = sorted(p for p in data_dir.iterdir() if p.is_dir())
    core = [p for p in packs if p.name == "core"]
    mods = [p for p in packs if p.name != "core"]
    return core + mods


def load_packs(data_dir: str | Path) -> ContentDB:
    data_dir = Path(data_dir)
    if not data_dir.is_dir():
        raise ContentError(f"data directory not found: {data_dir}")
    db = ContentDB()
    for pack in _pack_order(data_dir):
        for type_name in TYPE_SCHEMAS:
            type_dir = pack / type_name
            if not type_dir.is_dir():
                continue
            store = db.items.setdefault(type_name, {})
            for path in sorted(type_dir.iterdir()):
                if path.suffix not in (".toml", ".json"):
                    continue
                raw = _read_file(path)
                item_id = raw.get("id")
                if not isinstance(item_id, str):
                    raise ContentError(f"{path}: missing string 'id'")
                # New ids must carry their pack's prefix; PATCHES legitimately
                # reference foreign ids (a mod patching core content).
                expected_prefix = pack.name + ":"
                if not raw.get("patch", False) and not item_id.startswith(expected_prefix):
                    raise ContentError(
                        f"{path}: id {item_id!r} must start with {expected_prefix!r}")
                if item_id in store:
                    if not raw.get("patch", False):
                        raise ContentError(
                            f"{path}: id {item_id!r} collides with "
                            f"{db.sources[item_id]} and has no 'patch': true flag")
                    merged = dict(store[item_id])
                    for k, v in raw.items():
                        if k != "patch":
                            merged[k] = v
                    store[item_id] = merged
                else:
                    if raw.get("patch", False):
                        raise ContentError(
                            f"{path}: id {item_id!r} is flagged patch but "
                            f"nothing with that id was loaded before it")
                    store[item_id] = raw
                db.sources[item_id] = str(path)
    return db


def default_data_dir() -> Path:
    """data/ at the repo root (sibling of the aphelion package)."""
    return Path(__file__).resolve().parent.parent.parent / "data"
