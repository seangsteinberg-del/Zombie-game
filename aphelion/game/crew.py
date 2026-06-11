"""Crew as characters v2 (08 §4): five skill tracks (0–5), morale M,
conditioning C, P_health composition, medical events and the medbay
path, hidden traits, archetype recruitment. Dose careers (CrewDose)
still end careers; now ARS and starvation gate work too.

Back-compat: CrewMember(name, role, skill, dose, busy_until) keeps the
legacy shape — `role` is the primary track, `skill` its level; the
five-track dict derives from the archetype table when not supplied.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field

from aphelion.sim.habitat.dose import CrewDose
from aphelion.sim.habitat.food import BODY_RESERVE_KCAL

ROLES = ("pilot", "engineer", "scientist", "medic", "agronomist")

# archetype secondary-skill template at recruit level 3 (08 §4.10);
# secondaries scale down with the primary level
ARCHETYPES = {
    "pilot":      {"pilot": 3, "engineer": 1, "scientist": 0,
                   "medic": 1, "agronomist": 0},
    "engineer":   {"pilot": 1, "engineer": 3, "scientist": 1,
                   "medic": 0, "agronomist": 0},
    "scientist":  {"pilot": 0, "engineer": 1, "scientist": 3,
                   "medic": 1, "agronomist": 1},
    "medic":      {"pilot": 0, "engineer": 0, "scientist": 1,
                   "medic": 3, "agronomist": 0},
    "agronomist": {"pilot": 0, "engineer": 1, "scientist": 1,
                   "medic": 0, "agronomist": 3},
}

TRAITS = ("resilient", "veteran", "claustrophobic", "iron_gut")

# medical condition table (08 §4.6): productivity penalty (med_penalty,
# max-not-additive), days until fatal untreated (None = chronic), Medic
# level to treat, MedSupplies kg per treatment, recovery days once treated
MED_CONDITIONS = {
    "minor_illness": {"pen": 0.30, "fatal_days": None, "medic": 0,
                      "supplies": 0.5, "recover": 5.0},
    "injury":        {"pen": 0.50, "fatal_days": None, "medic": 1,
                      "supplies": 1.0, "recover": 10.0},
    "dental":        {"pen": 0.30, "fatal_days": None, "medic": 2,
                      "supplies": 0.3, "recover": 4.0},
    "appendicitis":  {"pen": 1.00, "fatal_days": 4.0, "medic": 3,
                      "supplies": 5.0, "recover": 14.0},
    "dcs":           {"pen": 0.50, "fatal_days": 10.0, "medic": 1,
                      "supplies": 1.0, "recover": 7.0},
    "kidney_stone":  {"pen": 0.60, "fatal_days": None, "medic": 1,
                      "supplies": 0.5, "recover": 6.0},
    "psych":         {"pen": 0.50, "fatal_days": None, "medic": 0,
                      "supplies": 0.2, "recover": 14.0},
}

P_MED_BASE_DAY = 0.0008          # ~1 event / 3.4 crew-years
MORALE_TAU_DAYS = 7.0
EVA_MIN_CONDITIONING = 40.0

# conditioning ODE constants (08 §4.3)
K_DECON_DAY = 0.44               # points/day at g=0, no exercise
K_RECOVER_DAY = 0.30             # points/day at full g
G_FULL = 9.81
ARS_PEN = {"prodromal": 0.30, "mild": 0.60, "severe": 1.00,
           "ld50": 1.00, "lethal": 1.00}


def _trait_roll(name: str) -> tuple:
    """Hidden traits, deterministic per name (surface through play)."""
    h = hashlib.blake2b(("trait:" + name).encode(), digest_size=4).digest()
    if h[0] < 90:                # ~35% carry one trait
        return (TRAITS[h[1] % len(TRAITS)],)
    return ()


def derive_skills(role: str, level: int) -> dict[str, int]:
    """Five tracks from the archetype template, primary pinned to level,
    secondaries scaled down for greener recruits."""
    arch = ARCHETYPES.get(role, ARCHETYPES["engineer"])
    out = {}
    for s in ROLES:
        if s == role:
            out[s] = level
        else:
            out[s] = min(arch[s], max(0, level - 1) if level < 3 else arch[s])
    return out


@dataclass
class CrewMember:
    name: str
    role: str                       # primary track
    skill: int                      # primary track level 0-5
    dose: CrewDose = field(default_factory=CrewDose)
    busy_until: float = 0.0         # in training until this sim time
    skills: dict = None             # five tracks; derived if None
    morale: float = 70.0            # M (recruit starts 70)
    cond: float = 100.0             # conditioning C (100 = Earth-fit)
    energy_kcal: float = BODY_RESERVE_KCAL
    traits: tuple = None            # hidden; deterministic per name
    conditions: list = field(default_factory=list)
    xp: dict = field(default_factory=dict)

    TRAIN_COST = 12.0e6
    TRAIN_DAYS = 90.0

    def __post_init__(self) -> None:
        if self.skills is None:
            self.skills = derive_skills(self.role, self.skill)
        if self.traits is None:
            self.traits = _trait_roll(self.name)
            if "veteran" in self.traits and self.dose.accumulated_msv == 0:
                self.dose.accumulated_msv = 100.0   # flown before

    # -- economy ------------------------------------------------------------
    @property
    def hire_cost(self) -> float:
        return (4.0 + 4.0 * self.skill) * 1e6

    def available(self, t: float) -> bool:
        return t >= self.busy_until

    # -- the multiplier stack (08 §4.1) ---------------------------------------
    @property
    def p_morale(self) -> float:
        return 0.5 + 0.5 * (self.morale / 100.0)

    @property
    def phi_err(self) -> float:
        """Human-error multiplier: low morale doubles incident rolls."""
        return 2.0 - self.morale / 100.0

    def med_penalty(self) -> float:
        """Worst active condition (max within category, NOT additive)."""
        pens = [MED_CONDITIONS[c["kind"]]["pen"] for c in self.conditions]
        return max(pens, default=0.0)

    def rad_penalty(self, t: float | None = None) -> float:
        band = self.dose.ars(t)
        return ARS_PEN.get(band[0], 0.0) if band else 0.0

    def starve_penalty(self) -> float:
        frac = max(0.0, self.energy_kcal / BODY_RESERVE_KCAL)
        return 0.0 if frac > 0.5 else 0.7 * (1.0 - frac / 0.5)

    def p_health(self, t: float | None = None) -> float:
        c_fac = min(1.0, max(0.3, self.cond / 100.0))
        return (c_fac * (1.0 - self.med_penalty())
                * (1.0 - self.rad_penalty(t))
                * (1.0 - self.starve_penalty()))

    def task_rate(self, skill: str, t: float | None = None) -> float:
        """rate = (0.5 + 0.25·level) · P_morale · P_health (08 §4.1).
        Level 0 in a required skill halves it further downstream."""
        lvl = self.skills.get(skill, 0)
        return (0.5 + 0.25 * lvl) * self.p_morale * self.p_health(t)

    @property
    def bedridden(self) -> bool:
        return self.med_penalty() >= 1.0 or self.rad_penalty() >= 1.0

    def eva_ok(self) -> bool:
        return self.cond >= EVA_MIN_CONDITIONING and not self.bedridden

    # -- morale (08 §4.4) -------------------------------------------------------
    def step_morale(self, target: float, days: float) -> None:
        tau = MORALE_TAU_DAYS * (2.0 if "resilient" in self.traits else 1.0)
        self.morale += (target - self.morale) / tau * days
        self.morale = min(100.0, max(0.0, self.morale))

    @property
    def crisis(self) -> bool:
        return self.morale <= 20.0

    # -- conditioning (08 §4.3) ----------------------------------------------------
    def step_conditioning(self, g_eff: float, h_ex: float,
                          days: float) -> None:
        if g_eff >= 3.71:               # Mars-g and up: recovery zone
            self.cond += K_RECOVER_DAY * min(1.0, g_eff / G_FULL) \
                * max(0.0, 100.0 - self.cond) / 100.0 * days
            self.cond = min(100.0, self.cond)
            return
        e_ex = min(0.85, 0.42 * h_ex)
        rate = K_DECON_DAY * max(0.0, 1.0 - g_eff / G_FULL) * (1.0 - e_ex)
        if g_eff >= 1.62:               # lunar gravity halves the decay
            rate *= 0.5
        self.cond = max(0.0, self.cond - rate * days)

    def readapt_days(self) -> float:
        return max(0.0, (100.0 - self.cond) / 10.0)

    # -- skill growth (08 §4.1) -------------------------------------------------------
    def accrue_xp(self, skill: str, hours: float, cap: int = 3) -> bool:
        """Slow on-the-job growth; True on a level-up. `cap` is the
        tier-gated ceiling (T0-1→3, T2→4, T3+→5)."""
        lvl = self.skills.get(skill, 0)
        if lvl >= cap:
            return False
        self.xp[skill] = self.xp.get(skill, 0.0) + hours
        if self.xp[skill] >= 400.0 * (lvl + 1):
            self.skills[skill] = lvl + 1
            self.xp[skill] = 0.0
            if skill == self.role:
                self.skill = lvl + 1
            return True
        return False

    # -- medical (08 §4.6) ---------------------------------------------------------------
    def roll_medical(self, rng, *, eva_hours: float = 0.0,
                     crowded: bool = False,
                     medic_aboard: int = 0) -> str | None:
        """One day's medical roll. Returns the condition contracted."""
        p = P_MED_BASE_DAY * self.phi_err
        p *= 1.0 + 0.4 * eva_hours / 8.0
        p *= 1.3 if crowded else 1.0
        p *= 1.5 if self.cond < 40.0 else 1.0
        p *= max(0.6, 1.0 - 0.08 * medic_aboard)     # preventive care
        if rng.random() >= p:
            if self.crisis and rng.random() < 0.01:
                self._add("psych")
                return "psych"
            return None
        r = rng.random()
        if "iron_gut" in self.traits:
            r = min(1.0, r + 0.25)       # illness-resistant
        kind = ("minor_illness" if r < 0.45 else
                "injury" if r < 0.65 else
                "dental" if r < 0.78 else
                "kidney_stone" if r < 0.90 else
                "appendicitis" if r < 0.94 else "minor_illness")
        if kind == "injury" and self.cond >= 40.0 and eva_hours == 0.0 \
                and rng.random() < 0.5:
            kind = "minor_illness"
        self._add(kind)
        return kind

    def _add(self, kind: str) -> None:
        if not any(c["kind"] == kind for c in self.conditions):
            self.conditions.append({"kind": kind, "age": 0.0,
                                    "treated": False})

    def step_medical(self, days: float, medic_level: int,
                     medsupplies_kg: float, rng) -> dict:
        """Advance conditions: treat what the medic + supplies allow,
        recover the treated, escalate the untreated. Returns supplies
        used and whether this member died of something untreated."""
        used = 0.0
        died = None
        for c in list(self.conditions):
            spec = MED_CONDITIONS[c["kind"]]
            c["age"] += days
            if not c["treated"] and medic_level >= spec["medic"] \
                    and medsupplies_kg - used >= spec["supplies"]:
                used += spec["supplies"]
                c["treated"] = True
                c["age"] = 0.0
            if c["treated"]:
                if c["age"] >= spec["recover"]:
                    self.conditions.remove(c)
            elif spec["fatal_days"] is not None \
                    and c["age"] >= spec["fatal_days"]:
                died = c["kind"]
        return {"supplies_used": used, "died_of": died}


