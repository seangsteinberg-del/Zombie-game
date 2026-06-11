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
    """A rails craft: elements in a frame, re-expressed at SOI crossings."""

    def __init__(self, tree, frame_id: str, elements) -> None:
        self.tree = tree
        self.frame_id = frame_id
        self.elements = elements
        self.legs = []
        self._legs_t0 = -1.0

    def state(self, t: float):
        return elements_to_state(self.elements, t)

    def burn(self, t: float, dv_prograde: float, dv_radial: float) -> None:
        rx, ry, vx, vy = self.state(t)
        v = math.hypot(vx, vy)
        r = math.hypot(rx, ry)
        if v == 0.0 or r == 0.0:
            return
        px, py = vx / v, vy / v
        ux, uy = rx / r, ry / r
        nvx = vx + dv_prograde * px + dv_radial * ux
        nvy = vy + dv_prograde * py + dv_radial * uy
        mu = self.tree.body(self.frame_id).mu
        self.elements = state_to_elements(rx, ry, nvx, nvy, t, mu)
        self._legs_t0 = -1.0          # invalidate prediction

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
    research = ResearchState()
    visited = {"core:earth"}

    starfield = Starfield(size)
    particles = Particles()
    audio = AudioCues()
    tutorial = first_flight_tutorial()

    frame_count = 0
    running = True
    while running:
        real_dt = pygame_clock.tick(60) / 1000.0
        t = clock.t
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                shift = event.mod & pygame.KMOD_SHIFT
                step = 100.0 if shift else 10.0
                if event.key == pygame.K_ESCAPE:
                    running = False
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
                    craft.burn(t, *dvp)
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
        hud2 = (f"CRAFT @ {craft.frame_id.split(':')[1]}   alt {alt/1e3:,.0f} km   "
                f"v {math.hypot(cvx, cvy):,.0f} m/s   "
                f"peri {peri/1e3:,.0f} km   apo {apo/1e3:,.0f} km   e {el.e:.4f}")
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
            "X/Z prograde±  A/D radial±  (shift=100)  C craft  TAB focus  ./, warp  F1 tutorial",
            True, (110, 120, 135)), (10, size[1] - 24))

        particles.update_draw(screen, real_dt)
        if tutorial.visible and tutorial.current_text:
            tut = font.render(tutorial.current_text, True, (140, 235, 255))
            screen.blit(tut, (size[0] // 2 - tut.get_width() // 2, 86))

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
