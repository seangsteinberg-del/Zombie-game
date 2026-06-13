"""Procedural colony art — MISSION FILM pass: the base is a PLACE.

Per-site-kind terrain strips (numpy fBM albedo, sun-direction slope
shading, a compacted walker path, utility cable runs with support posts,
boulders and craters that all cast contact shadows) and one engineered
sprite per buildable module in game.basebuild.CATALOG: hull gradients in
NASA-white / aluminium / graphite, panel seams + bolts, gold MLI on cryo
surfaces, international-orange accents, and lit windows / status lamps as
the only emitters.  Every module is grounded by a baked contact-shadow
ellipse (ART-DIRECTION §2.5 rule zero).  All pygame primitives rendered
at 2x and smoothscaled, cached at module level, zero asset files, seeded
rng only.  The sun sits LEFT of frame in every sprite and strip.
"""

from __future__ import annotations

import math

import numpy as np
import pygame

from aphelion.render.body_art import _fbm, body_sprite, sun_sprite
from aphelion.ui.theme import _mix, _seed

_TERRAIN_CACHE: dict[tuple, tuple[pygame.Surface, list[int]]] = {}
_SKY_CACHE: dict[tuple, pygame.Surface] = {}
_MODULE_CACHE: dict[tuple, pygame.Surface] = {}
_WALKER_CACHE: dict[tuple, pygame.Surface] = {}

# ground lo/hi, sky day, sky night, airless (stars always)
_KIND_PAL = {
    "psr_ice": ((62, 64, 74), (158, 164, 178), (10, 12, 18),
                (5, 6, 10), True),
    "mars_ice": ((96, 56, 38), (184, 124, 86), (198, 142, 104),
                 (24, 13, 14), False),
    "aerostat": ((196, 168, 128), (242, 222, 182), (236, 196, 128),
                 (48, 34, 26), False),
    "methane_lake": ((74, 58, 38), (130, 104, 64), (172, 124, 62),
                     (20, 16, 14), False),
    "ice_burrow": ((130, 144, 168), (216, 228, 242), (12, 14, 22),
                   (6, 8, 14), True),
}

# MACHINE-layer materials (ART-DIRECTION §1.2): NASA white, aluminium,
# graphite, international orange, gold MLI.  Gradients only — no flats.
_METAL = (170, 176, 186)              # bare aluminium (mid)
_METAL_DARK = (84, 90, 102)           # graphite structure
_PANEL_BLUE = (38, 52, 84)            # solar cell glass
_WHITE_HI = (228, 232, 238)
_WHITE_MID = (196, 201, 210)
_WHITE_LO = (138, 144, 156)
_ALU_HI = (198, 204, 214)
_ALU_LO = (110, 116, 128)
_GRAPH_HI = (108, 114, 126)
_GRAPH_LO = (48, 52, 62)
_ORANGE = (224, 96, 38)
_ORANGE_DK = (148, 58, 22)
_MLI_HI = (240, 202, 104)
_MLI_MID = (192, 146, 58)
_MLI_LO = (122, 86, 34)
_GLASS = (22, 28, 38)
_WIN_WARM = (255, 218, 148)           # emitters: windows, lamps, pour glow
_CYAN = (132, 204, 235)
_LAMP_OK = (124, 230, 160)
_LAMP_WARN = (255, 186, 96)
_SHADOW = (10, 11, 15)


def kind_palette(kind: str):
    return _KIND_PAL.get(kind, _KIND_PAL["psr_ice"])


# ---------------------------------------------------------------- sky --

