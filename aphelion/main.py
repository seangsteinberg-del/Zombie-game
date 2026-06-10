"""APHELION entry point — Phase 0 orbital sandbox (work in progress).

Current state: SYSTEM-layer view of a PROVISIONAL solar system (placeholder
elements with real NASA semi-major axes/eccentricities; replaced by the
data/core/bodies content pack once canon lands), rails time with the 01 §3.6
warp ladder, wheel zoom, body focus cycling.

Controls: . / ,  warp up/down | space pause | wheel zoom | TAB focus next
body | ESC quit.

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
from aphelion.sim.orbits.frames import Body, FrameTree
from aphelion.sim.orbits.kepler import Elements, elements_to_state, state_to_elements
from aphelion.sim.orbits.soi import soi_radius

MU_SUN = 1.327_124_400_18e20

# (name, a_m, e, varpi_rad, mu, radius_m, mass_kg, color)
_PROVISIONAL_PLANETS = [
    ("mercury", 5.7909e10, 0.2056, 1.35, 2.2032e13, 2.4397e6, 3.301e23, (140, 130, 120)),
    ("venus",   1.0821e11, 0.0068, 2.30, 3.24859e14, 6.0518e6, 4.867e24, (230, 200, 140)),
    ("earth",   1.495978707e11, 0.0167, 1.79, 3.986004418e14, 6.371e6, 5.972e24, (90, 140, 255)),
    ("mars",    2.2794e11, 0.0934, 5.87, 4.282837e13, 3.3895e6, 6.417e23, (230, 110, 70)),
    ("jupiter", 7.7857e11, 0.0489, 0.25, 1.26686534e17, 6.9911e7, 1.898e27, (220, 180, 140)),
    ("saturn",  1.43353e12, 0.0565, 1.62, 3.7931187e16, 5.8232e7, 5.683e26, (230, 210, 160)),
    ("uranus",  2.87246e12, 0.0457, 2.98, 5.793939e15, 2.5362e7, 8.681e25, (160, 210, 220)),
    ("neptune", 4.49506e12, 0.0113, 0.78, 6.836529e15, 2.4622e7, 1.024e26, (110, 140, 230)),
]
M_SUN = 1.989e30


def build_provisional_system() -> FrameTree:
    tree = FrameTree()
    tree.add(Body("sun", MU_SUN, 6.957e8, None, None, math.inf))
    for name, a, e, varpi, mu, radius, mass, _ in _PROVISIONAL_PLANETS:
        alpha = 1.0 / a
        el = Elements(mu=MU_SUN, alpha=alpha, e=e, varpi=varpi, tau=0.0, s=1.0)
        tree.add(Body(name, mu, radius, "sun", el, soi_radius(a, mass, M_SUN)))
    return tree


def build_demo_craft() -> Elements:
    """A heliocentric Earth->Mars transfer ellipse (perihelion 1 AU)."""
    a_t = 0.5 * (1.0 + 1.5237) * AU
    rp = AU
    vp = math.sqrt(MU_SUN * (2.0 / rp - 1.0 / a_t))
    return state_to_elements(rp, 0.0, 0.0, vp, 0.0, MU_SUN)


_BODY_COLORS = {name: color for name, *_, color in
                [(p[0], *p[1:]) for p in _PROVISIONAL_PLANETS]}
_WARP_LADDER = (1.0,) + RAILS_RATES


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

    pygame.init()
    size = (1280, 720)
    screen = pygame.display.set_mode(size, pygame.SCALED | pygame.DOUBLEBUF, vsync=0 if args.headless else 1)
    pygame_clock = pygame.time.Clock()
    font = pygame.font.SysFont("consolas", 14)

    tree = build_provisional_system()
    craft = build_demo_craft()
    clock = SimClock(t0=0.0)
    warp_idx = 3                                  # 100x to make motion visible
    paused = False

    cam = Camera(*size, frame_id="sun", zoom=1.2e-9, layer=ZoomLayer.SYSTEM)
    focus_order = ["sun"] + [p[0] for p in _PROVISIONAL_PLANETS]
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
                    focus_idx = (focus_idx + 1) % len(focus_order)
            elif event.type == pygame.MOUSEWHEEL:
                if event.y > 0:
                    cam.zoom_in(event.y)
                elif event.y < 0:
                    cam.zoom_out(-event.y)

        if not paused:
            clock.advance_analytic(clock.t + _WARP_LADDER[warp_idx] * real_dt)
        t = clock.t

        focus = focus_order[focus_idx]
        if focus == "sun":
            cam.follow(0.0, 0.0)
        else:
            fx, fy, _, _ = tree.state_in_parent(focus, t)
            cam.follow(fx, fy)

        screen.fill((6, 8, 14))
        for name, *_rest in _PROVISIONAL_PLANETS:
            body = tree.body(name)
            draw_conic(screen, body.elements, cam, (40, 50, 70))
        draw_conic(screen, craft, cam, (255, 200, 60))

        sun_px = cam.world_to_screen(0.0, 0.0)
        pygame.draw.circle(screen, (255, 220, 120), sun_px, 5)
        for name, *_rest in _PROVISIONAL_PLANETS:
            rx, ry, _, _ = tree.state_in_parent(name, t)
            px = cam.world_to_screen(rx, ry)
            if -50 < px[0] < size[0] + 50 and -50 < px[1] < size[1] + 50:
                pygame.draw.circle(screen, _BODY_COLORS[name], px, 3)
                screen.blit(font.render(name, True, (150, 160, 180)),
                            (px[0] + 6, px[1] - 6))
        crx, cry, _, _ = elements_to_state(craft, t)
        cpx = cam.world_to_screen(crx, cry)
        pygame.draw.circle(screen, (255, 200, 60), cpx, 2)

        hud = (f"t = {t / SECONDS_PER_DAY:9.2f} d   warp {_WARP_LADDER[warp_idx]:>9,.0f}x"
               f"{'  [PAUSED]' if paused else ''}   focus: {focus}   "
               f"zoom {cam.zoom:.2e} px/m")
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
