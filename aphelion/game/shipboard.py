"""Shipboard life — the LIVING INTERIORS simulation behind the walkable
aboard scene (08 §4.3 conditioning, §4.4 morale, §4.5 daily schedule,
§3.2 caloric ledger; 12 §3.5 alert classes). Stations are real places
with capacity; crew run a real day (staggered sleep shifts, 2.5 h of
exercise in free fall, shared meals drawn from the galley's actual kcal
stores); needs integrate continuously and push the EXISTING CrewMember
fields (morale, cond, energy_kcal, xp, conditions) — none of this is
flavor text. No exercise rack aboard at 0 g? Conditioning really decays
and the deconditioning caution really fires.

Renderer/orchestrator contract
------------------------------
- ``Shipboard.stations`` lists every interactive station with its strip
  position in metres: the airlock occupies room 0 and module ``i``
  spans ``[(i+1)*12, (i+2)*12)`` m, matching interior_art.ROOM_M.
- ``whereabouts(name)`` gives the scene each crew's current x, target
  station, ETA, and a pose key ("sleep_bag" / "exercise" / "seated" /
  "stand") for interior_art.crew_at_station. The sim moves the
  positions; the scene just draws them.
- ``verb(...)`` returns wire-friendly effects, e.g. ``("repair",
  module_id, amount)`` for main to apply to a module's cond, or
  ``("science", points)`` for the research ledger.
- ``step(t, dt, context)`` returns event dicts ({t, kind, who, text,
  class, chronicle}) ready for the alert bus / Chronicle.

Determinism: every roll derives from zlib.crc32 of a stable key (never
Python hash()); state is a plain JSON-safe dict (to_dict/from_dict).
"""

from __future__ import annotations

import math
import zlib

from aphelion.sim.habitat.food import (BODY_RESERVE_KCAL, KCAL_BASE_DAY,
                                       KCAL_PER_KG_DRY)

HOUR_S = 3_600.0
DAY_S = 86_400.0
ROOM_M = 12.0                    # keep in sync with interior_art.ROOM_M
WALK_MPS = 0.9                   # crew translation speed along the strip
SLICE_S = 900.0                  # internal integration slice (15 min)
MEAL_KCAL = KCAL_BASE_DAY / 3.0  # one scheduled meal (~833 kcal)
COOK_KCAL_EACH = 300.0           # a proper cooked meal, extra per diner
SLEEP_NEED_H_DAY = 8.0           # 08 §4.5 sleep block
G_FREEFALL = 1.0                 # below this: microgravity rules
G_MARS = 3.71                    # at/above: no exercise prescription

# station catalog: type -> (default capacity, player verbs)
STATION_TYPES: dict[str, dict] = {
    "galley":        {"cap": 3, "verbs": ("cook",)},
    "bunk":          {"cap": 4, "verbs": ()},
    "exercise":      {"cap": 2, "verbs": ("work_out",)},
    "science_bench": {"cap": 2, "verbs": ("research",)},
    "med_bay":       {"cap": 2, "verbs": ("scan",)},
    "comms_desk":    {"cap": 1, "verbs": ()},
    "cupola":        {"cap": 2, "verbs": ("gaze",)},
    "maint_panel":   {"cap": 1, "verbs": ("repair",)},
    "hygiene":       {"cap": 1, "verbs": ("wash",)},
}

# module kind -> ((station type, module-local x m, capacity), ...);
# x anchors sit by the drawn fixtures in interior_art's set dressing
_HAB = (("bunk", 2.8, 4), ("galley", 5.0, 3), ("hygiene", 10.2, 1))
MODULE_STATIONS: dict[str, tuple] = {
    "flight_deck":  (("comms_desk", 3.2, 1), ("cupola", 8.6, 2)),
    "hab_module":   _HAB, "hab_rigid": _HAB, "hab_inflatable": _HAB,
    "regolith_vault": _HAB, "basalt_hab": _HAB,
    "med_bay":      (("med_bay", 3.0, 2), ("hygiene", 9.6, 1)),
    "greenhouse":   (("maint_panel", 2.2, 1), ("science_bench", 8.0, 2)),
    "bio_farm":     (("maint_panel", 2.2, 1), ("science_bench", 8.0, 2)),
    "machine_shop": (("maint_panel", 2.4, 1), ("exercise", 7.6, 2)),
    "science_lab":  (("science_bench", 3.4, 2), ("comms_desk", 9.4, 1)),
}

# role -> preferred work station type (08 §4.1 skill tracks)
WORK_STATION = {"pilot": "comms_desk", "engineer": "maint_panel",
                "scientist": "science_bench", "medic": "med_bay",
                "agronomist": "science_bench"}
# station type -> the skill its work-hours train
STATION_SKILL = {"science_bench": "scientist", "maint_panel": "engineer",
                 "med_bay": "medic", "comms_desk": "pilot"}
POSES = {"sleep": "sleep_bag", "exercise": "exercise", "meal": "seated",
         "work": "seated", "hygiene": "stand", "free": "stand"}

