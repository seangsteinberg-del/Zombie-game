"""APHELION — the campaign game.

You run a space program: build rockets (B), fly them to orbit yourself
(KSP-style pad ascent), and operate a persistent FLEET — every vessel
keeps its real tanks, engines, stages, and crew. Burns spend actual
propellant; the predicted patched-conic trajectory — across up to 5 SOI
transitions — is drawn live ahead of the active vessel. V switches
vessels; warp through an encounter and the sim re-expresses the orbit in
the new frame exactly as the planner predicted (same math, by
construction).

Controls
  . / ,        warp up / down            space   pause
  TAB / S-TAB  focus next / prev body    C       focus your craft
  click body   focus it                  wheel   zoom
  X / Z        +-10 m/s prograde         A / D   +-10 m/s radial
  (hold shift for 100 m/s steps)
  B  builder   N  maneuver node          R  research   G  found base
  F1 tutorial  F2 base screen            F5 / F9  quicksave / load
  F11 fullscreen   M mute                ESC  pause menu

Dev flags: --frames N  --screenshot PATH  --headless  --scene S
"""

from __future__ import annotations

import argparse
import colorsys
import hashlib
import zlib
import json
import math
import os
import sys
import time

from aphelion.core.clock import RAILS_RATES, SimClock
from aphelion.core.units import SECONDS_PER_DAY
from aphelion.render.camera import Camera, ZoomLayer
from aphelion.sim.economy import Contract, Program
from aphelion.sim.orbits.ephemeris import load_solar_system
from aphelion.sim.orbits.kepler import elements_to_state, state_to_elements
from aphelion.sim.orbits import transfers as tr
from aphelion.sim.orbits.trajectory import predict_trajectory
from aphelion.sim.research import (MODULE_FAMILY, ResearchState, badge,
                                   engine_family, maturity)

# exploration science per first SOI entry (11: location-gated Science)
_FIRST_ENTRY_SCIENCE = {
    "core:moon": 400.0, "core:sun": 250.0, "core:mars": 900.0,
    "core:venus": 900.0, "core:mercury": 1_200.0, "core:jupiter": 1_500.0,
    "core:europa": 2_500.0, "core:titan": 2_500.0, "core:saturn": 1_500.0,
}

_BODY_COLORS = {
    "core:sun": (255, 220, 120), "core:mercury": (140, 130, 120),
    "core:venus": (230, 200, 140), "core:earth": (90, 140, 255),
    "core:moon": (170, 170, 175), "core:mars": (230, 110, 70),
    "core:jupiter": (220, 180, 140), "core:saturn": (230, 210, 160),
    "core:uranus": (160, 210, 220), "core:neptune": (110, 140, 230),
}
_DEFAULT_COLOR = (130, 135, 145)
_ORBIT_COLOR = (52, 64, 92)
_MOON_ORBIT_COLOR = (64, 76, 104)
_CRAFT_COLOR = (120, 255, 170)
_GROUND_COLORS = {
    "core:earth": (28, 46, 34), "core:moon": (68, 70, 76),
    "core:mars": (112, 60, 38), "core:titan": (92, 74, 48),
    "core:europa": (148, 158, 174), "core:venus": (118, 88, 48),
}
_CAPSULE_HEAT_W_M2 = 2.5e6     # ablative-protected stack survives this
_BARE_HEAT_W_M2 = 0.9e6        # bare tankage does not
_ENTRY_G_LIMIT = 8.0           # crewed sustained-g ceiling (08)

_DIFFICULTIES: dict[str, dict] = {
    "CADET": dict(funds=250e6, payout=1.25, deadline=1.5, overhead=0.0,
                  blurb="rich start · patient sponsors · no overhead"),
    "DIRECTOR": dict(funds=150e6, payout=1.0, deadline=1.0, overhead=1.0,
                     blurb="the intended program"),
    "HARDCORE": dict(funds=90e6, payout=0.75, deadline=0.8, overhead=2.0,
                     blurb="lean start · stingy sponsors · 2x overhead · "
                           "no launch revert"),
}
# monthly program overhead (per 30 days, scaled by difficulty)
_OVERHEAD_FIXED_M = 1.5
_OVERHEAD_PER_CREW_M = 0.4
_OVERHEAD_PER_BASE_M = 1.0
_LEG_COLORS = [(120, 255, 170), (255, 200, 60), (255, 120, 200),
               (140, 200, 255), (255, 160, 90), (200, 140, 255)]
_WARP_LADDER = (1.0,) + RAILS_RATES
_PREDICT_HORIZON = 60.0 * SECONDS_PER_DAY
_REVERT_WINDOW_S = 20.0      # pad-scrub window: ESC refunds only this long


def _frame_color(frame_id: str) -> tuple[int, int, int]:
    """Stable per-frame trajectory hue: a moon leg is ALWAYS the same color,
    so a 3-leg prediction reads as a plan instead of a color-cycled tangle."""
    h = int.from_bytes(hashlib.blake2b(frame_id.encode(),
                                       digest_size=2).digest(), "little")
    r, g, b = colorsys.hsv_to_rgb((h % 360) / 360.0, 0.55, 1.0)
    return int(r * 255), int(g * 255), int(b * 255)


def _wrap_pi(x: float) -> float:
    return (x + math.pi) % (2.0 * math.pi) - math.pi


def _transfer_window(mu_s: float, r1: float, r2: float,
                     phase_now: float) -> tuple[float, float, float]:
    """(wait_s, t_transfer_s, phase_required_rad) for a Hohmann departure
    from circular r1 to r2 around mu_s, given the current target-minus-
    origin phase angle. wait is in [0, synodic period)."""
    _, _, t_tr = tr.hohmann(mu_s, r1, r2)
    n_o = math.sqrt(mu_s / r1 ** 3)
    n_t = math.sqrt(mu_s / r2 ** 3)
    phase_req = math.pi - n_t * t_tr
    dphase = n_t - n_o
    syn = 2.0 * math.pi / abs(dphase)
    wait = _wrap_pi(phase_req - phase_now) / dphase
    wait %= syn
    if wait < 0.0:
        wait += syn
    return wait, t_tr, phase_req


def _next_apsis_times(el, t: float) -> tuple[float, float]:
    """(next periapsis time, next apoapsis time) for an elliptic orbit."""
    T = el.period
    if not math.isfinite(T) or T <= 0.0:
        return math.inf, math.inf
    t_pe = el.tau + math.ceil((t - el.tau) / T + 1e-9) * T
    t_ap = t_pe - T / 2.0
    if t_ap <= t:
        t_ap += T
    return t_pe, t_ap
_PAUSE_ITEMS = ("RESUME", "QUICKSAVE", "LOAD QUICKSAVE", "VOLUME -",
                "VOLUME +", "EXIT TO MAIN MENU", "QUIT TO DESKTOP")


_BRANCH_ORDER = ("PR", "GN", "PW", "IS", "IN", "SH", "HB", "LS", "VH", "SC")
_BRANCH_NAMES = {"PR": "PROPULSION", "GN": "GNC & COMMS", "PW": "POWER",
                 "IS": "ISRU", "IN": "INDUSTRY", "SH": "SHIPS",
                 "HB": "HABITATS", "LS": "LIFE SUPPORT", "VH": "VEHICLES",
                 "SC": "SCIENCE"}


def _tech_order(db, research=None) -> list[str]:
    """Board order: branch columns, then tier, then cost. With a research
    state, fogged nodes (11 §1.5) are excluded — they draw as ??? but are
    not selectable."""
    ids = sorted(
        db.tech,
        key=lambda i: (_BRANCH_ORDER.index(db.tech[i].get("category", "SC")),
                       db.tech[i]["tier"],
                       db.tech[i].get("cost_sci", 0.0)))
    if research is not None:
        ids = [i for i in ids if research.visible(db, i)]
    return ids


def _fresh_research(db) -> "ResearchState":
    rs = ResearchState()
    rs.bootstrap(db)
    return rs


# environment class (11 §3.5 M_env) by site kind / body for ED accrual
_KIND_ENV = {"psr_ice": "cryo_surface", "mars_ice": "vacuum_dusty_surface",
             "aerostat": "dense_atmosphere", "methane_lake": "cryo_surface",
             "ice_burrow": "high_radiation"}
_ATMO_BODIES = {"core:earth", "core:venus", "core:mars", "core:titan"}


def _stage_engine_families(vessel) -> set[str]:
    """ED families of the engines in the active (bottom) stage."""
    fams: set[str] = set()
    if vessel is None or not vessel.stage_plan:
        return fams
    for idx in vessel.stage_plan[0]:
        pid = vessel.rows[idx].part_id
        if "engine" in pid:
            fams.add(engine_family(pid))
    return fams


def _ascent_env(body_id: str) -> str:
    return ("dense_atmosphere" if body_id in _ATMO_BODIES
            else "vacuum_dusty_surface")


from aphelion.game.fleet import FleetVessel  # noqa: E402  (campaign vessel)
from aphelion.game.sites import SITES, sites_for_body  # noqa: E402
from aphelion.game.sectors import (  # noqa: E402
    BODY_OPS, landable, sector_site)
from aphelion.game import eva as eva_sim  # noqa: E402
from aphelion.game import tileworld  # noqa: E402
from aphelion.render import eva_art  # noqa: E402
from aphelion.render import glpost  # noqa: E402
from aphelion.render import vehicle_art  # noqa: E402
from aphelion.sim.vehicles import locomotion  # noqa: E402
from aphelion.sim.vehicles import marine  # noqa: E402
from aphelion.sim.vehicles import wear as vwear  # noqa: E402
from aphelion.render.tile_art import TileRenderer  # noqa: E402
from aphelion.sim.vessels import autostage as dd_stage  # noqa: E402
from aphelion.sim.vessels.buildermath import stage_report  # noqa: E402
from aphelion.sim.vessels.grid import GridVessel  # noqa: E402
from aphelion.sim.vessels.structure import (  # noqa: E402
    ascent_qsim, qalpha_limit_kpadeg, validate_e7)
from aphelion.sim.stations import keeping as keeping_sim  # noqa: E402
from aphelion.sim.stations import ports as ports_sim  # noqa: E402
from aphelion.sim.stations import spin as spin_sim  # noqa: E402
from aphelion.sim.environment.mars_climate import (  # noqa: E402
    MarsWeather, f_dust as mars_f_dust)
from aphelion.sim.environment.space_env import (  # noqa: E402
    SpeSchedule, spe_distance_factor)


def _drive_terrain_key(site: dict) -> str:
    """Map a landing site onto the 10 §2.1 terrain table (V5 driving)."""
    kind = str(site.get("kind", "")).lower()
    body = str(site.get("body", ""))
    if "dune" in kind:
        return "dune"
    if "ice" in kind or "psr" in kind:
        return "ice_plain"
    if body.endswith("mars"):
        return "duricrust"
    if body.endswith("titan"):
        return "titan_shore"
    if body.endswith("earth"):
        return "earth_road"
    return "regolith"


def _fmt_bps(bps: float) -> str:
    """Human link rate — Voyager bit/s up to optical Gbit/s (C wiring)."""
    if bps >= 1e9:
        return f"{bps / 1e9:,.1f} Gbit/s"
    if bps >= 1e6:
        return f"{bps / 1e6:,.1f} Mbit/s"
    if bps >= 1e3:
        return f"{bps / 1e3:,.0f} kbit/s"
    return f"{bps:,.0f} bit/s"


def _seg_blocked(ax: float, ay: float, bx: float, by: float,
                 cx: float, cy: float, r: float) -> bool:
    """True when the segment A→B passes through the disc at C (body
    occlusion for the comms LOS callable). Endpoints inside the disc
    don't count — their own body is abstracted by availability rules."""
    dx, dy = bx - ax, by - ay
    l2 = dx * dx + dy * dy
    if l2 <= 0.0:
        return False
    u = ((cx - ax) * dx + (cy - ay) * dy) / l2
    if u <= 0.0 or u >= 1.0:
        return False
    px, py = ax + u * dx, ay + u * dy
    return math.hypot(px - cx, py - cy) < r


def _corridor_advice(body_id: str, mu: float, radius: float, el,
                     beta: float,
                     rating_w_m2: float) -> list[tuple[str, str]]:
    """Aerocapture/entry corridor advisor for the NAV panel (01 §1.6).

    Judges the encounter leg's arrival conic against the live
    skip/capture/land corridor for THIS stack. Coarse integrator settings —
    this is advisory; the entry adjudicator still flies the real thing.
    Returns [(line, status)] with status in {"go", "warn", "danger"}.
    """
    from aphelion.sim.environment.atmosphere import interface_altitude
    from aphelion.sim.flight.corridor import advise, corridor

    h_int = interface_altitude(body_id)
    if not math.isfinite(h_int):
        return []
    r_i = radius + h_int
    v2 = mu * (2.0 / r_i - el.alpha)
    if v2 <= 0.0:
        return []                     # conic never reaches the interface
    v_i = math.sqrt(v2)
    try:
        rep = corridor(body_id, mu, radius, v_i, max(beta, 10.0),
                       tol_deg=0.1, dt=0.25)
    except ValueError:
        return []
    if el.periapsis >= r_i:
        # vacuum flyby: tell the player what periapsis to AIM for
        if rep.has_capture_band:
            return [(
                f"AEROCAPTURE window Pe "
                f"{rep.hp_window_lo_m / 1e3:,.0f}-"
                f"{rep.hp_window_hi_m / 1e3:,.0f} km — current Pe "
                f"{(el.periapsis - radius) / 1e3:,.0f} km HIGH (flyby)",
                "warn")]
        return []
    # the conic dips into the atmosphere: judge the entry angle itself
    v_pe = math.sqrt(max(mu * (2.0 / el.periapsis - el.alpha), 0.0))
    cosg = min(1.0, (el.periapsis * v_pe) / (r_i * v_i))
    gamma = math.degrees(math.acos(cosg))
    if not (rep.has_capture_band or math.isfinite(rep.gamma_land_limit)):
        return [("ENTRY: NO CORRIDOR — can neither capture nor land",
                 "danger")]
    _, margin = advise(rep, gamma)
    if rep.has_capture_band:
        lo = rep.gamma_capture_lo
        band = f"{lo:.1f}-{rep.gamma_capture_hi:.1f}"
    else:
        lo = rep.gamma_land_limit
        band = f"{rep.gamma_land_limit:.1f}+"
    lines: list[tuple[str, str]] = []
    if margin >= 0.0:
        lines.append((f"ENTRY {gamma:.1f} deg in corridor {band} — GO "
                      f"({margin:.1f} deg margin)",
                      "go" if margin >= 0.3 else "warn"))
    else:
        side = "SHALLOW (skip-out risk)" if gamma < lo else "STEEP"
        lines.append((f"ENTRY {gamma:.1f} deg vs corridor {band} — "
                      f"{-margin:.1f} deg {side}", "danger"))
    if (math.isfinite(rep.peak_heating_w_m2)
            and rep.peak_heating_w_m2 > rating_w_m2):
        lines.append((
            f"TPS: {rep.peak_heating_w_m2 / 1e6:.1f} MW/m2 at corridor "
            f"center vs {rating_w_m2 / 1e6:.1f} rated — WILL BURN UP",
            "danger"))
    return lines


def _surface_options(av, bases, db=None,
                     investigated=frozenset(),
                     vehicles=()) -> list[tuple[tuple, str]]:
    """Context actions for the surface-ops panel (G)."""
    opts: list[tuple[tuple, str]] = []
    if av.landed_at is not None:
        site = SITES[av.landed_at]
        opts.append((("relaunch",),
                     f"RELAUNCH — fly the ascent   (~{site['ascent_dv']:,.0f} m/s)"))
        if av.crew:
            opts.append((("eva",),
                         f"EVA — WALK THE SURFACE   ({av.crew[0]} suits up)"))
        if db is not None:
            anomalies = db.by_type("anomalies")
            for aid in site.get("anomalies", []):
                if aid in investigated:
                    continue
                an = anomalies[aid]
                opts.append((("investigate", aid),
                             f"INVESTIGATE {an['class']}: {an['name']}   "
                             f"(+{an['gb']:.0f} GB, +{2 * an['gb']:.0f} sci)"))
        home = next((b for b in bases
                     if getattr(b, "site_id", None) == av.landed_at), None)
        if home is None:
            opts.append((("found",),
                         "FOUND A BASE here (tanks + crew become the colony)"))
        else:
            banked = {res: buf.level for res, buf in home.net.buffers.items()
                      if res != "Battery" and buf.level > 1.0}
            if banked:
                inv = "  ".join(f"{res} {kg / 1e3:,.1f}t"
                                for res, kg in sorted(banked.items()))
                opts.append((("refuel",),
                             f"REFUEL FROM BASE   ({inv})"))
            if home.crew:
                opts.append((("board",),
                             f"BOARD CREW   ({', '.join(home.crew[:4])})"))
            # bulk parts cargo for the orbital yard economy (05 §3.1)
            if av.cargo_cap_kg > 0.0:
                from aphelion.sim.industry.yard import PARTS_CARGO
                on_shelf = sum(home.net.buffers[r].level
                               for r in PARTS_CARGO
                               if r in home.net.buffers)
                if on_shelf > 1.0:
                    opts.append((("load_parts",),
                                 f"LOAD PARTS CARGO   (shelves "
                                 f"{on_shelf / 1e3:,.1f} t, bays "
                                 f"{av.cargo_kg / 1e3:,.1f}/"
                                 f"{av.cargo_cap_kg / 1e3:,.0f} t)"))
            if av.cargo_kg > 0.0:
                opts.append((("unload_cargo",),
                             f"UNLOAD CARGO TO BASE   "
                             f"({av.cargo_kg / 1e3:,.1f} t aboard)"))
        # V5: vehicles parked at this site + the base motor pool
        for gv in vehicles:
            if gv.site_id == av.landed_at:
                kind_v = gv.catalog_id.rsplit(":", 1)[-1]
                verb_v = ("dive" if kind_v in ("sub_t", "boat_t")
                          else "drive")
                opts.append((
                    (verb_v, gv.vid),
                    f"{verb_v.upper()} {gv.name}   "
                    f"({kind_v.upper()}, charge "
                    f"{100.0 * gv.energy_kwh / max(gv.pack_kwh, 1e-9):.0f}%"
                    f", cond {100.0 * gv.cond:.0f}%)"))
        if home is not None and db is not None:
            from aphelion.game import motorpool as _mp
            vrows = db.by_type("vehicles")
            for cid in ("core:rvr_lrv", "core:rvr_press"):
                row = vrows.get(cid)
                if row is None:
                    continue
                dry = float(row.get("dry_t", 1.0))
                ok_b, why_b = _mp.can_build(home, dry)
                bill = _mp.build_bill_t(dry)
                if ok_b:
                    opts.append((("mp_build", cid),
                                 f"MOTOR POOL: BUILD {row.get('name', cid).upper()}   "
                                 f"({bill['MachineParts']:.2f} t MachParts"
                                 f" + {bill['Electronics']:.2f} t Elec)"))
                else:
                    opts.append((("mp_no", why_b),
                                 f"MOTOR POOL: {row.get('name', cid).upper()}"
                                 f"   [{why_b}]"))
    else:
        body = av.tree.body(av.frame_id)
        g_local = body.mu / (body.radius ** 2)
        m_now = av.vessel.total_mass_kg()
        twr_local = (av.vessel.active_thrust_n() / (m_now * g_local)
                     if m_now > 0.0 else 0.0)
        for sid, s in sites_for_body(av.frame_id):
            need = s.get("requires_part")
            missing = (need and not any(r.part_id == need
                                        for r in av.vessel.rows))
            label = f"LAND: {s['name']}   (~{s['land_dv']:,.0f} m/s, flown)"
            if missing:
                label += f"   [needs {need.split(':')[1]}]"
            elif not s.get("aero") and twr_local < 2.0:
                label += f"   [TWR {twr_local:.1f} — braking may not stop you]"
            opts.append((("land", sid), label))
    return opts


class BaseSite:
    """A founded surface base: a live ledger network advanced to sim time
    every frame (warp-exact by construction), failures pre-rolled, repairs
    on a maintenance turnaround that resident ENGINEERS shorten. Bases now
    have residents, a bounded event log, day/night power scheduling, and
    player-toggleable modules."""

    REPAIR_TURNAROUND = 48.0 * 3_600.0
    LOG_CAP = 200
    DAY_HORIZON = 365.25 * 86_400.0

    def __init__(self, name: str, t_founded: float, rng,
                 site_id: str = "site:peary") -> None:
        self.site_id = site_id
        self._init_net(name, t_founded, rng)
        self._schedule_daynight(t_founded)

    def _init_net(self, name: str, t_founded: float, rng) -> None:
        from aphelion.game.basebuild import starter_network
        self.name = name
        self.last_t = t_founded
        self.events: list = []
        self.pending_repairs: list[tuple[float, str]] = []
        self.pending_commission: list[tuple[float, str]] = []
        self.built: list[str] = ["solar_array"]
        self.crew: list[str] = []
        self.cond: dict[str, float] = {}      # F-7 condition per module
        self.day_sched_until = t_founded
        self.day_anchor = t_founded
        self.net = starter_network(SITES[self.site_id], rng=rng)

    # -- residents ------------------------------------------------------------
    def beds(self) -> int:
        from aphelion.game.basebuild import CATALOG
        return sum(CATALOG[k].get("beds", 0) for k in self.built)

    def engineer_skill(self, crew_db: dict) -> int:
        return max((crew_db[n].skill for n in self.crew
                    if n in crew_db and crew_db[n].role == "engineer"),
                   default=0)

    def robots(self) -> int:
        from aphelion.game.basebuild import CATALOG
        return sum(1 for k in self.built if CATALOG[k].get("robot"))

    def apply_crew_effects(self, crew_db: dict, a3: bool = False) -> None:
        """Resident engineers raise legacy producers' labor factor; 05
        fab modules instead draw on the REAL site labor pool — 8 crew-h
        per resident-day, 8 robot-h per robot (24 × 0.35 once supervised
        autonomy is researched), crew leftovers substituting for robots
        but never the reverse (05 §2)."""
        from aphelion.game.basebuild import CATALOG
        from aphelion.sim.industry.labor import a3_output_h_day, f_labor
        f_eng = 1.0 + 0.05 * self.engineer_skill(crew_db)
        crew_h = 8.0 * len(self.crew)
        robot_h = (a3_output_h_day() if a3 else 8.0) * self.robots()
        fabs = []
        crew_req = robot_req = 0.0
        for m in self.net.modules:
            spec = CATALOG.get(m.module_id.rsplit("_", 1)[0], {})
            lab = spec.get("labor_day")
            if lab and m.rate_kgps > 0.0:
                fabs.append(m)
                crew_req += lab[0]
                robot_req += lab[1]
            elif m.rate_kgps > 0.0:
                m.f_labor = f_eng
        if fabs:
            f_pool = f_labor(crew_req, robot_req, crew_h, robot_h)
            for m in fabs:
                m.f_labor = f_pool

    def repair_turnaround(self, crew_db: dict) -> float:
        return self.REPAIR_TURNAROUND / (
            1.0 + 0.25 * self.engineer_skill(crew_db))

    # -- spares economy (05 §3.4): parts-costed repairs, PM, RX-22 ---------
    def _debit_parts(self, cost_kg: dict) -> bool:
        """All-or-nothing parts draw from STORAGE (never inline from
        production buffers — §8's closed-chain rule is moot here because
        buffers ARE the site storage)."""
        for res, kg in cost_kg.items():
            buf = self.net.buffers.get(res)
            if buf is None or buf.level < kg:
                return False
        for res, kg in cost_kg.items():
            self.net.buffers[res].level -= kg
            self._reclaim(res, kg)
        return True

    def _reclaim(self, res: str, kg: float) -> None:
        """RX-22 (DECISIONS B16): with a live recycler on site, 80% of a
        consumed part's mass returns as canonical resources, 20% as
        Regolith. Electronics scrap reclaims only metal fractions."""
        from aphelion.game.basebuild import RECLAIM_SPLIT
        if not any(m.module_id.startswith("recycler")
                   and m.state not in ("FAILED", "OFF")
                   for m in self.net.modules):
            return
        for out, frac in RECLAIM_SPLIT.get(res, {}).items():
            buf = self.net.buffers.get(out)
            if buf is not None:
                buf.level = min(buf.capacity, buf.level + kg * frac)
        reg = self.net.buffers.get("Regolith")
        if reg is not None:
            reg.level = min(reg.capacity, reg.level + kg * 0.2)

    def _repair_parts_roll(self, mod, due: tuple) -> tuple[bool, dict]:
        """F-8 severity at repair time: minor 95% = 0.1% module mass in
        parts, major 5% = 1.0%, split per the §4.6 row — deterministic
        per (site, module, failure instant). Legacy modules without a
        maint row keep free repairs."""
        import zlib

        import numpy as np

        from aphelion.game.basebuild import CATALOG
        from aphelion.sim.industry.wear import MAINT, roll_failure
        spec = CATALOG.get(mod.module_id.rsplit("_", 1)[0], {})
        mk = spec.get("maint")
        if not mk:
            return True, {}
        seed = (zlib.crc32(f"{self.name}|{mod.module_id}".encode())
                ^ int(due[0])) & 0x7FFFFFFF
        roll = roll_failure(np.random.default_rng(seed),
                            spec.get("mass_t", 5.0), MAINT[mk].split)
        cost_kg = {r: t * 1_000.0 for r, t in roll["parts"].items()}
        return self._debit_parts(cost_kg), cost_kg

    def step_wear(self, hours: float, dusty: bool) -> list[str]:
        """F-7: RUNNING fab modules wear toward DEGRADED; auto-PM fires
        below C 0.55 when the §4.6 parts are in storage (+0.25, capped).
        f_condition follows F-1 (full rate to 0.5, then C/0.5)."""
        from aphelion.game.basebuild import CATALOG
        from aphelion.sim.industry.chains import f_condition
        from aphelion.sim.industry.wear import MAINT, after_pm, wear_dc
        notes = []
        for m in self.net.modules:
            spec = CATALOG.get(m.module_id.rsplit("_", 1)[0], {})
            mk = spec.get("maint")
            if not mk:
                continue
            row = MAINT[mk]
            c = self.cond.get(m.module_id, 1.0)
            if m.state == "RUNNING":
                c -= wear_dc(1.0, hours, row.l_wear_h, dust=dusty)
            if c <= 0.55:
                cost_kg = {r: v * 1_000.0 for r, v in row.pm_cost.items()
                           if r not in ("crew_h", "robot_h")}
                if self._debit_parts(cost_kg):
                    c = after_pm(c)
                    notes.append(f"{self.name}: PM on {m.module_id} "
                                 f"(C back to {c:.2f})")
            was = self.cond.get(m.module_id, 1.0)
            if was > 0.5 >= c:
                notes.append(f"{self.name}: {m.module_id} DEGRADED — "
                             f"throughput falling (PM parts short?)")
            c = max(0.0, c)
            self.cond[m.module_id] = c
            m.f_condition = f_condition(c)
        return notes

    # -- power scheduling -------------------------------------------------
    def _schedule_daynight(self, t0: float) -> None:
        from aphelion.sim.power import schedule_day_night
        day_s = SITES[self.site_id].get("day_s")
        if not day_s:
            self.day_sched_until = t0 + self.DAY_HORIZON * 100.0
            return
        arrays = [m.module_id for m in self.net.modules
                  if m.module_id.startswith("solar_array")]
        if arrays:
            schedule_day_night(self.net, arrays, t0, day_s,
                               self.DAY_HORIZON)
        self.day_sched_until = t0 + self.DAY_HORIZON

    def daylight(self, t: float) -> float:
        """1.0 in day, 0.0 in night (terminator phase for the scene sky)."""
        day_s = SITES[self.site_id].get("day_s")
        if not day_s:
            return 1.0
        phase = ((t - self.day_anchor) % day_s) / day_s
        return 1.0 if phase < 0.5 else 0.0

    # -- alerts / inspection ----------------------------------------------
    def alert(self, t: float) -> str | None:
        """Highest-severity standing problem, or None."""
        for m in self.net.modules:
            if m.state == "FAILED":
                return f"{m.module_id} FAILED"
        _, rates, f_power = self.net.solve_rates()
        if f_power < 0.999:
            return f"POWER DEFICIT (f={f_power:.2f})"
        for res, buf in self.net.buffers.items():
            rate = rates.get(res, 0.0)
            if rate < 0.0 and buf.level > 0.0:
                eta = buf.level / -rate
                if eta < 48.0 * 3_600.0:
                    return f"{res} EMPTY in {eta / 3_600.0:,.0f} h"
        return None

    def toggle_module(self, module_id: str, t: float) -> str:
        self.advance(t)
        for m in self.net.modules:
            if m.module_id == module_id:
                if m.state == "OFF":
                    m.state = "RUNNING"
                    return f"{module_id} ONLINE"
                if m.state in ("RUNNING", "STARVED", "BLOCKED"):
                    m.state = "OFF"
                    return f"{module_id} shut down"
                return f"{module_id} is FAILED — repair bot en route"
        return "module not found"

    def build(self, key: str, t: float, research, program) -> tuple[bool, str]:
        """Buy and install a module from the base catalog. ISRU-built
        structures consume LOCAL materials and commission after a real
        Deploy->Outfit->Commission schedule (07 §2.3)."""
        from aphelion.game.basebuild import CATALOG, add_module
        spec = CATALOG[key]
        if spec["tech"] and spec["tech"] not in research.unlocked:
            return False, f"{spec['name']} needs research: {spec['tech'].split(':')[1]}"
        pair_v = {"fab_wafer_fab", "mass_driver"}
        if key in pair_v and (pair_v - {key}) & set(self.built):
            return False, ("vibration: a wafer fab cannot share a site "
                           "with a mass driver (05 §3.2)")
        self.advance(t)                       # settle the ledger first
        mats = spec.get("build_materials", {})
        missing = [(r, kg) for r, kg in mats.items()
                   if self.net.buffers.get(r) is None
                   or self.net.buffers[r].level < kg]
        if missing:
            need = ", ".join(f"{kg / 1e3:,.1f} t {r}" for r, kg in missing)
            return False, f"needs local materials: {need}"
        cost = spec["price_m"] * 1e6
        if not program.spend(t, cost, f"base module {key}"):
            return False, f"insufficient funds (${spec['price_m']:,.0f}M)"
        for r, kg in mats.items():
            self.net.buffers[r].level -= kg
        mod = add_module(self.net, key, SITES[self.site_id],
                         serial=len(self.built))
        self.built.append(key)
        if key == "solar_array" and SITES[self.site_id].get("day_s"):
            from aphelion.sim.power import schedule_day_night
            schedule_day_night(self.net, [mod.module_id], t,
                               SITES[self.site_id]["day_s"],
                               max(self.day_sched_until - t, 86_400.0))
        days = spec.get("build_days", 0.0)
        if days > 0.0:
            mod.state = "OFF"                 # deploying, not yet online
            self.pending_commission.append(
                (t + days * 86_400.0, mod.module_id))
            used = ("  using " + ", ".join(f"{kg / 1e3:,.1f}t {r}"
                                           for r, kg in mats.items())
                    if mats else "")
            return True, (f"{spec['name']} DEPLOYING — commissions in "
                          f"{days:.0f} d{used} (${spec['price_m']:,.0f}M)")
        return True, f"{spec['name']} ONLINE (${spec['price_m']:,.0f}M)"

    @classmethod
    def from_restore(cls, name: str, last_t: float,
                     pending_repairs: list, net,
                     site_id: str = "site:peary",
                     built: list[str] | None = None,
                     crew: list[str] | None = None,
                     pending_commission: list | None = None,
                     cond: dict | None = None) -> "BaseSite":
        site = cls.__new__(cls)
        site.site_id = site_id
        site.built = list(built or ["solar_array"])
        site.crew = list(crew or [])
        site.name = name
        site.last_t = last_t
        site.events = []
        site.pending_repairs = list(pending_repairs)
        site.pending_commission = [tuple(c) for c in
                                   (pending_commission or [])]
        site.cond = dict(cond or {})
        site.net = net
        site.day_sched_until = last_t
        site.day_anchor = last_t
        site._schedule_daynight(last_t)   # boundaries are not serialized
        return site

    def advance(self, t: float, crew_db: dict | None = None) -> list:
        from aphelion.sim.ledger.network import LedgerEvent
        if t > self.day_sched_until - 30.0 * 86_400.0:
            self._schedule_daynight(self.day_sched_until)
        turnaround = (self.repair_turnaround(crew_db)
                      if crew_db is not None else self.REPAIR_TURNAROUND)
        new_events = []
        guard = 0
        while self.last_t < t - 1e-6 and guard < 600:
            guard += 1
            self.net.roll_failures(self.last_t)
            t_rep = min((r[0] for r in self.pending_repairs), default=float("inf"))
            t_com = min((c[0] for c in self.pending_commission),
                        default=float("inf"))
            # clamp at the next PRE-ROLLED failure too (13 §3.9: fates are
            # knowable) — else a long span strands its repairs forever
            t_fail = min((m.failure_t for m in self.net.modules
                          if m.failure_t is not None
                          and m.failure_t > self.last_t + 1e-6),
                         default=float("inf"))
            t_stop = min(t, t_rep, t_fail + 1.0, t_com)
            evs = self.net.advance(self.last_t, t_stop)
            new_events.extend(evs)
            for e in evs:
                if e.kind == "module_failed":
                    self.pending_repairs.append(
                        (e.t + turnaround, e.subject))
            if t_rep <= t_stop + 1e-6:
                due = min(self.pending_repairs)
                self.pending_repairs.remove(due)
                mod = [m for m in self.net.modules if m.module_id == due[1]][0]
                ok_parts, cost_kg = self._repair_parts_roll(mod, due)
                if ok_parts:
                    self.net.repair(mod, due[0])
                    new_events.append(LedgerEvent(due[0], "repaired", due[1]))
                else:
                    # no spares in storage: the module stays down and the
                    # crew re-checks the shelves tomorrow (05 §8)
                    self.pending_repairs.append((due[0] + 86_400.0, due[1]))
                    need = ", ".join(f"{kg:,.0f} kg {r}"
                                     for r, kg in cost_kg.items())
                    new_events.append(LedgerEvent(
                        due[0], "awaiting_parts", f"{due[1]} ({need})"))
            if t_com <= t_stop + 1e-6:
                due_c = min(self.pending_commission)
                self.pending_commission.remove(due_c)
                for m in self.net.modules:
                    if m.module_id == due_c[1] and m.state == "OFF":
                        m.state = "RUNNING"
                        new_events.append(
                            LedgerEvent(due_c[0], "commissioned",
                                        due_c[1]))
            self.last_t = t_stop
        self.events.extend(new_events)
        if len(self.events) > self.LOG_CAP:       # bounded log
            del self.events[:len(self.events) - self.LOG_CAP]
        return new_events


class Builder:
    """The Engineer screen (12 §5.4 / 06 §3): a real VAB. Categorized,
    filterable catalog with a stats card; a stack you can edit ANYWHERE
    (cursor, insert, remove, reorder, split); per-part pricing from
    sim.economy; crew assignment before launch; the flown ascent after."""

    CATS = ("ALL", "engine", "tank", "crew", "structure")
    CAT_LABELS = {"engine": "ENGINES", "tank": "TANKS",
                  "crew": "CREW & PAYLOAD", "structure": "STRUCTURE"}

    def __init__(self, db, research) -> None:
        self.db = db
        self.research = research
        self.filter_idx = 0
        self.focus = "catalog"                # or "stack"
        self.stack: list[list[str]] = [[]]    # stages, bottom first
        self.stack_cursor = 0                 # index into flat()
        self.cursor = 0                       # index into entries
        self.crew_pick: list[str] = []
        self.assign_open = False
        self.assign_cursor = 0
        self.message = "assemble a vessel from the catalog, then L to launch it"
        self._rebuild()

    # -- catalog ---------------------------------------------------------
    def _rebuild(self) -> None:
        want = self.CATS[self.filter_idx]
        entries: list[tuple[str, str]] = []
        for ty in ("engine", "tank", "crew", "structure"):
            if want != "ALL" and ty != want:
                continue
            pids = sorted((pid for pid, p in self.db.parts.items()
                           if p["type"] == ty),
                          key=lambda i: (self.db.parts[i]["tier"],
                                         self.db.parts[i]["name"]))
            if pids:
                entries.append(("header", self.CAT_LABELS[ty]))
                entries.extend(("part", pid) for pid in pids)
        self.entries = entries
        self.catalog = [pid for kind, pid in entries if kind == "part"]
        self.cursor = min(self.cursor, max(0, len(entries) - 1))
        if entries and entries[self.cursor][0] == "header":
            self.move_cursor(+1)

    def move_cursor(self, delta: int) -> None:
        if not self.entries:
            return
        i = self.cursor
        for _ in range(len(self.entries)):
            i = (i + delta) % len(self.entries)
            if self.entries[i][0] == "part":
                self.cursor = i
                return

    def cycle_filter(self, delta: int) -> None:
        self.filter_idx = (self.filter_idx + delta) % len(self.CATS)
        self.cursor = 0
        self._rebuild()

    @property
    def selected_pid(self) -> str | None:
        if self.entries and self.entries[self.cursor][0] == "part":
            return self.entries[self.cursor][1]
        return None

    def select(self, pid: str) -> bool:
        for i, (kind, payload) in enumerate(self.entries):
            if kind == "part" and payload == pid:
                self.cursor = i
                return True
        return False

    def locked(self, part_id: str) -> bool:
        return not self.research.part_available(self.db, part_id)

    # -- stack editing ----------------------------------------------------
    def flat(self) -> list[tuple[int, int, str]]:
        """Flattened (stage_idx, part_idx, pid) rows, bottom stage first."""
        return [(si, pi, pid)
                for si, stage in enumerate(self.stack)
                for pi, pid in enumerate(stage)]

    def add(self) -> None:
        pid = self.selected_pid
        if pid is None:
            return
        if self.locked(pid):
            self.message = f"{pid.split(':')[1]} is research-locked"
            return
        rows = self.flat()
        if self.focus == "stack" and rows:
            si, pi, _ = rows[min(self.stack_cursor, len(rows) - 1)]
            self.stack[si].insert(pi + 1, pid)
            self.stack_cursor = self.flat().index((si, pi + 1, pid))
        else:
            self.stack[-1].append(pid)
        self.message = f"added {pid.split(':')[1]}"

    def remove(self) -> None:
        rows = self.flat()
        if self.focus == "stack" and rows:
            si, pi, pid = rows[min(self.stack_cursor, len(rows) - 1)]
            self.stack[si].pop(pi)
            if not self.stack[si] and len(self.stack) > 1:
                self.stack.pop(si)
            self.stack_cursor = max(0, min(self.stack_cursor,
                                           len(self.flat()) - 1))
            self.message = f"removed {pid.split(':')[1]}"
        elif self.stack[-1]:
            self.stack[-1].pop()
        elif len(self.stack) > 1:
            self.stack.pop()

    def move_part(self, delta: int) -> None:
        """Shift the highlighted part up/down, across stage boundaries."""
        rows = self.flat()
        if not rows:
            return
        si, pi, pid = rows[min(self.stack_cursor, len(rows) - 1)]
        if 0 <= pi + delta < len(self.stack[si]):
            stage = self.stack[si]
            stage[pi], stage[pi + delta] = stage[pi + delta], stage[pi]
        elif 0 <= si + delta < len(self.stack):
            self.stack[si].pop(pi)
            tgt = self.stack[si + delta]
            tgt.insert(len(tgt) if delta < 0 else 0, pid)
            if not self.stack[si] and len(self.stack) > 1:
                self.stack.pop(si)
        else:
            return
        for i, row in enumerate(self.flat()):
            if row[2] == pid and (row[0] != si or row[1] != pi):
                self.stack_cursor = i
                break

    def split_stage(self) -> None:
        """Split the highlighted part's stage at the cursor (it and parts
        above it become a new upper stage)."""
        rows = self.flat()
        if not rows:
            return
        si, pi, _ = rows[min(self.stack_cursor, len(rows) - 1)]
        if pi == 0:
            self.message = "already a stage boundary"
            return
        stage = self.stack[si]
        self.stack[si] = stage[:pi]
        self.stack.insert(si + 1, stage[pi:])
        self.message = f"stage split — now {len(self.stack)} stages"

    def new_stage(self) -> None:
        if self.stack[-1]:
            self.stack.append([])

    def load_stack(self, stack) -> bool:
        """Restore a blueprint/saved stack, dropping unknown part ids."""
        clean = [[pid for pid in stage if pid in self.db.parts]
                 for stage in stack]
        clean = [s for s in clean if s] or [[]]
        self.stack = clean
        self.stack_cursor = 0
        return True

    # -- vessel & money ---------------------------------------------------
    def crew_capacity(self) -> int:
        return sum(int(self.db.parts[pid].get("crew", {}).get("capacity", 0))
                   for stage in self.stack for pid in stage)

    def build_vessel(self):
        from aphelion.sim.vessels.vessel import Vessel
        rows = []
        plan = []
        for stage in self.stack:
            idxs = []
            for pid in stage:
                idxs.append(len(rows))
                rows.append(Vessel.fueled_row(self.db, pid))
            if idxs:
                plan.append(idxs)
        if not plan:
            return None
        from aphelion.render.vessel_art import vessel_frontal_area
        return Vessel(self.db, rows, stage_plan=plan,
                      cd_a_m2=vessel_frontal_area(self.db, self.stack))

    def part_cost(self, pid: str) -> float:
        from aphelion.sim.economy import part_cost_usd
        return part_cost_usd(self.db.parts[pid])

    def price(self, vessel) -> float:
        from aphelion.sim.economy import vessel_cost_usd
        return vessel_cost_usd(vessel)


def run(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="aphelion")
    parser.add_argument("--frames", type=int, default=0)
    parser.add_argument("--screenshot", type=str, default="")
    parser.add_argument("--headless", action="store_true")
    parser.add_argument("--no-gl", action="store_true",
                        help="disable the GPU post pass (CPU renderer)")
    parser.add_argument("--perf", action="store_true",
                        help="QA: print PERF work-ms stats on exit")
    parser.add_argument("--warp", type=int, default=0,
                        help="QA: boot at this warp-ladder index")
    parser.add_argument("--zoom", type=float, default=1.0,
                        help="QA: zoom the boot camera OUT by this factor")
    parser.add_argument("--scene", type=str, default="auto",
                        choices=["auto", "menu", "flight", "builder", "base",
                                 "research", "research_ed", "research_codex",
                                 "ascent", "descent", "eva", "mine",
                                 "drive", "dive",
                                 "drydock", "proxops", "aboard", "help",
                                 "contracts", "crew", "pause", "planner",
                                 "comms"])
    args = parser.parse_args(argv)
    if args.headless:
        os.environ["SDL_VIDEODRIVER"] = "dummy"
        os.environ["SDL_AUDIODRIVER"] = "dummy"

    import numpy as np
    import pygame
    from aphelion.render.base_art import (
        module_sprite, sky_strip, terrain_strip, walker_sprite)
    from aphelion.render.body_art import body_sprite, marker_dot, sun_sprite
    from aphelion.sim.power import thermal_balance_kw
    from aphelion.render.draw_conics import draw_conic
    from aphelion.render.postfx import (Bloom, Nebula, soi_ring, sun_streak,
                                        vignette)
    from aphelion.render.surface_art import (
        PAD_GROUND_Y, PAD_W, RIDGE_PAD, ground_palette, ground_strip,
        pad_complex, ridge_layers, sky_surface)
    from aphelion.render.vessel_art import (
        app_icon, craft_icon, part_thumb, vessel_metrics, vessel_sprite)
    from aphelion.sim.environment.atmosphere import density as atmo_density
    from aphelion.sim.flight.ascent_live import LiveAscent
    from aphelion.sim.flight.descent_live import LiveDescent
    from aphelion.sim.flight.entry import fly_entry
    from aphelion.sim.flight.proxops_live import (
        CAPTURE_RANGE_M, CAPTURE_SPEED_MS, CONTACT_RANGE_M, PULSE_FINE_MS,
        ProxOps)
    from aphelion.ui import theme
    from aphelion.ui.audio import AudioCues
    from aphelion.ui.effects import Particles, Starfield
    from aphelion.ui.tutorial import (first_flight_tutorial, next_rail,
                                      restore_rail)

    from aphelion.core.rng import RngRegistry
    from aphelion.game import acts as acts_mod
    from aphelion.game import alerts as alerts_mod
    from aphelion.game.crew import (
        CrewMember, apply_crew_bonuses, best_skill, candidates,
        morale_target, reap_over_limit, science_multiplier)
    from aphelion.sim.habitat.food import BODY_RESERVE_KCAL
    from aphelion.save.campaign import (
        default_save_dir, read_campaign, snapshot_campaign, write_campaign)
    from aphelion.sim.habitat.dose import AMBIENT_MSV_DAY

    db, tree = load_solar_system()
    planets = sorted((i for i, b in db.bodies.items() if b["parent"] == "core:sun"),
                     key=lambda i: db.bodies[i]["elements"]["a_m"])
    moons_of = {i: tree.children(i) for i in planets}

    # land ANYWHERE (03 S-7): every landable sector joins the site registry
    # so descent, founding and surface ops work across the whole system
    for _sec_id, _sec in db.by_type("sectors").items():
        if landable(_sec) and _sec["body"] in BODY_OPS:
            SITES[_sec_id] = sector_site(db, _sec_id)
    # body -> (region code, X) for orbital-survey awards; Earth prefers LEO
    ORBIT_REGION: dict[str, tuple[str, float]] = {}
    SURF_REGION: dict[str, tuple[str, float]] = {}
    for _rr in sorted(db.by_type("regions").values(),
                      key=lambda r: r["code"]):
        slot = ORBIT_REGION if _rr["kind"] == "orbit" else SURF_REGION
        slot.setdefault(_rr["body"], (_rr["code"], _rr["x"]))

    pygame.init()
    size = (1280, 720)
    fullscreen = False
    pygame.display.set_icon(app_icon())
    # F0 GPU post pass: scenes keep drawing to a plain logical-size
    # surface; the GL chain (bloom/grade/filmic) presents it. Falls back
    # to the classic SCALED window when GL is unavailable (headless QA,
    # --no-gl, exotic hardware) — presentation only, never load-bearing.
    glp = (None if args.headless or args.no_gl
           else glpost.GLPost.try_create(size, vsync=True))
    if glp is not None:
        screen = pygame.Surface(size)
    else:
        screen = pygame.display.set_mode(
            size, pygame.SCALED | pygame.DOUBLEBUF,
            vsync=0 if args.headless else 1)
    pygame.display.set_caption("APHELION")
    pygame_clock = pygame.time.Clock()
    _thf = theme.init_fonts()
    font = _thf["ui_small"]             # single labels / annotations
    font_med = _thf["ui_title"]         # banners, menu rows
    font_big = pygame.font.SysFont(theme._UI_FACE, 44, bold=True)
    nebula = Nebula(size)
    bloom = Bloom(size)
    vig = vignette(size)

    cam = Camera(*size, frame_id="core:earth", zoom=3.0e-5, layer=ZoomLayer.LOCAL)
    focus_order = (["craft", "core:sun"] + planets
                   + [m for p in planets for m in moons_of[p]])
    focus_of_body = {bid: i for i, bid in enumerate(focus_order)}
    focus_idx = 0

    starfield = Starfield(size)
    particles = Particles()
    audio = AudioCues()
    if not args.headless:
        audio.start_music()
    save_dir = default_save_dir()
    qs_path = save_dir / "quicksave.aph"
    as_path = save_dir / "autosave.aph"

    def latest_save():
        saves = sorted(save_dir.glob("*.aph"),
                       key=lambda p: p.stat().st_mtime, reverse=True)
        return saves[0] if saves else None

    def fresh_campaign(diff: str = "DIRECTOR") -> dict:
        """A brand-new 2049 campaign (12 §3: Act 1 opens with money, two
        astronauts, an empty pad — and no rocket. Build one. Contracts
        arrive from the Act table (game/campaign.py) as you earn them."""
        return dict(clock=SimClock(t0=0.0), vessels=[], active_idx=0,
                    next_vid=1,
                    program=Program(funds=_DIFFICULTIES[diff]["funds"]),
                    difficulty=diff,
                    rng=RngRegistry(20490101), bases=[],
                    crew={"V. Ainsworth": CrewMember("V. Ainsworth",
                                                     "pilot", 2),
                          "J. Okafor": CrewMember("J. Okafor",
                                                  "engineer", 1)},
                    research=_fresh_research(db), visited={"core:earth"},
                    visited_surface=set(), milestones=set(),
                    tutorial=first_flight_tutorial(),
                    explore={"investigated": set(), "surveydata_gb": 0.0,
                             "survey_progress": {}, "flags": [],
                             "dug": {}, "deposits": {}})

    def loaded_campaign(path=None) -> dict:
        got = read_campaign(path or latest_save() or qs_path, db, tree)
        tut = restore_rail(got.get("tutorial_state"))
        if got.get("tutorial_state") is None and got["tutorial_done"]:
            tut.completed = True            # pre-depth saves: rail 1 done
            tut.done_rails = {"first"}
        rng = (RngRegistry.from_state(got["rng_state"]) if got["rng_state"]
               else RngRegistry(20490101))
        for b in got["bases"]:
            b["net"].rng = rng      # resume the SAME failure streams
        for v in got["vessels"]:
            apply_crew_bonuses(v, got["crew"])
            if "core:tech_ls07_closed_loop_eclss" in got["research"].unlocked:
                v.lss_bonus *= 2.5
        ex = got.get("explore") or {}
        return dict(clock=SimClock(t0=got["t"]), vessels=got["vessels"],
                    explore={"investigated": set(ex.get("investigated", [])),
                             "surveydata_gb": ex.get("surveydata_gb", 0.0),
                             "survey_progress": dict(
                                 ex.get("survey_progress", {})),
                             "flags": list(ex.get("flags", [])),
                             "dug": {k: [list(p) for p in v] for k, v
                                     in (ex.get("dug") or {}).items()},
                             "deposits": dict(ex.get("deposits", {}))},
                    active_idx=got["active_idx"], next_vid=got["next_vid"],
                    program=got["program"], rng=rng,
                    bases=[BaseSite.from_restore(b["name"], b["last_t"],
                                                 b["pending_repairs"], b["net"],
                                                 b.get("site_id", "site:peary"),
                                                 b.get("built"),
                                                 b.get("crew"),
                                                 b.get("pending_commission"),
                                                 b.get("cond"))
                           for b in got["bases"]],
                    crew=got["crew"], research=got["research"],
                    visited=got["visited"],
                    visited_surface=got["visited_surface"],
                    milestones=got["milestones"], tutorial=tut,
                    builder_stack=got.get("builder_stack", []),
                    yard_designs=got.get("yard_designs", []),
                    ground_vehicles=got.get("ground_vehicles", []),
                    acts2=got.get("acts2") or {},
                    difficulty=got.get("difficulty", "DIRECTOR"))

    def campaign_tuple(st: dict):
        """One unpack shape for new game, quickload, and startup."""
        from aphelion.game import motorpool
        b = Builder(db, st["research"])
        if st.get("builder_stack"):
            b.load_stack(st["builder_stack"])
        return (st["clock"], st["vessels"], st["active_idx"], st["next_vid"],
                st["program"], st["rng"], st["bases"], st["crew"],
                st["research"], st["visited"], st["visited_surface"],
                st["milestones"], st["tutorial"], b,
                st.get("difficulty", "DIRECTOR"),
                st.get("explore") or {"investigated": set(),
                                      "surveydata_gb": 0.0,
                                      "survey_progress": {}, "flags": [],
                                      "dug": {}, "deposits": {}},
                list(st.get("yard_designs") or []),
                [motorpool.GroundVehicle.from_dict(d)
                 for d in (st.get("ground_vehicles") or [])],
                None, 0, False, False, False, False, False, 0.0, "", 0.0)

    (clock, vessels, active_idx, next_vid, program, campaign_rng, bases,
     crew, research, visited, visited_surface, milestones, tutorial, builder,
     difficulty, explore, yard_designs, ground_vehicles,
     node, warp_idx, paused, base_screen, builder_open, research_open,
     crew_warned, last_dose_t, toast, toast_until) = \
        campaign_tuple(fresh_campaign())

    # E wiring: the campaign meta-layer — Prestige, the Firsts ladder,
    # the Chronicle, and the program-wide alert bus (12 §1.5/§4, A-1..6)
    def restore_acts2(a2: dict | None):
        a2 = a2 or {}
        pr = (acts_mod.Prestige.from_dict(a2["prestige"])
              if a2.get("prestige") else acts_mod.Prestige())
        earned = set(a2.get("firsts", []))
        ch = (alerts_mod.Chronicle.from_dict(a2["chronicle"])
              if a2.get("chronicle") else alerts_mod.Chronicle())
        bus = (alerts_mod.AlertBus.from_dict(a2["alerts"], ch)
               if a2.get("alerts") else alerts_mod.AlertBus(ch))
        hwm = dict(a2.get("prod_hwm", {}))
        return pr, earned, ch, bus, hwm

    prestige, firsts_earned, chron, abus, prod_hwm = restore_acts2(None)

    def acts2_dict() -> dict:
        return {"prestige": prestige.to_dict(),
                "firsts": sorted(firsts_earned),
                "chronicle": chron.to_dict(),
                "alerts": abus.to_dict(),
                "prod_hwm": dict(prod_hwm)}

    def acts_snapshot() -> dict:
        """The live campaign distilled into the Firsts-ladder snapshot
        (12 §1.5). Every field derives from systems that already exist —
        nothing here is bookkept twice."""
        landed_b = {SITES[s]["body"] for s in visited_surface
                    if s in SITES}
        crewed_b = {m.split("|", 1)[1] for m in research.milestones
                    if m.startswith("crewed_landing|")}
        colonized = {SITES[b.site_id]["body"] for b in bases if b.crew}
        tier = 0
        for u in research.unlocked:
            tr_s = str(db.tech.get(u, {}).get("tier", "T0"))
            if tr_s.startswith("T") and tr_s[1:].isdigit():
                tier = max(tier, int(tr_s[1:]))
        industry = {m.module_id.rsplit("_", 1)[0]
                    for b in bases for m in b.net.modules
                    if m.state == "RUNNING"}
        vehicles = set()
        for gv in ground_vehicles:
            if gv.odo_km > 0.0 or gv.bricked_events:
                vehicles.add("submarine" if "sub" in gv.catalog_id
                             else "rover")
        return acts_mod.snapshot(
            milestones=milestones, visited=visited,
            visited_surface=visited_surface, landed=landed_b,
            crewed_landed=crewed_b, colonized=colonized, tech_tier=tier,
            industry_online=industry, vehicles_operated=vehicles,
            extracted_t=dict(prod_hwm), refined_t=dict(prod_hwm))

    def env_models(rng):
        """SPE storms + Mars weather: pure functions of the campaign seed,
        so they rebuild identically after save/load with no extra state."""
        return (SpeSchedule(rng.campaign_seed ^ 0x53504531),
                MarsWeather(rng.campaign_seed ^ 0x4D525357))

    spe_sched, mars_wx = env_models(campaign_rng)
    env_state = {"spe_warned": -1.0, "spe_capped": False, "storm_was": False}
    alerts_seen: set[int] = set()     # E wiring: alert aids already toasted
    runway_state = {"cls": 0}         # G-9 runway alert posts on worsening

    def crew_refit(fv) -> None:
        """Crew bonuses + the closed-loop ECLSS retrofit when researched
        (the tech node finally GRANTS something: 2.5x life support)."""
        apply_crew_bonuses(fv, crew)
        if "core:tech_ls07_closed_loop_eclss" in research.unlocked:
            fv.lss_bonus *= 2.5

    def surface_award(av0, sid, site, t) -> str:
        """First-arrival science at a surface: site lump, the one-shot
        region ground survey (10·X, 11 §3.1), body firsts (k·X), and the
        AeroFlight EDL event for atmosphere worlds."""
        if sid in visited_surface:
            return ""
        visited_surface.add(sid)
        sci = site["science"] * science_multiplier(av0, crew)
        research.earn_science(sci)
        body = site["body"]
        sci += research.award_milestone("landing", body, t)
        if av0.crew:
            sci += research.award_milestone("crewed_landing", body, t)
        if "region_code" in site:
            sci += research.award_survey("ground", site["region_code"],
                                         site["x"], t)
        if site.get("aero"):
            research.accrue_event(db, "AeroFlight", "aero_event",
                                  env_class="dense_atmosphere")
        return f"  +{sci:.0f} science"

    def do_quicksave(path=None, label="QUICKSAVED") -> str:
        snap = snapshot_campaign(
            t=clock.t, vessels=vessels, active_idx=active_idx,
            next_vid=next_vid, program=program, research=research,
            crew=crew, visited=visited, visited_surface=visited_surface,
            milestones=milestones, bases=bases,
            tutorial_done=tutorial.completed, rng=campaign_rng,
            builder_stack=builder.stack, difficulty=difficulty,
            yard_designs=yard_designs, ground_vehicles=ground_vehicles,
            acts2=acts2_dict(),
            tutorial_state={"rail": tutorial.rail, "index": tutorial.index,
                            "visible": tutorial.visible,
                            "done": sorted(tutorial.done_rails)},
            explore={"investigated": sorted(explore["investigated"]),
                     "surveydata_gb": explore["surveydata_gb"],
                     "survey_progress": dict(explore["survey_progress"]),
                     "flags": list(explore.get("flags", [])),
                     "dug": explore.get("dug", {}),
                     "deposits": explore.get("deposits", {})})
        write_campaign(path or qs_path, snap)
        return label

    want = args.scene
    if want == "auto":
        want = "flight" if (args.frames or args.headless) else "menu"
    scene = "menu" if want == "menu" else "flight"
    if want == "builder":
        builder_open = True
    elif want == "research":
        research_open = True
    elif want == "base":
        bases.append(BaseSite("Peary Base", 0.0, campaign_rng))
        bases[-1].crew.append("J. Okafor")     # QA: a resident for the
        base_screen = True                     # humans-v2 hourly path
    boot_ascent = want == "ascent"
    if args.warp:
        warp_idx = min(args.warp, len(_WARP_LADDER) - 1)

    menu_cursor = 0
    menu_mode = "main"
    menu_rects: list = []
    pause_open = False
    pause_cursor = 0
    research_cursor = 0
    research_view = "tree"            # tree | ed (data dashboard) | codex
    eva_state = None                  # EvaState while walking the surface
    eva_av = None                     # the landed vessel the walker left
    eva_tiles = None                  # the sector's TileWorld (S-7c)
    eva_tr = None                     # its chunk renderer
    eva_dig = None                    # held-dig progress {tile, left, total}
    eva_camy = 0.0                    # vertical camera follow, metres
    EVA_TIME_FACTOR = 30.0            # EVA ops run at 30x sim time
    interior_x = 2.0                  # walker x inside the hab strip, m
    interior_home = None              # the BaseSite whose interior we walk
    interior_vessel = None            # ... or the flying stack we board (T)
    interior_rooms: tuple = ()        # habitable module keys, build order
    interior_labels: tuple = ()       # vessel mode: (part name, info) rows
    interior_return_x = 0.0           # where on the surface we re-emerge
    interior_face = 1                 # walker sprite facing/animation
    interior_frame = 0.0
    # Drydock 2.0 (06): the grid design room
    dd_v = GridVessel()
    dd_cursor = [4, 0]
    dd_cat_classes = ("ALL", "ENGINE", "TANK", "STRUCT", "HAB", "ELEC",
                      "MECH", "SHIELD")
    dd_class_idx = 0
    dd_cat_idx = 0
    dd_mode = "vac"                   # readout Isp law: vac | sl | traj
    dd_sim = None                     # last pre-flight ascent sim
    dd_move_cd = 0.0
    dd_err_idx = 0
    dd_msg = "place parts — the readouts are live"

    def dd_catalog():
        cls = dd_cat_classes[dd_class_idx]
        rows = [(pid, p) for pid, p in db.by_type("parts").items()
                if "size" in p]
        if cls != "ALL":
            rows = [(pid, p) for pid, p in rows
                    if p.get("class") == cls]
        rows.sort(key=lambda kv: (kv[1].get("class", ""),
                                  kv[1].get("tier", ""),
                                  kv[1].get("catalog_id", "")))
        return rows
    surface_open = False
    surface_cursor = 0
    base_cursor = 0
    base_idx = 0
    crew_open = False
    crew_cursor = 0
    crew_focus = "cands"              # or "roster" (training)
    roster_cursor = 0
    help_open = False
    station_open = False              # F7: spin/keeping/depot ops
    # map intelligence: target, transfer planner, warp-to-node
    target_id: str | None = None
    planner_open = False
    planner_cursor = 0
    warp_to_node = False
    ca_cache = {"at": -1e9, "tgt": None, "d": None, "t": 0.0}
    # O wiring: corridor advisor verdicts, recomputed at most hourly per
    # encounter (the bisection runs ~25 fly_entry passes — never per frame)
    corridor_cache = {"key": None, "lines": []}
    net_overlay = False               # C wiring: J toggles the comms map
    # V5 dive scene state (Titan seas)
    dive_gv = None
    dive_av = None
    dive_x = 200.0                    # m along the sea section
    dive_depth = 0.0
    dive_vx = 0.0
    dive_vz = 0.0
    dive_face = 1
    dive_warn_t = -1e9
    dive_painted: set = set()         # sonar-mapped 50 m cells (DSC-14)
    dive_ping_t = -1e9
    dive_bg_cache: dict = {}
    dive_sea: list = []               # live sealife entities (transient)
    dive_sea_cells: set = set()       # ecology cells already populated
    dive_uv = False                   # UV lamp (Tier-1 mats fluoresce)
    # V5 drive scene state
    drive_gv = None                   # GroundVehicle at the wheel
    drive_av = None                   # the landed vessel anchoring the site
    drive_v = 0.0                     # m/s, signed
    drive_x = 26.0                    # m along the site cross-section
    drive_face = 1
    drive_tiles = None
    drive_tr = None
    drive_camy = 0.0
    drive_stuck = 0.0
    drive_attempts = 0
    drive_warn_t = -1e9
    drive_eta = 1.0                   # L-13 teleop efficiency (1 = crewed)
    # colony scene state
    base_focus = "construct"          # or "modules"
    module_cursor = 0
    base_log_open = False
    # tutorial latches + contracts ledger overlay
    node_exec_seen = False
    prox_seen = False
    contracts_open = False
    contracts_scroll = 0
    if want == "help":                  # QA hooks: overlay screenshots
        help_open = True
    elif want == "contracts":
        contracts_open = True
    elif want == "crew":
        crew_open = True
    elif want in ("planner", "comms"):  # QA: a stack in LEO so rows quote
        from aphelion.sim.vessels.vessel import Vessel as _V
        _rows = [_V.fueled_row(db, "core:engine_ml111"),
                 _V.fueled_row(db, "core:tank_ml_s"),
                 _V.fueled_row(db, "core:capsule_vela")]
        _bq = tree.body("core:earth")
        _rq = _bq.radius + 300e3
        _el = state_to_elements(_rq, 0.0, 0.0,
                                tr.circular_speed(_bq.mu, _rq), 0.0, _bq.mu)
        vessels.append(FleetVessel(tree, "core:earth", _el,
                                   _V(db, _rows, stage_plan=[[0, 1, 2]]),
                                   "PLANNER-QA" if want == "planner"
                                   else "RELAY-QA", next_vid))
        next_vid += 1
        active_idx = len(vessels) - 1
        if want == "planner":
            planner_open = True
        else:
            net_overlay = True
    elif want == "pause":
        pause_open = True
    elif want == "research_ed":
        research_open, research_view = True, "ed"
    elif want == "research_codex":
        research_open, research_view = True, "codex"
    elif want in ("eva", "mine"):       # QA: a walker on the lunar pole
        from aphelion.sim.vessels.vessel import Vessel as _V
        _rows = [_V.fueled_row(db, "core:engine_ml111"),
                 _V.fueled_row(db, "core:tank_ml_s"),
                 _V.fueled_row(db, "core:capsule_vela")]
        _bq = tree.body("core:moon")
        _rq = _bq.radius + 100e3
        _el = state_to_elements(_rq, 0.0, 0.0,
                                tr.circular_speed(_bq.mu, _rq), 0.0, _bq.mu)
        _fvq = FleetVessel(tree, "core:moon", _el,
                           _V(db, _rows, stage_plan=[[0, 1, 2]]),
                           "EVA-QA", next_vid, crew=["V. Ainsworth"])
        next_vid += 1
        _fvq.land_at("site:peary", SITES["site:peary"], 0.0)
        vessels.append(_fvq)
        eva_av = _fvq
        _secq = SITES["site:peary"].get("sector_id", "site:peary")
        eva_tiles = tileworld.TileWorld(
            _secq, 8.0, SITES["site:peary"].get("kind", "psr_ice"),
            dug=explore.setdefault("dug", {}).get(_secq, []))
        eva_tr = TileRenderer(eva_tiles,
                              ground_palette(SITES["site:peary"]["body"]))
        eva_state = eva_sim.EvaState(
            _secq, 8.0, _bq.mu / _bq.radius ** 2, "V. Ainsworth",
            tiles=eva_tiles)
        if want == "mine":              # QA: a shaft + gallery, lamp on
            _mx = 18.0
            for _ in range(16):
                eva_tiles.dig(_mx, eva_tiles.surface_y(_mx) - 0.25)
            _fy = eva_tiles.surface_y(_mx)
            for _k in range(1, 9):
                for _h in (0.3, 0.8, 1.3, 1.8):
                    eva_tiles.dig(_mx + _k * 0.5, _fy + _h)
            explore["dug"][_secq] = eva_tiles.dug_list()
            eva_state.x = _mx + 2.5     # inside the gallery: lamp on
            eva_state.y = eva_tiles.ground_below(_mx + 2.5, _fy + 1.0)
            eva_camy = eva_state.y
        scene = "eva"
    elif want == "drive":               # QA: an LRV parked at Peary
        from aphelion.sim.vessels.vessel import Vessel as _V
        _rows = [_V.fueled_row(db, "core:engine_ml111"),
                 _V.fueled_row(db, "core:tank_ml_s"),
                 _V.fueled_row(db, "core:capsule_vela")]
        _bq = tree.body("core:moon")
        _rq = _bq.radius + 100e3
        _el = state_to_elements(_rq, 0.0, 0.0,
                                tr.circular_speed(_bq.mu, _rq), 0.0, _bq.mu)
        _fvq = FleetVessel(tree, "core:moon", _el,
                           _V(db, _rows, stage_plan=[[0, 1, 2]]),
                           "DRIVE-QA", next_vid, crew=["V. Ainsworth"])
        next_vid += 1
        _fvq.land_at("site:peary", SITES["site:peary"], 0.0)
        vessels.append(_fvq)
        from aphelion.game import motorpool as _mpq
        drive_gv = _mpq.GroundVehicle(
            vid=900, catalog_id="core:rvr_lrv", name="LRV-QA",
            body="core:moon", site_id="site:peary", pack_kwh=8.7,
            energy_kwh=7.4, park_x_m=24.0)
        drive_gv.dry_t = 0.21
        drive_gv.cargo_t = 0.46
        ground_vehicles.append(drive_gv)
        drive_av = _fvq
        drive_x = 24.0
        scene = "drive"
    elif want == "dive":                # QA: SUB-T in a Titan sea
        from aphelion.sim.vessels.vessel import Vessel as _V
        _rows = [_V.fueled_row(db, "core:engine_ml111"),
                 _V.fueled_row(db, "core:tank_ml_s"),
                 _V.fueled_row(db, "core:capsule_vela")]
        _tsid = next((s for s, v in SITES.items()
                      if v.get("body") == "core:titan"), None) or "site:peary"
        _tb = tree.body(SITES[_tsid]["body"])
        _rq = _tb.radius + 100e3
        _el = state_to_elements(_rq, 0.0, 0.0,
                                tr.circular_speed(_tb.mu, _rq), 0.0, _tb.mu)
        _fvq = FleetVessel(tree, SITES[_tsid]["body"], _el,
                           _V(db, _rows, stage_plan=[[0, 1, 2]]),
                           "DIVE-QA", next_vid, crew=["V. Ainsworth"])
        next_vid += 1
        _fvq.land_at(_tsid, SITES[_tsid], 0.0)
        vessels.append(_fvq)
        from aphelion.game import motorpool as _mpq
        dive_gv = _mpq.GroundVehicle(
            vid=901, catalog_id="core:sub_t", name="MAKO-QA",
            body=SITES[_tsid]["body"], site_id=_tsid, pack_kwh=20.0,
            energy_kwh=18.0, rtg_we=330.0, park_x_m=20.0)
        dive_gv.dry_t = 1.5
        ground_vehicles.append(dive_gv)
        dive_av = _fvq
        dive_x = 200.0
        dive_depth = 12.0
        scene = "dive"
    elif want == "drydock":             # QA: a two-stage demo on the grid
        _ps = db.by_type("parts")
        for _pid, _px, _py in (("core:engine_m2256", 2, 0),
                               ("core:tank_ml_m", 2, 3),
                               ("core:st_fin", 1, 0),
                               ("core:st_fin", 4, 0),
                               ("core:st_dc2", 2, 7),
                               ("core:st_is3", 1, 8),
                               ("core:engine_ml24", 2, 8),
                               ("core:tank_ml_s", 2, 10),
                               ("core:capsule_vela", 2, 12)):
            dd_v.add(_pid, _ps[_pid], _px, _py)
        dd_cursor = [5, 5]
        _defs = dd_stage.to_stage_defs(dd_v)
        _r0 = stage_report(_defs, mode="sl")[0]
        dd_sim = ascent_qsim(_r0["thrust_kn"], _r0["mdot_kgps"],
                             _r0["m0_t"], _defs[0].prop_t, 4.0)
        scene = "drydock"
    autosave_acc = 0.0
    gold_flash = 0.0
    ascent_event_count = 0
    body_click_pts: list = []
    vessel_click_pts: list = []
    burn_glow = 0.0
    # overlay row hitboxes, rebuilt by each overlay's draw pass (mouse UX)
    overlay_rects: dict[str, list] = {}
    # scene fade-in + real-time toast animation (toasts must outlive warp)
    fade = 0.0
    prev_scene = ""
    ui_t = 0.0
    toast_key: tuple = ("", 0.0)
    toast_real0 = -10.0

    # film grain: 4 pre-rendered sparse luminance-noise frames, cycled —
    # one alpha blit per frame, kills the too-clean software-render look
    grain_frames: list = []
    _grng = np.random.default_rng(909)
    for _gi in range(4):
        _gs = pygame.Surface(size, pygame.SRCALPHA)
        _ga = pygame.surfarray.pixels_alpha(_gs)
        _ga[...] = (_grng.random((size[0], size[1])) ** 3 * 24).astype(np.uint8)
        del _ga
        _grgb = pygame.surfarray.pixels3d(_gs)
        _grgb[...] = 235
        del _grgb
        grain_frames.append(_gs)

    def apply_fade() -> None:
        nonlocal fade
        screen.blit(grain_frames[frame_count & 3], (0, 0))
        if perf_open and len(perf_samples) > 10:
            _rec = perf_samples[-120:]
            _avg = sum(_rec) / len(_rec)
            _p95 = sorted(_rec)[int(0.95 * (len(_rec) - 1))]
            theme.draw_text(
                screen, size[0] - 248, 4,
                f"work {_avg:5.1f} ms avg  {_p95:5.1f} p95  "
                f"({min(999.0, 1000.0 / max(_avg, 0.01)):3.0f} fps uncapped)",
                color=theme.COLORS["danger"] if _avg > 33.0
                else theme.COLORS["warn"] if _avg > 22.0
                else theme.COLORS["good"], font="small")
        if fade > 0.0:
            fs = pygame.Surface(size)
            fs.fill((4, 6, 10))
            fs.set_alpha(int(255 * min(1.0, fade)))
            screen.blit(fs, (0, 0))
            fade = max(0.0, fade - 2.6 * real_dt)

    def apply_flash() -> None:
        nonlocal flash
        if flash > 0.0:
            fl2 = pygame.Surface(size)
            fl2.fill((255, 228, 196))
            fl2.set_alpha(int(220 * min(1.0, flash)))
            screen.blit(fl2, (0, 0))
            flash = max(0.0, flash - 2.2 * real_dt)

    def present_frame() -> None:
        """The one place a finished frame reaches the player: CPU fades
        first, then either the GL post chain (graded by whichever world
        the active scene is showing) or the classic flip."""
        apply_fade()
        if glp is None:
            pygame.display.flip()
            return
        key = "default"
        try:
            if scene == "menu":
                key = "menu"
            elif scene == "interior":
                key = "interior"
            else:
                _gav = (ascent_av if scene == "ascent" else
                        descent_av if scene == "descent" else
                        eva_av if scene in ("eva", "mine") else None)
                if _gav is None and vessels:
                    _gav = vessels[active_idx % len(vessels)]
                if _gav is not None:
                    _sid = getattr(_gav, "landed_at", None)
                    key = (SITES[_sid]["body"] if _sid in SITES
                           else _gav.frame_id)
        except Exception:
            key = "default"
        glp.present(screen, key, frame_count)

    def planner_rows_for(av0, t0: float) -> list[dict]:
        """Transfer-window quotes from the active vessel's parking orbit —
        built entirely on the tested Hohmann/synodic toolkit in
        sim.orbits.transfers (which the UI never exposed until now)."""
        rows: list[dict] = []
        if av0 is None or av0.landed_at is not None:
            return rows
        origin = av0.frame_id
        if origin not in planets:
            return rows
        mu_s = tree.body("core:sun").mu
        b_o = tree.body(origin)
        r1 = b_o.elements.a
        ox, oy, _, _ = tree.state_in_root(origin, t0)
        th_o = math.atan2(oy, ox)
        crx, cry, _, _ = av0.state(t0)
        park_r = math.hypot(crx, cry)
        for pid in planets:
            if pid == origin:
                continue
            b_t = tree.body(pid)
            r2 = b_t.elements.a
            _, dv2h, _ = tr.hohmann(mu_s, r1, r2)
            tx, ty, _, _ = tree.state_in_root(pid, t0)
            phase_now = _wrap_pi(math.atan2(ty, tx) - th_o)
            wait, t_tr, _ = _transfer_window(mu_s, r1, r2, phase_now)
            vinf = tr.hohmann_departure_vinf(mu_s, r1, r2)
            dv_dep = tr.departure_dv(b_o.mu, park_r, vinf)
            dv_cap = tr.departure_dv(b_t.mu, b_t.radius + 200e3, dv2h)
            rows.append(dict(
                pid=pid, name=pid.split(":")[1], wait=wait,
                t_dep=t0 + wait, t_tr=t_tr, dv_dep=dv_dep, dv_cap=dv_cap,
                affordable=dv_dep <= av0.dv_remaining))
        return rows

    # O wiring: Lambert-refined window per planner row, cached per sim-day
    # (a refinement is ~150 Izzo solves — run on selection, never per frame)
    lam_cache: dict[tuple, dict | None] = {}

    def lambert_refined(av0, row, t0: float) -> dict | None:
        """Sharpen a planner row with a real Lambert scan (01 §2.4): the
        Hohmann quote assumes circular coplanar orbits; this scans the
        actual eccentric ephemerides around that window and returns the
        true minimum — often days off and cheaper."""
        if av0 is None or av0.landed_at is not None:
            return None
        origin = av0.frame_id
        key = (origin, row["pid"], int(t0 // SECONDS_PER_DAY))
        if key in lam_cache:
            return lam_cache[key]
        from aphelion.sim.orbits import lambert as lam
        mu_s = tree.body("core:sun").mu
        b_o, b_t = tree.body(origin), tree.body(row["pid"])
        n_o = math.sqrt(mu_s / b_o.elements.a ** 3)
        n_t = math.sqrt(mu_s / b_t.elements.a ** 3)
        syn = 2.0 * math.pi / max(abs(n_t - n_o), 1e-12)
        lo = max(t0 + 3_600.0, row["t_dep"] - 0.12 * syn)
        hi = max(row["t_dep"] + 0.12 * syn, lo + SECONDS_PER_DAY)
        out: dict | None
        try:
            t_dep, tof, _ = lam.best_window(
                mu_s, b_o.elements, b_t.elements, (lo, hi),
                (0.55 * row["t_tr"], 1.45 * row["t_tr"]), n_grid=(13, 11))
            vinf_d, vinf_a = lam.transfer_vinfs(
                mu_s, b_o.elements, b_t.elements, t_dep, tof)
            crx0, cry0, _, _ = av0.state(t0)
            park_r = math.hypot(crx0, cry0)
            out = dict(
                t_dep=t_dep, tof=tof,
                dv_dep=tr.departure_dv(b_o.mu, park_r, vinf_d),
                dv_cap=tr.departure_dv(b_t.mu, b_t.radius + 200e3,
                                       vinf_a))
        except ValueError:
            out = None
        if len(lam_cache) > 64:
            lam_cache.clear()
        lam_cache[key] = out
        return out

    # C wiring: the comms network (16 §3.1 over 13 §3.11). DSN root rides
    # Earth; every vessel mounts the integrated avionics omni (UT-AV note,
    # linkbudget §2.1) + a 0.5 m HGA when crew-rated; bases mount an
    # MRO-class 3 m dish. Rebuilt at ~2 s wall cadence, routes memoized —
    # nothing here runs per frame.
    from aphelion.sim.network import graph as netg
    from aphelion.sim.network.linkbudget import PARTS as NET_PARTS
    from aphelion.sim.vehicles.control import teleop_eta_driving

    comms_cache: dict = {"at": -1e9, "graph": None, "pos": {}, "routes": {}}

    def comms_now(t0: float) -> dict:
        if (time.time() - comms_cache["at"] < 2.0
                and comms_cache["graph"] is not None):
            return comms_cache
        bpos: dict[str, tuple[float, float]] = {}
        for bid in db.bodies:
            bx0, by0, _, _ = tree.state_in_root(bid, t0)
            bpos[bid] = (bx0, by0)
        pos: dict[str, tuple[float, float, str | None]] = {}
        nodes: list = []
        ex0, ey0 = bpos["core:earth"]
        nodes.append(netg.dsn_root((ex0, ey0)))
        pos[netg.ROOT_UID] = (ex0, ey0, "core:earth")
        for v in vessels:
            fx0, fy0 = bpos.get(v.frame_id, (0.0, 0.0))
            if v.landed_at is not None:
                # on the surface: a site-keyed bearing keeps ground links
                # at honest ground distances (never co-located)
                _r0 = tree.body(v.frame_id).radius
                _h0 = (zlib.crc32(v.landed_at.encode()) % 628) / 100.0
                x0 = fx0 + _r0 * math.cos(_h0)
                y0 = fy0 + _r0 * math.sin(_h0)
                att = v.frame_id
            else:
                lx0, ly0, _, _ = v.state(t0)
                x0, y0, att = fx0 + lx0, fy0 + ly0, None
            crewed_rated = any(db.parts[r.part_id]["type"] == "crew"
                               for r in v.vessel.rows)
            parts = (("CM-OMNI", "UT-DISH-S") if crewed_rated
                     else ("CM-OMNI",))
            uid = f"v{v.vid}"
            nodes.append(netg.CommsNode(uid, (x0, y0), parts, ("UT-AV",)))
            pos[uid] = (x0, y0, att)
        for b in bases:
            bid = SITES[b.site_id]["body"]
            bx0, by0 = bpos.get(bid, (0.0, 0.0))
            _r0 = tree.body(bid).radius
            _h0 = (zlib.crc32(b.site_id.encode()) % 628) / 100.0
            uid = f"base:{b.name}"
            nodes.append(netg.CommsNode(
                uid, (bx0 + _r0 * math.cos(_h0),
                      by0 + _r0 * math.sin(_h0)),
                ("UT-DISH-M",), ("UT-AV",), kind="base"))
            pos[uid] = (bx0 + _r0 * math.cos(_h0),
                        by0 + _r0 * math.sin(_h0), bid)
        occ = [(bid, bpos[bid], tree.body(bid).radius)
               for bid in bpos if bid != "core:sun"]
        sx0, sy0 = bpos["core:sun"]

        def los(a_uid: str, b_uid: str) -> bool:
            ax0, ay0, abody = pos[a_uid]
            bx1, by1, bbody = pos[b_uid]
            for bid, (cx0, cy0), r0 in occ:
                if bid == abody or bid == bbody:
                    continue            # attached body: availability rules
                if _seg_blocked(ax0, ay0, bx1, by1, cx0, cy0, r0):
                    return False
            return True

        def env(tx_uid: str, rx_uid: str):
            # L-7 solar conjunction: separation (peer vs Sun) at the RX
            # endpoint; local links (< 0.1 AU) never graze the corona
            rxx, rxy, _ = pos[rx_uid]
            txx, txy, _ = pos[tx_uid]
            v2x, v2y = txx - rxx, txy - rxy
            n2 = math.hypot(v2x, v2y)
            if n2 < 1.5e10:
                return netg.CLEAR_ENV
            v1x, v1y = sx0 - rxx, sy0 - rxy
            n1 = math.hypot(v1x, v1y)
            if n1 <= 0.0:
                return netg.CLEAR_ENV
            cosd = max(-1.0, min(1.0,
                                 (v1x * v2x + v1y * v2y) / (n1 * n2)))
            return netg.LinkEnv(
                sep_sun_rx_deg=math.degrees(math.acos(cosd)))

        g = netg.CommsGraph(los=los, env=env)
        for n in nodes:
            g.add(n)
        comms_cache.update(at=time.time(), graph=g, pos=pos, routes={})
        return comms_cache

    def comms_route(uid: str, t0: float, floor: bool = False):
        """Route to the DSN root for one node, memoized per rebuild."""
        cc = comms_now(t0)
        key = (uid, floor)
        if key not in cc["routes"]:
            cc["routes"][key] = (
                cc["graph"].route_to_root(uid, floor_only=floor)
                if uid in cc["pos"] else None)
        return cc["routes"][key]

    def comms_label(uid: str) -> str:
        if uid == netg.ROOT_UID:
            return "DSN"
        if uid.startswith("base:"):
            return uid[5:]
        if uid.startswith("v"):
            for v in vessels:
                if f"v{v.vid}" == uid:
                    return v.name
        return uid

    def closest_approach(av0, tgt: str, t0: float) -> tuple[float, float]:
        """(min distance m, when) sampling the prediction over ≤30 days —
        the 'did I actually aim at it' number the map never gave."""
        best_d, best_t = float("inf"), t0
        horizon = min(_PREDICT_HORIZON, 30.0 * SECONDS_PER_DAY)
        for leg in av0.predict(t0)[:3]:
            lo = max(leg.t_start, t0)
            hi = min(leg.t_end, t0 + horizon)
            if hi <= lo:
                continue
            for k in range(33):
                tt = lo + (hi - lo) * k / 32.0
                ex, ey, _, _ = elements_to_state(leg.elements, tt)
                fx2, fy2, _, _ = tree.state_in_root(leg.frame_id, tt)
                tx2, ty2, _, _ = tree.state_in_root(tgt, tt)
                d = math.hypot(fx2 + ex - tx2, fy2 + ey - ty2)
                if d < best_d:
                    best_d, best_t = d, tt
        return best_d, best_t

    # ascent scene state (KSP-style flown launch)
    live: LiveAscent | None = None
    live_stack: list[list[str]] = []
    launch_cost = 0.0
    pending_crew: list[str] = []
    pending_assigned = False
    ascent_av = None               # FleetVessel being RELAUNCHED (None = pad)
    ascent_body_id = "core:earth"
    shake = 0.0                    # camera shake (ignition/staging/loss/max-q)
    flash = 0.0                    # white-out flash (vehicle loss)
    ascent_boomed = False          # explosion VFX fired for this outcome

    # descent scene state (the landing, FLOWN)
    descent: LiveDescent | None = None
    descent_av = None
    descent_warp = 1.0
    descent_acc = 0.0

    # prox-ops scene state (docking, FLOWN)
    prox: ProxOps | None = None
    prox_chaser = None
    prox_target = None
    prox_trail: list[tuple[float, float]] = []

    # blueprint slots (designs.json beside the saves)
    bp_path = save_dir / "designs.json"

    def load_designs() -> dict:
        try:
            return json.loads(bp_path.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def save_designs(d: dict) -> None:
        try:
            bp_path.write_text(json.dumps(d, indent=1), encoding="utf-8")
        except Exception:
            pass
    ascent_warp = 1.0
    ascent_acc = 0.0
    rot_cache: dict = {}
    menu_limb = None        # lazy hero Earth limb for the title screen
    # ---- ascent/descent scene dressing (cached in surface_art) -----------
    cloud_spr = pygame.Surface((150, 52), pygame.SRCALPHA)
    for _cx, _cy, _cr in ((40, 30, 22), (72, 24, 27), (104, 30, 20),
                          (60, 34, 24), (88, 34, 22)):
        pygame.draw.ellipse(cloud_spr, (255, 255, 255, 14),
                            (_cx - _cr, _cy - _cr // 2, _cr * 2, _cr))
    _CLOUD_DECK = ((1_500.0, 180.0), (2_400.0, 660.0), (3_300.0, 1_040.0),
                   (4_600.0, 420.0), (6_200.0, 880.0), (7_800.0, 130.0),
                   (5_400.0, 1_180.0))

    haze = pygame.Surface((size[0], 70), pygame.SRCALPHA)
    for _hy in range(70):
        pygame.draw.line(haze, (235, 240, 248, int(54 * (1.0 - _hy / 70.0))),
                         (0, 69 - _hy), (size[0], 69 - _hy))

    if boot_ascent:                      # --scene ascent: QA flight
        from aphelion.sim.vessels.vessel import Vessel
        _rows, _plan = [], []
        for _stage in (["core:engine_m733", "core:engine_m733",
                        "core:tank_ml_xl"],
                       ["core:engine_mv815", "core:tank_ml_m",
                        "core:payload_2t"]):
            _idxs = []
            for _pid in _stage:
                _idxs.append(len(_rows))
                _rows.append(Vessel.fueled_row(db, _pid))
            _plan.append(_idxs)
        live = LiveAscent.from_pad(
            Vessel(db, _rows, stage_plan=_plan, cd_a_m2=3.2), "core:earth",
            tree.body("core:earth").mu, tree.body("core:earth").radius,
            86_164.1)
        live_stack = [["core:engine_m733", "core:engine_m733",
                       "core:tank_ml_xl"],
                      ["core:engine_mv815", "core:tank_ml_m",
                       "core:payload_2t"]]
        live.ignite()
        scene = "ascent"
    if want == "descent":               # --scene descent: QA moon landing
        from aphelion.sim.vessels.vessel import Vessel
        _rows = [Vessel.fueled_row(db, p) for p in
                 ("core:engine_ml111", "core:tank_ml_s", "core:payload_2t")]
        _v = Vessel(db, _rows, stage_plan=[[0, 1, 2]], cd_a_m2=0.0)
        moon_b = tree.body("core:moon")
        _r0 = moon_b.radius + 100e3
        descent = LiveDescent.from_orbit(
            _v, moon_b.mu, moon_b.radius, "site:peary", _r0, 0.0, 0.0,
            tr.circular_speed(moon_b.mu, _r0), 0.0)
        descent.engage_autoland()
        descent_warp = 8.0
        scene = "descent"
    if want in ("proxops", "aboard"):   # QA: docking + interiors (T)
        from aphelion.sim.vessels.vessel import Vessel as _V
        _eb = tree.body("core:earth")
        _rq = _eb.radius + 400e3
        _elq = state_to_elements(_rq, 0.0, 0.0,
                                 tr.circular_speed(_eb.mu, _rq), 0.0,
                                 _eb.mu)
        _stn_rows = [_V.fueled_row(db, p) for p in
                     ("core:hb_rig_s", "core:hb_lab", "core:hb_grn_s",
                      "core:hb_dockyard", "core:cg_bay",
                      "core:dk_s", "core:dk_l", "core:pw_sa_r")]
        _stn = FleetVessel(tree, "core:earth", _elq,
                           _V(db, _stn_rows,
                              stage_plan=[list(range(len(_stn_rows)))]),
                           "Foothold Station", next_vid,
                           crew=["V. Ainsworth", "K. Osei"])
        next_vid += 1
        vessels.append(_stn)
        active_idx = len(vessels) - 1
        if want == "proxops":
            _ch_rows = [_V.fueled_row(db, p) for p in
                        ("core:engine_mv815", "core:tank_ml_s",
                         "core:capsule_vela", "core:dk_s")]
            _ch = FleetVessel(tree, "core:earth", _elq,
                              _V(db, _ch_rows, stage_plan=[[0, 1, 2, 3]]),
                              "Courier", next_vid, crew=["M. Reyes"])
            next_vid += 1
            vessels.append(_ch)
            prox = ProxOps(n=math.sqrt(_eb.mu / _rq ** 3), budget_dv=30.0,
                           port_size="S", x=-26.0, y=-14.0,
                           vx=0.35, vy=0.18)
            prox_chaser, prox_target = _ch, _stn
            prox_trail = []
            scene = "proxops"
        else:                           # aboard: walk the station rooms
            from aphelion.render.interior_art import vessel_rooms
            _rv = vessel_rooms(_stn.vessel)
            interior_vessel = _stn
            interior_rooms = tuple(k for k, _, _ in _rv)
            interior_labels = tuple((n, i2) for _, n, i2 in _rv)
            interior_x = 10.0
            scene = "interior"

    def docked_burn_veto(fv) -> str | None:
        """06 §2.8a across the docking joint: a burn loads every joint
        with the mass riding beyond it; the port rating (halved under W6
        wobble) is a hard gate."""
        if not fv.dock_joints:
            return None
        m = fv.vessel.total_mass_kg()
        thrust = fv.vessel.active_thrust_vac_n()
        if m <= 0.0 or thrust <= 0.0:
            return None
        a = thrust / m
        derate = 1.0
        if getattr(fv, "spin_rpm", 0.0) > 0.0 and spin_sim.balance(
                fv.docked_mass_t(), getattr(fv, "spin_r_m", 25.0)) != "ok":
            derate = 0.5
        for port, payload_t, load_kn in fv.joint_burn_loads(a):
            ok_j, _ = ports_sim.burn_load_ok(port, payload_t, a,
                                             derate=derate)
            if not ok_j:
                rating = ports_sim.PORTS[port]["rating_kn"] * derate
                return (f"E8: burn puts {load_kn:,.0f} kN through the "
                        f"DK-{port} joint (rated {rating:,.0f}"
                        + (", W6 wobble halves it" if derate < 1.0 else "")
                        + ") — undock first")
        return None

    frame_count = 0
    running = True
    # frame-budget instrumentation (Z pulled forward): WORK ms per frame,
    # measured between ticks so the 60 fps sleep never pollutes it
    perf_samples: list[float] = []
    perf_open = False
    _perf_prev_post = None
    if args.zoom != 1.0:                # QA: wider establishing shots
        cam.zoom /= max(args.zoom, 1e-6)
    while running:
        _perf_pre = time.perf_counter()
        if _perf_prev_post is not None:
            perf_samples.append((_perf_pre - _perf_prev_post) * 1000.0)
            if len(perf_samples) > 10_000:
                del perf_samples[:5_000]
        real_dt = pygame_clock.tick(60) / 1000.0
        _perf_prev_post = time.perf_counter()
        t = clock.t
        start_new = False
        load_save = False
        ascent_done = False
        ascent_abort = False
        descent_done = False
        prox_done = False
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_F8:
                perf_open = not perf_open
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_F11:
                fullscreen = not fullscreen
                if glp is not None:
                    # re-set_mode would destroy the GL context; SDL's
                    # desktop-fullscreen toggle keeps it alive
                    pygame.display.toggle_fullscreen()
                else:
                    flags = pygame.SCALED | pygame.DOUBLEBUF | (
                        pygame.FULLSCREEN if fullscreen else 0)
                    screen = pygame.display.set_mode(
                        size, flags, vsync=0 if args.headless else 1)
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_m:
                toast = ("audio muted" if audio.toggle_mute()
                         else "audio on")
                toast_until = t + 3.0
            elif scene == "menu":
                items = (list(_DIFFICULTIES) if menu_mode == "difficulty"
                         else ["NEW CAMPAIGN"]
                         + (["CONTINUE"] if latest_save() else [])
                         + ["QUIT"])

                def _menu_pick(choice: str):
                    nonlocal start_new, load_save, running, menu_mode
                    nonlocal menu_cursor
                    audio.play("blip")
                    if menu_mode == "difficulty":
                        start_new = choice
                        menu_mode = "main"
                        menu_cursor = 0
                    elif choice == "NEW CAMPAIGN":
                        menu_mode = "difficulty"
                        menu_cursor = 1          # DIRECTOR is the default
                    elif choice == "CONTINUE":
                        load_save = True
                    else:
                        running = False

                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_UP:
                        menu_cursor = (menu_cursor - 1) % len(items)
                        audio.play("tick")
                    elif event.key == pygame.K_DOWN:
                        menu_cursor = (menu_cursor + 1) % len(items)
                        audio.play("tick")
                    elif event.key == pygame.K_RETURN:
                        _menu_pick(items[menu_cursor % len(items)])
                    elif event.key == pygame.K_ESCAPE:
                        if menu_mode == "difficulty":
                            menu_mode = "main"
                            menu_cursor = 0
                        else:
                            running = False
                elif event.type == pygame.MOUSEMOTION:
                    for i, rect in enumerate(menu_rects):
                        if rect.collidepoint(event.pos):
                            menu_cursor = i
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    for i, rect in enumerate(menu_rects):
                        if rect.collidepoint(event.pos) and i < len(items):
                            _menu_pick(items[i])
                            break
            elif scene == "ascent":
                if event.type == pygame.KEYDOWN and live is not None:
                    if event.key == pygame.K_SPACE:
                        if not live.ignited:
                            live.ignite()
                            shake = 1.0
                            audio.play("ignition")
                            for fam in _stage_engine_families(live.vessel):
                                research.accrue_ignition(
                                    db, fam,
                                    env_class=_ascent_env(ascent_body_id))
                        elif live.t < 2.0:
                            pass        # debounce: SPACE-spam must not stage
                        elif live.stage():
                            shake = max(shake, 0.6)
                            audio.play("stage")
                            for fam in _stage_engine_families(live.vessel):
                                research.accrue_ignition(
                                    db, fam,
                                    env_class=_ascent_env(ascent_body_id))
                    elif event.key == pygame.K_x:
                        live.throttle_cmd = 1.0     # X = burn, as in flight
                    elif event.key == pygame.K_z:
                        live.throttle_cmd = 0.0
                    elif event.key == pygame.K_p:
                        live.prog = not live.prog
                        if not live.prog:
                            live.pitch_manual_deg = live.gamma_deg
                    elif event.key == pygame.K_c:
                        if live.arm_circularize():
                            audio.play("blip")
                    elif event.key in (pygame.K_LEFT, pygame.K_RIGHT,
                                       pygame.K_a, pygame.K_d):
                        if live.prog:
                            live.prog = False
                            live.pitch_manual_deg = live.gamma_deg
                    elif event.key == pygame.K_PERIOD:
                        ascent_warp = min(ascent_warp * 2.0, 64.0)
                    elif event.key == pygame.K_COMMA:
                        ascent_warp = max(ascent_warp / 2.0, 1.0)
                    elif (event.key == pygame.K_RETURN
                          and live.outcome is not None):
                        ascent_done = True
                    elif event.key == pygame.K_ESCAPE:
                        # revert is a pad-scrub, not an undo: once the tower
                        # is cleared (or the die is cast) the money is spent
                        if live.outcome is not None:
                            ascent_done = True
                        elif ascent_av is not None:
                            if not live.ignited:
                                live = None
                                ascent_av = None
                                scene = "flight"
                                toast, toast_until = ("relaunch stood down",
                                                      t + 4)
                            else:
                                toast = ("committed — no revert on a "
                                         "field relaunch")
                                toast_until = t + 4
                                audio.play("warn")
                        elif (live.t < _REVERT_WINDOW_S
                              and difficulty != "HARDCORE"):
                            ascent_abort = True
                        else:
                            toast = ("HARDCORE flies what it lights"
                                     if difficulty == "HARDCORE" else
                                     f"revert window closed "
                                     f"(T+{_REVERT_WINDOW_S:.0f}s) — fly it out")
                            toast_until = t + 4
                            audio.play("warn")
            elif scene == "descent":
                if event.type == pygame.KEYDOWN and descent is not None:
                    if event.key == pygame.K_x:
                        descent.throttle_cmd = 1.0
                        descent.auto = False
                    elif event.key == pygame.K_z:
                        descent.throttle_cmd = 0.0
                        descent.auto = False
                    elif event.key == pygame.K_SPACE:
                        if descent.stage():
                            audio.play("blip")
                    elif event.key == pygame.K_a:
                        if (descent_av is not None
                                and best_skill(descent_av, crew,
                                               "pilot") >= 2):
                            descent.engage_autoland()
                            audio.play("blip")
                        else:
                            toast = ("autoland needs a skill-2 pilot "
                                     "aboard — you fly it")
                            toast_until = t + 5
                            audio.play("warn")
                    elif event.key == pygame.K_PERIOD:
                        descent_warp = min(descent_warp * 2.0, 8.0)
                    elif event.key == pygame.K_COMMA:
                        descent_warp = max(descent_warp / 2.0, 1.0)
                    elif (event.key in (pygame.K_RETURN, pygame.K_ESCAPE)
                          and descent.outcome is not None):
                        descent_done = True
                    elif event.key == pygame.K_ESCAPE:
                        toast = ("committed to the descent — fly it down")
                        toast_until = t + 4
                        audio.play("warn")
            elif scene == "proxops":
                if event.type == pygame.KEYDOWN and prox is not None:
                    # inside the gate, un-shifted taps drop to verniers —
                    # port capture limits live at 0.05–0.20 m/s
                    if prox.range_m < CAPTURE_RANGE_M + 10.0:
                        mag = 0.5 if (event.mod & pygame.KMOD_SHIFT) \
                            else PULSE_FINE_MS
                    else:
                        mag = 2.0 if (event.mod & pygame.KMOD_SHIFT) else 0.5
                    if event.key in (pygame.K_UP, pygame.K_DOWN,
                                     pygame.K_LEFT, pygame.K_RIGHT):
                        dx = {pygame.K_UP: 1.0, pygame.K_DOWN: -1.0}.get(
                            event.key, 0.0)
                        dy = {pygame.K_RIGHT: 1.0, pygame.K_LEFT: -1.0}.get(
                            event.key, 0.0)
                        if prox.pulse(dx, dy, mag):
                            audio.play("burn")
                        else:
                            audio.play("warn")
                    elif event.key == pygame.K_a:
                        if (prox_chaser is not None
                                and best_skill(prox_chaser, crew,
                                               "pilot") >= 1):
                            prox.engage_auto()
                            audio.play("blip")
                        else:
                            toast = "approach autopilot needs a pilot aboard"
                            toast_until = t + 5
                            audio.play("warn")
                    elif (event.key == pygame.K_RETURN
                          and prox.outcome == "captured"):
                        prox_done = True
                    elif event.key == pygame.K_ESCAPE:
                        prox.outcome = "aborted"
                        prox_done = True
            elif scene == "drydock":
                if event.type == pygame.KEYDOWN:
                    rows_dd = dd_catalog()
                    if event.key == pygame.K_TAB:
                        dd_class_idx = (dd_class_idx + 1) \
                            % len(dd_cat_classes)
                        dd_cat_idx = 0
                        audio.play("tick")
                    elif event.key in (pygame.K_COMMA, pygame.K_PAGEUP):
                        dd_cat_idx -= 1
                        audio.play("tick")
                    elif event.key in (pygame.K_PERIOD,
                                       pygame.K_PAGEDOWN):
                        dd_cat_idx += 1
                        audio.play("tick")
                    elif event.key in (pygame.K_RETURN, pygame.K_SPACE) \
                            and rows_dd:
                        pid_dd, spec_dd = rows_dd[dd_cat_idx
                                                  % len(rows_dd)]
                        if dd_v.add(pid_dd, spec_dd, dd_cursor[0],
                                    dd_cursor[1]) is None:
                            dd_msg = "600-part cap — the dock refuses"
                        else:
                            dd_msg = f"placed {spec_dd['name']}"
                        audio.play("clunk")
                    elif event.key in (pygame.K_x, pygame.K_DELETE):
                        for i_dd, p_dd in enumerate(dd_v.parts):
                            if tuple(dd_cursor) in p_dd.cells:
                                dd_msg = f"removed {p_dd.spec['name']}"
                                dd_v.remove(i_dd)
                                audio.play("blip")
                                break
                    elif event.key == pygame.K_e:
                        errs_dd = [e for e in dd_v.validate()
                                   if e[1] is not None]
                        if errs_dd:
                            dd_err_idx = (dd_err_idx + 1) % len(errs_dd)
                            code_dd, off_dd = errs_dd[dd_err_idx]
                            dd_cursor = [dd_v.parts[off_dd].x,
                                         dd_v.parts[off_dd].y]
                            dd_msg = f"{code_dd} → " \
                                f"{dd_v.parts[off_dd].spec['name']}"
                            audio.play("warn")
                    elif event.key == pygame.K_m:
                        dd_mode = {"vac": "sl", "sl": "traj",
                                   "traj": "vac"}[dd_mode]
                        audio.play("tick")
                    elif event.key == pygame.K_s:
                        if dd_sim is not None:
                            dd_sim = None
                        else:
                            defs_dd = dd_stage.to_stage_defs(dd_v)
                            if defs_dd and defs_dd[0].engines \
                                    and defs_dd[0].prop_t > 0:
                                r0 = stage_report(defs_dd,
                                                  mode="sl")[0]
                                fr = max((p.w for p in dd_v.parts),
                                         default=2) * 1.0
                                dd_sim = ascent_qsim(
                                    r0["thrust_kn"], r0["mdot_kgps"],
                                    r0["m0_t"], defs_dd[0].prop_t, fr)
                                dd_msg = "pre-flight ascent sim flown"
                                audio.play("blip")
                            else:
                                dd_msg = ("the bottom stage needs an "
                                          "engine and propellant")
                    elif event.key == pygame.K_b:
                        plan_dd = dd_stage.flyable_stack(dd_v)
                        locked_dd = [pid for st in plan_dd for pid in st
                                     if builder.locked(pid)]
                        if not plan_dd:
                            dd_msg = "nothing flyable on the grid yet"
                        elif locked_dd:
                            dd_msg = ("research locks: "
                                      + ", ".join(sorted(
                                          set(locked_dd))[:3]))
                            audio.play("warn")
                        elif dd_v.validate():
                            dd_msg = "clear the validation list first"
                            audio.play("warn")
                        else:
                            builder.load_stack(plan_dd)
                            builder_open = True
                            scene = "flight"
                            toast = ("grid design sent to the pad — "
                                     "assemble and launch from the "
                                     "builder")
                            toast_until = t + 8
                            audio.play("paid")
                    elif event.key == pygame.K_y:
                        # blueprint for ORBITAL construction (05 §3.1):
                        # a yard with parts cargo erects it without a
                        # launch — F-11 learning per repeat build
                        plan_dd = dd_stage.flyable_stack(dd_v)
                        if not plan_dd:
                            dd_msg = "nothing flyable on the grid yet"
                        elif dd_v.validate():
                            dd_msg = "clear the validation list first"
                            audio.play("warn")
                        else:
                            dry_dd = sum(float(p.spec["mass_t"])
                                         for p in dd_v.parts)
                            yard_designs.append({
                                "name": f"BP-{len(yard_designs) + 1}",
                                "stack": [list(s) for s in plan_dd],
                                "dry_t": round(dry_dd, 2),
                                "n_parts": len(dd_v.parts),
                                "built": 0})
                            dd_msg = (f"blueprint BP-"
                                      f"{len(yard_designs)} saved "
                                      f"({dry_dd:,.1f} t dry) — build "
                                      f"it at any orbital dockyard (F7)")
                            audio.play("paid")
                    elif event.key == pygame.K_ESCAPE:
                        scene = "flight"
            elif scene == "dive":
                if event.type == pygame.KEYDOWN and dive_gv is not None:
                    if event.key in (pygame.K_e, pygame.K_ESCAPE):
                        if dive_depth > 3.0 and event.key == pygame.K_e:
                            toast = (f"{dive_depth:,.0f} m down — blow "
                                     f"ballast (W) and surface first")
                            toast_until = t + 5
                            audio.play("warn")
                        else:
                            toast = (f"{dive_gv.name} MOORED — hull "
                                     f"{100.0 * dive_gv.cond:.0f}%, "
                                     f"{len(dive_painted) * 50} m of "
                                     f"seafloor mapped")
                            toast_until = t + 7
                            dive_gv, dive_av = None, None
                            scene = "flight"
                            audio.play("clunk")
                    elif event.key == pygame.K_q:
                        dive_ping_t = t
                        audio.play("blip")
                        cell_q = int(dive_x // 50.0)
                        new_q = [c for c in (cell_q - 1, cell_q, cell_q + 1)
                                 if c not in dive_painted]
                        if new_q:
                            dive_painted.update(new_q)
                            research.earn_science(2.0 * len(new_q))
                            toast = (f"SONAR SWATH MAPPED "
                                     f"(+{2 * len(new_q)} sci, DSC-14 "
                                     f"bathymetry)")
                            toast_until = t + 5
                    elif event.key == pygame.K_u:
                        dive_uv = not dive_uv
                        toast = ("UV LAMP ON — biology fluoresces, if "
                                 "there is any" if dive_uv
                                 else "UV LAMP OFF")
                        toast_until = t + 4
                        audio.play("tick")
            elif scene == "drive":
                if event.type == pygame.KEYDOWN and drive_gv is not None:
                    if event.key in (pygame.K_e, pygame.K_ESCAPE):
                        drive_gv.park_x_m = drive_x
                        toast = (f"{drive_gv.name} PARKED — odo "
                                 f"{drive_gv.odo_km:,.1f} km, charge "
                                 f"{100.0 * drive_gv.energy_kwh / max(drive_gv.pack_kwh, 1e-9):.0f}%"
                                 f", cond {100.0 * drive_gv.cond:.0f}%")
                        toast_until = t + 7
                        drive_gv, drive_av = None, None
                        drive_tiles, drive_tr = None, None
                        scene = "flight"
                        audio.play("clunk")
                    elif event.key == pygame.K_x and drive_stuck > 0.0:
                        import zlib as _z
                        drive_attempts += 1
                        bdy_x = tree.body(
                            SITES[drive_av.landed_at]["body"])
                        g_x = bdy_x.mu / bdy_x.radius ** 2
                        # escape attempt burns 3x energy (10 fail row 2)
                        drive_gv.drive(0.03, g_x, "dune", v_kmh=2.0)
                        roll = _z.crc32(
                            f"{drive_gv.vid}|{drive_attempts}|"
                            f"{int(drive_gv.odo_km * 10)}".encode()) % 100
                        if roll < 30:
                            drive_stuck = 0.0
                            toast = "WHEELS FREE — easy on the throttle"
                            toast_until = t + 6
                            audio.play("paid")
                        else:
                            toast = (f"still embedded (attempt "
                                     f"{drive_attempts}) — X to rock it")
                            toast_until = t + 4
                            audio.play("thud")
            elif scene == "eva":
                if event.type == pygame.KEYDOWN and eva_state is not None:
                    if event.key == pygame.K_SPACE:
                        if not eva_state.airborne:
                            eva_state.step(0.0, 0, False, True)
                            audio.play("tick")
                    elif event.key == pygame.K_e:
                        # nearest interactable in range wins
                        if eva_state.depth_m() > 2.5:
                            toast = ("nothing to reach down here — climb "
                                     "back to daylight first")
                            toast_until = t + 4
                        elif eva_state.near(0.0):         # the lander
                            scene = "flight"
                            toast = (f"{eva_state.member} ABOARD — EVA "
                                     f"complete: {eva_state.dist_walked:,.0f}"
                                     f" m walked")
                            toast_until = t + 8
                            eva_state, eva_tiles, eva_tr = None, None, None
                            eva_dig = None
                            audio.play("clunk")
                        else:
                            home_b = next(
                                (b for b in bases
                                 if b.site_id == eva_av.landed_at), None)
                            handled = False
                            if home_b is not None:
                                from aphelion.render.interior_art import \
                                    HABITABLE
                                pos = eva_sim.module_positions(home_b.built)
                                for bi, bx in pos.items():
                                    if not eva_state.near(bx):
                                        continue
                                    key_b = home_b.built[bi]
                                    if key_b in HABITABLE:
                                        # step inside: airlock + rooms
                                        interior_home = home_b
                                        interior_vessel = None
                                        interior_rooms = tuple(
                                            k for k in home_b.built
                                            if k in HABITABLE)
                                        interior_x = 4.0
                                        interior_return_x = eva_state.x
                                        interior_face = eva_state.facing
                                        interior_frame = 0.0
                                        eva_state.o2_s = eva_sim.SUIT_O2_S
                                        scene = "interior"
                                        toast = (f"INSIDE {home_b.name} — "
                                                 f"suit recharged; walk "
                                                 f"the rooms, E at the "
                                                 f"airlock to exit")
                                        toast_until = t + 8
                                        audio.play("clunk")
                                    else:
                                        home_b.advance(t)
                                        mid = next(
                                            (m for m in home_b.net.modules
                                             if m.module_id.startswith(
                                                 key_b)), None)
                                        if mid is not None:
                                            toast = (f"CONSOLE "
                                                     f"{mid.module_id}: "
                                                     f"{mid.state}  ·  "
                                                     f"{abs(mid.power_kw):,.0f}"
                                                     f" kW  ·  F2 manages "
                                                     f"the colony")
                                            toast_until = t + 8
                                        audio.play("blip")
                                    handled = True
                                    break
                            if not handled and eva_state.near(
                                    eva_sim.ANOMALY_X_M, 6.0):
                                site_e = SITES[eva_av.landed_at]
                                pend = [a for a in site_e.get("anomalies", [])
                                        if a not in explore["investigated"]]
                                if pend:
                                    an = db.by_type("anomalies")[pend[0]]
                                    explore["investigated"].add(pend[0])
                                    gb = float(an["gb"])
                                    research.earn_science(2.0 * gb)
                                    explore["surveydata_gb"] += gb
                                    toast = (f"{an['class']} INVESTIGATED "
                                             f"ON FOOT: {an['name']} — "
                                             f"+{gb:.0f} GB, "
                                             f"+{2 * gb:.0f} sci")
                                    toast_until = t + 12
                                    audio.play("paid")
                    elif event.key == pygame.K_f:
                        flags = explore.setdefault("flags", [])
                        sid_e = eva_av.landed_at
                        if abs(eva_state.x) >= eva_sim.FLAG_X_MIN_M \
                                and sid_e not in flags:
                            flags.append(sid_e)
                            research.earn_science(5.0)
                            toast = (f"FLAG PLANTED at "
                                     f"{SITES[sid_e]['name']} (+5 sci, "
                                     f"and a photograph for the ages)")
                            toast_until = t + 10
                            audio.play("paid")
                        elif sid_e in flags:
                            toast = "the flag already stands here"
                            toast_until = t + 4
                    elif event.key == pygame.K_r:
                        if eva_state.scoops_left > 0:
                            eva_state.scoops_left -= 1
                            site_e = SITES[eva_av.landed_at]
                            got = research.analyze_sample(
                                "regolith_scoop",
                                site_e.get("region_code", "LOCAL"),
                                site_e.get("x", 3.0), "insitu")
                            toast = (f"SAMPLE SCOOPED + analyzed in-situ: "
                                     f"+{got:,.0f} sci  "
                                     f"({eva_state.scoops_left} bags left)")
                            toast_until = t + 8
                            audio.play("blip")
                        else:
                            toast = "sample bags spent — return to the lander"
                            toast_until = t + 5
                    elif event.key == pygame.K_ESCAPE:
                        toast = "board at the lander (walk to it, then E)"
                        toast_until = t + 5
                    elif event.key == pygame.K_F2 and base_screen:
                        base_screen = False
            elif scene == "interior":
                if event.type == pygame.KEYDOWN:
                    from aphelion.render.interior_art import ROOM_W
                    ppm_i = 24.0
                    if event.key == pygame.K_e:
                        if interior_x < ROOM_W / ppm_i:      # the airlock
                            if interior_vessel is not None:
                                scene = "flight"
                                interior_vessel = None
                                toast = "back on the flight deck"
                                toast_until = t + 4
                                audio.play("clunk")
                            elif eva_state is not None:
                                scene = "eva"
                                eva_state.x = interior_return_x
                                toast = "back on the surface"
                                toast_until = t + 5
                                audio.play("clunk")
                        else:
                            room_i = int(interior_x * ppm_i // ROOM_W) - 1
                            if (interior_vessel is not None
                                    and 0 <= room_i < len(interior_labels)):
                                nm_i, info_i = interior_labels[room_i]
                                toast = f"{nm_i} — {info_i}"
                                toast_until = t + 7
                                audio.play("blip")
                            elif (interior_home is not None
                                    and 0 <= room_i < len(interior_rooms)):
                                key_i = interior_rooms[room_i]
                                interior_home.advance(t)
                                mid = next(
                                    (m for m in interior_home.net.modules
                                     if m.module_id.startswith(key_i)),
                                    None)
                                if mid is not None:
                                    toast = (f"{mid.module_id}: {mid.state}"
                                             f"  ·  {abs(mid.power_kw):,.0f}"
                                             f" kW")
                                    toast_until = t + 7
                                    audio.play("blip")
                    elif event.key == pygame.K_ESCAPE:
                        toast = "exit through the airlock (far left, E)"
                        toast_until = t + 5
            elif scene == "victory":
                if event.type == pygame.KEYDOWN and event.key in (
                        pygame.K_RETURN, pygame.K_ESCAPE):
                    scene = "flight"
                    toast = ("the program continues — the sky is not the "
                             "limit anymore")
                    toast_until = t + 10
            elif event.type == pygame.KEYDOWN and help_open:
                if event.key in (pygame.K_F1, pygame.K_ESCAPE,
                                 pygame.K_RETURN, pygame.K_h):
                    help_open = False
            elif event.type == pygame.KEYDOWN and contracts_open:
                if event.key in (pygame.K_ESCAPE, pygame.K_o,
                                 pygame.K_RETURN):
                    contracts_open = False
                elif event.key == pygame.K_UP:
                    contracts_scroll = max(0, contracts_scroll - 1)
                    audio.play("tick")
                elif event.key == pygame.K_DOWN:
                    contracts_scroll += 1
                    audio.play("tick")
            elif event.type == pygame.KEYDOWN and planner_open:
                av0 = vessels[active_idx % len(vessels)] if vessels else None
                prows = planner_rows_for(av0, t)
                if event.key in (pygame.K_ESCAPE, pygame.K_p) or not prows:
                    planner_open = False
                elif event.key == pygame.K_UP:
                    planner_cursor = (planner_cursor - 1) % len(prows)
                    audio.play("tick")
                elif event.key == pygame.K_DOWN:
                    planner_cursor = (planner_cursor + 1) % len(prows)
                    audio.play("tick")
                elif event.key == pygame.K_RETURN:
                    row = prows[planner_cursor % len(prows)]
                    ref = lambert_refined(av0, row, t)
                    node = {"t_node": ref["t_dep"] if ref else row["t_dep"],
                            "dvp": ref["dv_dep"] if ref else row["dv_dep"],
                            "dvr": 0.0, "armed": False}
                    target_id = row["pid"]
                    planner_open = False
                    via = "Lambert window" if ref else "window"
                    toast = (f"TRANSFER NODE to {row['name']} at the {via} "
                             f"— fine-tune ([/] arrows), ENTER arms, W warps")
                    toast_until = t + 10
                    audio.play("blip")
            elif event.type == pygame.KEYDOWN and pause_open:
                if event.key == pygame.K_ESCAPE:
                    pause_open = False
                elif event.key == pygame.K_UP:
                    pause_cursor = (pause_cursor - 1) % len(_PAUSE_ITEMS)
                    audio.play("tick")
                elif event.key == pygame.K_DOWN:
                    pause_cursor = (pause_cursor + 1) % len(_PAUSE_ITEMS)
                    audio.play("tick")
                elif event.key == pygame.K_RETURN:
                    choice = _PAUSE_ITEMS[pause_cursor]
                    if choice == "RESUME":
                        pause_open = False
                    elif choice == "QUICKSAVE":
                        toast, toast_until = do_quicksave(), t + 5.0
                        audio.play("blip")
                    elif choice == "LOAD QUICKSAVE":
                        load_save = True
                    elif choice == "VOLUME -":
                        v = audio.set_master(audio.master - 0.1)
                        toast, toast_until = f"volume {v:.0%}", t + 3
                        audio.play("blip")
                    elif choice == "VOLUME +":
                        v = audio.set_master(audio.master + 0.1)
                        toast, toast_until = f"volume {v:.0%}", t + 3
                        audio.play("blip")
                    elif choice == "EXIT TO MAIN MENU":
                        pause_open = False
                        scene = "menu"
                        menu_cursor = 0
                    else:
                        running = False
            elif event.type == pygame.KEYDOWN and station_open:
                av0 = vessels[active_idx % len(vessels)] if vessels \
                    else None
                if event.key in (pygame.K_ESCAPE, pygame.K_F7):
                    station_open = False
                elif av0 is not None and av0.landed_at is None:
                    rpm0 = getattr(av0, "spin_rpm", 0.0)
                    r0 = getattr(av0, "spin_r_m", 25.0)
                    if event.key in (pygame.K_EQUALS, pygame.K_UP):
                        bal = spin_sim.balance(av0.docked_mass_t(), r0)
                        if bal == "despin":
                            toast = (f"W6: {av0.docked_mass_t():,.0f} t "
                                     f"docked off-axis unbalances the ring"
                                     f" — undock before spinning up")
                            toast_until = t + 8
                            audio.play("warn")
                        else:
                            cap = 6.0 if av0.crew else 8.0   # E9 crewed
                            av0.spin_rpm = min(cap, rpm0 + 0.5)
                            audio.play("tick" if bal == "ok" else "warn")
                    elif event.key in (pygame.K_MINUS, pygame.K_DOWN):
                        av0.spin_rpm = max(0.0, rpm0 - 0.5)
                        audio.play("tick")
                    elif event.key == pygame.K_LEFTBRACKET:
                        av0.spin_r_m = max(5.0, r0 - 5.0)
                        audio.play("tick")
                    elif event.key == pygame.K_RIGHTBRACKET:
                        av0.spin_r_m = min(450.0, r0 + 5.0)
                        audio.play("tick")
                    elif pygame.K_1 <= event.key <= pygame.K_9 \
                            and yard_designs:
                        # lay down a blueprint at the orbital yard (05 §3.1)
                        from aphelion.sim.industry.yard import (
                            has_dockyard, plan_build)
                        idx_y = event.key - pygame.K_1
                        if not has_dockyard(av0.vessel):
                            toast = ("no dockyard module aboard — fit "
                                     "HB-DOCKYARD in the drydock")
                            toast_until = t + 6
                            audio.play("warn")
                        elif av0.yard_job is not None:
                            toast = "the yard is already mid-build"
                            toast_until = t + 5
                            audio.play("warn")
                        elif not av0.crew:
                            toast = ("OUTFIT quality gate wants hands on "
                                     "the job — crew the yard first")
                            toast_until = t + 6
                            audio.play("warn")
                        elif idx_y < len(yard_designs):
                            d_y = yard_designs[idx_y]
                            a3_y = ("core:tech_in09_supervised_autonomy"
                                    in research.unlocked)
                            plan_y = plan_build(
                                d_y["dry_t"], d_y["n_parts"], a3=a3_y,
                                n_built_before=d_y.get("built", 0))
                            short = {r: kg - av0.cargo.get(r, 0.0)
                                     for r, kg in plan_y.bill_kg.items()
                                     if av0.cargo.get(r, 0.0) < kg - 1e-6}
                            if short:
                                toast = ("parts short at the yard: "
                                         + ", ".join(
                                             f"{kg / 1e3:,.1f} t {r}"
                                             for r, kg in short.items()))
                                toast_until = t + 8
                                audio.play("warn")
                            else:
                                for r, kg in plan_y.bill_kg.items():
                                    av0.cargo[r] -= kg
                                    if av0.cargo[r] <= 1e-9:
                                        av0.cargo.pop(r)
                                av0.yard_job = {
                                    "design": idx_y, "name": d_y["name"],
                                    "stack": [list(s)
                                              for s in d_y["stack"]],
                                    "done_t": t + plan_y.days * 86_400.0,
                                    "days": plan_y.days}
                                toast = (f"LAID DOWN: {d_y['name']} — "
                                         f"{plan_y.days:,.0f} d through "
                                         f"BERTH/FABWELD/OUTFIT/COMMISSION"
                                         + (f" (Wright ×"
                                            f"{plan_y.learning:.2f})"
                                            if plan_y.learning < 1.0
                                            else ""))
                                toast_until = t + 9
                                audio.play("paid")
            elif event.type == pygame.KEYDOWN and surface_open:
                av0 = vessels[active_idx % len(vessels)] if vessels else None
                opts = (_surface_options(av0, bases, db,
                                         explore["investigated"],
                                         ground_vehicles)
                        if av0 else [])
                if event.key in (pygame.K_ESCAPE, pygame.K_g) or not opts:
                    surface_open = False
                elif event.key == pygame.K_UP:
                    surface_cursor = (surface_cursor - 1) % len(opts)
                    audio.play("tick")
                elif event.key == pygame.K_DOWN:
                    surface_cursor = (surface_cursor + 1) % len(opts)
                    audio.play("tick")
                elif event.key == pygame.K_RETURN:
                    action = opts[surface_cursor % len(opts)][0]
                    if action[0] == "eva" and (
                            (w0 := crew.get(av0.crew[0])) is not None
                            and not w0.eva_ok()):
                        toast = (f"{av0.crew[0]} cannot EVA — "
                                 + ("bedridden" if w0.bedridden else
                                    f"deconditioned (C {w0.cond:.0f} < 40"
                                    f"; exercise or surface gravity)"))
                        toast_until = t + 8
                        audio.play("warn")
                    elif action[0] == "eva":
                        body_w = tree.body(av0.frame_id)
                        g_loc = body_w.mu / (body_w.radius ** 2)
                        sec_id = SITES[av0.landed_at].get(
                            "sector_id", av0.landed_at)
                        slope = db.by_type("sectors").get(
                            sec_id, {}).get("slope_sigma", 4.0)
                        eva_tiles = tileworld.TileWorld(
                            sec_id, slope,
                            SITES[av0.landed_at].get("kind", "regolith"),
                            dug=explore.setdefault("dug", {}).get(
                                sec_id, []))
                        eva_tr = TileRenderer(
                            eva_tiles,
                            ground_palette(SITES[av0.landed_at]["body"]))
                        eva_state = eva_sim.EvaState(
                            sec_id, slope, g_loc, av0.crew[0],
                            tiles=eva_tiles)
                        eva_av = av0
                        eva_camy = eva_state.y
                        eva_dig = None
                        surface_open = False
                        scene = "eva"
                        toast = (f"{av0.crew[0]} ON EVA — E interact, "
                                 f"X/C dig, F flag, R sample, board at "
                                 f"the lander")
                        toast_until = t + 8
                        audio.play("clunk")
                    elif action[0] == "drive":
                        gv_d = next((g for g in ground_vehicles
                                     if g.vid == action[1]), None)
                        # L-13 teleop gate: no crew on site = the rover is
                        # driven from Earth over the live path — refuse
                        # when the link can't carry a joystick
                        _tele_no = ""
                        drive_eta = 1.0
                        if gv_d is not None and not av0.crew:
                            _rt_d = comms_route(f"v{av0.vid}", t)
                            if _rt_d is None:
                                _tele_no = "no live path to the site"
                            else:
                                _eta_d = teleop_eta_driving(_rt_d.rtt_s)
                                _gain_d = min(
                                    (min(NET_PARTS[h.tx_part]["gain"],
                                         NET_PARTS[h.rx_part]["gain"])
                                     for h in _rt_d.hops), default=0.0)
                                if not netg.teleop_ok(_rt_d.rate_bps,
                                                      _eta_d, _gain_d):
                                    if _eta_d < 0.2:
                                        _tele_no = (
                                            f"RTT {theme.fmt_duration(_rt_d.rtt_s)}"
                                            f" puts η at {_eta_d:.2f} "
                                            f"(< 0.2) — too far to joystick")
                                    elif _rt_d.rate_bps < 0.5e6:
                                        _tele_no = (
                                            f"live path "
                                            f"{_fmt_bps(_rt_d.rate_bps)} "
                                            f"< 0.5 Mbit/s")
                                    else:
                                        _tele_no = ("an omni relay leg — "
                                                    "CM-PROX class needed")
                                else:
                                    drive_eta = _eta_d
                        if gv_d is not None and _tele_no:
                            toast = f"TELEOP REFUSED: {_tele_no}"
                            toast_until = t + 8
                            audio.play("warn")
                        elif gv_d is not None:
                            drive_gv, drive_av = gv_d, av0
                            drive_x = gv_d.park_x_m
                            drive_v, drive_face = 0.0, 1
                            drive_stuck, drive_attempts = 0.0, 0
                            drive_tiles, drive_tr = None, None
                            surface_open = False
                            scene = "drive"
                            _tele_tag = ("" if av0.crew else
                                         f"  TELEOP η {drive_eta:.2f}")
                            toast = (f"{gv_d.name} POWERED UP — A/D "
                                     f"drive, E park & dismount{_tele_tag}")
                            toast_until = t + 8
                            audio.play("clunk")
                    elif action[0] == "dive":
                        gv_d = next((g for g in ground_vehicles
                                     if g.vid == action[1]), None)
                        if gv_d is not None:
                            dive_gv, dive_av = gv_d, av0
                            dive_x = gv_d.park_x_m * 10.0
                            dive_depth, dive_vx, dive_vz = 0.0, 0.0, 0.0
                            dive_face = 1
                            dive_painted = set()
                            dive_sea, dive_sea_cells = [], set()
                            dive_uv = False
                            surface_open = False
                            scene = "dive"
                            toast = (f"{gv_d.name} CASTS OFF — A/D thrust, "
                                     f"W/S ballast, Q sonar, E surfaces")
                            toast_until = t + 8
                            audio.play("clunk")
                    elif action[0] == "mp_no":
                        toast = f"MOTOR POOL: {action[1]}"
                        toast_until = t + 6
                        audio.play("warn")
                    elif action[0] == "mp_build":
                        from aphelion.game import motorpool as _mp
                        home_v = next((b for b in bases
                                       if b.site_id == av0.landed_at), None)
                        row_v = db.by_type("vehicles").get(action[1], {})
                        st_v = _mp.row_stats(row_v)
                        if home_v is not None:
                            _mp.debit_build(home_v, st_v["dry_t"])
                            next_vid += 1
                            gv_n = _mp.GroundVehicle(
                                vid=next_vid, catalog_id=action[1],
                                name=(f"{row_v.get('name', 'Rover')}"
                                      f"-{next_vid}"),
                                body=SITES[av0.landed_at]["body"],
                                site_id=av0.landed_at,
                                pack_kwh=st_v["pack_kwh"],
                                energy_kwh=st_v["pack_kwh"] * 0.85,
                                rtg_we=st_v["rtg_we"],
                                tracks=st_v["tracks"],
                                crewed=st_v["crewed"],
                                park_x_m=22.0 + 8.0 * len(ground_vehicles))
                            gv_n.dry_t = st_v["dry_t"]
                            ground_vehicles.append(gv_n)
                            toast = (f"{gv_n.name} ASSEMBLED at the "
                                     f"motor pool — parts debited")
                            toast_until = t + 9
                            audio.play("paid")
                    elif action[0] == "investigate":
                        aid = action[1]
                        an = db.by_type("anomalies")[aid]
                        explore["investigated"].add(aid)
                        gb = float(an["gb"])
                        sci = 2.0 * gb              # 2 SCI/GB, one-shot (03)
                        research.earn_science(sci)
                        explore["surveydata_gb"] += gb
                        toast = (f"{an['class']} INVESTIGATED: {an['name']} "
                                 f"— +{gb:.0f} GB SurveyData, +{sci:.0f} sci"
                                 + ("  · HERITAGE SITE preserved"
                                    if an.get("heritage") else ""))
                        toast_until = t + 12
                        audio.play("paid")
                    elif action[0] == "relaunch":
                        site = SITES[av0.landed_at]
                        if av0.dv_remaining < site["ascent_dv"] * 0.8:
                            toast = (f"ascent needs ~{site['ascent_dv']:,.0f}"
                                     f" m/s — not enough propellant")
                            toast_until = t + 6
                            audio.play("alarm")
                        else:
                            # the ascent is FLOWN here too — same integrator,
                            # this body's gravity and (lack of) atmosphere
                            body_r = tree.body(av0.frame_id)
                            live = LiveAscent.from_pad(
                                av0.vessel, av0.frame_id, body_r.mu,
                                body_r.radius, 1.0e7)
                            live_stack = [
                                [av0.vessel.rows[i].part_id for i in st]
                                for st in av0.vessel.stage_plan]
                            launch_cost = 0.0
                            ascent_av = av0
                            ascent_body_id = av0.frame_id
                            pending_assigned = False
                            ascent_warp, ascent_acc = 1.0, 0.0
                            ascent_event_count = 0
                            node = None
                            surface_open = False
                            scene = "ascent"
                            audio.play("blip")
                    elif action[0] == "found":
                        site_id = av0.landed_at
                        site = SITES[site_id]
                        new_base = BaseSite(
                            f"{site['name'].split(' (')[0]} Base", t,
                            campaign_rng, site_id=site_id)
                        # the lander IS the colony: remaining tank contents
                        # pour into the buffers, the crew become residents
                        poured: dict[str, float] = {}
                        for row in av0.vessel.rows:
                            for res, kg in row.fill.items():
                                buf = new_base.net.buffers.get(res)
                                if buf is not None and kg > 0.0:
                                    take = min(kg, buf.capacity - buf.level)
                                    buf.level += take
                                    poured[res] = poured.get(res, 0.0) + take
                        new_base.crew = list(av0.crew)
                        new_base.apply_crew_effects(crew)
                        bases.append(new_base)
                        vessels.remove(av0)
                        active_idx = 0
                        node = None
                        surface_open = False
                        det = "  ".join(f"+{kg / 1e3:,.1f}t {res}"
                                        for res, kg in sorted(poured.items())
                                        if kg > 50.0)
                        who = (f"   residents: {', '.join(new_base.crew)}"
                               if new_base.crew else "")
                        toast = (f"BASE FOUNDED at {site['name']}  {det}"
                                 f"{who}  (F2 to build)")
                        toast_until = t + 12
                        audio.play("paid")
                    elif action[0] == "refuel":
                        home = next(b for b in bases
                                    if b.site_id == av0.landed_at)
                        home.advance(t, crew)
                        moved: dict[str, float] = {}
                        for row in av0.vessel.rows:
                            tank = av0.vessel.part(row).get("tank")
                            if not tank:
                                continue
                            cap_kg = tank["capacity_t"] * 1_000.0
                            for res, share in tank["mixture"].items():
                                buf = home.net.buffers.get(res)
                                if buf is None:
                                    continue
                                room = cap_kg * share - row.fill.get(res, 0.0)
                                take = min(max(room, 0.0), buf.level)
                                if take > 0.0:
                                    buf.level -= take
                                    row.fill[res] = (row.fill.get(res, 0.0)
                                                     + take)
                                    moved[res] = moved.get(res, 0.0) + take
                        if moved:
                            det = "  ".join(f"+{kg / 1e3:,.2f}t {res}" for
                                            res, kg in sorted(moved.items()))
                            toast = (f"REFUELED FROM {home.name}: {det} — "
                                     f"dv {av0.dv_remaining:,.0f} m/s")
                            toast_until = t + 10
                            surface_open = False
                            audio.play("paid")
                        else:
                            toast = ("nothing transferred — tanks full or "
                                     "buffers empty")
                            toast_until = t + 5
                            audio.play("warn")
                    elif action[0] == "board":
                        home = next(b for b in bases
                                    if b.site_id == av0.landed_at)
                        room = av0.crew_capacity - len(av0.crew)
                        taking = home.crew[:max(room, 0)]
                        if taking:
                            home.crew = home.crew[len(taking):]
                            av0.crew.extend(taking)
                            crew_refit(av0)
                            home.apply_crew_effects(crew)
                            toast = (f"BOARDED: {', '.join(taking)} — "
                                     f"LSS {av0.lss_margin_days:,.0f} d")
                            toast_until = t + 8
                            surface_open = False
                            audio.play("blip")
                        else:
                            toast = "no seats free for the colonists"
                            toast_until = t + 5
                            audio.play("warn")
                    elif action[0] == "load_parts":
                        from aphelion.sim.industry.yard import PARTS_CARGO
                        home = next(b for b in bases
                                    if b.site_id == av0.landed_at)
                        home.advance(t, crew)
                        moved_c: dict[str, float] = {}
                        for res in PARTS_CARGO:
                            buf = home.net.buffers.get(res)
                            if buf is None or buf.level <= 0.0:
                                continue
                            took = av0.load_cargo(res, buf.level)
                            if took > 0.0:
                                buf.level -= took
                                moved_c[res] = took
                        if moved_c:
                            det = "  ".join(f"+{kg / 1e3:,.2f}t {res}"
                                            for res, kg in
                                            sorted(moved_c.items()))
                            toast = (f"CARGO LOADED: {det} — bays "
                                     f"{av0.cargo_kg / 1e3:,.1f}/"
                                     f"{av0.cargo_cap_kg / 1e3:,.0f} t")
                            toast_until = t + 8
                            surface_open = False
                            audio.play("clunk")
                        else:
                            toast = "bays full or shelves empty"
                            toast_until = t + 5
                            audio.play("warn")
                    elif action[0] == "unload_cargo":
                        home = next(b for b in bases
                                    if b.site_id == av0.landed_at)
                        home.advance(t, crew)
                        from aphelion.game.basebuild import (
                            ensure_buffers as _ensb)
                        for res, kg in list(av0.cargo.items()):
                            _ensb(home.net, {"inputs": {res: 1},
                                             "outputs": {}})
                            buf = home.net.buffers[res]
                            put = min(kg, buf.capacity - buf.level)
                            buf.level += put
                            if put >= kg - 1e-9:
                                av0.cargo.pop(res)
                            else:
                                av0.cargo[res] = kg - put
                        toast = f"cargo offloaded to {home.name}"
                        toast_until = t + 6
                        surface_open = False
                        audio.play("clunk")
                    elif action[0] == "land":
                        sid = action[1]
                        site = SITES[sid]
                        ok_land, why = av0.can_land(site, t)
                        if not ok_land:
                            toast, toast_until = f"no descent: {why}", t + 6
                            audio.play("warn")
                        elif site.get("landing_class") == "A":
                            # dock-mode microgravity world: anchor, don't fly
                            av0._pay_dv(site.get("land_dv", 10.0))
                            surface_open = False
                            if av0.land_at(sid, site, t):
                                burn_glow = 0.4
                                msg = f"ANCHORED: {site['name']}"
                                msg += surface_award(av0, sid, site, t)
                                toast, toast_until = msg, t + 10
                                audio.play("soi")
                        elif site.get("aero"):
                            # the atmosphere adjudicates the entry first
                            body_b = tree.body(av0.frame_id)
                            rx0, ry0, vx0, vy0 = av0.state(t)
                            r0 = math.hypot(rx0, ry0)
                            r_pe = body_b.radius + 40e3
                            a_d = 0.5 * (r0 + r_pe)
                            r_int = min(r0, body_b.radius + 120e3)
                            v_int = tr.visviva_speed(body_b.mu, r_int, a_d)
                            v_pe = tr.visviva_speed(body_b.mu, r_pe, a_d)
                            cosg = min(1.0, (r_pe * v_pe) / (r_int * v_int))
                            beta = (av0.vessel.total_mass_kg()
                                    / max(av0.vessel.cd_a_m2, 0.5))
                            res = fly_entry(av0.frame_id, body_b.mu,
                                            body_b.radius, r_int, v_int,
                                            math.acos(cosg), beta)
                            has_capsule = any(
                                db.parts[r.part_id]["type"] == "crew"
                                for r in av0.vessel.rows)
                            rating = (_CAPSULE_HEAT_W_M2 if has_capsule
                                      else _BARE_HEAT_W_M2)
                            av0._pay_dv(80.0)        # deorbit targeting burn
                            surface_open = False
                            if res.peak_heating_w_m2 > rating:
                                for cn in list(av0.crew):
                                    crew.pop(cn, None)
                                vessels.remove(av0)
                                active_idx = 0
                                node = None
                                toast = (f"{av0.name} BURNED UP ON ENTRY — "
                                         f"{res.peak_heating_w_m2/1e6:,.1f} "
                                         f"MW/m² vs {rating/1e6:,.1f} rated")
                                toast_until = t + 12
                                audio.play("alarm")
                            else:
                                if (res.peak_g > _ENTRY_G_LIMIT
                                        and av0.crew):
                                    lost = list(av0.crew)
                                    for cn in lost:
                                        crew.pop(cn, None)
                                    av0.crew = []
                                    toast = (f"{res.peak_g:,.0f} g ON ENTRY"
                                             f" — crew lost: "
                                             + ", ".join(lost))
                                    toast_until = t + 12
                                    audio.play("alarm")
                                if site.get("kind") == "aerostat":
                                    # aerostat: balloon deploy, no descent
                                    if av0.land_at(sid, site, t):
                                        burn_glow = 0.8
                                        msg = (f"AEROSTAT DEPLOYED: "
                                               f"{site['name']}")
                                        msg += surface_award(av0, sid,
                                                             site, t)
                                        toast, toast_until = msg, t + 10
                                        audio.play("soi")
                                else:
                                    descent = LiveDescent.from_entry(
                                        av0.vessel, body_b.mu, body_b.radius,
                                        sid, h0=8e3,
                                        v_h=max(80.0, res.v_final * 0.7),
                                        v_v=-max(60.0, res.v_final * 0.5))
                                    descent_av = av0
                                    descent_warp, descent_acc = 1.0, 0.0
                                    scene = "descent"
                                    audio.play("blip")
                        else:
                            # vacuum world: deorbit, coast, FLY the braking
                            body_b = tree.body(av0.frame_id)
                            rx0, ry0, vx0, vy0 = av0.state(t)
                            descent = LiveDescent.from_orbit(
                                av0.vessel, body_b.mu, body_b.radius, sid,
                                rx0, ry0, vx0, vy0, t)
                            descent_av = av0
                            descent_warp, descent_acc = 1.0, 0.0
                            surface_open = False
                            scene = "descent"
                            audio.play("blip")
            elif event.type == pygame.KEYDOWN and crew_open:
                cands = candidates(crew)
                roster = list(crew)
                if event.key in (pygame.K_ESCAPE, pygame.K_k):
                    crew_open = False
                elif event.key == pygame.K_TAB:
                    crew_focus = ("roster" if crew_focus == "cands"
                                  else "cands")
                    audio.play("tick")
                elif event.key == pygame.K_UP:
                    if crew_focus == "cands" and cands:
                        crew_cursor = (crew_cursor - 1) % len(cands)
                    elif roster:
                        roster_cursor = (roster_cursor - 1) % len(roster)
                    audio.play("tick")
                elif event.key == pygame.K_DOWN:
                    if crew_focus == "cands" and cands:
                        crew_cursor = (crew_cursor + 1) % len(cands)
                    elif roster:
                        roster_cursor = (roster_cursor + 1) % len(roster)
                    audio.play("tick")
                elif event.key == pygame.K_RETURN:
                    if crew_focus == "cands" and cands:
                        cand = cands[crew_cursor % len(cands)]
                        if program.spend(t, cand.hire_cost,
                                         f"hire {cand.name}"):
                            crew[cand.name] = cand
                            toast = (f"HIRED {cand.name} "
                                     f"({cand.role}-{cand.skill}) for "
                                     f"${cand.hire_cost/1e6:,.0f}M")
                            toast_until = t + 6
                            audio.play("paid")
                        else:
                            toast = (f"hiring {cand.name} needs "
                                     f"${cand.hire_cost/1e6:,.0f}M")
                            toast_until = t + 5
                            audio.play("alarm")
                    elif roster:
                        name = roster[roster_cursor % len(roster)]
                        member = crew[name]
                        aboard_any = any(name in v.crew for v in vessels) \
                            or any(name in b.crew for b in bases)
                        if member.skill >= 3:
                            toast = f"{name} is already skill 3"
                            toast_until = t + 4
                            audio.play("warn")
                        elif aboard_any:
                            toast = (f"{name} must be ON EARTH to train")
                            toast_until = t + 5
                            audio.play("warn")
                        elif not member.available(t):
                            toast = f"{name} is already in training"
                            toast_until = t + 4
                            audio.play("warn")
                        elif program.spend(t, member.TRAIN_COST,
                                           f"train {name}"):
                            member.skill += 1
                            member.busy_until = (t + member.TRAIN_DAYS
                                                 * 86_400.0)
                            toast = (f"{name} in training — {member.role}-"
                                     f"{member.skill} in "
                                     f"{member.TRAIN_DAYS:.0f} days "
                                     f"(−${member.TRAIN_COST/1e6:,.0f}M)")
                            toast_until = t + 8
                            audio.play("paid")
                        else:
                            toast = (f"training costs "
                                     f"${member.TRAIN_COST/1e6:,.0f}M")
                            toast_until = t + 5
                            audio.play("alarm")
            elif event.type == pygame.KEYDOWN and base_screen:
                from aphelion.game.basebuild import CATALOG, catalog_for_kind
                site_b = bases[base_idx % len(bases)] if bases else None
                if site_b is None or event.key in (pygame.K_ESCAPE,
                                                   pygame.K_F2):
                    base_screen = False
                else:
                    avail = catalog_for_kind(SITES[site_b.site_id]["kind"])
                    mods = site_b.net.modules
                    if event.key == pygame.K_n:
                        base_idx = (base_idx + 1) % len(bases)
                        base_cursor = module_cursor = 0
                        audio.play("tick")
                    elif event.key == pygame.K_TAB:
                        base_focus = ("construct"
                                      if base_focus == "modules"
                                      else "modules")
                        audio.play("tick")
                    elif event.key == pygame.K_l:
                        base_log_open = not base_log_open
                    elif event.key == pygame.K_LEFT and mods:
                        base_focus = "modules"
                        module_cursor = (module_cursor - 1) % len(mods)
                        audio.play("tick")
                    elif event.key == pygame.K_RIGHT and mods:
                        base_focus = "modules"
                        module_cursor = (module_cursor + 1) % len(mods)
                        audio.play("tick")
                    elif event.key == pygame.K_UP:
                        base_focus = "construct"
                        base_cursor = (base_cursor - 1) % len(avail)
                        audio.play("tick")
                    elif event.key == pygame.K_DOWN:
                        base_focus = "construct"
                        base_cursor = (base_cursor + 1) % len(avail)
                        audio.play("tick")
                    elif event.key == pygame.K_RETURN:
                        if base_focus == "construct" and avail:
                            ok, msg = site_b.build(
                                avail[base_cursor % len(avail)], t,
                                research, program)
                            toast, toast_until = msg, t + 6
                            audio.play("paid" if ok else "alarm")
                        elif mods:
                            msg = site_b.toggle_module(
                                mods[module_cursor % len(mods)].module_id, t)
                            toast, toast_until = msg, t + 5
                            audio.play("blip")
            elif event.type == pygame.KEYDOWN and research_open:
                tech_ids = _tech_order(db, research)
                if event.key in (pygame.K_ESCAPE, pygame.K_r):
                    research_open = False
                elif event.key == pygame.K_TAB:
                    research_view = {"tree": "ed", "ed": "codex",
                                     "codex": "tree"}[research_view]
                    audio.play("tick")
                elif research_view != "tree":
                    pass                       # data/codex panes are read-only
                elif event.key == pygame.K_UP:
                    research_cursor = (research_cursor - 1) % len(tech_ids)
                    audio.play("tick")
                elif event.key == pygame.K_DOWN:
                    research_cursor = (research_cursor + 1) % len(tech_ids)
                    audio.play("tick")
                elif event.key in (pygame.K_LEFT, pygame.K_RIGHT):
                    # jump a whole branch column
                    cur = tech_ids[research_cursor % len(tech_ids)]
                    bi = _BRANCH_ORDER.index(db.tech[cur].get("category", "SC"))
                    step = 1 if event.key == pygame.K_RIGHT else -1
                    for hop in range(1, len(_BRANCH_ORDER)):
                        want_br = _BRANCH_ORDER[(bi + step * hop)
                                                % len(_BRANCH_ORDER)]
                        nxt = next((k for k, n in enumerate(tech_ids)
                                    if db.tech[n].get("category") == want_br),
                                   None)
                        if nxt is not None:
                            research_cursor = nxt
                            audio.play("tick")
                            break
                elif event.key == pygame.K_RETURN:
                    nid = tech_ids[research_cursor % len(tech_ids)]
                    nd = db.tech[nid]
                    if research.unlock(db, nid, t):
                        toast = f"RESEARCHED: {nd['name']}"
                        toast_until = t + 8.0
                        audio.play("paid")
                    else:
                        missing = research.missing_ed(db, nid)
                        dscs = db.by_type("discoveries")
                        need_dsc = [d for d in nd.get("discovery_prereqs", [])
                                    if d not in research.discoveries]
                        if nid in research.unlocked:
                            toast = "already researched"
                        elif need_dsc:
                            names = ", ".join(dscs[d]["name"]
                                              for d in need_dsc)
                            toast = f"requires discovery: {names}"
                        elif missing:
                            toast = "needs data: " + ", ".join(
                                f"{f} {h:,.0f}/{n:,.0f}"
                                for f, h, n in missing)
                        elif research.science < research.discounted_cost(
                                db, nid):
                            toast = (f"insufficient science "
                                     f"({research.discounted_cost(db, nid):,.0f}"
                                     f" needed)")
                        else:
                            toast = "prerequisite nodes not researched"
                        toast_until = t + 6.0
                        audio.play("alarm")
            elif event.type == pygame.KEYDOWN and builder_open:
                ground = sorted(
                    n for n in crew
                    if n not in {x for v in vessels for x in v.crew}
                    and n not in {x for b in bases for x in b.crew}
                    and crew[n].available(t))
                do_launch = False
                if builder.assign_open:
                    cap = builder.crew_capacity()
                    if event.key == pygame.K_ESCAPE:
                        builder.assign_open = False
                        builder.message = "crew assignment cancelled"
                    elif event.key == pygame.K_UP and ground:
                        builder.assign_cursor = (builder.assign_cursor - 1) % len(ground)
                        audio.play("tick")
                    elif event.key == pygame.K_DOWN and ground:
                        builder.assign_cursor = (builder.assign_cursor + 1) % len(ground)
                        audio.play("tick")
                    elif event.key in (pygame.K_RETURN, pygame.K_SPACE) and ground:
                        name = ground[builder.assign_cursor % len(ground)]
                        if name in builder.crew_pick:
                            builder.crew_pick.remove(name)
                        elif len(builder.crew_pick) < cap:
                            builder.crew_pick.append(name)
                        else:
                            builder.message = f"capacity is {cap}"
                            audio.play("warn")
                        audio.play("tick")
                    elif event.key == pygame.K_l:
                        do_launch = True
                elif event.key in (pygame.K_b, pygame.K_ESCAPE):
                    builder_open = False
                elif event.key == pygame.K_TAB:
                    builder.focus = ("stack" if builder.focus == "catalog"
                                     else "catalog")
                    audio.play("tick")
                elif event.key == pygame.K_UP:
                    if builder.focus == "stack" and builder.flat():
                        builder.stack_cursor = max(0, builder.stack_cursor - 1)
                    else:
                        builder.move_cursor(-1)
                    audio.play("tick")
                elif event.key == pygame.K_DOWN:
                    if builder.focus == "stack" and builder.flat():
                        builder.stack_cursor = min(len(builder.flat()) - 1,
                                                   builder.stack_cursor + 1)
                    else:
                        builder.move_cursor(+1)
                    audio.play("tick")
                elif event.key in (pygame.K_LEFT, pygame.K_RIGHT):
                    builder.cycle_filter(
                        1 if event.key == pygame.K_RIGHT else -1)
                    audio.play("tick")
                elif event.key == pygame.K_LEFTBRACKET:
                    builder.focus = "stack"
                    builder.move_part(-1)
                elif event.key == pygame.K_RIGHTBRACKET:
                    builder.focus = "stack"
                    builder.move_part(+1)
                elif event.key == pygame.K_RETURN:
                    builder.add()
                    audio.play("blip")
                elif event.key in (pygame.K_BACKSPACE, pygame.K_DELETE):
                    builder.remove()
                elif event.key == pygame.K_s and (
                        event.mod & pygame.KMOD_SHIFT):
                    builder.split_stage()
                elif event.key == pygame.K_s:
                    builder.new_stage()
                elif pygame.K_1 <= event.key <= pygame.K_6:
                    slot = str(event.key - pygame.K_0)
                    designs = load_designs()
                    if event.mod & pygame.KMOD_CTRL:
                        vessel = builder.build_vessel()
                        if vessel is not None:
                            stats_bp = vessel.stage_stats()
                            total = sum(s["dv_vac"] for s in stats_bp)
                            top = next((s for s in reversed(builder.stack)
                                        if s), ["?"])
                            nm = (f"{db.parts[top[-1]]['name'].split(' (')[0]}"
                                  f" / {total:,.0f} m/s")
                            designs[slot] = {
                                "name": nm,
                                "stack": [list(s) for s in builder.stack]}
                            save_designs(designs)
                            builder.message = f"blueprint {slot} saved: {nm}"
                            audio.play("blip")
                    elif slot in designs:
                        builder.load_stack(designs[slot]["stack"])
                        builder.message = (f"blueprint {slot} loaded: "
                                           f"{designs[slot]['name']}")
                        audio.play("blip")
                    else:
                        builder.message = f"blueprint slot {slot} is empty"
                elif event.key == pygame.K_l:
                    cap = builder.crew_capacity()
                    if (cap > 0 and ground
                            and builder.build_vessel() is not None):
                        builder.assign_open = True
                        builder.assign_cursor = 0
                        builder.crew_pick = [n for n in builder.crew_pick
                                             if n in ground][:cap]
                        builder.message = (f"assign up to {cap} crew "
                                           f"(ENTER toggles) — L launches")
                    else:
                        do_launch = True
                if do_launch:
                    vessel = builder.build_vessel()
                    if vessel is None:
                        builder.message = "nothing to launch"
                    else:
                        cost = builder.price(vessel)
                        if not program.spend(t, cost, f"launch {len(vessel.rows)} parts"):
                            builder.message = f"insufficient funds (${cost/1e6:,.0f}M)"
                            audio.play("alarm")
                        else:
                            # to the pad — the ascent is FLOWN (KSP-style),
                            # not adjudicated
                            live = LiveAscent.from_pad(
                                vessel, "core:earth",
                                tree.body("core:earth").mu,
                                tree.body("core:earth").radius, 86_164.1)
                            live_stack = [list(s) for s in builder.stack if s]
                            launch_cost = cost
                            pending_crew = list(builder.crew_pick)
                            pending_assigned = builder.assign_open
                            builder.assign_open = False
                            ascent_warp, ascent_acc = 1.0, 0.0
                            ascent_event_count = 0
                            node = None
                            builder_open = False
                            scene = "ascent"
                            milestones.add("launched")   # E-13 first First
                            audio.play("blip")
            elif event.type == pygame.KEYDOWN:
                shift = event.mod & pygame.KMOD_SHIFT
                step = 100.0 if shift else 10.0
                if event.key == pygame.K_ESCAPE:
                    pause_open = True
                    pause_cursor = 0
                elif event.key == pygame.K_r:
                    research_open = True
                elif event.key == pygame.K_F5:
                    toast, toast_until = do_quicksave(), t + 5.0
                    audio.play("blip")
                elif event.key == pygame.K_F9:
                    load_save = True
                elif event.key == pygame.K_b:
                    builder_open = True
                elif event.key == pygame.K_n:
                    if node is None:
                        node = {"t_node": t + 600.0, "dvp": 0.0, "dvr": 0.0,
                                "armed": False}
                        toast, toast_until = (
                            "NODE: arrows dv (CTRL 1/SHIFT 100)  [/] time "
                            "(min/hr/day)  P/A snap Pe/Ap  O +1 orbit  "
                            "ENTER arm  W warp", t + 10)
                    else:
                        node = None
                        warp_to_node = False
                        toast, toast_until = "node cancelled", t + 4
                elif event.key == pygame.K_j:
                    net_overlay = not net_overlay
                    if net_overlay:
                        toast, toast_until = (
                            "COMMS NETWORK — every node's route home, "
                            "rate-colored; J closes", t + 6)
                    audio.play("tick")
                elif event.key == pygame.K_BACKSPACE:
                    # A-6 master alarm + acknowledge: releases warp caps
                    # (live Class 1 latches until the condition resolves)
                    abus.master_alarm(t)
                    _n_ack = 0
                    for _al in abus.active(t):
                        if not _al.acked:
                            abus.acknowledge(_al.aid)
                            _n_ack += 1
                    if _n_ack:
                        toast = (f"{_n_ack} alert"
                                 f"{'s' if _n_ack > 1 else ''} "
                                 f"acknowledged — warp caps released")
                        toast_until = t + 5
                        audio.play("blip")
                elif node is not None and not node["armed"] and event.key in (
                        pygame.K_UP, pygame.K_DOWN, pygame.K_LEFT, pygame.K_RIGHT,
                        pygame.K_LEFTBRACKET, pygame.K_RIGHTBRACKET,
                        pygame.K_p, pygame.K_a, pygame.K_o, pygame.K_RETURN):
                    ctrl = event.mod & pygame.KMOD_CTRL
                    nstep = 1.0 if ctrl else 100.0 if shift else 10.0
                    tstep = 86_400.0 if ctrl else 3_600.0 if shift else 60.0
                    av0 = vessels[active_idx % len(vessels)] if vessels else None
                    if event.key == pygame.K_UP:
                        node["dvp"] += nstep
                    elif event.key == pygame.K_DOWN:
                        node["dvp"] -= nstep
                    elif event.key == pygame.K_RIGHT:
                        node["dvr"] += nstep
                    elif event.key == pygame.K_LEFT:
                        node["dvr"] -= nstep
                    elif event.key == pygame.K_LEFTBRACKET:
                        node["t_node"] = max(t + 60.0, node["t_node"] - tstep)
                    elif event.key == pygame.K_RIGHTBRACKET:
                        node["t_node"] += tstep
                    elif (event.key in (pygame.K_p, pygame.K_a)
                          and av0 is not None and av0.elements.alpha > 0):
                        t_pe, t_ap = _next_apsis_times(av0.elements,
                                                       max(t + 60.0,
                                                           node["t_node"]
                                                           - av0.elements.period))
                        want = t_pe if event.key == pygame.K_p else t_ap
                        while want <= t + 60.0:
                            want += av0.elements.period
                        node["t_node"] = want
                        toast = ("node snapped to next "
                                 + ("periapsis" if event.key == pygame.K_p
                                    else "apoapsis"))
                        toast_until = t + 4
                    elif (event.key == pygame.K_o and av0 is not None
                          and av0.elements.alpha > 0):
                        node["t_node"] += av0.elements.period
                    elif event.key == pygame.K_RETURN:
                        need = math.hypot(node["dvp"], node["dvr"])
                        if (av0 is None or av0.landed_at is not None
                                or need > av0.dv_remaining):
                            toast, toast_until = "node exceeds dv budget", t + 5
                            audio.play("alarm")
                        else:
                            node["armed"] = True
                            toast, toast_until = ("node ARMED — W warps to "
                                                  "the burn"), t + 6
                            audio.play("blip")
                elif (node is not None and node["armed"]
                      and event.key == pygame.K_RETURN):
                    node["armed"] = False
                    warp_to_node = False
                    toast, toast_until = "node disarmed for editing", t + 4
                elif (event.key == pygame.K_w and node is not None
                      and node["armed"]):
                    warp_to_node = True
                    toast, toast_until = ("warping to the burn — any warp "
                                          "key cancels"), t + 5
                    audio.play("blip")
                elif event.key == pygame.K_F2:
                    base_screen = not base_screen
                elif event.key in (pygame.K_v, pygame.K_e, pygame.K_u,
                                   pygame.K_t) and not vessels:
                    toast, toast_until = "no vessel — build one (B)", t + 5
                    audio.play("warn")
                elif event.key == pygame.K_v and vessels:
                    active_idx = (active_idx + 1) % len(vessels)
                    node = None
                    av0 = vessels[active_idx]
                    toast, toast_until = f"ACTIVE: {av0.name}", t + 4
                    audio.play("blip")
                elif event.key == pygame.K_e and vessels:
                    # rendezvous: pay the velocity match, then FLY the
                    # terminal approach (prox-ops scene)
                    av0 = vessels[active_idx % len(vessels)]
                    best_tgt, best_cost = None, float("inf")
                    for other in vessels:
                        c = av0.rendezvous_cost(other, t, include_prox=False)
                        if c is not None and c < best_cost:
                            best_tgt, best_cost = other, c
                    if best_tgt is None:
                        toast = ("no dock target within 100 km of "
                                 f"{av0.name} — see NAV for range")
                        toast_until = t + 5
                        audio.play("warn")
                    elif av0.dv_remaining < best_cost + 2.0:
                        toast = (f"rendezvous needs {best_cost:,.0f} m/s "
                                 f"— exceeds propellant")
                        toast_until = t + 6
                        audio.play("alarm")
                    else:
                        # E8 pre-flight: matching port class, sound rings,
                        # and a despun hub (06 §3.3) — refused BEFORE the
                        # velocity match is paid
                        psize, soft, why = ports_sim.mate_plan(
                            av0.vessel, best_tgt.vessel)
                        rep_h = max(getattr(av0, "port_repair_h", 0.0),
                                    getattr(best_tgt, "port_repair_h", 0.0))
                        spin_max = max(getattr(av0, "spin_rpm", 0.0),
                                       getattr(best_tgt, "spin_rpm", 0.0))
                        if psize is None:
                            toast, toast_until = why, t + 8
                            audio.play("warn")
                        elif rep_h > 0.0:
                            toast = (f"docking ring damaged — {rep_h:,.0f} h"
                                     f" of repair left (an engineer aboard "
                                     f"or a landed base works it off)")
                            toast_until = t + 8
                            audio.play("warn")
                        elif spin_max > 0.5:
                            toast = ("despin below 0.5 rpm to dock — "
                                     "ports mate at a still hub (F7)")
                            toast_until = t + 7
                            audio.play("warn")
                        else:
                            av0._pay_dv(best_cost)
                            body_p = tree.body(av0.frame_id)
                            a_t = max(abs(best_tgt.elements.a),
                                      body_p.radius + 100e3)
                            budget = min(3.0 * av0.prox_ops_dv,
                                         max(2.0, av0.dv_remaining))
                            prox = ProxOps(
                                n=math.sqrt(body_p.mu / a_t ** 3),
                                budget_dv=budget, port_size=psize,
                                magnetic=soft)
                            prox_chaser, prox_target = av0, best_tgt
                            prox_trail = []
                            prox_seen = True
                            node = None
                            scene = "proxops"
                            toast = (f"rendezvous {best_cost:,.0f} m/s paid"
                                     f" — fly the approach to the DK-"
                                     f"{psize}"
                                     + (" (arm-assisted capture)"
                                        if soft else ""))
                            toast_until = t + 6
                            audio.play("burn")
                elif event.key == pygame.K_u and vessels:
                    av0 = vessels[active_idx % len(vessels)]
                    split = av0.undock_last(t, next_vid)
                    if split is None:
                        toast, toast_until = "nothing docked to release", t + 4
                    else:
                        next_vid += 1
                        vessels.append(split)
                        toast = (f"UNDOCKED: {split.name} free-flying — "
                                 f"spring separation "
                                 f"{FleetVessel.UNDOCK_SEP_MS:.1f} m/s")
                        toast_until = t + 6
                        audio.play("clunk")
                elif event.key == pygame.K_t and vessels:
                    av0 = vessels[active_idx % len(vessels)]
                    moved = av0.crossfeed()
                    if moved > 0.0:
                        toast = (f"CROSSFEED: {moved/1e3:,.2f} t into the "
                                 f"active stage — dv now "
                                 f"{av0.dv_remaining:,.0f} m/s")
                        toast_until = t + 6
                        audio.play("blip")
                    else:
                        bad_j = [p for p in
                                 getattr(av0, "dock_joint_ports", [])
                                 if p != "L"]
                        toast = (f"no fluid lines through a DK-{bad_j[0]} "
                                 f"joint — only a DK-L berth crossfeeds"
                                 if bad_j else "no propellant to crossfeed")
                        toast_until = t + 5
                elif event.key == pygame.K_i and vessels:
                    # board the active stack: every pressurized part is a
                    # walkable room (06 §3 station interiors)
                    av0 = vessels[active_idx % len(vessels)]
                    from aphelion.render.interior_art import vessel_rooms
                    rooms_v = vessel_rooms(av0.vessel)
                    if not rooms_v:
                        toast = ("no pressurized modules aboard — fit a "
                                 "hab, lab, or capsule")
                        toast_until = t + 6
                        audio.play("warn")
                    else:
                        interior_vessel = av0
                        interior_home = None
                        interior_rooms = tuple(k for k, _, _ in rooms_v)
                        interior_labels = tuple((n, i2)
                                                for _, n, i2 in rooms_v)
                        interior_x = 4.0
                        interior_face, interior_frame = 1, 0.0
                        scene = "interior"
                        toast = (f"ABOARD {av0.name} — E at a console "
                                 f"reads the module; the airlock exits")
                        toast_until = t + 7
                        audio.play("clunk")
                elif event.key == pygame.K_g:
                    if vessels:
                        surface_open = not surface_open
                        surface_cursor = 0
                    else:
                        toast, toast_until = "no vessel — build one (B)", t + 5
                        audio.play("alarm")
                elif event.key == pygame.K_p:
                    planner_open = True
                    planner_cursor = 0
                elif event.key == pygame.K_o:
                    contracts_open = True
                    contracts_scroll = 0
                elif event.key == pygame.K_SPACE:
                    paused = not paused
                elif event.key == pygame.K_PERIOD:
                    warp_idx = min(warp_idx + 1, len(_WARP_LADDER) - 1)
                    warp_to_node = False
                elif event.key == pygame.K_COMMA:
                    warp_idx = max(warp_idx - 1, 0)
                    warp_to_node = False
                elif event.key == pygame.K_TAB:
                    focus_idx = (focus_idx + (-1 if shift else 1)) % len(focus_order)
                elif event.key == pygame.K_c:
                    focus_idx = 0
                elif event.key == pygame.K_F1:
                    help_open = True
                elif event.key == pygame.K_h:
                    tutorial.visible = not tutorial.visible
                elif event.key == pygame.K_k:
                    crew_open = True
                    crew_cursor = 0
                elif event.key == pygame.K_F7:
                    station_open = True
                elif event.key in (pygame.K_x, pygame.K_z, pygame.K_a, pygame.K_d):
                    av0 = vessels[active_idx % len(vessels)] if vessels else None
                    if av0 is None:
                        toast, toast_until = "no vessel — build one (B)", t + 5
                        audio.play("alarm")
                        continue
                    if av0.landed_at is not None:
                        toast, toast_until = ("vessel is LANDED — G to "
                                              "relaunch"), t + 5
                        audio.play("alarm")
                        continue
                    dvp = {pygame.K_x: (+step, 0.0), pygame.K_z: (-step, 0.0),
                           pygame.K_a: (0.0, +step), pygame.K_d: (0.0, -step)}[event.key]
                    veto = docked_burn_veto(av0)
                    if veto is not None:
                        toast, toast_until = veto, t + 8
                        audio.play("warn")
                        continue
                    crx0, cry0, cvx0, cvy0 = av0.state(t)
                    if not av0.burn(t, *dvp):
                        toast = "INSUFFICIENT PROPELLANT — build a new vessel (B)"
                        toast_until = t + 6
                        audio.play("alarm")
                        continue
                    names = {pygame.K_x: "prograde +", pygame.K_z: "retrograde -",
                             pygame.K_a: "radial-out +", pygame.K_d: "radial-in -"}
                    toast = f"{names[event.key]}{step:.0f} m/s"
                    toast_until = t + 5
                    burn_glow = 0.6
                    audio.play("burn")
                    frx0, fry0, _, _ = tree.state_in_root(av0.frame_id, t)
                    px0 = cam.world_to_screen(frx0 + crx0, fry0 + cry0)
                    v0n = math.hypot(cvx0, cvy0) or 1.0
                    # exhaust plume opposes the dv direction (screen y flips)
                    sgn = -1.0 if event.key == pygame.K_x else 1.0
                    particles.emit_burn(px0[0], px0[1],
                                        sgn * cvx0 / v0n, -sgn * cvy0 / v0n)
            elif (event.type in (pygame.MOUSEMOTION, pygame.MOUSEBUTTONDOWN,
                                 pygame.MOUSEWHEEL)
                  and (pause_open or help_open or surface_open or crew_open
                       or base_screen or research_open or builder_open
                       or planner_open or contracts_open)
                  and scene == "flight"):
                # every overlay is mouse-first: hover selects, click acts,
                # wheel scrolls, right-click closes — by re-posting the
                # exact key the keyboard path already handles
                top = ("pause" if pause_open else "help" if help_open
                       else "contracts" if contracts_open
                       else "planner" if planner_open
                       else "surface" if surface_open
                       else "crew" if crew_open
                       else "base" if base_screen
                       else "research" if research_open else "builder")

                def _post(key_const):
                    pygame.event.post(pygame.event.Event(
                        pygame.KEYDOWN, key=key_const, mod=0))

                def _row_at(pos):
                    for rect, idx in overlay_rects.get(top, []):
                        if rect.collidepoint(pos):
                            return idx
                    return None

                def _set_cursor(idx) -> None:
                    nonlocal pause_cursor, surface_cursor, crew_cursor
                    nonlocal base_cursor, research_cursor, planner_cursor
                    nonlocal base_focus, module_cursor
                    nonlocal crew_focus, roster_cursor
                    if top == "pause":
                        pause_cursor = idx
                    elif top == "planner":
                        planner_cursor = idx
                    elif top == "base" and idx >= 30_000:
                        base_focus = "modules"
                        module_cursor = idx - 30_000
                    elif top == "surface":
                        surface_cursor = idx
                    elif top == "crew":
                        if idx >= 40_000:
                            crew_focus = "roster"
                            roster_cursor = idx - 40_000
                        else:
                            crew_focus = "cands"
                            crew_cursor = idx
                    elif top == "base":
                        base_focus = "construct"
                        base_cursor = idx
                    elif top == "research":
                        research_cursor = idx
                    elif top == "builder":
                        if idx >= 20_000:
                            pass                   # filter tabs: click-only
                        elif builder.assign_open:
                            builder.assign_cursor = idx
                        elif idx >= 10_000:        # stack rows offset
                            builder.focus = "stack"
                            builder.stack_cursor = idx - 10_000
                        else:
                            builder.focus = "catalog"
                            builder.cursor = idx

                if event.type == pygame.MOUSEMOTION:
                    idx = _row_at(event.pos)
                    if idx is not None:
                        _set_cursor(idx)
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:
                        idx = _row_at(event.pos)
                        if (top == "builder" and idx is not None
                                and idx >= 20_000):
                            builder.filter_idx = ((idx - 20_000)
                                                  % len(builder.CATS))
                            builder.cursor = 0
                            builder._rebuild()
                            audio.play("tick")
                        elif (top == "base" and idx is not None
                              and idx >= 30_000):
                            _set_cursor(idx)   # select module; ENTER toggles
                            audio.play("tick")
                        elif idx is not None:
                            _set_cursor(idx)
                            _post(pygame.K_RETURN)
                    elif event.button == 3:
                        idx = _row_at(event.pos)
                        if (top == "builder" and idx is not None
                                and idx >= 10_000):
                            builder.focus = "stack"   # right-click removes
                            builder.stack_cursor = idx - 10_000
                            _post(pygame.K_BACKSPACE)
                        else:
                            _post(pygame.K_ESCAPE)
                elif event.type == pygame.MOUSEWHEEL and event.y:
                    _post(pygame.K_UP if event.y > 0 else pygame.K_DOWN)
            elif (event.type == pygame.MOUSEBUTTONDOWN and event.button == 3
                  and not (pause_open or builder_open or research_open
                           or base_screen or crew_open or surface_open
                           or help_open or planner_open
                           or contracts_open)):
                # right-click a body: set/clear the navigation TARGET
                mx, my = event.pos
                best = None
                best_d = 20.0 ** 2
                for px, py, fi in body_click_pts:
                    d = (px - mx) ** 2 + (py - my) ** 2
                    if d < best_d:
                        best, best_d = fi, d
                if best is not None and focus_order[best] != "core:sun":
                    bid = focus_order[best]
                    if target_id == bid:
                        target_id = None
                        toast, toast_until = "target cleared", t + 4
                    else:
                        target_id = bid
                        toast = (f"TARGET: {bid.split(':')[1]} — encounter "
                                 f"and closest-approach on the NAV panel")
                        toast_until = t + 6
                    audio.play("tick")
            elif (event.type == pygame.MOUSEBUTTONDOWN and event.button == 1
                  and not (pause_open or builder_open or research_open
                           or base_screen or crew_open or surface_open
                           or help_open or planner_open
                           or contracts_open)):
                mx, my = event.pos
                best_v = None
                best_d = 16.0 ** 2
                for px, py, vi in vessel_click_pts:
                    d = (px - mx) ** 2 + (py - my) ** 2
                    if d < best_d:
                        best_v, best_d = vi, d
                if best_v is not None:
                    active_idx = best_v
                    node = None
                    focus_idx = 0
                    toast, toast_until = f"ACTIVE: {vessels[best_v].name}", t + 4
                    audio.play("blip")
                else:
                    best = None
                    best_d = 18.0 ** 2
                    for px, py, fi in body_click_pts:
                        d = (px - mx) ** 2 + (py - my) ** 2
                        if d < best_d:
                            best, best_d = fi, d
                    if best is not None:
                        focus_idx = best
                        audio.play("blip")
            elif event.type == pygame.MOUSEWHEEL:
                if event.y > 0:
                    cam.zoom_in(event.y)
                elif event.y < 0:
                    cam.zoom_out(-event.y)

        # scene transitions decided during event handling
        if start_new:
            (clock, vessels, active_idx, next_vid, program, campaign_rng,
             bases, crew, research, visited, visited_surface, milestones,
             tutorial, builder, difficulty, explore, yard_designs,
             ground_vehicles, node,
             warp_idx, paused,
             base_screen, builder_open, research_open, crew_warned,
             last_dose_t, toast,
             toast_until) = campaign_tuple(fresh_campaign(
                 start_new if start_new in _DIFFICULTIES else "DIRECTOR"))
            prestige, firsts_earned, chron, abus, prod_hwm = \
                restore_acts2(None)
            spe_sched, mars_wx = env_models(campaign_rng)
            env_state = {"spe_warned": -1.0, "spe_capped": False,
                         "storm_was": False}
            scene, pause_open, focus_idx = "flight", False, 0
            surface_open = False
        if load_save:
            if latest_save() is not None:
                try:
                    _st_l = loaded_campaign()
                    (clock, vessels, active_idx, next_vid, program,
                     campaign_rng, bases, crew, research, visited,
                     visited_surface, milestones, tutorial, builder,
                     difficulty, explore, yard_designs, ground_vehicles,
                     node,
                     warp_idx, paused, base_screen, builder_open,
                     research_open, crew_warned, last_dose_t, toast,
                     toast_until) = campaign_tuple(_st_l)
                    prestige, firsts_earned, chron, abus, prod_hwm = \
                        restore_acts2(_st_l.get("acts2"))
                    spe_sched, mars_wx = env_models(campaign_rng)
                    env_state = {"spe_warned": -1.0, "spe_capped": False,
                                 "storm_was": False}
                    scene, pause_open, focus_idx = "flight", False, 0
                    surface_open = False
                    toast, toast_until = "QUICKSAVE LOADED", clock.t + 5.0
                except Exception as exc:
                    toast, toast_until = f"load failed: {exc}", t + 8.0
                    audio.play("alarm")
            else:
                toast, toast_until = "no quicksave found", t + 4.0

        if ascent_abort and live is not None:
            program.earn(t, launch_cost, "launch revert")
            live = None
            scene = "flight"
            builder_open = True
            builder.message = "launch reverted — funds refunded"
            toast, toast_until = "LAUNCH REVERTED", t + 5.0
        if ascent_done and live is not None:
            if live.outcome == "orbit":
                clock.advance_analytic(t + live.t)
                t = clock.t
                body_a = tree.body(ascent_body_id)
                el_new = state_to_elements(live.x, live.y, live.vx,
                                           live.vy, t, body_a.mu)
                if ascent_av is not None:
                    # field relaunch: the SAME vessel returns to orbit
                    ascent_av.elements = el_new
                    ascent_av.landed_at = None
                    ascent_av._legs_t0 = -1.0
                    toast = (f"{ascent_av.name} BACK IN ORBIT — "
                             f"{ascent_av.dv_remaining:,.0f} m/s remains")
                    toast_until = t + 8.0
                else:
                    fv = FleetVessel(tree, "core:earth", el_new,
                                     live.vessel, f"Vessel-{next_vid}",
                                     next_vid, t_now=t)
                    next_vid += 1
                    # crew board: the pre-launch assignment when one was
                    # made, else auto-board whoever is free
                    aboard_elsewhere = {n for v in vessels for n in v.crew}
                    resident = {n for b in bases for n in b.crew}
                    free = [n for n in crew
                            if n not in aboard_elsewhere
                            and n not in resident
                            and crew[n].available(t)]
                    if pending_assigned:
                        fv.crew = [n for n in pending_crew
                                   if n in free][:fv.crew_capacity]
                    else:
                        fv.crew = free[:fv.crew_capacity]
                    pending_crew, pending_assigned = [], False
                    vessels.append(fv)
                    active_idx = len(vessels) - 1
                    milestones.add("orbited")
                    if fv.crew:
                        milestones.add("crewed_orbit")
                    research.award_milestone("orbit", ascent_body_id, t)
                    # burn-time ED for the stack that flew (0.05 ED/s)
                    for fam in _stage_engine_families(live.vessel):
                        research.accrue_burn_seconds(
                            db, fam, live.t,
                            env_class=_ascent_env(ascent_body_id))
                    crew_refit(fv)
                    crewed = (f" — crew: {', '.join(fv.crew)}"
                              if fv.crew else "")
                    toast = (f"{fv.name} IN ORBIT — "
                             f"{fv.dv_remaining:,.0f} m/s remaining{crewed}")
                    toast_until = t + 10.0
                audio.play("paid")
                focus_idx = 0
            else:
                if ascent_av is not None:
                    for cn in list(ascent_av.crew):
                        crew.pop(cn, None)
                    if ascent_av in vessels:
                        vessels.remove(ascent_av)
                    active_idx = 0
                    toast = (f"{ascent_av.name} LOST ON ASCENT — vehicle "
                             f"and crew gone")
                else:
                    toast = "LOSS OF VEHICLE — funds spent, vessel destroyed"
                toast_until = t + 8.0
                audio.play("alarm")
            live = None
            ascent_av = None
            ascent_body_id = "core:earth"
            scene = "flight"

        if descent_done and descent is not None:
            if descent.outcome == "landed" and descent_av is not None:
                clock.advance_analytic(t + descent.coast_s + descent.t)
                t = clock.t
                sid = descent.site_id
                site = SITES[sid]
                descent_av.finalize_landing(sid)
                burn_glow = 0.8
                msg = (f"TOUCHDOWN: {site['name']} at "
                       f"{descent.td_speed:,.1f} m/s")
                msg += surface_award(descent_av, sid, site, t)
                toast, toast_until = msg, t + 10
                audio.play("soi")
            elif descent_av is not None:
                lost_names = list(descent_av.crew)
                for cn in lost_names:
                    crew.pop(cn, None)
                if descent_av in vessels:
                    vessels.remove(descent_av)
                active_idx = 0
                node = None
                toast = (f"{descent_av.name} DESTROYED ON THE SURFACE"
                         + (f" — crew lost: {', '.join(lost_names)}"
                            if lost_names else ""))
                toast_until = t + 12
                audio.play("alarm")
            descent = None
            descent_av = None
            scene = "flight"

        if prox is not None and (prox_done or prox.outcome == "damage"):
            if (prox.outcome == "captured" and prox_chaser is not None
                    and prox_target is not None and prox_chaser in vessels
                    and prox_target in vessels):
                prox_chaser._pay_dv(min(prox.used_dv,
                                        prox_chaser.dv_remaining))
                cname = prox_chaser.name
                prox_chaser.dock_join(prox_target,
                                      port_size=prox.port_size)
                vessels.remove(prox_chaser)
                active_idx = vessels.index(prox_target)
                node = None
                milestones.add("docked")
                toast = (f"DOCKED through the DK-{prox.port_size}: "
                         f"{cname} -> {prox_target.name} "
                         f"({prox.used_dv:,.1f} m/s RCS"
                         + (f", {prox.bounces} bounce"
                            + ("s" if prox.bounces != 1 else "")
                            if prox.bounces else "")
                         + (")" if prox.port_size == "L"
                            else "; no fluid lines — DK-L crossfeeds)"))
                toast_until = t + 8
                audio.play("clunk")
            elif prox.outcome == "damage" and prox_chaser is not None:
                prox_chaser._pay_dv(min(prox.used_dv,
                                        prox_chaser.dv_remaining))
                prox_chaser.port_repair_h = 24.0
                toast = (f"HARD IMPACT — {prox_chaser.name}'s docking ring"
                         f" bent: 24 h of repairs before the next attempt")
                toast_until = t + 10
                audio.play("alarm")
            else:
                if prox_chaser is not None:
                    prox_chaser._pay_dv(min(prox.used_dv,
                                            prox_chaser.dv_remaining))
                toast = "approach aborted — vessels hold station"
                toast_until = t + 6
            prox = None
            prox_chaser = prox_target = None
            scene = "flight"

        # cut-to-black fade-in on every scene change (no hard cuts)
        ui_t += real_dt
        if scene != prev_scene:
            fade = 1.0 if prev_scene else 0.0
            prev_scene = scene
        # music mood rides the scene; engine rumble only where engines live
        audio.update(real_dt)
        audio.set_mood("tense" if scene in ("ascent", "descent", "proxops")
                       else "warm" if scene == "victory" or base_screen
                       else "calm")
        if scene not in ("ascent", "descent"):
            audio.set_engine(0.0)

        if scene == "ascent" and live is not None:
            # continuous stick: SHIFT/CTRL throttle, arrows pitch
            keys = pygame.key.get_pressed()
            if keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]:
                live.throttle_cmd = min(1.0, live.throttle_cmd
                                        + 0.8 * real_dt)
            if keys[pygame.K_LCTRL] or keys[pygame.K_RCTRL]:
                live.throttle_cmd = max(0.0, live.throttle_cmd
                                        - 0.8 * real_dt)
            if not live.prog:
                rate = 28.0 * real_dt
                if keys[pygame.K_LEFT] or keys[pygame.K_a]:
                    live.pitch_manual_deg = min(90.0,
                                                live.pitch_manual_deg + rate)
                if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
                    live.pitch_manual_deg = max(-15.0,
                                                live.pitch_manual_deg - rate)
            if live.q > 1.0 and ascent_warp > 4.0:
                ascent_warp = 4.0          # physics warp only out of atmo
            if live.ignited and live.outcome is None:
                ascent_acc += real_dt * ascent_warp
                n_steps = min(int(ascent_acc / 0.02), 6000)
                ascent_acc -= n_steps * 0.02
                for _ in range(n_steps):
                    live.step(0.02)
                    if live.outcome is not None:
                        if live.outcome == "orbit":
                            audio.play("paid")
                        else:
                            audio.play("boom")
                            shake = 1.5
                            flash = 1.0
                        break
            audio.set_engine(live.throttle_eff
                             if live.ignited and live.outcome is None
                             else 0.0)

            # ---- draw: sky fades to space with THIS body's air density ----
            screen.fill((6, 8, 14))
            nebula.draw(screen, None)
            rho0 = atmo_density(live.body_id, 0.0)
            rho_n = (min(1.0, atmo_density(live.body_id, max(live.h, 0.0))
                         / rho0) if rho0 > 0.0 else 0.0)
            sky_a = int(255.0 * rho_n ** 0.35)
            if sky_a > 2:
                sky_now = sky_surface(size, live.body_id)
                sky_now.set_alpha(sky_a)
                screen.blit(sky_now, (0, 0))
            elif rho0 <= 0.0:
                starfield.draw(screen, cam)

            # world scale: starts at 0.26 px/m on the pad and decays SLOWLY
            # enough that h*px_per_m keeps growing — the ground genuinely
            # falls away (gone by ~3 km) instead of hanging in frame forever
            px_per_m = max(0.0022, 0.26 * 5000.0 / (5000.0 + live.h))
            rocket_y = int(size[1] * 0.62)

            # camera shake: ignition/staging/loss impulses + max-q rattle
            if (live.q > 0.55 * live.params.q_limit
                    and live.outcome is None):
                shake = max(shake, min(0.4, 0.3 * live.q
                                       / live.params.q_limit))
            sox = int(7.0 * shake * math.sin(ui_t * 67.0))
            soy = int(6.0 * shake * math.sin(ui_t * 53.0 + 1.7))
            shake *= math.exp(-2.6 * real_dt)

            stack_now = live_stack[live.stages_spent:]
            tilt = -(90.0 - live.gamma_deg)
            # the VEHICLE stays readable: shrink only through the first
            # ~2 km of climb, then lock at 60% — never a 12% speck again
            rs = max(0.60, 2600.0 / (2600.0 + 0.9 * live.h))
            rkey = (live.stages_spent, int(tilt // 4), round(rs, 2))
            if rkey not in rot_cache:
                if len(rot_cache) > 160:
                    rot_cache.clear()
                base = (vessel_sprite(db, stack_now) if stack_now
                        else craft_icon(math.radians(live.gamma_deg), 16))
                rot_cache[rkey] = pygame.transform.rotozoom(base, tilt, rs)
            rspr = rot_cache[rkey]
            rx = size[0] // 2 - rspr.get_width() // 2 + sox
            ry = rocket_y - rspr.get_height() // 2 - int(12 * rs) + soy
            # ground anchors to the rocket's BASE so the vehicle never
            # draws buried in the terrain at low altitude
            ground_y = ry + rspr.get_height() + int(max(live.h, 0.0)
                                                    * px_per_m)
            theta = math.atan2(live.y, live.x)
            pad_ang = (theta - live.omega * live.t + math.pi) % (
                2.0 * math.pi) - math.pi
            downrange = pad_ang * live.radius
            pad_x = size[0] // 2 - int(downrange * px_per_m) + sox

            # clouds sweep past while there is air to hold them
            if rho0 > 0.0 and sky_a > 8 and live.h < 12_000.0:
                for c_alt, c_x in _CLOUD_DECK:
                    cy2 = ry + rspr.get_height() // 2 + int(
                        (live.h - c_alt) * px_per_m)
                    cx2 = int(c_x - downrange * px_per_m * 0.9) % (
                        size[0] + 300) - 150
                    if -60 < cy2 < size[1] + 60:
                        screen.blit(cloud_spr, (cx2, cy2))

            if ground_y < size[1] + 600:
                # parallax ridge silhouettes behind the pad horizon
                for ridge_spr, rfac in ridge_layers(live.body_id, size[0]):
                    rxo = -int((downrange * px_per_m * rfac) % RIDGE_PAD)
                    screen.blit(ridge_spr,
                                (rxo, ground_y - ridge_spr.get_height()))
                pygame.draw.rect(screen, ground_palette(live.body_id).dark,
                                 (0, min(ground_y, size[1]), size[0],
                                  max(0, size[1] - ground_y) + 4))
                if ground_y < size[1] + 8:
                    tex = ground_strip(live.body_id, size[0])
                    tex_x = int(-downrange * px_per_m) % size[0]
                    screen.blit(tex, (tex_x - size[0], ground_y))
                    screen.blit(tex, (tex_x, ground_y))
                if rho0 > 0.0 and sky_a > 8 and ground_y < size[1] + 70:
                    haze.set_alpha(int(140 * sky_a / 255))
                    screen.blit(haze, (0, ground_y - 70))
                if ascent_av is None and -300 < pad_x < size[0] + 300:
                    screen.blit(pad_complex(),
                                (pad_x - PAD_W // 2,
                                 ground_y - PAD_GROUND_Y - 12))
            if not (live.outcome == "lost" and ascent_boomed):
                screen.blit(rspr, (rx, ry))
            if live.throttle_eff > 0.0 and live.outcome is None:
                ang = math.radians(live.gamma_deg)
                ex = -math.cos(ang)
                ey = math.sin(ang)              # exhaust dir, screen y-down
                ccx = size[0] // 2 + sox
                ccy = ry + rspr.get_height() // 2
                hh = rspr.get_height() / 2.0 - 4.0
                n_fl = int(2 + 10 * live.throttle_eff)
                particles.emit_burn(ccx + ex * hh, ccy + ey * hh, ex, ey,
                                    n=n_fl)
                if live.h < 6_000.0 and frame_count % 3 == 0:
                    particles.emit_burn(ccx + ex * hh, ccy + ey * hh,
                                        ex, ey, n=1, color=(126, 126, 132),
                                        smoke=True, speed=(60.0, 130.0),
                                        life=(0.7, 1.4))
            if live.outcome == "lost" and not ascent_boomed:
                ascent_boomed = True
                particles.explosion(size[0] // 2,
                                    ry + rspr.get_height() // 2, 1.3)
            elif live.outcome is None:
                ascent_boomed = False
            if len(live.events) > ascent_event_count:
                for ev_line in live.events[ascent_event_count:]:
                    if "STAGE" in ev_line:       # separation debris puff
                        particles.emit_burn(size[0] // 2,
                                            ry + rspr.get_height(),
                                            0.0, 1.0, n=22,
                                            color=(220, 224, 232))
                        shake = max(shake, 0.6)
                        audio.play("stage")
                    elif "MECO" in ev_line or "CIRC" in ev_line:
                        audio.play("soi")
                ascent_event_count = len(live.events)
            particles.update_draw(
                screen, real_dt,
                floor_y=ground_y if live.h < 2_000.0 else None)
            bloom.apply(screen)        # bloom the world, not the HUD glass

            # ---- HUD ----
            screen.blit(theme.panel(258, 308, "ASCENT"), (16, 16))
            hx, hy = 32, 52
            q_col = (theme.COLORS["danger"] if live.q > live.params.q_limit
                     else theme.COLORS["text"])
            rows = [
                (f"ALT   {live.h/1e3:10,.2f} km", theme.COLORS["text"]),
                (f"VEL   {live.v_air:10,.0f} m/s", theme.COLORS["text"]),
                (f"APO   {live.apo_km:10,.0f} km", theme.COLORS["accent"]),
                (f"PERI  {live.peri_km:10,.0f} km", theme.COLORS["accent"]),
                (f"Q     {live.q/1e3:10,.1f} kPa", q_col),
                (f"TWR   {live.twr:10,.2f}", theme.COLORS["text"]),
                (f"STAGE {max(len(live.vessel.stage_plan), 0):>6d} left",
                 theme.COLORS["text"]),
                (f"dv    {live.dv_remaining:10,.0f} m/s",
                 theme.COLORS["good"]),
                (f"MODE  {'PROG' if live.prog else 'MANUAL':>10s}",
                 theme.COLORS["gold"] if live.prog
                 else theme.COLORS["warn"]),
                (f"WARP  {ascent_warp:8.0f}x", theme.COLORS["text_dim"]),
            ]
            for txt, col in rows:
                theme.draw_text(screen, hx, hy, txt, color=col, font="small")
                hy += 21
            theme.draw_text(screen, hx, hy + 2, "THROTTLE",
                            color=theme.COLORS["text_dim"], font="small")
            screen.blit(theme.bar(150, 10, live.throttle_cmd,
                                  theme.COLORS["warn"]), (hx + 78, hy + 4))

            for i, ev_txt in enumerate(live.events[-3:]):
                theme.draw_text(screen, 16, size[1] - 96 + i * 20, ev_txt,
                                color=theme.COLORS["accent"], font="small")
            if not live.ignited:
                msg = font_med.render("SPACE — IGNITION", True,
                                      theme.COLORS["gold"])
                screen.blit(msg, (size[0] // 2 - msg.get_width() // 2, 140))
            if live.outcome is not None:
                good = live.outcome == "orbit"
                ttl = font_big.render(
                    "ORBIT ACHIEVED" if good else "LOSS OF VEHICLE", True,
                    theme.COLORS["good"] if good else theme.COLORS["danger"])
                screen.blit(ttl, (size[0] // 2 - ttl.get_width() // 2, 200))
                rep = (f"spent {live.dv_int:,.0f} m/s — gravity "
                       f"{live.dv_grav:,.0f}, drag {live.dv_drag:,.0f}, "
                       f"steering {live.dv_steer:,.0f}")
                theme.draw_text(screen, size[0] // 2 - 230, 260, rep,
                                color=theme.COLORS["text"])
                theme.draw_text(screen, size[0] // 2 - 110, 286,
                                "ENTER to continue",
                                color=theme.COLORS["gold"])
            screen.blit(theme.footer(
                size[0],
                "SPACE ignite/stage   SHIFT/CTRL throttle   X/Z max/cut   "
                "arrows pitch (manual)   P autopilot   C circularize   "
                "./, warp   ESC revert (T+20s)"),
                (0, size[1] - theme.FOOTER_H))
            screen.blit(vig, (0, 0))
            apply_flash()
            present_frame()
            frame_count += 1
            if args.frames and frame_count >= args.frames:
                running = False
            continue

        if scene == "descent" and descent is not None:
            keys = pygame.key.get_pressed()
            if keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]:
                descent.throttle_cmd = min(1.0, descent.throttle_cmd
                                           + 0.9 * real_dt)
                descent.auto = False
            if keys[pygame.K_LCTRL] or keys[pygame.K_RCTRL]:
                descent.throttle_cmd = max(0.0, descent.throttle_cmd
                                           - 0.9 * real_dt)
                descent.auto = False
            if descent.outcome is None:
                descent_acc += real_dt * descent_warp
                n_steps = min(int(descent_acc / 0.02), 4000)
                descent_acc -= n_steps * 0.02
                for _ in range(n_steps):
                    descent.step(0.02)
                    if descent.outcome is not None:
                        if descent.outcome == "landed":
                            shake = max(shake, 0.7)
                            audio.play("thud")
                        else:
                            shake, flash = 1.5, 1.0
                            audio.play("boom")
                        break
            audio.set_engine(descent.throttle_eff
                             if descent.outcome is None else 0.0)

            # ---- draw: this body's sky, seeded terrain, the lander ----
            screen.fill((6, 8, 14))
            nebula.draw(screen, None)
            site_d = SITES[descent.site_id]
            rho0 = atmo_density(site_d["body"], 0.0)
            a_sky = 0
            if rho0 > 0.0:
                a_sky = int(190.0 * min(
                    1.0, atmo_density(site_d["body"],
                                      max(descent.h, 0.0)) / rho0) ** 0.4)
                dsky = sky_surface(size, site_d["body"])
                dsky.set_alpha(a_sky)
                screen.blit(dsky, (0, 0))
            else:
                starfield.draw(screen, cam)

            sox = int(7.0 * shake * math.sin(ui_t * 67.0))
            soy = int(6.0 * shake * math.sin(ui_t * 53.0 + 1.7))
            shake *= math.exp(-2.6 * real_dt)

            ppm_d = max(0.004, 0.30 * 900.0 / (900.0 + descent.h))
            dstack = [[descent.vessel.rows[i].part_id for i in st]
                      for st in descent.vessel.stage_plan]
            dspr0 = vessel_sprite(db, dstack)
            # lander stays readable through the whole burn (floor 55%),
            # growing back to full size on final approach
            ds = max(0.55, 1600.0 / (1600.0 + 0.8 * descent.h))
            dkey = (len(descent.vessel.stage_plan), round(ds, 2))
            if dkey not in rot_cache:
                if len(rot_cache) > 160:
                    rot_cache.clear()
                rot_cache[dkey] = pygame.transform.rotozoom(dspr0, 0.0, ds)
            dspr = rot_cache[dkey]
            drx = size[0] // 2 - dspr.get_width() // 2 + sox
            dry = int(size[1] * 0.40) - dspr.get_height() // 2 + soy
            ground_y = (dry + dspr.get_height()
                        + int(max(descent.h, 0.0) * ppm_d))
            if ground_y < size[1] + 800:
                off = int(descent.downrange * ppm_d)
                # parallax ridge silhouettes on the horizon
                for ridge_spr, rfac in ridge_layers(site_d["body"], size[0]):
                    rxo = -int((descent.downrange * ppm_d * rfac) % RIDGE_PAD)
                    screen.blit(ridge_spr,
                                (rxo, ground_y - ridge_spr.get_height()))
                pygame.draw.rect(screen, ground_palette(site_d["body"]).dark,
                                 (0, min(ground_y, size[1]), size[0],
                                  max(0, size[1] - ground_y) + 4))
                if ground_y < size[1] + 8:
                    tex = ground_strip(site_d["body"], size[0])
                    tex_x = (-off) % size[0]
                    screen.blit(tex, (tex_x - size[0], ground_y))
                    screen.blit(tex, (tex_x, ground_y))
                if rho0 > 0.0 and a_sky > 8 and ground_y < size[1] + 70:
                    haze.set_alpha(int(110 * a_sky / 190))
                    screen.blit(haze, (0, ground_y - 70))
                # LZ beacon where the descent began (downrange zero)
                lz_x = size[0] // 2 - off
                if -200 < lz_x < size[0] + 200 and ground_y < size[1] + 30:
                    pygame.draw.line(screen, theme.COLORS["gold"],
                                     (lz_x, ground_y - 22),
                                     (lz_x, ground_y - 2), 2)
                    pygame.draw.circle(screen, (255, 230, 160),
                                       (lz_x, ground_y - 24), 3)
            if not (descent.outcome == "crash" and ascent_boomed):
                screen.blit(dspr, (drx, dry))
            if descent.throttle_eff > 0.0 and descent.outcome is None:
                particles.emit_burn(size[0] // 2 + sox,
                                    dry + dspr.get_height() - 2,
                                    0.0, 1.0,
                                    n=int(2 + 8 * descent.throttle_eff))
            if descent.outcome == "crash" and not ascent_boomed:
                ascent_boomed = True
                particles.explosion(size[0] // 2,
                                    dry + dspr.get_height() // 2, 1.4)
            elif descent.outcome is None:
                ascent_boomed = False
            particles.update_draw(
                screen, real_dt,
                floor_y=ground_y if descent.h < 2_000.0 else None)
            bloom.apply(screen)

            # ---- HUD ----
            screen.blit(theme.panel(258, 296, "DESCENT"), (16, 16))
            hx, hy = 32, 52
            v_h_d = math.sqrt(max(descent.v ** 2 - descent.v_up ** 2, 0.0))
            ratio = descent.burn_ratio
            r_col = (theme.COLORS["danger"] if ratio >= 1.0
                     else theme.COLORS["warn"] if ratio > 0.8
                     else theme.COLORS["text"])
            for txt, col in (
                    (f"ALT   {descent.h:10,.0f} m", theme.COLORS["text"]),
                    (f"VSPD  {descent.v_up:10,.1f} m/s",
                     theme.COLORS["danger"] if descent.v_up < -60.0
                     else theme.COLORS["text"]),
                    (f"HSPD  {v_h_d:10,.1f} m/s", theme.COLORS["text"]),
                    (f"TWR   {descent.twr:10,.2f}",
                     theme.COLORS["danger"] if descent.twr < 1.0
                     else theme.COLORS["text"]),
                    (f"STOP  {descent.stop_dist:10,.0f} m", r_col),
                    (f"PROP  {descent.vessel.active_propellant_kg():10,.0f} kg",
                     theme.COLORS["good"]),
                    (f"MODE  {'AUTO' if descent.auto else 'MANUAL':>10s}",
                     theme.COLORS["gold"] if descent.auto
                     else theme.COLORS["warn"]),
                    (f"WARP  {descent_warp:8.0f}x",
                     theme.COLORS["text_dim"])):
                theme.draw_text(screen, hx, hy, txt, color=col, font="small")
                hy += 21
            theme.draw_text(screen, hx, hy + 2, "THROTTLE",
                            color=theme.COLORS["text_dim"], font="small")
            screen.blit(theme.bar(150, 10, descent.throttle_cmd,
                                  theme.COLORS["warn"]), (hx + 78, hy + 4))
            theme.draw_text(screen, hx, hy + 22, "BURN LADDER",
                            color=theme.COLORS["text_dim"], font="small")
            screen.blit(theme.bar(150, 10, min(1.0, ratio), r_col),
                        (hx + 96, hy + 24))
            if 0.85 <= ratio and descent.outcome is None:
                burn_now = font_med.render("BURN NOW", True,
                                           theme.COLORS["danger"])
                if int(ui_t * 4) % 2 == 0:
                    screen.blit(burn_now,
                                (size[0] // 2 - burn_now.get_width() // 2,
                                 150))
            for i, ev_txt in enumerate(descent.events[-3:]):
                theme.draw_text(screen, 16, size[1] - 96 + i * 20, ev_txt,
                                color=theme.COLORS["accent"], font="small")
            if descent.outcome is not None:
                good_d = descent.outcome == "landed"
                ttl = font_big.render(
                    "THE EAGLE HAS LANDED" if good_d else "LOSS OF VEHICLE",
                    True, theme.COLORS["good"] if good_d
                    else theme.COLORS["danger"])
                screen.blit(ttl, (size[0] // 2 - ttl.get_width() // 2, 200))
                theme.draw_text(screen, size[0] // 2 - 110, 260,
                                "ENTER to continue",
                                color=theme.COLORS["gold"])
            screen.blit(theme.footer(
                size[0],
                "SHIFT/CTRL throttle   X/Z max/cut   A autoland (pilot)   "
                "SPACE stage   ./, warp   ⚠ keep contact under 3 m/s"),
                (0, size[1] - theme.FOOTER_H))
            screen.blit(vig, (0, 0))
            apply_flash()
            present_frame()
            frame_count += 1
            if args.frames and frame_count >= args.frames:
                running = False
            continue

        if scene == "proxops" and prox is not None:
            was_open = prox.outcome
            if prox.outcome is None:
                for _ in range(4):
                    prox.step(real_dt / 4.0)
                prox_trail.append((prox.x, prox.y))
                if len(prox_trail) > 240:
                    prox_trail.pop(0)
                if prox.outcome == "captured" and was_open is None:
                    audio.play("soi")

            # ---- draw: LVLH radar — target centered, you fly the dot ----
            screen.fill((4, 6, 12))
            nebula.draw(screen, None)
            starfield.draw(screen, cam)
            cx0, cy0 = size[0] // 2, size[1] // 2 + 20
            sc = 230.0 / max(prox.range_m, 90.0)
            for ring_m, lbl in ((50.0, "50 m"), (100.0, ""),
                                (200.0, "200 m"), (400.0, "")):
                rp = int(ring_m * sc)
                if 8 < rp < 520:
                    pygame.draw.circle(screen, (40, 52, 74), (cx0, cy0), rp, 1)
                    if lbl:
                        theme.draw_text(screen, cx0 + rp + 4, cy0 - 8, lbl,
                                        color=theme.COLORS["text_dim"],
                                        font="small")
            cap_ok = prox.speed_ms <= (
                prox.capture_limit_ms
                if prox.range_m < CAPTURE_RANGE_M else CAPTURE_SPEED_MS)
            cap_px = max(8, int(CAPTURE_RANGE_M * sc))
            pygame.draw.circle(screen,
                               theme.COLORS["good"] if cap_ok
                               else theme.COLORS["danger"],
                               (cx0, cy0), cap_px, 2)
            # the adapter itself: contact at 4 m runs the capture ladder
            con_px = max(5, int(CONTACT_RANGE_M * sc))
            pygame.draw.circle(screen,
                               theme.COLORS["gold"] if cap_ok
                               else theme.COLORS["danger"],
                               (cx0, cy0), con_px, 1)
            tspr = craft_icon(math.pi / 2.0, 16)
            screen.blit(tspr, (cx0 - tspr.get_width() // 2,
                               cy0 - tspr.get_height() // 2))
            if len(prox_trail) > 2:
                tpts = [(cx0 + int(py * sc), cy0 - int(px * sc))
                        for px, py in prox_trail]
                pygame.draw.lines(screen, (60, 80, 110), False, tpts, 1)
            chx = cx0 + int(prox.y * sc)
            chy = cy0 - int(prox.x * sc)
            cspr2 = craft_icon(math.atan2(-(prox.vx), prox.vy), 14,
                               burning=False)
            screen.blit(cspr2, (chx - cspr2.get_width() // 2,
                                chy - cspr2.get_height() // 2))
            pygame.draw.line(screen, theme.COLORS["accent"], (chx, chy),
                             (chx + int(prox.vy * sc * 18),
                              chy - int(prox.vx * sc * 18)), 1)
            particles.update_draw(screen, real_dt)
            bloom.apply(screen)

            # ---- HUD ----
            screen.blit(theme.panel(258, 236, "PROX-OPS"), (16, 16))
            hx, hy = 32, 52
            cl = prox.closing_ms
            for txt, col in (
                    (f"RANGE  {prox.range_m:9,.0f} m", theme.COLORS["text"]),
                    (f"SPEED  {prox.speed_ms:9,.2f} m/s",
                     theme.COLORS["good"] if cap_ok
                     else theme.COLORS["danger"]),
                    (f"CLOSE  {cl:9,.2f} m/s",
                     theme.COLORS["good"] if cl > 0
                     else theme.COLORS["warn"]),
                    (f"TARGET {prox_target.name if prox_target else '?':>9s}",
                     theme.COLORS["accent"]),
                    (f"PORT   DK-{prox.port_size}"
                     + ("·ARM" if prox.magnetic else "")
                     + f"  ≤{prox.capture_limit_ms:.2f}",
                     theme.COLORS["text"]),
                    (f"BOUNCE {prox.bounces:9d}",
                     theme.COLORS["warn"] if prox.bounces
                     else theme.COLORS["text_dim"]),
                    (f"MODE   {'AUTO' if prox.auto else 'MANUAL':>9s}",
                     theme.COLORS["gold"] if prox.auto
                     else theme.COLORS["warn"])):
                theme.draw_text(screen, hx, hy, txt, color=col, font="small")
                hy += 21
            theme.draw_text(screen, hx, hy + 2, "RCS",
                            color=theme.COLORS["text_dim"], font="small")
            screen.blit(theme.bar(170, 10,
                                  prox.dv_left / max(prox.budget_dv, 0.1),
                                  theme.COLORS["accent"]), (hx + 36, hy + 4))
            theme.draw_text(screen, hx, hy + 22,
                            f"{prox.dv_left:,.1f} / {prox.budget_dv:,.1f} m/s",
                            color=theme.COLORS["text_dim"], font="small")
            for i, ev_txt in enumerate(prox.events[-3:]):
                theme.draw_text(screen, 16, size[1] - 96 + i * 20, ev_txt,
                                color=theme.COLORS["accent"], font="small")
            if prox.outcome == "captured":
                ttl = font_big.render("SOFT CAPTURE", True,
                                      theme.COLORS["good"])
                screen.blit(ttl, (size[0] // 2 - ttl.get_width() // 2, 150))
                theme.draw_text(screen, size[0] // 2 - 110, 210,
                                "ENTER — hard dock",
                                color=theme.COLORS["gold"])
            screen.blit(theme.footer(
                size[0],
                "arrows RCS (verniers inside 60 m; SHIFT coarse)   "
                "A autopilot (pilot)   ◎ contact at 4 m under the port "
                "limit — over 0.5 m/s bends the ring   ESC abort"),
                (0, size[1] - theme.FOOTER_H))
            screen.blit(vig, (0, 0))
            present_frame()
            frame_count += 1
            if args.frames and frame_count >= args.frames:
                running = False
            continue

        if scene == "victory":
            screen.fill((6, 8, 14))
            nebula.draw(screen, None)
            starfield.draw(screen, cam)
            ttl = font_big.render("THE PRECURSOR FLIES", True,
                                  (255, 215, 130))
            screen.blit(ttl, (size[0] // 2 - ttl.get_width() // 2, 130))
            days = t / SECONDS_PER_DAY
            done = sum(1 for c in program.contracts
                       if c.completed_t is not None)
            lines = [
                "Humanity's first starship is on a hyperbolic solar orbit.",
                "",
                f"campaign time      {days:,.0f} days "
                f"({2049 + days / 365.25:.1f} CE)",
                f"program funds      ${program.funds / 1e6:,.0f}M",
                f"contracts honored  {done}",
                f"fleet              {len(vessels)} vessels, "
                f"{len(bases)} surface bases",
                f"science banked     {research.science:,.0f}",
                f"crew on the books  {len(crew)}",
                "",
                "ENTER — keep flying the program (sandbox continues)",
            ]
            for i, line in enumerate(lines):
                txt = font_med.render(line, True, (200, 210, 224))
                screen.blit(txt, (size[0] // 2 - 290, 220 + i * 30))
            bloom.apply(screen)
            screen.blit(vig, (0, 0))
            present_frame()
            frame_count += 1
            if args.frames and frame_count >= args.frames:
                running = False
            continue

        if scene == "menu":
            screen.fill((6, 8, 14))
            nebula.draw(screen, cam)
            starfield.draw(screen, cam)
            # hero: a lit Earth limb breathing at the bottom of the frame
            if menu_limb is None:
                menu_limb = pygame.transform.smoothscale(
                    body_sprite("core:earth", 360, -math.pi / 2),
                    (1240, 1240))
            screen.blit(menu_limb,
                        (size[0] // 2 - 620,
                         size[1] - 296 + int(5 * math.sin(ui_t * 0.23))))
            title = theme.tracked("APHELION", "ui_huge",
                                  theme.COLORS["accent"], 20)
            tx0 = size[0] // 2 - title.get_width() // 2
            screen.blit(title, (tx0, 128))
            for rx0, rx1 in ((tx0 - 150, tx0 - 28),
                             (tx0 + title.get_width() + 28,
                              tx0 + title.get_width() + 150)):
                pygame.draw.line(screen, (90, 150, 175), (rx0, 156),
                                 (rx1, 156), 1)
            sub = theme.tracked("A HARD-REALISM SOLAR-SYSTEM PROGRAM · 2049",
                                "ui_small", (132, 146, 166), 3)
            screen.blit(sub, (size[0] // 2 - sub.get_width() // 2, 196))
            items = (list(_DIFFICULTIES) if menu_mode == "difficulty"
                     else ["NEW CAMPAIGN"]
                     + (["CONTINUE"] if latest_save() else [])
                     + ["QUIT"])
            if menu_mode == "difficulty":
                head = theme.tracked("SELECT PROGRAM DIFFICULTY", "ui_title",
                                     theme.COLORS["accent"], 4)
                screen.blit(head, (size[0] // 2 - head.get_width() // 2, 252))
            menu_rects = []
            card_w = 700 if menu_mode == "difficulty" else 300
            for i, label in enumerate(items):
                sel = i == menu_cursor % len(items)
                card = pygame.Rect(size[0] // 2 - card_w // 2,
                                   298 + i * 46, card_w, 38)
                fill = (24, 36, 58) if sel else (12, 18, 30)
                pygame.draw.rect(screen, fill, card, border_radius=8)
                pygame.draw.rect(
                    screen,
                    theme.COLORS["gold"] if sel
                    else theme.COLORS["panel_edge"],
                    card, width=1, border_radius=8)
                tcol = (theme.COLORS["gold"] if sel
                        else theme.COLORS["text"])
                if menu_mode == "difficulty":
                    d = _DIFFICULTIES[label]
                    theme.draw_text(screen, card.x + 24, card.y + 9, label,
                                    color=tcol, font="ui")
                    theme.draw_text(screen, card.x + 170, card.y + 9,
                                    f"${d['funds'] / 1e6:,.0f}M",
                                    color=theme.COLORS["gold"], font="ui")
                    theme.draw_text(screen, card.x + 268, card.y + 10,
                                    d["blurb"],
                                    color=theme.COLORS["text_dim"],
                                    font="ui_small")
                else:
                    img = theme.init_fonts()["ui"].render(label, True, tcol)
                    screen.blit(img, (card.centerx - img.get_width() // 2,
                                      card.y + 9))
                menu_rects.append(card)
            foot = theme.tracked(
                "ARROWS + ENTER OR CLICK  ·  F11 FULLSCREEN  ·  M MUTE  ·  "
                "ESC QUIT", "ui_small", (148, 160, 180), 2)
            fx0 = size[0] // 2 - foot.get_width() // 2
            fpill = pygame.Surface((foot.get_width() + 36, 28),
                                   pygame.SRCALPHA)
            pygame.draw.rect(fpill, (6, 10, 18, 175), fpill.get_rect(),
                             border_radius=14)
            screen.blit(fpill, (fx0 - 18, size[1] - 59))
            screen.blit(foot, (fx0, size[1] - 53))
            bloom.apply(screen)
            screen.blit(vig, (0, 0))
            present_frame()
            frame_count += 1
            if args.frames and frame_count >= args.frames:
                running = False
            continue

        if scene == "drydock":
            # ---- DRYDOCK 2.0: the grid design room (06 §2.13) ----
            keys = pygame.key.get_pressed()
            dd_move_cd = max(0.0, dd_move_cd - real_dt)
            if dd_move_cd <= 0.0:
                dxc = ((1 if keys[pygame.K_RIGHT] else 0)
                       - (1 if keys[pygame.K_LEFT] else 0))
                dyc = ((1 if keys[pygame.K_UP] else 0)
                       - (1 if keys[pygame.K_DOWN] else 0))
                if dxc or dyc:
                    dd_cursor[0] = max(0, min(69, dd_cursor[0] + dxc))
                    dd_cursor[1] = max(0, min(50, dd_cursor[1] + dyc))
                    dd_move_cd = 0.09

            screen.fill((6, 8, 14))
            cs = 11
            vx0, vy0 = 70, 636            # cell (0,0) bottom-left
            for gx in range(0, 64):       # the grid bed
                lx = vx0 + gx * cs
                pygame.draw.line(screen, (16, 20, 30) if gx % 5 else
                                 (24, 30, 44), (lx, vy0 - 52 * cs),
                                 (lx, vy0))
            for gy in range(0, 53):
                ly = vy0 - gy * cs
                pygame.draw.line(screen, (16, 20, 30) if gy % 5 else
                                 (24, 30, 44), (vx0, ly),
                                 (vx0 + 63 * cs, ly))
            cls_col = {"STRUCT": (120, 124, 134), "TANK": (96, 138, 178),
                       "ENGINE": (196, 122, 60), "HAB": (104, 164, 116),
                       "ELEC": (188, 172, 80), "MECH": (148, 110, 170),
                       "SHIELD": (84, 168, 178)}
            for p_dd in dd_v.parts:
                rx = vx0 + p_dd.x * cs
                ry = vy0 - (p_dd.y + p_dd.h) * cs
                col = cls_col.get(p_dd.spec.get("class", "STRUCT"),
                                  (120, 124, 134))
                pygame.draw.rect(screen, col,
                                 (rx + 1, ry + 1, p_dd.w * cs - 2,
                                  p_dd.h * cs - 2))
                pygame.draw.rect(screen, (10, 12, 18),
                                 (rx, ry, p_dd.w * cs, p_dd.h * cs), 1)
                if p_dd.w * cs >= 30 and p_dd.h * cs >= 12:
                    theme.draw_text(screen, rx + 2, ry + 1,
                                    p_dd.spec.get("catalog_id", "")[:7],
                                    color=(8, 10, 14), font="small")
            # the ghost of the selected catalog part rides the cursor
            rows_dd = dd_catalog()
            sel_dd = rows_dd[dd_cat_idx % len(rows_dd)] if rows_dd \
                else None
            if sel_dd:
                sw, sh = sel_dd[1].get("size", [1, 1])
                pygame.draw.rect(
                    screen, theme.COLORS["gold"],
                    (vx0 + dd_cursor[0] * cs,
                     vy0 - (dd_cursor[1] + int(sh)) * cs,
                     int(sw) * cs, int(sh) * cs), 2)
            # COM markers: wet gold dot, dry orange ring (06 §2.2)
            if dd_v.parts:
                wcx, wcy = dd_stage.wet_com(dd_v)
                dcx, dcy = dd_v.com()
                pygame.draw.circle(screen, theme.COLORS["gold"],
                                   (int(vx0 + wcx * cs),
                                    int(vy0 - wcy * cs)), 5)
                pygame.draw.circle(screen, (220, 140, 60),
                                   (int(vx0 + dcx * cs),
                                    int(vy0 - dcy * cs)), 7, 2)

            # ---- right panel: catalog + live readouts + validation ----
            px0 = 790
            screen.blit(theme.panel(470, 660, "DRYDOCK 2.0"), (px0, 10))
            yy = 52
            cls_dd = dd_cat_classes[dd_class_idx]
            theme.draw_text(screen, px0 + 16, yy,
                            f"CATALOG [{cls_dd}] — TAB class, ,/. part",
                            color=theme.COLORS["gold"], font="small")
            yy += 22
            if rows_dd:
                base_dd = dd_cat_idx % len(rows_dd)
                for k in range(-2, 4):
                    pid_k, p_k = rows_dd[(base_dd + k) % len(rows_dd)]
                    sel_k = k == 0
                    theme.draw_text(
                        screen, px0 + 16, yy,
                        f"{'>' if sel_k else ' '} "
                        f"{p_k.get('catalog_id', ''):10.10s} "
                        f"{p_k['name'][:24]:24.24s} {p_k['tier']}",
                        color=(theme.COLORS["gold"] if sel_k
                               else theme.COLORS["text_dim"]),
                        font="small")
                    yy += 18
            yy += 8
            defs_dd = dd_stage.to_stage_defs(dd_v)
            rep_dd = stage_report(defs_dd, mode=dd_mode) if defs_dd \
                else []
            badge_dd = dd_stage.torque_badge(dd_v)
            chips_dd = [
                (f"parts {len(dd_v.parts)}/600", theme.COLORS["text"]),
                (f"wet {sum(dd_stage.part_wet_t(p.spec) for p in dd_v.parts):,.1f} t",
                 theme.COLORS["text_dim"]),
                (f"${dd_stage.cost_musd(dd_v):,.0f}M",
                 theme.COLORS["text_dim"]),
                (badge_dd["badge"],
                 {"GREEN": theme.COLORS["accent"],
                  "YELLOW": theme.COLORS["warn"],
                  "RED": theme.COLORS["danger"]}[badge_dd["badge"]]),
            ]
            chx_dd = px0 + 16
            for ct, cc in chips_dd:
                cs_chip = theme.chip(ct, cc)
                screen.blit(cs_chip, (chx_dd, yy))
                chx_dd += cs_chip.get_width() + 6
            yy += 30
            theme.draw_text(screen, px0 + 16, yy,
                            f"STAGES ({dd_mode} Isp — M cycles)",
                            color=theme.COLORS["gold"], font="small")
            yy += 20
            for si, r_dd in enumerate(rep_dd):
                theme.draw_text(
                    screen, px0 + 16, yy,
                    f"S{si}  dv {r_dd['dv_ms']:6,.0f} m/s   "
                    f"TWR {r_dd['twr_ignition']:4.2f}   "
                    f"burn {r_dd['burn_s']:5,.0f} s",
                    color=theme.COLORS["text"], font="small")
                yy += 18
            yy += 8
            errs_dd = dd_v.validate()
            theme.draw_text(screen, px0 + 16, yy,
                            "VALIDATION — E jumps to the offender"
                            if errs_dd else "VALIDATION — CLEAN",
                            color=(theme.COLORS["danger"] if errs_dd
                                   else theme.COLORS["accent"]),
                            font="small")
            yy += 20
            for code_dd, off_dd in errs_dd[:6]:
                nm = (dd_v.parts[off_dd].spec["name"][:28]
                      if off_dd is not None else "whole vessel")
                theme.draw_text(screen, px0 + 16, yy,
                                f"{code_dd}  {nm}",
                                color=theme.COLORS["danger"],
                                font="small")
                yy += 17
            yy += 6
            if dd_sim is not None:
                # q / q·α traces with limit lines (06 §2.13)
                gw, gh = 430, 110
                gx0, gy0 = px0 + 20, yy
                pygame.draw.rect(screen, (14, 18, 28),
                                 (gx0, gy0, gw, gh))
                qmax_dd = max(40.0, dd_sim["peak_q_kpa"] * 1.15)
                trace_dd = dd_sim["trace"]
                tmax = max(1.0, trace_dd[-1][0])
                for series, colr in ((1, theme.COLORS["accent"]),
                                     (2, theme.COLORS["warn"])):
                    pts_dd = [(gx0 + tt / tmax * gw,
                               gy0 + gh - min(1.0, val / (
                                   qmax_dd if series == 1
                                   else qalpha_limit_kpadeg(dd_v)))
                               * gh)
                              for tt, *vals in [(p[0], p[1], p[2])
                                                for p in trace_dd[::4]]
                              for val in [vals[series - 1]]]
                    if len(pts_dd) > 1:
                        pygame.draw.lines(screen, colr, False,
                                          pts_dd, 1)
                bad_q = validate_e7(dd_v, dd_sim["peak_q_kpa"])
                theme.draw_text(
                    screen, gx0, gy0 + gh + 4,
                    f"peak q {dd_sim['peak_q_kpa']:.0f} kPa   "
                    f"q·α {dd_sim['peak_qalpha']:.0f}/"
                    f"{qalpha_limit_kpadeg(dd_v):.0f}   "
                    f"E7 {'FAIL ' + str(len(bad_q)) if bad_q else 'ok'}",
                    color=(theme.COLORS["danger"] if bad_q
                           else theme.COLORS["text_dim"]),
                    font="small")
            theme.draw_text(screen, 70, 24, dd_msg,
                            color=theme.COLORS["accent"], font="small")
            screen.blit(theme.footer(
                size[0],
                "ARROWS cursor   TAB class   ,/. part   ENTER place   "
                "X remove   E offender   S ascent sim   M isp   "
                "B send to pad   Y yard blueprint   ESC back"),
                (0, size[1] - theme.FOOTER_H))
            screen.blit(vig, (0, 0))
            present_frame()
            frame_count += 1
            if args.frames and frame_count >= args.frames:
                running = False
            continue

        if scene == "dive" and dive_gv is not None and dive_av is not None:
            # ---- THE DIVE (V5): a Titan sea by RTG light (10 §2.7) ----
            clock.advance_analytic(clock.t + EVA_TIME_FACTOR * real_dt)
            t = clock.t
            keys = pygame.key.get_pressed()
            mvx = ((keys[pygame.K_d] or keys[pygame.K_RIGHT])
                   - (keys[pygame.K_a] or keys[pygame.K_LEFT]))
            mvz = ((keys[pygame.K_s] or keys[pygame.K_DOWN])
                   - (keys[pygame.K_w] or keys[pygame.K_UP]))
            # SUB-T closes at ~1 m/s on 50 W prop; ballast pumps ±0.5 m/s
            dive_vx += max(-0.8 * real_dt, min(0.8 * real_dt,
                                               mvx * 1.0 - dive_vx))
            dive_vz += max(-0.6 * real_dt, min(0.6 * real_dt,
                                               mvz * 0.5 - dive_vz))
            if mvx:
                dive_face = mvx
            sid_v = f"{dive_av.landed_at}|sea"

            def _floor_m(wx: float) -> float:
                s1 = (zlib.crc32(sid_v.encode()) % 628) / 100.0
                return max(15.0, min(280.0,
                                     90.0 + 55.0 * math.sin(wx * 0.011 + s1)
                                     + 24.0 * math.sin(wx * 0.041 + 2 * s1)
                                     + 9.0 * math.sin(wx * 0.13 + 3 * s1)))

            dt_sim = real_dt * EVA_TIME_FACTOR
            dive_x += dive_vx * dt_sim
            floor_here = _floor_m(dive_x)
            dive_depth = max(0.0, min(floor_here - 2.5,
                                      dive_depth + dive_vz * dt_sim))
            # hull clock: pressure vs the H1 rating (V-21)
            p_now = marine.pressure_pa(dive_depth)
            p_rated = marine.pressure_pa(300.0)
            hull_frac = p_now / p_rated
            if hull_frac > 1.0:
                dive_gv.cond = max(0.0, dive_gv.cond
                                   - marine.OVERPRESSURE_LEAK_PER_MIN
                                   * ((hull_frac - 1.0) * 10.0)
                                   * (dt_sim / 60.0))
                if t - dive_warn_t > 4.0:
                    dive_warn_t = t
                    toast = (f"HULL OVER RATING ({dive_depth:,.0f} m) — "
                             f"leaking {100 * dive_gv.cond:.0f}%; CLIMB")
                    toast_until = t + 4
                    audio.play("alarm")
                if dive_gv.cond <= 0.0:
                    ground_vehicles.remove(dive_gv)
                    toast = (f"{dive_gv.name} CRUSHED at "
                             f"{dive_depth:,.0f} m — hull failure")
                    toast_until = t + 12
                    dive_gv, dive_av = None, None
                    scene = "flight"
                    audio.play("boom")
                    continue
            # hull wear ticks per dive-hour (V-24c)
            dive_gv.cond = max(0.0, dive_gv.cond
                               - vwear.dc_hull(dt_sim / 3600.0))

            # ---- THE LIVING SEA: deterministic ecology per 80 m cell ----
            from aphelion.game import sealife
            from aphelion.render import marine_art
            body_v = SITES[dive_av.landed_at]["body"]
            _cell_v = sealife.cell_of(dive_x)
            for _c in (_cell_v - 1, _cell_v, _cell_v + 1):
                if _c not in dive_sea_cells:
                    dive_sea_cells.add(_c)
                    _cx_m = (_c + 0.5) * sealife.CELL_W_M
                    dive_sea.extend(sealife.populate(
                        body_v, sid_v, _floor_m(_cx_m), _cx_m))
            if len(dive_sea_cells) > 7:     # cull far cells; they respawn
                _near_c = {c for c in dive_sea_cells
                           if abs(c - _cell_v) <= 2}
                dive_sea = [en for en in dive_sea
                            if sealife.cell_of(en.get("x", dive_x))
                            in _near_c]
                dive_sea_cells = _near_c
            # Tier 3: once per campaign, deep water only — THE CONTACT
            if ("sea_contact_seen" not in milestones
                    and dive_depth >= sealife.CONTACT_MIN_DEPTH_M):
                _ct = sealife.maybe_contact(
                    body_v, sid_v, dive_depth, dive_x, dive_face,
                    campaign_rng.campaign_seed, False)
                if _ct is not None:
                    dive_sea.append(_ct)
                    milestones.add("sea_contact_seen")
            for _ev_s in sealife.step(dive_sea, dt_sim, dive_x,
                                      dive_depth, True, dive_gv.rtg_we,
                                      uv_on=dive_uv):
                if _ev_s[0] == "sonar_contact":
                    if t - dive_warn_t > 3.0:
                        dive_warn_t = t
                        toast = f"SONAR: {str(_ev_s[1]).upper()} CONTACT"
                        toast_until = t + 5
                        audio.play("tick")
                elif _ev_s[0] == "discovery":
                    _, _tier_s, _sci_s, _dsc_s, _eid_s = _ev_s
                    _ikey = f"sea|{_eid_s}"
                    if _ikey not in explore["investigated"]:
                        explore["investigated"].add(_ikey)
                        research.earn_science(_sci_s)
                        _ent_s = next((en for en in dive_sea
                                       if en.get("id") == _eid_s), None)
                        if _ent_s is not None and sealife.is_first(_ent_s):
                            chron.add(t, "FIRST_CONTACT",
                                      sealife.chronicle_text(_ent_s),
                                      cls=2)
                            toast = ("CONTACT. Something large is pacing "
                                     "the boat — it will not close. "
                                     f"+{_sci_s:,.0f} sci")
                            toast_until = t + 16
                            audio.play("alarm")
                        else:
                            _lbl_s = (sealife.label(_ent_s)
                                      if _ent_s else "phenomenon")
                            toast = (f"DISCOVERY: {_lbl_s}  "
                                     f"+{_sci_s:,.0f} sci")
                            toast_until = t + 10
                            audio.play("paid")

            # ---- draw: methane gloom by depth ----
            bkt = int(dive_depth // 8)
            bgd = dive_bg_cache.get(bkt)
            if bgd is None:
                bgd = pygame.Surface(size)
                f0 = max(0.0, 1.0 - bkt * 8.0 / 240.0)
                top = (int(8 + 40 * f0), int(22 + 52 * f0),
                       int(26 + 44 * f0))
                bot = (max(2, top[0] - 14), max(4, top[1] - 22),
                       max(6, top[2] - 18))
                for yy in range(0, size[1], 4):
                    fy2 = yy / size[1]
                    cc = tuple(int(top[c] + (bot[c] - top[c]) * fy2)
                               for c in range(3))
                    pygame.draw.rect(bgd, cc, (0, yy, size[0], 4))
                dive_bg_cache[bkt] = bgd
            screen.blit(bgd, (0, 0))
            ppm_v = 6.0
            cy_px = size[1] * 0.42

            def _sxv(wx: float) -> float:
                return size[0] / 2.0 + (wx - dive_x) * ppm_v

            def _syv2(d_m: float) -> float:
                return cy_px + (d_m - dive_depth) * ppm_v

            # surface shimmer when shallow
            if dive_depth < 35.0:
                sy0 = _syv2(0.0)
                for k in range(4):
                    a_s = max(0, 70 - k * 18 - int(dive_depth))
                    if a_s > 0 and -40 < sy0 + k * 3 < size[1]:
                        srf = pygame.Surface((size[0], 2), pygame.SRCALPHA)
                        srf.fill((150, 190, 200, a_s))
                        screen.blit(srf, (0, sy0 + k * 3))
            # marine snow (deterministic drift)
            for i in range(46):
                px_s = (i * 173.31 + t * (2.0 + i % 5)) % (size[0] + 40) - 20
                py_s = (i * 97.7 + t * (5.0 + i % 7)) % (size[1] + 30) - 15
                b_s = 60 + (i * 37) % 70
                screen.fill((b_s, b_s + 8, b_s + 6),
                            (int(px_s), int(py_s), 2, 2),
                            special_flags=pygame.BLEND_ADD)
            # the sea floor: silhouette polygon + sonar-lit crest
            pts_f = [(x_px, _syv2(_floor_m(dive_x
                                           + (x_px - size[0] / 2) / ppm_v)))
                     for x_px in range(-8, size[0] + 9, 16)]
            poly_f = pts_f + [(size[0] + 8, size[1] + 8), (-8, size[1] + 8)]
            pygame.draw.polygon(screen, (14, 18, 20), poly_f)
            ping_age = t - dive_ping_t
            crest_c = ((120, 220, 200) if ping_age < 5.0
                       else (40, 56, 56))
            pygame.draw.lines(screen, crest_c, False, pts_f,
                              2 if ping_age < 5.0 else 1)
            if ping_age < 2.2:                      # expanding ping ring
                pygame.draw.circle(
                    screen, (90, 200, 180),
                    (int(size[0] / 2), int(cy_px)),
                    int(30 + ping_age * 220), 2)
            # the living sea, lit only by what light there is
            beam = vehicle_art.headlight_beam(20.0, dive_face)
            _cam_m = {"x0": dive_x, "depth": dive_depth, "ppm": ppm_v,
                      "cx": size[0] / 2, "cy": cy_px}
            _beam_g = {"x": size[0] / 2, "y": cy_px, "dir": dive_face,
                       "reach": beam.get_width(),
                       "half": beam.get_height() / 2}
            marine_art.draw_backscatter(screen, _beam_g, t)
            marine_art.draw_entities(screen, dive_sea, _cam_m, _beam_g, t)
            # headlight + the boat
            bx_v = (size[0] / 2 if dive_face > 0
                    else size[0] / 2 - beam.get_width())
            screen.blit(beam, (bx_v, cy_px - beam.get_height() / 2),
                        special_flags=pygame.BLEND_ADD)
            sspr_v = vehicle_art.vehicle_sprite(dive_gv.catalog_id, 16.0,
                                                dive_face)
            rock_v = 2.5 * math.sin(t * 0.6)
            sspr_v = pygame.transform.rotozoom(sspr_v, rock_v, 1.0)
            screen.blit(sspr_v, (size[0] / 2 - sspr_v.get_width() / 2,
                                 cy_px - sspr_v.get_height() / 2))
            if abs(dive_vx) > 0.1 or abs(dive_vz) > 0.1:  # prop bubbles
                for k in range(5):
                    bx2 = (size[0] / 2 - dive_face
                           * (sspr_v.get_width() / 2 + 6 + k * 7
                              + (t * 40) % 7))
                    by2 = cy_px + 4 * math.sin(t * 7 + k * 1.7)
                    pygame.draw.circle(screen, (70, 110, 110),
                                       (int(bx2), int(by2)), 1 + k % 2)

            # depth tape (right edge) + hull bar
            tape_x = size[0] - 56
            pygame.draw.line(screen, (70, 90, 92), (tape_x, 40),
                             (tape_x, size[1] - 60), 1)
            for dm in range(0, 320, 20):
                ty = _syv2(float(dm))
                if 30 < ty < size[1] - 50:
                    pygame.draw.line(screen, (90, 116, 118),
                                     (tape_x - 6, ty), (tape_x, ty), 1)
                    theme.draw_text(screen, tape_x + 6, ty - 7, f"{dm}",
                                    color=theme.COLORS["text_dim"],
                                    font="small")
            ry = _syv2(300.0)
            if 30 < ry < size[1] - 50:
                pygame.draw.line(screen, theme.COLORS["danger"],
                                 (tape_x - 10, ry), (tape_x + 34, ry), 2)
            pygame.draw.polygon(screen, theme.COLORS["accent"],
                                ((tape_x - 14, cy_px), (tape_x - 6, cy_px - 5),
                                 (tape_x - 6, cy_px + 5)))
            chips_v = [
                (dive_gv.name, theme.COLORS["text"]),
                (f"depth {dive_depth:5.0f} m", theme.COLORS["accent"]),
                (f"hull {100.0 * min(hull_frac, 1.5):3.0f}% of rating",
                 theme.COLORS["danger"] if hull_frac > 1.0 else
                 theme.COLORS["warn"] if hull_frac > 0.85 else
                 theme.COLORS["text_dim"]),
                (f"{abs(dive_vx):3.1f} m/s", theme.COLORS["text_dim"]),
                (f"cond {100.0 * dive_gv.cond:3.0f}%",
                 theme.COLORS["warn"] if dive_gv.cond < 0.5
                 else theme.COLORS["text_dim"]),
                (f"mapped {len(dive_painted) * 50} m",
                 theme.COLORS["text_dim"]),
                ("RTG 330 We" if dive_gv.rtg_we > 0 else "BATTERY",
                 theme.COLORS["text_dim"]),
            ]
            chx_v = 10
            for chip_txt, chip_col in chips_v:
                cs = theme.chip(chip_txt, chip_col)
                screen.blit(cs, (chx_v, 8))
                chx_v += cs.get_width() + 8
            if dive_uv:
                cs = theme.chip("UV LAMP", theme.COLORS["accent"])
                screen.blit(cs, (chx_v, 8))
            screen.blit(theme.footer(
                size[0], "A/D thrust   W/S ballast   Q sonar ping   "
                         "U uv lamp   E surface & moor"),
                (0, size[1] - theme.FOOTER_H))
            screen.blit(vig, (0, 0))
            apply_flash()
            present_frame()
            frame_count += 1
            if args.frames and frame_count >= args.frames:
                running = False
            continue

        if scene == "drive" and drive_gv is not None and drive_av is not None:
            # ---- THE DRIVE (V5): the V-laws under your right foot ----
            clock.advance_analytic(clock.t + EVA_TIME_FACTOR * real_dt)
            t = clock.t
            site_d = SITES[drive_av.landed_at]
            body_d = site_d["body"]
            _bd = tree.body(body_d)
            g_d = _bd.mu / _bd.radius ** 2
            terr_key = _drive_terrain_key(site_d)
            terr_d = locomotion.TERRAIN.get(terr_key,
                                            locomotion.TERRAIN["regolith"])
            if drive_tiles is None:
                sec_d = site_d.get("sector_id", drive_av.landed_at)
                drive_tiles = tileworld.TileWorld(
                    sec_d, 4.0, site_d.get("kind", "regolith"),
                    dug=explore.setdefault("dug", {}).get(sec_d, []))
                drive_tr = TileRenderer(drive_tiles, ground_palette(body_d))
                drive_camy = drive_tiles.surface_y(drive_x)

            keys = pygame.key.get_pressed()
            mv = 0
            if keys[pygame.K_LEFT] or keys[pygame.K_a]:
                mv -= 1
            if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
                mv += 1
            if drive_stuck > 0.0:
                mv = 0
            v_lim = (locomotion.v_max_ms(g_d, "raw")
                     * getattr(terr_d, "speed_mult", 1.0)
                     * drive_eta)      # L-13: teleop crawls with light lag
            tgt_v = mv * v_lim
            step_a = 2.4 * real_dt
            drive_v += max(-step_a, min(step_a, tgt_v - drive_v))
            if mv == 0 and abs(drive_v) < 0.05:
                drive_v = 0.0
            if mv:
                drive_face = mv
            # V-6: the slope ahead refuses you past the traction limit
            rise_d = (drive_tiles.surface_y(drive_x + drive_face * 2.0)
                      - drive_tiles.surface_y(drive_x))
            slope_d = abs(math.degrees(math.atan2(rise_d, 2.0)))
            th_max = locomotion.theta_max_deg(terr_d.mu, terr_d.crr)
            if mv and rise_d > 0 and slope_d > th_max:
                drive_v = 0.0
                if t - drive_warn_t > 4.0:
                    drive_warn_t = t
                    toast = (f"SLOPE {slope_d:.0f}° > traction limit "
                             f"{th_max:.0f}° on {terr_key} — go around")
                    toast_until = t + 4
                    audio.play("warn")
            dx_d = drive_v * real_dt * EVA_TIME_FACTOR
            if abs(dx_d) > 1e-6:
                km_pre = drive_gv.odo_km
                ok_d = drive_gv.drive(
                    abs(dx_d) / 1000.0, g_d, terr_key,
                    v_kmh=max(abs(drive_v) * 3.6, 0.5),
                    hotel_kw=0.15 if drive_gv.crewed else 0.06,
                    dust_body=body_d.rsplit(":", 1)[-1])
                if not ok_d:
                    drive_v = 0.0
                    if t - drive_warn_t > 6.0:
                        drive_warn_t = t
                        toast = ("BATTERY FLAT — E dismounts; recharge "
                                 "comes from base stores")
                        toast_until = t + 8
                        audio.play("alarm")
                else:
                    drive_x = max(2.0,
                                  min(getattr(drive_tiles, "width_m",
                                              2000.0) - 2.0,
                                      drive_x + dx_d))
                    if int(drive_gv.odo_km) != int(km_pre):
                        import zlib as _z
                        p_g = locomotion.p_ground_pa(
                            drive_gv.mass_t * 1000.0, g_d, 4, 0.05)
                        if locomotion.embedding_risk(terr_key, p_g) and (
                                _z.crc32(
                                    f"{drive_gv.vid}|"
                                    f"{int(drive_gv.odo_km)}".encode())
                                % 100) < 5:
                            drive_stuck = 1.0
                            drive_attempts = 0
                            drive_v = 0.0
                            toast = ("EMBEDDED — wheels dug in (the "
                                     "Spirit special). X to rock free")
                            toast_until = t + 8
                            audio.play("thud")

            ppm = 16.0
            h_ground = 470
            camx_d = drive_x
            surf_d = drive_tiles.surface_y(drive_x)
            drive_camy += (surf_d - drive_camy) * min(1.0, 6.0 * real_dt)

            screen.fill((4, 6, 12))
            if site_d.get("aero") or body_d in _ATMO_BODIES:
                dsky = sky_surface(size, body_d)
                dsky.set_alpha(255)
                screen.blit(dsky, (0, 0))
            else:
                starfield.draw(screen, cam)
                dsky = sky_surface(size, body_d)
                dsky.set_alpha(70)
                screen.blit(dsky, (0, 0))
            for ridge_s, fac in ridge_layers(body_d, size[0]):
                rx = -((camx_d * ppm * fac * 0.25) % RIDGE_PAD)
                screen.blit(ridge_s,
                            (rx, h_ground + drive_camy * ppm
                             - ridge_s.get_height() - 36))

            def _syd(wy: float) -> float:
                return h_ground - (wy - drive_camy) * ppm

            def _sxd(wx: float) -> float:
                return size[0] / 2.0 + (wx - camx_d) * ppm

            drive_tr.draw(screen, camx_d, drive_camy, size, ppm, h_ground)
            # the lander + colony share the cross-section
            stack_d = [[drive_av.vessel.rows[i].part_id for i in st]
                       for st in drive_av.vessel.stage_plan]
            lspr_d = pygame.transform.rotozoom(vessel_sprite(db, stack_d),
                                               0.0, 0.6)
            screen.blit(lspr_d, (_sxd(0.0) - lspr_d.get_width() / 2,
                                 _syd(drive_tiles.surface_y(0.0))
                                 - lspr_d.get_height()))
            home_dv = next((b for b in bases
                            if b.site_id == drive_av.landed_at), None)
            if home_dv is not None:
                from aphelion.render.base_art import module_sprite
                for bi, bx in eva_sim.module_positions(
                        home_dv.built).items():
                    spr = module_sprite(home_dv.built[bi])
                    screen.blit(spr,
                                (_sxd(bx) - spr.get_width() / 2,
                                 _syd(drive_tiles.surface_y(bx))
                                 - spr.get_height()))

            # the vehicle: grounded by its contact shadow (rule zero)
            vppm = 22.0
            vspr = vehicle_art.vehicle_sprite(drive_gv.catalog_id, vppm,
                                              drive_face)
            v_top = _syd(surf_d) - vspr.get_height() + 6
            shw = int(vspr.get_width() * 0.92)
            shs = pygame.Surface((shw, 14), pygame.SRCALPHA)
            pygame.draw.ellipse(shs, (0, 0, 0, 84), (0, 0, shw, 14))
            screen.blit(shs, (size[0] / 2 - shw / 2,
                              v_top + vspr.get_height() - 10))
            if drive_stuck > 0.0:                   # nose-down when dug in
                vspr = pygame.transform.rotozoom(vspr, -6 * drive_face, 1.0)
            screen.blit(vspr, (size[0] / 2 - vspr.get_width() / 2, v_top))

            prompt_d = ("X — ROCK FREE" if drive_stuck > 0.0
                        else "E — PARK & DISMOUNT")
            theme.draw_text(screen, size[0] / 2 - 64, v_top - 22, prompt_d,
                            color=theme.COLORS["gold"], font="ui_small")

            chg = (100.0 * drive_gv.energy_kwh
                   / max(drive_gv.pack_kwh, 1e-9))
            e_now = drive_gv.e_km(g_d, terr_key,
                                  v_kmh=max(abs(drive_v) * 3.6, 5.0),
                                  hotel_kw=0.15 if drive_gv.crewed
                                  else 0.06)
            rng_km = (float("inf") if drive_gv.rtg_we > 0.0
                      else drive_gv.energy_kwh / max(e_now, 1e-9))
            chips_d = [
                (drive_gv.name, theme.COLORS["text"]),
                (f"{abs(drive_v) * 3.6:4.1f} km/h", theme.COLORS["accent"]),
                (f"chg {chg:3.0f}%",
                 theme.COLORS["danger"] if chg < 15 else
                 theme.COLORS["warn"] if chg < 35 else
                 theme.COLORS["text_dim"]),
                ("range ∞" if rng_km == float("inf")
                 else f"range {rng_km:,.0f} km", theme.COLORS["text_dim"]),
                (f"cond {100.0 * drive_gv.cond:3.0f}%",
                 theme.COLORS["warn"] if drive_gv.cond < 0.5
                 else theme.COLORS["text_dim"]),
                (f"odo {drive_gv.odo_km:,.1f} km", theme.COLORS["text_dim"]),
                (f"{terr_key} · slope {slope_d:.0f}°",
                 theme.COLORS["text_dim"]),
            ]
            chx_d = 10
            for chip_txt, chip_col in chips_d:
                cs = theme.chip(chip_txt, chip_col)
                screen.blit(cs, (chx_d, 8))
                chx_d += cs.get_width() + 8
            screen.blit(theme.footer(
                size[0], "A/D drive   E park & dismount   X rock free"),
                (0, size[1] - theme.FOOTER_H))
            screen.blit(vig, (0, 0))
            apply_flash()
            present_frame()
            frame_count += 1
            if args.frames and frame_count >= args.frames:
                running = False
            continue

        if scene == "eva" and eva_state is not None and eva_av is not None:
            # ---- THE WALK: side-view surface EVA at body-true gravity ----
            clock.advance_analytic(clock.t + EVA_TIME_FACTOR * real_dt)
            t = clock.t
            keys = pygame.key.get_pressed()
            move = 0
            if keys[pygame.K_LEFT] or keys[pygame.K_a]:
                move -= 1
            if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
                move += 1
            run = bool(keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT])
            eva_state.step(real_dt, move, run, False)
            # the suit clock runs at sim rate (step burned 1x already)
            eva_state.o2_s = max(0.0, eva_state.o2_s
                                 - (EVA_TIME_FACTOR - 1.0) * real_dt)
            if eva_state.o2_s <= 0.0:
                lost_w = eva_state.member
                crew.pop(lost_w, None)
                if lost_w in eva_av.crew:
                    eva_av.crew.remove(lost_w)
                toast = f"{lost_w} DIED ON EVA — suit oxygen exhausted"
                toast_until = t + 14
                audio.play("alarm")
                eva_state, eva_tiles, eva_tr, eva_dig = None, None, None, None
                scene = "flight"
                continue

            site_e = SITES[eva_av.landed_at]
            body_e = site_e["body"]
            if eva_tiles is None:       # safety: any path into the scene
                eva_tiles = tileworld.TileWorld(
                    eva_state.sector_id, 4.0,
                    site_e.get("kind", "regolith"),
                    dug=explore.setdefault("dug", {}).get(
                        eva_state.sector_id, []))
                eva_state.tiles = eva_tiles
                eva_tr = TileRenderer(eva_tiles, ground_palette(body_e))

            # held-tool digging: X carves the wall ahead, C the floor below
            dig_down = bool(keys[pygame.K_c])
            tgt_d = (eva_state.dig_target(dig_down)
                     if (keys[pygame.K_x] or dig_down) else None)
            if tgt_d is not None and eva_tiles.tile_at(
                    *tgt_d) in tileworld.DIG_S:
                c_t, r_t = eva_tiles.col(tgt_d[0]), eva_tiles.row(tgt_d[1])
                tt_d = eva_tiles.tile_at(*tgt_d)
                if eva_dig is None or eva_dig["tile"] != (c_t, r_t):
                    eva_dig = {"tile": (c_t, r_t),
                               "left": tileworld.DIG_S[tt_d],
                               "total": tileworld.DIG_S[tt_d]}
                eva_dig["left"] -= real_dt
                if eva_dig["left"] <= 0.0:
                    got_t, _secs = eva_tiles.dig(*tgt_d)
                    eva_tr.invalidate(c_t, r_t)
                    explore.setdefault("dug", {})[
                        eva_state.sector_id] = eva_tiles.dug_list()
                    # first strike logs the deposit (the I-chunk extraction
                    # ladder feeds on these)
                    dep_d = explore.setdefault("deposits", {}).setdefault(
                        eva_state.sector_id, [])
                    if got_t == tileworld.ICE and "ice" not in dep_d:
                        dep_d.append("ice")
                        research.earn_science(15.0)
                        toast = ("ICE LENS CONFIRMED — deposit logged "
                                 "for extraction (+15 sci)")
                        toast_until = t + 10
                        audio.play("paid")
                    elif got_t == tileworld.ORE and "ore" not in dep_d:
                        dep_d.append("ore")
                        research.earn_science(15.0)
                        toast = ("METAL VEIN STRUCK — deposit logged "
                                 "for extraction (+15 sci)")
                        toast_until = t + 10
                        audio.play("paid")
                    # spoil goes to the colony stores if one is here
                    home_d = next((b for b in bases
                                   if b.site_id == eva_av.landed_at), None)
                    if home_d is not None:
                        res_d = ("Water" if got_t == tileworld.ICE
                                 else "Regolith")
                        buf_d = home_d.net.buffers.get(res_d)
                        if buf_d is not None:
                            kg_d = tileworld.TILE_KG[got_t] * (
                                0.9 if got_t == tileworld.ICE else 1.0)
                            buf_d.level = min(buf_d.capacity,
                                              buf_d.level + kg_d)
                    eva_dig = None
                    audio.play("tick")
            else:
                eva_dig = None

            ppm = 16.0
            h_ground = 470
            camx = eva_state.x
            eva_camy += (eva_state.y - eva_camy) * min(1.0, 6.0 * real_dt)
            camy = eva_camy

            screen.fill((4, 6, 12))
            if site_e.get("aero") or body_e in _ATMO_BODIES:
                esky = sky_surface(size, body_e)
                esky.set_alpha(255)
                screen.blit(esky, (0, 0))
            else:
                starfield.draw(screen, cam)
                esky = sky_surface(size, body_e)
                esky.set_alpha(70)
                screen.blit(esky, (0, 0))
            for ridge_s, fac in ridge_layers(body_e, size[0]):
                rx = -((camx * ppm * fac * 0.25) % RIDGE_PAD)
                screen.blit(ridge_s,
                            (rx, h_ground + camy * ppm
                             - ridge_s.get_height() - 36))

            gp = ground_palette(body_e)

            def _syv(wy: float) -> float:
                return h_ground - (wy - camy) * ppm

            def _sy(wx: float) -> float:
                return _syv(eva_tiles.surface_y(wx))

            def _sx(wx: float) -> float:
                return size[0] / 2.0 + (wx - camx) * ppm

            # the site cross-section: strata, lenses, veins, your tunnels
            eva_tr.draw(screen, camx, camy, size, ppm, h_ground)
            for rwx, rr in eva_state.rocks:
                rsx = _sx(rwx)
                if -20 < rsx < size[0] + 20:
                    pygame.draw.ellipse(
                        screen, gp.dark,
                        (rsx - rr * ppm / 2, _sy(rwx) - rr * ppm * 0.35,
                         rr * ppm, rr * ppm * 0.55))

            # the lander you walked out of (x = 0)
            stack_e = [[eva_av.vessel.rows[i].part_id for i in st]
                       for st in eva_av.vessel.stage_plan]
            lspr = pygame.transform.rotozoom(vessel_sprite(db, stack_e),
                                             0.0, 0.6)
            screen.blit(lspr, (_sx(0.0) - lspr.get_width() / 2,
                               _sy(0.0) - lspr.get_height()))
            # the colony, walkable end to end
            home_b = next((b for b in bases
                           if b.site_id == eva_av.landed_at), None)
            if home_b is not None:
                from aphelion.render.base_art import module_sprite
                for bi, bx in eva_sim.module_positions(home_b.built).items():
                    spr = module_sprite(home_b.built[bi])
                    screen.blit(spr, (_sx(bx) - spr.get_width() / 2,
                                      _sy(bx) - spr.get_height()))
            pend_e = [a for a in site_e.get("anomalies", [])
                      if a not in explore["investigated"]]
            if pend_e:
                mk = eva_art.anomaly_marker(ui_t)
                screen.blit(mk, (_sx(eva_sim.ANOMALY_X_M) - 13,
                                 _sy(eva_sim.ANOMALY_X_M) - 52))
                theme.draw_text(screen, _sx(eva_sim.ANOMALY_X_M) - 30,
                                _sy(eva_sim.ANOMALY_X_M) - 70, "ANOMALY",
                                color=theme.COLORS["gold"], font="small")
            if eva_av.landed_at in explore.get("flags", []):
                fspr = eva_art.flag()
                screen.blit(fspr, (_sx(14.0),
                                   _sy(14.0) - fspr.get_height()))

            aspr = eva_art.astronaut(int(eva_state.frame),
                                     eva_state.facing, eva_state.airborne)
            walker_top = _syv(eva_state.y) - aspr.get_height()
            screen.blit(aspr, (size[0] / 2 - aspr.get_width() / 2,
                               walker_top))

            # underground: the sky stops helping, the suit lamp takes over
            depth_e = eva_state.depth_m()
            eva_tr.darkness(screen,
                            (int(size[0] / 2),
                             int(walker_top + aspr.get_height() * 0.4)),
                            depth_e)
            if eva_dig is not None:     # the tool bites: progress bar
                frac_d = 1.0 - max(0.0, eva_dig["left"]) / eva_dig["total"]
                pygame.draw.rect(screen, (38, 40, 50),
                                 (size[0] / 2 - 24, walker_top - 12, 48, 6))
                pygame.draw.rect(screen, theme.COLORS["gold"],
                                 (size[0] / 2 - 24, walker_top - 12,
                                  int(48 * min(1.0, frac_d)), 6))

            # interaction prompt above the helmet
            prompt = ""
            if depth_e > 2.5:
                if eva_state.dig_target(False) is not None:
                    prompt = "X — DIG"
            elif eva_state.near(0.0):
                prompt = "E — BOARD THE LANDER"
            elif pend_e and eva_state.near(eva_sim.ANOMALY_X_M, 6.0):
                prompt = "E — INVESTIGATE"
            elif home_b is not None and any(
                    eva_state.near(bx) for bx in
                    eva_sim.module_positions(home_b.built).values()):
                prompt = "E — MODULE CONSOLE"
            elif eva_state.dig_target(False) is not None:
                prompt = "X — DIG"
            if prompt:
                theme.draw_text(screen, size[0] / 2 - 60,
                                walker_top - 24,
                                prompt, color=theme.COLORS["gold"],
                                font="ui_small")

            # HUD: who, where, the suit clock, what this gravity allows
            chx_e = 10
            o2c = (theme.COLORS["danger"] if eva_state.o2_frac < 0.25
                   else theme.COLORS["accent"])
            chips_e = [
                (f"EVA  {eva_state.member}", theme.COLORS["text"]),
                (site_e["name"], theme.COLORS["text_dim"]),
                (f"g {eva_state.g:.2f} m/s²", theme.COLORS["accent"]),
                (f"jump {eva_state.jump_apex_m():.1f} m",
                 theme.COLORS["text_dim"]),
                (f"bags {eva_state.scoops_left}",
                 theme.COLORS["text_dim"]),
                (f"walked {eva_state.dist_walked:,.0f} m",
                 theme.COLORS["text_dim"])]
            if depth_e > 1.0:
                chips_e.append((f"depth {depth_e:.1f} m",
                                theme.COLORS["gold"]))
            for chip_txt, chip_col in chips_e:
                cs = theme.chip(chip_txt, chip_col)
                screen.blit(cs, (chx_e, 8))
                chx_e += cs.get_width() + 8
            theme.draw_text(screen, 10, 40, "SUIT O2",
                            color=o2c, font="small")
            screen.blit(theme.bar(220, 12, eva_state.o2_frac, o2c),
                        (70, 39))
            if eva_state.o2_frac < 0.25:
                theme.draw_text(screen, 300, 39,
                                "RETURN TO THE LANDER",
                                color=theme.COLORS["danger"],
                                font="ui_small")
            screen.blit(theme.footer(
                size[0],
                "A/D walk   SHIFT run   SPACE jump   X dig ahead   "
                "C dig down   E interact   F flag   R sample"),
                (0, size[1] - theme.FOOTER_H))
            screen.blit(vig, (0, 0))
            present_frame()
            frame_count += 1
            if args.frames and frame_count >= args.frames:
                running = False
            continue

        if scene == "interior" and (interior_home is not None
                                    or interior_vessel is not None):
            # ---- inside the hab: walk the rooms, meet the residents ----
            from aphelion.render.interior_art import (
                FLOOR_Y, PPM, ROOM_W, room_strip, space_backdrop,
                strip_scaled)
            clock.advance_analytic(clock.t + EVA_TIME_FACTOR * real_dt)
            t = clock.t
            ppm_i = float(PPM)
            strip = room_strip(interior_rooms)
            total_m = strip.get_width() / ppm_i
            keys = pygame.key.get_pressed()
            move = 0
            if keys[pygame.K_LEFT] or keys[pygame.K_a]:
                move -= 1
            if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
                move += 1
            if move:
                interior_face = move
                interior_frame += real_dt * 6.0
                interior_x = max(1.0, min(total_m - 1.0,
                                          interior_x + move * 1.8 * real_dt))

            # microgravity unless the spin section (or the ground) holds you
            if interior_vessel is not None:
                g_in = (spin_sim.a_spin(
                    getattr(interior_vessel, "spin_rpm", 0.0),
                    getattr(interior_vessel, "spin_r_m", 25.0))
                    if interior_vessel.landed_at is None else 9.81)
                inhabitants = interior_vessel.crew
                place_name = interior_vessel.name
            else:
                g_in = 9.81
                inhabitants = interior_home.crew
                place_name = interior_home.name
            floating = g_in < 1.0

            # deep space drifts behind the hull cutaway (slow parallax)
            bdrop = space_backdrop(size)
            bx_off = -int((interior_x * ppm_i * 0.25)
                          % (bdrop.get_width() - size[0]))
            screen.blit(bdrop, (bx_off, 0))
            scale_i = 2.0
            strip_big = strip_scaled(interior_rooms, scale_i)
            sh = strip_big.get_height()
            ox = size[0] / 2 - interior_x * ppm_i * scale_i
            oy = size[1] / 2 - sh / 2
            screen.blit(strip_big, (ox, oy))
            # crew share the player's sprite scale — humans, not pixels.
            # Floating = a DRIFT pose (frame 0, slow tumble), never a
            # mid-air walk cycle (ART-DIRECTION §4)
            for ri, rname in enumerate(inhabitants[:6]):
                rx_m = (7.0 + (ri + 1) * (total_m - 10.0) / 7.0
                        + 0.8 * math.sin(ui_t * 0.7 + ri * 2.1))
                fy = (44 + 22 * math.sin(ui_t * 0.9 + ri * 1.7)
                      if floating else 0)
                cspr = eva_art.astronaut(0, -1 if ri % 2 else 1,
                                         False, h_px=148)
                if floating:
                    cspr = pygame.transform.rotozoom(
                        cspr, 9.0 * math.sin(ui_t * 0.5 + ri * 1.3), 1.0)
                screen.blit(cspr, (ox + rx_m * ppm_i * scale_i
                                   - cspr.get_width() / 2,
                                   oy + FLOOR_Y * scale_i
                                   - cspr.get_height() - fy))
            # you
            fy_me = 36 + 16 * math.sin(ui_t * 1.1) if floating else 0
            aspr = eva_art.astronaut(
                0 if floating else int(interior_frame), interior_face,
                False, h_px=160)
            if floating:
                aspr = pygame.transform.rotozoom(
                    aspr, 6.0 * math.sin(ui_t * 0.7), 1.0)
            screen.blit(aspr, (size[0] / 2 - aspr.get_width() / 2,
                               oy + FLOOR_Y * scale_i - aspr.get_height()
                               - fy_me))
            # room label + prompt
            room_i = int(interior_x * ppm_i // ROOM_W) - 1
            if room_i < 0:
                label = ("AIRLOCK — E returns to the flight deck"
                         if interior_vessel is not None else
                         "AIRLOCK — E exits to the surface")
            elif (interior_vessel is not None
                    and room_i < len(interior_labels)):
                label = (interior_labels[room_i][0].upper()
                         + "   ·   E reads the module")
            else:
                label = (interior_rooms[room_i].replace("_", " ").upper()
                         + "   ·   E console")
            theme.draw_text(screen, size[0] / 2 - 120, int(oy) - 26, label,
                            color=theme.COLORS["gold"], font="ui_small")
            chips_in = [(f"INSIDE  {place_name}", theme.COLORS["text"]),
                        (f"{'crew' if interior_vessel is not None else 'residents'}"
                         f" {len(inhabitants)}", theme.COLORS["text_dim"])]
            if interior_vessel is not None:
                chips_in.append(
                    (f"{g_in:.1f} m/s² spin gravity" if not floating
                     else "0 g — handrails", theme.COLORS["accent"]))
            else:
                chips_in.append((f"beds {interior_home.beds()}",
                                 theme.COLORS["text_dim"]))
            chx_i = 10
            for chip_txt, chip_col in chips_in:
                cs = theme.chip(chip_txt, chip_col)
                screen.blit(cs, (chx_i, 8))
                chx_i += cs.get_width() + 8
            screen.blit(theme.footer(
                size[0], "A/D walk   E console / airlock"),
                (0, size[1] - theme.FOOTER_H))
            screen.blit(vig, (0, 0))
            present_frame()
            frame_count += 1
            if args.frames and frame_count >= args.frames:
                running = False
            continue

        # warp-to-node (W): climb the ladder while the burn is far away …
        if node is not None and node["armed"] and warp_to_node:
            while (warp_idx + 1 < len(_WARP_LADDER)
                   and node["t_node"] - t >= _WARP_LADDER[warp_idx + 1] * 6.0):
                warp_idx += 1
        # … and the armed-node guard (01 §3.6) steps down to land on time
        if node is not None and node["armed"]:
            while (warp_idx > 0
                   and node["t_node"] - t < _WARP_LADDER[warp_idx] * 5.0):
                warp_idx -= 1
        if not paused and not pause_open:
            # A-2 warp law: live unacknowledged alerts cap the ladder
            # (Class 2 pins real-time, Class 1 freezes until handled)
            _wrate = abus.warp_max_effective(_WARP_LADDER[warp_idx], t)
            clock.advance_analytic(clock.t + max(_wrate, 0.0) * real_dt)
            autosave_acc += real_dt
            if autosave_acc >= 300.0:        # five real minutes
                autosave_acc = 0.0
                try:
                    do_quicksave(as_path, "AUTOSAVED")
                    toast, toast_until = "autosaved", clock.t + 3.0
                except Exception:
                    pass
        t = clock.t
        av = vessels[active_idx % len(vessels)] if vessels else None
        # node execution at its instant (the plan IS the burn at rails fidelity)
        if node is not None and node["armed"] and t >= node["t_node"]:
            veto = docked_burn_veto(av) if av is not None else None
            if veto is not None:
                toast = f"NODE REFUSED — {veto}"
                audio.play("alarm")
            elif av is not None and av.burn(node["t_node"], node["dvp"],
                                            node["dvr"]):
                toast = (f"NODE EXECUTED: {math.hypot(node['dvp'], node['dvr']):,.0f}"
                         f" m/s")
                burn_glow = 0.8
                node_exec_seen = True
                audio.play("burn")
                research.accrue_event(db, "Avionics", "program_exec",
                                      vessel_id=str(av.vid))
            else:
                toast = "NODE FAILED: insufficient propellant"
                audio.play("alarm")
            toast_until = t + 6
            node = None
            warp_to_node = False
        # orbital yards finish hulls (05 §3.1): the new ship spawns on a
        # gently diverging orbit, tanks DRY — crossfeed from a tanker
        for fv in vessels:
            job_y = getattr(fv, "yard_job", None)
            if not job_y or t < job_y["done_t"]:
                continue
            from aphelion.sim.vessels.vessel import PartRow
            from aphelion.sim.vessels.vessel import Vessel as _VY
            rows_y, plan_y2 = [], []
            for stg in job_y["stack"]:
                idxs = []
                for pid in stg:
                    idxs.append(len(rows_y))
                    rows_y.append(PartRow(part_id=pid, fill={}))
                plan_y2.append(idxs)
            rx_y, ry_y, vx_y, vy_y = fv.state(t)
            r_y = math.hypot(rx_y, ry_y) or 1.0
            mu_y = tree.body(fv.frame_id).mu
            el_y = state_to_elements(
                rx_y, ry_y, vx_y + 1.5 * rx_y / r_y,
                vy_y + 1.5 * ry_y / r_y, t, mu_y)
            built_n = 0
            if 0 <= job_y.get("design", -1) < len(yard_designs):
                yard_designs[job_y["design"]]["built"] = \
                    yard_designs[job_y["design"]].get("built", 0) + 1
                built_n = yard_designs[job_y["design"]]["built"]
            nv_y = FleetVessel(
                tree, fv.frame_id, el_y,
                _VY(db, rows_y, stage_plan=plan_y2, cd_a_m2=3.2),
                f"{job_y['name']}-{built_n or 1}", next_vid, t_now=t)
            next_vid += 1
            vessels.append(nv_y)
            fv.yard_job = None
            milestones.add("orbital_build")
            toast = (f"COMMISSIONED AT THE YARD: {nv_y.name} — built in "
                     f"orbit, tanks dry (dock a tanker, T crossfeeds "
                     f"through a DK-L)")
            toast_until = t + 12
            audio.play("paid")

        # the whole fleet flies: SOI handoffs + first-entry science
        for fv in vessels:
            for note in fv.advance_to(t):
                toast, toast_until = f"SOI {note}", t + 8
                # avionics ED is capped per SOI leg (11 §3.5)
                research.reset_avionics_leg(str(fv.vid))
            if fv.frame_id not in visited:
                visited.add(fv.frame_id)
                mult = science_multiplier(fv, crew)
                sci = _FIRST_ENTRY_SCIENCE.get(fv.frame_id, 200.0) * mult
                research.earn_science(sci)
                sci += research.award_milestone("flyby", fv.frame_id, t)
                if fv.elements.alpha > 0.0 and fv.landed_at is None:
                    sci += research.award_milestone("orbit", fv.frame_id, t)
                toast = (f"FIRST ENTRY: {fv.frame_id.split(':')[1]} "
                         f"+{sci:.0f} science"
                         + (f" (x{mult:.1f} — scientist aboard)"
                            if mult > 1.01 else f" ({fv.name})"))
                toast_until = t + 10
                audio.play("soi")

        # the Act table sweeps REAL state: offers, payouts, the win
        from aphelion.game.campaign import act_progress
        from aphelion.game.campaign import sweep as campaign_sweep
        sweep_state = {"vessels": vessels, "bases": bases, "visited": visited,
                       "visited_surface": visited_surface,
                       "milestones": milestones, "research": research}
        dmul = _DIFFICULTIES[difficulty]
        sweep_toasts, won_now = campaign_sweep(
            program, sweep_state, t,
            payout_mult=dmul["payout"], deadline_mult=dmul["deadline"])
        for line in sweep_toasts:
            toast, toast_until = line, t + 10
            if "PAID" in line:
                audio.play("paid")
                gold_flash = 0.6
            else:
                audio.play("blip")
        if won_now and "won" not in milestones:
            milestones.add("won")
            scene = "victory"
        program.expire_overdue(t)

        # crew dose + vessel life support (08): hourly bookkeeping
        if t - last_dose_t > 3_600.0:
            days = (t - last_dose_t) / 86_400.0
            aboard: dict[str, str] = {}
            for fv in vessels:
                for n in fv.crew:
                    aboard[n] = fv.frame_id
            resident: dict[str, str] = {}
            for b in bases:
                for n in b.crew:
                    resident[n] = SITES[b.site_id]["body"]
            for cname, member in crew.items():
                loc = aboard.get(cname, resident.get(cname, "core:earth"))
                if loc not in AMBIENT_MSV_DAY:
                    loc = "deep_space"
                # flying: hull only; resident: regolith-bermed hab; Earth: sky
                shield = (20.0 if cname in aboard
                          else 100.0 if cname in resident else 1_000.0)
                member.dose.accrue(loc, days, areal_g_cm2=shield,
                                   material="water", t=t)
            # solar-particle events (03 S-8b): warning, storm dose, warp cap
            warn = spe_sched.warning(t)
            if warn is not None and env_state["spe_warned"] != warn[0]:
                env_state["spe_warned"] = warn[0]
                toast = ("SOLAR PARTICLE EVENT INBOUND — protons in "
                         "~45 min; flying crews will take storm dose")
                toast_until = t + 12
                audio.play("alarm")
            ev_spe = spe_sched.active(t)
            if ev_spe is not None:
                _, spe_dur, spe_dose_1au = ev_spe
                spe_frac = min(days * 86_400.0, spe_dur) / spe_dur
                for cname, member in crew.items():
                    loc = aboard.get(cname)
                    if loc is None:     # residents bermed, Earth under sky
                        continue
                    d_au = BODY_OPS.get(loc, {}).get("d", 1.0)
                    member.dose.accrue_event_msv(
                        spe_dose_1au * spe_distance_factor(d_au) * spe_frac,
                        areal_g_cm2=20.0, material="water")
                if any(fv.crew and fv.landed_at is None for fv in vessels) \
                        and warp_idx > 2:
                    warp_idx = 2
                    if not env_state["spe_capped"]:
                        env_state["spe_capped"] = True
                        toast = ("SPE IN PROGRESS — warp capped while "
                                 "crews fly unsheltered")
                        toast_until = t + 10
                        audio.play("alarm")
            else:
                env_state["spe_capped"] = False

            # ---- humans v2 (08 §4): morale, conditioning, energy — the
            # daily character dynamics, integrated at the hourly cadence
            from aphelion.game.basebuild import CATALOG as _CAT
            base_of = {n: b for b in bases for n in b.crew}
            fv_of = {n: fv for fv in vessels for n in fv.crew}
            starved_dead = []
            for cname, member in crew.items():
                fv0 = fv_of.get(cname)
                b0 = base_of.get(cname)
                if fv0 is not None:
                    body0 = fv0.frame_id
                    d_au = BODY_OPS.get(body0, {}).get("d", 1.0)
                    if fv0.landed_at is not None:
                        _bw = tree.body(body0)
                        g_eff = _bw.mu / _bw.radius ** 2
                    else:
                        # spin gravity counts (06 §3.1 rule 7)
                        g_eff = spin_sim.a_spin(
                            getattr(fv0, "spin_rpm", 0.0),
                            getattr(fv0, "spin_r_m", 25.0))
                    ctx = {"vol_m3": 14.0, "private_quarters": False,
                           "window": True, "g_eff": g_eff,
                           "light_min": abs(d_au - 1.0) * 8.32}
                    fed = True        # the vessel LSS clock owns starving
                elif b0 is not None:
                    body0 = SITES[b0.site_id]["body"]
                    d_au = BODY_OPS.get(body0, {}).get("d", 1.0)
                    _bw = tree.body(body0)
                    g_eff = _bw.mu / _bw.radius ** 2
                    beds = sum(_CAT.get(k, {}).get("beds", 0)
                               for k in b0.built)
                    n_res = max(1, len(b0.crew))
                    fresh = any(
                        m.state == "RUNNING"
                        and m.module_id.rsplit("_", 1)[0] in
                        ("greenhouse", "bio_farm", "salad_rack")
                        for m in b0.net.modules)
                    food_buf = b0.net.buffers.get("FoodRations")
                    fed = food_buf is not None and food_buf.level > 0.5
                    ctx = {"vol_m3": 25.0 * max(1, beds) / n_res,
                           "private_quarters": beds >= n_res,
                           "fresh_food": fresh, "plants": fresh,
                           "window": True, "g_eff": g_eff,
                           "light_min": abs(d_au - 1.0) * 8.32}
                else:                 # on Earth between flights: recover
                    member.step_morale(75.0, days)
                    member.step_conditioning(9.81, 0.0, days)
                    member.energy_kcal = BODY_RESERVE_KCAL
                    member.conditions.clear()       # Earth hospitals
                    continue
                member.step_morale(morale_target(ctx, member), days)
                member.step_conditioning(
                    g_eff, 2.0 if g_eff < 3.71 else 0.0, days)
                need = 2_500.0 * days
                member.energy_kcal = min(
                    BODY_RESERVE_KCAL,
                    member.energy_kcal + (need if fed else 0.0) - need)
                if member.energy_kcal <= 0.0:
                    starved_dead.append(cname)
            for cname in starved_dead:
                crew.pop(cname, None)
                for v in vessels:
                    if cname in v.crew:
                        v.crew.remove(cname)
                for b in bases:
                    if cname in b.crew:
                        b.crew.remove(cname)
                for m2 in crew.values():
                    m2.morale = max(0.0, m2.morale - 25.0)
                toast = f"{cname} STARVED — the food chain failed"
                toast_until = t + 14
                audio.play("alarm")

            # industry wear (05 §3.4): fab modules wear while RUNNING,
            # auto-PM draws real parts, the labor pool re-prices f_labor
            _a3 = "core:tech_in09_supervised_autonomy" in research.unlocked
            for b in bases:
                dusty_b = SITES[b.site_id].get("kind", "regolith") in (
                    "regolith", "mars_ice", "psr_ice")
                for note in b.step_wear(days * 24.0, dusty_b):
                    toast, toast_until = note, t + 8
                    audio.play("warn")
                b.apply_crew_effects(crew, a3=_a3)

            # mass drivers fling whitelist bulk to an orbiting catcher
            # (05 §3.2): 43.2 t/day, zero propellant, 2% miss
            from aphelion.sim.industry import logistics as logi_sim
            for b in bases:
                md_mod = next((m for m in b.net.modules
                               if m.module_id.startswith("mass_driver")
                               and m.state == "RUNNING"), None)
                if md_mod is None:
                    continue
                _, _, f_pw = b.net.solve_rates()
                if f_pw < 0.95:
                    continue              # the 2.6 MW duty isn't served
                body_b = SITES[b.site_id]["body"]
                catcher = next(
                    (v for v in vessels
                     if v.frame_id == body_b and v.landed_at is None
                     and v.cargo_cap_kg - v.cargo_kg > 100.0), None)
                if catcher is None:
                    continue
                budget_kg = logi_sim.MD_THROUGHPUT_T_DAY * 1e3 * days
                flung = 0.0
                for res in logi_sim.MD_WHITELIST:
                    if budget_kg <= 0.0:
                        break
                    buf = b.net.buffers.get(res)
                    if buf is None or buf.level <= 0.0:
                        continue
                    room = ((catcher.cargo_cap_kg - catcher.cargo_kg)
                            / (1.0 - logi_sim.MD_MISS_FRAC))
                    take = min(budget_kg, buf.level, room)
                    if take <= 0.0:
                        continue
                    buf.level -= take
                    catcher.load_cargo(
                        res, take * (1.0 - logi_sim.MD_MISS_FRAC))
                    budget_kg -= take
                    flung += take
                if flung > 0.0 and not env_state.get("md_seen"):
                    env_state["md_seen"] = True
                    toast = (f"MASS DRIVER: {flung / 1e3:,.1f} t flung "
                             f"to {catcher.name} for zero propellant "
                             f"(2% catcher miss)")
                    toast_until = t + 10
                    audio.play("paid")

            # bent docking rings: an engineer aboard (or a landed base's
            # shop) works the backlog off in real hours
            for fv in vessels:
                rep = getattr(fv, "port_repair_h", 0.0)
                if rep <= 0.0:
                    continue
                if fv.landed_at is not None \
                        or best_skill(fv, crew, "engineer") >= 1:
                    fv.port_repair_h = max(0.0, rep - days * 24.0)
                    if fv.port_repair_h == 0.0:
                        toast = (f"{fv.name}: docking ring trued and "
                                 f"re-certified")
                        toast_until = t + 6
                        audio.play("blip")

            # medicine runs on a daily cadence (08 §4.6)
            env_state["med_acc"] = env_state.get("med_acc", 0.0) + days
            if env_state["med_acc"] >= 1.0:
                d_med = env_state["med_acc"]
                env_state["med_acc"] = 0.0
                # transient per-day generator: registry streams serialize
                # into saves, and a key-per-day would bloat them forever
                med_rng = np.random.Generator(np.random.PCG64(
                    np.random.SeedSequence(
                        entropy=campaign_rng.campaign_seed ^ 0x4D454443,
                        spawn_key=(int(t // 86_400),))))
                med_dead = []
                for cname, member in crew.items():
                    fv0 = fv_of.get(cname)
                    b0 = base_of.get(cname)
                    if fv0 is None and b0 is None:
                        continue                  # home: handled above
                    if b0 is not None:
                        med_lvl = max(
                            (crew[n].skills.get("medic", 0)
                             for n in b0.crew if n in crew), default=0)
                        if "med_bay" not in b0.built:
                            med_lvl = min(med_lvl, 1)   # field care only
                        sup_buf = b0.net.buffers.get("MedSupplies")
                        sup = sup_buf.level if sup_buf else 0.0
                        crowded = len(b0.crew) > sum(
                            _CAT.get(k, {}).get("beds", 0)
                            for k in b0.built)
                    else:
                        med_lvl = best_skill(fv0, crew, "medic")
                        sup_buf, sup = None, 2.0        # flight medkit
                        crowded = len(fv0.crew) > 3
                    kind = member.roll_medical(med_rng, crowded=crowded,
                                               medic_aboard=med_lvl)
                    if kind:
                        toast = (f"MEDICAL: {cname} — "
                                 f"{kind.replace('_', ' ')}"
                                 + ("" if med_lvl > 0
                                    else " (no medic nearby)"))
                        toast_until = t + 10
                        audio.play("warn")
                    out_med = member.step_medical(d_med, med_lvl, sup,
                                                  med_rng)
                    if sup_buf is not None and out_med["supplies_used"]:
                        sup_buf.level = max(
                            0.0, sup_buf.level - out_med["supplies_used"])
                    if out_med["died_of"]:
                        med_dead.append((cname, out_med["died_of"]))
                for cname, cause in med_dead:
                    crew.pop(cname, None)
                    for v in vessels:
                        if cname in v.crew:
                            v.crew.remove(cname)
                    for b in bases:
                        if cname in b.crew:
                            b.crew.remove(cname)
                    for m2 in crew.values():
                        m2.morale = max(0.0, m2.morale - 25.0)
                    toast = (f"{cname} DIED of {cause.replace('_', ' ')}"
                             f" — a medbay, a surgeon and MedSupplies "
                             f"would have saved them")
                    toast_until = t + 14
                    audio.play("alarm")

            # Mars dust (03 S-9): storms throttle every solar array on Mars
            mars_storm = mars_wx.global_storm_active(t)
            fd_mars = mars_f_dust(mars_wx.tau(t))
            for b in bases:
                if SITES[b.site_id]["body"] != "core:mars":
                    continue
                base_solar = _CAT["solar_array"]["power_kw"] \
                    * SITES[b.site_id].get("solar", 1.0)
                for m in b.net.modules:
                    if m.module_id.startswith("solar_array"):
                        m.power_kw = base_solar * fd_mars
            if mars_storm != env_state["storm_was"]:
                env_state["storm_was"] = mars_storm
                toast = (("MARS GLOBAL DUST STORM — solar output collapsing"
                          f" (f_dust {fd_mars:.2f})") if mars_storm
                         else "Mars dust storm clearing — arrays recovering")
                toast_until = t + 12
                audio.play("alarm" if mars_storm else "blip")

            # the radiator doctrine (09 H-1/H-2): rejection scales with
            # the local sink — the lunar-noon 330 K trap is real. Declared
            # waste heat (reactors, exothermic plants) beyond capacity
            # SCRAMs the hottest emitter.
            from aphelion.sim.power import sink_factor, thermal_balance_kw
            for b in bases:
                site_kind = SITES[b.site_id].get("kind", "regolith")
                sf = sink_factor(site_kind, b.daylight(t) > 0.0)
                for m in b.net.modules:
                    spec0 = _CAT.get(m.module_id.rsplit("_", 1)[0])
                    if spec0 and spec0.get("radiator"):
                        m.heat_kw = spec0["heat_kw"] * sf
                emitted, capacity = thermal_balance_kw(b.net)
                if emitted > capacity * 1.05 and emitted > 1.0:
                    hottest = max(
                        (m for m in b.net.modules
                         if m.state == "RUNNING" and (m.heat_kw or 0) > 0),
                        key=lambda m: m.heat_kw, default=None)
                    if hottest is not None:
                        hottest.state = "OFF"
                        toast = (f"{b.name}: THERMAL TRIP — "
                                 f"{hottest.module_id} SCRAM "
                                 f"({emitted:,.0f} kWt emitted vs "
                                 f"{capacity:,.0f} rejected; build "
                                 f"radiators)")
                        toast_until = t + 12
                        audio.play("alarm")

            # orbital surveys (03 S-10): mapping accrues in low orbit; L1
            # completion pays the one-shot region survey + SurveyData
            for fv in vessels:
                sbody = fv.frame_id
                if (fv.landed_at is not None or sbody == "core:sun"
                        or fv.elements.alpha <= 0.0):
                    continue
                reg = ORBIT_REGION.get(sbody) or SURF_REGION.get(sbody)
                if reg is None or f"orbital|{reg[0]}" in research.surveys:
                    continue
                bb = tree.body(sbody)
                srx, sry, _, _ = fv.state(t)
                if math.hypot(srx, sry) > bb.radius + 5.0e6:
                    continue            # above the 5,000 km scan ceiling
                prog = explore["survey_progress"].get(sbody, 0.0) \
                    + days / 30.0       # full map in ~30 days on station
                explore["survey_progress"][sbody] = prog
                if prog >= 1.0:
                    code, x_reg = reg
                    sci = research.award_survey("orbital", code, x_reg, t)
                    gb = max(5.0, 20.0 * math.sqrt(bb.radius / 1.0e6))
                    explore["surveydata_gb"] += gb
                    toast = (f"ORBITAL SURVEY COMPLETE: "
                             f"{sbody.split(':')[1]} — +{sci:.0f} sci, "
                             f"+{gb:.0f} GB SurveyData")
                    toast_until = t + 12
                    audio.play("paid")

            # engineering data tracks OPERATIONS per part FAMILY (11 §3.5):
            # running modules accrue to their family with √N damping and
            # the ×3 novel-environment window per site class
            fam_groups: dict[tuple[str, str], int] = {}
            for b in bases:
                env = _KIND_ENV.get(SITES[b.site_id].get("kind"),
                                    "vacuum_dusty_surface")
                for m in b.net.modules:
                    if m.state == "RUNNING":
                        fam = MODULE_FAMILY.get(m.module_id.rsplit("_", 1)[0])
                        if fam:
                            key = (fam, env)
                            fam_groups[key] = fam_groups.get(key, 0) + 1
            for (fam, env), n_units in fam_groups.items():
                research.accrue_hours(db, fam, days * 24.0,
                                      n_units=n_units, env_class=env)
            # crewed habs log PressureStructures hours
            for b in bases:
                if b.crew:
                    habs = sum(1 for m in b.net.modules
                               if m.module_id.startswith("hab_module"))
                    if habs:
                        research.accrue_hours(
                            db, "PressureStructures", days * 24.0,
                            n_units=habs,
                            env_class=_KIND_ENV.get(
                                SITES[b.site_id].get("kind"),
                                "vacuum_dusty_surface"))
            labs_on = sum(1 for b in bases for m in b.net.modules
                          if m.module_id.startswith("science_lab")
                          and m.state == "RUNNING")
            if labs_on:
                research.earn_science(2.5 * days * labs_on)
            # the program has a payroll: fixed ops + salaries + base upkeep
            burn = (_OVERHEAD_FIXED_M + _OVERHEAD_PER_CREW_M * len(crew)
                    + _OVERHEAD_PER_BASE_M * len(bases)) * 1e6 \
                * days / 30.0 * _DIFFICULTIES[difficulty]["overhead"]
            if burn > 0.0:
                program.spend(t, min(burn, program.funds),
                              "program overhead")
            # E wiring: production high-water marks feed the extraction
            # Firsts (the best shelf level ever seen per resource — a
            # monotone, save-persistent proxy for cumulative output)
            for b in bases:
                for res, buf in b.net.buffers.items():
                    lvl_t = buf.level / 1000.0
                    if lvl_t > prod_hwm.get(res, 0.0):
                        prod_hwm[res] = lvl_t
            # the Firsts ladder + Prestige (12 §1.5): one-shot, paid
            # through the existing Program ledger, logged forever
            S_acts = acts_snapshot()
            _new_f = acts_mod.check_firsts(S_acts, firsts_earned)
            if _new_f:
                for _tl in acts_mod.award_firsts(
                        program, prestige, t, S_acts, firsts_earned,
                        funding_mult=_DIFFICULTIES[difficulty]["payout"]):
                    toast, toast_until = _tl, t + 12
                audio.play("paid")
                for _fid in _new_f:
                    chron.add(t, f"FIRST_{_fid.upper()}",
                              acts_mod.FIRST_BY_ID[_fid].name,
                              numbers={"prestige": acts_mod.first_prestige(
                                  _fid, S_acts)})
            # alert taxonomy sweeps: contract deadlines (E-9 T-90/30/7)
            # and the G-9 runway death-spiral ladder
            alerts_mod.deadline_sweep(abus, program.contracts, t)
            _burn_day = ((_OVERHEAD_FIXED_M
                          + _OVERHEAD_PER_CREW_M * len(crew)
                          + _OVERHEAD_PER_BASE_M * len(bases)) * 1e6
                         / 30.0 * _DIFFICULTIES[difficulty]["overhead"])
            if _burn_day > 0.0:
                _rw_d = program.funds / _burn_day
                _rw_cls = 2 if _rw_d < 14 else 3 if _rw_d < 60 else 0
                if _rw_cls and _rw_cls != runway_state["cls"]:
                    alerts_mod.runway_sweep(abus, t, _rw_d)
                runway_state["cls"] = _rw_cls
            for _al in abus.toasts(t):
                if _al.aid not in alerts_seen:
                    alerts_seen.add(_al.aid)
                    toast = f"{_al.text}   (BACKSPACE acks alerts)"
                    toast_until = t + 8
                    audio.play("alarm" if _al.cls <= 2 else "warn")
            last_dose_t = t
            for fv in vessels:
                for ev_txt in fv.tick_lss(t):
                    toast, toast_until = ev_txt, t + 10
                    audio.play("alarm")
                    if "EXHAUSTED" in ev_txt:
                        for cname in list(crew):
                            if cname in ev_txt:
                                del crew[cname]
            for name in reap_over_limit(crew, vessels):
                program.spend(t, min(25e6, program.funds),
                              f"casualty review: {name}")
                toast = (f"{name} has exceeded the career radiation limit "
                         f"— lost to the program (−$25M review)")
                toast_until = t + 12
                audio.play("alarm")
            if crew:
                worst = max(crew.values(),
                            key=lambda c: c.dose.career_fraction)
                if worst.dose.career_fraction > 0.8 and not crew_warned:
                    crew_warned = True
                    toast = (f"CREW DOSE WARNING: {worst.name} at "
                             f"{worst.dose.career_fraction:.0%} of career "
                             f"limit — get them home")
                    toast_until = t + 10
                    audio.play("alarm")

        # bases tick on the ledger (warp-exact); contracts watch via sweep
        for site in bases:
            for ev in site.advance(t, crew):
                if ev.kind == "module_failed":
                    eta_h = site.repair_turnaround(crew) / 3_600.0
                    toast = (f"{site.name}: {ev.subject} FAILED — repair in "
                             f"{eta_h:,.0f} h")
                    toast_until = t + 8
                    audio.play("alarm")
                elif ev.kind == "commissioned":
                    toast = f"{site.name}: {ev.subject} COMMISSIONED — online"
                    toast_until = t + 8
                    audio.play("paid")
                elif ev.kind == "repaired":
                    # investigated failure: lessons learned pay family ED
                    fam = MODULE_FAMILY.get(
                        ev.subject.rsplit("_", 1)[0]) or "FabricationMachines"
                    got = research.accrue_event(db, fam,
                                                "failure_investigated")
                    toast = (f"{site.name}: {ev.subject} repaired "
                             f"(+{got:.0f} {fam} data)")
                    toast_until = t + 6
                    audio.play("blip")

        # tutorial rails (12 §5.8): complete from real state, then the
        # next rail teaches the next system the campaign demands
        legs_now = av.predict(t) if av is not None else []
        if tutorial.update({
            "builder_open": builder_open,
            "stack_launchable": (
                sum(1 for s2 in builder.stack if s2) >= 2
                and any(db.parts[p]["type"] == "crew"
                        for s2 in builder.stack for p in s2)),
            "in_orbit": av is not None and av.landed_at is None,
            "warp_idx": warp_idx,
            "apo_m": ((av.elements.apoapsis - tree.body(av.frame_id).radius)
                      if av is not None and av.elements.alpha > 0 else 0.0),
            "moon_leg": any(leg.frame_id == "core:moon" for leg in legs_now),
            "frame": av.frame_id if av is not None else "",
            "moon_paid": any(c.contract_id == "c_moon"
                             and c.completed_t is not None
                             for c in program.contracts),
            "node_placed": node is not None,
            "node_armed": node is not None and node["armed"],
            "node_executed": node_exec_seen,
            "fleet_two": sum(1 for v in vessels
                             if v.landed_at is None) >= 2,
            "prox_open": prox_seen,
            "docked": "docked" in milestones,
            "landed_surface": bool(visited_surface),
            "base_founded": bool(bases),
            "base_producing": any(
                b.net.buffers.get("Oxygen") is not None
                and b.net.buffers["Oxygen"].level > 1_000.0
                for b in bases),
        }):
            audio.play("blip")
        if tutorial.completed:
            nxt = next_rail(tutorial.done_rails | {tutorial.rail})
            if nxt is not None:
                nxt.visible = tutorial.visible
                tutorial = nxt
                toast = (f"NEW OBJECTIVE RAIL — "
                         f"{tutorial.steps[0].text[:48]}…")
                toast_until = t + 8

        # camera follow (positions in ROOT frame; camera frame is the root)
        def body_root(bid: str) -> tuple[float, float]:
            rx, ry, _, _ = tree.state_in_root(bid, t)
            return rx, ry

        focus = focus_order[focus_idx]
        if focus == "craft":
            if av is not None and av.landed_at is None:
                frx, fry = body_root(av.frame_id)
                crx, cry, _, _ = av.state(t)
                cam.follow(frx + crx, fry + cry)
            elif av is not None:
                cam.follow(*body_root(av.frame_id))
            else:
                cam.follow(*body_root("core:earth"))
        elif focus == "core:sun":
            cam.follow(0.0, 0.0)
        else:
            cam.follow(*body_root(focus))

        screen.fill((6, 8, 14))
        nebula.draw(screen, cam)
        starfield.draw(screen, cam)
        body_click_pts = []

        def blit_body(bid: str, wx: float, wy: float, px: tuple) -> None:
            """Shaded sprite when resolved, crisp marker dot otherwise."""
            d_px = 2.0 * tree.body(bid).radius * cam.zoom
            if d_px >= 5.0:
                # light comes FROM the sun at the world origin (screen y-down)
                ang = math.atan2(wy, -wx) if (wx or wy) else 0.0
                spr = body_sprite(bid, min(int(d_px), 512), ang)
                screen.blit(spr, (px[0] - spr.get_width() // 2,
                                  px[1] - spr.get_height() // 2))
            else:
                dot = marker_dot(bid, 3)
                screen.blit(dot, (px[0] - dot.get_width() // 2,
                                  px[1] - dot.get_height() // 2))

        for pid in planets:
            draw_conic(screen, tree.body(pid).elements, cam, _ORBIT_COLOR,
                       glow=True)
        sun_px = cam.world_to_screen(0.0, 0.0)
        if -400 < sun_px[0] < size[0] + 400 and -400 < sun_px[1] < size[1] + 400:
            sd = max(10, min(int(2.0 * tree.body("core:sun").radius * cam.zoom),
                             512))
            # anamorphic streak UNDER the disc: the sun reads as the light
            # source of the whole frame, not another sprite (F0.8)
            stk = sun_streak(max(sd, 26))
            screen.blit(stk, (sun_px[0] - stk.get_width() // 2,
                              sun_px[1] - stk.get_height() // 2),
                        special_flags=pygame.BLEND_ADD)
            sspr = sun_sprite(sd)
            screen.blit(sspr, (sun_px[0] - sspr.get_width() // 2,
                               sun_px[1] - sspr.get_height() // 2))
            body_click_pts.append((sun_px[0], sun_px[1], 1))
        for pid in planets:
            prx, pry = body_root(pid)
            ppx = cam.world_to_screen(prx, pry)
            on_screen = -60 < ppx[0] < size[0] + 60 and -60 < ppx[1] < size[1] + 60
            if on_screen:
                blit_body(pid, prx, pry, ppx)
                # label clears the disc: beside small dots, under big spheres
                _lr = tree.body(pid).radius * cam.zoom
                screen.blit(font.render(pid.split(":")[1], True, (150, 160, 180)),
                            (ppx[0] + 8, ppx[1] + max(-8, _lr * 0.78 + 4)))
                body_click_pts.append((ppx[0], ppx[1], focus_of_body[pid]))
            for mid in moons_of.get(pid, []):
                mel = tree.body(mid).elements
                draw_conic(screen, mel, cam, _MOON_ORBIT_COLOR,
                           origin=(prx, pry), glow=True)
                mrx, mry, _, _ = tree.state_in_parent(mid, t)
                mpx = cam.world_to_screen(prx + mrx, pry + mry)
                if (2.0 * abs(mel.a) * cam.zoom > 8.0
                        and -60 < mpx[0] < size[0] + 60 and -60 < mpx[1] < size[1] + 60):
                    blit_body(mid, prx + mrx, pry + mry, mpx)
                    _mr = tree.body(mid).radius * cam.zoom
                    screen.blit(font.render(mid.split(":")[1], True, (120, 130, 150)),
                                (mpx[0] + 7, mpx[1] + max(-7, _mr * 0.78 + 4)))
                    body_click_pts.append((mpx[0], mpx[1], focus_of_body[mid]))

        # SOI boundary of the active vessel's frame (faint dashed cyan)
        if av is not None:
            soi_m = tree.body(av.frame_id).soi_radius
            if math.isfinite(soi_m):
                soi_px = int(soi_m * cam.zoom)
                if 24 < soi_px <= 2000:
                    ring = soi_ring(soi_px)
                    if ring is not None:
                        frx_s, fry_s = body_root(av.frame_id)
                        fpx = cam.world_to_screen(frx_s, fry_s)
                        screen.blit(ring, (fpx[0] - ring.get_width() // 2,
                                           fpx[1] - ring.get_height() // 2))

        # navigation target: bright orbit, its SOI bubble, a diamond tag —
        # the thing you are trying to hit is no longer invisible
        if target_id is not None and target_id in db.bodies:
            tparent = db.bodies[target_id]["parent"]
            torigin = ((0.0, 0.0) if tparent == "core:sun"
                       else body_root(tparent))
            draw_conic(screen, tree.body(target_id).elements, cam,
                       (110, 190, 255), origin=torigin, glow=True)
            ttx, tty = body_root(target_id)
            tpx = cam.world_to_screen(ttx, tty)
            soi_t = tree.body(target_id).soi_radius
            if math.isfinite(soi_t):
                spx_t = int(soi_t * cam.zoom)
                if 10 < spx_t <= 2000:
                    ring = soi_ring(spx_t)
                    if ring is not None:
                        screen.blit(ring, (tpx[0] - ring.get_width() // 2,
                                           tpx[1] - ring.get_height() // 2))
            if (math.isfinite(tpx[0]) and math.isfinite(tpx[1])
                    and -50 < tpx[0] < size[0] + 50
                    and -50 < tpx[1] < size[1] + 50):
                pygame.draw.polygon(screen, (110, 190, 255),
                                    [(tpx[0], tpx[1] - 9), (tpx[0] + 9, tpx[1]),
                                     (tpx[0], tpx[1] + 9), (tpx[0] - 9, tpx[1])],
                                    width=1)

        # node preview: post-burn legs (lightened frame hues) + node marker
        node_post = None
        node_enc = None
        if node is not None and av is not None:
            from aphelion.sim.flight.node_exec import ManeuverNode, apply_node_impulsive
            try:
                post = apply_node_impulsive(
                    av.elements,
                    ManeuverNode(node["t_node"], node["dvp"], node["dvr"]))
                node_legs = predict_trajectory(tree, av.frame_id, post,
                                               node["t_node"], _PREDICT_HORIZON)
                node_post = post
                for leg in node_legs:
                    lfx, lfy = body_root(leg.frame_id)
                    r_soi_l = tree.body(leg.frame_id).soi_radius
                    fc = _frame_color(leg.frame_id)
                    lite = tuple(min(255, int(c * 0.45 + 140)) for c in fc)
                    draw_conic(screen, leg.elements, cam, lite,
                               r_max=r_soi_l if math.isfinite(r_soi_l) else None,
                               origin=(lfx, lfy))
                    if (target_id is not None and node_enc is None
                            and leg.frame_id == target_id):
                        node_enc = leg
                nfx, nfy = body_root(av.frame_id)
                nx, ny, _, _ = elements_to_state(av.elements, node["t_node"])
                npx = cam.world_to_screen(nfx + nx, nfy + ny)
                if (math.isfinite(npx[0]) and math.isfinite(npx[1])
                        and -100 < npx[0] < size[0] + 100
                        and -100 < npx[1] < size[1] + 100):
                    pygame.draw.circle(screen, (255, 120, 220), npx, 5,
                                       width=2)
            except Exception:
                pass

        # the fleet: active vessel gets trajectory legs + big icon; the
        # rest draw as dim markers with names (click to take command)
        vessel_click_pts = []
        soi_marks: list[tuple[float, float, str]] = []
        apsis_marks: list[tuple[tuple, str, float]] = []
        if av is not None:
            _avx, _avy, _, _ = av.state(t)
            _av_px = cam.world_to_screen(_avx, _avy)
            for _li, leg in enumerate(av.predict(t)):
                frx, fry = body_root(leg.frame_id)
                r_soi = tree.body(leg.frame_id).soi_radius
                r_max = r_soi if math.isfinite(r_soi) else None
                draw_conic(screen, leg.elements, cam,
                           _frame_color(leg.frame_id),
                           r_max=r_max, origin=(frx, fry), glow=True,
                           fade_from=(_av_px if _li == 0 and
                                      math.isfinite(_av_px[0]) else None))
                if leg.end_reason.startswith("soi"):
                    ex, ey, _, _ = elements_to_state(leg.elements, leg.t_end)
                    epx = cam.world_to_screen(frx + ex, fry + ey)
                    if math.isfinite(epx[0]) and math.isfinite(epx[1]):
                        nxt = (leg.end_reason.split(":", 1)[1]
                               if ":" in leg.end_reason
                               else db.bodies[leg.frame_id]["parent"])
                        soi_marks.append(
                            (epx[0], epx[1],
                             f"{nxt.split(':')[-1]}  "
                             f"{theme.fmt_duration(leg.t_end - t)}"))
            # Ap/Pe chevrons on the CURRENT orbit when it subtends enough
            if av.landed_at is None and av.elements.alpha > 0:
                el_a = av.elements
                frx, fry = body_root(av.frame_id)
                body_r = tree.body(av.frame_id).radius
                if 2.0 * el_a.a * cam.zoom > 70.0:
                    for rr, ang, tag2 in (
                            (el_a.periapsis, el_a.varpi, "Pe"),
                            (el_a.apoapsis, el_a.varpi + math.pi, "Ap")):
                        if not math.isfinite(rr) or (tag2 == "Ap"
                                                     and el_a.e < 1e-4):
                            continue
                        ppx2 = cam.world_to_screen(frx + rr * math.cos(ang),
                                                   fry + rr * math.sin(ang))
                        if (math.isfinite(ppx2[0]) and math.isfinite(ppx2[1])
                                and -40 < ppx2[0] < size[0] + 40
                                and -40 < ppx2[1] < size[1] + 40):
                            apsis_marks.append((ppx2, tag2, rr - body_r))
        for vi, fv in enumerate(vessels):
            vfx, vfy = body_root(fv.frame_id)
            if fv.landed_at is not None:
                body_r = tree.body(fv.frame_id).radius
                ang = 0.9 * list(SITES).index(fv.landed_at) + 0.6
                vpx = cam.world_to_screen(vfx + body_r * math.cos(ang),
                                          vfy + body_r * math.sin(ang))
                heading, vvx, vvy = math.pi / 2.0, 0.0, 0.0
            else:
                vrx, vry, vvx, vvy = fv.state(t)
                vpx = cam.world_to_screen(vfx + vrx, vfy + vry)
                heading = math.atan2(-vvy, vvx)
            if not (math.isfinite(vpx[0]) and math.isfinite(vpx[1])
                    and -200 < vpx[0] < size[0] + 200
                    and -200 < vpx[1] < size[1] + 200):
                continue
            is_active = fv is av
            cspr = craft_icon(heading, size=14 if is_active else 9,
                              burning=is_active and burn_glow > 0.0)
            if not is_active:
                cspr = cspr.copy()
                cspr.set_alpha(140)
                tag = fv.name + (" [LANDED]" if fv.landed_at else "")
                screen.blit(font.render(tag, True, (110, 122, 140)),
                            (vpx[0] + 10, vpx[1] - 10))
            screen.blit(cspr, (vpx[0] - cspr.get_width() // 2,
                               vpx[1] - cspr.get_height() // 2))
            vessel_click_pts.append((vpx[0], vpx[1], vi))
        burn_glow = max(0.0, burn_glow - real_dt)

        # world is done — bloom it, then draw the HUD glass on top
        particles.update_draw(screen, real_dt)
        bloom.apply(screen)

        # crisp world annotations above the bloom: SOI crossings, Ap/Pe
        for mx2, my2, lbl in soi_marks:
            if -40 < mx2 < size[0] + 40 and -40 < my2 < size[1] + 40:
                pygame.draw.polygon(
                    screen, (235, 240, 250),
                    [(mx2, my2 - 5), (mx2 + 5, my2), (mx2, my2 + 5),
                     (mx2 - 5, my2)], width=1)
                theme.draw_text(screen, int(mx2) + 8, int(my2) - 6, lbl,
                                color=theme.COLORS["text_dim"], font="small")
        for ppx2, tag2, alt_m in apsis_marks:
            col = (theme.COLORS["accent"] if tag2 == "Pe"
                   else theme.COLORS["warn"])
            if alt_m < 0:
                col = theme.COLORS["danger"]
            pygame.draw.polygon(
                screen, col, [(ppx2[0], ppx2[1] - 6), (ppx2[0] + 5, ppx2[1] + 3),
                              (ppx2[0] - 5, ppx2[1] + 3)], width=1)
            theme.draw_text(screen, ppx2[0] + 8, ppx2[1] - 7,
                            f"{tag2} {alt_m / 1e3:,.0f} km", color=col,
                            font="small")

        if node is not None:
            state_txt = "ARMED" if node["armed"] else "editing"
            screen.blit(font.render(
                f"NODE [{state_txt}] T-{theme.fmt_duration(max(0.0, node['t_node'] - t))}   "
                f"prograde {node['dvp']:+,.0f}  radial {node['dvr']:+,.0f}  "
                f"({math.hypot(node['dvp'], node['dvr']):,.0f} m/s)",
                True, (255, 120, 220)), (10, size[1] - 48))
            # O wiring: the finite burn this node actually is (01 §2.9) —
            # t_b from the rocket equation, ignition centered on the node
            _ndv = math.hypot(node["dvp"], node["dvr"])
            if av is not None and _ndv > 0.5:
                _F = av.vessel.active_thrust_n(0.0)
                if _F <= 0.0:
                    screen.blit(font.render(
                        "no active engine — node cannot be executed",
                        True, theme.COLORS["danger"]), (10, size[1] - 88))
                else:
                    _ve = av.vessel.active_isp(0.0) * 9.80665
                    _m0 = av.vessel.total_mass_kg()
                    _tb = (_m0 * _ve / _F) * (1.0 - math.exp(-_ndv / _ve))
                    _ign = node["t_node"] - 0.5 * _tb
                    _frac = (_tb / av.elements.period
                             if av.elements.alpha > 0 else 0.0)
                    _btxt = (f"burn {theme.fmt_duration(_tb)} — ignition "
                             f"T-{theme.fmt_duration(max(0.0, _ign - t))}"
                             + (f"   ({_frac:.0%} of orbit: impulse "
                                f"approx degrades)"
                                if _frac > 0.12 else ""))
                    _bcol = ((255, 170, 235) if _frac <= 0.12 and _ign > t
                             else theme.COLORS["warn"] if _ign > t
                             else theme.COLORS["danger"])
                    if _ign <= t and not node["armed"]:
                        _btxt = ("IGNITION TIME PASSED — " + _btxt)
                    screen.blit(font.render(_btxt, True, _bcol),
                                (10, size[1] - 88))
            if node_post is not None and av is not None:
                body_r = tree.body(av.frame_id).radius
                pe_post = node_post.periapsis - body_r
                ap_post = (node_post.apoapsis - body_r
                           if node_post.alpha > 0 else float("inf"))
                after = (f"after: Pe {pe_post / 1e3:,.0f} km  Ap "
                         + ("escape" if not math.isfinite(ap_post)
                            else f"{ap_post / 1e3:,.0f} km"))
                if node_enc is not None:
                    enc_pe = (node_enc.elements.periapsis
                              - tree.body(node_enc.frame_id).radius)
                    after += (f"   ENCOUNTER {node_enc.frame_id.split(':')[1]}"
                              f" — Pe {enc_pe / 1e3:,.0f} km"
                              + ("  IMPACT" if enc_pe < 0 else ""))
                screen.blit(font.render(after, True, (255, 170, 235)),
                            (10, size[1] - 68))

        if av is not None and av.landed_at is not None:
            lss = f"   LSS {av.lss_margin_days:,.0f} d" if av.crew else ""
            hud2 = (f"{av.name} — LANDED: {SITES[av.landed_at]['name']}   "
                    f"dv {av.dv_remaining:,.0f} m/s   G surface ops{lss}")
        elif av is not None:
            el = av.elements
            body = tree.body(av.frame_id)
            crx, cry, cvx, cvy = av.state(t)
            alt = math.hypot(crx, cry) - body.radius
            peri = el.periapsis - body.radius
            apo = (el.apoapsis - body.radius) if el.alpha > 0 else float("inf")
            lss = (f"   LSS {av.lss_margin_days:,.0f} d"
                   if av.crew else "")
            hud2 = (f"{av.name} @ {av.frame_id.split(':')[1]}   "
                    f"alt {alt/1e3:,.0f} km   v {math.hypot(cvx, cvy):,.0f} m/s   "
                    f"peri {peri/1e3:,.0f} km   apo {apo/1e3:,.0f} km   "
                    f"dv {av.dv_remaining:,.0f} m/s   "
                    f"stages {len(av.vessel.stage_plan)}{lss}")
        else:
            hud2 = "NO VESSEL — press B to build and launch your first rocket"
        open_contracts = [c for c in program.contracts
                          if c.completed_t is None and not c.failed]
        worst_frac = max((c.dose.career_fraction for c in crew.values()),
                         default=0.0)
        screen.blit(theme.panel(size[0], 76), (0, 0))
        chx = 10                            # status row: chips, not a string
        _wcap = abus.highest_warp_cap(t)
        _wcapped = _wcap < _WARP_LADDER[warp_idx]
        for chip_txt, chip_col in (
                (f"T+ {t / SECONDS_PER_DAY:,.2f} d", theme.COLORS["text"]),
                (f"warp {_WARP_LADDER[warp_idx]:,.0f}x"
                 + ("  ·  PAUSED" if paused else
                    f"  ·  ALERT-CAPPED {_wcap:,.0f}x" if _wcapped else ""),
                 theme.COLORS["warn"] if paused or _wcapped
                 else theme.COLORS["accent"]),
                (f"focus  {focus.split(':')[-1]}", theme.COLORS["text_dim"]),
                (f"fleet  {len(vessels)}", theme.COLORS["text_dim"])):
            cs = theme.chip(chip_txt, chip_col)
            screen.blit(cs, (chx, 5))
            chx += cs.get_width() + 8
        screen.blit(theme.icon("dv", 14), (12, 32))
        theme.draw_text(screen, 32, 31, hud2, color=_CRAFT_COLOR)
        chx = 10                            # program row
        for chip_txt, chip_col in (
                (f"$ {program.funds / 1e6:,.0f}M", theme.COLORS["gold"]),
                (f"P {prestige.value:,.0f}", theme.COLORS["gold"]),
                (f"sci {research.science:,.0f}", theme.COLORS["accent"]),
                (f"tech {len(research.unlocked)}/{len(db.tech)}",
                 theme.COLORS["accent"]),
                (f"dose {worst_frac:.0%}",
                 theme.COLORS["danger"] if worst_frac > 0.8
                 else theme.COLORS["text_dim"]),
                (act_progress(program), theme.COLORS["text"])):
            cs = theme.chip(chip_txt, chip_col)
            screen.blit(cs, (chx, 51))
            chx += cs.get_width() + 8
        if av is not None:
            # C wiring: the link chip — the program's thread home (L-1..5)
            _uidc = f"v{av.vid}"
            _rtc = comms_route(_uidc, t)
            if _rtc is not None and _rtc.rate_bps >= 1e6:
                _ltxt, _lcol = (f"link {_fmt_bps(_rtc.rate_bps)}",
                                theme.COLORS["good"])
            elif _rtc is not None and _rtc.rate_bps > 0.0:
                _ltxt, _lcol = (f"link {_fmt_bps(_rtc.rate_bps)}",
                                theme.COLORS["warn"])
            elif comms_route(_uidc, t, floor=True) is not None:
                _ltxt, _lcol = "link FLOOR", theme.COLORS["warn"]
            else:
                _ltxt, _lcol = "link LOST", theme.COLORS["danger"]
            cs = theme.chip(_ltxt + "  (J)", _lcol)
            screen.blit(cs, (chx, 51))
            chx += cs.get_width() + 8
        theme.draw_text(screen, chx + 8, 54,
                        " | ".join(c.description[:30]
                                   for c in open_contracts[:2])
                        or "no open contracts",
                        color=theme.COLORS["text_dim"], font="small")
        # toasts are latched on REAL time so they survive 1,000,000x warp,
        # slide in, and fade out instead of teleporting
        if toast and (toast, toast_until) != toast_key:
            toast_key = (toast, toast_until)
            toast_real0 = ui_t
        t_age = ui_t - toast_real0
        rem = (3.0 - t_age) if t >= toast_until else 1.0
        if toast and rem > 0.0 and t_age < 30.0:
            up = toast.upper()
            kind = ("paid" if ("PAID" in up or "QUICKSAVE" in up or "ORBIT" in up)
                    else "alarm" if any(w in up for w in (
                        "WARNING", "FAILED", "INSUFFICIENT", "LOSS", "CANNOT",
                        "NEEDS", "EXCEEDS", "NO QUICK"))
                    else "science" if ("FIRST ENTRY" in up or "RESEARCHED" in up)
                    else "info")
            ts = theme.toast_surface(toast, kind)
            slide = min(1.0, t_age / 0.18)
            ts.set_alpha(int(255 * min(1.0, slide, max(0.0, rem / 0.35))))
            screen.blit(ts, (size[0] // 2 - ts.get_width() // 2,
                             64 + int(20 * slide)))
            ts.set_alpha(255)

        # crew panel (08): portraits + role + career-dose gauges (K = roster)
        cw = 216
        shown = list(crew.items())[:4]
        cpanel = theme.panel(cw, 46 + 34 * max(len(shown), 1), "CREW  (K)")
        cx0, cy0 = size[0] - cw - 10, size[1] - cpanel.get_height() - 42
        screen.blit(cpanel, (cx0, cy0))
        yy = cy0 + 32
        aboard_names = {n for v in vessels for n in v.crew}
        for cname, member in shown:
            screen.blit(theme.portrait(cname, 28), (cx0 + 8, yy))
            tag = f"{cname}  ({member.role[:3]}-{member.skill})"
            tcol = (theme.COLORS["accent"] if cname in aboard_names
                    else theme.COLORS["text"])
            theme.draw_text(screen, cx0 + 44, yy, tag, color=tcol,
                            font="small")
            frac = member.dose.career_fraction
            bcol = (theme.COLORS["good"] if frac < 0.5 else
                    theme.COLORS["warn"] if frac < 0.8 else
                    theme.COLORS["danger"])
            screen.blit(theme.bar(160, 7, frac, bcol), (cx0 + 44, yy + 17))
            yy += 34

        # NAV panel: orbit clocks, target intelligence, fleet rendezvous —
        # the questions the sim could always answer, finally on screen
        nav_lines: list[tuple[str, tuple]] = []
        if av is not None and av.landed_at is None:
            el_n = av.elements
            if el_n.alpha > 0:
                t_pe_n, t_ap_n = _next_apsis_times(el_n, t)
                nav_lines.append((
                    f"T {theme.fmt_duration(el_n.period)}   "
                    f"Pe in {theme.fmt_duration(t_pe_n - t)}   "
                    f"Ap in {theme.fmt_duration(t_ap_n - t)}",
                    theme.COLORS["text"]))
            if target_id is not None:
                tname = target_id.split(":")[1]
                enc = next((leg for leg in legs_now
                            if leg.frame_id == target_id), None)
                if enc is not None and enc.t_start > t:
                    pe_enc = (enc.elements.periapsis
                              - tree.body(target_id).radius)
                    nav_lines.append((
                        f"ENCOUNTER {tname} in "
                        f"{theme.fmt_duration(enc.t_start - t)} — Pe "
                        f"{pe_enc / 1e3:,.0f} km"
                        + ("  IMPACT" if pe_enc < 0 else ""),
                        theme.COLORS["danger"] if pe_enc < 0
                        else theme.COLORS["good"]))
                    # §1.6 corridor advisor for atmospheric arrivals
                    _ck = (target_id, av.vid, int(enc.t_start // 3600))
                    if corridor_cache["key"] != _ck:
                        _body_e = tree.body(target_id)
                        _beta_e = (av.vessel.total_mass_kg()
                                   / max(av.vessel.cd_a_m2, 0.5))
                        _rate_e = (_CAPSULE_HEAT_W_M2 if any(
                            db.parts[r.part_id]["type"] == "crew"
                            for r in av.vessel.rows)
                            else _BARE_HEAT_W_M2)
                        corridor_cache.update(
                            key=_ck,
                            lines=_corridor_advice(
                                target_id, _body_e.mu, _body_e.radius,
                                enc.elements, _beta_e, _rate_e))
                    for _cl, _cs in corridor_cache["lines"]:
                        nav_lines.append((_cl, theme.COLORS[
                            {"go": "good", "warn": "warn",
                             "danger": "danger"}[_cs]]))
                else:
                    if (ui_t - ca_cache["at"] > 0.5
                            or ca_cache["tgt"] != target_id):
                        d_ca, t_ca = closest_approach(av, target_id, t)
                        ca_cache.update(at=ui_t, tgt=target_id, d=d_ca,
                                        t=t_ca)
                    if ca_cache["d"] is not None and math.isfinite(
                            ca_cache["d"]):
                        nav_lines.append((
                            f"TGT {tname} — closest "
                            f"{ca_cache['d'] / 1e3:,.0f} km in "
                            f"{theme.fmt_duration(max(0.0, ca_cache['t'] - t))}",
                            theme.COLORS["warn"]))
            else:
                nav_lines.append(("right-click a body to TARGET it",
                                  theme.COLORS["text_dim"]))
            others = [o for o in vessels
                      if o is not av and o.frame_id == av.frame_id
                      and o.landed_at is None]
            if others:
                arx, ary, avx2, avy2 = av.state(t)
                best_o, best_rng, best_close = None, float("inf"), 0.0
                for o in others:
                    orx, ory, ovx, ovy = o.state(t)
                    rng_m = math.hypot(orx - arx, ory - ary)
                    if rng_m < best_rng:
                        rel_r = (orx - arx, ory - ary)
                        rel_v = (ovx - avx2, ovy - avy2)
                        best_close = (-(rel_r[0] * rel_v[0]
                                        + rel_r[1] * rel_v[1])
                                      / max(rng_m, 1.0))
                        best_o, best_rng = o, rng_m
                if best_o is not None:
                    in_env = best_rng < 100e3
                    nav_lines.append((
                        f"REL {best_o.name} — {best_rng / 1e3:,.1f} km  "
                        f"{'closing' if best_close > 0 else 'opening'} "
                        f"{abs(best_close):,.1f} m/s"
                        + ("   E docks" if in_env else ""),
                        theme.COLORS["good"] if in_env
                        else theme.COLORS["accent"]))
        if av is not None:
            # C wiring: the link home, with route + light-time truth
            _rtn = comms_route(f"v{av.vid}", t)
            if _rtn is None:
                _fln = comms_route(f"v{av.vid}", t, floor=True)
                nav_lines.append((
                    "LINK: P0 floor only — commands crawl, no science"
                    if _fln is not None else
                    "LINK LOST — no path to DSN (occlusion/conjunction)",
                    theme.COLORS["warn"] if _fln is not None
                    else theme.COLORS["danger"]))
            else:
                _rtt_txt = (f"{_rtn.rtt_s * 1e3:,.0f} ms"
                            if _rtn.rtt_s < 1.0
                            else theme.fmt_duration(_rtn.rtt_s))
                _hopn = max(0, len(_rtn.path) - 2)
                _vian = (f" via {comms_label(_rtn.path[1])}"
                         if _hopn >= 1 else " direct")
                nav_lines.append((
                    f"LINK {_fmt_bps(_rtn.rate_bps)} · RTT {_rtt_txt}"
                    f"{_vian}",
                    theme.COLORS["good"] if _rtn.rate_bps >= 1e6
                    else theme.COLORS["warn"]))
        if nav_lines:
            npan = theme.panel(354, 34 + 20 * len(nav_lines), "NAV")
            nx0, ny0 = size[0] - 364, 84
            screen.blit(npan, (nx0, ny0))
            for li, (txt2, col2) in enumerate(nav_lines):
                theme.draw_text(screen, nx0 + 12, ny0 + 30 + li * 20, txt2,
                                color=col2, font="small")

        screen.blit(theme.footer(
            size[0],
            "X/Z burn   B build   N node   P planner   O contracts   "
            "V ship   E dock   I aboard   G surface   F2 colony   "
            "R research   K crew   SPACE pause   ./, warp   F1 help   "
            "ESC menu"),
            (0, size[1] - theme.FOOTER_H))

        # one shared dimmer under any content overlay (kills HUD bleed-through)
        if (base_screen and bases) or research_open or crew_open or (
                surface_open and av is not None) or planner_open \
                or contracts_open:
            dimmer = pygame.Surface(size, pygame.SRCALPHA)
            dimmer.fill((4, 6, 10, 168))
            screen.blit(dimmer, (0, 0))

        if contracts_open:
            from aphelion.game.campaign import CONTRACTS as _SPECS
            from aphelion.game.campaign import YEAR as _YEAR
            from aphelion.game.campaign import act_unlocked as _au
            lpan = theme.panel(880, 584, "CONTRACT LEDGER")
            lx0, ly0 = size[0] // 2 - 440, size[1] // 2 - 292
            screen.blit(lpan, (lx0, ly0))
            lines3: list[tuple[str, tuple]] = []
            by_id = {c.contract_id: c for c in program.contracts}
            for act in (1, 2, 3, 4):
                roman = ("I", "II", "III", "IV")[act - 1]
                lines3.append((
                    f"ACT {roman}"
                    + ("" if _au(act, program)
                       else "   — locked: complete 60% of the act before"),
                    theme.COLORS["gold"]))
                for spec in (s for s in _SPECS if s.act == act):
                    c = by_id.get(spec.cid)
                    if c is None:
                        lines3.append((
                            f"   {spec.desc[:46]:48s}"
                            f"${spec.payout_m:>6,.0f}M   —",
                            theme.COLORS["text_dim"]))
                        continue
                    if c.completed_t is not None:
                        status, col3 = "PAID ✓", theme.COLORS["good"]
                    elif c.failed:
                        status = ("FAILED — renegotiation pending"
                                  if c.retries < 2 else "FAILED — final")
                        col3 = theme.COLORS["danger"]
                    else:
                        rem = c.deadline_s - t
                        status = f"due in {theme.fmt_duration(rem)}"
                        col3 = (theme.COLORS["warn"]
                                if rem < spec.years * _YEAR * 0.25
                                else theme.COLORS["text"])
                        if c.retries:
                            status += f"  (renegotiated x{c.retries})"
                    lines3.append((
                        f"   {c.description[:46]:48s}"
                        f"${c.payout / 1e6:>6,.0f}M   {status}", col3))
            max_rows = 24
            contracts_scroll = max(0, min(contracts_scroll,
                                          max(0, len(lines3) - max_rows)))
            ly = ly0 + 36
            for txt3, col3 in lines3[contracts_scroll:
                                     contracts_scroll + max_rows]:
                theme.draw_text(screen, lx0 + 18, ly, txt3, color=col3,
                                font="small")
                ly += 22
            theme.draw_text(
                screen, lx0 + 18, ly0 + 556,
                f"{act_progress(program)} toward the next act   ·   "
                "UP/DOWN scroll   O/ESC close",
                color=theme.COLORS["text_dim"], font="small")

        if net_overlay:
            # C wiring: the comms map (16 §3.1) — every node's Dijkstra
            # route home, rate-colored in the art bible's nav cyan
            _cc = comms_now(t)

            def _clip_seg(ax1, ay1, bx1, by1, m=2000.0):
                # Liang–Barsky to a sane box: pygame chokes on the huge
                # coords world_to_screen returns for far nodes when zoomed
                t0c, t1c = 0.0, 1.0
                dx1, dy1 = bx1 - ax1, by1 - ay1
                for p1, q1 in ((-dx1, ax1 + m), (dx1, size[0] + m - ax1),
                               (-dy1, ay1 + m), (dy1, size[1] + m - ay1)):
                    if p1 == 0.0:
                        if q1 < 0.0:
                            return None
                        continue
                    r1 = q1 / p1
                    if p1 < 0.0:
                        if r1 > t1c:
                            return None
                        t0c = max(t0c, r1)
                    else:
                        if r1 < t0c:
                            return None
                        t1c = min(t1c, r1)
                return (ax1 + t0c * dx1, ay1 + t0c * dy1,
                        ax1 + t1c * dx1, ay1 + t1c * dy1)

            _act_uid = f"v{av.vid}" if av is not None else None
            _seen_e: set = set()
            for _uid in _cc["pos"]:
                _rt0 = comms_route(_uid, t)
                if _rt0 is None:
                    continue
                _hot = _uid == _act_uid
                for _h in _rt0.hops:
                    _ek = (_h.tx_uid, _h.rx_uid)
                    if _ek in _seen_e and not _hot:
                        continue
                    _seen_e.add(_ek)
                    _pa = cam.world_to_screen(*_cc["pos"][_h.tx_uid][:2])
                    _pb = cam.world_to_screen(*_cc["pos"][_h.rx_uid][:2])
                    _seg = _clip_seg(_pa[0], _pa[1], _pb[0], _pb[1])
                    if _seg is None:
                        continue
                    _col = ((96, 205, 195) if _h.rate_bps >= 1e6 else
                            (70, 145, 150) if _h.rate_bps >= 1e3 else
                            (88, 96, 116))
                    if _hot:
                        pygame.draw.line(
                            screen, (140, 235, 225),
                            (_seg[0], _seg[1]), (_seg[2], _seg[3]), 2)
                    else:
                        pygame.draw.aaline(
                            screen, _col,
                            (_seg[0], _seg[1]), (_seg[2], _seg[3]))
            for _uid, (_nx, _ny, _) in _cc["pos"].items():
                _np = cam.world_to_screen(_nx, _ny)
                if not (-40 < _np[0] < size[0] + 40
                        and -40 < _np[1] < size[1] + 40):
                    continue
                _live = comms_route(_uid, t) is not None
                pygame.draw.circle(
                    screen, (130, 225, 215) if _live else (110, 80, 80),
                    (int(_np[0]), int(_np[1])), 4, 1)
                screen.blit(font.render(
                    comms_label(_uid), True,
                    (115, 175, 175) if _live else (150, 100, 100)),
                    (_np[0] + 7, _np[1] + 5))

        if planner_open:
            prows = planner_rows_for(av, t)
            # viewport: the destination list outgrew the screen (planets +
            # asteroids + comets) — scroll a window that follows the cursor
            n_vis = min(max(1, len(prows)), max(4, (size[1] - 330) // 26))
            ppan2 = theme.panel(760, 148 + 26 * n_vis, "TRANSFER PLANNER")
            ppx2, ppy2 = size[0] // 2 - 380, 110
            screen.blit(ppan2, (ppx2, ppy2))
            overlay_rects["planner"] = []
            if not prows:
                theme.draw_text(
                    screen, ppx2 + 18, ppy2 + 42,
                    "the planner quotes departures from a PARKING ORBIT "
                    "around a planet — get one first",
                    color=theme.COLORS["text_dim"], font="small")
            else:
                cur = planner_cursor % len(prows)
                first = max(0, min(cur - n_vis // 2, len(prows) - n_vis))
                theme.draw_text(
                    screen, ppx2 + 18, ppy2 + 34,
                    f"{'DESTINATION':14s}{'WINDOW IN':>12s}{'TRANSIT':>12s}"
                    f"{'DEPART dv':>12s}{'CAPTURE dv':>12s}",
                    color=theme.COLORS["gold"], font="small")
                if len(prows) > n_vis:
                    theme.draw_text(screen, ppx2 + 636, ppy2 + 34,
                                    f"{first + 1}-{first + n_vis} of "
                                    f"{len(prows)}",
                                    color=theme.COLORS["text_dim"],
                                    font="small")
                for vi, i in enumerate(range(first, first + n_vis)):
                    row = prows[i]
                    sel = i == cur
                    ry2 = ppy2 + 58 + vi * 26
                    if sel:
                        screen.blit(theme.row_glow(724, 24), (ppx2 + 14, ry2 - 3))
                    col2 = (theme.COLORS["good"] if row["affordable"]
                            else theme.COLORS["danger"])
                    theme.draw_text(
                        screen, ppx2 + 18, ry2,
                        f"{row['name']:14s}"
                        f"{theme.fmt_duration(row['wait']):>12s}"
                        f"{theme.fmt_duration(row['t_tr']):>12s}"
                        f"{row['dv_dep']:>10,.0f} m/s"
                        f"{row['dv_cap']:>10,.0f} m/s",
                        color=theme.COLORS["gold"] if sel else col2,
                        font="small")
                    overlay_rects["planner"].append(
                        (pygame.Rect(ppx2 + 14, ry2 - 3, 724, 26), i))
                _ry3 = ppy2 + 64 + n_vis * 26
                # Lambert refinement of the SELECTED row: the real
                # ephemerides beat the circular-Hohmann quote above
                _selrow = prows[cur]
                _ref = lambert_refined(av, _selrow, t)
                if _ref is not None:
                    _save = ((_selrow["dv_dep"] + _selrow["dv_cap"])
                             - (_ref["dv_dep"] + _ref["dv_cap"]))
                    _reftxt = (
                        f"LAMBERT {_selrow['name'].upper()}: depart in "
                        f"{theme.fmt_duration(max(0.0, _ref['t_dep'] - t))}"
                        f" · transit {theme.fmt_duration(_ref['tof'])} · "
                        f"inject {_ref['dv_dep']:,.0f} + capture "
                        f"{_ref['dv_cap']:,.0f} m/s")
                    if _save > 10.0:
                        _reftxt += f"   (saves {_save:,.0f} m/s)"
                    theme.draw_text(screen, ppx2 + 18, _ry3, _reftxt,
                                    color=theme.COLORS["accent"],
                                    font="small")
                theme.draw_text(
                    screen, ppx2 + 18, _ry3 + 26,
                    "ENTER places the node at the window + sets target   ·"
                    "   quotes assume your parking orbit   ·   P/ESC close",
                    color=theme.COLORS["text_dim"], font="small")

        if base_screen and bases:
            # THE COLONY, DRAWN: terrain, sky, module structures with live
            # status lights and residents — the spreadsheet retired
            from aphelion.game.basebuild import CATALOG, catalog_for_kind
            site_b = bases[base_idx % len(bases)]
            site_def = SITES[site_b.site_id]
            module_rates, rates, f_power = site_b.net.solve_rates()
            avail = catalog_for_kind(site_def["kind"])
            mods = site_b.net.modules
            daylight = site_b.daylight(t)
            overlay_rects["base"] = []

            scene_h = 444
            screen.fill((6, 8, 14))      # opaque: the map fully yields
            screen.blit(sky_strip(site_def["kind"], size[0], scene_h,
                                  daylight * site_def["solar"]), (0, 0))
            terr, ridge = terrain_strip(site_b.site_id, site_def["kind"],
                                        size[0], 300)
            screen.blit(terr, (0, scene_h - 300))
            state_cols = {"RUNNING": theme.COLORS["good"],
                          "FAILED": theme.COLORS["danger"],
                          "STARVED": theme.COLORS["warn"],
                          "BLOCKED": theme.COLORS["warn"],
                          "OFF": theme.COLORS["text_dim"]}
            mod_sel = module_cursor % max(1, len(mods))
            for mi, m in enumerate(mods):
                key = m.module_id.rsplit("_", 1)[0]
                spr = module_sprite(key)
                mx0 = 56 + mi * 102
                gy = (scene_h - 300
                      + ridge[min(mx0 + 44, size[0] - 1)])
                bob = (int(2.0 * math.sin(ui_t * 3.0 + mi))
                       if key == "drill_ice" and m.state == "RUNNING" else 0)
                my0 = gy - spr.get_height() + 10 + bob
                screen.blit(spr, (mx0, my0))
                col = state_cols.get(m.state, theme.COLORS["text"])
                pulse = (0.55 + 0.45 * math.sin(ui_t * 4.0 + mi)
                         if m.state != "OFF" else 0.25)
                pygame.draw.circle(screen, tuple(int(c * pulse) for c in col),
                                   (mx0 + 44, my0 - 8), 5)
                if key == "tank_farm":     # aggregate storage fill readout
                    tot = sum(b2.level for r2, b2 in
                              site_b.net.buffers.items() if r2 != "Battery")
                    cap = sum(b2.capacity for r2, b2 in
                              site_b.net.buffers.items() if r2 != "Battery")
                    screen.blit(theme.bar(64, 6, tot / max(cap, 1.0),
                                          theme.COLORS["accent"]),
                                (mx0 + 12, my0 + spr.get_height() - 4))
                if mi == mod_sel and mods:
                    pygame.draw.rect(screen, theme.COLORS["gold"],
                                     (mx0 - 4, my0 - 16, 96, spr.get_height()
                                      + 24), 1)
                overlay_rects["base"].append(
                    (pygame.Rect(mx0 - 4, my0 - 16, 96,
                                 spr.get_height() + 24), 30_000 + mi))
            # residents stroll between the structures
            for wi, wname in enumerate(site_b.crew[:6]):
                span = max(len(mods), 1) * 102
                wx = 70 + int((wi * 97 + ui_t * 11.0) % max(span, 120))
                wy = (scene_h - 300
                      + ridge[min(wx, size[0] - 1)] - 16)
                screen.blit(walker_sprite(wname, int(ui_t * 2.0) + wi),
                            (wx, wy))

            # header strip: identity line + status chips
            screen.blit(theme.panel(size[0], 54), (0, 0))
            emitted, capacity = thermal_balance_kw(site_b.net)
            alert_txt = site_b.alert(t)
            theme.draw_text(screen, 14, 6,
                            f"{site_b.name}  —  {site_def['name']}",
                            color=theme.COLORS["text"], font="ui")
            chx_b = 14
            base_chips = [
                (f"{'DAY' if daylight > 0.5 else 'NIGHT'} · sun "
                 f"x{site_def['solar'] * daylight:.2f}",
                 theme.COLORS["gold"] if daylight > 0.5
                 else theme.COLORS["accent"]),
                (f"power f={f_power:.2f}",
                 theme.COLORS["good"] if f_power >= 0.99
                 else theme.COLORS["warn"]),
                (f"heat {emitted:,.0f}/{capacity:,.0f} kW",
                 theme.COLORS["danger"] if emitted > capacity
                 else theme.COLORS["text_dim"]),
                (f"crew {len(site_b.crew)}/{site_b.beds()}",
                 theme.COLORS["text_dim"]),
                (f"$ {program.funds / 1e6:,.0f}M", theme.COLORS["gold"]),
            ]
            if len(bases) > 1:
                base_chips.append((f"base {base_idx + 1}/{len(bases)} (N)",
                                   theme.COLORS["text_dim"]))
            if alert_txt:
                base_chips.append((f"⚠ {alert_txt}", theme.COLORS["danger"]))
            for chip_txt, chip_col in base_chips:
                cs = theme.chip(chip_txt, chip_col)
                screen.blit(cs, (chx_b, 29))
                chx_b += cs.get_width() + 8

            # resources panel
            rp = theme.panel(396, 250, "RESOURCES")
            screen.blit(rp, (16, scene_h + 6))
            res_icons = {"Water": "water", "Oxygen": "oxygen",
                         "Hydrogen": "hydrogen", "Methane": "tank",
                         "CO2": "dot", "Battery": "power"}
            ry0 = scene_h + 40
            for res in ("Water", "Oxygen", "Hydrogen", "Methane", "CO2",
                        "Battery"):
                buf = site_b.net.buffers.get(res)
                if buf is None:
                    continue
                rate = rates.get(res, 0.0)
                frac = min(1.0, buf.level / max(buf.capacity, 1e-9))
                screen.blit(theme.icon(res_icons.get(res, "dot"), 14),
                            (30, ry0))
                theme.draw_text(screen, 50, ry0, f"{res:9s}",
                                color=theme.COLORS["text"], font="small")
                screen.blit(theme.bar(110, 9, frac, theme.COLORS["good"]),
                            (128, ry0 + 3))
                if res == "Battery":
                    line = (f"{buf.level:6.0f} kWh "
                            f"{rate * 3_600.0:+5.1f} kW")
                else:
                    line = (f"{buf.level / 1e3:6.1f} t "
                            f"{rate * 86_400.0 / 1e3:+6.2f} t/d")
                # time-to-full/empty: the ledger knows, so say it
                eta = ""
                if rate > 1e-9 and frac < 1.0:
                    eta = f" full {theme.fmt_duration((buf.capacity - buf.level) / rate)}"
                elif rate < -1e-9 and buf.level > 0.0:
                    eta_s = buf.level / -rate
                    eta = f" empty {theme.fmt_duration(eta_s)}"
                theme.draw_text(
                    screen, 246, ry0, line + eta,
                    color=(theme.COLORS["danger"]
                           if "empty" in eta and eta_s < 86_400.0
                           else theme.COLORS["text"]), font="small")
                ry0 += 24
            theme.draw_text(screen, 30, ry0 + 2,
                            f"vent: h2 relief −0.001 kg/s   ·   repairs "
                            f"pending {len(site_b.pending_repairs)}",
                            color=theme.COLORS["text_dim"], font="small")

            # module inspect / event log panel
            mp = theme.panel(424, 250,
                             "EVENT LOG (L)" if base_log_open
                             else "MODULE — ENTER toggles")
            screen.blit(mp, (420, scene_h + 6))
            if base_log_open:
                ly = scene_h + 38
                for ev in site_b.events[-9:]:
                    theme.draw_text(
                        screen, 434, ly,
                        f"{ev.t / SECONDS_PER_DAY:9.2f} d  {ev.kind:14s} "
                        f"{ev.subject}",
                        color=theme.COLORS["text"], font="small")
                    ly += 22
                if not site_b.events:
                    theme.draw_text(screen, 434, ly, "no events yet",
                                    color=theme.COLORS["text_dim"],
                                    font="small")
            elif mods:
                m = mods[mod_sel]
                key = m.module_id.rsplit("_", 1)[0]
                spec = CATALOG.get(key, {})
                col = state_cols.get(m.state, theme.COLORS["text"])
                iy = scene_h + 38
                theme.draw_text(screen, 434, iy,
                                f"{spec.get('name', key)}  [{m.state}]",
                                color=col, font="body")
                iy += 24
                lines2 = []
                if m.rate_kgps > 0.0:
                    act = module_rates.get(m.module_id, 0.0)
                    pri = (spec.get("primary") or ("?", 0))[0]
                    lines2.append(f"rate {act:,.3f} / {m.rate_kgps:,.3f} "
                                  f"kg/s {pri}  (labor x{m.f_labor:.2f})")
                if spec.get("inputs") or spec.get("outputs"):
                    rec_in = " + ".join(f"{v:g} {k2}" for k2, v in
                                        spec.get("inputs", {}).items())
                    rec_out = " + ".join(f"{v:g} {k2}" for k2, v in
                                         spec.get("outputs", {}).items())
                    lines2.append(f"{rec_in or 'nothing'} → "
                                  f"{rec_out or 'nothing'}")
                pw = m.power_kw
                lines2.append(f"power {'+' if pw < 0 else '−'}"
                              f"{abs(pw):,.0f} kW"
                              + (f"   heat {m.heat_kw:+,.0f} kW"
                                 if m.heat_kw else ""))
                if m.mtbf_s:
                    lines2.append(f"MTBF {m.mtbf_s / 86_400.0:,.0f} d")
                    if site_b.engineer_skill(crew) > 0 and m.failure_t:
                        lines2.append(
                            f"engineer's forecast: next fault in "
                            f"{theme.fmt_duration(max(0.0, m.failure_t - t))}")
                if m.module_id in site_b.cond:
                    c_w = site_b.cond[m.module_id]
                    lines2.append(
                        f"condition {c_w:.2f}"
                        + ("  — DEGRADED (C/0.5 rate)" if c_w < 0.5
                           else "  (PM below 0.55)"))
                if m.state == "FAILED":
                    eta_rep = min((r[0] for r in site_b.pending_repairs
                                   if r[1] == m.module_id),
                                  default=None)
                    if eta_rep is not None:
                        lines2.append(f"repair ETA "
                                      f"{theme.fmt_duration(max(0.0, eta_rep - t))}")
                if m.state == "STARVED":
                    starving = [k2 for k2 in spec.get("inputs", {})
                                if site_b.net.buffers.get(k2)
                                and site_b.net.buffers[k2].level <= 0.0]
                    if starving:
                        lines2.append("starved of: " + ", ".join(starving))
                for line2 in lines2:
                    theme.draw_text(screen, 434, iy, line2,
                                    color=theme.COLORS["text"], font="small")
                    iy += 21

            # construct panel
            cpanel = theme.panel(420, 250, "CONSTRUCT")
            screen.blit(cpanel, (848, scene_h + 6))
            cx, cy = 862, scene_h + 38
            rows_fit_b = 7
            top_b = max(0, min(base_cursor - rows_fit_b // 2,
                               len(avail) - rows_fit_b))
            for i, key in enumerate(avail):
                if i < top_b or i >= top_b + rows_fit_b:
                    continue
                spec = CATALOG[key]
                sel = (i == base_cursor % len(avail)
                       and base_focus == "construct")
                locked = (spec["tech"] is not None
                          and spec["tech"] not in research.unlocked)
                color = (theme.COLORS["text_dim"] if locked
                         else theme.COLORS["gold"] if sel
                         else theme.COLORS["text"])
                pw = spec["power_kw"]
                pw_txt = (f"+{-pw:,.0f}kW" if pw < 0 else f"{pw:,.0f}kW")
                yy2 = cy + (i - top_b) * 24
                if sel:
                    screen.blit(theme.row_glow(396, 22), (858, yy2 - 3))
                theme.draw_text(
                    screen, cx, yy2,
                    f"{spec['name'][:24]:25s}${spec['price_m']:>3,.0f}M "
                    f"{pw_txt}" + ("  LOCKED" if locked else ""),
                    color=color, font="small")
                overlay_rects["base"].append(
                    (pygame.Rect(858, yy2 - 3, 396, 23), i))
            sel_spec = CATALOG[avail[base_cursor % len(avail)]]
            need_line = (" + ".join(f"{v:g} {k2}" for k2, v in
                                    sel_spec.get("inputs", {}).items())
                         or "no feedstock")
            theme.draw_text(screen, cx, cy + rows_fit_b * 24 + 6,
                            f"needs: {need_line}",
                            color=theme.COLORS["text_dim"], font="small")
            screen.blit(theme.footer(
                size[0],
                "◄► select module   ENTER toggle/build   TAB focus   "
                "UP/DOWN catalog   L log   N next base   F2/ESC close"),
                (0, size[1] - theme.FOOTER_H))

        if builder_open:
            dimmer = pygame.Surface(size, pygame.SRCALPHA)
            dimmer.fill((6, 9, 16, 242))
            screen.blit(dimmer, (0, 0))
            cat_focus = builder.focus == "catalog" and not builder.assign_open
            screen.blit(theme.panel(560, size[1] - 80,
                                    "PART CATALOG" + (" ◄" if cat_focus else "")),
                        (16, 16))
            screen.blit(theme.panel(360, size[1] - 80,
                                    "STACK" + ("" if cat_focus else " ◄")),
                        (592, 16))
            screen.blit(theme.panel(296, size[1] - 80, "VESSEL"), (968, 16))
            overlay_rects["builder"] = []

            # category filter tabs (LEFT/RIGHT or click)
            tab_x = 28
            for ci, cat in enumerate(builder.CATS):
                label = cat.upper() if cat != "ALL" else "ALL"
                col = (theme.COLORS["gold"] if ci == builder.filter_idx
                       else theme.COLORS["text_dim"])
                cs = theme.chip(label, col)
                screen.blit(cs, (tab_x, 44))
                overlay_rects["builder"].append(
                    (pygame.Rect(tab_x, 44, cs.get_width(), 20),
                     20_000 + ci))
                tab_x += cs.get_width() + 8

            detail_h = 152
            list_y0 = 74
            row_h = 27
            rows_fit = (size[1] - 80 - detail_h - 60 - (list_y0 - 16)) // row_h
            top = max(0, min(builder.cursor - rows_fit // 2,
                             len(builder.entries) - rows_fit))
            for i, (kind, payload) in enumerate(builder.entries):
                if i < top or i >= top + rows_fit:
                    continue
                ry = list_y0 + (i - top) * row_h
                if kind == "header":
                    theme.draw_text(screen, 32, ry + 6, payload,
                                    color=theme.COLORS["gold"], font="small")
                    pygame.draw.line(screen, theme.COLORS["panel_edge"],
                                     (140, ry + 13), (552, ry + 13))
                    continue
                pid = payload
                p = db.parts[pid]
                locked = builder.locked(pid)
                overlay_rects["builder"].append(
                    (pygame.Rect(26, ry - 1, 540, row_h - 1), i))
                if i == builder.cursor and cat_focus:
                    screen.blit(theme.row_glow(540, row_h - 2), (26, ry - 1))
                screen.blit(part_thumb(p, pid, 22), (32, ry + 1))
                tcol = (theme.COLORS["text_dim"] if locked
                        else theme.COLORS["text"])
                theme.draw_text(screen, 62, ry + 5, p["name"][:38],
                                color=tcol, font="small")
                theme.draw_text(screen, 408, ry + 5,
                                f"${builder.part_cost(pid)/1e6:6,.1f}M",
                                color=(theme.COLORS["text_dim"] if locked
                                       else theme.COLORS["gold"]),
                                font="small")
                screen.blit(theme.chip(p["tier"], theme.COLORS["accent"]),
                            (492, ry + 2))
                if locked:
                    screen.blit(theme.icon("lock", 14), (538, ry + 4))

            # part detail card (the stats that make choices informed)
            sel_pid = builder.selected_pid
            dy0 = size[1] - 80 - detail_h
            pygame.draw.line(screen, theme.COLORS["panel_edge"],
                             (24, dy0), (560, dy0))
            if sel_pid is not None:
                p = db.parts[sel_pid]
                screen.blit(part_thumb(p, sel_pid, 56), (32, dy0 + 12))
                theme.draw_text(screen, 100, dy0 + 10, p["name"],
                                color=theme.COLORS["accent"], font="body")
                lines = [f"mass {p['mass_t']:.2f} t    "
                         f"unit ${builder.part_cost(sel_pid)/1e6:,.1f}M"]
                if "engine" in p:
                    eng = p["engine"]
                    fam = ", ".join(eng["propellant"])
                    lines.append(
                        f"thrust {eng['thrust_kN']:,.0f} kN   Isp "
                        f"{eng['isp_s']:,.0f}s vac"
                        + (f" / {eng['isp_sl_s']:,.0f}s asl"
                           if eng.get("isp_sl_s") else ""))
                    lines.append(f"burns {fam}")
                elif "tank" in p:
                    tank = p["tank"]
                    mix = " + ".join(f"{frac:.0%} {res}"
                                     for res, frac in tank["mixture"].items())
                    lines.append(f"capacity {tank['capacity_t']:,.1f} t")
                    lines.append(f"holds {mix}")
                elif "crew" in p:
                    cc = p["crew"]
                    lines.append(f"seats {cc.get('capacity', 0)}   life "
                                 f"support {cc.get('endurance_days', 0):,.0f}"
                                 f" crew-days")
                if builder.locked(sel_pid):
                    need = next((nd["name"] for nd in db.tech.values()
                                 if sel_pid in nd.get("unlocks", [])),
                                "unknown research")
                    lines.append(f"LOCKED — requires: {need}")
                for li, line in enumerate(lines):
                    theme.draw_text(
                        screen, 100, dy0 + 34 + li * 19, line,
                        color=(theme.COLORS["warn"]
                               if line.startswith("LOCKED")
                               else theme.COLORS["text"]), font="small")

            # the stack: stage headers + cursor-editable part rows
            sx0 = 608
            yy = 48
            vessel = builder.build_vessel()
            stats = vessel.stage_stats() if vessel else []
            flat_i = 0
            for si, stage in enumerate(builder.stack):
                stat = stats[si] if si < len(stats) else None
                if stat and si == 0:
                    line = (f"S{si + 1}  dv {stat['dv_vac']:,.0f}"
                            f" ({stat['dv_sl']:,.0f} asl)  TWR "
                            f"{stat['twr_sl']:.2f}  {stat['burn_s']:,.0f}s")
                elif stat:
                    line = (f"S{si + 1}  dv {stat['dv_vac']:,.0f} m/s  TWR "
                            f"{stat['twr']:.2f}  burn {stat['burn_s']:,.0f}s")
                else:
                    line = f"S{si + 1}  (empty)"
                theme.draw_text(screen, sx0, yy, line,
                                color=theme.COLORS["accent"], font="small")
                yy += 20
                for pi, pid in enumerate(stage):
                    p = db.parts[pid]
                    sel_row = (not cat_focus
                               and flat_i == builder.stack_cursor)
                    overlay_rects["builder"].append(
                        (pygame.Rect(sx0 - 4, yy - 2, 336, 21),
                         10_000 + flat_i))
                    if sel_row:
                        screen.blit(theme.row_glow(336, 20), (sx0 - 4, yy - 2))
                    screen.blit(part_thumb(p, pid, 16), (sx0 + 4, yy))
                    theme.draw_text(screen, sx0 + 26, yy + 2,
                                    p["name"][:32],
                                    color=theme.COLORS["text"], font="small")
                    yy += 21
                    flat_i += 1
                yy += 7
            if vessel:
                total_dv = sum(s["dv_vac"] for s in stats)
                cost = builder.price(vessel)
                h_m, d_m = vessel_metrics(db, builder.stack)
                for ci, (txt, col) in enumerate((
                        (f"dv {total_dv:,.0f} m/s", theme.COLORS["good"]),
                        (f"{vessel.total_mass_kg()/1e3:,.1f} t   "
                         f"drag {vessel.cd_a_m2:.1f} m²",
                         theme.COLORS["accent"]),
                        (f"${cost/1e6:,.0f}M of ${program.funds/1e6:,.0f}M",
                         theme.COLORS["gold"] if cost <= program.funds
                         else theme.COLORS["danger"]))):
                    screen.blit(theme.chip(txt, col), (sx0, size[1] - 138 + ci * 26))
                # the rocket, as large as the bay allows (crisp nearest)
                vspr = vessel_sprite(db, builder.stack)
                if vspr.get_width() > 4:
                    k = min(2.5, (size[1] - 210) / vspr.get_height(),
                            252 / vspr.get_width())
                    if k > 1.05:
                        vspr = pygame.transform.scale_by(vspr, int(k * 4) / 4)
                vx = 968 + (296 - vspr.get_width()) // 2
                vy = 48 + max(0, (size[1] - 190 - vspr.get_height()) // 2)
                screen.blit(vspr, (vx, vy))
                theme.draw_text(screen, 984, size[1] - 116,
                                f"{h_m:,.1f} m tall · {d_m:,.1f} m wide",
                                color=theme.COLORS["text_dim"], font="small")
                cap = builder.crew_capacity()
                if cap:
                    theme.draw_text(screen, 984, size[1] - 96,
                                    f"seats {cap}"
                                    + (f" — crew: {len(builder.crew_pick)}"
                                       f" assigned" if builder.crew_pick
                                       else ""),
                                    color=theme.COLORS["accent"],
                                    font="small")
            theme.draw_text(screen, 24, size[1] - 52, builder.message,
                            color=theme.COLORS["accent"])
            screen.blit(theme.footer(
                size[0],
                "TAB stack   ◄► filter   ENTER add   BKSP del   "
                "[/] reorder   S stage   ⇧S split   1-6 blueprints   "
                "L launch   ESC close"), (0, size[1] - theme.FOOTER_H))

            # crew assignment (L with seats aboard): pick who flies
            if builder.assign_open:
                ground = sorted(n for n in crew
                                if n not in {x for v in vessels
                                             for x in v.crew})
                cap = builder.crew_capacity()
                apan = theme.panel(520, 110 + 34 * max(1, len(ground)),
                                   f"CREW ASSIGNMENT — {cap} SEAT"
                                   + ("S" if cap != 1 else ""))
                apx, apy = size[0] // 2 - 260, 120
                screen.blit(apan, (apx, apy))
                overlay_rects["builder"] = []
                ayy = apy + 38
                for i, name in enumerate(ground):
                    member = crew[name]
                    sel = i == builder.assign_cursor % max(1, len(ground))
                    picked = name in builder.crew_pick
                    if sel:
                        screen.blit(theme.row_glow(488, 30), (apx + 16, ayy - 3))
                    screen.blit(theme.portrait(name, 26), (apx + 22, ayy - 1))
                    box = "[x]" if picked else "[ ]"
                    theme.draw_text(
                        screen, apx + 58, ayy + 4,
                        f"{box} {name:18s} {member.role:9s} "
                        f"skill {member.skill}  dose "
                        f"{member.dose.career_fraction:4.0%}",
                        color=(theme.COLORS["good"] if picked
                               else theme.COLORS["gold"] if sel
                               else theme.COLORS["text"]), font="small")
                    overlay_rects["builder"].append(
                        (pygame.Rect(apx + 16, ayy - 3, 488, 32), i))
                    ayy += 34
                theme.draw_text(
                    screen, apx + 16, ayy + 8,
                    "ENTER/click toggle   L launch   ESC back",
                    color=theme.COLORS["text_dim"], font="small")

        if surface_open and av is not None:
            opts = _surface_options(av, bases, db, explore["investigated"],
                                    ground_vehicles)
            max_rows = 14                       # 18-sector worlds scroll
            n_rows = max(min(len(opts), max_rows), 1)
            spanel = theme.panel(640, 96 + 30 * n_rows, "SURFACE OPERATIONS")
            spx, spy = size[0] // 2 - 320, 110
            screen.blit(spanel, (spx, spy))
            if not opts:
                theme.draw_text(screen, spx + 16, spy + 40,
                                f"no landable surface at "
                                f"{av.frame_id.split(':')[1]}",
                                color=theme.COLORS["text_dim"])
            overlay_rects["surface"] = []
            cur = surface_cursor % len(opts) if opts else 0
            first = 0
            if len(opts) > max_rows:
                first = max(0, min(cur - max_rows // 2,
                                   len(opts) - max_rows))
            for row, (action, label) in enumerate(
                    opts[first:first + max_rows]):
                i = first + row
                sel = i == cur
                color = theme.COLORS["gold"] if sel else theme.COLORS["text"]
                if sel:
                    screen.blit(theme.row_glow(608, 26),
                                (spx + 12, spy + 34 + row * 30))
                theme.draw_text(screen, spx + 16, spy + 38 + row * 30,
                                ("> " if sel else "  ") + label[:78],
                                color=color, font="small")
                overlay_rects["surface"].append(
                    (pygame.Rect(spx + 12, spy + 34 + row * 30, 608, 28), i))
            if first > 0:
                theme.draw_text(screen, spx + 300, spy + 26, "▲ more",
                                color=theme.COLORS["text_dim"], font="small")
            if first + max_rows < len(opts):
                theme.draw_text(screen, spx + 300, spy + 36 + max_rows * 30,
                                "▼ more", color=theme.COLORS["text_dim"],
                                font="small")
            if opts:
                action = opts[cur][0]
                blurb = ""
                if action[0] == "land":
                    blurb = SITES[action[1]]["blurb"]
                elif av.landed_at:
                    blurb = SITES[av.landed_at]["blurb"]
                theme.draw_text(screen, spx + 16,
                                spy + 96 + 30 * (n_rows - 1), blurb,
                                color=theme.COLORS["accent"], font="small")

        if station_open and vessels:
            # ---- STATION OPS (06 §3): spin, fees, the depot economy ----
            av0 = vessels[active_idx % len(vessels)]
            rpm0 = getattr(av0, "spin_rpm", 0.0)
            r0 = getattr(av0, "spin_r_m", 25.0)
            cf = spin_sim.comfort(rpm0, r0)
            syy = 160
            m_kg = av0.vessel.total_mass_kg()
            i_spin = spin_sim.moment_of_inertia([(m_kg, r0)])
            quote = spin_sim.spinup_prop_kg(i_spin, max(rpm0, 1.0), r0,
                                            300.0)
            try:
                _bb = tree.body(av0.frame_id)
                _sx, _sy2, _, _ = av0.state(t)
                alt_km = (math.hypot(_sx, _sy2) - _bb.radius) / 1e3
            except Exception:
                alt_km = 400.0
            fee = keeping_sim.stationkeeping_ms_yr(av0.frame_id, alt_km)
            off_t = av0.docked_mass_t()
            bal_st = spin_sim.balance(off_t, r0)
            # the orbital yard (05 §3.1) rides the same panel
            from aphelion.sim.industry.yard import (has_dockyard,
                                                    plan_build)
            yard_rows = []
            if has_dockyard(av0.vessel):
                cargo_txt = "  ".join(
                    f"{r.replace('Parts', '')} {kg / 1e3:,.1f}t"
                    for r, kg in sorted(av0.cargo.items())) or "empty bays"
                yard_rows.append((f"YARD — stores: {cargo_txt}",
                                  theme.COLORS["gold"]))
                job_st = av0.yard_job
                if job_st:
                    left_d = max(0.0, (job_st["done_t"] - t) / 86_400.0)
                    frac_j = 1.0 - left_d / max(job_st["days"], 1e-9)
                    yard_rows.append(
                        (f"building {job_st['name']}: "
                         f"{frac_j:5.0%} — {left_d:,.1f} d to "
                         f"commissioning", theme.COLORS["accent"]))
                elif yard_designs:
                    a3_q = ("core:tech_in09_supervised_autonomy"
                            in research.unlocked)
                    for di, d_q in enumerate(yard_designs[:4]):
                        p_q = plan_build(d_q["dry_t"], d_q["n_parts"],
                                         a3=a3_q,
                                         n_built_before=d_q.get("built", 0))
                        bill_q = "  ".join(
                            f"{kg / 1e3:,.1f}t {r.replace('Parts', '')}"
                            for r, kg in p_q.bill_kg.items())
                        yard_rows.append(
                            (f"[{di + 1}] {d_q['name']}  "
                             f"{d_q['dry_t']:,.0f} t dry — "
                             f"{p_q.days:,.0f} d, {bill_q}",
                             theme.COLORS["text"]))
                else:
                    yard_rows.append(
                        ("no blueprints — press Y over a clean design "
                         "in the drydock", theme.COLORS["text_dim"]))
            rows_st = [
                (f"{av0.name} — spin section r {r0:.0f} m   "
                 f"[ ] adjusts radius", theme.COLORS["text"]),
                (f"spin {rpm0:.1f} rpm (+/− adjusts)   a_spin "
                 f"{cf['a_ms2']:.2f} m/s²   v_rim "
                 f"{spin_sim.v_rim(rpm0, r0):.1f} m/s",
                 theme.COLORS["accent"]),
                (("E9 — CREWED SPIN CAPPED AT 6 RPM" if rpm0 >= 6.0
                  and av0.crew else
                  f"comfort ×{cf['productivity']:.2f}   adapt "
                  f"{cf['adapt_days']:.0f} d   deconditioning: "
                  f"{cf['decon_regime']}"),
                 theme.COLORS["warn"] if cf["productivity"] < 1.0
                 else theme.COLORS["text_dim"]),
                (f"spin-up quote ~{quote:,.0f} kg storables at the rim "
                 f"(I = {i_spin:.2e} kg·m²)", theme.COLORS["text_dim"]),
                ((f"W6 balance {bal_st.upper()} — {off_t:,.0f} t docked "
                  f"off-axis" if av0.dock_joints else
                  "W6 balance OK — nothing docked off-axis"),
                 theme.COLORS["danger"] if bal_st == "despin"
                 else theme.COLORS["warn"] if bal_st == "wobble"
                 else theme.COLORS["text_dim"]),
                (f"station-keeping {fee:.0f} m/s/yr at "
                 f"{alt_km:,.0f} km (auto-RCS)",
                 theme.COLORS["text_dim"]),
                (f"MMOD P_pen {keeping_sim.mmod_p_pen(1e-4, 40.0, 365.25):.2%}/yr"
                 f" bare hull — Whipple panels cut it 10–50×",
                 theme.COLORS["text_dim"]),
                ("crew aboard feel a_spin as gravity: conditioning "
                 "and morale follow", theme.COLORS["text_dim"]),
            ] + yard_rows
            screen.blit(theme.panel(680, 56 + 26 * len(rows_st),
                                    "STATION OPS"),
                        (size[0] // 2 - 340, 120))
            for txt_st, col_st in rows_st:
                theme.draw_text(screen, size[0] // 2 - 322, syy, txt_st,
                                color=col_st, font="small")
                syy += 26

        if crew_open:
            from aphelion.game.crew import ROLES as _ROLES
            cands = candidates(crew)
            roster = list(crew.items())
            ph = 154 + 30 * (len(roster) + len(cands))
            kp = theme.panel(780, ph, "CREW ROSTER & HIRING")
            kx, ky = size[0] // 2 - 390, 100
            screen.blit(kp, (kx, ky))
            yy = ky + 36
            theme.draw_text(
                screen, kx + 14, yy,
                f"ROSTER — ENTER trains primary (+1, "
                f"${CrewMember.TRAIN_COST/1e6:,.0f}M, "
                f"{CrewMember.TRAIN_DAYS:.0f} d on Earth)"
                + ("  ◄" if crew_focus == "roster" else ""),
                color=theme.COLORS["gold"], font="small")
            theme.draw_text(
                screen, kx + 388, yy, "P E S M A   morale  cond  dose",
                color=theme.COLORS["text_dim"], font="small")
            yy += 24
            aboard_names = {n for v in vessels for n in v.crew}
            resident_names = {n for b in bases for n in b.crew}
            overlay_rects["crew"] = []
            for ri, (cname, member) in enumerate(roster):
                sel_r = (crew_focus == "roster"
                         and ri == roster_cursor % max(1, len(roster)))
                if sel_r:
                    screen.blit(theme.row_glow(748, 26), (kx + 10, yy - 4))
                screen.blit(theme.portrait(cname, 24), (kx + 14, yy - 2))
                where = next((v.name for v in vessels if cname in v.crew),
                             None)
                if where is None:
                    where = next((b.name for b in bases
                                  if cname in b.crew), "Earth")
                if not member.available(t):
                    where = (f"TRAIN "
                             f"{theme.fmt_duration(member.busy_until - t)}")
                if member.conditions:
                    where = ("⚕ " + member.conditions[0]["kind"]
                             .replace("_", " "))
                name_col = (theme.COLORS["danger"] if member.bedridden
                            else theme.COLORS["warn"]
                            if member.conditions or member.crisis
                            else theme.COLORS["accent"]
                            if cname in aboard_names
                            or cname in resident_names
                            else theme.COLORS["text"])
                theme.draw_text(screen, kx + 48, yy,
                                f"{cname:17.17s} {member.role:10.10s}",
                                color=name_col, font="small")
                tracks = " ".join(
                    str(member.skills.get(s, 0)) for s in _ROLES)
                theme.draw_text(screen, kx + 388, yy, tracks,
                                color=theme.COLORS["text"], font="small")
                bx0 = kx + 488
                for frac_b, col_b in (
                        (member.morale / 100.0,
                         theme.COLORS["danger"] if member.crisis
                         else theme.COLORS["accent"]),
                        (member.cond / 100.0,
                         theme.COLORS["danger"] if member.cond < 40.0
                         else theme.COLORS["accent"]),
                        (min(1.0, member.dose.career_fraction),
                         theme.COLORS["danger"]
                         if member.dose.caution
                         else theme.COLORS["text_dim"])):
                    screen.blit(theme.bar(44, 9,
                                          max(0.0, min(1.0, frac_b)),
                                          col_b), (bx0, yy + 3))
                    bx0 += 56
                theme.draw_text(screen, bx0 + 4, yy, f"{where:13.13s}",
                                color=theme.COLORS["text_dim"],
                                font="small")
                overlay_rects["crew"].append(
                    (pygame.Rect(kx + 10, yy - 4, 748, 28), 40_000 + ri))
                yy += 30
            yy += 8
            theme.draw_text(
                screen, kx + 14, yy,
                "CANDIDATES — ENTER hires (boards next launch)"
                + ("  ◄" if crew_focus == "cands" else ""),
                color=theme.COLORS["gold"], font="small")
            yy += 26
            for i, cand in enumerate(cands):
                sel = (crew_focus == "cands"
                       and i == crew_cursor % len(cands) if cands else False)
                if sel:
                    screen.blit(theme.row_glow(748, 26), (kx + 10, yy - 4))
                tracks_c = " ".join(
                    str(cand.skills.get(s, 0)) for s in _ROLES)
                theme.draw_text(
                    screen, kx + 14, yy,
                    f"{'>' if sel else ' '} {cand.name:18.18s} "
                    f"{cand.role:10.10s}  "
                    f"${cand.hire_cost/1e6:,.0f}M",
                    color=(theme.COLORS["gold"] if sel
                           else theme.COLORS["text"]), font="small")
                theme.draw_text(screen, kx + 388, yy, tracks_c,
                                color=theme.COLORS["text_dim"],
                                font="small")
                overlay_rects["crew"].append(
                    (pygame.Rect(kx + 10, yy - 4, 748, 28), i))
                yy += 30
            theme.draw_text(
                screen, kx + 14, yy + 4,
                "P pilot · E engineer · S scientist · M medic · A agronomist"
                "  —  morale low = errors; conditioning < 40 blocks EVA",
                color=theme.COLORS["text_dim"], font="small")

        if research_open:
            # R&D board (11): 10 branch columns of tier-sorted cards with
            # fog-of-research ??? silhouettes; TAB cycles tree/data/codex
            tech_ids = _tech_order(db, research)
            all_ids = _tech_order(db)
            pw, ph = 1216, 576
            px0, py0 = size[0] // 2 - pw // 2, 72
            screen.blit(theme.panel(pw, ph, "RESEARCH"), (px0, py0))
            screen.blit(theme.chip(f"science {research.science:,.0f}",
                                   theme.COLORS["accent"]),
                        (px0 + pw - 340, py0 + 3))
            screen.blit(theme.chip(
                f"tech {len(research.unlocked)}/{len(all_ids)}",
                theme.COLORS["gold"]), (px0 + pw - 168, py0 + 3))
            overlay_rects["research"] = []
            if research_view == "ed":
                # ED dashboard: 22 family bars, maturity and saturation
                theme.draw_text(
                    screen, px0 + 24, py0 + 38,
                    "ENGINEERING DATA — per-family flight experience; "
                    "thresholds CHECK it, nothing spends it",
                    color=theme.COLORS["text_dim"], font="ui_small")
                from aphelion.sim.research import FAMILIES
                half = (len(FAMILIES) + 1) // 2
                for i, fam in enumerate(FAMILIES):
                    cx = px0 + 24 + (0 if i < half else pw // 2)
                    cy = py0 + 66 + (i % half) * 42
                    d = research.d_f(fam)
                    cap = research.ed_cap(db, fam)
                    bdg = badge(d)
                    theme.draw_text(screen, cx, cy, fam,
                                    color=theme.COLORS["text"],
                                    font="ui_small")
                    tag = f"×{maturity(d, fam):.2f} failure"
                    if bdg:
                        tag += f"  ·  {bdg}"
                    if d >= cap - 1e-9 and d > 0:
                        tag += "  ·  DATA SATURATED"
                    theme.draw_text(screen, cx + 226, cy, tag,
                                    color=(theme.COLORS["good"] if bdg
                                           else theme.COLORS["text_dim"]),
                                    font="small")
                    screen.blit(theme.bar(296, 9,
                                          min(1.0, d / max(1.0, cap)),
                                          theme.COLORS["accent"]),
                                (cx, cy + 18))
                    theme.draw_text(screen, cx + 306, cy + 14,
                                    f"{d:,.0f} / {cap:,.0f}",
                                    color=theme.COLORS["text_dim"],
                                    font="small")
                theme.draw_text(screen, px0 + 24, py0 + ph - 28,
                                "TAB codex   ·   R close",
                                color=theme.COLORS["text_dim"], font="small")
            elif research_view == "codex":
                theme.draw_text(
                    screen, px0 + 24, py0 + 38,
                    "DISCOVERY CODEX — location-gated firsts; each reveals "
                    "and discounts technology",
                    color=theme.COLORS["text_dim"], font="ui_small")
                dscs = db.by_type("discoveries")
                for i, did in enumerate(sorted(dscs)):
                    dd = dscs[did]
                    cy = py0 + 66 + i * 26
                    got = did in research.discoveries
                    if got:
                        screen.blit(theme.icon("check", 13),
                                    (px0 + 24, cy + 1))
                    theme.draw_text(screen, px0 + 44, cy, dd["name"],
                                    color=(theme.COLORS["good"] if got
                                           else theme.COLORS["text"]),
                                    font="ui_small")
                    info = f"+{dd['sci']:,.0f} sci" + \
                        ("  · staged" if dd.get("staged") else "")
                    theme.draw_text(screen, px0 + 318, cy, info,
                                    color=(theme.COLORS["gold"] if got
                                           else theme.COLORS["text_dim"]),
                                    font="small")
                    req = "ACQUIRED" if got else dd["requirement"]
                    theme.draw_text(screen, px0 + 452, cy, req[:96],
                                    color=theme.COLORS["text_dim"],
                                    font="small")
                theme.draw_text(screen, px0 + 24, py0 + ph - 28,
                                "TAB tree   ·   R close",
                                color=theme.COLORS["text_dim"], font="small")
            else:
                col_w = (pw - 36) // 10
                card_w, card_h, pitch = col_w - 10, 44, 50
                col_of: dict[str, int] = {}
                row_of: dict[str, int] = {}
                rows_used: dict[str, int] = {}
                for nid in all_ids:
                    br = db.tech[nid].get("category", "SC")
                    j = rows_used.get(br, 0)
                    rows_used[br] = j + 1
                    col_of[nid] = _BRANCH_ORDER.index(br)
                    row_of[nid] = j
                sel_nid = tech_ids[research_cursor % len(tech_ids)]
                y_base = py0 + 84
                view_h = ph - 140
                sel_y = row_of[sel_nid] * pitch
                scroll = max(0, sel_y - (view_h - pitch))
                idx_of = {nid: i for i, nid in enumerate(tech_ids)}
                for k, br in enumerate(_BRANCH_ORDER):
                    done = sum(1 for n in all_ids
                               if db.tech[n].get("category") == br
                               and n in research.unlocked)
                    tot = sum(1 for n in all_ids
                              if db.tech[n].get("category") == br)
                    hx = px0 + 18 + k * col_w
                    theme.draw_text(screen, hx, py0 + 38,
                                    f"{br}  {done}/{tot}",
                                    color=(theme.COLORS["good"]
                                           if done == tot
                                           else theme.COLORS["text"]),
                                    font="ui_small")
                    theme.draw_text(screen, hx, py0 + 58, _BRANCH_NAMES[br],
                                    color=theme.COLORS["text_dim"],
                                    font="small")
                clip = pygame.Rect(px0 + 12, y_base, pw - 24, view_h)
                screen.set_clip(clip)
                for nid in all_ids:
                    x = px0 + 18 + col_of[nid] * col_w
                    y = y_base + row_of[nid] * pitch - scroll
                    if y + card_h < y_base or y > y_base + view_h:
                        continue
                    nd = db.tech[nid]
                    card = pygame.Rect(x, y, card_w, card_h)
                    if nid not in idx_of:          # fogged: ??? silhouette
                        pygame.draw.rect(screen, (8, 12, 20), card,
                                         border_radius=6)
                        pygame.draw.rect(screen, (26, 34, 50), card,
                                         width=1, border_radius=6)
                        theme.draw_text(screen, x + 8, y + 6, "???",
                                        color=(60, 72, 96), font="ui_small")
                        theme.draw_text(screen, x + 8, y + card_h - 17,
                                        nd["tier"], color=(60, 72, 96),
                                        font="small")
                        continue
                    unlocked = nid in research.unlocked
                    can = research.can_unlock(db, nid)
                    if unlocked:
                        fill, edge = (14, 40, 28), theme.COLORS["good"]
                    elif can:
                        fill, edge = (44, 36, 16), theme.COLORS["gold"]
                    elif nd.get("speculative"):
                        fill, edge = (16, 13, 28), (74, 56, 104)
                    else:
                        fill, edge = (12, 18, 30), theme.COLORS["panel_edge"]
                    pygame.draw.rect(screen, fill, card, border_radius=6)
                    pygame.draw.rect(screen, edge, card, width=1,
                                     border_radius=6)
                    if nid == sel_nid:
                        pygame.draw.rect(screen, theme.COLORS["accent"],
                                         card.inflate(6, 6), width=2,
                                         border_radius=8)
                    line1, line2 = "", ""
                    for wd in nd["name"].split():   # word-aware 2-line wrap
                        if not line2 and len(line1) + len(wd) < 17:
                            line1 = (line1 + " " + wd).strip()
                        else:
                            line2 = (line2 + " " + wd).strip()
                    ncol = (theme.COLORS["good"] if unlocked
                            else theme.COLORS["text"])
                    theme.draw_text(screen, x + 8, y + 4, line1,
                                    color=ncol, font="small")
                    if line2:
                        theme.draw_text(screen, x + 8, y + 16, line2[:18],
                                        color=ncol, font="small")
                    if nd.get("era"):
                        theme.draw_text(screen, x + card_w - 14, y + 3, "*",
                                        color=theme.COLORS["gold"],
                                        font="ui_small")
                    if unlocked:
                        state, scol = "researched", theme.COLORS["good"]
                    else:
                        state = f"{research.discounted_cost(db, nid):,.0f}"
                        if research.missing_ed(db, nid):
                            state += " +data"
                        if any(d not in research.discoveries
                               for d in nd.get("discovery_prereqs", [])):
                            state += " +dsc"
                        scol = (theme.COLORS["gold"] if can
                                else theme.COLORS["text_dim"])
                    theme.draw_text(screen, x + 8, y + card_h - 15, state,
                                    color=scol, font="small")
                    theme.draw_text(screen, x + card_w - 22, y + card_h - 15,
                                    nd["tier"],
                                    color=theme.COLORS["text_dim"],
                                    font="small")
                    overlay_rects["research"].append((card.copy(),
                                                      idx_of[nid]))
                screen.set_clip(None)
                # detail strip: the selected node, all gates explicit
                nd = db.tech[sel_nid]
                dscs = db.by_type("discoveries")
                cost = research.discounted_cost(db, sel_nid)
                bits = [nd["tier"], f"{cost:,.0f} sci"]
                if cost < nd.get("cost_sci", 0.0) - 0.5:
                    bits[-1] += f" (was {nd.get('cost_sci', 0.0):,.0f})"
                for th in nd.get("ed_thresholds", []):
                    bits.append(f"{th['family']} "
                                f"{research.d_f(th['family']):,.0f}"
                                f"/{th['value']:,.0f}")
                for d in nd.get("discovery_prereqs", []):
                    mark = "ok:" if d in research.discoveries else "needs"
                    bits.append(f"{mark} {dscs[d]['name']}")
                if nd.get("speculative"):
                    bits.append("[SPECULATIVE]")
                if nd.get("era"):
                    bits.append("ERA-DEFINING")
                theme.draw_text(screen, px0 + 24, py0 + ph - 50,
                                (nd["name"] + "   ·   "
                                 + "   ".join(bits))[:158],
                                color=theme.COLORS["text"], font="ui_small")
                pres = []
                for term in nd["prereqs"]:
                    if isinstance(term, list):
                        pres.append(" / ".join(db.tech[p]["name"]
                                               for p in term))
                    else:
                        pres.append(db.tech[term]["name"])
                info2 = ("needs: " + (", ".join(pres) or "—") + "   ·   "
                         + nd.get("anchor", "")
                         + "   ·   ENTER research  TAB data  R close")
                theme.draw_text(screen, px0 + 24, py0 + ph - 28, info2[:170],
                                color=theme.COLORS["text_dim"], font="small")

        # tutorial rail draws ABOVE every content overlay so guidance is
        # never hidden by the very screen it is teaching. Overlays whose
        # content starts high (research/ledger/crew/planner) get the rail
        # docked into the free lane above the footer instead; the builder
        # docks it right of its own message line; help/pause hide it.
        if (tutorial.visible and tutorial.current_text
                and not help_open and not pause_open):
            docked = (research_open or contracts_open or crew_open
                      or planner_open or builder_open)
            rail_txt = tutorial.current_text + ("" if docked
                                                else "   ·  H hides")
            max_w = 580 if builder_open else 920
            rail_lines, cur = [], ""
            for wd in rail_txt.split(" "):      # measured greedy wrap
                trial = (cur + " " + wd).strip()
                if cur and font.size(trial)[0] > max_w:
                    rail_lines.append(cur)
                    cur = wd
                else:
                    cur = trial
            rail_lines.append(cur)
            imgs = [font.render(ln, True, (140, 235, 255))
                    for ln in rail_lines]
            pw_r = max(i.get_width() for i in imgs) + 20
            ph_r = 8 + 19 * len(imgs)
            ty = (size[1] - theme.FOOTER_H - ph_r - 8 if docked else 116)
            tx = (size[0] - pw_r - 16 if builder_open
                  else size[0] // 2 - pw_r // 2)
            tbg = pygame.Surface((pw_r, ph_r), pygame.SRCALPHA)
            pygame.draw.rect(tbg, (10, 16, 28, 215), tbg.get_rect(),
                             border_radius=11)
            pygame.draw.rect(tbg, (60, 86, 116, 220), tbg.get_rect(),
                             width=1, border_radius=11)
            screen.blit(tbg, (tx, ty))
            for li_r, img in enumerate(imgs):
                screen.blit(img, (tx + 10, ty + 4 + li_r * 19))

        if pause_open:
            dim = pygame.Surface(size, pygame.SRCALPHA)
            dim.fill((4, 6, 10, 170))
            screen.blit(dim, (0, 0))
            ppan = theme.panel(340, 80 + 34 * len(_PAUSE_ITEMS), "PAUSED")
            ppx = size[0] // 2 - 170
            ppy = 200
            screen.blit(ppan, (ppx, ppy))
            overlay_rects["pause"] = []
            for i, label in enumerate(_PAUSE_ITEMS):
                sel = i == pause_cursor
                color = theme.COLORS["gold"] if sel else theme.COLORS["text"]
                if sel:
                    screen.blit(theme.row_glow(296, 30),
                                (ppx + 20, ppy + 44 + i * 34))
                txt = font_med.render(("> " if sel else "  ") + label, True,
                                      color)
                screen.blit(txt, (ppx + 28, ppy + 48 + i * 34))
                overlay_rects["pause"].append(
                    (pygame.Rect(ppx + 20, ppy + 44 + i * 34, 296, 32), i))

        if help_open:
            dim = pygame.Surface(size, pygame.SRCALPHA)
            dim.fill((4, 6, 10, 200))
            screen.blit(dim, (0, 0))
            hp = theme.panel(880, 612, "CONTROLS")
            hpx, hpy = size[0] // 2 - 440, size[1] // 2 - 306
            screen.blit(hp, (hpx, hpy))
            cols = (
                ("FLIGHT", (
                    ("X / Z", "burn prograde / retrograde"),
                    ("A / D", "burn radial out / in  (SHIFT = 100 m/s)"),
                    ("N", "node — arrows dv (CTRL fine), [/] time, "
                          "P/A snap, O +1 orbit"),
                    ("W", "warp to the armed node's burn"),
                    ("P", "transfer planner: windows + dv to every planet"),
                    ("right-click", "set TARGET body (encounter + closest "
                                    "approach)"),
                    ("V / click", "switch command between vessels"),
                    ("E / U / T", "dock (E8 port match) · undock · "
                                  "crossfeed (DK-L only)"),
                    ("I", "board the stack: walk its pressurized modules"),
                    ("F7", "station ops: spin gravity, balance, fees"),
                    ("G", "surface ops: land, relaunch, found a base"),
                    ("TAB / click", "camera focus   ·   C your craft"),
                    ("wheel", "zoom   ·   . , time warp   ·   SPACE pause"),
                )),
                ("ASCENT", (
                    ("SPACE", "ignition, then stage"),
                    ("SHIFT/CTRL", "throttle up / down   ·   X/Z max / cut"),
                    ("arrows", "pitch (manual)   ·   P autopilot"),
                    ("C", "circularize assist   ·   ESC revert (T+20s)"),
                )),
                ("PROGRAM", (
                    ("B", "vessel builder"),
                    ("O", "contract ledger: every deadline and payout"),
                    ("R / K", "research tree · crew roster (ENTER trains)"),
                    ("F2", "colony operations + construction"),
                    ("F5 / F9", "quicksave / quickload (autosaves 5 min)"),
                    ("H / F1", "tutorial rail · this screen"),
                    ("M / F11", "mute · fullscreen"),
                )),
            )
            hy = hpy + 40
            for title2, rows2 in cols:
                theme.draw_text(screen, hpx + 28, hy, title2,
                                color=theme.COLORS["gold"], font="title")
                hy += 28
                for keys2, what2 in rows2:
                    theme.draw_text(screen, hpx + 40, hy, f"{keys2:12s}",
                                    color=theme.COLORS["accent"], font="small")
                    theme.draw_text(screen, hpx + 150, hy, what2,
                                    color=theme.COLORS["text"], font="small")
                    hy += 21
                hy += 8
            theme.draw_text(screen, hpx + 28, hpy + 582,
                            "F1 / ESC — close",
                            color=theme.COLORS["text_dim"], font="small")

        screen.blit(vig, (0, 0))
        if gold_flash > 0.0:
            fl = pygame.Surface(size, pygame.SRCALPHA)
            fl.fill((255, 215, 130, int(56 * gold_flash)))
            screen.blit(fl, (0, 0))
            gold_flash = max(0.0, gold_flash - 1.6 * real_dt)
        present_frame()
        frame_count += 1
        if args.frames and frame_count >= args.frames:
            running = False

    if args.screenshot:
        pygame.image.save(glp.read_screen() if glp is not None else screen,
                          args.screenshot)
    if args.perf and len(perf_samples) > 40:
        body = sorted(perf_samples[30:])        # caches warm after ~30
        avg = sum(body) / len(body)
        p95 = body[int(0.95 * (len(body) - 1))]
        print(f"PERF avg={avg:.2f} p95={p95:.2f} n={len(body)}",
              flush=True)
    pygame.quit()
    return 0


if __name__ == "__main__":
    sys.exit(run())
