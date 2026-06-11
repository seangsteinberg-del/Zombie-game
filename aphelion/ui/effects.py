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


def _glow_sprite(radius: int) -> pygame.Surface:
    """White radial-gradient blob; tinted at blit time, stacked with
    BLEND_ADD so hot pixels saturate to white like real exhaust."""
    d = radius * 2 + 1
    surf = pygame.Surface((d, d), pygame.SRCALPHA)
    arr = pygame.surfarray.pixels3d(surf)
    alpha = pygame.surfarray.pixels_alpha(surf)
    yy, xx = np.mgrid[0:d, 0:d]
    r = np.hypot(xx - radius, yy - radius) / max(radius, 1)
    fall = np.clip(1.0 - r, 0.0, 1.0) ** 1.6
    arr[...] = 255
    alpha[...] = (fall * 255).astype(np.uint8)
    del arr, alpha
    return surf


class Particles:
    """Fixed-capacity SoA particle pool (13 §3.13: FX never allocate per
    frame). Flame particles blit pre-rendered radial glows with BLEND_ADD
    (they GLOW and stack to white); smoke draws normal grey puffs that
    drift and linger. A floor_y kills/deflects anything below the ground
    line, so launch exhaust pools at the pad instead of tunneling."""

    def __init__(self, cap: int = 1024) -> None:
        self.cap = cap
        self.pos = np.zeros((cap, 2), dtype=np.float32)
        self.vel = np.zeros((cap, 2), dtype=np.float32)
        self.age = np.full(cap, 1.0e9, dtype=np.float32)
        self.life = np.ones(cap, dtype=np.float32)
        self.color = np.zeros((cap, 3), dtype=np.uint8)
        self.smoke = np.zeros(cap, dtype=bool)
        self._next = 0
        self._glows = [_glow_sprite(r) for r in (2, 3, 4, 6)]
        self._tinted: dict[tuple, list[pygame.Surface]] = {}

    def _tint(self, color: tuple) -> list[pygame.Surface]:
        key = tuple(int(c) for c in color[:3])
        hit = self._tinted.get(key)
        if hit is None:
            hit = []
            for g in self._glows:
                s = g.copy()
                s.fill((*key, 255), special_flags=pygame.BLEND_RGBA_MULT)
                hit.append(s)
            if len(self._tinted) > 24:
                self._tinted.clear()
            self._tinted[key] = hit
        return hit

    def emit_burn(self, x: float, y: float, dir_x: float, dir_y: float,
                  n: int = 14, color=(255, 200, 90),
                  smoke: bool = False, spread: float = 0.5,
                  speed: tuple[float, float] = (40.0, 140.0),
                  life: tuple[float, float] = (0.35, 0.8)) -> None:
        # screen-space emitters can be handed huge/non-finite coords when
        # the camera is focused far from the craft — refuse those quietly
        if not (math.isfinite(x) and math.isfinite(y)
                and -1.0e4 < x < 1.0e4 and -1.0e4 < y < 1.0e4):
            return
        rng = np.random.default_rng(self._next)     # deterministic enough for FX
        for _ in range(n):
            i = self._next % self.cap
            self._next += 1
            ang = math.atan2(dir_y, dir_x) + rng.uniform(-spread, spread)
            spd = rng.uniform(*speed)
            self.pos[i] = (x, y)
            self.vel[i] = (math.cos(ang) * spd, math.sin(ang) * spd)
            self.age[i] = 0.0
            self.life[i] = rng.uniform(*life)
            self.color[i] = color
            self.smoke[i] = smoke

    def explosion(self, x: float, y: float, scale: float = 1.0) -> None:
        """The full pyrotechnic stack: white core, orange fire, slow smoke."""
        self.emit_burn(x, y, 0.0, -1.0, n=int(50 * scale),
                       color=(255, 244, 214), spread=math.pi,
                       speed=(60.0, 260.0), life=(0.3, 0.7))
        self.emit_burn(x, y, 0.0, -1.0, n=int(60 * scale),
                       color=(255, 140, 40), spread=math.pi,
                       speed=(30.0, 180.0), life=(0.5, 1.1))
        self.emit_burn(x, y, 0.0, -1.0, n=int(40 * scale),
                       color=(92, 92, 98), spread=math.pi,
                       speed=(15.0, 80.0), life=(1.2, 2.4), smoke=True)

    def update_draw(self, screen: pygame.Surface, dt: float,
                    floor_y: float | None = None) -> None:
        self.age += dt
        alive = self.age < self.life
        if not alive.any():
            return
        self.pos[alive] += self.vel[alive] * dt
        self.vel[alive] *= (1.0 - 1.8 * dt)
        if floor_y is not None:
            below = alive & (self.pos[:, 1] > floor_y)
            if below.any():
                # deflect along the ground: kill vertical, keep a sideways
                # billow with a touch of upward roll
                self.pos[below, 1] = floor_y
                side = np.sign(self.vel[below, 0])
                side[side == 0.0] = 1.0
                mag = np.hypot(self.vel[below, 0], self.vel[below, 1])
                self.vel[below, 0] = side * mag * 0.8
                self.vel[below, 1] = -mag * 0.12
        w, h = screen.get_width(), screen.get_height()
        for i in np.nonzero(alive)[0]:
            x = float(self.pos[i, 0])
            y = float(self.pos[i, 1])
            # pygame blits with non-finite / C-int-overflow centers crash;
            # anything in that regime is off-screen anyway
            if not (math.isfinite(x) and math.isfinite(y)
                    and -50.0 < x < w + 50.0 and -50.0 < y < h + 50.0):
                continue
            f = 1.0 - self.age[i] / self.life[i]
            if self.smoke[i]:
                c = tuple(int(v * (0.5 + 0.35 * f))
                          for v in self.color[i])
                r = max(1, int(3.5 * (1.25 - f)))
                pygame.draw.circle(screen, c, (x, y), r)
            else:
                sprites = self._tint(tuple(self.color[i]))
                idx = min(3, max(0, int(f * 4)))
                spr = sprites[idx]
                spr.set_alpha(int(255 * f))
                screen.blit(spr, (x - spr.get_width() // 2,
                                  y - spr.get_height() // 2),
                            special_flags=pygame.BLEND_ADD)