def sky_strip(kind: str, w: int, h: int, daylight: float) -> pygame.Surface:
    """Vertical sky gradient lerped night->day with horizon haze, a sun
    glow camera-left on atmospheric days, power-law stars when dark."""
    key = (kind, w, h, round(daylight, 2))
    hit = _SKY_CACHE.get(key)
    if hit is not None:
        return hit
    lo, hi, day, night, airless = kind_palette(kind)
    dl = 0.0 if airless else max(0.0, min(1.0, daylight))
    g = np.linspace(0.0, 1.0, h)[None, :] ** 1.2
    top = np.array(_mix(night, day, dl * 0.45), dtype=float)
    bot = np.array(_mix(night, day, dl), dtype=float)
    arr = np.repeat(top[None, None, :] * (1.0 - g[..., None])
                    + bot[None, None, :] * g[..., None], w, axis=0)
    if not airless:                       # horizon haze lift
        hz = np.clip((g - 0.68) / 0.32, 0.0, 1.0) ** 1.5
        arr += hz[..., None] * bot[None, None, :] * 0.28
    if dl > 0.20 and not airless:         # the sun, camera-left
        xs = np.arange(w)[:, None]
        ys = np.arange(h)[None, :]
        r2 = (((xs - w * 0.20) ** 2 + ((ys - h * 0.26) * 1.25) ** 2)
              / max((h * 0.55) ** 2, 1.0))
        warm = np.array((255, 226, 180), dtype=float)
        arr += (np.exp(-r2 * 2.0) * dl)[..., None] * warm * 0.35
        arr += (np.exp(-r2 * 55.0) * dl)[..., None] \
            * np.array((255, 250, 240), dtype=float) * 0.9
    surf = pygame.Surface((w, h))
    pygame.surfarray.blit_array(surf, np.clip(arr, 0, 255).astype("uint8"))
    if airless or dl < 0.35:              # power-law starfield, no xmas tree
        rng = np.random.default_rng(_seed(kind + "stars"))
        fade = 1.0 if airless else (1.0 - dl)
        n = 130
        xs2 = rng.integers(0, w, n)
        ys2 = rng.integers(0, max(int(h * 0.88), 1), n)
        us = rng.random(n)
        for x, y, u in zip(xs2, ys2, us):
            v = int((50 + 200 * u ** 3) * fade)
            if v <= 26:
                continue
            c = (v, v, min(255, v + 16))
            surf.set_at((int(x), int(y)), c)
            if v > 195:                   # the handful of bright ones
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    px, py = int(x) + dx, int(y) + dy
                    if 0 <= px < w and 0 <= py < h:
                        surf.set_at((px, py), (v // 2, v // 2, v // 2 + 10))
        if airless:                       # faint diagonal galaxy band
            for _ in range(90):
                bx = int(rng.integers(0, w))
                by = int(h * 0.18 + bx * 0.20 + rng.normal(0.0, h * 0.06))
                if 0 <= by < int(h * 0.9):
                    v = int(rng.integers(22, 64))
                    surf.set_at((bx, by), (v, v, v + 8))
    if len(_SKY_CACHE) > 24:
        _SKY_CACHE.clear()
    _SKY_CACHE[key] = surf
    return surf


def draw_sky_bodies(surf, w: int, scene_h: int, body_id: str, tree,
                    daylight: float, airless: bool) -> None:
    """The parent world hanging over the site (Earthrise over a lunar base,
    Jupiter over Europa) + the sun disk camera-left when it's up. Resolves
    'are we a moon?' from the frame tree's parent chain. Cinematic depth for
    any surface scene (colony, drive, EVA)."""
    try:
        pid = tree.body(body_id).parent
        is_moon = pid is not None and tree.body(pid).parent is not None
    except Exception:
        pid, is_moon = None, False
    if is_moon and pid:
        psp = body_sprite(pid, 150, sun_angle=3.5)
        surf.blit(psp, (int(w * 0.72 - psp.get_width() / 2),
                        int(scene_h * 0.20 - psp.get_height() / 2)))
    if daylight > 0.20:
        # the sun rides time of day: low on the horizon at dawn/dusk, high
        # at midday; bigger near the horizon (and warmer on atmo worlds)
        el = max(0.0, min(1.0, (daylight - 0.20) / 0.80))
        sun_y = scene_h * (0.50 - 0.38 * el)
        low = el < 0.4
        base_d = (44 if low else 36) if airless else (34 if low else 26)
        ssp = sun_sprite(base_d)
        sx = int(w * 0.13 - ssp.get_width() / 2)
        sy = int(sun_y - ssp.get_height() / 2)
        if low and not airless:           # warm horizon haze under the disk
            haze = pygame.Surface((ssp.get_width() * 3, ssp.get_height() * 2),
                                  pygame.SRCALPHA)
            pygame.draw.ellipse(haze, (120, 70, 40,
                                       int(70 * (1.0 - el / 0.4))),
                                haze.get_rect())
            surf.blit(haze, (sx - ssp.get_width(), sy - ssp.get_height() // 2),
                      special_flags=pygame.BLEND_RGB_ADD)
        surf.blit(ssp, (sx, sy))


# ------------------------------------------------------------ terrain --

def terrain_strip(site_id: str, kind: str, w: int,
                  h: int) -> tuple[pygame.Surface, list[int]]:
    """(surface, ridge_y per column): seeded ground band — fBM albedo,
    sun-from-the-left slope shading, a far silhouette ridge, compacted
    walker path, utility cable runs on posts, grounded boulders/craters;
    methane_lake gets a real shoreline into dark liquid on the right."""
    key = (site_id, kind, w, h)
    hit = _TERRAIN_CACHE.get(key)
    if hit is not None:
        return hit
    lo, hi, day, _night, airless = kind_palette(kind)
    cloudy = kind == "aerostat"           # a cloud deck, not rock
    rng = np.random.default_rng(_seed(site_id))
    noise = _fbm(rng, 256, octaves=4, base_cells=4)

    def _bilerp(fx, fy):                  # smooth 2D noise sampling —
        x0 = fx.astype(int) % 256         # nearest sampling bands columns
        y0 = fy.astype(int) % 256
        x1 = (x0 + 1) % 256
        y1 = (y0 + 1) % 256
        tx = (fx % 1.0)[:, None]
        ty = (fy % 1.0)[None, :]
        return (noise[np.ix_(x0, y0)] * (1 - tx) * (1 - ty)
                + noise[np.ix_(x1, y0)] * tx * (1 - ty)
                + noise[np.ix_(x0, y1)] * (1 - tx) * ty
                + noise[np.ix_(x1, y1)] * tx * ty)

    line = np.interp(np.arange(w) * 255.0 / max(w - 1, 1),
                     np.arange(256.0), noise[64])
    pad = np.concatenate([line[:3][::-1], line, line[-3:][::-1]])
    line = np.convolve(pad, np.ones(7) / 7.0, mode="valid")
    ridge_arr = (h * 0.30 + line * h * 0.28).astype(int)

    lake_from = int(w * 0.68) if kind == "methane_lake" else w + 1
    lake_y = h
    if lake_from < w:
        lake_y = int(ridge_arr[lake_from:].max())
        x0 = max(0, lake_from - 36)       # shoreline ramps into the liquid
        for x in range(x0, lake_from):
            t = (x - x0) / max(lake_from - x0, 1)
            ridge_arr[x] = int(ridge_arr[x] * (1 - t * t) + lake_y * t * t)
        ridge_arr[lake_from:] = lake_y

    X = np.arange(w)[:, None]
    Y = np.arange(h)[None, :]
    d = Y - ridge_arr[:, None]
    ground = d >= 0
    in_lake = (X >= lake_from) & ground

    fxs = np.arange(w) * 255.0 / max(w - 1, 1)
    fys = np.arange(h) * 255.0 / max(h - 1, 1)
    tex = _bilerp(fxs, fys)
    tex2 = _bilerp(fxs * 2.7 + 71.0, fys * 4.3 + 31.0)
    alb = np.clip(0.30 + 0.55 * (1.0 - (0.65 * tex + 0.35 * tex2)), 0.0, 1.0)
    lo_v = np.array(lo, dtype=float)
    hi_v = np.array(hi, dtype=float)
    col = lo_v[None, None, :] + (hi_v - lo_v)[None, None, :] * alb[..., None]

    # light has a DIRECTION: sun left, slopes that fall away to the right
    # face it; depth below the crest falls into ambient occlusion
    slope = np.gradient(ridge_arr.astype(float))
    slope = np.convolve(np.pad(slope, 2, mode="edge"),
                        np.ones(5) / 5.0, mode="valid")
    sun = np.clip(1.0 + 0.16 * slope, 0.74, 1.26)[:, None]
    sun = 1.0 + (sun - 1.0) * np.clip(1.0 - d / 70.0, 0.0, 1.0)
    shade = sun * (1.0 - 0.32 * np.clip(d / max(h * 0.85, 1.0), 0.0, 1.0))
    shade = np.where((d >= 0) & (d <= 2),
                     shade * (1.06 + 0.18 * tex), shade)        # lit crest
    # compacted path where the walkers travel between modules
    if not cloudy:
        pw = (np.clip((d - 3) / 3.0, 0, 1) * np.clip((15 - d) / 3.0, 0, 1)
              * np.clip((X - 24) / 18.0, 0, 1)
              * np.clip((w - 24 - X) / 18.0, 0, 1))
        pw = np.where(X >= lake_from, 0.0, pw)
        mean = (lo_v + hi_v) * 0.5 * 0.78
        col = (col * (1.0 - 0.58 * pw[..., None])
               + mean[None, None, :] * (0.58 * pw[..., None]))
    col = col * shade[..., None]
    col += rng.normal(0.0, 1.0, (w, h))[..., None] * 3.0   # film grain

    # far silhouette hills peeking over the crest (aerial-perspective haze
    # on atmospheric worlds, crisp dark relief on airless ones)
    line2 = np.interp(np.arange(w) * 255.0 / max(w - 1, 1),
                      np.arange(256.0), noise[140])
    pad2 = np.concatenate([line2[:4][::-1], line2, line2[-4:][::-1]])
    line2 = np.convolve(pad2, np.ones(9) / 9.0, mode="valid")
    ridge2 = np.maximum((h * 0.20 + line2 * h * 0.22).astype(int),
                        ridge_arr - int(h * 0.16))
    far = (Y >= ridge2[:, None]) & (Y < ridge_arr[:, None])
    if airless:
        fc = np.array(_mix(lo, (0, 0, 0), 0.28), dtype=float)
    else:
        fc = np.array(_mix(_mix(lo, hi, 0.5), day, 0.55), dtype=float)
    fade2 = 1.0 - 0.22 * np.clip((ridge_arr[:, None] - Y) / 40.0, 0.0, 1.0)
    colf = fc[None, None, :] * ((0.86 + 0.26 * tex) * fade2)[..., None]
    col = np.where(far[..., None], colf, col)

    if lake_from < w:                     # dark hydrocarbon liquid
        t_liq = np.clip((Y - lake_y) / max(h - lake_y, 1), 0.0, 1.0) ** 0.7
        liq = (np.array((72, 60, 36), dtype=float)[None, None, :]
               * (1.0 - t_liq[..., None])
               + np.array((14, 13, 12), dtype=float)[None, None, :]
               * t_liq[..., None])
        ltex = _bilerp(fxs * 6.0 + 13.0, fys * 0.5 + 91.0)
        liq = liq * (0.92 + 0.16 * ltex[..., None])    # surface streaking
        col = np.where(in_lake[..., None], liq, col)

    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    rgb = pygame.surfarray.pixels3d(surf)
    rgb[:] = np.clip(col, 0, 255).astype("uint8")
    del rgb
    av = pygame.surfarray.pixels_alpha(surf)
    av[:] = ((ground | far) * 255).astype("uint8")
    del av

    ridge = [int(v) for v in ridge_arr]

    # ---- pygame feature pass (everything below casts a shadow) ----
    crater_dark = _mix(lo, (0, 0, 0), 0.35)
    crater_lt = _mix(hi, (255, 255, 255), 0.18)
    craters = []
    if not cloudy and kind in ("psr_ice", "ice_burrow", "mars_ice"):
        for _ in range(6):                # shallow crater dishes
            cx = int(rng.integers(12, max(min(w, lake_from) - 12, 13)))
            cy = ridge[cx] + int(rng.integers(18, max(19, h - ridge[cx] - 8)))
            cw = int(rng.integers(10, 26))
            ch = max(4, cw // 3)
            if cy + ch < h:
                craters.append(pygame.Rect(cx - cw // 2, cy - ch // 2,
                                           cw, ch))

    boulders = []
    if not cloudy:
        for _ in range(max(10, w // 55)):
            bx = int(rng.integers(6, w - 6))
            if bx >= lake_from - 4:
                continue
            by = ridge[bx] + int(rng.integers(7, max(8, h - ridge[bx] - 4)))
            if by >= h - 3:
                continue
            boulders.append((bx, by, int(rng.integers(2, 6))))

    anchors = ([] if cloudy else
               [a for a in range(100, w - 50, 102) if a < lake_from - 24])

    ov = pygame.Surface((w, h), pygame.SRCALPHA)      # blended shadow pass
    for rect in craters:                  # crater bowls darken inside
        pygame.draw.ellipse(ov, (*_SHADOW, 44), rect)
    for bx, by, r in boulders:
        pygame.draw.ellipse(ov, (*_SHADOW, 96),
                            (bx - r // 2, by + r - 2, int(r * 2.6),
                             max(2, r)))              # cast right of the sun
    for ax in anchors:
        pygame.draw.ellipse(ov, (*_SHADOW, 80),
                            (ax - 6, ridge[ax] + 1, 13, 4))
    surf.blit(ov, (0, 0))

    for rect in craters:                  # rims: lit on the down-sun wall
        pygame.draw.arc(surf, crater_dark, rect, math.pi * 0.25,
                        math.pi * 1.1, 2)             # shadowed inner lip
        pygame.draw.arc(surf, crater_lt, rect.move(1, 1), math.pi * 1.2,
                        math.pi * 2.1, 2)             # sun-facing inner wall

    for bx, by, r in boulders:
        pygame.draw.circle(surf, _mix(lo, (0, 0, 0), 0.22), (bx, by), r)
        pygame.draw.circle(surf, _mix(hi, (255, 255, 255), 0.12),
                           (bx - max(1, r // 3), by - max(1, r // 3)),
                           max(1, r - 2))

    # utility runs: cable on posts strung between module pads (bible:
    # visible infrastructure), drawn under the modules main blits on top
    if len(anchors) >= 2:
        posts: list[int] = []
        for ax, bx2 in zip(anchors, anchors[1:]):
            seg = max(2, (bx2 - ax) // 26)
            posts.extend(ax + (bx2 - ax) * i // seg for i in range(seg + 1))
        posts = sorted(set(posts))
        tops = []
        for px in posts:
            ty = ridge[px] - 7
            pygame.draw.line(surf, (44, 47, 56), (px, ridge[px] + 2),
                             (px, ty), 2)
            tops.append((px, ty))
        for (x1, y1), (x2, y2) in zip(tops, tops[1:]):
            sag = [(x1, y1), ((x1 + x2) // 2, max(y1, y2) + 3), (x2, y2)]
            pygame.draw.lines(surf, (24, 26, 32), False, sag, 2)
            pygame.draw.lines(surf, (70, 75, 86), False,
                              [(x, y - 1) for x, y in sag], 1)
        for px, ty in tops:               # insulator catchlights
            surf.set_at((px, ty), (148, 154, 166))
        for ax in anchors:                # junction pedestals + amber tell
            bx_r = pygame.Rect(ax - 4, ridge[ax] - 9, 8, 11)
            _grad_rect(surf, bx_r, _GRAPH_HI, _GRAPH_LO, radius=2)
            pygame.draw.line(surf, _LAMP_WARN, (ax - 2, bx_r.y + 2),
                             (ax + 1, bx_r.y + 2), 2)

    if lake_from < w:                     # liquid edge + sun glints
        pygame.draw.line(surf, (124, 102, 60), (max(lake_from - 2, 0),
                                                lake_y), (w - 1, lake_y), 1)
        for i in range(9):                # specular shimmer rows
            yy = lake_y + 4 + i * 6
            if yy >= h:
                continue
            for _ in range(6):
                gx = int(rng.integers(lake_from + 3, w - 14))
                ln = int(rng.integers(3, 12))
                pygame.draw.line(surf, (104, 86, 50), (gx, yy),
                                 (gx + ln, yy))
                if rng.random() < 0.4:    # brighter sun glints
                    pygame.draw.line(surf, (148, 122, 70), (gx + 2, yy),
                                     (gx + min(ln, 5), yy))

    if len(_TERRAIN_CACHE) > 12:
        _TERRAIN_CACHE.clear()
    _TERRAIN_CACHE[key] = (surf, ridge)
    return surf, ridge


# ------------------------------------------------- sprite helper kit --

def _at2x(draw_fn, w: int, h: int) -> pygame.Surface:
    big = pygame.Surface((w * 2, h * 2), pygame.SRCALPHA)
    draw_fn(big, w * 2, h * 2)
    return pygame.transform.smoothscale(big, (w, h))


def _round_mask(tmp: pygame.Surface, radius: int) -> None:
    msk = pygame.Surface(tmp.get_size(), pygame.SRCALPHA)
    pygame.draw.rect(msk, (255, 255, 255, 255), msk.get_rect(),
                     border_radius=radius)
    tmp.blit(msk, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)


def _grad_rect(s, rect, c_top, c_bot, radius=0, horiz=False):
    """Vertical (or horizontal) gradient fill — never a flat fill."""
    rect = pygame.Rect(rect)
    if rect.w <= 0 or rect.h <= 0:
        return
    tmp = pygame.Surface(rect.size, pygame.SRCALPHA)
    n = rect.w if horiz else rect.h
    for i in range(n):
        c = _mix(c_top, c_bot, i / max(n - 1, 1))
        if horiz:
            pygame.draw.line(tmp, c, (i, 0), (i, rect.h))
        else:
            pygame.draw.line(tmp, c, (0, i), (rect.w, i))
    if radius:
        _round_mask(tmp, radius)
    s.blit(tmp, rect.topleft)


def _cyl(s, rect, c_lo, c_hi, radius=0, horiz=True):
    """Cylinder lambert: bright band toward the sun (top-left)."""
    rect = pygame.Rect(rect)
    if rect.w <= 0 or rect.h <= 0:
        return
    tmp = pygame.Surface(rect.size, pygame.SRCALPHA)
    n = rect.h if horiz else rect.w
    for i in range(n):
        t = i / max(n - 1, 1)
        if t <= 0.30:
            lum = 0.45 + 0.55 * math.sin(0.5 * math.pi * t / 0.30)
        else:
            lum = 0.10 + 0.90 * math.cos(0.5 * math.pi * (t - 0.30) / 0.70)
        c = _mix(c_lo, c_hi, lum)
        if horiz:
            pygame.draw.line(tmp, c, (0, i), (rect.w, i))
        else:
            pygame.draw.line(tmp, c, (i, 0), (i, rect.h))
    if radius:
        _round_mask(tmp, radius)
    s.blit(tmp, rect.topleft)


def _dome(s, rect, c_lo, c_hi):
    rect = pygame.Rect(rect)
    if rect.w <= 1 or rect.h <= 1:
        return
    tmp = pygame.Surface(rect.size, pygame.SRCALPHA)
    for i in range(rect.h):
        t = i / max(rect.h - 1, 1)
        pygame.draw.line(tmp, _mix(c_hi, c_lo, t ** 1.3), (0, i),
                         (rect.w, i))
    msk = pygame.Surface(rect.size, pygame.SRCALPHA)
    pygame.draw.ellipse(msk, (255, 255, 255, 255), msk.get_rect())
    tmp.blit(msk, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
    spec = pygame.Surface(rect.size, pygame.SRCALPHA)
    pygame.draw.ellipse(spec, (255, 255, 255, 64),
                        (int(rect.w * 0.16), int(rect.h * 0.10),
                         max(2, int(rect.w * 0.34)),
                         max(2, int(rect.h * 0.22))))
    tmp.blit(spec, (0, 0))
    s.blit(tmp, rect.topleft)


def _contact(s, w, h, cx=None, span=0.84, dy=0, strength=1.0):
    """Rule zero: the contact shadow that grounds the module.  Drawn
    FIRST (replace semantics over the transparent sprite floor)."""
    cx = w // 2 if cx is None else int(cx)
    gy = h - 16 + dy
    rx = max(6, int(w * span * 0.5))
    ry = max(6, rx // 5)
    off = max(2, w // 44)                 # sun left: the shadow leans right
    for f, a in ((1.0, 46), (0.70, 76), (0.42, 102)):
        rr = pygame.Rect(0, 0, max(2, int(rx * 2 * f)),
                         max(2, int(ry * 2 * f)))
        rr.center = (cx + off, gy)
        pygame.draw.ellipse(s, (*_SHADOW, int(a * strength)), rr)


def _pad_shadow(s, x, y, rx=9):
    pygame.draw.ellipse(s, (*_SHADOW, 92),
                        (int(x) - rx, int(y) - rx // 3, rx * 2,
                         max(3, (rx * 2) // 3)))


def _lamp(s, x, y, col, r=4):
    """Status lamp: the only glow allowed besides windows/plumes."""
    glow = pygame.Surface((r * 8, r * 8), pygame.SRCALPHA)
    pygame.draw.circle(glow, (*col, 30), (r * 4, r * 4), r * 4)
    pygame.draw.circle(glow, (*col, 70), (r * 4, r * 4), r * 2)
    s.blit(glow, (int(x) - r * 4, int(y) - r * 4))
    pygame.draw.circle(s, _mix(col, (255, 255, 255), 0.55),
                       (int(x), int(y)), r)
    pygame.draw.circle(s, _mix(col, (0, 0, 0), 0.35), (int(x), int(y)), r, 1)


def _window(s, rect, col=_WIN_WARM, mullion=0):
    """A lit window: graphite frame, warm gradient glass, soft halo,
    inner shadow at the head (it is a recess)."""
    rect = pygame.Rect(rect)
    halo = pygame.Surface((rect.w * 3, rect.h * 3), pygame.SRCALPHA)
    pygame.draw.rect(halo, (*col, 26), halo.get_rect(),
                     border_radius=max(4, rect.h))
    s.blit(halo, (rect.x - rect.w, rect.y - rect.h))
    pygame.draw.rect(s, _GRAPH_LO, rect.inflate(4, 4), border_radius=3)
    _grad_rect(s, rect, _mix(col, (255, 255, 255), 0.6),
               _mix(col, (120, 70, 25), 0.25), radius=2)
    for i in range(1, mullion + 1):
        x = rect.x + i * rect.w // (mullion + 1)
        pygame.draw.line(s, _GRAPH_LO, (x, rect.y), (x, rect.bottom - 1), 2)
    pygame.draw.line(s, (44, 38, 30), (rect.x, rect.y + 1),
                     (rect.right - 1, rect.y + 1), 2)


def _bolts(s, pts, col=(58, 62, 72)):
    for x, y in pts:
        pygame.draw.circle(s, col, (int(x), int(y)), 2)
        pygame.draw.circle(s, (212, 216, 224), (int(x) - 1, int(y) - 1), 1)


def _seam(s, x, y0, y1, lt=True):
    pygame.draw.line(s, (60, 64, 74), (x, y0), (x, y1), 2)
    if lt:
        pygame.draw.line(s, (216, 220, 228), (x + 2, y0), (x + 2, y1), 1)


def _mli(s, rect, tag="mli", cell=16):
    """Quilted gold multi-layer insulation."""
    rect = pygame.Rect(rect)
    _grad_rect(s, rect, _MLI_HI, _MLI_LO)
    rng = np.random.default_rng(_seed(tag))
    for gx in range(rect.x + cell, rect.right, cell):
        j = int(rng.integers(-2, 3))
        pygame.draw.line(s, _MLI_LO, (gx + j, rect.y), (gx - j, rect.bottom),
                         2)
    for gy in range(rect.y + cell, rect.bottom, cell):
        j = int(rng.integers(-2, 3))
        pygame.draw.line(s, _MLI_LO, (rect.x, gy + j), (rect.right, gy - j),
                         2)
    for gx in range(rect.x, rect.right - cell + 1, cell):
        for gy in range(rect.y, rect.bottom - cell + 1, cell):
            pygame.draw.line(s, _mix(_MLI_HI, (255, 255, 255), 0.25),
                             (gx + 4, gy + 5), (gx + cell - 6, gy + 4), 2)


def _stripe(s, rect, col=_ORANGE):
    _grad_rect(s, rect, _mix(col, (255, 255, 255), 0.18),
               _mix(col, (0, 0, 0), 0.25))


def _grain(s, rect, tag, n=150):
    """Subtle surface grain so nothing reads as a flat fill."""
    rect = pygame.Rect(rect)
    if rect.w <= 2 or rect.h <= 2:
        return
    g = pygame.Surface(rect.size, pygame.SRCALPHA)
    rng = np.random.default_rng(_seed(tag))
    for _ in range(n):
        x = int(rng.integers(0, rect.w))
        y = int(rng.integers(0, rect.h))
        g.set_at((x, y), (0, 0, 0, 20) if rng.random() < 0.5
                 else (255, 255, 255, 14))
    s.blit(g, rect.topleft)


def _skid(s, w, h, col=_METAL_DARK):
    """Contact shadow + the landing-skid frame a surface module sits on:
    twin beam, queenposts, regolith-sunk feet pads, orange lift point."""
    gy = h - 20
    _contact(s, w, h)
    x0, x1 = int(w * 0.10), int(w * 0.90)
    for fx in (x0 + 8, w // 2, x1 - 8):
        pygame.draw.ellipse(s, (*_SHADOW, 96), (fx - 9, gy + 2, 18, 6))
        _grad_rect(s, pygame.Rect(fx - 7, gy - 4, 14, 9), _GRAPH_HI,
                   _GRAPH_LO, radius=2)
        pygame.draw.rect(s, _GRAPH_LO, (fx - 3, gy - 8, 6, 6))
    _grad_rect(s, pygame.Rect(x0, gy - 16, x1 - x0, 10),
               _mix(col, (255, 255, 255), 0.28), _mix(col, (0, 0, 0), 0.35),
               radius=3)
    pygame.draw.line(s, _mix(col, (255, 255, 255), 0.45),
                     (x0 + 2, gy - 15), (x1 - 2, gy - 15), 2)
    _stripe(s, pygame.Rect(x0, gy - 16, 10, 10))


# ------------------------------------------------------ the modules --
# All drawers run on a 2x canvas (default 176x192); ground = h - 20.

def _d_drill(s, w, h):
    """Polar ice drill: derrick truss, travelling block, winch, spoil."""
    gy = h - 20
    _skid(s, w, h)
    cx = w // 2
    top = 26
    foot = gy - 16
    for side, c in ((-1, _GRAPH_HI), (1, _GRAPH_LO)):   # masts: lit / shaded
        pygame.draw.line(s, c, (cx + side * 22, foot),
                         (cx + side * 13, top), 5)
    for i in range(5):                                  # cross bracing
        y0 = top + 12 + i * (foot - top - 16) // 5
        y1 = top + 12 + (i + 1) * (foot - top - 16) // 5
        xo0 = 22 - 9 * (1 - (y0 - top) / (foot - top))
        xo1 = 22 - 9 * (1 - (y1 - top) / (foot - top))
        pygame.draw.line(s, (120, 126, 138), (cx - xo0, y0),
                         (cx + xo1, y1), 2)
        pygame.draw.line(s, (52, 56, 66), (cx + xo0, y0), (cx - xo1, y1), 2)
    _grad_rect(s, pygame.Rect(cx - 26, 12, 52, 18), _ALU_HI, _ALU_LO,
               radius=4)                                # crown block
    _bolts(s, [(cx - 18, 21), (cx + 18, 21)])
    _lamp(s, cx, 8, _LAMP_WARN, 3)
    pygame.draw.line(s, (70, 74, 84), (cx, 30), (cx, gy - 6), 5)
    pygame.draw.line(s, (150, 156, 168), (cx - 2, 30), (cx - 2, gy - 6), 1)
    blk = pygame.Rect(cx - 15, 78, 30, 22)              # travelling block
    _grad_rect(s, blk, _WHITE_HI, _WHITE_LO, radius=4)
    _stripe(s, pygame.Rect(blk.x, blk.y + 14, blk.w, 5))
    _lamp(s, blk.right + 4, blk.y + 4, _LAMP_OK, 3)
    _grad_rect(s, pygame.Rect(cx - 14, gy - 14, 28, 10), _GRAPH_HI,
               _GRAPH_LO, radius=2)                     # well collar
    pygame.draw.line(s, (160, 166, 178), (cx - 14, gy - 14),
                     (cx + 14, gy - 14), 2)
    win = pygame.Rect(26, 132, 30, 24)                  # hoist winch
    _grad_rect(s, win, _GRAPH_HI, _GRAPH_LO, radius=3)
    pygame.draw.circle(s, _ALU_HI, win.center, 8)
    pygame.draw.circle(s, _ALU_LO, win.center, 8, 2)
    pygame.draw.line(s, (38, 40, 48), win.center, (cx - 20, 18), 1)
    pygame.draw.ellipse(s, (*_SHADOW, 80), (cx + 18, gy - 4, 26, 8))
    for i, r in enumerate((6, 4, 3)):                   # spoil pile
        pygame.draw.circle(s, _mix(_GRAPH_HI, (255, 255, 255), 0.2),
                           (cx + 26 + i * 7, gy - 4 - i), r)


def _d_electrolyzer(s, w, h):
    """Electrolysis skid: white pressure vessel, lit sight glasses."""
    gy = h - 20
    _skid(s, w, h)
    body = pygame.Rect(24, 78, 128, 64)
    _cyl(s, body, _WHITE_LO, _WHITE_HI, radius=26)
    pygame.draw.rect(s, (70, 76, 88), body, 2, border_radius=26)
    _grad_rect(s, pygame.Rect(body.x, body.y + 6, 12, body.h - 12),
               _WHITE_LO, _mix(_WHITE_LO, (0, 0, 0), 0.25), horiz=True,
               radius=6)                                # dished end
    for fr in (0.36, 0.68):
        x = body.x + int(body.w * fr)
        _seam(s, x, body.y + 4, body.bottom - 4)
        _bolts(s, [(x - 4, body.y + 10), (x - 4, body.bottom - 10)])
    for i in range(3):                                  # lit sight glasses
        cxg = 62 + i * 28
        pygame.draw.circle(s, (40, 44, 52), (cxg, 100), 10)
        glow = pygame.Surface((36, 36), pygame.SRCALPHA)
        pygame.draw.circle(glow, (*_CYAN, 36), (18, 18), 16)
        s.blit(glow, (cxg - 18, 82))
        pygame.draw.circle(s, _mix(_CYAN, (0, 40, 70), 0.35), (cxg, 100), 8)
        pygame.draw.circle(s, _mix(_CYAN, (255, 255, 255), 0.5),
                           (cxg - 3, 97), 3)
    _grad_rect(s, pygame.Rect(44, 60, 10, 20), _GRAPH_HI, _GRAPH_LO)
    pygame.draw.circle(s, _ORANGE, (49, 58), 5)         # relief valve wheel
    pygame.draw.circle(s, _ORANGE_DK, (49, 58), 5, 1)
    _grad_rect(s, pygame.Rect(130, 60, 8, 20), _GRAPH_HI, _GRAPH_LO)
    pygame.draw.lines(s, (150, 156, 168), False,
                      [(134, 60), (134, 52), (148, 52), (148, 80)], 3)
    _stripe(s, pygame.Rect(130, 124, 20, 8))
    pygame.draw.rect(s, (52, 56, 64), (40, 124, 22, 10), border_radius=2)
    for i in range(3):                                  # stencil ticks
        pygame.draw.line(s, (180, 184, 192), (43 + i * 6, 127),
                         (43 + i * 6, 131), 1)
    _lamp(s, 142, 70, _LAMP_OK, 3)
    _grain(s, body, "elec")


def _d_sabatier(s, w, h):
    """Methanation reactor: MLI-wrapped hot section, burner glow port."""
    gy = h - 20
    _skid(s, w, h)
    body = pygame.Rect(16, 92, 144, 46)
    _cyl(s, body, _WHITE_LO, _WHITE_HI, radius=23)
    pygame.draw.rect(s, (70, 76, 88), body, 2, border_radius=23)
    _mli(s, pygame.Rect(54, 90, 68, 50), "sab")         # gold hot section
    for x in (50, 124):                                 # flange rings
        _grad_rect(s, pygame.Rect(x, 88, 6, 54), _ALU_HI, _ALU_LO)
        _bolts(s, [(x + 3, 94), (x + 3, 136)])
    glow = pygame.Surface((36, 36), pygame.SRCALPHA)    # burner port
    pygame.draw.circle(glow, (255, 150, 60, 50), (18, 18), 17)
    s.blit(glow, (12, 97))
    pygame.draw.circle(s, (60, 50, 44), (30, 115), 8)
    pygame.draw.circle(s, (255, 178, 80), (30, 115), 6)
    pygame.draw.circle(s, (255, 236, 180), (29, 114), 3)
    cond = pygame.Rect(128, 58, 32, 26)                 # condenser
    _grad_rect(s, cond, _ALU_HI, _ALU_LO, radius=4)
    for i in range(3):
        pygame.draw.line(s, (90, 96, 108), (cond.x + 4, cond.y + 6 + i * 7),
                         (cond.right - 4, cond.y + 6 + i * 7), 2)
    pygame.draw.lines(s, (150, 156, 168), False,
                      [(140, 92), (140, 84)], 4)
    _grad_rect(s, pygame.Rect(40, 76, 8, 18), _GRAPH_HI, _GRAPH_LO)
    pygame.draw.circle(s, _ORANGE, (44, 74), 5)
    pygame.draw.circle(s, _ORANGE_DK, (44, 74), 5, 1)
    _lamp(s, 152, 96, _LAMP_OK, 3)
    _grain(s, body, "sab2")


def _d_co2(s, w, h):
    """Atmosphere intake: shrouded fan, recessed mouth, filter cassette."""
    gy = h - 20
    _skid(s, w, h)
    house = pygame.Rect(30, 54, 110, gy - 12 - 54)
    _grad_rect(s, house, _ALU_HI, _ALU_LO, radius=16)
    pygame.draw.rect(s, (70, 76, 88), house, 2, border_radius=16)
    cxf, cyf = 84, 106
    pygame.draw.circle(s, (18, 20, 26), (cxf, cyf), 40)  # intake mouth
    ring = pygame.Rect(cxf - 44, cyf - 44, 88, 88)
    pygame.draw.arc(s, (222, 226, 234), ring, math.pi * 0.4,
                    math.pi * 1.15, 5)                  # lit shroud rim
    pygame.draw.arc(s, (54, 58, 68), ring, math.pi * 1.3,
                    math.pi * 2.25, 5)
    inner = pygame.Rect(cxf - 36, cyf - 36, 72, 72)
    pygame.draw.arc(s, (8, 9, 12), inner, math.pi * 0.35,
                    math.pi * 1.2, 7)                   # recess inner shadow
    pygame.draw.arc(s, (130, 136, 148), inner, math.pi * 1.45,
                    math.pi * 2.1, 3)                   # lip catchlight
    for k in range(4):                                  # blades
        a = k * math.pi / 2 + 0.55
        pygame.draw.line(s, (96, 102, 114), (cxf, cyf),
                         (cxf + int(30 * math.cos(a)),
                          cyf + int(30 * math.sin(a))), 7)
    _dome(s, pygame.Rect(cxf - 9, cyf - 9, 18, 18), _ALU_LO, _ALU_HI)
    for dy in (-14, 0, 14):                             # safety grille
        pygame.draw.line(s, (40, 44, 52),
                         (cxf - int(math.sqrt(max(0, 34 ** 2 - dy * dy))),
                          cyf + dy),
                         (cxf + int(math.sqrt(max(0, 34 ** 2 - dy * dy))),
                          cyf + dy), 2)
    filt = pygame.Rect(138, 96, 26, 48)                 # filter cassette
    _grad_rect(s, filt, _GRAPH_HI, _GRAPH_LO, radius=4)
    _stripe(s, pygame.Rect(filt.x + 4, filt.y + 20, filt.w - 8, 6))
    _bolts(s, [(filt.x + 6, filt.y + 6), (filt.x + 6, filt.bottom - 6)])
    _lamp(s, 40, 62, _LAMP_OK, 3)
    _grain(s, house, "co2")


def _d_pump(s, w, h):
    """Shoreline pump: white house, truss boom, hose into the liquid."""
    gy = h - 20
    _contact(s, w, h, cx=int(w * 0.30), span=0.5)
    for fx in (22, 64):
        _pad_shadow(s, fx, gy + 4)
        _grad_rect(s, pygame.Rect(fx - 7, gy - 4, 14, 9), _GRAPH_HI,
                   _GRAPH_LO, radius=2)
    house = pygame.Rect(12, 96, 62, gy - 8 - 96)
    _grad_rect(s, house, _WHITE_HI, _WHITE_LO, radius=6)
    pygame.draw.rect(s, (70, 76, 88), house, 2, border_radius=6)
    _seam(s, house.x + 30, house.y + 4, house.bottom - 4)
    _window(s, pygame.Rect(house.x + 8, house.y + 10, 16, 12))
    pygame.draw.circle(s, _ORANGE, (house.right - 8, house.y + 30), 6)
    pygame.draw.circle(s, _ORANGE_DK, (house.right - 8, house.y + 30), 6, 2)
    pygame.draw.line(s, (44, 47, 56), (house.right - 8, house.y + 30),
                     (house.right - 8, house.y + 22), 2)
    boom_y0, boom_y1 = house.y + 8, 88                  # truss boom
    pygame.draw.line(s, (150, 156, 168), (house.right, boom_y0),
                     (158, boom_y1), 6)
    pygame.draw.line(s, (84, 90, 102), (house.right, boom_y0 + 4),
                     (158, boom_y1 + 4), 2)
    for i in range(4):
        bx = house.right + 10 + i * 18
        by = boom_y0 - (boom_y0 - boom_y1) * (bx - house.right) // 84
        pygame.draw.line(s, (96, 102, 114), (bx, by + 4), (bx + 8, by - 2), 2)
    pygame.draw.line(s, (38, 40, 48), (house.centerx, house.y),
                     (158, boom_y1), 1)                 # stay cable
    pygame.draw.lines(s, (52, 48, 42), False,           # drop hose
                      [(158, boom_y1), (160, 120), (154, gy + 4)], 4)
    pygame.draw.ellipse(s, (*_SHADOW, 90), (142, gy + 2, 26, 7))
    _grad_rect(s, pygame.Rect(146, gy - 4, 18, 9), _GRAPH_HI, _GRAPH_LO,
               radius=3)                                # intake bell
    _lamp(s, house.x + 8, house.y - 4, _LAMP_OK, 3)
    _grain(s, house, "pump")


def _d_solar(s, w, h):
    """Tracking solar wings: dark cell glass, specular sweep, tripod."""
    gy = h - 20
    cx = w // 2
    _contact(s, w, h, span=0.34)
    for side in (-1, 1):                                # tripod legs
        fx = cx + side * 28
        _pad_shadow(s, fx, gy + 3, 8)
        pygame.draw.line(s, _GRAPH_LO if side > 0 else _GRAPH_HI,
                         (cx, gy - 26), (fx, gy + 2), 5)
        pygame.draw.rect(s, _GRAPH_LO, (fx - 6, gy, 12, 5), border_radius=2)
    _cyl(s, pygame.Rect(cx - 5, 96, 10, gy - 96), _GRAPH_LO, _GRAPH_HI,
         horiz=False)                                   # mast
    drv = pygame.Rect(cx - 11, 124, 22, 18)             # drive box
    _grad_rect(s, drv, _ALU_HI, _ALU_LO, radius=3)
    _lamp(s, cx, 118, _LAMP_OK, 3)
    pygame.draw.circle(s, _ALU_HI, (cx, 96), 7)         # gimbal
    pygame.draw.circle(s, (60, 64, 74), (cx, 96), 7, 2)
    for side in (-1, 1):
        panel = pygame.Rect(0, 0, 74, 62)
        panel.center = (cx + side * 46, 66)
        _grad_rect(s, panel, _mix(_PANEL_BLUE, (255, 255, 255), 0.18),
                   _mix(_PANEL_BLUE, (0, 0, 0), 0.35), radius=3)
        pygame.draw.rect(s, (188, 194, 204), panel, 2, border_radius=3)
        for i in range(1, 3):
            pygame.draw.line(s, (16, 24, 44),
                             (panel.x, panel.y + i * panel.h // 3),
                             (panel.right, panel.y + i * panel.h // 3), 2)
        for i in range(1, 5):
            pygame.draw.line(s, (16, 24, 44),
                             (panel.x + i * panel.w // 5, panel.y),
                             (panel.x + i * panel.w // 5, panel.bottom), 2)
        sheen = pygame.Surface(panel.size, pygame.SRCALPHA)
        pygame.draw.polygon(sheen, (210, 230, 255, 44),
                            [(4, panel.h - 6), (panel.w * 0.34, 4),
                             (panel.w * 0.52, 4), (panel.w * 0.16,
                                                   panel.h - 6)])
        s.blit(sheen, panel.topleft)                    # sun glint
        pygame.draw.line(s, (38, 40, 48), (cx, 92), (panel.centerx,
                                                     panel.bottom), 1)


def _d_reactor(s, w, h):
    """Fission unit: graphite cask, umbrella radiator, warning band."""
    gy = h - 20
    cx = w // 2
    _contact(s, w, h, span=0.6)
    drum = pygame.Rect(cx - 32, 86, 64, gy - 12 - 86)
    for side in (-1, 1):                                # stand legs + guys
        fx = cx + side * 44
        _pad_shadow(s, fx, gy + 3, 7)
        pygame.draw.line(s, (38, 40, 48), (cx + side * 26, 92),
                         (fx, gy + 1), 1)               # guy wire
        pygame.draw.rect(s, _GRAPH_LO, (fx - 4, gy - 3, 8, 6))
    for side in (-1, 1):
        pygame.draw.line(s, _GRAPH_HI if side < 0 else _GRAPH_LO,
                         (cx + side * 22, drum.bottom - 2),
                         (cx + side * 28, gy + 2), 5)
    _cyl(s, drum, _GRAPH_LO, _GRAPH_HI, radius=8, horiz=False)
    pygame.draw.rect(s, (36, 40, 48), drum, 2, border_radius=8)
    pygame.draw.polygon(s, _mix(_ALU_HI, (255, 255, 255), 0.1),
                        [(cx, 86), (cx - 44, 50), (cx, 58)])   # umbrella
    pygame.draw.polygon(s, _ALU_LO, [(cx, 86), (cx + 44, 50), (cx, 58)])
    for i in range(5):                                  # radiator fins
        t = (i + 1) / 6
        pygame.draw.line(s, (70, 76, 88), (cx, 86 - int(t * 28)),
                         (cx - int(t * 44), 86 - int(t * 36) + 14), 1)
        pygame.draw.line(s, (54, 58, 68), (cx, 86 - int(t * 28)),
                         (cx + int(t * 44), 86 - int(t * 36) + 14), 1)
    band = pygame.Rect(drum.x + 4, drum.bottom - 18, drum.w - 8, 9)
    _stripe(s, band)                                    # warning band
    for i in range(3):
        pygame.draw.line(s, (30, 30, 34), (band.x + 8 + i * 16, band.bottom),
                         (band.x + 16 + i * 16, band.y), 3)
    pygame.draw.circle(s, (218, 222, 230), (cx, drum.y + 26), 9)  # trefoil
    for k in range(3):
        a = math.pi / 2 + k * 2 * math.pi / 3
        pygame.draw.line(s, (40, 40, 46), (cx, drum.y + 26),
                         (cx + int(7 * math.cos(a)),
                          drum.y + 26 - int(7 * math.sin(a))), 4)
    _lamp(s, drum.x + 6, drum.y + 6, _LAMP_OK, 3)
    _lamp(s, drum.right - 6, drum.y + 6, _LAMP_OK, 3)
    _grain(s, drum, "reac")


def _d_hab(s, w, h):
    """Crew can: white cylinder hull, lit windows, recessed airlock,
    handrails, floodlight pool — the heart of the night scene."""
    gy = h - 20
    _skid(s, w, h)
    hull = pygame.Rect(14, 64, 148, gy - 14 - 64)
    _cyl(s, hull, _WHITE_LO, _WHITE_HI, radius=26)
    pygame.draw.rect(s, (70, 76, 88), hull, 2, border_radius=26)
    for fr in (0.16, 0.42, 0.66):
        x = hull.x + int(hull.w * fr)
        _seam(s, x, hull.y + 6, hull.bottom - 6)
        _bolts(s, [(x - 4, hull.y + 14), (x - 4, hull.bottom - 14)])
    _stripe(s, pygame.Rect(hull.x + 8, hull.bottom - 22, hull.w - 16, 8))
    for i in range(4):                                  # NO STEP ticks
        pygame.draw.line(s, (74, 80, 92), (hull.x + 22 + i * 12,
                                           hull.bottom - 27),
                         (hull.x + 28 + i * 12, hull.bottom - 27), 2)
    for i in range(3):                                  # lit cabin windows
        _window(s, pygame.Rect(34 + i * 30, hull.y + 26, 17, 13))
    frame = pygame.Rect(hull.right - 36, hull.bottom - 60, 28, 52)
    pygame.draw.rect(s, _GRAPH_LO, frame, border_radius=5)   # airlock frame
    rec = frame.inflate(-8, -8)
    pygame.draw.rect(s, (26, 28, 34), rec, border_radius=4)  # recess
    pygame.draw.line(s, (150, 156, 168), (rec.right - 1, rec.y + 2),
                     (rec.right - 1, rec.bottom - 2), 2)     # lip catchlight
    door = rec.inflate(-8, -12)
    _grad_rect(s, door, _WHITE_MID, _WHITE_LO, radius=3)
    _window(s, pygame.Rect(door.centerx - 4, door.y + 6, 9, 8))
    for hx in (frame.x - 6, frame.right + 5):           # orange handrails
        pygame.draw.line(s, _ORANGE, (hx, frame.y + 6),
                         (hx, frame.bottom - 2), 3)
        pygame.draw.line(s, _ORANGE_DK, (hx + 1, frame.y + 6),
                         (hx + 1, frame.bottom - 2), 1)
    _lamp(s, frame.centerx, frame.y - 5, _LAMP_OK, 3)
    pygame.draw.line(s, (90, 96, 108), (44, hull.y + 2), (44, 40), 2)
    _lamp(s, 44, 36, _LAMP_WARN, 3)                     # anti-collision
    pygame.draw.line(s, (90, 96, 108), (64, hull.y + 2), (64, 50), 2)
    pygame.draw.arc(s, (190, 196, 206), pygame.Rect(54, 42, 20, 13),
                    math.pi * 0.05, math.pi * 0.95, 3)  # dish on its mast
    fx = int(w * 0.55) + 8                              # floodlight mast
    flood = pygame.Surface((100, 132), pygame.SRCALPHA)
    pygame.draw.polygon(flood, (255, 222, 160, 30),
                        [(78, 4), (4, 128), (96, 128)])
    pygame.draw.ellipse(flood, (255, 222, 160, 40), (8, 114, 88, 16))
    s.blit(flood, (fx - 72, 46))
    pygame.draw.line(s, (90, 96, 108), (fx, hull.y + 2), (fx, 50), 3)
    pygame.draw.line(s, (60, 64, 74), (fx, 50), (fx - 6, 48), 4)
    pygame.draw.circle(s, (255, 240, 210), (fx - 5, 49), 4)
    _grain(s, hull, "hab")


def _d_tanks(s, w, h):
    """Cryo farm: gold-MLI spheres in graphite saddles, manifold pipe."""
    gy = h - 20
    _skid(s, w, h)
    r = 28
    pipe_y = gy - 12
    pygame.draw.line(s, (60, 64, 74), (22, pipe_y + 2), (156, pipe_y + 2), 2)
    pygame.draw.line(s, (150, 156, 168), (22, pipe_y), (156, pipe_y), 3)
    for i in range(3):
        cx = 35 + i * 53
        cy = gy - 36
        sad = pygame.Rect(cx - 22, gy - 18, 44, 12)     # saddle cradle
        _grad_rect(s, sad, _GRAPH_HI, _GRAPH_LO, radius=3)
        ao = pygame.Surface((44, 14), pygame.SRCALPHA)  # sphere-saddle AO
        pygame.draw.ellipse(ao, (*_SHADOW, 90), (4, 0, 36, 12))
        s.blit(ao, (cx - 22, gy - 26))
        pygame.draw.circle(s, _MLI_LO, (cx, cy), r)     # gold sphere
        _dome(s, pygame.Rect(cx - r + 1, cy - r + 1, r * 2 - 2, r * 2 - 2),
              _MLI_LO, _MLI_HI)
        for k in (-1, 1):                               # quilt seams
            pygame.draw.arc(s, _MLI_LO,
                            pygame.Rect(cx - r + (8 if k > 0 else 2),
                                        cy - r, int(r * 1.4), r * 2),
                            math.pi * 0.5, math.pi * 1.5, 2)
        pygame.draw.arc(s, _MLI_LO, pygame.Rect(cx - r, cy - 10, r * 2, 20),
                        math.pi, math.pi * 2, 2)
        pygame.draw.arc(s, (60, 44, 22), pygame.Rect(cx - r, cy - r,
                                                     r * 2, r * 2),
                        math.pi * 1.15, math.pi * 1.85, 4)  # dark belly
        frost = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
        pygame.draw.arc(frost, (235, 242, 250, 70),
                        frost.get_rect(), math.pi * 1.25, math.pi * 1.75, 6)
        s.blit(frost, (cx - r, cy - r + 4))             # boiloff frost
        pygame.draw.line(s, (110, 116, 128), (cx, cy + r - 4),
                         (cx, pipe_y), 3)               # riser
        pygame.draw.circle(s, _ORANGE, (cx, pipe_y - 7), 5)
        pygame.draw.circle(s, _ORANGE_DK, (cx, pipe_y - 7), 5, 2)
    _lamp(s, 152, gy - 40, _LAMP_OK, 3)
    for i in range(3):                                  # stencil ticks
        pygame.draw.line(s, (70, 76, 86), (146 + i * 5, gy - 28),
                         (146 + i * 5, gy - 23), 2)


def _d_battery(s, w, h):
    """Battery bank: graphite cabinet, recessed green charge windows."""
    gy = h - 20
    _skid(s, w, h)
    box = pygame.Rect(28, 88, 120, gy - 14 - 88)
    _grad_rect(s, box, _GRAPH_HI, _GRAPH_LO, radius=6)
    pygame.draw.rect(s, (36, 40, 48), box, 2, border_radius=6)
    for i in range(4):                                  # vent louvres
        pygame.draw.line(s, (38, 42, 50), (box.x + 8, box.y + 6 + i * 4),
                         (box.right - 8, box.y + 6 + i * 4), 2)
    fills = (0.85, 0.55, 0.70, 0.40)
    for i in range(4):                                  # recessed cells
        slot = pygame.Rect(box.x + 10 + i * 27, box.y + 26, 19, 42)
        pygame.draw.rect(s, (20, 22, 28), slot, border_radius=3)
        pygame.draw.line(s, (8, 9, 12), (slot.x, slot.y + 1),
                         (slot.right - 1, slot.y + 1), 2)   # inner shadow
        fh = int((slot.h - 8) * fills[i])
        bar = pygame.Rect(slot.x + 3, slot.bottom - 4 - fh, slot.w - 6, fh)
        _grad_rect(s, bar, _mix(_LAMP_OK, (255, 255, 255), 0.2),
                   _mix(_LAMP_OK, (0, 60, 30), 0.4), radius=2)
        gl = pygame.Surface((slot.w + 12, slot.h + 12), pygame.SRCALPHA)
        pygame.draw.rect(gl, (*_LAMP_OK, 18), gl.get_rect(),
                         border_radius=6)
        s.blit(gl, (slot.x - 6, slot.y - 6))
    _bolts(s, [(box.x + 6, box.y + 6), (box.right - 6, box.y + 6),
               (box.x + 6, box.bottom - 6), (box.right - 6, box.bottom - 6)])
    pygame.draw.polygon(s, _ORANGE,                     # flash mark
                        [(box.x + 13, box.y - 12), (box.x + 5, box.y + 2),
                         (box.x + 11, box.y + 2), (box.x + 9, box.y + 14),
                         (box.x + 18, box.y - 1), (box.x + 12, box.y - 1)])
    _lamp(s, box.right - 8, box.y - 6, _LAMP_WARN, 3)
    pygame.draw.lines(s, (40, 42, 50), False,           # conduit to ground
                      [(box.right, box.bottom - 10), (box.right + 12,
                                                      box.bottom - 6),
                       (box.right + 14, gy + 2)], 4)
    _grain(s, box, "batt")


def _d_radiator(s, w, h):
    """Heat rejection wing pair: white panels, coolant runs, pump."""
    gy = h - 20
    cx = w // 2
    _contact(s, w, h, span=0.36)
    for side in (-1, 1):
        fx = cx + side * 24
        _pad_shadow(s, fx, gy + 3, 7)
        pygame.draw.line(s, _GRAPH_HI if side < 0 else _GRAPH_LO,
                         (cx, gy - 22), (fx, gy + 2), 5)
    _cyl(s, pygame.Rect(cx - 4, 56, 8, gy - 56), _GRAPH_LO, _GRAPH_HI,
         horiz=False)
    pmp = pygame.Rect(cx - 12, gy - 36, 24, 22)         # coolant pump
    _grad_rect(s, pmp, _ALU_HI, _ALU_LO, radius=3)
    _lamp(s, cx, pmp.y - 5, _LAMP_OK, 3)
    for side in (-1, 1):
        panel = pygame.Rect(0, 0, 64, 84)
        panel.center = (cx + side * 46, 100)
        _grad_rect(s, panel, _WHITE_HI, _WHITE_MID, radius=3)
        pygame.draw.rect(s, _ALU_LO, panel, 2, border_radius=3)
        for i in range(1, 7):                           # coolant tubes
            yy = panel.y + i * panel.h // 7
            pygame.draw.line(s, (206, 210, 220), (panel.x + 6, yy),
                             (panel.right - 6, yy), 2)
        hx = panel.x + 2 if side > 0 else panel.right - 8
        _grad_rect(s, pygame.Rect(hx, panel.y + 4, 6, panel.h - 8),
                   _ALU_HI, _ALU_LO)                    # header pipe
        edge = panel.x if side > 0 else panel.right - 1
        pygame.draw.line(s, (70, 76, 88), (edge, panel.y),
                         (edge, panel.bottom), 2)       # AO at the mast
        pygame.draw.line(s, (110, 116, 128),
                         (cx + side * 6, pmp.y + 4),
                         (hx + 3, panel.bottom - 6), 3)


def _d_lab(s, w, h):
    """Science/clean box: white body, big lit cyan glass, instruments."""
    gy = h - 20
    _skid(s, w, h)
    box = pygame.Rect(16, 80, 116, gy - 14 - 80)
    _grad_rect(s, box, _WHITE_HI, _WHITE_LO, radius=8)
    pygame.draw.rect(s, (70, 76, 88), box, 2, border_radius=8)
    for fr in (0.32, 0.64):
        x = box.x + int(box.w * fr)
        _seam(s, x, box.y + 4, box.bottom - 4)
    _bolts(s, [(box.x + 8, box.y + 8), (box.right - 8, box.y + 8),
               (box.x + 8, box.bottom - 8), (box.right - 8, box.bottom - 8)])
    _window(s, pygame.Rect(box.x + 12, box.y + 16, 72, 18), col=_CYAN,
            mullion=2)
    _stripe(s, pygame.Rect(box.x + 6, box.bottom - 14, box.w - 12, 7))
    ann = pygame.Rect(132, gy - 14 - 58, 28, 58)        # airlock annex
    _grad_rect(s, ann, _ALU_HI, _ALU_LO, radius=5)
    pygame.draw.rect(s, (70, 76, 88), ann, 2, border_radius=5)
    rec = pygame.Rect(ann.x + 5, ann.y + 14, ann.w - 10, 34)
    pygame.draw.rect(s, (26, 28, 34), rec, border_radius=3)
    pygame.draw.line(s, (150, 156, 168), (rec.right - 1, rec.y + 2),
                     (rec.right - 1, rec.bottom - 2), 2)
    _grad_rect(s, rec.inflate(-6, -10), _WHITE_MID, _WHITE_LO, radius=2)
    pygame.draw.line(s, _ORANGE, (rec.x + 4, rec.centery),
                     (rec.right - 4, rec.centery), 3)   # door handle
    _lamp(s, ann.centerx, ann.y + 7, _LAMP_OK, 3)
    pygame.draw.line(s, (90, 96, 108), (40, box.y + 2), (40, 56), 2)
    pygame.draw.arc(s, (210, 214, 224), pygame.Rect(28, 44, 24, 18),
                    math.pi * 0.1, math.pi * 0.9, 3)    # dish
    pygame.draw.line(s, (130, 136, 148), (100, box.y + 2), (100, 50), 1)
    pygame.draw.circle(s, (190, 196, 206), (100, 48), 2)  # whip antenna
    sens = pygame.Rect(110, 68, 18, 12)
    _grad_rect(s, sens, _GRAPH_HI, _GRAPH_LO, radius=2)
    _grain(s, box, "lab")


def _d_foundry(s, w, h):
    """Fab shed: north-light roof, corrugated wall, hot pour door."""
    gy = h - 20
    _skid(s, w, h)
    shed = pygame.Rect(10, 84, 156, gy - 12 - 84)
    _grad_rect(s, shed, _ALU_HI, _ALU_LO, radius=4)
    pygame.draw.rect(s, (70, 76, 88), shed, 2, border_radius=4)
    for x in range(shed.x + 8, shed.right - 4, 10):     # corrugation
        pygame.draw.line(s, (132, 138, 150), (x, shed.y + 8),
                         (x, shed.bottom - 6), 1)
    for i in range(4):                                  # sawtooth roof
        x0 = shed.x + i * 39
        pygame.draw.polygon(s, _GRAPH_LO,
                            [(x0, shed.y), (x0 + 39, shed.y - 18),
                             (x0 + 39, shed.y)])
        pygame.draw.line(s, _GRAPH_HI, (x0, shed.y), (x0 + 39, shed.y - 18),
                         2)                             # lit slope
        sky = pygame.Rect(x0 + 35, shed.y - 15, 4, 14)  # skylight glass
        gl = pygame.Surface((sky.w * 4, sky.h * 3), pygame.SRCALPHA)
        pygame.draw.rect(gl, (*_WIN_WARM, 30), gl.get_rect(),
                         border_radius=4)
        s.blit(gl, (sky.x - sky.w, sky.y - sky.h))
        _grad_rect(s, sky, _mix(_WIN_WARM, (255, 255, 255), 0.3),
                   _mix(_WIN_WARM, (120, 70, 30), 0.3))
    pygame.draw.line(s, (60, 64, 74), (shed.x, shed.y), (shed.right,
                                                         shed.y), 2)
    door = pygame.Rect(18, shed.bottom - 46, 30, 44)    # pour door
    pygame.draw.rect(s, _GRAPH_LO, door, border_radius=4)
    inn = door.inflate(-8, -8)
    pygame.draw.rect(s, (16, 14, 14), inn, border_radius=3)
    _grad_rect(s, inn.inflate(-6, -10), (255, 206, 120), (226, 92, 30),
               radius=2)                                # the melt glows
    gl2 = pygame.Surface((door.w * 3, door.h * 2), pygame.SRCALPHA)
    pygame.draw.ellipse(gl2, (255, 160, 70, 40), gl2.get_rect())
    s.blit(gl2, (door.x - door.w, door.y - door.h // 2))
    pool = pygame.Surface((56, 12), pygame.SRCALPHA)    # glow pool out front
    pygame.draw.ellipse(pool, (255, 200, 130, 30), pool.get_rect())
    s.blit(pool, (door.x - 6, gy - 4))
    stack = pygame.Rect(140, 28, 12, 58)                # stack
    _cyl(s, stack, _GRAPH_LO, _GRAPH_HI, horiz=False)
    _stripe(s, pygame.Rect(stack.x, stack.y + 8, stack.w, 7))
    pygame.draw.rect(s, (30, 32, 38), (stack.x - 1, stack.y, stack.w + 2, 4))
    for i, r in enumerate((7, 5)):                      # slag heap
        pygame.draw.circle(s, (52, 50, 52), (60 + i * 9, gy - 3 - i * 2), r)
    pygame.draw.line(s, (90, 96, 108), (shed.x + 6, shed.y + 5),
                     (shed.right - 6, shed.y + 5), 2)   # crane rail
    _lamp(s, door.centerx, door.y - 6, _LAMP_WARN, 3)
    _grain(s, shed, "fnd")


def _d_greenhouse(s, w, h):
    """Grow vault: glowing barrel glasshouse, plant rows, white annex."""
    gy = h - 20
    _skid(s, w, h)
    vault = pygame.Rect(16, 72, 116, gy - 12 - 72)
    halo = pygame.Surface((vault.w + 28, vault.h + 24), pygame.SRCALPHA)
    pygame.draw.ellipse(halo, (255, 222, 190, 14), halo.get_rect())
    s.blit(halo, (vault.x - 14, vault.y - 14))          # the glow carries
    tmp = pygame.Surface(vault.size, pygame.SRCALPHA)   # lit glass barrel
    for i in range(vault.h):
        t = i / max(vault.h - 1, 1)
        pygame.draw.line(tmp, _mix((255, 240, 212), (176, 128, 100),
                                   t ** 1.1), (0, i), (vault.w, i))
    msk = pygame.Surface(vault.size, pygame.SRCALPHA)
    pygame.draw.rect(msk, (255, 255, 255, 255), msk.get_rect(),
                     border_top_left_radius=54, border_top_right_radius=54)
    tmp.blit(msk, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
    for i in range(6):                                  # plant silhouettes
        px = 10 + i * 19
        pygame.draw.circle(tmp, (52, 84, 56), (px, vault.h - 10), 8)
        pygame.draw.circle(tmp, (38, 64, 42), (px + 7, vault.h - 6), 6)
    s.blit(tmp, vault.topleft)
    half = vault.w / 2
    for i in range(7):                                  # frame ribs
        x = vault.x + 2 + i * (vault.w - 4) // 6
        nu = (x - vault.centerx) / half
        ytop = vault.y + int(54 * (1 - math.sqrt(max(0.0, 1 - nu * nu)))
                             ) if abs(nu) > 0.55 else vault.y
        pygame.draw.line(s, (70, 76, 88), (x, ytop + 2),
                         (x, vault.bottom - 2), 2)
    pygame.draw.rect(s, (70, 76, 88), vault, 2,
                     border_top_left_radius=54, border_top_right_radius=54)
    pool = pygame.Surface((vault.w, 16), pygame.SRCALPHA)
    pygame.draw.ellipse(pool, (255, 214, 180, 30), pool.get_rect())
    s.blit(pool, (vault.x, gy - 4))                     # light pool
    ann = pygame.Rect(132, 96, 28, gy - 12 - 96)        # white annex
    _grad_rect(s, ann, _WHITE_HI, _WHITE_LO, radius=5)
    pygame.draw.rect(s, (70, 76, 88), ann, 2, border_radius=5)
    rec = pygame.Rect(ann.x + 5, ann.bottom - 40, ann.w - 10, 32)
    pygame.draw.rect(s, (26, 28, 34), rec, border_radius=3)
    _grad_rect(s, rec.inflate(-6, -8), _WHITE_MID, _WHITE_LO, radius=2)
    pygame.draw.line(s, _ORANGE, (rec.x + 3, rec.centery),
                     (rec.right - 3, rec.centery), 3)
    _lamp(s, ann.centerx, ann.y + 6, _LAMP_OK, 3)


def _d_robot(s, w, h):
    """Surface worker bot parked at its charge post, cable plugged in."""
    gy = h - 20
    _contact(s, w, h, cx=64, span=0.46)
    post = pygame.Rect(118, gy - 44, 6, 44)             # charge post
    _pad_shadow(s, 121, gy + 3, 7)
    _grad_rect(s, post, _GRAPH_HI, _GRAPH_LO)
    head = pygame.Rect(110, gy - 52, 20, 10)
    _grad_rect(s, head, _ALU_HI, _ALU_LO, radius=3)
    _lamp(s, 120, gy - 56, _LAMP_OK, 3)
    pygame.draw.lines(s, (40, 42, 50), False,           # charge cable
                      [(118, gy - 18), (104, gy - 6), (94, gy - 14)], 3)
    body = pygame.Rect(34, gy - 34, 60, 22)
    for wx in (44, 60, 76, 90):                         # wheel shadows
        pygame.draw.ellipse(s, (*_SHADOW, 110), (wx - 7, gy - 1, 14, 6))
    _grad_rect(s, body, _ALU_HI, _ALU_LO, radius=6)
    pygame.draw.rect(s, (70, 76, 88), body, 2, border_radius=6)
    for i in range(2):                                  # orange chevrons
        pygame.draw.line(s, _ORANGE, (body.right - 16 + i * 7, body.y + 4),
                         (body.right - 22 + i * 7, body.bottom - 4), 3)
    for wx in (44, 60, 76, 90):                         # wheels
        pygame.draw.circle(s, (30, 32, 38), (wx, gy - 8), 8)
        pygame.draw.circle(s, (14, 15, 18), (wx, gy - 8), 8, 2)
        pygame.draw.circle(s, (130, 136, 148), (wx, gy - 8), 3)
    pygame.draw.line(s, (90, 96, 108), (46, body.y), (46, body.y - 16), 3)
    cam = pygame.Rect(40, body.y - 24, 13, 9)           # sensor head
    _grad_rect(s, cam, _GRAPH_HI, _GRAPH_LO, radius=2)
    pygame.draw.circle(s, _CYAN, (cam.x + 4, cam.centery), 2)
    pygame.draw.lines(s, (150, 156, 168), False,        # work arm + tool
                      [(40, body.y - 4), (24, gy - 44), (14, gy - 26)], 4)
    pygame.draw.circle(s, (70, 76, 88), (14, gy - 24), 4)
    _lamp(s, body.right - 5, body.y - 4, _LAMP_WARN, 2)
    _grain(s, body, "bot")


def _d_recycler(s, w, h):
    """RX-22 reclaimer: feed conveyor, hopper, shredder, sorted bins."""
    gy = h - 20
    _skid(s, w, h)
    pygame.draw.line(s, (36, 38, 46), (14, gy - 4), (70, 74), 10)  # belt
    pygame.draw.line(s, (96, 102, 114), (14, gy - 8), (70, 70), 2)
    for i in range(5):                                  # rollers
        t = i / 4
        pygame.draw.circle(s, (70, 76, 88),
                           (int(14 + 56 * t), int(gy - 4 - (gy - 78) * t)),
                           3)
    hop = [(58, 72), (118, 72), (98, 112), (78, 112)]   # hopper
    pygame.draw.polygon(s, _ALU_LO, hop)
    pygame.draw.polygon(s, _ALU_HI, [(58, 72), (88, 72), (84, 112),
                                     (78, 112)])        # lit half
    pygame.draw.polygon(s, (70, 76, 88), hop, 2)
    pygame.draw.line(s, (222, 226, 234), (58, 72), (118, 72), 3)  # rim
    pygame.draw.line(s, (40, 44, 52), (60, 76), (116, 76), 2)  # inner shade
    shred = pygame.Rect(64, 112, 48, 28)                # shredder
    _grad_rect(s, shred, _GRAPH_HI, _GRAPH_LO, radius=3)
    for i in range(3):
        pygame.draw.line(s, _ORANGE, (shred.x + 6 + i * 14, shred.bottom - 4),
                         (shred.x + 12 + i * 14, shred.y + 4), 3)
    _bolts(s, [(shred.x + 5, shred.y + 5), (shred.right - 5, shred.y + 5)])
    for i, col in enumerate(((128, 132, 140), (150, 96, 60),
                             (108, 128, 108))):         # sorted stock bins
        bin_r = pygame.Rect(118 + i * 15, gy - 32, 13, 20)
        _grad_rect(s, bin_r, _mix(col, (255, 255, 255), 0.2),
                   _mix(col, (0, 0, 0), 0.3), radius=2)
        pygame.draw.circle(s, _mix(col, (255, 255, 255), 0.35),
                           (bin_r.centerx - 2, bin_r.y - 2), 4)
        pygame.draw.circle(s, _mix(col, (0, 0, 0), 0.2),
                           (bin_r.centerx + 3, bin_r.y - 1), 3)
    _lamp(s, shred.right + 5, shred.y - 4, _LAMP_WARN, 3)


def _d_massdriver(s, w, h):
    """Launch rail on trusses: coil rings climbing to the muzzle."""
    gy = h - 20
    _contact(s, w, h, span=0.9)
    p0, p1 = (14, gy - 8), (164, 28)
    for t in (0.32, 0.58, 0.82):                        # support trusses
        rx = int(p0[0] + (p1[0] - p0[0]) * t)
        ry = int(p0[1] + (p1[1] - p0[1]) * t)
        _pad_shadow(s, rx, gy + 3, 8)
        pygame.draw.line(s, _GRAPH_HI, (rx, ry), (rx - 8, gy + 2), 4)
        pygame.draw.line(s, _GRAPH_LO, (rx, ry), (rx + 8, gy + 2), 4)
        pygame.draw.line(s, (70, 76, 88), (rx - 6, gy - 10),
                         (rx + 6, gy - 10), 2)
    pygame.draw.line(s, (60, 64, 74), p0, p1, 7)        # the rail
    pygame.draw.line(s, (150, 156, 168), (p0[0], p0[1] - 4),
                     (p1[0], p1[1] - 4), 2)             # lit top chord
    for i in range(8):                                  # accel coils
        t = 0.12 + i * 0.11
        rx = int(p0[0] + (p1[0] - p0[0]) * t)
        ry = int(p0[1] + (p1[1] - p0[1]) * t)
        pygame.draw.line(s, (210, 214, 224), (rx - 4, ry - 9),
                         (rx + 2, ry + 9), 4)
        pygame.draw.line(s, (90, 96, 108), (rx + 3, ry + 7),
                         (rx + 5, ry + 9), 2)
        if i % 3 == 0:
            _lamp(s, rx, ry - 13, _LAMP_WARN, 2)
    _stripe(s, pygame.Rect(152, 24, 16, 8))             # muzzle band
    breech = pygame.Rect(18, gy - 36, 32, 24)           # breech house
    _grad_rect(s, breech, _WHITE_HI, _WHITE_LO, radius=4)
    pygame.draw.rect(s, (70, 76, 88), breech, 2, border_radius=4)
    _stripe(s, pygame.Rect(breech.x, breech.bottom - 8, breech.w, 5))
    cab = pygame.Rect(56, gy - 30, 36, 20)              # capacitor bank
    _grad_rect(s, cab, _GRAPH_HI, _GRAPH_LO, radius=3)
    for i in range(3):
        _lamp(s, cab.x + 8 + i * 10, cab.y + 6, _LAMP_OK, 2)
    pygame.draw.lines(s, (40, 42, 50), False,
                      [(cab.right, cab.bottom - 4), (108, gy - 2),
                       (120, gy - 24)], 3)              # power feed
    pyl = pygame.Rect(0, 0, 12, 7)                      # payload slug
    pyl.center = (int(p0[0] + (p1[0] - p0[0]) * 0.2),
                  int(p0[1] + (p1[1] - p0[1]) * 0.2) - 7)
    _grad_rect(s, pyl, _WHITE_HI, _WHITE_LO, radius=3)


def _d_vault(s, w, h):
    """Buried hab: regolith berm over a cylinder, recessed lit entry."""
    gy = h - 20
    _contact(s, w, h, span=0.92)
    mound = pygame.Rect(10, 56, 156, (gy + 8 - 56) * 2)
    clip = s.get_clip()
    s.set_clip(pygame.Rect(0, 0, w, gy + 6))
    tmp = pygame.Surface(mound.size, pygame.SRCALPHA)
    for i in range(mound.h):
        t = i / max(mound.h - 1, 1)
        pygame.draw.line(tmp, _mix((124, 118, 108), (52, 48, 46),
                                   min(1.0, t * 1.9)), (0, i), (mound.w, i))
    msk = pygame.Surface(mound.size, pygame.SRCALPHA)
    pygame.draw.ellipse(msk, (255, 255, 255, 255), msk.get_rect())
    tmp.blit(msk, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
    spec = pygame.Surface(mound.size, pygame.SRCALPHA)
    pygame.draw.ellipse(spec, (255, 255, 255, 30),
                        (mound.w * 0.12, mound.h * 0.06, mound.w * 0.36,
                         mound.h * 0.16))
    tmp.blit(spec, (0, 0))
    s.blit(tmp, mound.topleft)
    s.set_clip(clip)
    rng = np.random.default_rng(_seed("vault"))
    for _ in range(40):                                 # regolith clods
        rx = int(rng.integers(20, 156))
        ry = int(rng.integers(64, gy + 2))
        nu = (rx - 88) / 78
        if ry < 56 + (1 - math.sqrt(max(0.0, 1 - nu * nu))) * (gy - 56):
            continue
        c = (96, 90, 82) if rng.random() < 0.5 else (66, 62, 58)
        pygame.draw.circle(s, c, (rx, ry), int(rng.integers(1, 3)))
    frame = pygame.Rect(70, gy - 40, 36, 40)            # entry portal
    pygame.draw.rect(s, _GRAPH_LO, frame,
                     border_top_left_radius=14, border_top_right_radius=14)
    rec = frame.inflate(-10, -8)
    rec.bottom = frame.bottom
    pygame.draw.rect(s, (22, 24, 30), rec,
                     border_top_left_radius=10, border_top_right_radius=10)
    pygame.draw.line(s, (150, 156, 168), (rec.right - 1, rec.y + 4),
                     (rec.right - 1, rec.bottom - 2), 2)
    door = rec.inflate(-8, -10)
    door.bottom = rec.bottom
    _grad_rect(s, door, _WHITE_MID, _WHITE_LO, radius=3)
    _window(s, pygame.Rect(door.centerx - 4, door.y + 5, 9, 8))
    for hx in (frame.x - 5, frame.right + 4):
        pygame.draw.line(s, _ORANGE, (hx, frame.y + 10),
                         (hx, frame.bottom - 2), 3)
    _lamp(s, frame.centerx, frame.y - 5, _LAMP_WARN, 3)
    pool = pygame.Surface((52, 14), pygame.SRCALPHA)
    pygame.draw.ellipse(pool, (255, 214, 150, 34), pool.get_rect())
    s.blit(pool, (frame.centerx - 26, gy - 2))          # entry light pool
    vent = pygame.Rect(124, 58, 9, 26)                  # berm vent
    _cyl(s, vent, _GRAPH_LO, _GRAPH_HI, horiz=False)
    pygame.draw.rect(s, (30, 32, 38), (vent.x - 2, vent.y, vent.w + 4, 4))


_DRAWERS = {
    # extraction rigs
    "drill_ice": _d_drill, "ice_corer": _d_drill, "rodwell": _d_drill,
    "ice_strip_miner": _d_drill, "drum_excavator": _d_drill,
    "bucket_wheel": _d_drill, "volatile_oven": _d_foundry,
    # atmosphere intakes / liquid acquisition
    "co2_intake": _d_co2, "venus_intake": _d_co2, "titan_intake": _d_co2,
    "lake_pump": _d_pump,
    # chemistry skids
    "electrolyzer": _d_electrolyzer, "electrolyzer_soec": _d_electrolyzer,
    "soxe": _d_electrolyzer, "bosch": _d_electrolyzer,
    "haber_loop": _d_electrolyzer, "mmh_loop": _d_electrolyzer,
    "nto_plant": _d_electrolyzer, "polymer_plant": _d_electrolyzer,
    "sabatier": _d_sabatier, "fab_chem_plant": _d_sabatier,
    # refining, furnaces and fab sheds
    "ilmenite_line": _d_foundry, "carbothermal": _d_foundry,
    "mre_cell": _d_foundry, "mond_refinery": _d_foundry,
    "aluminum_line": _d_foundry, "dri_steel": _d_foundry,
    "basalt_furnace": _d_foundry, "glass_furnace": _d_foundry,
    "ffc_titanium": _d_foundry, "he3_kiln": _d_foundry,
    "machine_shop": _d_foundry, "struct_mill": _d_foundry,
    "fab_foundry_mill": _d_foundry, "fab_machine_shop": _d_foundry,
    "fab_assembly_hall": _d_foundry, "fab_waam": _d_foundry,
    "yard_extension": _d_foundry,
    # clean rooms / labs
    "fab_elec_assy": _d_lab, "fab_wafer_fab": _d_lab,
    "fab_printer_poly": _d_lab, "fab_printer_lpbf": _d_lab,
    "science_lab": _d_lab, "med_bay": _d_lab, "pharma_lab": _d_lab,
    # habitation
    "hab_module": _d_hab, "hab_rigid": _d_hab, "hab_inflatable": _d_hab,
    "airlock": _d_hab,
    "regolith_vault": _d_vault, "basalt_hab": _d_vault,
    "storm_shelter": _d_vault,
    # food
    "salad_rack": _d_greenhouse, "greenhouse": _d_greenhouse,
    "bio_farm": _d_greenhouse,
    # power and thermal
    "solar_array": _d_solar, "solar_blanket": _d_solar,
    "reactor_100": _d_reactor, "reactor_kilo": _d_reactor,
    "battery_pack": _d_battery, "rfc_unit": _d_battery,
    "thermal_battery": _d_battery,
    "radiator_wing": _d_radiator, "radiator_high": _d_radiator,
    # storage and logistics
    "tank_farm": _d_tanks, "recycler": _d_recycler,
    "mass_driver": _d_massdriver,
    "bot_worker": _d_robot, "bot_mule": _d_robot,
}


def module_sprite(key: str, w: int = 88, h: int = 96) -> pygame.Surface:
    """The drawn structure for one CATALOG module key."""
    ck = (key, w, h)
    hit = _MODULE_CACHE.get(ck)
    if hit is not None:
        return hit
    drawer = _DRAWERS.get(key, _d_electrolyzer)
    surf = _at2x(drawer, w, h)
    _MODULE_CACHE[ck] = surf
    return surf


def walker_sprite(name: str, frame: int, size: int = 18) -> pygame.Surface:
    """A two-frame suited colonist: white EVA suit, orange accents, a
    per-crew muted ID patch, grounded by its own contact shadow."""
    ck = (name, frame % 2, size)
    hit = _WALKER_CACHE.get(ck)
    if hit is not None:
        return hit
    rng = np.random.default_rng(_seed(name))
    tint = ((196, 92, 40), (96, 118, 160), (116, 138, 98),
            (150, 120, 164), (170, 148, 88))[int(rng.integers(5))]

    def draw(s, w, h):
        cx = w // 2
        for f, a in ((1.0, 50), (0.6, 95)):             # contact shadow
            rr = pygame.Rect(0, 0, max(2, int(w * 0.62 * f)),
                             max(2, int(6 * f)))
            rr.center = (cx + 1, h - 4)
            pygame.draw.ellipse(s, (*_SHADOW, a), rr)
        spread = int(w * 0.16) if frame % 2 == 0 else int(w * 0.06)
        hip = (cx, int(h * 0.62))
        for side, col in ((-1, _mix(_WHITE_LO, (0, 0, 0), 0.15)),
                          (1, _WHITE_MID)):             # far / near leg
            ft = (cx + side * spread, h - 5)
            pygame.draw.line(s, col, hip, ft, 5)
            pygame.draw.rect(s, _GRAPH_LO, (ft[0] - 3, h - 8, 7, 5),
                             border_radius=2)           # boot
        pygame.draw.rect(s, _mix(_WHITE_LO, (0, 0, 0), 0.2),
                         (cx - 11, int(h * 0.36), 6, int(h * 0.24)),
                         border_radius=2)               # PLSS pack
        _grad_rect(s, pygame.Rect(cx - 7, int(h * 0.32), 14,
                                  int(h * 0.32)), _WHITE_HI, _WHITE_LO,
                   radius=4)                            # torso
        pygame.draw.rect(s, _ORANGE, (cx - 7, int(h * 0.40), 14, 3))
        pygame.draw.rect(s, tint, (cx + 2, int(h * 0.47), 4, 6),
                         border_radius=1)               # crew ID patch
        arm = int(w * 0.12) if frame % 2 == 0 else int(w * 0.04)
        for side in (-1, 1):
            sh = (cx + side * 6, int(h * 0.37))
            pygame.draw.line(s, _WHITE_MID if side > 0
                             else _mix(_WHITE_LO, (0, 0, 0), 0.1), sh,
                             (sh[0] + side * arm, int(h * 0.55)), 4)
        hr = max(4, int(h * 0.13))                      # helmet + visor
        hc = (cx, int(h * 0.20))
        pygame.draw.circle(s, _WHITE_HI, hc, hr)
        pygame.draw.circle(s, _WHITE_LO, hc, hr, 2)
        pygame.draw.circle(s, _GLASS, (hc[0] + 2, hc[1]), max(2, hr - 3))
        s.set_at((hc[0] + 3, hc[1] - 2), (240, 244, 250))
        pygame.draw.line(s, _ORANGE, (cx - 7, int(h * 0.33)),
                         (cx + 7, int(h * 0.33)), 2)    # shoulder stripe

    surf = _at2x(draw, size, size + 4)
    _WALKER_CACHE[ck] = surf
    return surf
