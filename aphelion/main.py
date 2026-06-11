"""APHELION entry point — Phase 0 orbital sandbox.

The real solar system: 37 canon bodies loaded from data/core/bodies (the
03-solar-system.md tables), validated at launch, propagated on rails by the
universal-variable Kepler engine. Moons render around their primaries; the
demo craft rides an Earth->Mars transfer ellipse.

Controls: . / ,  warp up/down | space pause | wheel zoom | TAB / Shift+TAB
focus next/prev body | ESC quit.

Dev flags: --frames N (exit after N frames), --screenshot PATH (save last
frame), --headless (SDL dummy driver).
"""

from __future__ import annotations

import argparse
import math
import os
import sys

from aphelion.core.clock import RAILS_RATES, SimClock
from aphelion.core.units import AU, SECONDS_PER_DAY
from aphelion.render.camera import Camera, ZoomLayer
from aphelion.sim.orbits.ephemeris import load_solar_system
from aphelion.sim.orbits.kepler import elements_to_state, state_to_elements

MU_SUN = 1.32712440018e20

_BODY_COLORS = {
    "core:sun": (255, 220, 120), "core:mercury": (140, 130, 120),
    "core:venus": (230, 200, 140), "core:earth": (90, 140, 255),
    "core:moon": (170, 170, 175), "core:mars": (230, 110, 70),
    "core:jupiter": (220, 180, 140), "core:saturn": (230, 210, 160),
    "core:uranus": (160, 210, 220), "core:neptune": (110, 140, 230),
    "core:pluto": (200, 180, 170), "core:europa": (200, 190, 170),
    "core:titan": (220, 170, 90), "core:io": (210, 190, 110),
}
_DEFAULT_COLOR = (130, 135, 145)
_ORBIT_COLOR = (40, 50, 70)
_MOON_ORBIT_COLOR = (55, 65, 85)
_WARP_LADDER = (1.0,) + RAILS_RATES


def build_demo_craft():
    """Heliocentric Earth->Mars transfer ellipse (perihelion 1 AU)."""
    a_t = 0.5 * (1.0 + 1.5237) * AU
    vp = math.sqrt(MU_SUN * (2.0 / AU - 1.0 / a_t))
    return state_to_elements(AU, 0.0, 0.0, vp, 0.0, MU_SUN)


def run(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="aphelion")
    parser.add_argument("--frames", type=int, default=0)
    parser.add_argument("--screenshot", type=str, default="")
    parser.add_argument("--headless", action="store_true")
    args = parser.parse_args(argv)

    if args.headless:
        os.environ["SDL_VIDEODRIVER"] = "dummy"

    import pygame
    from aphelion.render.draw_conics import draw_conic

    db, tree = load_solar_system()
    planets = sorted(
        (i for i, b in db.bodies.items() if b["parent"] == "core:sun"),
        key=lambda i: db.bodies[i]["elements"]["a_m"])
    moons_of = {i: tree.children(i) for i in planets}
    craft = build_demo_craft()

    pygame.init()
    size = (1280, 720)
    screen = pygame.display.set_mode(size, pygame.SCALED | pygame.DOUBLEBUF,
                                     vsync=0 if args.headless else 1)
    pygame.display.set_caption("APHELION")
    pygame_clock = pygame.time.Clock()
    font = pygame.font.SysFont("consolas", 14)

    clock = SimClock(t0=0.0)
    warp_idx = 3
    paused = False
    cam = Camera(*size, frame_id="core:sun", zoom=1.2e-9, layer=ZoomLayer.SYSTEM)
    focus_order = ["core:sun"] + planets
    focus_idx = 0

    frame_count = 0
    running = True
    while running:
        real_dt = pygame_clock.tick(60) / 1000.0
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_SPACE:
                    paused = not paused
                elif event.key == pygame.K_PERIOD:
                    warp_idx = min(warp_idx + 1, len(_WARP_LADDER) - 1)
                elif event.key == pygame.K_COMMA:
                    warp_idx = max(warp_idx - 1, 0)
                elif event.key == pygame.K_TAB:
                    step = -1 if event.mod & pygame.KMOD_SHIFT else 1
                    focus_idx = (focus_idx + step) % len(focus_order)
            elif event.type == pygame.MOUSEWHEEL:
                if event.y > 0:
                    cam.zoom_in(event.y)
                elif event.y < 0:
                    cam.zoom_out(-event.y)

        if not paused:
            clock.advance_analytic(clock.t + _WARP_LADDER[warp_idx] * real_dt)
        t = clock.t

        focus = focus_order[focus_idx]
        if focus == "core:sun":
            cam.follow(0.0, 0.0)
        else:
            fx, fy, _, _ = tree.state_in_parent(focus, t)
            cam.follow(fx, fy)

        screen.fill((6, 8, 14))

        # planet orbits + bodies
        for pid in planets:
            draw_conic(screen, tree.body(pid).elements, cam, _ORBIT_COLOR)
        draw_conic(screen, craft, cam, (255, 200, 60))

        sun_px = cam.world_to_screen(0.0, 0.0)
        pygame.draw.circle(screen, _BODY_COLORS["core:sun"], sun_px, 5)
        for pid in planets:
            rx, ry, _, _ = tree.state_in_parent(pid, t)
            px = cam.world_to_screen(rx, ry)
            if -60 < px[0] < size[0] + 60 and -60 < px[1] < size[1] + 60:
                color = _BODY_COLORS.get(pid, _DEFAULT_COLOR)
                pygame.draw.circle(screen, color, px, 3)
                screen.blit(font.render(pid.split(":")[1], True, (150, 160, 180)),
                            (px[0] + 6, px[1] - 6))
            # moons render around their primary (visible when zoomed in)
            for mid in moons_of.get(pid, []):
                mel = tree.body(mid).elements
                draw_conic(screen, mel, cam, _MOON_ORBIT_COLOR, origin=(rx, ry))
                mrx, mry, _, _ = tree.state_in_parent(mid, t)
                mpx = cam.world_to_screen(rx + mrx, ry + mry)
                if (2.0 * abs(mel.a) * cam.zoom > 8.0
                        and -60 < mpx[0] < size[0] + 60
                        and -60 < mpx[1] < size[1] + 60):
                    pygame.draw.circle(screen, _BODY_COLORS.get(mid, _DEFAULT_COLOR),
                                       mpx, 2)
                    screen.blit(font.render(mid.split(":")[1], True, (120, 130, 150)),
                                (mpx[0] + 5, mpx[1] - 5))

        crx, cry, _, _ = elements_to_state(craft, t)
        cpx = cam.world_to_screen(crx, cry)
        pygame.draw.circle(screen, (255, 200, 60), cpx, 2)

        hud = (f"t = {t / SECONDS_PER_DAY:9.2f} d   warp {_WARP_LADDER[warp_idx]:>9,.0f}x"
               f"{'  [PAUSED]' if paused else ''}   focus: {focus.split(':')[1]}   "
               f"zoom {cam.zoom:.2e} px/m   bodies: {len(db.bodies)}")
        screen.blit(font.render(hud, True, (190, 200, 215)), (10, 8))
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
