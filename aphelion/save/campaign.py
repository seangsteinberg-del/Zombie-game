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

from aphelion.save.serialize import (
    SCHEMA_VERSION, elements_from_dict, elements_to_dict, ledger_from_dict,
    ledger_to_dict, read_save, write_save,
)
from aphelion.sim.economy import Contract, Program
from aphelion.sim.habitat.dose import CrewDose
from aphelion.sim.research import ResearchState


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


def snapshot_campaign(*, t: float, craft_frame: str, craft_elements,
                      craft_dv: float, craft_name: str, program: Program,
                      research: ResearchState, crew: dict[str, CrewDose],
                      visited: set[str], bases: list,
                      tutorial_done: bool, rng=None) -> dict:
    """bases: objects with .name .last_t .pending_repairs .net (BaseSite)."""
    save = {
        "schema_version": SCHEMA_VERSION,
        "propagator": "patched_conics",
        "t": t,
        "campaign": {
            "craft": {
                "frame_id": craft_frame,
                "elements": elements_to_dict(craft_elements),
                "dv_remaining": craft_dv,
                "name": craft_name,
            },
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
            "tutorial_done": tutorial_done,
            "bases": [{
                "name": b.name,
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


def restore_campaign(save: dict):
    """Returns a plain dict of reconstructed campaign state; the caller
    (main) re-wraps craft/bases in its runtime classes."""
    c = save["campaign"]
    program = Program(funds=c["program"]["funds"])
    program.history = [tuple(h) for h in c["program"]["history"]]
    for cd in c["program"]["contracts"]:
        program.offer(Contract(**cd))
    research = ResearchState(
        science=c["research"]["science"], eng_data=c["research"]["eng_data"],
        unlocked=set(c["research"]["unlocked"]),
        history=[tuple(h) for h in c["research"]["history"]])
    crew = {name: CrewDose(msv) for name, msv in c["crew"].items()}
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
            "pending_repairs": [tuple(r) for r in bd["pending_repairs"]],
            "net": net,
        })
    return {
        "t": save["t"],
        "craft_frame": c["craft"]["frame_id"],
        "craft_elements": elements_from_dict(c["craft"]["elements"]),
        "craft_dv": c["craft"]["dv_remaining"],
        "craft_name": c["craft"]["name"],
        "program": program,
        "research": research,
        "crew": crew,
        "visited": set(c["visited"]),
        "tutorial_done": c["tutorial_done"],
        "bases": bases,
        "rng_state": save.get("rng"),
    }


def write_campaign(path: str | Path, save: dict) -> None:
    write_save(path, save)


def read_campaign(path: str | Path) -> dict:
    return restore_campaign(read_save(path))
