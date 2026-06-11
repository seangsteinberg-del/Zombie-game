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
    Spec("c_base", "Found a lunar surface base", 150.0, 2.5, 1,
         lambda S: _base_at(S, "site:peary")),
    Spec("c_lox", "Bank 100 t of lunar LOX", 200.0, 2.5, 1,
         lambda S: _banked(S, "site:peary", "Oxygen", 100_000.0)),
    # -- Act II: the inner system --------------------------------------------
    Spec("c_helio", "Achieve heliocentric orbit", 120.0, 2.0, 2,
         lambda S: "core:sun" in S["visited"]),
    Spec("c_mars", "Reach the Mars SOI", 300.0, 3.2, 2,
         lambda S: "core:mars" in S["visited"]),
    Spec("c_land_mars", "Land on Mars (Jezero delta)", 350.0, 5.0, 2,
         lambda S: "site:jezero" in S["visited_surface"]),
    Spec("c_base_mars", "Found a Mars surface base", 400.0, 6.0, 2,
         lambda S: _base_at(S, "site:jezero")),
    Spec("c_methalox", "Bank 20 t of martian methane", 300.0, 5.0, 2,
         lambda S: _banked(S, "site:jezero", "Methane", 20_000.0)),
    Spec("c_venus", "Reach the Venus SOI", 250.0, 4.0, 2,
         lambda S: "core:venus" in S["visited"]),
    Spec("c_venus_cloud", "Float in the Venus cloud deck", 450.0, 6.0, 2,
         lambda S: "site:venus_cloud" in S["visited_surface"]),
    # -- Act III: the outer system -------------------------------------------
    Spec("c_jupiter", "Reach the Jupiter SOI", 300.0, 8.0, 3,
         lambda S: "core:jupiter" in S["visited"]),
    Spec("c_europa", "Land on Europa", 400.0, 10.0, 3,
         lambda S: "site:europa_burrow" in S["visited_surface"]),
    Spec("c_saturn", "Reach the Saturn SOI", 300.0, 10.0, 3,
         lambda S: "core:saturn" in S["visited"]),
    Spec("c_titan", "Land on the Ligeia shoreline (Titan)", 450.0, 12.0, 3,
         lambda S: "site:titan_shore" in S["visited_surface"]),
    Spec("c_titan_base", "Found a Titan surface base", 500.0, 10.0, 3,
         lambda S: _base_at(S, "site:titan_shore")),
    # -- Act IV: the way out --------------------------------------------------
    Spec("c_torch", "Research the fusion torch", 400.0, 20.0, 4,
         lambda S: "core:tech_pr22_fusion_torch" in S["research"].unlocked),
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

MAX_RETRIES = 2
RETRY_GRACE_S = 0.5 * YEAR
RETRY_HAIRCUT = 0.6
EARLY_BONUS = 0.25


def act_progress(program: Program) -> str:
    """One-line campaign status for the HUD: where the gate stands."""
    for act in (1, 2, 3):
        if not act_unlocked(act + 1, program):
            done = sum(1 for c in program.contracts
                       if c.completed_t is not None
                       and _ACT_OF.get(c.contract_id) == act)
            need = math.ceil(0.6 * _ACT_TOTALS[act])
            return f"Act {('I', 'II', 'III')[act - 1]} {done}/{need}"
    return "Act IV"


def sweep(program: Program, S: dict, t: float,
          payout_mult: float = 1.0,
          deadline_mult: float = 1.0) -> tuple[list[str], bool]:
    """Offer newly unlocked contracts, complete satisfied ones, RE-OFFER
    blown ones at a haircut (a fail is a setback, never a silent
    soft-lock), and pay an early-delivery bonus. Returns (toast lines,
    won_this_sweep)."""
    toasts: list[str] = []
    won = False
    have = {c.contract_id for c in program.contracts}
    for spec in CONTRACTS:
        if spec.cid not in have and act_unlocked(spec.act, program):
            program.offer(Contract(spec.cid, spec.desc,
                                   payout=spec.payout_m * 1e6 * payout_mult,
                                   deadline_s=t + spec.years * YEAR
                                   * deadline_mult))
            toasts.append(f"NEW CONTRACT (Act {spec.act}): {spec.desc} "
                          f"+${spec.payout_m * payout_mult:,.0f}M")
    for c in program.contracts:
        spec = _BY_ID.get(c.contract_id)
        if spec is None or c.completed_t is not None:
            continue
        window = spec.years * YEAR * deadline_mult
        if c.failed:
            if (c.retries < MAX_RETRIES
                    and t > c.deadline_s + RETRY_GRACE_S):
                c.failed = False
                c.retries += 1
                c.payout *= RETRY_HAIRCUT
                c.deadline_s = t + window
                toasts.append(
                    f"CONTRACT RE-NEGOTIATED at "
                    f"{RETRY_HAIRCUT ** c.retries:.0%}: {spec.desc} "
                    f"+${c.payout / 1e6:,.0f}M")
            continue
        if spec.check(S):
            payout_now = c.payout
            if program.complete(t, c.contract_id):
                line = (f"CONTRACT PAID +${payout_now / 1e6:,.0f}M — "
                        f"{spec.desc}")
                offered_t = c.deadline_s - window
                if t - offered_t < 0.5 * window and c.retries == 0:
                    bonus = EARLY_BONUS * payout_now
                    program.earn(t, bonus, f"early:{spec.cid}")
                    line += f"  EARLY +${bonus / 1e6:,.0f}M"
                toasts.append(line)
                if spec.cid == "c_precursor":
                    won = True
    return toasts, won
