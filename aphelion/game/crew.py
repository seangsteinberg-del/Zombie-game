"""Crew as characters (08, game layer): roles, skills, hiring, and real
mechanical effects. Pilots cut prox-ops docking cost, engineers stretch
life-support endurance, scientists multiply exploration science earned
by the vessel they fly on. Dose careers (CrewDose) end careers.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from aphelion.sim.habitat.dose import CrewDose

ROLES = ("pilot", "engineer", "scientist")


@dataclass
class CrewMember:
    name: str
    role: str
    skill: int                      # 1-3
    dose: CrewDose = field(default_factory=CrewDose)

    @property
    def hire_cost(self) -> float:
        return (4.0 + 4.0 * self.skill) * 1e6


# deterministic candidate pool (the 2049 astronaut class; hire in order)
CANDIDATE_POOL: tuple[tuple[str, str, int], ...] = (
    ("M. Reyes", "pilot", 1), ("K. Sato", "scientist", 2),
    ("T. Eze", "engineer", 2), ("L. Marchetti", "pilot", 2),
    ("H. Lindqvist", "scientist", 1), ("D. Okonkwo", "engineer", 1),
    ("A. Sharma", "pilot", 3), ("R. Castellanos", "scientist", 3),
    ("J. Mbeki", "engineer", 3), ("S. Novak", "pilot", 1),
    ("Y. Tanaka", "engineer", 2), ("P. Laurent", "scientist", 2),
    ("N. Petrova", "pilot", 2), ("W. Achebe", "scientist", 1),
    ("F. Gutierrez", "engineer", 1), ("B. Kowalski", "pilot", 3),
    ("E. Nakamura", "scientist", 3), ("G. Diallo", "engineer", 3),
)


def candidates(crew: dict, count: int = 3) -> list[CrewMember]:
    """The next hireable candidates: pool order, minus anyone already on
    the books (or who died there — names retire with their people)."""
    out = []
    for name, role, skill in CANDIDATE_POOL:
        if name not in crew:
            out.append(CrewMember(name, role, skill))
            if len(out) >= count:
                break
    return out


def best_skill(fv, crew: dict, role: str) -> int:
    """Highest skill of the given role aboard a vessel."""
    return max((crew[n].skill for n in fv.crew
                if n in crew and crew[n].role == role), default=0)


def apply_crew_bonuses(fv, crew: dict) -> None:
    """Set a vessel's crew-derived performance attributes (recomputed at
    boarding and on load — never serialized)."""
    fv.prox_ops_dv = max(5.0, 20.0 - 5.0 * best_skill(fv, crew, "pilot"))
    fv.lss_bonus = 1.0 + 0.15 * best_skill(fv, crew, "engineer")


def science_multiplier(fv, crew: dict) -> float:
    return 1.0 + 0.20 * best_skill(fv, crew, "scientist")


def reap_over_limit(crew: dict, vessels: list) -> list[str]:
    """Career dose past the limit ends a career — permanently (08 §3.6).
    Returns the names lost; removes them from the roster and any vessel.
    Europa's 5.4 Sv/day surface makes this arrive in DAYS, not years."""
    lost = [name for name, m in crew.items() if m.dose.over_limit]
    for name in lost:
        del crew[name]
        for v in vessels:
            if name in v.crew:
                v.crew.remove(name)
    return lost
