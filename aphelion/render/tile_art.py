"""Tile-world rendering: the site cross-section as cached chunk surfaces
(32×32 tiles each), re-rendered only when a dig edits them. Strata read in
the body's ground palette; ice is pale blue, ore glints warm, bedrock is
near-black. Underground, a helmet-lamp overlay closes the dark in.
"""

from __future__ import annotations

import pygame

from aphelion.game.tileworld import (
    AIR, BEDROCK, H_TILES, ICE, ORE, REGOLITH, ROCK, SKY_ROWS, TILE_M,
    W_TILES)
from aphelion.game.eva import _TERRAIN_SPAN_M

CHUNK = 32                       # tiles per chunk side
PX = 8                           # pixels per tile (0.5 m at 16 px/m)
_ICE_RGB = (132, 178, 214)
_ORE_RGB = (198, 156, 82)
_BEDROCK_RGB = (24, 22, 30)


def _shade(c: tuple, f: float) -> tuple:
    return (min(255, max(0, int(c[0] * f))),
            min(255, max(0, int(c[1] * f))),
            min(255, max(0, int(c[2] * f))))


class TileRenderer:
    """Blits the visible window of one TileWorld. Chunks are lazy and
    cached; invalidate(c, r) after a dig re-renders just that patch."""

    def __init__(self, world, palette) -> None:
        self.w = world
        base = tuple(palette.base)
        self.colors = {
            REGOLITH: base,
            ROCK: _shade(tuple(palette.dark), 0.85),
            ICE: _ICE_RGB,
            ORE: _ORE_RGB,
            BEDROCK: _BEDROCK_RGB,
        }
        self._cache: dict[tuple[int, int], pygame.Surface] = {}
        self._lamp: pygame.Surface | None = None

    def invalidate(self, c: int, r: int) -> None:
        cx, cy = (c // CHUNK) % (W_TILES // CHUNK), r // CHUNK
        # the dug tile, plus the row below (its top-edge highlight changed)
        self._cache.pop((cx, cy), None)
        self._cache.pop((cx, cy + 1), None)

    def _chunk(self, cx: int, cy: int) -> pygame.Surface:
        key = (cx, cy)
        s = self._cache.get(key)
        if s is not None:
            return s
        s = pygame.Surface((CHUNK * PX, CHUNK * PX), pygame.SRCALPHA)
        g = self.w.grid
        c0, r0 = cx * CHUNK, cy * CHUNK
        for i in range(CHUNK):
            col = g[(c0 + i) % W_TILES]
            for j in range(CHUNK):
                r = r0 + j
                if r >= H_TILES:
                    break
                tt = int(col[r])
                if tt == AIR:
                    continue
                # deterministic per-tile grain (no rng: chunks re-render);
                # murmur-style finalizer — raw xor of products stripes
                n = ((c0 + i) * 0x9E3779B1 ^ r * 0x85EBCA77) & 0xFFFFFFFF
                n = (n ^ (n >> 13)) * 0xC2B2AE35 & 0xFFFFFFFF
                n ^= n >> 16
                f = 0.86 + (n & 31) / 31.0 * 0.26
                color = _shade(self.colors[tt], f)
                s.fill(color, (i * PX, j * PX, PX, PX))
                if r > 0 and col[r - 1] == AIR:     # lit top edge
                    s.fill(_shade(color, 1.45),
                           (i * PX, j * PX, PX, 2))
        self._cache[key] = s
        return s

    def draw(self, screen, camx: float, camy: float, size: tuple,
             ppm: float, y0px: float) -> None:
        """World point (x, y) lands at (size[0]/2 + (x−camx)·ppm,
        y0px − (y−camy)·ppm) — the same map the eva scene uses."""
        chunk_m = CHUNK * TILE_M
        # continuous tile coordinate of the left screen edge (unwrapped)
        tc_left = (camx - size[0] / 2.0 / ppm) / _TERRAIN_SPAN_M + 0.5
        tc_left *= W_TILES
        cx_lo = int(tc_left // CHUNK) - 1
        cx_hi = cx_lo + int(size[0] / (chunk_m * ppm)) + 3
        y_top_m = camy + y0px / ppm
        cy_lo = max(0, int((SKY_ROWS * TILE_M - y_top_m) / chunk_m))
        y_bot_m = camy - (size[1] - y0px) / ppm
        cy_hi = min(H_TILES // CHUNK - 1,
                    int((SKY_ROWS * TILE_M - y_bot_m) / chunk_m) + 1)
        for cxu in range(cx_lo, cx_hi + 1):
            x_m = (cxu * CHUNK / W_TILES - 0.5) * _TERRAIN_SPAN_M
            sx = size[0] / 2.0 + (x_m - camx) * ppm
            for cy in range(cy_lo, cy_hi + 1):
                top_m = (SKY_ROWS - cy * CHUNK) * TILE_M
                sy = y0px - (top_m - camy) * ppm
                screen.blit(self._chunk(cxu % (W_TILES // CHUNK), cy),
                            (int(sx), int(sy)))

    # -- the dark down there -------------------------------------------------
    def darkness(self, screen, walker_px: tuple, depth_m: float) -> None:
        """Past ~2 m of overburden the sky stops helping; the suit lamp
        holds a warm circle around the walker."""
        if depth_m <= 2.0:
            return
        if self._lamp is None:
            # multiplied into the dark layer: alpha 0 at the walker (clear)
            # rising to 255 at the rim and beyond (full dark)
            rad = 150
            lamp = pygame.Surface((rad * 2, rad * 2), pygame.SRCALPHA)
            lamp.fill((255, 255, 255, 255))
            for rr in range(rad, 0, -2):
                a = int(255 * (rr / rad) ** 1.6)
                pygame.draw.circle(lamp, (255, 255, 255, a),
                                   (rad, rad), rr)
            self._lamp = lamp
        alpha = min(215, int((depth_m - 2.0) * 18))
        size = screen.get_size()
        dark = pygame.Surface(size, pygame.SRCALPHA)
        dark.fill((2, 2, 8, alpha))
        lamp = self._lamp
        dark.blit(lamp, (walker_px[0] - lamp.get_width() // 2,
                         walker_px[1] - lamp.get_height() // 2),
                  special_flags=pygame.BLEND_RGBA_MULT)
        screen.blit(dark, (0, 0))
