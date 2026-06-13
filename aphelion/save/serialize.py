"""Save system v1 (13 §3.15): versioned schema, JSON + zlib, state
snapshots (never input replays). Serialization is "walk the component
state and emit fields" — symmetric, schema-versionable, no pickle magic.

SCHEMA_VERSION history:
  1 — Phase 2: elements, vessels, ledger networks, rng registry, sim time.
      One reserved field: propagator="patched_conics" (DECISIONS G35e —
      headroom for a future n-body "Principia mode" swap).
"""

from __future__ import annotations

import json
import math
import os
import zlib
from pathlib import Path

from aphelion.core.rng import RngRegistry
from aphelion.sim.ledger.network import Buffer, LedgerNetwork, Module, Source
from aphelion.sim.orbits.kepler import Elements
from aphelion.sim.vessels.vessel import PartRow, Vessel

SCHEMA_VERSION = 1


# -- per-type encoders (plain dicts, round-trip exact via repr floats) --------

def elements_to_dict(el: Elements) -> dict:
    return {"mu": el.mu, "alpha": el.alpha, "e": el.e, "varpi": el.varpi,
            "tau": el.tau, "s": el.s}


def elements_from_dict(d: dict) -> Elements:
    return Elements(mu=d["mu"], alpha=d["alpha"], e=d["e"], varpi=d["varpi"],
                    tau=d["tau"], s=d["s"])


def vessel_to_dict(v: Vessel) -> dict:
    return {
        "rows": [{"part_id": r.part_id, "fill": dict(r.fill),
                  "condition": r.condition,
                  "attach": [list(a) for a in r.attach]} for r in v.rows],
        "stage_plan": [list(s) for s in v.stage_plan],
        "cd_a_m2": v.cd_a_m2,
    }


def vessel_from_dict(d: dict, db) -> Vessel:
    rows = [PartRow(part_id=r["part_id"], fill=dict(r["fill"]),
                    condition=r["condition"],
                    attach=[tuple(a) for a in r["attach"]])
            for r in d["rows"]]
    return Vessel(db, rows, stage_plan=[list(s) for s in d["stage_plan"]],
                  cd_a_m2=d["cd_a_m2"])


def ledger_to_dict(net: LedgerNetwork) -> dict:
    def num(x: float):
        return "inf" if x == math.inf else x

    return {
        "buffers": {res: {"level": b.level, "capacity": num(b.capacity)}
                    for res, b in net.buffers.items()},
        "modules": [{
            "module_id": m.module_id, "inputs": dict(m.inputs),
            "outputs": dict(m.outputs), "rate_kgps": m.rate_kgps,
            "power_kw": m.power_kw, "state": m.state,
            "f_condition": m.f_condition, "f_labor": m.f_labor,
            "yield_y": m.yield_y} for m in net.modules],
        "sources": [{
            "source_id": s.source_id, "resource": s.resource,
            "rate_kgps": s.rate_kgps, "remaining": num(s.remaining)}
            for s in net.sources],
    }


def ledger_from_dict(d: dict) -> LedgerNetwork:
    def num(x):
        return math.inf if x == "inf" else float(x)

    net = LedgerNetwork()
    for res, b in d["buffers"].items():
        net.buffers[res] = Buffer(level=float(b["level"]),
                                  capacity=num(b["capacity"]))
    for m in d["modules"]:
        net.add_module(Module(
            module_id=m["module_id"], inputs=dict(m["inputs"]),
            outputs=dict(m["outputs"]), rate_kgps=m["rate_kgps"],
            power_kw=m["power_kw"], state=m["state"],
            f_condition=m["f_condition"], f_labor=m["f_labor"],
            yield_y=m["yield_y"]))
    for s in d["sources"]:
        net.add_source(Source(
            source_id=s["source_id"], resource=s["resource"],
            rate_kgps=s["rate_kgps"], remaining=num(s["remaining"])))
    return net


# -- the save container -------------------------------------------------------

def build_save(*, t: float, vessels: dict[str, Vessel] | None = None,
               orbits: dict[str, Elements] | None = None,
               ledgers: dict[str, LedgerNetwork] | None = None,
               rng: RngRegistry | None = None) -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "propagator": "patched_conics",          # reserved (G35e)
        "t": t,
        "vessels": {k: vessel_to_dict(v) for k, v in (vessels or {}).items()},
        "orbits": {k: elements_to_dict(e) for k, e in (orbits or {}).items()},
        "ledgers": {k: ledger_to_dict(n) for k, n in (ledgers or {}).items()},
        "rng": rng.state() if rng else None,
    }


def write_save(path: str | Path, save: dict) -> None:
    # atomic: serialize to a temp file in the same directory, then
    # os.replace it into place — a crash mid-write leaves the previous
    # save intact instead of truncating it (Z hardening, 13 §3.15).
    raw = json.dumps(save, separators=(",", ":"), sort_keys=True).encode("utf-8")
    path = Path(path)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_bytes(zlib.compress(raw, level=6))
    os.replace(tmp, path)


def read_save(path: str | Path) -> dict:
    raw = zlib.decompress(Path(path).read_bytes())
    save = json.loads(raw)
    version = save.get("schema_version")
    if version != SCHEMA_VERSION:
        raise ValueError(
            f"save schema {version} unsupported (engine is {SCHEMA_VERSION}; "
            f"migrations arrive with schema 2)")
    return save
