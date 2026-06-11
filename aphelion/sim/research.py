"""Research system (11, full build): Science is a global spendable scalar;
Engineering Data is a per-family cumulative high-water mark — checked
against node thresholds, never spent (11 §3.5). Adds the fog of research,
OR-prereq grammar, Discoveries with discounts, sample pools with
diminishing returns, milestone lumps, and the prototyping/maturation
stack (m_state / m_unit / m(D_f)) that the one-wear-model ruling
(DECISIONS A5) composes with 02's wear terms.

Formula IDs cited inline refer to design/extracts/11-research-buildspec.md.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from aphelion.content.loader import ContentDB

# ---------------------------------------------------------------------------
# canon tables

# The 22 part families (11 §3.5, F-15 donor audit).
FAMILIES: tuple[str, ...] = (
    "SolidMotors", "StorableEngines", "KeroloxEngines", "HydroloxEngines",
    "MethaloxEngines", "NTRCores", "EPThrusters", "CryoFluidMgmt",
    "SolarPower", "EnergyStorage", "FissionSystems", "ThermalControl",
    "ECLSS-PhysChem", "ECLSS-Bio", "PressureStructures", "ISRU-Chem",
    "MiningMachines", "FabricationMachines", "RoboticsAutonomy",
    "SurfaceMobility", "AeroFlight", "Avionics",
)

D_HALF: dict[str, float] = {
    "Avionics": 100.0,
    "SolidMotors": 150.0, "StorableEngines": 150.0, "SurfaceMobility": 150.0,
    "PressureStructures": 150.0, "SolarPower": 150.0, "EnergyStorage": 150.0,
    "KeroloxEngines": 200.0, "HydroloxEngines": 200.0,
    "MethaloxEngines": 200.0, "MiningMachines": 200.0, "ThermalControl": 200.0,
    "EPThrusters": 250.0, "CryoFluidMgmt": 250.0, "ECLSS-PhysChem": 250.0,
    "FabricationMachines": 250.0,
    "NTRCores": 300.0, "ISRU-Chem": 300.0, "RoboticsAutonomy": 300.0,
    "AeroFlight": 300.0,
    "FissionSystems": 400.0, "ECLSS-Bio": 400.0,
}

ENGINE_FAMILIES = ("SolidMotors", "StorableEngines", "KeroloxEngines",
                   "HydroloxEngines", "MethaloxEngines", "NTRCores")

# Continuous accrual (ED/h) per family class (11 §3.5 rate table).
RATE_HOURLY: dict[str, float] = {
    "EPThrusters": 0.04,
    "CryoFluidMgmt": 0.05, "SolarPower": 0.05, "EnergyStorage": 0.05,
    "FissionSystems": 0.05, "ThermalControl": 0.05, "ECLSS-PhysChem": 0.05,
    "ECLSS-Bio": 0.05, "ISRU-Chem": 0.05, "MiningMachines": 0.05,
    "FabricationMachines": 0.05,
    "PressureStructures": 0.01,        # while crewed and pressurized
    "RoboticsAutonomy": 0.03,          # while active (+1 per task order)
    "SurfaceMobility": 0.02,           # powered (+0.5 per km driven)
}

# Seven environment classes (03 tags; M_env ×3 for the first 200 h).
ENV_CLASSES: tuple[str, ...] = (
    "leo_microgravity", "deep_space", "vacuum_dusty_surface", "cryo_surface",
    "dense_atmosphere", "high_radiation", "liquid_immersion",
)
NOVEL_HOURS = 200.0
NOVEL_MULT = 3.0

# Milestones ("firsts", 11 §3.4): lump = k · X(body surface class).
MILESTONE_K: dict[str, float] = {
    "flyby": 10.0, "orbit": 20.0, "landing": 40.0, "sample_return": 60.0,
    "crewed_landing": 80.0, "crewed_30d": 100.0,
}

# Exoticism X (11 §3.2) by body id — region-level X lands with chunk S;
# body-level is the milestone/survey fallback.
BODY_X: dict[str, float] = {
    "core:earth": 1.0, "core:moon": 2.0, "core:mars": 5.0,
    "core:phobos": 5.0, "core:deimos": 5.0, "core:venus": 8.0,
    "core:mercury": 6.0, "core:ceres": 6.0, "core:vesta": 6.0,
    "core:psyche": 6.0, "core:hygiea": 6.0, "core:bennu": 4.0,
    "core:ryugu": 4.0, "core:itokawa": 4.0, "core:eros": 4.0,
    "core:apophis": 4.0, "core:halley": 7.0, "core:67p": 7.0,
    "core:jupiter": 9.0, "core:io": 10.0, "core:europa": 10.0,
    "core:ganymede": 8.0, "core:callisto": 8.0,
    "core:saturn": 10.0, "core:titan": 11.0, "core:enceladus": 12.0,
    "core:uranus": 10.0, "core:miranda": 10.0, "core:titania": 10.0,
    "core:oberon": 10.0, "core:neptune": 11.0, "core:triton": 11.0,
    "core:pluto": 12.0, "core:charon": 12.0, "core:eris": 13.0,
    "core:arrokoth": 12.0, "core:sun": 1.0,
}

# Sample activities (11 §3.3): type -> (V_base SCI, mass kg, needs_cryo)
SAMPLE_TYPES: dict[str, tuple[float, float, bool]] = {
    "atmosphere_grab": (25.0, 0.2, False),
    "regolith_scoop": (40.0, 0.5, False),
    "drill_core": (60.0, 2.0, False),
    "ice_core": (90.0, 5.0, True),
    "deep_core": (140.0, 25.0, False),
    "liquid_grab": (120.0, 1.0, True),
    "plume_capture": (70.0, 0.05, False),
}

# Analysis paths: M_analysis multipliers (11 §3.3).
ANALYSIS_PATHS: dict[str, float] = {
    "insitu": 0.40, "glovebox": 0.55, "field_lab": 0.70,
    "orbital_lab": 0.90, "earth_lab": 1.25,
}

# Maturity perks (11 §4.2).
BADGE_MATURE = 600.0
BADGE_REFINED = 2_000.0
BADGE_OPTIMIZED = 5_000.0

# Legacy 13-node pack -> canonical ids (save migration; F-12 stable ids).
LEGACY_TECH_MAP: dict[str, str] = {
    "core:tech_cryo_depots": "core:tech_pr04_cryo_fluid_mgmt",
    "core:tech_fission_100kwe": "core:tech_pw05_fission_surface",
    "core:tech_ntr": "core:tech_pr09_ntr",
    "core:tech_isru_large": "core:tech_is05_polar_ice_mining",
    "core:tech_closed_loop_eclss": "core:tech_ls07_closed_loop_eclss",
    "core:tech_wafer_fab": "core:tech_in11_wafer_fab",
    "core:tech_autonomous_factories": "core:tech_in10_autonomous_factory",
    "core:tech_aerostat_ops": "core:tech_hb05_venus_aerostat_hab",
    "core:tech_titan_ops": "core:tech_hb07_titan_outpost",
    "core:tech_transit_habs": "core:tech_sh02_inflatable_modules",
    "core:tech_deep_habs": "core:tech_hb06_spin_centrifuge",
    "core:tech_fusion_torch": "core:tech_pr22_fusion_torch",
    "core:tech_precursor": "core:tech_sh09_interstellar_precursor",
}

# Existing content -> ED family bridges (replaced by full catalogs later).
MODULE_FAMILY: dict[str, str | None] = {
    "drill_ice": "MiningMachines", "electrolyzer": "ISRU-Chem",
    "sabatier": "ISRU-Chem", "co2_intake": "ISRU-Chem",
    "lake_pump": "MiningMachines", "solar_array": "SolarPower",
    "reactor_100": "FissionSystems", "battery_pack": "EnergyStorage",
    "radiator_wing": "ThermalControl", "science_lab": None,
    "hab_module": "PressureStructures", "tank_farm": "CryoFluidMgmt",
}

_ENGINE_PART_FAMILY = {
    "k845": "KeroloxEngines", "kv981": "KeroloxEngines",
    "h102": "HydroloxEngines", "h2280": "HydroloxEngines",
    "hl67": "HydroloxEngines",
    "m2256": "MethaloxEngines", "m733": "MethaloxEngines",
    "ml111": "MethaloxEngines", "ml24": "MethaloxEngines",
    "mv2530": "MethaloxEngines", "mv815": "MethaloxEngines",
    "oms27": "StorableEngines", "sps91": "StorableEngines",
    "lnd71": "StorableEngines",
    "ntr_k2": "NTRCores", "torch_d1": "FissionSystems",
}


def engine_family(part_id: str) -> str:
    """Map an engine part id (core:engine_xxx) to its ED family."""
    tail = part_id.rsplit(":", 1)[-1]
    if tail.startswith("engine_"):
        tail = tail[len("engine_"):]
    return _ENGINE_PART_FAMILY.get(tail, "StorableEngines")


def maturity(d_f: float, family: str) -> float:
    """m(D_f) = 1 + 3·2^(−D_f/D_half): 4 (new) -> 1 (mature)."""
    return 1.0 + 3.0 * 2.0 ** (-d_f / D_HALF[family])


def m_unit(hours: float, ignitions: int) -> float:
    """Per-unit infant mortality: ×2.5 first 50 h / 3 ignitions (11 §4.2)."""
    return 2.5 if (hours < 50.0 and ignitions < 3) else 1.0


def badge(d_f: float) -> str | None:
    if d_f >= BADGE_OPTIMIZED:
        return "OPTIMIZED"
    if d_f >= BADGE_REFINED:
        return "REFINED"
    if d_f >= BADGE_MATURE:
        return "MATURE"
    return None


def sample_award(activity: str, x: float, n: int) -> float:
    """S_n = 0.6 · 0.4^(n−1) · V_base·X — the nth draw from one pool."""
    v_base = SAMPLE_TYPES[activity][0]
    return 0.6 * (0.4 ** (n - 1)) * v_base * x


def cryo_decay(days_above_150k: float) -> float:
    """F-4: linear decay floored at 20% (mineralogy survives)."""
    return max(0.2, 1.0 - 0.02 * days_above_150k)


def _prereq_groups(node: dict) -> list[list[str]]:
    """Normalize the prereq grammar: each entry is an AND term; a list entry
    is an OR group (any one suffices). Returns a list of OR-groups."""
    out: list[list[str]] = []
    for p in node.get("prereqs", []):
        out.append(list(p) if isinstance(p, list) else [p])
    return out


def flat_prereqs(node: dict) -> set[str]:
    return {nid for grp in _prereq_groups(node) for nid in grp}


@dataclass(slots=True)
class ResearchState:
    science: float = 0.0
    # per-family cumulative ED high-water mark — checked, never spent
    ed: dict[str, float] = field(default_factory=dict)
    # novel-environment hours used, keyed "family|env_class"
    ed_novel: dict[str, float] = field(default_factory=dict)
    unlocked: set[str] = field(default_factory=set)
    discoveries: set[str] = field(default_factory=set)
    # staged-discovery tranches paid, dsc_id -> count (of 3)
    tranches: dict[str, int] = field(default_factory=dict)
    # sample pools: "activity|region" -> draws analyzed so far
    pools: dict[str, int] = field(default_factory=dict)
    milestones: set[str] = field(default_factory=set)
    # part-type prototype states: type id -> True once full-duration success
    type_proven: set[str] = field(default_factory=set)
    # part types ever built (anything built but unproven is PROTOTYPE)
    type_built: set[str] = field(default_factory=set)
    # avionics per-vessel SOI-leg ED (capped at 10, reset on SOI change)
    avionics_leg: dict[str, float] = field(default_factory=dict)
    history: list[tuple[float, str]] = field(default_factory=list)

    def bootstrap(self, db: ContentDB) -> None:
        """T0 nodes are start-unlocked (11 §1.2): cost 0, no prereqs."""
        for nid, node in db.tech.items():
            if node["tier"] == "T0":
                self.unlocked.add(nid)

    # -- science ------------------------------------------------------------
    def earn_science(self, points: float) -> None:
        self.science += points

    def earn_eng_data(self, points: float, family: str | None = None) -> None:
        """Direct family credit. family=None credits every family (test/
        legacy shim — production callers always name a family)."""
        for f in ([family] if family else FAMILIES):
            self.ed[f] = self.ed.get(f, 0.0) + points

    def d_f(self, family: str) -> float:
        return self.ed.get(family, 0.0)

    # -- ED accrual (11 §3.5) -------------------------------------------------
    def _novel_mult(self, family: str, env_class: str, hours: float) -> float:
        """Average multiplier over `hours`, consuming the 200 h ×3 window."""
        key = f"{family}|{env_class}"
        used = self.ed_novel.get(key, 0.0)
        if used >= NOVEL_HOURS or hours <= 0.0:
            return 1.0
        boosted = min(hours, NOVEL_HOURS - used)
        self.ed_novel[key] = used + boosted
        return (boosted * NOVEL_MULT + (hours - boosted)) / hours

    def ed_cap(self, db: ContentDB, family: str) -> float:
        """C_f = max(1.5·max visible threshold naming f, 6·D_half) (F-7)."""
        best = 0.0
        for nid, node in db.tech.items():
            if not self.visible(db, nid):
                continue
            for th in node.get("ed_thresholds", []):
                if th["family"] == family:
                    best = max(best, float(th["value"]))
        return max(1.5 * best, 6.0 * D_HALF[family])

    def _credit(self, db: ContentDB | None, family: str, amount: float) -> float:
        cur = self.ed.get(family, 0.0)
        cap = self.ed_cap(db, family) if db is not None else float("inf")
        new = min(cap, cur + amount)
        self.ed[family] = max(cur, new)
        return self.ed[family] - cur

    def accrue_hours(self, db: ContentDB | None, family: str, hours: float,
                     *, n_units: int = 1, env_class: str = "leo_microgravity",
                     duty: float = 1.0) -> float:
        """Continuous accrual: dD = R_f · √N · M_env · hours (√N damping)."""
        rate = RATE_HOURLY.get(family, 0.0)
        if rate <= 0.0 or hours <= 0.0 or n_units < 1:
            return 0.0
        if family not in ("PressureStructures", "RoboticsAutonomy",
                          "SurfaceMobility", "EPThrusters"):
            rate = rate if duty >= 0.5 else rate * duty
        mult = self._novel_mult(family, env_class, hours)
        return self._credit(db, family, rate * math.sqrt(n_units) * mult * hours)

    def accrue_ignition(self, db: ContentDB | None, family: str,
                        burn_s: float = 0.0, *,
                        env_class: str = "leo_microgravity",
                        unit_rank: int = 1) -> float:
        """Engines: 5 ED per successful ignition + 0.05 ED/s of burn."""
        amount = 5.0 + 0.05 * burn_s
        if unit_rank >= 5:
            amount *= 0.5
        key = f"{family}|{env_class}"
        if self.ed_novel.get(key, 0.0) < NOVEL_HOURS:
            amount *= NOVEL_MULT
        return self._credit(db, family, amount)

    def accrue_event(self, db: ContentDB | None, family: str, kind: str, *,
                     env_class: str = "leo_microgravity",
                     unit_rank: int = 1, vessel_id: str | None = None) -> float:
        """Event accrual: aero_event 25 · robot_task 1 · failure_investigated
        +25 (machines) / +40 (engines) · teardown handled by caller."""
        if kind == "aero_event":
            amount = 25.0
        elif kind == "robot_task":
            amount = 1.0
        elif kind == "failure_investigated":
            amount = 40.0 if family in ENGINE_FAMILIES else 25.0
        elif kind == "program_exec":            # Avionics, 2 ED, 10/leg cap
            vid = vessel_id or "_"
            used = self.avionics_leg.get(vid, 0.0)
            amount = min(2.0, 10.0 - used)
            if amount <= 0.0:
                return 0.0
            self.avionics_leg[vid] = used + amount
        else:
            raise ValueError(f"unknown ED event kind {kind!r}")
        if kind != "program_exec":
            if unit_rank >= 5:
                amount *= 0.5
            key = f"{family}|{env_class}"
            if self.ed_novel.get(key, 0.0) < NOVEL_HOURS:
                amount *= NOVEL_MULT
        return self._credit(db, family, amount)

    def reset_avionics_leg(self, vessel_id: str) -> None:
        self.avionics_leg.pop(vessel_id, None)

    # -- visibility (fog of research, 11 §1.5) --------------------------------
    def visible(self, db: ContentDB, node_id: str) -> bool:
        node = db.tech.get(node_id)
        if node is None:
            return False
        tier = node["tier"]
        if tier in ("T0", "T1"):
            return True
        if node_id in self.unlocked:
            return True
        # gating discovery acquired reveals the node
        for d in node.get("discovery_prereqs", []):
            if d in self.discoveries:
                return True
        # T4 extra gate: a researched T3 node in the same category
        if tier == "T4":
            cat = node.get("category")
            if not any(db.tech[u].get("category") == cat
                       and db.tech[u]["tier"] == "T3"
                       for u in self.unlocked if u in db.tech):
                return False
        # distance 1 in the prereq graph: a researched prereq or dependent
        if any(p in self.unlocked for p in flat_prereqs(node)):
            return True
        for other_id in self.unlocked:
            other = db.tech.get(other_id)
            if other and node_id in flat_prereqs(other):
                return True
        return False

    # -- unlocking ------------------------------------------------------------
    def discounted_cost(self, db: ContentDB, node_id: str) -> float:
        """F-13: multiplicative Discovery discounts, floor 0.4·base."""
        node = db.tech[node_id]
        base = float(node.get("cost_sci", 0.0))
        cost = base
        dscs = db.by_type("discoveries")
        for did in self.discoveries:
            for d in dscs.get(did, {}).get("discounts", []):
                if d["node"] == node_id:
                    cost *= 1.0 - float(d["frac"])
        return max(0.4 * base, cost)

    def missing_ed(self, db: ContentDB, node_id: str) -> list[tuple[str, float, float]]:
        """[(family, have, need)] for unmet thresholds."""
        out = []
        for th in db.tech[node_id].get("ed_thresholds", []):
            fam, need = th["family"], float(th["value"])
            have = self.ed.get(fam, 0.0)
            if have < need:
                out.append((fam, have, need))
        return out

    def can_unlock(self, db: ContentDB, node_id: str) -> bool:
        node = db.tech.get(node_id)
        if node is None or node_id in self.unlocked:
            return False
        if not self.visible(db, node_id):
            return False
        for grp in _prereq_groups(node):
            if not any(p in self.unlocked for p in grp):
                return False
        for d in node.get("discovery_prereqs", []):
            if d not in self.discoveries:
                return False
        if self.missing_ed(db, node_id):
            return False
        return self.science >= self.discounted_cost(db, node_id)

    def unlock(self, db: ContentDB, node_id: str, t: float = 0.0) -> bool:
        if not self.can_unlock(db, node_id):
            return False
        self.science -= self.discounted_cost(db, node_id)
        self.unlocked.add(node_id)
        self.history.append((t, node_id))
        return True

    # -- discoveries -----------------------------------------------------------
    def acquire_discovery(self, db: ContentDB, dsc_id: str,
                          t: float = 0.0) -> float:
        """First tranche (or full lump). Returns SCI awarded."""
        if dsc_id in self.discoveries:
            return 0.0
        d = db.by_type("discoveries").get(dsc_id)
        if d is None:
            return 0.0
        self.discoveries.add(dsc_id)
        self.history.append((t, dsc_id))
        if d.get("staged", False):
            self.tranches[dsc_id] = 1
            award = 0.4 * float(d["sci"])
        else:
            award = float(d["sci"])
        self.science += award
        return award

    def discovery_tranche(self, db: ContentDB, dsc_id: str,
                          organics_bonus: bool = False) -> float:
        """Pay the next 30% tranche of a staged discovery (11 §5): tranche 2
        on SC-07 analysis, tranche 3 on Earth-return verdict. ×1.5 with the
        astrobiology suite (tranches 2-3 only)."""
        d = db.by_type("discoveries").get(dsc_id)
        if d is None or not d.get("staged", False):
            return 0.0
        paid = self.tranches.get(dsc_id, 0)
        if dsc_id not in self.discoveries or paid >= 3:
            return 0.0
        award = 0.3 * float(d["sci"]) * (1.5 if organics_bonus else 1.0)
        self.tranches[dsc_id] = paid + 1
        self.science += award
        return award

    # -- milestones & samples ----------------------------------------------------
    def award_milestone(self, kind: str, body_id: str, t: float = 0.0) -> float:
        key = f"{kind}|{body_id}"
        if key in self.milestones or kind not in MILESTONE_K:
            return 0.0
        self.milestones.add(key)
        award = MILESTONE_K[kind] * BODY_X.get(body_id, 3.0)
        self.science += award
        self.history.append((t, key))
        return award

    def analyze_sample(self, activity: str, region: str, x: float,
                       path: str, days_above_150k: float = 0.0,
                       organics_bonus: bool = False) -> float:
        """Pool draw at ANALYSIS time (F-3: loss refunds by never drawing).
        Returns SCI credited."""
        key = f"{activity}|{region}"
        n = self.pools.get(key, 0) + 1
        s_n = sample_award(activity, x, n)
        mult = ANALYSIS_PATHS[path] * (1.1 if organics_bonus else 1.0)
        award = s_n * mult
        if SAMPLE_TYPES[activity][2]:
            award *= cryo_decay(days_above_150k)
        self.pools[key] = n
        self.science += award
        return award

    # -- prototyping (11 §4.1) ----------------------------------------------------
    def type_state(self, part_type: str) -> str:
        if part_type in self.type_proven:
            return "FLIGHT"
        if part_type in self.type_built:
            return "PROTOTYPE"
        return "NEW"

    def m_state(self, part_type: str) -> float:
        return 1.0 if part_type in self.type_proven else 4.0

    def record_build(self, part_type: str) -> float:
        """Returns the build-cost multiplier: ×3 first article, ×1.5 for
        parallel prototypes, ×1 after the type is proven (F-6)."""
        if part_type in self.type_proven:
            return 1.0
        first = part_type not in self.type_built
        self.type_built.add(part_type)
        return 3.0 if first else 1.5

    def record_full_duration_success(self, part_type: str) -> None:
        self.type_built.add(part_type)
        self.type_proven.add(part_type)

    def live_failure_multiplier(self, family: str, part_type: str,
                                unit_hours: float = 1e9,
                                unit_ignitions: int = 99) -> float:
        """m(D_f)·m_state·m_unit — multiplies 02/05 catalog floors (A5)."""
        return (maturity(self.ed.get(family, 0.0), family)
                * self.m_state(part_type)
                * m_unit(unit_hours, unit_ignitions))

    # -- availability -----------------------------------------------------------
    def part_available(self, db: ContentDB, part_id: str) -> bool:
        """A part is available iff some unlocked node lists it, or no node
        gates it at all (T0 base set)."""
        gated = False
        for node_id, node in db.tech.items():
            if part_id in node.get("unlocks", []):
                gated = True
                if node_id in self.unlocked:
                    return True
        return not gated
