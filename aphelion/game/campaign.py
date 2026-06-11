"""The campaign arc (12 §3, Acts I–IV): a declarative contract table
swept against REAL game state every frame. Acts unlock as the previous
act is substantially complete (≥60%); deadlines start when a contract is
OFFERED, not at campaign start. The final contract is the win condition:
an interstellar precursor on a hyperbolic solar orbit.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Callable

from aphelion.sim.economy import Contract, Program

YEAR = 365.0 * 86_400.0


@dataclass(frozen=True)
class Spec:
    cid: str
    desc: str
    payout_m: float
    years: float
    act: int
    check: Callable[[dict], bool]


def _base_at(S: dict, site_id: str) -> bool:
    return any(getattr(b, "site_id", None) == site_id for b in S["bases"])


def _banked(S: dict, site_id: str, resource: str, kg: float) -> bool:
    return any(getattr(b, "site_id", None) == site_id
               and b.net.buffers.get(resource) is not None
               and b.net.buffers[resource].level >= kg
               for b in S["bases"])


def _carrying_precursor_hyperbolic(S: dict) -> bool:
    for v in S["vessels"]:
        if (v.frame_id == "core:sun" and v.landed_at is None
                and v.elements.alpha < 0.0
                and any(r.part_id == "core:probe_longshot"
                        for r in v.vessel.rows)):
            return True
    return False


CONTRACTS: tuple[Spec, ...] = (
    # -- Act I: LEO and Luna --------------------------------------------------
    Spec("c_orbit", "Put a vessel in orbit", 100.0, 0.5, 1,
         lambda S: "orbited" in S["milestones"]),
    Spec("c_crewed", "Crewed vessel in orbit", 60.0, 1.0, 1,
         lambda S: any(v.crew and v.landed_at is None
                       for v in S["vessels"])),
    Spec("c_moon", "Reach the Moon's SOI", 80.0, 1.0, 1,
         lambda S: "core:moon" in S["visited"]),
    Spec("c_land_moon", "Land on the Moon", 120.0, 2.0, 1,
         lambda S: "site:peary" in S["visited_surface"]),
    Spec("c_station", "Dock two vessels together", 90.0, 2.0, 1,
         lambda S: "docked" in S["milestones"]),
    Spec("c_base", "Found a lunar surface base", 150.0, 3.0, 1,
         lambda S: _base_at(S, "site:peary")),
    Spec("c_lox", "Bank 100 t of lunar LOX", 200.0, 4.0, 1,
         lambda S: _banked(S, "site:peary", "Oxygen", 100_000.0)),
    # -- Act II: the inner system --------------------------------------------
    Spec("c_helio", "Achieve heliocentric orbit", 120.0, 2.0, 2,
         lambda S: "core:sun" in S["visited"]),
    Spec("c_mars", "Reach the Mars SOI", 300.0, 4.0, 2,
         lambda S: "core:mars" in S["visited"]),
    Spec("c_land_mars", "Land on Mars (Jezero delta)", 350.0, 5.0, 2,
         lambda S: "site:jezero" in S["visited_surface"]),
    Spec("c_base_mars", "Found a Mars surface base", 400.0, 6.0, 2,
         lambda S: _base_at(S, "site:jezero")),
    Spec("c_methalox", "Bank 20 t of martian methane", 300.0, 7.0, 2,
         lambda S: _banked(S, "site:jezero", "Methane", 20_000.0)),
    Spec("c_venus", "Reach the Venus SOI", 250.0, 4.0, 2,
         lambda S: "core:venus" in S["visited"]),
    Spec("c_venus_cloud", "Float in the Venus cloud deck", 450.0, 6.0, 2,
         lambda S: "site:venus_cloud" in S["visited_surface"]),
    # -- Act III: the outer system -------------------------------------------
    Spec("c_jupiter", "Reach the Jupiter SOI", 500.0, 8.0, 3,
         lambda S: "core:jupiter" in S["visited"]),
    Spec("c_europa", "Land on Europa", 600.0, 10.0, 3,
         lambda S: "site:europa_burrow" in S["visited_surface"]),
    Spec("c_saturn", "Reach the Saturn SOI", 500.0, 10.0, 3,
         lambda S: "core:saturn" in S["visited"]),
    Spec("c_titan", "Land on the Ligeia shoreline (Titan)", 650.0, 12.0, 3,
         lambda S: "site:titan_shore" in S["visited_surface"]),
    Spec("c_titan_base", "Found a Titan surface base", 700.0, 14.0, 3,
         lambda S: _base_at(S, "site:titan_shore")),
    # -- Act IV: the way out --------------------------------------------------
    Spec("c_torch", "Research the fusion torch", 800.0, 20.0, 4,
         lambda S: "core:tech_fusion_torch" in S["research"].unlocked),
    Spec("c_precursor", "LAUNCH THE INTERSTELLAR PRECURSOR", 2_000.0, 30.0, 4,
         _carrying_precursor_hyperbolic),
)

_ACT_TOTALS = {a: sum(1 for s in CONTRACTS if s.act == a) for a in (1, 2, 3, 4)}


def act_unlocked(act: int, program: Program) -> bool:
    if act <= 1:
        return True
    done_prev = sum(1 for c in program.contracts
                    if c.completed_t is not None
                    and _ACT_OF.get(c.contract_id) == act - 1)
    return done_prev >= math.ceil(0.6 * _ACT_TOTALS[act - 1])


_ACT_OF = {s.cid: s.act for s in CONTRACTS}
_BY_ID = {s.cid: s for s in CONTRACTS}


def sweep(program: Program, S: dict, t: float) -> tuple[list[str], bool]:
    """Offer newly unlocked contracts, complete satisfied ones. Returns
    (toast lines, won_this_sweep)."""
    toasts: list[str] = []
    won = False
    have = {c.contract_id for c in program.contracts}
    for spec in CONTRACTS:
        if spec.cid not in have and act_unlocked(spec.act, program):
            program.offer(Contract(spec.cid, spec.desc,
                                   payout=spec.payout_m * 1e6,
                                   deadline_s=t + spec.years * YEAR))
            toasts.append(f"NEW CONTRACT (Act {spec.act}): {spec.desc} "
                          f"+${spec.payout_m:,.0f}M")
    for c in program.contracts:
        if c.completed_t is not None or c.failed:
            continue
        spec = _BY_ID.get(c.contract_id)
        if spec is None:
            continue
        if spec.check(S) and program.complete(t, c.contract_id):
            toasts.append(f"CONTRACT PAID +${spec.payout_m:,.0f}M — "
                          f"{spec.desc}")
            if spec.cid == "c_precursor":
                won = True
    return toasts, won
