"""Campaign snapshot/restore (13 §3.15): the whole-game save built on the
schema-v1 container. The core encoders stay frozen (golden1.sav remains
valid); everything campaign-level rides in an additive "campaign" section.

Module failure fates (mtbf_s / failure_t) and heat_kw are not part of the
v1 ledger encoder, so bases store them as per-module extras — restoring a
base resumes the SAME pre-rolled failure timeline (warp-invariance across
save/load, 13 §3.9).
"""

from __future__ import annotations

import math
from pathlib import Path

from aphelion.game.fleet import FleetVessel
from aphelion.save.serialize import (
    SCHEMA_VERSION, elements_from_dict, elements_to_dict, ledger_from_dict,
    ledger_to_dict, read_save, vessel_from_dict, vessel_to_dict, write_save,
)
from aphelion.sim.economy import Contract, Program
from aphelion.sim.habitat.dose import CrewDose
from aphelion.sim.research import ResearchState

CAMPAIGN_VERSION = 2        # 2: fleet (real-propellant vessels) replaced
                            # the single dv-scalar craft


def default_save_dir() -> Path:
    d = Path.home() / ".aphelion" / "saves"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _num(x):
    if x is None:
        return None
    return "inf" if x == math.inf else x


def _unnum(x):
    if x is None:
        return None
    return math.inf if x == "inf" else float(x)


def snapshot_campaign(*, t: float, vessels: list[FleetVessel],
                      active_idx: int, next_vid: int, program: Program,
                      research: ResearchState, crew: dict[str, CrewDose],
                      visited: set[str], bases: list,
                      tutorial_done: bool, rng=None,
                      visited_surface: set[str] | None = None) -> dict:
    """bases: objects with .name .last_t .pending_repairs .net (BaseSite)."""
    save = {
        "schema_version": SCHEMA_VERSION,
        "propagator": "patched_conics",
        "t": t,
        "campaign": {
            "version": CAMPAIGN_VERSION,
            "vessels": [{
                "vid": v.vid,
                "name": v.name,
                "frame_id": v.frame_id,
                "elements": elements_to_dict(v.elements),
                "vessel": vessel_to_dict(v.vessel),
                "crew": list(v.crew),
                "landed_at": v.landed_at,
                "lss_used_days": v.lss_used_days,
                "dock_joints": list(v.dock_joints),
            } for v in vessels],
            "active_idx": active_idx,
            "next_vid": next_vid,
            "program": {
                "funds": program.funds,
                "history": [list(h) for h in program.history],
                "contracts": [{
                    "contract_id": c.contract_id, "description": c.description,
                    "payout": c.payout, "deadline_s": c.deadline_s,
                    "completed_t": c.completed_t, "failed": c.failed,
                } for c in program.contracts],
            },
            "research": {
                "science": research.science, "eng_data": research.eng_data,
                "unlocked": sorted(research.unlocked),
                "history": [list(h) for h in research.history],
            },
            "crew": {name: d.accumulated_msv for name, d in crew.items()},
            "visited": sorted(visited),
            "visited_surface": sorted(visited_surface or set()),
            "tutorial_done": tutorial_done,
            "bases": [{
                "name": b.name,
                "site_id": getattr(b, "site_id", "site:peary"),
                "built": list(getattr(b, "built", ["solar_array"])),
                "last_t": b.last_t,
                "pending_repairs": [list(r) for r in b.pending_repairs],
                "ledger": ledger_to_dict(b.net),
                "module_extras": {m.module_id: {
                    "mtbf_s": _num(m.mtbf_s), "failure_t": _num(m.failure_t),
                    "heat_kw": m.heat_kw,
                } for m in b.net.modules},
            } for b in bases],
        },
        "rng": rng.state() if rng else None,
    }
    return save


def restore_campaign(save: dict, db, tree):
    """Returns a plain dict of reconstructed campaign state; the caller
    (main) re-wraps bases in its runtime classes."""
    c = save["campaign"]
    if c.get("version", 1) != CAMPAIGN_VERSION:
        raise ValueError(
            f"save is campaign v{c.get('version', 1)}; this build needs "
            f"v{CAMPAIGN_VERSION} (pre-fleet saves are not migratable)")
    program = Program(funds=c["program"]["funds"])
    program.history = [tuple(h) for h in c["program"]["history"]]
    for cd in c["program"]["contracts"]:
        program.offer(Contract(**cd))
    research = ResearchState(
        science=c["research"]["science"], eng_data=c["research"]["eng_data"],
        unlocked=set(c["research"]["unlocked"]),
        history=[tuple(h) for h in c["research"]["history"]])
    crew = {name: CrewDose(msv) for name, msv in c["crew"].items()}
    vessels = []
    for vd in c["vessels"]:
        fv = FleetVessel(tree, vd["frame_id"],
                         elements_from_dict(vd["elements"]),
                         vessel_from_dict(vd["vessel"], db),
                         vd["name"], vd["vid"], crew=vd["crew"],
                         t_now=save["t"])
        fv.landed_at = vd["landed_at"]
        fv.lss_used_days = vd["lss_used_days"]
        fv.dock_joints = list(vd.get("dock_joints", []))
        vessels.append(fv)
    bases = []
    for bd in c["bases"]:
        net = ledger_from_dict(bd["ledger"])
        for m in net.modules:
            extra = bd["module_extras"].get(m.module_id)
            if extra:
                m.mtbf_s = _unnum(extra["mtbf_s"])
                m.failure_t = _unnum(extra["failure_t"])
                m.heat_kw = extra["heat_kw"]
        bases.append({
            "name": bd["name"], "last_t": bd["last_t"],
            "site_id": bd.get("site_id", "site:peary"),
            "built": bd.get("built", ["solar_array"]),
            "pending_repairs": [tuple(r) for r in bd["pending_repairs"]],
            "net": net,
        })
    return {
        "t": save["t"],
        "vessels": vessels,
        "active_idx": c["active_idx"],
        "next_vid": c["next_vid"],
        "program": program,
        "research": research,
        "crew": crew,
        "visited": set(c["visited"]),
        "visited_surface": set(c.get("visited_surface", [])),
        "tutorial_done": c["tutorial_done"],
        "bases": bases,
        "rng_state": save.get("rng"),
    }


def write_campaign(path: str | Path, save: dict) -> None:
    write_save(path, save)


def read_campaign(path: str | Path, db, tree) -> dict:
    return restore_campaign(read_save(path), db, tree)
