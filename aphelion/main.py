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
import math
import os
import sys

from aphelion.core.clock import RAILS_RATES, SimClock
from aphelion.core.units import SECONDS_PER_DAY
from aphelion.render.camera import Camera, ZoomLayer
from aphelion.sim.economy import Contract, Program
from aphelion.sim.orbits.ephemeris import load_solar_system
from aphelion.sim.orbits.kepler import elements_to_state, state_to_elements
from aphelion.sim.orbits import transfers as tr
from aphelion.sim.orbits.trajectory import predict_trajectory
from aphelion.sim.research import ResearchState

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
_ORBIT_COLOR = (40, 50, 70)
_MOON_ORBIT_COLOR = (55, 65, 85)
_CRAFT_COLOR = (120, 255, 170)
_LEG_COLORS = [(120, 255, 170), (255, 200, 60), (255, 120, 200),
               (140, 200, 255), (255, 160, 90), (200, 140, 255)]
_WARP_LADDER = (1.0,) + RAILS_RATES
_PREDICT_HORIZON = 60.0 * SECONDS_PER_DAY
_PAUSE_ITEMS = ("RESUME", "QUICKSAVE", "LOAD QUICKSAVE",
                "EXIT TO MAIN MENU", "QUIT TO DESKTOP")


def _tech_order(db) -> list[str]:
    return sorted(db.tech, key=lambda i: (db.tech[i].get("cost_sci", 0.0)
                                          + db.tech[i].get("cost_ed", 0.0)))


from aphelion.game.fleet import FleetVessel  # noqa: E402  (campaign vessel)
from aphelion.game.sites import SITES, sites_for_body  # noqa: E402


def _surface_options(av, bases) -> list[tuple[tuple, str]]:
    """Context actions for the surface-ops panel (G)."""
    opts: list[tuple[tuple, str]] = []
    if av.landed_at is not None:
        site = SITES[av.landed_at]
        opts.append((("relaunch",),
                     f"RELAUNCH to 100 km orbit   ({site['ascent_dv']:,.0f} m/s)"))
        if not any(getattr(b, "site_id", None) == av.landed_at for b in bases):
            opts.append((("found",),
                         "FOUND A BASE here (vessel becomes base hardware)"))
    else:
        for sid, s in sites_for_body(av.frame_id):
            opts.append((("land", sid),
                         f"LAND: {s['name']}   ({s['land_dv']:,.0f} m/s)"))
    return opts


class BaseSite:
    """A founded surface base: a live ledger network advanced to sim time
    every frame (warp-exact by construction), failures pre-rolled, repairs
    on a 48 h maintenance turnaround (Phase 3 acceptance machinery)."""

    REPAIR_TURNAROUND = 48.0 * 3_600.0

    def __init__(self, name: str, t_founded: float, rng,
                 site_id: str = "site:peary") -> None:
        self.site_id = site_id
        self._init_net(name, t_founded, rng)

    def _init_net(self, name: str, t_founded: float, rng) -> None:
        from aphelion.game.basebuild import starter_network
        self.name = name
        self.last_t = t_founded
        self.events: list = []
        self.pending_repairs: list[tuple[float, str]] = []
        self.built: list[str] = ["solar_array"]
        self.net = starter_network(SITES[self.site_id], rng=rng)

    def build(self, key: str, t: float, research, program) -> tuple[bool, str]:
        """Buy and install a module from the base catalog."""
        from aphelion.game.basebuild import CATALOG, add_module
        spec = CATALOG[key]
        if spec["tech"] and spec["tech"] not in research.unlocked:
            return False, f"{spec['name']} needs research: {spec['tech'].split(':')[1]}"
        cost = spec["price_m"] * 1e6
        if not program.spend(t, cost, f"base module {key}"):
            return False, f"insufficient funds (${spec['price_m']:,.0f}M)"
        self.advance(t)                       # settle the ledger first
        add_module(self.net, key, SITES[self.site_id], serial=len(self.built))
        self.built.append(key)
        return True, f"{spec['name']} ONLINE (${spec['price_m']:,.0f}M)"

    @classmethod
    def from_restore(cls, name: str, last_t: float,
                     pending_repairs: list, net,
                     site_id: str = "site:peary",
                     built: list[str] | None = None) -> "BaseSite":
        site = cls.__new__(cls)
        site.site_id = site_id
        site.built = list(built or ["solar_array"])
        site.name = name
        site.last_t = last_t
        site.events = []
        site.pending_repairs = list(pending_repairs)
        site.net = net
        return site

    def advance(self, t: float) -> list:
        from aphelion.sim.ledger.network import LedgerEvent
        new_events = []
        guard = 0
        while self.last_t < t - 1e-6 and guard < 200:
            guard += 1
            self.net.roll_failures(self.last_t)
            t_rep = min((r[0] for r in self.pending_repairs), default=float("inf"))
            t_stop = min(t, t_rep)
            evs = self.net.advance(self.last_t, t_stop)
            new_events.extend(evs)
            for e in evs:
                if e.kind == "module_failed":
                    self.pending_repairs.append(
                        (e.t + self.REPAIR_TURNAROUND, e.subject))
            if t_rep <= t_stop + 1e-6:
                due = min(self.pending_repairs)
                self.pending_repairs.remove(due)
                mod = [m for m in self.net.modules if m.module_id == due[1]][0]
                self.net.repair(mod, due[0])
                new_events.append(LedgerEvent(due[0], "repaired", due[1]))
            self.last_t = t_stop
        self.events.extend(new_events)
        return new_events


class Builder:
    """The Engineer screen (12 §5.4 / 06 §3): pick parts (research-gated),
    group into stages, watch live Tsiolkovsky/TWR, then fly the real
    ascent sim. Pricing is the 12-owned placeholder $2M/t dry + $0.5M/t
    propellant until the economy pass lands final tags."""

    def __init__(self, db, research) -> None:
        self.db = db
        self.research = research
        self.catalog = sorted(
            [pid for pid, p in db.parts.items()
             if p["type"] in ("engine", "tank", "structure", "crew")])
        self.cursor = 0
        self.stack: list[list[str]] = [[]]    # stages, bottom first
        self.message = "assemble a vessel from the catalog, then L to launch it"

    def locked(self, part_id: str) -> bool:
        return not self.research.part_available(self.db, part_id)

    def add(self) -> None:
        pid = self.catalog[self.cursor]
        if self.locked(pid):
            self.message = f"{pid.split(':')[1]} is research-locked"
            return
        self.stack[-1].append(pid)
        self.message = f"added {pid.split(':')[1]}"

    def remove(self) -> None:
        if self.stack[-1]:
            self.stack[-1].pop()
        elif len(self.stack) > 1:
            self.stack.pop()

    def new_stage(self) -> None:
        if self.stack[-1]:
            self.stack.append([])

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
        return Vessel(self.db, rows, stage_plan=plan, cd_a_m2=3.2)

    def price(self, vessel) -> float:
        dry = vessel.dry_mass_kg() / 1_000.0
        prop = (vessel.total_mass_kg() - vessel.dry_mass_kg()) / 1_000.0
        return (2.0 * dry + 0.5 * prop) * 1e6


