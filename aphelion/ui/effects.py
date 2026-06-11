"""Visual juice (90-14): parallax starfield (cached layers) and burn
particles. CPU-cheap by construction — numpy SoA particles, pre-rendered
star surfaces, no per-frame allocation in the hot path.
"""

from __future__ import annotations

import math

import numpy as np
import pygame


class Starfield:
    """Two cached parallax layers; regenerated only on resize. The shift is
    camera-position-scaled and wraps, so it works at every zoom layer."""

    def __init__(self, size: tuple[int, int], seed: int = 7) -> None:
        self.size = size
        rng = np.random.default_rng(seed)
        self.layers: list[tuple[pygame.Surface, float]] = []
        for count, brightness, parallax in ((140, 90, 0.35), (70, 160, 0.7)):
            surf = pygame.Surface(size, pygame.SRCALPHA)
            xs = rng.uniform(0, size[0], count)
            ys = rng.uniform(0, size[1], count)
            for x, y in zip(xs, ys):
                b = int(brightness * rng.uniform(0.5, 1.0))
                surf.set_at((int(x), int(y)), (b, b, min(255, b + 20)))
            self.layers.append((surf, parallax))

    def draw(self, screen: pygame.Surface, cam) -> None:
        w, h = self.size
        # camera-proportional drift, wrapped; tiny factor keeps it subtle
        base_x = cam.cx * cam.zoom * 1e-3
        base_y = -cam.cy * cam.zoom * 1e-3
        for surf, parallax in self.layers:
            ox = int(-base_x * parallax) % w
            oy = int(-base_y * parallax) % h
            screen.blit(surf, (ox - w, oy - h))
            screen.blit(surf, (ox, oy - h))
            screen.blit(surf, (ox - w, oy))
            screen.blit(surf, (ox, oy))


class Particles:
    """Fixed-capacity SoA particle pool (13 §3.13: FX never allocate per
    frame). Additive micro-circles."""

    def __init__(self, cap: int = 512) -> None:
        self.cap = cap
        self.pos = np.zeros((cap, 2), dtype=np.float32)
        self.vel = np.zeros((cap, 2), dtype=np.float32)
        self.age = np.full(cap, 1.0e9, dtype=np.float32)
        self.life = np.ones(cap, dtype=np.float32)
        self.color = np.zeros((cap, 3), dtype=np.uint8)
        self._next = 0

    def emit_burn(self, x: float, y: float, dir_x: float, dir_y: float,
                  n: int = 14, color=(255, 200, 90)) -> None:
        # screen-space emitters can be handed huge/non-finite coords when
        # the camera is focused far from the craft — refuse those quietly
        if not (math.isfinite(x) and math.isfinite(y)
                and -1.0e4 < x < 1.0e4 and -1.0e4 < y < 1.0e4):
            return
        rng = np.random.default_rng(self._next)     # deterministic enough for FX
        for _ in range(n):
            i = self._next % self.cap
            self._next += 1
            ang = math.atan2(dir_y, dir_x) + rng.uniform(-0.5, 0.5)
            spd = rng.uniform(40.0, 140.0)
            self.pos[i] = (x, y)
            self.vel[i] = (math.cos(ang) * spd, math.sin(ang) * spd)
            self.age[i] = 0.0
            self.life[i] = rng.uniform(0.35, 0.8)
            self.color[i] = color

    def update_draw(self, screen: pygame.Surface, dt: float) -> None:
        self.age += dt
        alive = self.age < self.life
        if not alive.any():
            return
        self.pos[alive] += self.vel[alive] * dt
        self.vel[alive] *= (1.0 - 1.8 * dt)
        w, h = screen.get_width(), screen.get_height()
        for i in np.nonzero(alive)[0]:
            x = float(self.pos[i, 0])
            y = float(self.pos[i, 1])
            # pygame.draw.circle raises on non-finite / C-int-overflow
            # centers; anything in that regime is off-screen anyway
            if not (math.isfinite(x) and math.isfinite(y)
                    and -50.0 < x < w + 50.0 and -50.0 < y < h + 50.0):
                continue
            f = 1.0 - self.age[i] / self.life[i]
            c = (int(self.color[i, 0] * f), int(self.color[i, 1] * f),
                 int(self.color[i, 2] * f))
            r = max(1, int(2.5 * f))
            pygame.draw.circle(screen, c, (x, y), r)