# deterministic candidate pool (the 2049 astronaut class; hire in order).
# Surgeons and agronomists join once programs get serious.
CANDIDATE_POOL: tuple[tuple[str, str, int], ...] = (
    ("M. Reyes", "pilot", 1), ("K. Sato", "scientist", 2),
    ("T. Eze", "engineer", 2), ("L. Marchetti", "pilot", 2),
    ("Dr. I. Whitfield", "medic", 3), ("O. Banda", "agronomist", 2),
    ("H. Lindqvist", "scientist", 1), ("D. Okonkwo", "engineer", 1),
    ("A. Sharma", "pilot", 3), ("R. Castellanos", "scientist", 3),
    ("C. Vasquez", "medic", 1), ("M. Haugen", "agronomist", 3),
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


def best_skill(fv, crew: dict, skill: str) -> int:
    """Highest level of the given TRACK aboard a vessel (any role)."""
    return max((crew[n].skills.get(skill, 0) for n in fv.crew
                if n in crew), default=0)


def apply_crew_bonuses(fv, crew: dict) -> None:
    """Set a vessel's crew-derived performance attributes (recomputed at
    boarding and on load — never serialized)."""
    fv.prox_ops_dv = max(5.0, 20.0 - 5.0 * best_skill(fv, crew, "pilot"))
    fv.lss_bonus = 1.0 + 0.15 * best_skill(fv, crew, "engineer")


def science_multiplier(fv, crew: dict) -> float:
    return 1.0 + 0.20 * best_skill(fv, crew, "scientist")


def morale_target(ctx: dict, member: CrewMember | None = None) -> float:
    """M_target = 50 + Σ modifiers (08 §4.4). ctx keys all optional:
    vol_m3 (per crew), private_quarters, fresh_food, ration_days,
    ration_kind, window, plants, light_min (one-way), blackout,
    death_days, near_miss_days, g_eff, overwork_h, fulfilling."""
    s = 50.0
    vol = ctx.get("vol_m3", 25.0)
    claus = member is not None and "claustrophobic" in member.traits
    if vol >= 25.0:
        s += 10.0
    elif vol >= 10.0:
        s += 10.0 * (vol - 10.0) / 15.0
    else:
        s -= 2.0 * (10.0 - vol) * (2.0 if claus else 1.0)
    s += 10.0 if ctx.get("private_quarters") else -5.0
    if ctx.get("fresh_food"):
        s += 12.0
    elif ctx.get("ration_days", 0.0) > 30.0:
        s -= min(15.0, 0.2 * (ctx["ration_days"] - 30.0))
    if ctx.get("ration_kind") == "FD-EMRG":
        s -= 10.0
    if ctx.get("window"):
        s += 6.0
    if ctx.get("plants"):
        s += 4.0
    s -= min(15.0, ctx.get("light_min", 0.0) * 0.5)
    if ctx.get("blackout"):
        s -= 10.0
    dd = ctx.get("death_days")
    if dd is not None and dd <= 30.0:
        s -= 25.0 * (1.0 - dd / 30.0)
    nm = ctx.get("near_miss_days")
    if nm is not None and nm <= 14.0:
        s -= 8.0 * (1.0 - nm / 14.0)
    if ctx.get("g_eff", 9.81) < 1.0:
        s -= 5.0
    if ctx.get("overwork_h", 10.0) > 12.0:
        s -= 5.0
    if ctx.get("fulfilling"):
        s += 5.0
    return s


def reap_over_limit(crew: dict, vessels: list) -> list[str]:
    """Career dose past 600 mSv ends a career — permanently (08 §4.2).
    Returns the names lost; removes them from the roster and any vessel.
    Europa's 5.4 Sv/day surface makes this arrive in HOURS, not years."""
    lost = [name for name, m in crew.items() if m.dose.over_limit]
    for name in lost:
        del crew[name]
        for v in vessels:
            if name in v.crew:
                v.crew.remove(name)
    return lost