VERB_COOLDOWN_H = {"cook": 6.0, "scan": 12.0, "repair": 4.0,
                   "research": 6.0, "gaze": 2.0, "wash": 1.0,
                   "work_out": 3.0}

# alert thresholds (rising-edge events; clear at 80% of the threshold)
EXHAUSTED_H = 10.0               # sleep debt
DECON_DEBT_H = 5.0               # exercise debt at 0 g
FILTHY_D = 3.0                   # days unwashed
STARVING_FRAC = 0.35             # of the 90,000 kcal body reserve


def _roll(key: str) -> float:
    """Deterministic [0,1) from a stable string key (NEVER hash())."""
    return (zlib.crc32(key.encode()) & 0xFFFFFFFF) / 4294967296.0


def exercise_need_h(spin_g: float) -> float:
    """Prescribed exercise h/day: 2.5 in free fall, 1.0 in partial g,
    0 at/above Mars gravity (08 §4.3/§4.5)."""
    if spin_g < G_FREEFALL:
        return 2.5
    if spin_g < G_MARS:
        return 1.0
    return 0.0


def _norm_modules(modules_summary) -> list[list]:
    """Accept ["hab_module", ...], [(kind, id), ...] or [{kind,id}]."""
    out = []
    for i, m in enumerate(modules_summary):
        if isinstance(m, str):
            out.append([m, f"{m}-{i}"])
        elif isinstance(m, dict):
            out.append([m["kind"], m.get("id", f"{m['kind']}-{i}")])
        else:
            out.append([m[0], m[1]])
    return out


def _fresh_needs() -> dict:
    return {"sleep_debt_h": 0.0, "ex_debt_h": 0.0, "ex_rate_h": 2.0,
            "hygiene_d": 0.0, "social": 0.2, "last_meal_h": 4.0,
            "flags": {}}


