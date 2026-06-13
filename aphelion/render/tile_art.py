"""Tile-world rendering: the site cross-section as cached chunk surfaces
(32×32 tiles each), re-rendered only when a dig edits them. The cross
section reads as geological documentary photography (ART-DIRECTION §1.1):
material gradients and strata in the body's ground palette, ambient
occlusion wherever rock meets a void, a sun-struck warm lip along the
daylight surface, ice with sparse internal glints, ore as mineral flecks
in host rock, bedrock near-black. Underground, a helmet-lamp overlay
closes the dark in with a smooth radial pool.
"""

from __future__ import annotations

import numpy as np
import pygame
from pygame import surfarray

from aphelion.game.tileworld import (
    AIR, BEDROCK, D_TILES, H_TILES, ICE, ORE, REGOLITH, ROCK, SKY_ROWS,
    TILE_M, W_TILES)
from aphelion.game.eva import _TERRAIN_SPAN_M

CHUNK = 32                       # tiles per chunk side
PX = 8                           # pixels per tile (0.5 m at 16 px/m)
_ICE_RGB = (138, 176, 206)
_ORE_RGB = (198, 156, 82)
_BEDROCK_RGB = (24, 22, 30)
_CAVITY_RGB = (11.0, 12.0, 17.0)   # enclosed void backdrop (not the sky)
_GLINT_RGB = (208, 226, 242)       # ice crystal facet catching the lamp
_FLECK_A = (214, 168, 88)          # bright mineral fleck in an ore vein
_FLECK_B = (156, 102, 64)          # oxidised, coppery fleck
_SUN_WARM = (26.0, 19.0, 8.0)      # warm add on the sun-struck surface lip
_DEPTH_COOL = np.array([0.26, 0.24, 0.16])   # deep rock: darker AND cooler
_LAMP_R = 165                      # suit-lamp pool radius, px
_GLOW_R = 110                      # warm additive pool radius, px


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
        dark = tuple(palette.dark)
        # rock sits between the regolith blanket and bedrock: dark enough
        # to read dense, light enough that strata and AO still show
        rock = tuple(int(dk * 0.82 + bs * 0.24) for dk, bs in zip(dark, base))
        self.colors = {
            REGOLITH: base,
            ROCK: rock,
            ICE: _ICE_RGB,
            ORE: _ORE_RGB,
            BEDROCK: _BEDROCK_RGB,
        }
        self._speck = tuple(getattr(palette, "speck", base))
        # material LUTs (indexed by tile type). Ore renders as HOST ROCK
        # warm-tinted, with bright flecks added per-pixel — a vein, not
        # an orange brick.
        self._lut = np.zeros((6, 3))
        for tt, col in self.colors.items():
            self._lut[tt] = col
        rock = np.asarray(self.colors[ROCK], dtype=float)
        self._lut[ORE] = rock * 0.7 + np.asarray(_ORE_RGB, dtype=float) * 0.3
        #               AIR   REGO  ROCK  ICE   ORE   BEDR
        self._amp = np.array([0.5, 0.9, 1.1, 0.35, 0.9, 0.5])
        self._band = np.array([0.0, 0.045, 0.10, 0.04, 0.10, 0.06])
        self._cache: dict[tuple[int, int], pygame.Surface] = {}
        self._lamp: pygame.Surface | None = None
        self._glow: dict[int, pygame.Surface] = {}

    def invalidate(self, c: int, r: int) -> None:
        ncx = W_TILES // CHUNK
        ncy = H_TILES // CHUNK
        # the dug tile plus its 8 neighbours (their AO edges changed) …
        r_lo = max(0, r - 1) // CHUNK
        r_hi = min(H_TILES - 1, r + 1) // CHUNK
        for dc in (-1, 0, 1):
            cx = ((c + dc) // CHUNK) % ncx
            for cy in range(r_lo, min(ncy - 1, r_hi) + 1):
                self._cache.pop((cx, cy), None)
        # … plus everything below in this column: daylight may now reach
        # deeper down the shaft (the sun-lip follows the dig).
        cx0 = (c // CHUNK) % ncx
        for cy in range(r_hi, ncy):
            self._cache.pop((cx0, cy), None)

    def _chunk(self, cx: int, cy: int) -> pygame.Surface:
        key = (cx, cy)
        s = self._cache.get(key)
        if s is not None:
            return s
        side = CHUNK * PX
        s = pygame.Surface((side, side), pygame.SRCALPHA)
        g = self.w.grid
        c0, r0 = cx * CHUNK, cy * CHUNK
        n_r = min(CHUNK, H_TILES - r0)
        if n_r <= 0:
            self._cache[key] = s
            return s

        # tile window plus a 1-tile apron (neighbour-aware AO)
        cols = np.arange(c0 - 1, c0 + CHUNK + 1) % W_TILES
        T = g[cols].astype(np.int16)             # (CHUNK+2, H_TILES)
        solid_f = T != AIR
        above = np.cumsum(solid_f, axis=1) - solid_f
        open_sky = above == 0                    # daylight reaches this row
        Tp = np.pad(T, ((0, 0), (1, 1)), mode="edge")
        sl = slice(r0, r0 + n_r)
        tw = T[1:-1, sl]                         # (CHUNK, n_r) tile types
        up = Tp[1:-1, r0:r0 + n_r]
        dn = Tp[1:-1, r0 + 2:r0 + n_r + 2]
        lf, rt = T[:-2, sl], T[2:, sl]
        sky = open_sky[1:-1, sl]
        sol = tw != AIR
        cav = (~sol) & (~sky)                    # enclosed void (gallery air)

        # deterministic per-tile grain (no rng: chunks re-render);
        # murmur-style finalizer — raw xor of products stripes
        gx = np.arange(c0, c0 + CHUNK, dtype=np.uint64)[:, None]
        gy = np.arange(r0, r0 + n_r, dtype=np.uint64)[None, :]
        n = ((gx * 0x9E3779B1) ^ (gy * 0x85EBCA77)) & 0xFFFFFFFF
        n = ((n ^ (n >> 13)) * 0xC2B2AE35) & 0xFFFFFFFF
        n = n ^ (n >> 16)
        f = 1.0 + ((n & 31).astype(float) / 31.0 - 0.5) * 0.10 * self._amp[tw]

        # strata: low-frequency, domain-warped banding — geology, not noise
        gxf = np.arange(c0, c0 + CHUNK, dtype=float)[:, None]
        gyf = np.arange(r0, r0 + n_r, dtype=float)[None, :]
        warp = 2.2 * np.sin(gxf * 0.043) + 3.0 * np.sin(gxf * 0.011 + 1.7)
        layers = (np.sin(gyf * 0.42 + warp)
                  + 0.6 * np.sin(gyf * 0.13 + 0.5 * warp + 2.3))
        f = f * (1.0 + self._band[tw] * layers)

        # depth: deeper rock reads denser, darker, cooler — and the top
        # few metres below the daylight line catch a soft vertical
        # gradient (no 40 px surface goes flat — ART-DIRECTION §3)
        d = np.clip((gyf - SKY_ROWS) / D_TILES, 0.0, 1.0)
        first_solid = np.argmax(solid_f, axis=1)[1:-1].astype(float)
        dsurf = gyf - first_solid[:, None]       # tiles below local surface
        near = 0.13 * np.exp(-np.clip(dsurf, 0.0, None) / 7.0)
        rgb = (self._lut[tw] * (f * (1.0 + near))[..., None]
               * (1.0 - _DEPTH_COOL * d[..., None]))
        db = np.broadcast_to(d, tw.shape)
        rgb[cav] = np.asarray(_CAVITY_RGB) * (1.0 - 0.45 * db[cav][:, None])

        # 8× upscale, then pixel-scale work
        R = np.repeat(np.repeat(rgb, PX, axis=0), PX, axis=1)
        h_px = n_r * PX

        def _up8(mask):
            return np.repeat(np.repeat(mask, PX, axis=0), PX, axis=1)

        # per-pixel grain (same murmur idiom, different stripe constants)
        ppx = np.arange(c0 * PX, (c0 + CHUNK) * PX, dtype=np.uint64)[:, None]
        ppy = np.arange(r0 * PX, (r0 + n_r) * PX, dtype=np.uint64)[None, :]
        m = ((ppx * 0xC2B2AE3D) ^ (ppy * 0x27D4EB2F)) & 0xFFFFFFFF
        m = ((m ^ (m >> 15)) * 0x85EBCA77) & 0xFFFFFFFF
        m = m ^ (m >> 13)
        amp_px = _up8(self._amp[tw])
        R *= (1.0 + ((m & 63).astype(float) / 63.0 - 0.5)
              * 0.05 * amp_px)[..., None]

        # smooth mineral mottle: tile-corner hashes interpolated bilinearly
        # at pixel scale (a real value-noise FIELD, not white noise)
        gx2 = np.arange(c0, c0 + CHUNK + 1, dtype=np.uint64)[:, None]
        gy2 = np.arange(r0, r0 + n_r + 1, dtype=np.uint64)[None, :]
        q = ((gx2 * 0x9E3779B1) ^ (gy2 * 0x85EBCA77)) & 0xFFFFFFFF
        q = ((q ^ (q >> 13)) * 0xC2B2AE35) & 0xFFFFFFFF
        q = q ^ (q >> 16)
        corner = (q & 255).astype(float) / 255.0
        u = (((np.arange(side) % PX) + 0.5) / PX)[:, None]
        v = (((np.arange(h_px) % PX) + 0.5) / PX)[None, :]
        us, vs = u * u * (3 - 2 * u), v * v * (3 - 2 * v)
        ml = np.repeat(np.repeat(corner[:-1, :-1], PX, 0), PX, 1)
        mr = np.repeat(np.repeat(corner[1:, :-1], PX, 0), PX, 1)
        md = np.repeat(np.repeat(corner[:-1, 1:], PX, 0), PX, 1)
        me = np.repeat(np.repeat(corner[1:, 1:], PX, 0), PX, 1)
        mott = (ml * (1 - us) * (1 - vs) + mr * us * (1 - vs)
                + md * (1 - us) * vs + me * us * vs) - 0.5
        R *= (1.0 + mott * 0.18 * amp_px)[..., None]

        # material micro-features: ice glints, ore flecks, regolith specks
        ice_px = _up8(tw == ICE) & ((m % 211) < 3)
        R[ice_px] = R[ice_px] * 0.35 + np.asarray(_GLINT_RGB, float) * 0.72
        ore_px = _up8(tw == ORE) & ((m % 89) < 7)
        R[ore_px] = np.where((m[ore_px] & 64)[:, None] > 0,
                             np.asarray(_FLECK_A, float),
                             np.asarray(_FLECK_B, float))
        reg_px = _up8(tw == REGOLITH) & ((m % 257) < 2)
        R[reg_px] = R[reg_px] * 0.45 + np.asarray(self._speck, float) * 0.6

        # ambient occlusion at every solid/void boundary, sun on the
        # daylight line (sun high and a touch to the LEFT — rule §2.1)
        row_i = (np.arange(h_px) % PX)[None, :]
        col_i = (np.arange(side) % PX)[:, None]
        ao = np.ones((side, h_px))
        add = np.zeros((side, h_px, 3))
        up_dark = _up8(sol & (up == AIR) & ~sky)
        up_sun = _up8(sol & (up == AIR) & sky)
        dn_air = _up8(sol & (dn == AIR))
        lf_dark = _up8(sol & (lf == AIR) & ~sky)
        lf_sun = _up8(sol & (lf == AIR) & sky)
        rt_dark = _up8(sol & (rt == AIR) & ~sky)
        rt_sun = _up8(sol & (rt == AIR) & sky)
        for k, v in ((0, 0.42), (1, 0.60), (2, 0.80)):
            ao *= np.where(up_dark & (row_i == k), v, 1.0)
        for k, v in ((PX - 1, 0.45), (PX - 2, 0.62), (PX - 3, 0.82)):
            ao *= np.where(dn_air & (row_i == k), v, 1.0)
        for k, v in ((0, 0.50), (1, 0.70), (2, 0.86)):
            ao *= np.where(lf_dark & (col_i == k), v, 1.0)
        for k, v in ((PX - 1, 0.46), (PX - 2, 0.66), (PX - 3, 0.84)):
            ao *= np.where(rt_dark & (col_i == k), v, 1.0)
        for k, v in ((0, 1.72), (1, 1.34), (2, 1.12)):
            ao *= np.where(up_sun & (row_i == k), v, 1.0)
        add += np.where((up_sun & (row_i == 0))[..., None],
                        np.asarray(_SUN_WARM) * 2.4, 0.0)
        add += np.where((up_sun & (row_i == 1))[..., None],
                        np.asarray(_SUN_WARM) * 1.1, 0.0)
        for k, v in ((0, 1.22), (1, 1.08)):
            ao *= np.where(lf_sun & (col_i == k), v, 1.0)
        for k, v in ((PX - 1, 0.78), (PX - 2, 0.90)):
            ao *= np.where(rt_sun & (col_i == k), v, 1.0)
        # cavity-rim tiles pool a little extra dark (AO settles in digs)
        rim = _up8(sol & ~sky & ((up == AIR) | (dn == AIR)
                                 | (lf == AIR) | (rt == AIR)))
        ao *= np.where(rim, 0.92, 1.0)
        # geological contact: a faint seam where two materials touch
        seam_u = _up8(sol & (up != AIR) & (up != tw))
        ao *= np.where(seam_u & (row_i == 0), 0.88, 1.0)
        seam_l = _up8(sol & (lf != AIR) & (lf != tw))
        ao *= np.where(seam_l & (col_i == 0), 0.90, 1.0)
        R = R * ao[..., None] + add

        out = np.clip(R, 0.0, 255.0).astype(np.uint8)
        alpha = np.where(_up8(sol | cav), 255, 0).astype(np.uint8)
        arr = surfarray.pixels3d(s)
        arr[:, :h_px] = out
        del arr
        aar = surfarray.pixels_alpha(s)
        aar[:, :h_px] = alpha
        del aar
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
    def darkness(self, screen, walker_px: tuple, depth_m: float,
                 lamp_on: bool = True) -> None:
        """Past ~2 m of overburden the sky stops helping; the suit lamp
        holds a warm circle around the walker. With a dead battery
        (lamp_on=False) the dark closes in completely — no pool, no glow."""
        if depth_m <= 2.0:
            return
        if not lamp_on:
            alpha = min(238, int((depth_m - 2.0) * 18) + 24)
            dark = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
            dark.fill((2, 2, 8, alpha))
            screen.blit(dark, (0, 0))
            return
        if self._lamp is None:
            # multiplied into the dark layer: alpha 0 at the walker (clear)
            # rising smoothly to 255 at the rim — a radial pool, no rings
            rad = _LAMP_R
            lamp = pygame.Surface((rad * 2, rad * 2), pygame.SRCALPHA)
            lamp.fill((255, 255, 255, 255))
            ax = np.arange(rad * 2, dtype=float) - (rad - 0.5)
            dist = np.sqrt(ax[:, None] ** 2 + ax[None, :] ** 2) / rad
            t = np.clip((dist - 0.08) / 0.92, 0.0, 1.0)
            fall = t * t * (3.0 - 2.0 * t)       # smoothstep falloff
            aar = surfarray.pixels_alpha(lamp)
            aar[...] = (255.0 * fall ** 1.2).astype(np.uint8)
            del aar
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
        # the lamp itself is WARM: a faint amber pool added over the rock
        lvl = min(6, alpha // 36)
        if lvl > 0:
            glow = self._glow.get(lvl)
            if glow is None:
                glow = pygame.Surface((_GLOW_R * 2, _GLOW_R * 2))
                ax = np.arange(_GLOW_R * 2, dtype=float) - (_GLOW_R - 0.5)
                dd = np.sqrt(ax[:, None] ** 2 + ax[None, :] ** 2) / _GLOW_R
                fal = np.clip(1.0 - dd, 0.0, 1.0) ** 2
                tint = np.asarray((34.0, 25.0, 13.0)) * (lvl / 6.0)
                arr = surfarray.pixels3d(glow)
                arr[...] = (fal[..., None] * tint).astype(np.uint8)
                del arr
                self._glow[lvl] = glow
            screen.blit(glow, (walker_px[0] - _GLOW_R,
                               walker_px[1] - _GLOW_R),
                        special_flags=pygame.BLEND_RGB_ADD)
