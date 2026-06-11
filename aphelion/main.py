"""APHELION — playable orbital sandbox (Phases 0-2 engine, flyable).

You fly a craft starting in LEO-300. Burns are applied along your current
velocity (prograde/retrograde) or radially; the predicted patched-conic
trajectory — across up to 5 SOI transitions — is drawn live ahead of you.
Warp through an encounter and the sim re-expresses your orbit in the new
frame exactly as the planner predicted (same math, by construction).

Controls
  . / ,        warp up / down            space   pause
  TAB / S-TAB  focus next / prev body    C       focus your craft
  X / Z        +10 / -10 m/s prograde    A / D   +10 / -10 m/s radial
  (hold shift for 100 m/s steps)         wheel   zoom
  ESC          quit

Dev flags: --frames N  --screenshot PATH  --headless
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
    args = parser.parse_args(argv)
    if args.headless:
        os.environ["SDL_VIDEODRIVER"] = "dummy"
        os.environ["SDL_AUDIODRIVER"] = "dummy"

    import pygame
    from aphelion.render.draw_conics import draw_conic
    from aphelion.ui.audio import AudioCues
    from aphelion.ui.effects import Particles, Starfield
    from aphelion.ui.tutorial import first_flight_tutorial

    db, tree = load_solar_system()
    planets = sorted((i for i, b in db.bodies.items() if b["parent"] == "core:sun"),
                     key=lambda i: db.bodies[i]["elements"]["a_m"])
    moons_of = {i: tree.children(i) for i in planets}

    mu_e = tree.body("core:earth").mu
    r_leo = 6.678e6
    craft = Craft(tree, "core:earth",
                  state_to_elements(r_leo, 0.0, 0.0,
                                    tr.circular_speed(mu_e, r_leo), 0.0, mu_e))

    pygame.init()
    size = (1280, 720)
    screen = pygame.display.set_mode(size, pygame.SCALED | pygame.DOUBLEBUF,
                                     vsync=0 if args.headless else 1)
    pygame.display.set_caption("APHELION")
    pygame_clock = pygame.time.Clock()
    font = pygame.font.SysFont("consolas", 14)

    clock = SimClock(t0=0.0)
    warp_idx = 0
    paused = False
    cam = Camera(*size, frame_id="core:earth", zoom=3.0e-5, layer=ZoomLayer.LOCAL)
    focus_order = ["craft", "core:sun"] + planets
    focus_idx = 0
    toast = ""
    toast_until = 0.0

    # -- campaign layer (12/11): funds, contracts, exploration science --
    program = Program(funds=150_000_000.0)
    program.offer(Contract("c_moon", "Reach the Moon's SOI",
                           payout=80_000_000.0, deadline_s=120 * 86_400.0))
    program.offer(Contract("c_helio", "Achieve heliocentric orbit",
                           payout=120_000_000.0, deadline_s=365 * 86_400.0))
    program.offer(Contract("c_base", "Found a lunar surface base (G in Moon SOI)",
                           payout=150_000_000.0, deadline_s=2 * 365 * 86_400.0))
    program.offer(Contract("c_lox", "Bank 100 t of lunar LOX",
                           payout=200_000_000.0, deadline_s=4 * 365 * 86_400.0))
    from aphelion.core.rng import RngRegistry
    campaign_rng = RngRegistry(20490101)
    bases: list[BaseSite] = []
    base_screen = False
    research = ResearchState()
    visited = {"core:earth"}

    starfield = Starfield(size)
    particles = Particles()
    audio = AudioCues()
    tutorial = first_flight_tutorial()
    builder = Builder(db, research)
    builder_open = False

    frame_count = 0
    running = True
    while running:
        real_dt = pygame_clock.tick(60) / 1000.0
        t = clock.t
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
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
                    running = False
                elif event.key == pygame.K_b:
                    builder_open = True
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
            elif event.type == pygame.MOUSEWHEEL:
                if event.y > 0:
                    cam.zoom_in(event.y)
                elif event.y < 0:
                    cam.zoom_out(-event.y)

        if not paused:
            clock.advance_analytic(clock.t + _WARP_LADDER[warp_idx] * real_dt)
        t = clock.t
        for note in craft.advance_to(t):
            toast, toast_until = f"SOI {note}", t + 8
        # campaign hooks: first-entry science + contract completion
        if craft.frame_id not in visited:
            visited.add(craft.frame_id)
            sci = _FIRST_ENTRY_SCIENCE.get(craft.frame_id, 200.0)
            research.earn_science(sci)
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
        hud3 = (f"PROGRAM  ${program.funds/1e6:,.0f}M   science {research.science:,.0f}"
                f"   contracts open: "
                + (" | ".join(c.description for c in open_contracts) or "none"))
        screen.blit(font.render(hud3, True, (255, 215, 130)), (10, 48))
        if t < toast_until and toast:
            screen.blit(font.render(toast, True, (255, 230, 140)), (10, 68))
        screen.blit(font.render(
            "X/Z prograde±  A/D radial±  (shift=100)  B builder  C craft  TAB focus  ./, warp  F1 tutorial",
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
