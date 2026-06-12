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

from aphelion.game.crew import CrewMember
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
                      visited_surface: set[str] | None = None,
                      milestones: set[str] | None = None,
                      builder_stack: list | None = None,
                      difficulty: str = "DIRECTOR",
                      tutorial_state: dict | None = None,
                      explore: dict | None = None,
                      yard_designs: list | None = None) -> dict:
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
                "dock_joint_ports": list(getattr(v, "dock_joint_ports", [])),
                "port_repair_h": getattr(v, "port_repair_h", 0.0),
                "spin_rpm": getattr(v, "spin_rpm", 0.0),
                "spin_r_m": getattr(v, "spin_r_m", 25.0),
                "cargo": dict(getattr(v, "cargo", {}) or {}),
                "yard_job": getattr(v, "yard_job", None),
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
                "science": research.science,
                "ed": dict(research.ed),
                "ed_novel": dict(research.ed_novel),
                "unlocked": sorted(research.unlocked),
                "discoveries": sorted(research.discoveries),
                "tranches": dict(research.tranches),
                "pools": dict(research.pools),
                "sci_milestones": sorted(research.milestones),
                "surveys": sorted(research.surveys),
                "type_proven": sorted(research.type_proven),
                "type_built": sorted(research.type_built),
                "history": [list(h) for h in research.history],
            },
            "crew": {name: {"msv": m.dose.accumulated_msv, "role": m.role,
                            "skill": m.skill,
                            "acute": [list(p) for p in m.dose.acute_log],
                            "busy": getattr(m, "busy_until", 0.0),
                            "skills": dict(getattr(m, "skills", {}) or {}),
                            "morale": getattr(m, "morale", 70.0),
                            "cond": getattr(m, "cond", 100.0),
                            "energy": getattr(m, "energy_kcal", 90_000.0),
                            "traits": list(getattr(m, "traits", ()) or ()),
                            "conditions": [dict(c) for c in
                                           getattr(m, "conditions", [])],
                            "xp": dict(getattr(m, "xp", {}) or {})}
                     for name, m in crew.items()},
            "difficulty": difficulty,
            "tutorial_state": tutorial_state,
            "explore": explore or {},
            "visited": sorted(visited),
            "visited_surface": sorted(visited_surface or set()),
            "milestones": sorted(milestones or set()),
            "tutorial_done": tutorial_done,
            "builder_stack": [list(s) for s in (builder_stack or [])],
            "yard_designs": list(yard_designs or []),
            "bases": [{
                "name": b.name,
                "site_id": getattr(b, "site_id", "site:peary"),
                "built": list(getattr(b, "built", ["solar_array"])),
                "crew": list(getattr(b, "crew", [])),
                "last_t": b.last_t,
                "pending_repairs": [list(r) for r in b.pending_repairs],
                "pending_commission": [list(c) for c in
                                       getattr(b, "pending_commission", [])],
                "ledger": ledger_to_dict(b.net),
                "module_extras": {m.module_id: {
                    "mtbf_s": _num(m.mtbf_s), "failure_t": _num(m.failure_t),
                    "heat_kw": m.heat_kw,
                    "cond": getattr(b, "cond", {}).get(m.module_id, 1.0),
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
    r = c["research"]
    if "ed" in r:
        research = ResearchState(
            science=r["science"], ed=dict(r["ed"]),
            ed_novel=dict(r.get("ed_novel", {})),
            unlocked=set(r["unlocked"]),
            discoveries=set(r.get("discoveries", [])),
            tranches=dict(r.get("tranches", {})),
            pools=dict(r.get("pools", {})),
            milestones=set(r.get("sci_milestones", [])),
            surveys=set(r.get("surveys", [])),
            type_proven=set(r.get("type_proven", [])),
            type_built=set(r.get("type_built", [])),
            history=[tuple(h) for h in r["history"]])
    else:
        # legacy scalar-ED save: migrate ids via LEGACY_TECH_MAP and seed
        # every family at the old scalar (generous, but old values were small)
        from aphelion.sim.research import FAMILIES, LEGACY_TECH_MAP
        research = ResearchState(
            science=r["science"],
            ed={f: float(r.get("eng_data", 0.0)) for f in FAMILIES},
            unlocked={LEGACY_TECH_MAP.get(u, u) for u in r["unlocked"]},
            history=[tuple(h) for h in r["history"]])
    research.bootstrap(db)      # T0 start nodes are always unlocked
    crew = {}
    for name, cd in c["crew"].items():
        if isinstance(cd, dict):
            crew[name] = CrewMember(
                name, cd["role"], cd["skill"],
                CrewDose(cd["msv"], cd.get("acute", [])),
                busy_until=cd.get("busy", 0.0),
                skills=dict(cd["skills"]) if cd.get("skills") else None,
                morale=cd.get("morale", 70.0),
                cond=cd.get("cond", 100.0),
                energy_kcal=cd.get("energy", 90_000.0),
                traits=(tuple(cd["traits"])
                        if cd.get("traits") is not None else None),
                conditions=[dict(c) for c in cd.get("conditions", [])],
                xp=dict(cd.get("xp", {})))
        else:                       # early-v2 shape: bare msv float
            crew[name] = CrewMember(name, "pilot", 1, CrewDose(cd))
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
        # pre-port saves: grandfather old joints as fluid-capable L berths
        fv.dock_joint_ports = list(
            vd.get("dock_joint_ports", ["L"] * len(fv.dock_joints)))
        fv.port_repair_h = vd.get("port_repair_h", 0.0)
        fv.spin_rpm = vd.get("spin_rpm", 0.0)
        fv.spin_r_m = vd.get("spin_r_m", 25.0)
        fv.cargo = dict(vd.get("cargo", {}))
        fv.yard_job = vd.get("yard_job")
        vessels.append(fv)
    bases = []
    for bd in c["bases"]:
        net = ledger_from_dict(bd["ledger"])
        cond = {}
        for m in net.modules:
            extra = bd["module_extras"].get(m.module_id)
            if extra:
                m.mtbf_s = _unnum(extra["mtbf_s"])
                m.failure_t = _unnum(extra["failure_t"])
                m.heat_kw = extra["heat_kw"]
                cond[m.module_id] = extra.get("cond", 1.0)
        bases.append({
            "name": bd["name"], "last_t": bd["last_t"],
            "site_id": bd.get("site_id", "site:peary"),
            "built": bd.get("built", ["solar_array"]),
            "crew": bd.get("crew", []),
            "pending_repairs": [tuple(r) for r in bd["pending_repairs"]],
            "pending_commission": [tuple(c) for c in
                                   bd.get("pending_commission", [])],
            "cond": cond,
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
        "milestones": set(c.get("milestones", [])),
        "tutorial_done": c["tutorial_done"],
        "builder_stack": c.get("builder_stack", []),
        "yard_designs": c.get("yard_designs", []),
        "difficulty": c.get("difficulty", "DIRECTOR"),
        "tutorial_state": c.get("tutorial_state"),
        "explore": c.get("explore", {}),
        "bases": bases,
        "rng_state": save.get("rng"),
    }


def write_campaign(path: str | Path, save: dict) -> None:
    write_save(path, save)


def read_campaign(path: str | Path, db, tree) -> dict:
    return restore_campaign(read_save(path), db, tree)