def run(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="aphelion")
    parser.add_argument("--frames", type=int, default=0)
    parser.add_argument("--screenshot", type=str, default="")
    parser.add_argument("--headless", action="store_true")
    parser.add_argument("--scene", type=str, default="auto",
                        choices=["auto", "menu", "flight", "builder", "base",
                                 "research", "ascent"])
    args = parser.parse_args(argv)
    if args.headless:
        os.environ["SDL_VIDEODRIVER"] = "dummy"
        os.environ["SDL_AUDIODRIVER"] = "dummy"

    import numpy as np
    import pygame
    from aphelion.render.body_art import body_sprite, marker_dot, sun_sprite
    from aphelion.render.draw_conics import draw_conic
    from aphelion.render.postfx import Bloom, Nebula, soi_ring, vignette
    from aphelion.render.vessel_art import (
        app_icon, craft_icon, part_thumb, vessel_sprite)
    from aphelion.sim.environment.atmosphere import density as atmo_density
    from aphelion.sim.flight.ascent_live import LiveAscent
    from aphelion.ui import theme
    from aphelion.ui.audio import AudioCues
    from aphelion.ui.effects import Particles, Starfield
    from aphelion.ui.tutorial import first_flight_tutorial

    from aphelion.core.rng import RngRegistry
    from aphelion.game.crew import (
        CrewMember, apply_crew_bonuses, candidates, science_multiplier)
    from aphelion.save.campaign import (
        default_save_dir, read_campaign, snapshot_campaign, write_campaign)
    from aphelion.sim.habitat.dose import AMBIENT_MSV_DAY

    db, tree = load_solar_system()
    planets = sorted((i for i, b in db.bodies.items() if b["parent"] == "core:sun"),
                     key=lambda i: db.bodies[i]["elements"]["a_m"])
    moons_of = {i: tree.children(i) for i in planets}

    pygame.init()
    size = (1280, 720)
    fullscreen = False
    pygame.display.set_icon(app_icon())
    screen = pygame.display.set_mode(size, pygame.SCALED | pygame.DOUBLEBUF,
                                     vsync=0 if args.headless else 1)
    pygame.display.set_caption("APHELION")
    pygame_clock = pygame.time.Clock()
    font = pygame.font.SysFont("consolas", 14)
    font_med = pygame.font.SysFont("consolas", 18, bold=True)
    font_big = pygame.font.SysFont("consolas", 44, bold=True)
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
    qs_path = default_save_dir() / "quicksave.aph"

    def fresh_campaign() -> dict:
        """A brand-new 2049 campaign (12 §3: Act 1 opens with money, two
        astronauts, an empty pad — and no rocket. Build one. Contracts
        arrive from the Act table (game/campaign.py) as you earn them."""
        return dict(clock=SimClock(t0=0.0), vessels=[], active_idx=0,
                    next_vid=1, program=Program(funds=150_000_000.0),
                    rng=RngRegistry(20490101), bases=[],
                    crew={"V. Ainsworth": CrewMember("V. Ainsworth",
                                                     "pilot", 2),
                          "J. Okafor": CrewMember("J. Okafor",
                                                  "engineer", 1)},
                    research=ResearchState(), visited={"core:earth"},
                    visited_surface=set(), milestones=set(),
                    tutorial=first_flight_tutorial())

    def loaded_campaign() -> dict:
        got = read_campaign(qs_path, db, tree)
        tut = first_flight_tutorial()
        tut.completed = got["tutorial_done"]
        rng = (RngRegistry.from_state(got["rng_state"]) if got["rng_state"]
               else RngRegistry(20490101))
        for b in got["bases"]:
            b["net"].rng = rng      # resume the SAME failure streams
        for v in got["vessels"]:
            apply_crew_bonuses(v, got["crew"])
        return dict(clock=SimClock(t0=got["t"]), vessels=got["vessels"],
                    active_idx=got["active_idx"], next_vid=got["next_vid"],
                    program=got["program"], rng=rng,
                    bases=[BaseSite.from_restore(b["name"], b["last_t"],
                                                 b["pending_repairs"], b["net"],
                                                 b.get("site_id", "site:peary"),
                                                 b.get("built"))
                           for b in got["bases"]],
                    crew=got["crew"], research=got["research"],
                    visited=got["visited"],
                    visited_surface=got["visited_surface"],
                    milestones=got["milestones"], tutorial=tut)

    def campaign_tuple(st: dict):
        """One unpack shape for new game, quickload, and startup."""
        return (st["clock"], st["vessels"], st["active_idx"], st["next_vid"],
                st["program"], st["rng"], st["bases"], st["crew"],
                st["research"], st["visited"], st["visited_surface"],
                st["milestones"], st["tutorial"], Builder(db, st["research"]),
                None, 0, False, False, False, False, False, 0.0, "", 0.0)

    (clock, vessels, active_idx, next_vid, program, campaign_rng, bases,
     crew, research, visited, visited_surface, milestones, tutorial, builder,
     node, warp_idx, paused, base_screen, builder_open, research_open,
     crew_warned, last_dose_t, toast, toast_until) = \
        campaign_tuple(fresh_campaign())

    def do_quicksave() -> str:
        snap = snapshot_campaign(
            t=clock.t, vessels=vessels, active_idx=active_idx,
            next_vid=next_vid, program=program, research=research,
            crew=crew, visited=visited, visited_surface=visited_surface,
            milestones=milestones, bases=bases,
            tutorial_done=tutorial.completed, rng=campaign_rng)
        write_campaign(qs_path, snap)
        return "QUICKSAVED"

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
        base_screen = True
    boot_ascent = want == "ascent"

    menu_cursor = 0
    menu_rects: list = []
    pause_open = False
    pause_cursor = 0
    research_cursor = 0
    surface_open = False
    surface_cursor = 0
    base_cursor = 0
    base_idx = 0
    crew_open = False
    crew_cursor = 0
    body_click_pts: list = []
    vessel_click_pts: list = []
    burn_glow = 0.0

    # ascent scene state (KSP-style flown launch)
    live: LiveAscent | None = None
    live_stack: list[list[str]] = []
    launch_cost = 0.0
    ascent_warp = 1.0
    ascent_acc = 0.0
    rot_cache: dict = {}
    # cached sky gradient, alpha-faded by local air density during ascent
    sky_grad = pygame.Surface(size)
    _g = np.linspace(0.0, 1.0, size[1])[:, None]
    _sky = ((1.0 - _g) * np.array([88.0, 146.0, 212.0])
            + _g * np.array([148.0, 192.0, 238.0]))
    pygame.surfarray.blit_array(sky_grad,
                                np.repeat(_sky[None, :, :], size[0],
                                          axis=0).astype("uint8"))
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

    frame_count = 0
    running = True
    while running:
        real_dt = pygame_clock.tick(60) / 1000.0
        t = clock.t
        start_new = False
        load_save = False
        ascent_done = False
        ascent_abort = False
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_F11:
                fullscreen = not fullscreen
                flags = pygame.SCALED | pygame.DOUBLEBUF | (
                    pygame.FULLSCREEN if fullscreen else 0)
                screen = pygame.display.set_mode(size, flags,
                                                 vsync=0 if args.headless else 1)
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_m:
                audio.muted = not audio.muted
                toast = "audio muted" if audio.muted else "audio on"
                toast_until = t + 3.0
            elif scene == "menu":
                items = (["NEW CAMPAIGN"]
                         + (["CONTINUE"] if qs_path.exists() else [])
                         + ["QUIT"])
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_UP:
                        menu_cursor = (menu_cursor - 1) % len(items)
                    elif event.key == pygame.K_DOWN:
                        menu_cursor = (menu_cursor + 1) % len(items)
                    elif event.key == pygame.K_RETURN:
                        choice = items[menu_cursor % len(items)]
                        audio.play("blip")
                        if choice == "NEW CAMPAIGN":
                            start_new = True
                        elif choice == "CONTINUE":
                            load_save = True
                        else:
                            running = False
                    elif event.key == pygame.K_ESCAPE:
                        running = False
                elif event.type == pygame.MOUSEMOTION:
                    for i, rect in enumerate(menu_rects):
                        if rect.collidepoint(event.pos):
                            menu_cursor = i
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    for i, rect in enumerate(menu_rects):
                        if rect.collidepoint(event.pos) and i < len(items):
                            choice = items[i]
                            audio.play("blip")
                            if choice == "NEW CAMPAIGN":
                                start_new = True
                            elif choice == "CONTINUE":
                                load_save = True
                            else:
                                running = False
            elif scene == "ascent":
                if event.type == pygame.KEYDOWN and live is not None:
                    if event.key == pygame.K_SPACE:
                        if not live.ignited:
                            live.ignite()
                            audio.play("burn")
                        elif live.stage():
                            audio.play("blip")
                    elif event.key == pygame.K_z:
                        live.throttle_cmd = 1.0
                    elif event.key == pygame.K_x:
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
                        ascent_abort = True
            elif scene == "victory":
                if event.type == pygame.KEYDOWN and event.key in (
                        pygame.K_RETURN, pygame.K_ESCAPE):
                    scene = "flight"
                    toast = ("the program continues — the sky is not the "
                             "limit anymore")
                    toast_until = t + 10
            elif event.type == pygame.KEYDOWN and pause_open:
                if event.key == pygame.K_ESCAPE:
                    pause_open = False
                elif event.key == pygame.K_UP:
                    pause_cursor = (pause_cursor - 1) % len(_PAUSE_ITEMS)
                elif event.key == pygame.K_DOWN:
                    pause_cursor = (pause_cursor + 1) % len(_PAUSE_ITEMS)
                elif event.key == pygame.K_RETURN:
                    choice = _PAUSE_ITEMS[pause_cursor]
                    if choice == "RESUME":
                        pause_open = False
                    elif choice == "QUICKSAVE":
                        toast, toast_until = do_quicksave(), t + 5.0
                        audio.play("blip")
                    elif choice == "LOAD QUICKSAVE":
                        load_save = True
                    elif choice == "EXIT TO MAIN MENU":
                        pause_open = False
                        scene = "menu"
                        menu_cursor = 0
                    else:
                        running = False
            elif event.type == pygame.KEYDOWN and surface_open:
                av0 = vessels[active_idx % len(vessels)] if vessels else None
                opts = _surface_options(av0, bases) if av0 else []
                if event.key in (pygame.K_ESCAPE, pygame.K_g) or not opts:
                    surface_open = False
                elif event.key == pygame.K_UP:
                    surface_cursor = (surface_cursor - 1) % len(opts)
                elif event.key == pygame.K_DOWN:
                    surface_cursor = (surface_cursor + 1) % len(opts)
                elif event.key == pygame.K_RETURN:
                    action = opts[surface_cursor % len(opts)][0]
                    if action[0] == "relaunch":
                        site = SITES[av0.landed_at]
                        if av0.relaunch(site, t):
                            toast = (f"{av0.name} BACK IN ORBIT — "
                                     f"{av0.dv_remaining:,.0f} m/s remains")
                            toast_until = t + 8
                            surface_open = False
                            audio.play("burn")
                        else:
                            toast = (f"ascent needs {site['ascent_dv']:,.0f}"
                                     f" m/s — not enough propellant")
                            toast_until = t + 6
                            audio.play("alarm")
                    elif action[0] == "found":
                        site_id = av0.landed_at
                        site = SITES[site_id]
                        bases.append(BaseSite(
                            f"{site['name'].split(' (')[0]} Base", t,
                            campaign_rng, site_id=site_id))
                        vessels.remove(av0)
                        active_idx = 0
                        node = None
                        surface_open = False
                        toast = f"BASE FOUNDED at {site['name']} (F2 to build)"
                        toast_until = t + 10
                        audio.play("paid")
                    elif action[0] == "land":
                        sid = action[1]
                        site = SITES[sid]
                        if av0.land_at(sid, site, t):
                            surface_open = False
                            burn_glow = 0.8
                            msg = f"TOUCHDOWN: {site['name']}"
                            if sid not in visited_surface:
                                visited_surface.add(sid)
                                sci = (site["science"]
                                       * science_multiplier(av0, crew))
                                research.earn_science(sci)
                                research.earn_eng_data(sci * 0.3)
                                msg += f"  +{sci:.0f} science"
                            toast, toast_until = msg, t + 10
                            audio.play("soi")
                        else:
                            toast = (f"landing needs {site['land_dv']:,.0f}"
                                     f" m/s — not enough propellant")
                            toast_until = t + 6
                            audio.play("alarm")
            elif event.type == pygame.KEYDOWN and crew_open:
                cands = candidates(crew)
                if event.key in (pygame.K_ESCAPE, pygame.K_k):
                    crew_open = False
                elif event.key == pygame.K_UP and cands:
                    crew_cursor = (crew_cursor - 1) % len(cands)
                elif event.key == pygame.K_DOWN and cands:
                    crew_cursor = (crew_cursor + 1) % len(cands)
                elif event.key == pygame.K_RETURN and cands:
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
            elif event.type == pygame.KEYDOWN and base_screen:
                from aphelion.game.basebuild import CATALOG, catalog_for_kind
                site_b = bases[base_idx % len(bases)] if bases else None
                if site_b is None or event.key in (pygame.K_ESCAPE,
                                                   pygame.K_F2):
                    base_screen = False
                else:
                    avail = catalog_for_kind(SITES[site_b.site_id]["kind"])
                    if event.key == pygame.K_TAB:
                        base_idx = (base_idx + 1) % len(bases)
                        base_cursor = 0
                    elif event.key == pygame.K_UP:
                        base_cursor = (base_cursor - 1) % len(avail)
                    elif event.key == pygame.K_DOWN:
                        base_cursor = (base_cursor + 1) % len(avail)
                    elif event.key == pygame.K_RETURN and avail:
                        ok, msg = site_b.build(
                            avail[base_cursor % len(avail)], t, research,
                            program)
                        toast, toast_until = msg, t + 6
                        audio.play("paid" if ok else "alarm")
            elif event.type == pygame.KEYDOWN and research_open:
                tech_ids = _tech_order(db)
                if event.key in (pygame.K_ESCAPE, pygame.K_r):
                    research_open = False
                elif event.key == pygame.K_UP:
                    research_cursor = (research_cursor - 1) % len(tech_ids)
                elif event.key == pygame.K_DOWN:
                    research_cursor = (research_cursor + 1) % len(tech_ids)
                elif event.key == pygame.K_RETURN:
                    nid = tech_ids[research_cursor % len(tech_ids)]
                    if research.unlock(db, nid, t):
                        toast = f"RESEARCHED: {db.tech[nid]['name']}"
                        toast_until = t + 8.0
                        audio.play("paid")
                    else:
                        toast = "cannot unlock (prereqs or insufficient sci/ed)"
                        toast_until = t + 5.0
                        audio.play("alarm")
            elif event.type == pygame.KEYDOWN and builder_open:
                if event.key in (pygame.K_b, pygame.K_ESCAPE):
                    builder_open = False
                elif event.key == pygame.K_UP:
                    builder.cursor = (builder.cursor - 1) % len(builder.catalog)
                elif event.key == pygame.K_DOWN:
                    builder.cursor = (builder.cursor + 1) % len(builder.catalog)
                elif event.key == pygame.K_RETURN:
                    builder.add()
                    audio.play("blip")
                elif event.key == pygame.K_BACKSPACE:
                    builder.remove()
                elif event.key == pygame.K_s:
                    builder.new_stage()
                elif event.key == pygame.K_l:
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
                            ascent_warp, ascent_acc = 1.0, 0.0
                            node = None
                            builder_open = False
                            scene = "ascent"
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
                        toast, toast_until = ("NODE placed +10 min: arrows set dv, "
                                              "[/] move time, ENTER arm, N cancel"), t + 8
                    else:
                        node = None
                        toast, toast_until = "node cancelled", t + 4
                elif node is not None and not node["armed"] and event.key in (
                        pygame.K_UP, pygame.K_DOWN, pygame.K_LEFT, pygame.K_RIGHT,
                        pygame.K_LEFTBRACKET, pygame.K_RIGHTBRACKET,
                        pygame.K_RETURN):
                    nstep = 100.0 if shift else 10.0
                    if event.key == pygame.K_UP:
                        node["dvp"] += nstep
                    elif event.key == pygame.K_DOWN:
                        node["dvp"] -= nstep
                    elif event.key == pygame.K_RIGHT:
                        node["dvr"] += nstep
                    elif event.key == pygame.K_LEFT:
                        node["dvr"] -= nstep
                    elif event.key == pygame.K_LEFTBRACKET:
                        node["t_node"] = max(t + 60.0,
                                             node["t_node"] - (600.0 if shift else 60.0))
                    elif event.key == pygame.K_RIGHTBRACKET:
                        node["t_node"] += 600.0 if shift else 60.0
                    elif event.key == pygame.K_RETURN:
                        need = math.hypot(node["dvp"], node["dvr"])
                        av0 = vessels[active_idx % len(vessels)] if vessels else None
                        if (av0 is None or av0.landed_at is not None
                                or need > av0.dv_remaining):
                            toast, toast_until = "node exceeds dv budget", t + 5
                            audio.play("alarm")
                        else:
                            node["armed"] = True
                            toast, toast_until = ("node ARMED — warp on; burn "
                                                  "executes on time"), t + 6
                            audio.play("blip")
                elif event.key == pygame.K_F2:
                    base_screen = not base_screen
                elif event.key == pygame.K_v and vessels:
                    active_idx = (active_idx + 1) % len(vessels)
                    node = None
                    av0 = vessels[active_idx]
                    toast, toast_until = f"ACTIVE: {av0.name}", t + 4
                    audio.play("blip")
                elif event.key == pygame.K_e and vessels:
                    # dock: chaser = active vessel, target = nearest in envelope
                    av0 = vessels[active_idx % len(vessels)]
                    best_tgt, best_cost = None, float("inf")
                    for other in vessels:
                        c = av0.rendezvous_cost(other, t)
                        if c is not None and c < best_cost:
                            best_tgt, best_cost = other, c
                    if best_tgt is None:
                        toast = ("no dock target within 100 km of "
                                 f"{av0.name}")
                        toast_until = t + 5
                        audio.play("alarm")
                    elif av0.dock_with(best_tgt, t):
                        vessels.remove(av0)
                        active_idx = vessels.index(best_tgt)
                        node = None
                        milestones.add("docked")
                        toast = (f"DOCKED: {av0.name} -> {best_tgt.name} "
                                 f"({best_cost:,.0f} m/s rendezvous)")
                        toast_until = t + 8
                        audio.play("paid")
                    else:
                        toast = (f"dock refused: {best_cost:,.0f} m/s "
                                 f"rendezvous exceeds propellant")
                        toast_until = t + 6
                        audio.play("alarm")
                elif event.key == pygame.K_u and vessels:
                    av0 = vessels[active_idx % len(vessels)]
                    split = av0.undock_last(t, next_vid)
                    if split is None:
                        toast, toast_until = "nothing docked to release", t + 4
                    else:
                        next_vid += 1
                        vessels.append(split)
                        toast = f"UNDOCKED: {split.name} is free-flying"
                        toast_until = t + 6
                        audio.play("blip")
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
                        toast, toast_until = "no propellant to crossfeed", t + 4
                elif event.key == pygame.K_g:
                    if vessels:
                        surface_open = not surface_open
                        surface_cursor = 0
                    else:
                        toast, toast_until = "no vessel — build one (B)", t + 5
                        audio.play("alarm")
                elif event.key == pygame.K_SPACE:
                    paused = not paused
                elif event.key == pygame.K_PERIOD:
                    warp_idx = min(warp_idx + 1, len(_WARP_LADDER) - 1)
                elif event.key == pygame.K_COMMA:
                    warp_idx = max(warp_idx - 1, 0)
                elif event.key == pygame.K_TAB:
                    focus_idx = (focus_idx + (-1 if shift else 1)) % len(focus_order)
                elif event.key == pygame.K_c:
                    focus_idx = 0
                elif event.key == pygame.K_F1:
                    tutorial.visible = not tutorial.visible
                elif event.key == pygame.K_k:
                    crew_open = True
                    crew_cursor = 0
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
            elif (event.type == pygame.MOUSEBUTTONDOWN and event.button == 1
                  and not (pause_open or builder_open or research_open)):
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
             tutorial, builder, node, warp_idx, paused, base_screen,
             builder_open, research_open, crew_warned, last_dose_t, toast,
             toast_until) = campaign_tuple(fresh_campaign())
            scene, pause_open, focus_idx = "flight", False, 0
            surface_open = False
        if load_save:
            if qs_path.exists():
                try:
                    (clock, vessels, active_idx, next_vid, program,
                     campaign_rng, bases, crew, research, visited,
                     visited_surface, milestones, tutorial, builder, node,
                     warp_idx, paused, base_screen, builder_open,
                     research_open, crew_warned, last_dose_t, toast,
                     toast_until) = campaign_tuple(loaded_campaign())
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
                mu_e = tree.body("core:earth").mu
                fv = FleetVessel(tree, "core:earth",
                                 state_to_elements(live.x, live.y, live.vx,
                                                   live.vy, t, mu_e),
                                 live.vessel, f"Vessel-{next_vid}",
                                 next_vid, t_now=t)
                next_vid += 1
                # crew board up to capacity (those not already flying)
                aboard_elsewhere = {n for v in vessels for n in v.crew}
                free = [n for n in crew if n not in aboard_elsewhere]
                fv.crew = free[:fv.crew_capacity]
                vessels.append(fv)
                active_idx = len(vessels) - 1
                milestones.add("orbited")
                apply_crew_bonuses(fv, crew)
                crewed = f" — crew: {', '.join(fv.crew)}" if fv.crew else ""
                toast = (f"{fv.name} IN ORBIT — "
                         f"{fv.dv_remaining:,.0f} m/s remaining{crewed}")
                toast_until = t + 10.0
                focus_idx = 0
                audio.play("paid")
            else:
                toast = "LOSS OF VEHICLE — funds spent, vessel destroyed"
                toast_until = t + 8.0
                audio.play("alarm")
            live = None
            scene = "flight"

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
                        audio.play("paid" if live.outcome == "orbit"
                                   else "alarm")
                        break

            # ---- draw: sky fades to space with air density ----
            screen.fill((6, 8, 14))
            nebula.draw(screen, None)
            rho_n = min(1.0, atmo_density("core:earth",
                                          max(live.h, 0.0)) / 1.225)
            sky_a = int(255.0 * rho_n ** 0.35)
            if sky_a > 2:
                sky_grad.set_alpha(sky_a)
                screen.blit(sky_grad, (0, 0))

            px_per_m = max(0.0022, 0.26 * 1500.0 / (1500.0 + live.h))
            rocket_y = int(size[1] * 0.62)
            ground_y = rocket_y + int(max(live.h, 0.0) * px_per_m)
            theta = math.atan2(live.y, live.x)
            pad_ang = (theta - live.omega * live.t + math.pi) % (
                2.0 * math.pi) - math.pi
            downrange = pad_ang * live.radius
            pad_x = size[0] // 2 - int(downrange * px_per_m)
            if ground_y < size[1] + 600:
                pygame.draw.rect(screen, (28, 46, 34),
                                 (0, min(ground_y, size[1]), size[0],
                                  max(0, size[1] - ground_y) + 4))
                if -300 < pad_x < size[0] + 300:
                    pygame.draw.rect(screen, (70, 74, 82),
                                     (pad_x - 52, ground_y - 6, 104, 8))
                    pygame.draw.rect(screen, (96, 60, 48),
                                     (pad_x + 58, ground_y - 70, 8, 66))

            stack_now = live_stack[live.stages_spent:]
            tilt = -(90.0 - live.gamma_deg)
            rs = max(0.12, 1500.0 / (1500.0 + 1.2 * live.h))
            rkey = (live.stages_spent, int(tilt // 4), round(rs, 2))
            if rkey not in rot_cache:
                if len(rot_cache) > 160:
                    rot_cache.clear()
                base = (vessel_sprite(db, stack_now) if stack_now
                        else craft_icon(math.radians(live.gamma_deg), 16))
                rot_cache[rkey] = pygame.transform.rotozoom(base, tilt, rs)
            rspr = rot_cache[rkey]
            rx = size[0] // 2 - rspr.get_width() // 2
            ry = rocket_y - rspr.get_height() // 2 - int(
                12 * rs) if live.h > 1.0 else ground_y - rspr.get_height()
            screen.blit(rspr, (rx, ry))
            if live.throttle_eff > 0.0:
                ang = math.radians(live.gamma_deg)
                ex = -math.cos(ang)
                ey = math.sin(ang)              # exhaust dir, screen y-down
                ccx = size[0] // 2
                ccy = ry + rspr.get_height() // 2
                hh = rspr.get_height() / 2.0 - 4.0
                particles.emit_burn(ccx + ex * hh, ccy + ey * hh, ex, ey,
                                    n=3)
            particles.update_draw(screen, real_dt)

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
            screen.blit(theme.panel(size[0], 26), (0, size[1] - 26))
            theme.draw_text(
                screen, 10, size[1] - 21,
                "SPACE ignite/stage   SHIFT/CTRL throttle   Z/X max/cut   "
                "arrows pitch (manual)   P autopilot   C circularize   "
                "./, warp   ESC revert",
                color=theme.COLORS["text_dim"], font="small", shadow=False)
            bloom.apply(screen)
            screen.blit(vig, (0, 0))
            pygame.display.flip()
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
            pygame.display.flip()
            frame_count += 1
            if args.frames and frame_count >= args.frames:
                running = False
            continue

        if scene == "menu":
            screen.fill((6, 8, 14))
            nebula.draw(screen, cam)
            starfield.draw(screen, cam)
            title = font_big.render("A P H E L I O N", True, (140, 235, 255))
            screen.blit(title, (size[0] // 2 - title.get_width() // 2, 150))
            sub = font.render(
                "a hard-realism solar-system program  ·  2049", True,
                (110, 122, 140))
            screen.blit(sub, (size[0] // 2 - sub.get_width() // 2, 205))
            items = (["NEW CAMPAIGN"]
                     + (["CONTINUE"] if qs_path.exists() else [])
                     + ["QUIT"])
            menu_rects = []
            for i, label in enumerate(items):
                sel = i == menu_cursor % len(items)
                color = (255, 215, 130) if sel else (200, 210, 224)
                txt = font_med.render(("> " if sel else "  ") + label, True,
                                      color)
                pos = (size[0] // 2 - 110, 300 + i * 36)
                screen.blit(txt, pos)
                menu_rects.append(pygame.Rect(pos[0], pos[1] - 4, 280, 30))
            foot = font.render(
                "arrows + ENTER or click  ·  F11 fullscreen  ·  M mute  ·  "
                "ESC quit", True, (110, 122, 140))
            screen.blit(foot, (size[0] // 2 - foot.get_width() // 2,
                               size[1] - 60))
            bloom.apply(screen)
            screen.blit(vig, (0, 0))
            pygame.display.flip()
            frame_count += 1
            if args.frames and frame_count >= args.frames:
                running = False
            continue

        # armed-node warp guard (01 §3.6): step down so the burn lands on time
        if node is not None and node["armed"]:
            while (warp_idx > 0
                   and node["t_node"] - t < _WARP_LADDER[warp_idx] * 5.0):
                warp_idx -= 1
        if not paused and not pause_open:
            clock.advance_analytic(clock.t + _WARP_LADDER[warp_idx] * real_dt)
        t = clock.t
        av = vessels[active_idx % len(vessels)] if vessels else None
        # node execution at its instant (the plan IS the burn at rails fidelity)
        if node is not None and node["armed"] and t >= node["t_node"]:
            if av is not None and av.burn(node["t_node"], node["dvp"],
                                          node["dvr"]):
                toast = (f"NODE EXECUTED: {math.hypot(node['dvp'], node['dvr']):,.0f}"
                         f" m/s")
                burn_glow = 0.8
                audio.play("burn")
            else:
                toast = "NODE FAILED: insufficient propellant"
                audio.play("alarm")
            toast_until = t + 6
            node = None
        # the whole fleet flies: SOI handoffs + first-entry science
        for fv in vessels:
            for note in fv.advance_to(t):
                toast, toast_until = f"SOI {note}", t + 8
            if fv.frame_id not in visited:
                visited.add(fv.frame_id)
                sci = (_FIRST_ENTRY_SCIENCE.get(fv.frame_id, 200.0)
                       * science_multiplier(fv, crew))
                research.earn_science(sci)
                research.earn_eng_data(sci * 0.25)
                toast = (f"FIRST ENTRY: {fv.frame_id.split(':')[1]} "
                         f"+{sci:.0f} science ({fv.name})")
                toast_until = t + 10
                audio.play("soi")

        # the Act table sweeps REAL state: offers, payouts, the win
        from aphelion.game.campaign import sweep as campaign_sweep
        sweep_state = {"vessels": vessels, "bases": bases, "visited": visited,
                       "visited_surface": visited_surface,
                       "milestones": milestones, "research": research}
        sweep_toasts, won_now = campaign_sweep(program, sweep_state, t)
        for line in sweep_toasts:
            toast, toast_until = line, t + 10
            audio.play("paid" if "PAID" in line else "blip")
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
            for cname, member in crew.items():
                loc = aboard.get(cname, "core:earth")
                if loc not in AMBIENT_MSV_DAY:
                    loc = "deep_space"
                shield = 20.0 if cname in aboard else 1_000.0
                member.dose.accrue(loc, days, areal_g_cm2=shield,
                                   material="water")
            # operating bases generate engineering data (11: ops currency)
            if bases:
                research.earn_eng_data(2.0 * days * len(bases))
            last_dose_t = t
            for fv in vessels:
                for ev_txt in fv.tick_lss(t):
                    toast, toast_until = ev_txt, t + 10
                    audio.play("alarm")
                    if "EXHAUSTED" in ev_txt:
                        for cname in list(crew):
                            if cname in ev_txt:
                                del crew[cname]
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
            for ev in site.advance(t):
                if ev.kind == "module_failed":
                    toast, toast_until = f"{site.name}: {ev.subject} FAILED — bot dispatched", t + 8
                    audio.play("alarm")
                elif ev.kind == "repaired":
                    toast, toast_until = f"{site.name}: {ev.subject} repaired", t + 6
                    audio.play("blip")

        # tutorial rail (12 §5.8): completes from real state
        legs_now = av.predict(t) if av is not None else []
        if tutorial.update({
            "builder_open": builder_open,
            "in_orbit": av is not None,
            "warp_idx": warp_idx,
            "apo_m": ((av.elements.apoapsis - tree.body(av.frame_id).radius)
                      if av is not None and av.elements.alpha > 0 else 0.0),
            "moon_leg": any(leg.frame_id == "core:moon" for leg in legs_now),
            "frame": av.frame_id if av is not None else "",
        }):
            audio.play("blip")

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
            draw_conic(screen, tree.body(pid).elements, cam, _ORBIT_COLOR)
        sun_px = cam.world_to_screen(0.0, 0.0)
        if -400 < sun_px[0] < size[0] + 400 and -400 < sun_px[1] < size[1] + 400:
            sd = max(10, min(int(2.0 * tree.body("core:sun").radius * cam.zoom),
                             512))
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
                screen.blit(font.render(pid.split(":")[1], True, (150, 160, 180)),
                            (ppx[0] + 8, ppx[1] - 8))
                body_click_pts.append((ppx[0], ppx[1], focus_of_body[pid]))
            for mid in moons_of.get(pid, []):
                mel = tree.body(mid).elements
                draw_conic(screen, mel, cam, _MOON_ORBIT_COLOR, origin=(prx, pry))
                mrx, mry, _, _ = tree.state_in_parent(mid, t)
                mpx = cam.world_to_screen(prx + mrx, pry + mry)
                if (2.0 * abs(mel.a) * cam.zoom > 8.0
                        and -60 < mpx[0] < size[0] + 60 and -60 < mpx[1] < size[1] + 60):
                    blit_body(mid, prx + mrx, pry + mry, mpx)
                    screen.blit(font.render(mid.split(":")[1], True, (120, 130, 150)),
                                (mpx[0] + 7, mpx[1] - 7))
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

        # node preview: post-burn legs in magenta + node marker
        if node is not None and av is not None:
            from aphelion.sim.flight.node_exec import ManeuverNode, apply_node_impulsive
            try:
                post = apply_node_impulsive(
                    av.elements,
                    ManeuverNode(node["t_node"], node["dvp"], node["dvr"]))
                node_legs = predict_trajectory(tree, av.frame_id, post,
                                               node["t_node"], _PREDICT_HORIZON)
                for leg in node_legs:
                    lfx, lfy = body_root(leg.frame_id)
                    r_soi_l = tree.body(leg.frame_id).soi_radius
                    draw_conic(screen, leg.elements, cam, (255, 120, 220),
                               r_max=r_soi_l if math.isfinite(r_soi_l) else None,
                               origin=(lfx, lfy))
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
            state_txt = "ARMED" if node["armed"] else "editing"
            screen.blit(font.render(
                f"NODE [{state_txt}] T-{max(0.0, node['t_node'] - t):,.0f} s   "
                f"prograde {node['dvp']:+,.0f}  radial {node['dvr']:+,.0f}  "
                f"({math.hypot(node['dvp'], node['dvr']):,.0f} m/s)",
                True, (255, 120, 220)), (10, size[1] - 48))

        # the fleet: active vessel gets trajectory legs + big icon; the
        # rest draw as dim markers with names (click to take command)
        vessel_click_pts = []
        if av is not None:
            for i, leg in enumerate(av.predict(t)):
                frx, fry = body_root(leg.frame_id)
                r_soi = tree.body(leg.frame_id).soi_radius
                r_max = r_soi if math.isfinite(r_soi) else None
                draw_conic(screen, leg.elements, cam,
                           _LEG_COLORS[i % len(_LEG_COLORS)],
                           r_max=r_max, origin=(frx, fry))
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

        hud1 = (f"t {t / SECONDS_PER_DAY:9.3f} d   warp {_WARP_LADDER[warp_idx]:>9,.0f}x"
                f"{'  [PAUSED]' if paused else ''}   focus: {focus.split(':')[-1]}"
                f"   fleet: {len(vessels)}")
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
        hud3 = (f"${program.funds/1e6:,.0f}M   sci {research.science:,.0f}"
                f"  ed {research.eng_data:,.0f}"
                f"   dose {worst_frac:.0%}   "
                + (" | ".join(c.description[:30] for c in open_contracts[:3])
                   or "no open contracts"))
        screen.blit(theme.panel(size[0], 76), (0, 0))
        for icon_name, line, yy, color in (
                ("clock", hud1, 8, theme.COLORS["text"]),
                ("dv", hud2, 28, _CRAFT_COLOR),
                ("funds", hud3, 48, theme.COLORS["gold"])):
            screen.blit(theme.icon(icon_name, 14), (10, yy + 1))
            theme.draw_text(screen, 30, yy, line, color=color)
        if t < toast_until and toast:
            up = toast.upper()
            kind = ("paid" if ("PAID" in up or "QUICKSAVE" in up or "ORBIT" in up)
                    else "alarm" if any(w in up for w in (
                        "WARNING", "FAILED", "INSUFFICIENT", "LOSS", "CANNOT",
                        "NEEDS", "EXCEEDS", "NO QUICK"))
                    else "science" if ("FIRST ENTRY" in up or "RESEARCHED" in up)
                    else "info")
            ts = theme.toast_surface(toast, kind)
            screen.blit(ts, (size[0] // 2 - ts.get_width() // 2, 84))

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

        screen.blit(theme.panel(size[0], 26), (0, size[1] - 26))
        theme.draw_text(
            screen, 10, size[1] - 21,
            "X/Z A/D burn  B build  N node  V ship  E dock  U undock  "
            "T crossfeed  R research  G base  F2 base  F5/F9 save  "
            "TAB/click focus  ./, warp  ESC menu",
            color=theme.COLORS["text_dim"], font="small", shadow=False)

        particles.update_draw(screen, real_dt)
        if tutorial.visible and tutorial.current_text:
            tut = font.render(tutorial.current_text, True, (140, 235, 255))
            tbg = pygame.Surface((tut.get_width() + 20, 24), pygame.SRCALPHA)
            tbg.fill((10, 16, 28, 180))
            tx = size[0] // 2 - tut.get_width() // 2
            screen.blit(tbg, (tx - 10, 116))
            screen.blit(tut, (tx, 120))

        if base_screen and bases:
            from aphelion.game.basebuild import CATALOG, catalog_for_kind
            site_b = bases[base_idx % len(bases)]
            site_def = SITES[site_b.site_id]
            _, rates, f_power = site_b.net.solve_rates()
            avail = catalog_for_kind(site_def["kind"])
            n_left = 5 + len(site_b.net.modules)
            n_right = len(avail)
            ph = 110 + 24 * max(n_left, n_right + 1)
            bpanel = theme.panel(440, ph, f"{site_b.name} — OPERATIONS")
            screen.blit(bpanel, (size[0] - 904, 80))
            cpanel = theme.panel(440, ph, "CONSTRUCT (funds-built)")
            screen.blit(cpanel, (size[0] - 454, 80))
            bx, by = size[0] - 888, 116
            theme.draw_text(screen, bx, by,
                            f"{site_def['name']}  ·  sun x{site_def['solar']:.2f}"
                            + (f"  ·  base {base_idx + 1}/{len(bases)} (TAB)"
                               if len(bases) > 1 else ""),
                            color=theme.COLORS["text_dim"], font="small")
            by += 24
            res_icons = {"Water": "water", "Oxygen": "oxygen",
                         "Hydrogen": "hydrogen", "Methane": "tank",
                         "CO2": "signal"}
            for res in ("Water", "Oxygen", "Hydrogen", "Methane", "CO2"):
                buf = site_b.net.buffers.get(res)
                if buf is None:
                    continue
                rate = rates.get(res, 0.0)
                frac = min(1.0, buf.level / max(buf.capacity, 1e-9))
                screen.blit(theme.icon(res_icons[res], 14), (bx, by))
                screen.blit(theme.bar(140, 10, frac, theme.COLORS["good"]),
                            (bx + 22, by + 2))
                theme.draw_text(
                    screen, bx + 172, by,
                    f"{buf.level/1e3:7.1f} t {rate * 86_400.0 / 1e3:+6.2f} t/d",
                    color=theme.COLORS["text"], font="small")
                by += 22
            by += 6
            for m in site_b.net.modules:
                color = {"RUNNING": theme.COLORS["good"],
                         "FAILED": theme.COLORS["danger"],
                         "STARVED": theme.COLORS["warn"],
                         "BLOCKED": theme.COLORS["warn"],
                         "OFF": theme.COLORS["text_dim"]}.get(
                             m.state, theme.COLORS["text"])
                pygame.draw.circle(screen, color, (bx + 6, by + 8), 4)
                theme.draw_text(screen, bx + 20, by,
                                f"{m.module_id:18s} {m.state}", color=color,
                                font="small")
                by += 22
            screen.blit(theme.icon("power", 14), (bx, by + 2))
            theme.draw_text(
                screen, bx + 22, by + 2,
                f"power f={f_power:.2f}   repairs pending: "
                f"{len(site_b.pending_repairs)}",
                color=theme.COLORS["accent"], font="small")

            cx, cy = size[0] - 438, 116
            for i, key in enumerate(avail):
                spec = CATALOG[key]
                sel = i == base_cursor % len(avail)
                locked = (spec["tech"] is not None
                          and spec["tech"] not in research.unlocked)
                color = (theme.COLORS["text_dim"] if locked
                         else theme.COLORS["gold"] if sel
                         else theme.COLORS["text"])
                pw = spec["power_kw"]
                pw_txt = (f"+{-pw:,.0f} kW" if pw < 0 else f"{pw:,.0f} kW")
                theme.draw_text(
                    screen, cx, cy + i * 24,
                    f"{'>' if sel else ' '} {spec['name'][:28]:29s}"
                    f"${spec['price_m']:>4,.0f}M  {pw_txt}"
                    + ("  LOCKED" if locked else ""),
                    color=color, font="small")
            theme.draw_text(
                screen, cx, cy + len(avail) * 24 + 8,
                "UP/DOWN pick   ENTER build   TAB next base   F2 close",
                color=theme.COLORS["text_dim"], font="small")

        if builder_open:
            dimmer = pygame.Surface(size, pygame.SRCALPHA)
            dimmer.fill((6, 9, 16, 242))
            screen.blit(dimmer, (0, 0))
            screen.blit(theme.panel(560, size[1] - 80, "PART CATALOG"),
                        (16, 16))
            screen.blit(theme.panel(360, size[1] - 80, "STACK"), (592, 16))
            screen.blit(theme.panel(296, size[1] - 80, "VESSEL"), (968, 16))
            rows_fit = (size[1] - 150) // 30
            top = max(0, min(builder.cursor - rows_fit // 2,
                             len(builder.catalog) - rows_fit))
            for i, pid in enumerate(builder.catalog):
                if i < top or i >= top + rows_fit:
                    continue
                p = db.parts[pid]
                locked = builder.locked(pid)
                ry = 54 + (i - top) * 30
                if i == builder.cursor:
                    hi = pygame.Surface((540, 28), pygame.SRCALPHA)
                    hi.fill((140, 235, 255, 26))
                    screen.blit(hi, (26, ry - 2))
                screen.blit(part_thumb(p, pid, 26), (32, ry))
                tcol = (theme.COLORS["text_dim"] if locked
                        else theme.COLORS["text"])
                theme.draw_text(screen, 66, ry + 4, p["name"][:46], color=tcol,
                                font="small")
                screen.blit(theme.chip(p["tier"], theme.COLORS["accent"]),
                            (470, ry + 2))
                if locked:
                    screen.blit(theme.icon("lock", 14), (530, ry + 5))
            sx0 = 608
            yy = 54
            vessel = builder.build_vessel()
            stats = vessel.stage_stats() if vessel else []
            for si, stage in enumerate(builder.stack):
                stat = stats[si] if si < len(stats) else None
                line = f"STAGE {si + 1}: " + (
                    f"dv {stat['dv_vac']:,.0f} m/s  TWR {stat['twr']:.2f}"
                    if stat else "(empty)")
                theme.draw_text(screen, sx0, yy, line,
                                color=theme.COLORS["accent"], font="small")
                yy += 20
                for pid in stage:
                    p = db.parts[pid]
                    screen.blit(part_thumb(p, pid, 18), (sx0 + 6, yy))
                    theme.draw_text(screen, sx0 + 30, yy + 2,
                                    p["name"][:32],
                                    color=theme.COLORS["text"], font="small")
                    yy += 22
                yy += 8
            if vessel:
                total_dv = sum(s["dv_vac"] for s in stats)
                cost = builder.price(vessel)
                for ci, (txt, col) in enumerate((
                        (f"dv {total_dv:,.0f} m/s", theme.COLORS["good"]),
                        (f"{vessel.total_mass_kg()/1e3:,.1f} t",
                         theme.COLORS["accent"]),
                        (f"${cost/1e6:,.0f}M of ${program.funds/1e6:,.0f}M",
                         theme.COLORS["gold"] if cost <= program.funds
                         else theme.COLORS["danger"]))):
                    screen.blit(theme.chip(txt, col), (sx0, size[1] - 132 + ci * 26))
                vspr = vessel_sprite(db, builder.stack)
                vx = 968 + (296 - vspr.get_width()) // 2
                vy = 54 + max(0, (size[1] - 150 - vspr.get_height()) // 2)
                screen.blit(vspr, (vx, vy))
            theme.draw_text(screen, 24, size[1] - 52, builder.message,
                            color=theme.COLORS["accent"])
            theme.draw_text(
                screen, 24, size[1] - 30,
                "UP/DOWN browse   ENTER add   S new stage   BACKSPACE remove   "
                "L launch   B/ESC close", color=theme.COLORS["text_dim"],
                font="small", shadow=False)

        if surface_open and av is not None:
            opts = _surface_options(av, bases)
            n_rows = max(len(opts), 1)
            spanel = theme.panel(620, 96 + 30 * n_rows, "SURFACE OPERATIONS")
            spx, spy = size[0] // 2 - 310, 140
            screen.blit(spanel, (spx, spy))
            if not opts:
                theme.draw_text(screen, spx + 16, spy + 40,
                                f"no surveyed sites at "
                                f"{av.frame_id.split(':')[1]} — explore on",
                                color=theme.COLORS["text_dim"])
            for i, (action, label) in enumerate(opts):
                sel = i == surface_cursor % len(opts)
                color = theme.COLORS["gold"] if sel else theme.COLORS["text"]
                theme.draw_text(screen, spx + 16, spy + 38 + i * 30,
                                ("> " if sel else "  ") + label, color=color)
            if opts:
                action = opts[surface_cursor % len(opts)][0]
                blurb = ""
                if action[0] == "land":
                    blurb = SITES[action[1]]["blurb"]
                elif av.landed_at:
                    blurb = SITES[av.landed_at]["blurb"]
                theme.draw_text(screen, spx + 16,
                                spy + 96 + 30 * (n_rows - 1), blurb,
                                color=theme.COLORS["accent"], font="small")

        if crew_open:
            cands = candidates(crew)
            roster = list(crew.items())
            ph = 130 + 30 * (len(roster) + len(cands))
            kp = theme.panel(640, ph, "CREW ROSTER & HIRING")
            kx, ky = size[0] // 2 - 320, 100
            screen.blit(kp, (kx, ky))
            yy = ky + 36
            aboard_names = {n for v in vessels for n in v.crew}
            for cname, member in roster:
                screen.blit(theme.portrait(cname, 24), (kx + 14, yy - 2))
                where = next((v.name for v in vessels if cname in v.crew),
                             "Earth")
                frac = member.dose.career_fraction
                theme.draw_text(
                    screen, kx + 48, yy,
                    f"{cname:18s} {member.role:9s} skill {member.skill}   "
                    f"dose {frac:5.0%}   {where}",
                    color=(theme.COLORS["accent"] if cname in aboard_names
                           else theme.COLORS["text"]), font="small")
                yy += 30
            yy += 8
            theme.draw_text(screen, kx + 14, yy,
                            "CANDIDATES — ENTER hires (boards next launch):",
                            color=theme.COLORS["gold"], font="small")
            yy += 26
            for i, cand in enumerate(cands):
                sel = i == crew_cursor % len(cands) if cands else False
                theme.draw_text(
                    screen, kx + 14, yy,
                    f"{'>' if sel else ' '} {cand.name:18s} "
                    f"{cand.role:9s} skill {cand.skill}   "
                    f"${cand.hire_cost/1e6:,.0f}M",
                    color=(theme.COLORS["gold"] if sel
                           else theme.COLORS["text"]), font="small")
                yy += 30
            theme.draw_text(
                screen, kx + 14, yy + 4,
                "pilots cut docking cost · engineers stretch life support · "
                "scientists multiply science", color=theme.COLORS["text_dim"],
                font="small")

        if research_open:
            tech_ids = _tech_order(db)
            px0, py0 = size[0] // 2 - 330, 110
            screen.blit(theme.panel(660, 120 + 24 * len(tech_ids), "RESEARCH"),
                        (px0, py0))
            screen.blit(theme.icon("science", 16), (px0 + 16, py0 + 34))
            theme.draw_text(
                screen, px0 + 38, py0 + 34,
                f"science {research.science:,.0f}   eng data "
                f"{research.eng_data:,.0f}   —   ENTER unlock, R close",
                color=theme.COLORS["accent"], font="small")
            yy = py0 + 62
            for i, nid in enumerate(tech_ids):
                nd = db.tech[nid]
                unlocked = nid in research.unlocked
                can = research.can_unlock(db, nid)
                sel = i == research_cursor % len(tech_ids)
                color = ((120, 255, 170) if unlocked
                         else (255, 215, 130) if can else (110, 122, 140))
                state = ("UNLOCKED" if unlocked else
                         f"{nd.get('cost_sci', 0):,.0f} sci / "
                         f"{nd.get('cost_ed', 0):,.0f} ed")
                screen.blit(font.render(
                    f"{'>' if sel else ' '} {nd['tier']:3s} "
                    f"{nd['name'][:36]:37s} {state}", True, color),
                    (px0 + 16, yy))
                yy += 24
            sel_nid = tech_ids[research_cursor % len(tech_ids)]
            unl = ", ".join(p.split(":")[1]
                            for p in db.tech[sel_nid].get("unlocks", [])) or "—"
            pre = ", ".join(p.split(":")[1]
                            for p in db.tech[sel_nid]["prereqs"]) or "none"
            screen.blit(font.render(f"unlocks: {unl}   prereqs: {pre}",
                                    True, (200, 210, 224)), (px0 + 16, yy + 4))

        if pause_open:
            dim = pygame.Surface(size, pygame.SRCALPHA)
            dim.fill((4, 6, 10, 170))
            screen.blit(dim, (0, 0))
            ppan = theme.panel(340, 80 + 34 * len(_PAUSE_ITEMS), "PAUSED")
            ppx = size[0] // 2 - 170
            ppy = 200
            screen.blit(ppan, (ppx, ppy))
            for i, label in enumerate(_PAUSE_ITEMS):
                sel = i == pause_cursor
                color = theme.COLORS["gold"] if sel else theme.COLORS["text"]
                txt = font_med.render(("> " if sel else "  ") + label, True,
                                      color)
                screen.blit(txt, (ppx + 28, ppy + 48 + i * 34))

        bloom.apply(screen)
        screen.blit(vig, (0, 0))
        pygame.display.flip()
        frame_count += 1
        if args.frames and frame_count >= args.frames:
            running = False

    if args.screenshot:
        pygame.image.save(screen, args.screenshot)
    pygame.quit()
    return 0


if __name__ == "__main__":
    sys.exit(run())
