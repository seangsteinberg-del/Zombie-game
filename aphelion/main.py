"""APHELION — playable orbital sandbox (Phases 0-2 engine, flyable).

You fly a craft starting in LEO-300. Burns are applied along your current
velocity (prograde/retrograde) or radially; the predicted patched-conic
trajectory — across up to 5 SOI transitions — is drawn live ahead of you.
Warp through an encounter and the sim re-expresses your orbit in the new
frame exactly as the planner predicted (same math, by construction).

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


class Craft:
    """A rails craft: elements in a frame, re-expressed at SOI crossings.
    Burns spend a finite dv budget — the budget your launched design earned
    (06: the builder's Tsiolkovsky readout is the law)."""

    def __init__(self, tree, frame_id: str, elements,
                 dv_budget: float = 5_000.0, name: str = "Pathfinder-0") -> None:
        self.tree = tree
        self.frame_id = frame_id
        self.elements = elements
        self.dv_remaining = dv_budget
        self.name = name
        self.legs = []
        self._legs_t0 = -1.0

    def state(self, t: float):
        return elements_to_state(self.elements, t)

    def burn(self, t: float, dv_prograde: float, dv_radial: float) -> bool:
        cost = math.hypot(dv_prograde, dv_radial)
        if cost > self.dv_remaining:
            return False
        rx, ry, vx, vy = self.state(t)
        v = math.hypot(vx, vy)
        r = math.hypot(rx, ry)
        if v == 0.0 or r == 0.0:
            return False
        px, py = vx / v, vy / v
        ux, uy = rx / r, ry / r
        nvx = vx + dv_prograde * px + dv_radial * ux
        nvy = vy + dv_prograde * py + dv_radial * uy
        mu = self.tree.body(self.frame_id).mu
        self.elements = state_to_elements(rx, ry, nvx, nvy, t, mu)
        self.dv_remaining -= cost
        self._legs_t0 = -1.0          # invalidate prediction
        return True

    def predict(self, t: float):
        if self._legs_t0 < 0.0 or abs(t - self._legs_t0) > 600.0:
            self.legs = predict_trajectory(
                self.tree, self.frame_id, self.elements, t, _PREDICT_HORIZON)
            self._legs_t0 = t
        return self.legs

    def advance_to(self, t: float) -> list[str]:
        """Follow predicted legs through any SOI crossings up to time t."""
        notes: list[str] = []
        for _ in range(8):
            legs = self.predict(max(self._legs_t0, 0.0) if self._legs_t0 >= 0 else t)
            current = None
            for leg in legs:
                if leg.t_start <= t < leg.t_end or leg is legs[-1]:
                    current = leg
                    if leg.t_start <= t:
                        break
            if current is None:
                break
            if current.frame_id != self.frame_id or current.elements != self.elements:
                if t >= current.t_start:
                    self.frame_id = current.frame_id
                    self.elements = current.elements
                    notes.append(f"frame -> {current.frame_id.split(':')[1]}")
                    self._legs_t0 = -1.0
                    continue
            break
        return notes


class BaseSite:
    """A founded surface base: a live ledger network advanced to sim time
    every frame (warp-exact by construction), failures pre-rolled, repairs
    on a 48 h maintenance turnaround (Phase 3 acceptance machinery)."""

    REPAIR_TURNAROUND = 48.0 * 3_600.0

    def __init__(self, name: str, t_founded: float, rng) -> None:
        from aphelion.sim.habitat.lsc import oga_electrolysis
        from aphelion.sim.ledger.network import LedgerNetwork, Module, Source
        self.name = name
        self.last_t = t_founded
        self.events: list = []
        self.pending_repairs: list[tuple[float, str]] = []
        net = LedgerNetwork(rng=rng)
        net.add_buffer("Water", 200.0, 50_000.0)
        net.add_buffer("Oxygen", 0.0, 200_000.0)
        net.add_buffer("Hydrogen", 0.0, 20_000.0)
        net.add_source(Source("psr_ice", "Water", 0.03, remaining=1.0e6))
        net.add_source(Source("h2_vent", "Hydrogen", -0.005))
        oga = oga_electrolysis(rate_o2_kgps=0.02, power_kw=80.0)
        oga.mtbf_s = 45.0 * 86_400.0
        net.add_module(oga)
        net.add_module(Module("reactor", inputs={}, outputs={}, rate_kgps=0.0,
                              power_kw=-120.0))
        self.net = net

    @classmethod
    def from_restore(cls, name: str, last_t: float,
                     pending_repairs: list, net) -> "BaseSite":
        site = cls.__new__(cls)
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
             if p["type"] in ("engine", "tank", "structure")])
        self.cursor = 0
        self.stack: list[list[str]] = [[]]    # stages, bottom first
        self.message = "ENTER add part | S new stage | BACKSPACE remove | L launch | B close"

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
                                 "research"])
    args = parser.parse_args(argv)
    if args.headless:
        os.environ["SDL_VIDEODRIVER"] = "dummy"
        os.environ["SDL_AUDIODRIVER"] = "dummy"

    import pygame
    from aphelion.render.draw_conics import draw_conic
    from aphelion.ui.audio import AudioCues
    from aphelion.ui.effects import Particles, Starfield
    from aphelion.ui.tutorial import first_flight_tutorial

    from aphelion.core.rng import RngRegistry
    from aphelion.save.campaign import (
        default_save_dir, read_campaign, snapshot_campaign, write_campaign)
    from aphelion.sim.habitat.dose import AMBIENT_MSV_DAY, CrewDose

    db, tree = load_solar_system()
    planets = sorted((i for i, b in db.bodies.items() if b["parent"] == "core:sun"),
                     key=lambda i: db.bodies[i]["elements"]["a_m"])
    moons_of = {i: tree.children(i) for i in planets}

    pygame.init()
    size = (1280, 720)
    fullscreen = False
    screen = pygame.display.set_mode(size, pygame.SCALED | pygame.DOUBLEBUF,
                                     vsync=0 if args.headless else 1)
    pygame.display.set_caption("APHELION")
    pygame_clock = pygame.time.Clock()
    font = pygame.font.SysFont("consolas", 14)
    font_med = pygame.font.SysFont("consolas", 18, bold=True)
    font_big = pygame.font.SysFont("consolas", 44, bold=True)

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
        """A brand-new 2049 campaign (12 §3: the Act 1 opening state)."""
        mu_e = tree.body("core:earth").mu
        r_leo = 6.678e6
        craft = Craft(tree, "core:earth",
                      state_to_elements(r_leo, 0.0, 0.0,
                                        tr.circular_speed(mu_e, r_leo),
                                        0.0, mu_e))
        program = Program(funds=150_000_000.0)
        program.offer(Contract("c_moon", "Reach the Moon's SOI",
                               payout=80_000_000.0, deadline_s=120 * 86_400.0))
        program.offer(Contract("c_helio", "Achieve heliocentric orbit",
                               payout=120_000_000.0, deadline_s=365 * 86_400.0))
        program.offer(Contract("c_base", "Found a lunar surface base (G in Moon SOI)",
                               payout=150_000_000.0, deadline_s=2 * 365 * 86_400.0))
        program.offer(Contract("c_lox", "Bank 100 t of lunar LOX",
                               payout=200_000_000.0, deadline_s=4 * 365 * 86_400.0))
        program.offer(Contract("c_mars", "Reach the Mars SOI",
                               payout=300_000_000.0, deadline_s=6 * 365 * 86_400.0))
        program.offer(Contract("c_venus", "Reach the Venus SOI",
                               payout=250_000_000.0, deadline_s=6 * 365 * 86_400.0))
        return dict(clock=SimClock(t0=0.0), craft=craft, program=program,
                    rng=RngRegistry(20490101), bases=[],
                    crew={"V. Ainsworth": CrewDose(), "J. Okafor": CrewDose()},
                    research=ResearchState(), visited={"core:earth"},
                    tutorial=first_flight_tutorial())

    def loaded_campaign() -> dict:
        got = read_campaign(qs_path)
        craft = Craft(tree, got["craft_frame"], got["craft_elements"],
                      dv_budget=got["craft_dv"], name=got["craft_name"])
        tut = first_flight_tutorial()
        tut.completed = got["tutorial_done"]
        rng = (RngRegistry.from_state(got["rng_state"]) if got["rng_state"]
               else RngRegistry(20490101))
        for b in got["bases"]:
            b["net"].rng = rng      # resume the SAME failure streams
        return dict(clock=SimClock(t0=got["t"]), craft=craft,
                    program=got["program"], rng=rng,
                    bases=[BaseSite.from_restore(b["name"], b["last_t"],
                                                 b["pending_repairs"], b["net"])
                           for b in got["bases"]],
                    crew=got["crew"], research=got["research"],
                    visited=got["visited"], tutorial=tut)

    def campaign_tuple(st: dict):
        """One unpack shape for new game, quickload, and startup."""
        return (st["clock"], st["craft"], st["program"], st["rng"],
                st["bases"], st["crew"], st["research"], st["visited"],
                st["tutorial"], Builder(db, st["research"]),
                None, 0, False, False, False, False, False, 0.0, "", 0.0)

    (clock, craft, program, campaign_rng, bases, crew, research, visited,
     tutorial, builder, node, warp_idx, paused, base_screen, builder_open,
     research_open, crew_warned, last_dose_t, toast, toast_until) = \
        campaign_tuple(fresh_campaign())

    def do_quicksave() -> str:
        snap = snapshot_campaign(
            t=clock.t, craft_frame=craft.frame_id,
            craft_elements=craft.elements, craft_dv=craft.dv_remaining,
            craft_name=craft.name, program=program, research=research,
            crew=crew, visited=visited, bases=bases,
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

    menu_cursor = 0
    menu_rects: list = []
    pause_open = False
    pause_cursor = 0
    research_cursor = 0
    body_click_pts: list = []

    frame_count = 0
    running = True
    while running:
        real_dt = pygame_clock.tick(60) / 1000.0
        t = clock.t
        start_new = False
        load_save = False
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
                            from aphelion.sim.flight.ascent import AscentParams, fly_ascent
                            res = fly_ascent(vessel, "core:earth",
                                             tree.body("core:earth").mu,
                                             tree.body("core:earth").radius,
                                             86_164.1, AscentParams())
                            if res.reached_orbit:
                                budget = sum(s["dv_vac"] for s in vessel.stage_stats())
                                mu_e2 = tree.body("core:earth").mu
                                r_orb = tree.body("core:earth").radius + res.periapsis_m
                                craft = Craft(tree, "core:earth",
                                              state_to_elements(
                                                  r_orb, 0.0, 0.0,
                                                  tr.circular_speed(mu_e2, r_orb),
                                                  t, mu_e2),
                                              dv_budget=budget,
                                              name=f"Vessel-{len(program.history)}")
                                builder.message = (f"ORBIT! {res.dv_integrated:,.0f} m/s spent; "
                                                   f"{budget:,.0f} m/s on-orbit budget")
                                toast, toast_until = builder.message, t + 10
                                audio.play("paid")
                                builder_open = False
                            else:
                                builder.message = "LOSS OF VEHICLE on ascent (see design TWR)"
                                audio.play("alarm")
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
                        if need > craft.dv_remaining:
                            toast, toast_until = "node exceeds dv budget", t + 5
                            audio.play("alarm")
                        else:
                            node["armed"] = True
                            toast, toast_until = ("node ARMED — warp on; burn "
                                                  "executes on time"), t + 6
                            audio.play("blip")
                elif event.key == pygame.K_F2:
                    base_screen = not base_screen
                elif event.key == pygame.K_g:
                    if craft.frame_id != "core:moon":
                        toast, toast_until = "Base founding needs the Moon SOI", t + 5
                        audio.play("alarm")
                    elif bases:
                        toast, toast_until = "Base already founded (F2 to view)", t + 5
                    elif not craft.burn(t, -1_900.0, 0.0):
                        toast, toast_until = ("Landing needs 1,900 m/s of dv "
                                              "budget"), t + 6
                        audio.play("alarm")
                    else:
                        bases.append(BaseSite("Peary Base", t, campaign_rng))
                        if program.complete(t, "c_base"):
                            toast = "PEARY BASE FOUNDED — CONTRACT PAID +$150M (F2 to view)"
                        else:
                            toast = "PEARY BASE FOUNDED (F2 to view)"
                        toast_until = t + 10
                        audio.play("paid")
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
                elif event.key in (pygame.K_x, pygame.K_z, pygame.K_a, pygame.K_d):
                    dvp = {pygame.K_x: (+step, 0.0), pygame.K_z: (-step, 0.0),
                           pygame.K_a: (0.0, +step), pygame.K_d: (0.0, -step)}[event.key]
                    crx0, cry0, cvx0, cvy0 = craft.state(t)
                    if not craft.burn(t, *dvp):
                        toast = "INSUFFICIENT dv — build a new vessel (B)"
                        toast_until = t + 6
                        audio.play("alarm")
                        continue
                    names = {pygame.K_x: "prograde +", pygame.K_z: "retrograde -",
                             pygame.K_a: "radial-out +", pygame.K_d: "radial-in -"}
                    toast = f"{names[event.key]}{step:.0f} m/s"
                    toast_until = t + 5
                    audio.play("burn")
                    frx0, fry0, _, _ = tree.state_in_root(craft.frame_id, t)
                    px0 = cam.world_to_screen(frx0 + crx0, fry0 + cry0)
                    v0n = math.hypot(cvx0, cvy0) or 1.0
                    # exhaust plume opposes the dv direction (screen y flips)
                    sgn = -1.0 if event.key == pygame.K_x else 1.0
                    particles.emit_burn(px0[0], px0[1],
                                        sgn * cvx0 / v0n, -sgn * cvy0 / v0n)
            elif (event.type == pygame.MOUSEBUTTONDOWN and event.button == 1
                  and not (pause_open or builder_open or research_open)):
                mx, my = event.pos
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
            (clock, craft, program, campaign_rng, bases, crew, research,
             visited, tutorial, builder, node, warp_idx, paused, base_screen,
             builder_open, research_open, crew_warned, last_dose_t, toast,
             toast_until) = campaign_tuple(fresh_campaign())
            scene, pause_open, focus_idx = "flight", False, 0
        if load_save:
            if qs_path.exists():
                (clock, craft, program, campaign_rng, bases, crew, research,
                 visited, tutorial, builder, node, warp_idx, paused,
                 base_screen, builder_open, research_open, crew_warned,
                 last_dose_t, toast, toast_until) = \
                    campaign_tuple(loaded_campaign())
                scene, pause_open, focus_idx = "flight", False, 0
                toast, toast_until = "QUICKSAVE LOADED", clock.t + 5.0
            else:
                toast, toast_until = "no quicksave found", t + 4.0

        if scene == "menu":
            screen.fill((6, 8, 14))
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
        # node execution at its instant (the plan IS the burn at rails fidelity)
        if node is not None and node["armed"] and t >= node["t_node"]:
            if craft.burn(node["t_node"], node["dvp"], node["dvr"]):
                toast = (f"NODE EXECUTED: {math.hypot(node['dvp'], node['dvr']):,.0f}"
                         f" m/s")
                audio.play("burn")
            else:
                toast = "NODE FAILED: insufficient dv"
                audio.play("alarm")
            toast_until = t + 6
            node = None
        for note in craft.advance_to(t):
            toast, toast_until = f"SOI {note}", t + 8
        # campaign hooks: first-entry science + contract completion
        if craft.frame_id not in visited:
            visited.add(craft.frame_id)
            sci = _FIRST_ENTRY_SCIENCE.get(craft.frame_id, 200.0)
            research.earn_science(sci)
            research.earn_eng_data(sci * 0.25)
            toast = f"FIRST ENTRY: {craft.frame_id.split(':')[1]} +{sci:.0f} science"
            toast_until = t + 10
            audio.play("soi")
            if craft.frame_id == "core:moon" and program.complete(t, "c_moon"):
                toast += "  |  CONTRACT PAID +$80M"
                audio.play("paid")
            if craft.frame_id == "core:sun" and program.complete(t, "c_helio"):
                toast += "  |  CONTRACT PAID +$120M"
                audio.play("paid")
        program.expire_overdue(t)

        # crew dose accrual (08): real location rates; 20 g/cm2 hull water-
        # equivalent shielding assumed for the crewed craft
        if t - last_dose_t > 3_600.0:
            days = (t - last_dose_t) / 86_400.0
            loc = craft.frame_id if craft.frame_id in AMBIENT_MSV_DAY else "deep_space"
            for member in crew.values():
                member.accrue(loc, days, areal_g_cm2=20.0, material="water")
            # operating bases generate engineering data (11: ops currency)
            if bases:
                research.earn_eng_data(2.0 * days * len(bases))
            last_dose_t = t
            worst = max(crew.values(), key=lambda c: c.career_fraction)
            if worst.career_fraction > 0.8 and not crew_warned:
                crew_warned = True
                toast = (f"CREW DOSE WARNING: {worst.career_fraction:.0%} of "
                         f"career limit — get them home")
                toast_until = t + 10
                audio.play("alarm")

        # contract sweep for the planetary arcs
        if craft.frame_id == "core:mars" and program.complete(t, "c_mars"):
            toast, toast_until = "MARS SOI — CONTRACT PAID +$300M", t + 10
            audio.play("paid")
        if craft.frame_id == "core:venus" and program.complete(t, "c_venus"):
            toast, toast_until = "VENUS SOI — CONTRACT PAID +$250M", t + 10
            audio.play("paid")

        # bases tick on the ledger (warp-exact); LOX contract watches stores
        for site in bases:
            for ev in site.advance(t):
                if ev.kind == "module_failed":
                    toast, toast_until = f"{site.name}: {ev.subject} FAILED — bot dispatched", t + 8
                    audio.play("alarm")
                elif ev.kind == "repaired":
                    toast, toast_until = f"{site.name}: {ev.subject} repaired", t + 6
                    audio.play("blip")
            if (site.net.buffers["Oxygen"].level >= 100_000.0
                    and program.complete(t, "c_lox")):
                toast = "100 t LUNAR LOX BANKED — CONTRACT PAID +$200M"
                toast_until = t + 10
                audio.play("paid")

        # tutorial rail (12 §5.8): completes from real state
        legs_now = craft.predict(t)
        if tutorial.update({
            "warp_idx": warp_idx,
            "apo_m": (craft.elements.apoapsis
                      - tree.body(craft.frame_id).radius
                      if craft.elements.alpha > 0 else 0.0),
            "moon_leg": any(leg.frame_id == "core:moon" for leg in legs_now),
            "frame": craft.frame_id,
        }):
            audio.play("blip")

        # camera follow (positions in ROOT frame; camera frame is the root)
        def body_root(bid: str) -> tuple[float, float]:
            rx, ry, _, _ = tree.state_in_root(bid, t)
            return rx, ry

        focus = focus_order[focus_idx]
        if focus == "craft":
            frx, fry = body_root(craft.frame_id)
            crx, cry, _, _ = craft.state(t)
            cam.follow(frx + crx, fry + cry)
        elif focus == "core:sun":
            cam.follow(0.0, 0.0)
        else:
            cam.follow(*body_root(focus))

        screen.fill((6, 8, 14))
        starfield.draw(screen, cam)
        body_click_pts = []

        for pid in planets:
            draw_conic(screen, tree.body(pid).elements, cam, _ORBIT_COLOR)
        sun_px = cam.world_to_screen(0.0, 0.0)
        pygame.draw.circle(screen, _BODY_COLORS["core:sun"], sun_px, 5)
        for pid in planets:
            prx, pry = body_root(pid)
            ppx = cam.world_to_screen(prx, pry)
            on_screen = -60 < ppx[0] < size[0] + 60 and -60 < ppx[1] < size[1] + 60
            if on_screen:
                pygame.draw.circle(screen, _BODY_COLORS.get(pid, _DEFAULT_COLOR), ppx, 3)
                screen.blit(font.render(pid.split(":")[1], True, (150, 160, 180)),
                            (ppx[0] + 6, ppx[1] - 6))
                body_click_pts.append((ppx[0], ppx[1], focus_of_body[pid]))
            for mid in moons_of.get(pid, []):
                mel = tree.body(mid).elements
                draw_conic(screen, mel, cam, _MOON_ORBIT_COLOR, origin=(prx, pry))
                mrx, mry, _, _ = tree.state_in_parent(mid, t)
                mpx = cam.world_to_screen(prx + mrx, pry + mry)
                if (2.0 * abs(mel.a) * cam.zoom > 8.0
                        and -60 < mpx[0] < size[0] + 60 and -60 < mpx[1] < size[1] + 60):
                    pygame.draw.circle(screen, _BODY_COLORS.get(mid, _DEFAULT_COLOR), mpx, 2)
                    screen.blit(font.render(mid.split(":")[1], True, (120, 130, 150)),
                                (mpx[0] + 5, mpx[1] - 5))
                    body_click_pts.append((mpx[0], mpx[1], focus_of_body[mid]))

        # node preview: post-burn legs in magenta + node marker
        if node is not None:
            from aphelion.sim.flight.node_exec import ManeuverNode, apply_node_impulsive
            try:
                post = apply_node_impulsive(
                    craft.elements,
                    ManeuverNode(node["t_node"], node["dvp"], node["dvr"]))
                node_legs = predict_trajectory(tree, craft.frame_id, post,
                                               node["t_node"], _PREDICT_HORIZON)
                for leg in node_legs:
                    lfx, lfy = body_root(leg.frame_id)
                    r_soi_l = tree.body(leg.frame_id).soi_radius
                    draw_conic(screen, leg.elements, cam, (255, 120, 220),
                               r_max=r_soi_l if math.isfinite(r_soi_l) else None,
                               origin=(lfx, lfy))
                nfx, nfy = body_root(craft.frame_id)
                nx, ny, _, _ = elements_to_state(craft.elements, node["t_node"])
                npx = cam.world_to_screen(nfx + nx, nfy + ny)
                pygame.draw.circle(screen, (255, 120, 220), npx, 5, width=2)
            except Exception:
                pass
            state_txt = "ARMED" if node["armed"] else "editing"
            screen.blit(font.render(
                f"NODE [{state_txt}] T-{max(0.0, node['t_node'] - t):,.0f} s   "
                f"prograde {node['dvp']:+,.0f}  radial {node['dvr']:+,.0f}  "
                f"({math.hypot(node['dvp'], node['dvr']):,.0f} m/s)",
                True, (255, 120, 220)), (10, size[1] - 48))

        # craft: predicted legs + marker
        for i, leg in enumerate(craft.predict(t)):
            frx, fry = body_root(leg.frame_id)
            r_soi = tree.body(leg.frame_id).soi_radius
            r_max = r_soi if math.isfinite(r_soi) else None
            draw_conic(screen, leg.elements, cam,
                       _LEG_COLORS[i % len(_LEG_COLORS)],
                       r_max=r_max, origin=(frx, fry))
        frx, fry = body_root(craft.frame_id)
        crx, cry, cvx, cvy = craft.state(t)
        cpx = cam.world_to_screen(frx + crx, fry + cry)
        pygame.draw.circle(screen, _CRAFT_COLOR, cpx, 3)
        body_click_pts.append((cpx[0], cpx[1], 0))

        el = craft.elements
        body = tree.body(craft.frame_id)
        alt = math.hypot(crx, cry) - body.radius
        hud1 = (f"t = {t / SECONDS_PER_DAY:9.3f} d   warp {_WARP_LADDER[warp_idx]:>9,.0f}x"
                f"{'  [PAUSED]' if paused else ''}   focus: {focus.split(':')[-1]}   "
                f"zoom {cam.zoom:.2e}")
        peri = el.periapsis - body.radius
        apo = (el.apoapsis - body.radius) if el.alpha > 0 else float("inf")
        hud2 = (f"{craft.name} @ {craft.frame_id.split(':')[1]}   "
                f"alt {alt/1e3:,.0f} km   v {math.hypot(cvx, cvy):,.0f} m/s   "
                f"peri {peri/1e3:,.0f} km   apo {apo/1e3:,.0f} km   "
                f"dv {craft.dv_remaining:,.0f} m/s")
        screen.blit(font.render(hud1, True, (190, 200, 215)), (10, 8))
        screen.blit(font.render(hud2, True, _CRAFT_COLOR), (10, 28))
        open_contracts = [c for c in program.contracts
                          if c.completed_t is None and not c.failed]
        worst_dose = max(crew.values(), key=lambda c: c.career_fraction)
        hud3 = (f"PROGRAM  ${program.funds/1e6:,.0f}M   sci {research.science:,.0f}"
                f"  ed {research.eng_data:,.0f}"
                f"   crew dose {worst_dose.career_fraction:.0%}   contracts: "
                + (" | ".join(c.description[:28] for c in open_contracts[:3])
                   or "none"))
        screen.blit(font.render(hud3, True, (255, 215, 130)), (10, 48))
        if t < toast_until and toast:
            screen.blit(font.render(toast, True, (255, 230, 140)), (10, 68))
        screen.blit(font.render(
            "X/Z A/D burn  B build  N node  R research  G base  F2 base view  "
            "F5/F9 save/load  TAB/click focus  ./, warp  ESC menu",
            True, (110, 120, 135)), (10, size[1] - 24))

        particles.update_draw(screen, real_dt)
        if tutorial.visible and tutorial.current_text:
            tut = font.render(tutorial.current_text, True, (140, 235, 255))
            screen.blit(tut, (size[0] // 2 - tut.get_width() // 2, 86))

        if base_screen and bases:
            site = bases[0]
            panel = pygame.Surface((430, 230), pygame.SRCALPHA)
            panel.fill((8, 14, 24, 225))
            screen.blit(panel, (size[0] - 444, 90))
            bx, by = size[0] - 430, 100
            screen.blit(font.render(f"{site.name} — live ledger (F2 hide)",
                                    True, (255, 215, 130)), (bx, by))
            by += 22
            _, rates, f_power = site.net.solve_rates()
            for res in ("Water", "Oxygen", "Hydrogen"):
                buf = site.net.buffers[res]
                rate = rates.get(res, 0.0)
                frac = min(1.0, buf.level / buf.capacity)
                pygame.draw.rect(screen, (40, 50, 70), (bx, by + 4, 200, 10))
                pygame.draw.rect(screen, (120, 255, 170),
                                 (bx, by + 4, int(200 * frac), 10))
                screen.blit(font.render(
                    f"{res:9s} {buf.level/1e3:8.1f} t  "
                    f"{rate * 86_400.0 / 1e3:+6.2f} t/d", True,
                    (190, 200, 215)), (bx + 210, by))
                by += 22
            for m in site.net.modules:
                color = {"RUNNING": (120, 255, 170), "FAILED": (255, 110, 110),
                         "STARVED": (255, 200, 90), "BLOCKED": (255, 200, 90),
                         "OFF": (120, 130, 150)}.get(m.state, (200, 200, 200))
                screen.blit(font.render(f"{m.module_id:14s} {m.state}",
                                        True, color), (bx, by))
                by += 18
            screen.blit(font.render(
                f"power OK (f={f_power:.2f})   repairs pending: "
                f"{len(site.pending_repairs)}", True, (140, 235, 255)),
                (bx, by + 4))

        if builder_open:
            panel = pygame.Surface(size, pygame.SRCALPHA)
            panel.fill((8, 12, 20, 235))
            screen.blit(panel, (0, 0))
            screen.blit(font.render(
                "ENGINEER — VESSEL ASSEMBLY (12 §5.4)", True, (240, 240, 250)),
                (20, 16))
            top = builder.cursor - 10
            for i, pid in enumerate(builder.catalog):
                if i < top or i > top + 24:
                    continue
                p = db.parts[pid]
                locked = builder.locked(pid)
                color = (90, 95, 105) if locked else (200, 210, 220)
                marker = ">" if i == builder.cursor else " "
                lock = " [LOCKED]" if locked else ""
                screen.blit(font.render(
                    f"{marker} {p['tier']}  {p['name'][:42]}{lock}",
                    True, color), (20, 48 + (i - max(top, 0)) * 18))
            vx0 = 660
            screen.blit(font.render("STACK (bottom stage first):", True,
                                    (255, 215, 130)), (vx0, 48))
            yy = 70
            vessel = builder.build_vessel()
            stats = vessel.stage_stats() if vessel else []
            for si, stage in enumerate(builder.stack):
                stat = stats[si] if si < len(stats) else None
                line = f"STAGE {si + 1}: " + (
                    f"dv {stat['dv_vac']:,.0f} m/s  TWR {stat['twr']:.2f}"
                    if stat else "(empty)")
                screen.blit(font.render(line, True, (140, 235, 255)), (vx0, yy))
                yy += 18
                for pid in stage:
                    screen.blit(font.render("   " + pid.split(":")[1], True,
                                            (190, 200, 215)), (vx0, yy))
                    yy += 16
                yy += 6
            if vessel:
                total_dv = sum(s["dv_vac"] for s in stats)
                cost = builder.price(vessel)
                screen.blit(font.render(
                    f"TOTAL dv {total_dv:,.0f} m/s   mass "
                    f"{vessel.total_mass_kg()/1e3:,.1f} t   price ${cost/1e6:,.0f}M"
                    f"   funds ${program.funds/1e6:,.0f}M",
                    True, (255, 230, 140)), (vx0, yy + 6))
            screen.blit(font.render(builder.message, True, (140, 235, 255)),
                        (20, size[1] - 48))

        if research_open:
            tech_ids = _tech_order(db)
            panel = pygame.Surface((660, 90 + 24 * len(tech_ids)),
                                   pygame.SRCALPHA)
            panel.fill((8, 12, 22, 235))
            px0, py0 = size[0] // 2 - 330, 110
            screen.blit(panel, (px0, py0))
            screen.blit(font_med.render(
                "RESEARCH — ENTER unlock, R close", True, (255, 215, 130)),
                (px0 + 16, py0 + 10))
            screen.blit(font.render(
                f"science {research.science:,.0f}   eng data "
                f"{research.eng_data:,.0f}", True, (140, 235, 255)),
                (px0 + 16, py0 + 34))
            yy = py0 + 58
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
            ttl = font_big.render("PAUSED", True, (140, 235, 255))
            screen.blit(ttl, (size[0] // 2 - ttl.get_width() // 2, 180))
            for i, label in enumerate(_PAUSE_ITEMS):
                sel = i == pause_cursor
                color = (255, 215, 130) if sel else (200, 210, 224)
                txt = font_med.render(("> " if sel else "  ") + label, True,
                                      color)
                screen.blit(txt, (size[0] // 2 - 130, 280 + i * 34))

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