class Shipboard:
    """One pressurized stack's interior life. ``crew_dict`` is the LIVE
    name -> CrewMember roster aboard (effects mutate those objects);
    ``spin_g`` is m/s² of artificial/surface gravity (0 = free fall)."""

    def __init__(self, modules_summary, crew_dict: dict, spin_g: float = 0.0,
                 t0: float = 0.0, stores: dict | None = None) -> None:
        self.modules = _norm_modules(modules_summary)
        self.crew = crew_dict
        self.spin_g = float(spin_g)
        self.t = float(t0)
        self.day = int(t0 // DAY_S)
        self.seed = zlib.crc32(
            ("|".join(mid for _, mid in self.modules)).encode())
        self.stores = dict(stores) if stores else {
            "food_kg": 60.0, "medsupplies_kg": 6.0, "samples": 0.0}
        self.needs: dict[str, dict] = {}
        self.crew_x: dict[str, float] = {}
        self.cooldowns: dict[str, float] = {}    # "sid|verb" -> ready t
        self.overrides: dict[str, list] = {}
        self.arguments: list[dict] = []          # active crew arguments
        self.birthdays_today: list[str] = []
        self.celebrated: list[str] = []
        self.pending_nightmare: list[str] = []
        self.injured_today: list[str] = []
        self.cupola_uses = 0
        self.kcal_served = 0.0                   # store -> crew, cumulative
        self.kcal_burned = 0.0                   # crew metabolic, cumulative
        self._stations = self._build_stations()
        self._by_type: dict[str, list] = {}
        for st in self._stations:
            self._by_type.setdefault(st["type"], []).append(st)
        self._occ: dict[str, list] = {st["id"]: [] for st in self._stations}
        self._asg: dict[str, tuple] = {}
        self._attn: dict[str, bool] = {}
        self._ship_flags: dict[str, bool] = {}
        for name in self.crew:
            self._enroll(name)

    # -- stations ---------------------------------------------------------
    def _build_stations(self) -> list[dict]:
        out, counts = [], {}
        for i, (kind, mid) in enumerate(self.modules):
            for st_type, x_m, cap in MODULE_STATIONS.get(kind, ()):
                n = counts.get(st_type, 0)
                counts[st_type] = n + 1
                out.append({"id": f"{st_type}.{n}", "type": st_type,
                            "module_index": i, "module_id": mid,
                            "module_kind": kind, "x_m": x_m,
                            "strip_x_m": (i + 1) * ROOM_M + x_m,
                            "capacity": cap,
                            "verbs": list(STATION_TYPES[st_type]["verbs"])})
        return out

    @property
    def stations(self) -> list[dict]:
        """Snapshot with live occupancy/attention/active markers."""
        out = []
        for st in self._stations:
            d = dict(st)
            d["occupants"] = list(self._occ.get(st["id"], ()))
            d["active"] = bool(d["occupants"])
            d["attention"] = bool(self._attn.get(st["id"], False))
            out.append(d)
        return out

    def station(self, sid: str) -> dict | None:
        for st in self.stations:
            if st["id"] == sid:
                return st
        return None

    def nearest_station(self, strip_x_m: float,
                        max_m: float = 2.5) -> dict | None:
        """The closest interactable to the player's strip x (the amber
        highlight ring target). None when nothing is within reach."""
        best, best_d = None, max_m
        for st in self.stations:
            d = abs(st["strip_x_m"] - strip_x_m)
            if d <= best_d:
                best, best_d = st, d
        return best

    # -- enrolment / needs ---------------------------------------------------
    def _enroll(self, name: str) -> None:
        if name not in self.needs:
            self.needs[name] = _fresh_needs()
        if name not in self.crew_x:
            self.crew_x[name] = ROOM_M * (
                1.5 + (zlib.crc32(name.encode()) % 80) / 80.0
                * max(1, len(self.modules) - 0.5))

    def need(self, name: str) -> dict:
        return dict(self.needs.get(name, _fresh_needs()))

    # -- the daily plan (08 §4.5) ------------------------------------------------
    def plan(self, name: str) -> list[dict]:
        """The crew's 24 h schedule: sleep shift, exercise prescription,
        meals at the galley, work blocks at the role's station. Player
        overrides (``override``) replace it wholesale."""
        if name in self.overrides:
            return [dict(b) for b in self.overrides[name]]
        names = sorted(self.crew)
        idx = names.index(name) if name in names else 0
        bunk_cap = sum(st["capacity"] for st in self._by_type.get("bunk", ()))
        groups = max(1, math.ceil(len(names) / max(1, bunk_cap)))
        wake = (6.0 + (idx % groups) * (24.0 / groups if groups > 1
                                        else 0.0)) % 24.0
        ex_h = exercise_need_h(self.spin_g)
        work_st = self._preferred_work(name)
        blocks, h = [], wake

        def _add(act, dur, station=None):
            nonlocal h
            if dur <= 0.0:
                return
            blocks.append({"h0": round(h % 24.0, 3), "dur": round(dur, 3),
                           "act": act, "station": station})
            h += dur

        gal = self._by_type.get("galley", ())
        gal_id = gal[0]["id"] if gal else None
        ex = self._by_type.get("exercise", ())
        ex_id = ex[0]["id"] if ex else None
        hyg = self._by_type.get("hygiene", ())
        hyg_id = hyg[0]["id"] if hyg else None
        _add("hygiene", 0.5, hyg_id)
        _add("meal", 0.5, gal_id)
        _add("work", 5.0, work_st)
        _add("exercise", ex_h / 2.0, ex_id)
        _add("meal", 0.5, gal_id)
        _add("work", 5.0, work_st)
        _add("exercise", ex_h / 2.0, ex_id)
        _add("meal", 0.5, gal_id)
        _add("free", 16.0 - 2.0 - 10.0 - ex_h)
        bunks = self._by_type.get("bunk", ())
        _add("sleep", 8.0, bunks[0]["id"] if bunks else None)
        return blocks

    def override(self, name: str, blocks: list[dict]) -> bool:
        """Player schedule override: blocks must tile 24 h."""
        total = sum(float(b["dur"]) for b in blocks)
        if abs(total - 24.0) > 0.02:
            return False
        for b in blocks:
            if b["act"] not in POSES and b["act"] != "sleep":
                return False
        self.overrides[name] = [
            {"h0": float(b["h0"]), "dur": float(b["dur"]),
             "act": b["act"], "station": b.get("station")} for b in blocks]
        return True

    def clear_override(self, name: str) -> None:
        self.overrides.pop(name, None)

    def activity(self, name: str, t: float) -> str:
        hour = (t / HOUR_S) % 24.0
        for b in self.plan(name):
            if (hour - b["h0"]) % 24.0 < b["dur"]:
                return b["act"]
        return "free"

    def _preferred_work(self, name: str) -> str | None:
        m = self.crew.get(name)
        role = getattr(m, "role", "engineer")
        want = WORK_STATION.get(role, "maint_panel")
        cands = list(self._by_type.get(want, ()))
        if role == "agronomist":
            cands.sort(key=lambda s: s["module_kind"]
                       not in ("greenhouse", "bio_farm"))
        return cands[0]["id"] if cands else None

    # -- station claiming (capacity-aware, deterministic order) -----------------
    def _strongest_need(self, name: str) -> str | None:
        nd = self.needs[name]
        scored = (
            (nd["sleep_debt_h"] / 8.0, "bunk"),
            (nd["ex_debt_h"] / 3.0 if self.spin_g < G_MARS else 0.0,
             "exercise"),
            (nd["hygiene_d"] / 2.0, "hygiene"),
            (nd["social"], "cupola" if self._by_type.get("cupola")
             else "galley"),
        )
        score, st_type = max(scored)
        return st_type if score > 0.3 else None

    def _pick(self, st_type: str | None, occ: dict,
              prefer: str | None = None) -> str | None:
        if st_type is None:
            return None
        cands = self._by_type.get(st_type, ())
        if prefer is not None:
            cands = sorted(cands, key=lambda s: s["id"] != prefer)
        for st in cands:
            if len(occ[st["id"]]) < st["capacity"]:
                return st["id"]
        return None

    def _assign(self, t: float) -> None:
        occ = {st["id"]: [] for st in self._stations}
        asg = {}
        for name in sorted(self.crew):
            self._enroll(name)
            act = self.activity(name, t)
            st_type = {"sleep": "bunk", "meal": "galley",
                       "exercise": "exercise", "hygiene": "hygiene"}.get(act)
            prefer = None
            if act == "work":
                prefer = self._preferred_work(name)
                st_type = (prefer.split(".")[0] if prefer else None)
            elif act == "free":
                st_type = self._strongest_need(name)
            sid = self._pick(st_type, occ, prefer)
            asg[name] = (act, sid)
            if sid is not None:
                occ[sid].append(name)
        self._occ, self._asg = occ, asg

    def whereabouts(self, name: str) -> dict:
        """Where the scene should draw this crew member: current x,
        target station + ETA, pose key for interior_art."""
        act, sid = self._asg.get(name, ("free", None))
        x = self.crew_x.get(name, ROOM_M * 1.5)
        target = x
        if sid is not None:
            st = next(s for s in self._stations if s["id"] == sid)
            target = st["strip_x_m"]
        moving = abs(target - x) > 0.4
        return {"name": name, "activity": act, "station": sid,
                "x_m": x, "target_x_m": target,
                "eta_s": abs(target - x) / WALK_MPS,
                "moving": moving,
                "pose": "stand" if moving else POSES.get(act, "stand")}

    # -- the integrator ------------------------------------------------------
    def step(self, t: float, dt: float, context: dict | None = None) -> list:
        """Advance shipboard life from t to t+dt (seconds). Returns the
        events that happened: alert-worthy states, arguments, birthdays,
        nightmares, workout injuries, level-ups. context keys (all
        optional): morale_base (08 §4.4 M_target from main's habitat
        ctx; default 60), skill_cap (tier gate, default 3), flyby
        (planet out the cupola), module_cond {module_id: 0-100}."""
        ctx = context or {}
        events: list[dict] = []
        end = t + dt
        n_slices = max(1, math.ceil(dt / SLICE_S))
        if n_slices > 2400:                       # deep warp: coarsen
            n_slices = 2400
        sl = dt / n_slices
        tt = t
        for _ in range(n_slices):
            self._slice(tt, sl, ctx, events)
            tt += sl
        self.t = end
        self._attention(ctx)
        return events

    def _slice(self, t0: float, dt_s: float, ctx: dict,
               events: list) -> None:
        day = int(t0 // DAY_S)
        if day != self.day:
            self._new_day(day, t0, ctx, events)
        self._assign(t0)
        h = dt_s / HOUR_S
        d = dt_s / DAY_S
        ex_need = exercise_need_h(self.spin_g)
        base = float(ctx.get("morale_base", 60.0))
        cap = int(ctx.get("skill_cap", 3))
        diners = [n for n, (a, s) in self._asg.items()
                  if a == "meal" and s is not None]
        for name in sorted(self.crew):
            m = self.crew[name]
            nd = self.needs[name]
            act, sid = self._asg[name]
            # walk toward the claimed station
            target = self.crew_x[name]
            if sid is not None:
                st = next(s for s in self._stations if s["id"] == sid)
                target = st["strip_x_m"]
            dx = target - self.crew_x[name]
            stepm = WALK_MPS * dt_s
            self.crew_x[name] += (dx if abs(dx) <= stepm
                                  else math.copysign(stepm, dx))
            # --- needs integration -------------------------------------
            a_meta = 0.75 if act == "sleep" else (
                1.6 if act == "exercise" else 1.0)
            burn = min(m.energy_kcal, KCAL_BASE_DAY * a_meta * d)
            m.energy_kcal -= burn
            self.kcal_burned += burn
            if act == "sleep":
                nd["sleep_debt_h"] = max(0.0, nd["sleep_debt_h"] - h)
                if name in self.pending_nightmare:
                    self.pending_nightmare.remove(name)
                    nd["sleep_debt_h"] += 2.0
                    m.morale = max(0.0, m.morale - 2.0)
                    events.append({"t": t0, "kind": "nightmare",
                                   "who": [name], "class": 4,
                                   "chronicle": False,
                                   "text": f"{name} wakes from a "
                                           "nightmare — sleep lost"})
            else:
                nd["sleep_debt_h"] += h * (SLEEP_NEED_H_DAY
                                           / (24.0 - SLEEP_NEED_H_DAY))
            if act == "exercise" and sid is not None:
                nd["ex_debt_h"] = max(0.0, nd["ex_debt_h"] - h)
                nd["ex_rate_h"] += (24.0 - nd["ex_rate_h"]) * h / 24.0
                if (nd["ex_debt_h"] > 3.0
                        and name not in self.injured_today
                        and _roll(f"{self.seed}|strain|{day}|{name}")
                        < 0.08):
                    self.injured_today.append(name)
                    m.cond = max(0.0, m.cond - 4.0)
                    if not any(c["kind"] == "injury"
                               for c in m.conditions):
                        m.conditions.append({"kind": "injury", "age": 0.0,
                                             "treated": False})
                    events.append({"t": t0, "kind": "workout_injury",
                                   "who": [name], "class": 3,
                                   "chronicle": False,
                                   "text": f"{name} strained a muscle on "
                                           "the rack (exercise debt was "
                                           "high)"})
            else:
                nd["ex_debt_h"] += h * ex_need / 24.0
                nd["ex_rate_h"] += (0.0 - nd["ex_rate_h"]) * h / 24.0
            if act == "hygiene" and sid is not None:
                nd["hygiene_d"] = max(0.0, nd["hygiene_d"] - 8.0 * h)
            else:
                nd["hygiene_d"] += d
            nd["social"] = min(1.5, nd["social"] + d / 2.0)
            nd["last_meal_h"] += h
            # --- scheduled meals from the real galley stores --------------
            if act == "meal":
                want = MEAL_KCAL * (h / 0.5)
                avail = self.stores["food_kg"] * KCAL_PER_KG_DRY
                room = BODY_RESERVE_KCAL - m.energy_kcal
                got = max(0.0, min(want, avail, room))
                if got > 0.0:
                    m.energy_kcal += got
                    self.stores["food_kg"] -= got / KCAL_PER_KG_DRY
                    self.kcal_served += got
                    nd["last_meal_h"] = 0.0
                    if sid is not None and len(diners) >= 2:
                        nd["social"] = max(0.0, nd["social"] - 0.5 * h)
                elif avail <= 0.0 and self._edge("no_food", True):
                    events.append({"t": t0, "kind": "no_food",
                                   "who": sorted(self.crew), "class": 2,
                                   "chronicle": True,
                                   "text": "galley stores empty — crew "
                                           "are missing meals"})
            if self.stores["food_kg"] > 1.0:
                self._edge("no_food", False)
            if act == "free" and sid is not None \
                    and sid.startswith("cupola"):
                nd["social"] = max(0.0, nd["social"] - 0.25 * h)
            # --- existing CrewMember physiology --------------------------
            m.step_conditioning(self.spin_g, nd["ex_rate_h"], d)
            off = 0.0
            if nd["sleep_debt_h"] > 8.0:
                off -= 8.0
            elif nd["sleep_debt_h"] > 4.0:
                off -= 4.0
            if nd["hygiene_d"] > 1.5:
                off -= 4.0
            if nd["social"] > 0.6:
                off -= 5.0
            if nd["ex_debt_h"] > 3.0:
                off -= 3.0
            if nd["last_meal_h"] > 9.0:
                off -= 4.0
            if act == "sleep" and sid is None:
                off -= 3.0                        # hot-bunking (08 §4.4)
            m.step_morale(base + off, d)
            if act == "work" and sid is not None:
                skill = STATION_SKILL.get(sid.split(".")[0])
                if skill and m.accrue_xp(skill, h, cap=cap):
                    events.append({"t": t0, "kind": "level_up",
                                   "who": [name], "class": 4,
                                   "chronicle": True,
                                   "text": f"{name} qualifies {skill} "
                                           f"level {m.skills[skill]}"})
            self._crew_alerts(t0, name, m, nd, events)

    def _edge(self, flag: str, state: bool) -> bool:
        """Rising-edge latch for ship-level alerts."""
        was = self._ship_flags.get(flag, False)
        self._ship_flags[flag] = state
        return state and not was

    def _crew_alerts(self, t0: float, name: str, m, nd: dict,
                     events: list) -> None:
        checks = (
            ("exhausted", nd["sleep_debt_h"] > EXHAUSTED_H,
             nd["sleep_debt_h"] < EXHAUSTED_H * 0.8, 3,
             f"{name} is exhausted — schedule sleep"),
            ("decon", self.spin_g < G_FREEFALL
             and nd["ex_debt_h"] > DECON_DEBT_H,
             nd["ex_debt_h"] < DECON_DEBT_H * 0.8, 3,
             f"{name} is missing exercise — bone/muscle loss "
             "accelerating"),
            ("filthy", nd["hygiene_d"] > FILTHY_D,
             nd["hygiene_d"] < FILTHY_D * 0.8, 4,
             f"{name} has gone days without hygiene"),
            ("starving",
             m.energy_kcal < STARVING_FRAC * BODY_RESERVE_KCAL,
             m.energy_kcal > STARVING_FRAC * BODY_RESERVE_KCAL * 1.25,
             2, f"{name} is starving — body reserve critical"),
        )
        flags = nd["flags"]
        for key, on, clear, cls, text in checks:
            if on and not flags.get(key):
                flags[key] = True
                events.append({"t": t0, "kind": key, "who": [name],
                               "class": cls, "chronicle": cls <= 2,
                               "text": text})
            elif flags.get(key) and clear:
                flags[key] = False

    # -- the day boundary: deterministic small events ---------------------------
    def _new_day(self, day: int, t0: float, ctx: dict,
                 events: list) -> None:
        names = sorted(self.crew)
        # forgotten birthdays sting
        for name in self.birthdays_today:
            if name not in self.celebrated and name in self.crew:
                self.crew[name].morale = max(
                    0.0, self.crew[name].morale - 3.0)
        self.day = day
        self.cupola_uses = 0
        self.injured_today = []
        self.birthdays_today = []
        self.celebrated = []
        bunk_cap = sum(st["capacity"]
                       for st in self._by_type.get("bunk", ()))
        crowd = 1.3 if len(names) > max(1, bunk_cap) else 1.0
        for i, a in enumerate(names):            # crew arguments
            for b in names[i + 1:]:
                pa, pb = self.crew[a], self.crew[b]
                p = 0.02 * crowd * (pa.phi_err + pb.phi_err) / 2.0
                if _roll(f"{self.seed}|argue|{day}|{a}|{b}") < p:
                    pa.morale = max(0.0, pa.morale - 6.0)
                    pb.morale = max(0.0, pb.morale - 6.0)
                    self.needs[a]["social"] = min(
                        1.5, self.needs[a]["social"] + 0.4)
                    self.needs[b]["social"] = min(
                        1.5, self.needs[b]["social"] + 0.4)
                    self.arguments.append({"a": a, "b": b, "day": day})
                    events.append({"t": t0, "kind": "argument",
                                   "who": [a, b], "class": 3,
                                   "chronicle": False,
                                   "text": f"{a} and {b} had a blazing "
                                           "row — a shared meal would "
                                           "help"})
        for name in names:                       # birthdays + nightmares
            if zlib.crc32(f"bday|{name}".encode()) % 365 == day % 365:
                self.birthdays_today.append(name)
                events.append({"t": t0, "kind": "birthday",
                               "who": [name], "class": 4,
                               "chronicle": True,
                               "text": f"it is {name}'s birthday — cook "
                                       "something in the galley"})
            p_night = 0.05 * (1.0 + max(
                0.0, (70.0 - self.crew[name].morale) / 100.0))
            if _roll(f"{self.seed}|night|{day}|{name}") < p_night:
                self.pending_nightmare.append(name)

    # -- attention markers for the renderer ----------------------------------------
    def _attention(self, ctx: dict) -> None:
        cond = ctx.get("module_cond", {})
        sick = any(not c.get("treated") for m in self.crew.values()
                   for c in m.conditions)
        self._attn = {}
        for st in self._stations:
            a = False
            if st["type"] == "maint_panel":
                a = cond.get(st["module_id"], 100.0) < 75.0
            elif st["type"] == "med_bay":
                a = sick
            elif st["type"] == "galley":
                a = bool(self.birthdays_today
                         and not self.celebrated)
            self._attn[st["id"]] = a

    # -- player verbs (real effects, cooldowns, capacity gates) ----------------
    def verb(self, verb: str, station_id: str, t: float,
             context: dict | None = None,
             actor: str | None = None) -> dict:
        """Run a player verb at a station. Returns {"ok", "events",
        "effects", ...}; effects are wire-friendly tuples for main
        (e.g. ("repair", module_id, amount))."""
        ctx = context or {}
        st = next((s for s in self._stations if s["id"] == station_id),
                  None)
        if st is None or verb not in st["verbs"]:
            return {"ok": False, "reason": "no such verb here",
                    "events": [], "effects": None}
        key = f"{station_id}|{verb}"
        ready = self.cooldowns.get(key, -1e18)
        if t < ready:
            return {"ok": False, "reason": "cooldown",
                    "ready_in_s": ready - t, "events": [],
                    "effects": None}
        occ = self._occ.get(station_id, [])
        if len(occ) >= st["capacity"] and (actor is None
                                           or actor not in occ):
            return {"ok": False, "reason": "station is fully occupied",
                    "events": [], "effects": None}
        if not self.crew and verb != "gaze":
            return {"ok": False, "reason": "no crew aboard",
                    "events": [], "effects": None}
        fn = getattr(self, f"_verb_{verb}")
        out = fn(st, t, ctx, actor)
        if out.get("ok"):
            self.cooldowns[key] = t + VERB_COOLDOWN_H[verb] * HOUR_S
        return out

    def _best(self, skill: str, actor: str | None):
        if actor is not None and actor in self.crew:
            return actor, self.crew[actor]
        if not self.crew:
            return None, None
        name = max(sorted(self.crew),
                   key=lambda n: self.crew[n].skills.get(skill, 0))
        return name, self.crew[name]

    def _verb_cook(self, st, t, ctx, actor) -> dict:
        """A proper cooked meal: extra kcal from stores, +morale to all
        who eat together, clears arguments, celebrates birthdays."""
        diners = [n for n in sorted(self.crew)
                  if self.activity(n, t) != "sleep"]
        if not diners:
            return {"ok": False, "reason": "everyone is asleep",
                    "events": [], "effects": None}
        avail = self.stores["food_kg"] * KCAL_PER_KG_DRY
        if avail < COOK_KCAL_EACH:
            return {"ok": False, "reason": "stores too lean to cook",
                    "events": [], "effects": None}
        events = []
        served = 0.0
        bump = 5.0 if len(diners) >= 2 else 2.0
        for n in diners:
            m = self.crew[n]
            got = min(COOK_KCAL_EACH, avail - served,
                      BODY_RESERVE_KCAL - m.energy_kcal)
            got = max(0.0, got)
            m.energy_kcal += got
            served += got
            m.morale = min(100.0, m.morale + bump)
            self.needs[n]["social"] = 0.0
            self.needs[n]["last_meal_h"] = 0.0
        self.stores["food_kg"] -= served / KCAL_PER_KG_DRY
        self.kcal_served += served
        for arg in list(self.arguments):         # the social fix
            if arg["a"] in diners and arg["b"] in diners:
                self.arguments.remove(arg)
                for n in (arg["a"], arg["b"]):
                    self.crew[n].morale = min(
                        100.0, self.crew[n].morale + 4.0)
                events.append({"t": t, "kind": "made_up",
                               "who": [arg["a"], arg["b"]], "class": 4,
                               "chronicle": False,
                               "text": f"{arg['a']} and {arg['b']} "
                                       "cleared the air over dinner"})
        for n in self.birthdays_today:
            if n in diners and n not in self.celebrated:
                self.celebrated.append(n)
                for dn in diners:
                    self.crew[dn].morale = min(
                        100.0, self.crew[dn].morale
                        + (10.0 if dn == n else 4.0))
                events.append({"t": t, "kind": "birthday_party",
                               "who": diners, "class": 4,
                               "chronicle": True,
                               "text": f"the crew celebrated {n}'s "
                                       "birthday in the galley"})
        events.append({"t": t, "kind": "meal", "who": diners,
                       "class": 4, "chronicle": False,
                       "text": f"a proper meal for {len(diners)} "
                               f"({served:,.0f} kcal from stores)"})
        return {"ok": True, "events": events,
                "effects": ("meal", diners, round(served, 1))}

    def _verb_scan(self, st, t, ctx, actor) -> dict:
        """Medical scan: reveals every condition aboard early and (with
        a medic + MedSupplies) treats what it can right now."""
        from aphelion.game.crew import MED_CONDITIONS
        _, medic = self._best("medic", actor)
        lvl = medic.skills.get("medic", 0) if medic else 0
        findings, treated, events = [], [], []
        for n in sorted(self.crew):
            for c in self.crew[n].conditions:
                spec = MED_CONDITIONS[c["kind"]]
                c["revealed"] = True
                findings.append((n, c["kind"], bool(c["treated"])))
                if (not c["treated"] and lvl >= spec["medic"]
                        and self.stores["medsupplies_kg"]
                        >= spec["supplies"]):
                    self.stores["medsupplies_kg"] -= spec["supplies"]
                    c["treated"] = True
                    c["age"] = 0.0
                    treated.append((n, c["kind"]))
        if treated:
            events.append({"t": t, "kind": "treated",
                           "who": [n for n, _ in treated], "class": 4,
                           "chronicle": False,
                           "text": "med scan: treated "
                                   + ", ".join(f"{n} ({k})"
                                               for n, k in treated)})
        elif findings:
            events.append({"t": t, "kind": "diagnosis",
                           "who": [n for n, _, _ in findings],
                           "class": 3, "chronicle": False,
                           "text": "med scan flagged: "
                                   + ", ".join(f"{n} ({k})"
                                               for n, k, _ in findings)})
        return {"ok": True, "events": events,
                "effects": ("scan", findings, treated)}

    def _verb_repair(self, st, t, ctx, actor) -> dict:
        """Maintenance at the panel — restores the module's cond. Main
        applies the returned amount to the module."""
        name, eng = self._best("engineer", actor)
        rate = eng.task_rate("engineer", t) if eng else 0.5
        amount = round(5.0 + 10.0 * rate, 1)
        if eng:
            eng.accrue_xp("engineer", 1.0,
                          cap=int(ctx.get("skill_cap", 3)))
        ev = [{"t": t, "kind": "repair", "who": [name] if name else [],
               "class": 4, "chronicle": False,
               "text": f"{name or 'crew'} serviced {st['module_id']} "
                       f"(+{amount:.0f} cond)"}]
        return {"ok": True, "events": ev,
                "effects": ("repair", st["module_id"], amount)}

    def _verb_research(self, st, t, ctx, actor) -> dict:
        """Bench science: crew time + one sample -> science points,
        scaled by the scientist's task rate."""
        if self.stores.get("samples", 0.0) < 1.0:
            return {"ok": False, "reason": "no samples to analyze",
                    "events": [], "effects": None}
        name, sci = self._best("scientist", actor)
        rate = sci.task_rate("scientist", t) if sci else 0.5
        pts = round(6.0 * rate, 2)
        self.stores["samples"] -= 1.0
        if sci:
            sci.accrue_xp("scientist", 2.0,
                          cap=int(ctx.get("skill_cap", 3)))
        ev = [{"t": t, "kind": "science", "who": [name] if name else [],
               "class": 4, "chronicle": False,
               "text": f"{name or 'crew'} worked a sample at the bench "
                       f"(+{pts:.1f} science)"}]
        return {"ok": True, "events": ev, "effects": ("science", pts)}

    def _verb_gaze(self, st, t, ctx, actor) -> dict:
        """The cupola: morale restore with diminishing returns per day;
        a planet flyby out the glass is worth the trip every time."""
        gain = 6.0 * (0.5 ** self.cupola_uses)
        flyby = bool(ctx.get("flyby"))
        if flyby:
            gain += 10.0
        self.cupola_uses += 1
        who = []
        if actor is not None and actor in self.crew:
            self.crew[actor].morale = min(
                100.0, self.crew[actor].morale + gain)
            who = [actor]
        else:
            for n in sorted(self.crew):
                self.crew[n].morale = min(
                    100.0, self.crew[n].morale + gain / 2.0)
                who.append(n)
        txt = ("the planet fills the cupola — the crew crowd the glass"
               if flyby else "a long look out the cupola")
        ev = [{"t": t, "kind": "cupola", "who": who, "class": 4,
               "chronicle": flyby, "text": txt}]
        return {"ok": True, "events": ev,
                "effects": ("morale", round(gain, 2))}

    def _verb_wash(self, st, t, ctx, actor) -> dict:
        name = actor if actor in self.needs else (
            sorted(self.needs)[0] if self.needs else None)
        if name is None:
            return {"ok": False, "reason": "no crew aboard",
                    "events": [], "effects": None}
        self.needs[name]["hygiene_d"] = 0.0
        self.crew[name].morale = min(100.0, self.crew[name].morale + 1.0)
        return {"ok": True, "events": [], "effects": ("wash", name)}

    def _verb_work_out(self, st, t, ctx, actor) -> dict:
        name, m = self._best("pilot", actor)   # anyone; actor preferred
        if actor is None and self.needs:
            name = max(sorted(self.needs),
                       key=lambda n: self.needs[n]["ex_debt_h"])
            m = self.crew[name]
        nd = self.needs[name]
        was_high = nd["ex_debt_h"] > 3.0
        nd["ex_debt_h"] = max(0.0, nd["ex_debt_h"] - 1.5)
        nd["ex_rate_h"] = min(24.0, nd["ex_rate_h"] + 1.0)
        events, effects = [], ("exercise", name)
        if was_high and name not in self.injured_today and _roll(
                f"{self.seed}|strain|{self.day}|{name}|v") < 0.08:
            self.injured_today.append(name)
            m.cond = max(0.0, m.cond - 4.0)
            if not any(c["kind"] == "injury" for c in m.conditions):
                m.conditions.append({"kind": "injury", "age": 0.0,
                                     "treated": False})
            events.append({"t": t, "kind": "workout_injury",
                           "who": [name], "class": 3,
                           "chronicle": False,
                           "text": f"{name} strained a muscle on the "
                                   "rack (exercise debt was high)"})
        return {"ok": True, "events": events, "effects": effects}

    # -- persistence (plain JSON-safe dicts) ------------------------------------
    def to_dict(self) -> dict:
        return {
            "modules": [list(m) for m in self.modules],
            "spin_g": self.spin_g, "t": self.t, "day": self.day,
            "stores": dict(self.stores),
            "needs": {n: {k: (dict(v) if isinstance(v, dict) else v)
                          for k, v in nd.items()}
                      for n, nd in self.needs.items()},
            "crew_x": dict(self.crew_x),
            "cooldowns": dict(self.cooldowns),
            "overrides": {n: [dict(b) for b in bl]
                          for n, bl in self.overrides.items()},
            "arguments": [dict(a) for a in self.arguments],
            "birthdays_today": list(self.birthdays_today),
            "celebrated": list(self.celebrated),
            "pending_nightmare": list(self.pending_nightmare),
            "injured_today": list(self.injured_today),
            "cupola_uses": self.cupola_uses,
            "kcal_served": self.kcal_served,
            "kcal_burned": self.kcal_burned,
            "ship_flags": dict(self._ship_flags),
        }

    @classmethod
    def from_dict(cls, d: dict, crew_dict: dict) -> "Shipboard":
        sb = cls(d["modules"], crew_dict, d.get("spin_g", 0.0),
                 d.get("t", 0.0), stores=d.get("stores"))
        sb.day = int(d.get("day", sb.day))
        sb.needs = {n: {k: (dict(v) if isinstance(v, dict) else v)
                        for k, v in nd.items()}
                    for n, nd in d.get("needs", {}).items()}
        for name in crew_dict:
            sb._enroll(name)
        sb.crew_x.update(d.get("crew_x", {}))
        sb.cooldowns = dict(d.get("cooldowns", {}))
        sb.overrides = {n: [dict(b) for b in bl]
                        for n, bl in d.get("overrides", {}).items()}
        sb.arguments = [dict(a) for a in d.get("arguments", [])]
        sb.birthdays_today = list(d.get("birthdays_today", []))
        sb.celebrated = list(d.get("celebrated", []))
        sb.pending_nightmare = list(d.get("pending_nightmare", []))
        sb.injured_today = list(d.get("injured_today", []))
        sb.cupola_uses = int(d.get("cupola_uses", 0))
        sb.kcal_served = float(d.get("kcal_served", 0.0))
        sb.kcal_burned = float(d.get("kcal_burned", 0.0))
        sb._ship_flags = dict(d.get("ship_flags", {}))
        return sb
