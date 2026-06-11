"""Surface-scene dressing for the flown verbs (ascent/descent): scattering
sky gradients with a baked sun, parallax ridge silhouettes, fBM ground
strips, and the launch-pad complex. All procedural (numpy + pygame.draw),
deterministic (seeded by body id), headless-safe (plain Surfaces, no
display), and cached at module level — every public call is O(1) after the
first hit.

The sky is a three-stop nonlinear gradient (zenith -> mid -> horizon) with
a warm exponential horizon glow and per-pixel dither so the 24-bit ramp
doesn't band. Callers fade it over the starfield with set_alpha(rho^0.35),
exactly like the old flat gradient.
"""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass

import numpy as np
import pygame

_RGB = tuple[int, int, int]


@dataclass(frozen=True, slots=True)
class SkyPal:
    zenith: _RGB
    mid: _RGB
    horizon: _RGB
    glow: _RGB
    sun_r: int          # baked sun radius px; 0 = hidden by haze


@dataclass(frozen=True, slots=True)
class GroundPal:
    base: _RGB
    dark: _RGB
    speck: _RGB
    atmo: bool          # aerial perspective on the far ridge


SKY_PALS: dict[str, SkyPal] = {
    "earth":   SkyPal((18, 58, 138), (92, 154, 216), (188, 216, 238),
                      (255, 226, 180), 40),
    "mars":    SkyPal((86, 58, 44), (170, 120, 82), (224, 176, 128),
                      (255, 210, 150), 24),
    "titan":   SkyPal((110, 72, 30), (180, 124, 52), (228, 176, 92),
                      (255, 210, 120), 0),
    "venus":   SkyPal((168, 140, 100), (208, 180, 134), (240, 218, 170),
                      (255, 236, 190), 0),
    "default": SkyPal((40, 48, 64), (96, 108, 128), (160, 170, 184),
                      (220, 225, 235), 28),
}

GROUND_PALS: dict[str, GroundPal] = {
    "earth":   GroundPal((52, 92, 46), (24, 44, 22), (120, 150, 96), True),
    "moon":    GroundPal((108, 110, 114), (54, 56, 60), (168, 170, 176), False),
    "mars":    GroundPal((158, 92, 52), (86, 46, 26), (214, 150, 100), True),
    "titan":   GroundPal((104, 80, 46), (54, 40, 22), (150, 120, 72), True),
    "venus":   GroundPal((152, 132, 102), (86, 72, 52), (200, 180, 144), True),
    "europa":  GroundPal((196, 202, 210), (108, 114, 124), (238, 242, 248), False),
    "default": GroundPal((78, 80, 86), (40, 42, 46), (120, 124, 130), False),
}

RIDGE_LAYERS = ((110, 0.22), (70, 0.45))     # (height px, parallax factor)
RIDGE_PAD = 512                              # scroll window beyond screen w
GROUND_STRIP_H = 260

_SKY_CACHE: dict[tuple, pygame.Surface] = {}
_GROUND_CACHE: dict[tuple, pygame.Surface] = {}
_RIDGE_CACHE: dict[tuple, list[tuple[pygame.Surface, float]]] = {}
_PAD_CACHE: list[pygame.Surface] = []


def _key(body_id: str) -> str:
    return body_id.rsplit(":", 1)[-1]


def _seed(s: str) -> int:
    return int.from_bytes(hashlib.blake2b(s.encode(), digest_size=8).digest(),
                          "little")


def sky_palette(body_id: str) -> SkyPal:
    return SKY_PALS.get(_key(body_id), SKY_PALS["default"])


def ground_palette(body_id: str) -> GroundPal:
    return GROUND_PALS.get(_key(body_id), GROUND_PALS["default"])


# ---- noise -------------------------------------------------------------------

def _fbm1(rng: np.random.Generator, n: int, octaves: int = 4,
          base: int = 6) -> np.ndarray:
    """Seeded 1-D value-noise fBM in [0, 1]."""
    out = np.zeros(n)
    amp, tot = 1.0, 0.0
    for octave in range(octaves):
        cells = base * (2 ** octave)
        lat = rng.random(cells + 1)
        xs = np.linspace(0.0, cells, n)
        i = np.minimum(xs.astype(np.intp), cells - 1)
        f = xs - i
        f = f * f * (3.0 - 2.0 * f)
        out += amp * (lat[i] * (1.0 - f) + lat[i + 1] * f)
        tot += amp
        amp *= 0.5
    return out / tot


def _fbm2(rng: np.random.Generator, w: int, h: int, octaves: int = 4,
          base: int = 4) -> np.ndarray:
    """Seeded 2-D value-noise fBM in [0, 1], shape (w, h)."""
    out = np.zeros((w, h))
    amp, tot = 1.0, 0.0
    for octave in range(octaves):
        cw = base * (2 ** octave)
        ch = max(2, int(cw * h / max(w, 1)))
        lat = rng.random((cw + 1, ch + 1))
        xs = np.linspace(0.0, cw, w)
        ys = np.linspace(0.0, ch, h)
        xi = np.minimum(xs.astype(np.intp), cw - 1)
        yi = np.minimum(ys.astype(np.intp), ch - 1)
        fx = (xs - xi)[:, None]
        fy = (ys - yi)[None, :]
        fx = fx * fx * (3.0 - 2.0 * fx)
        fy = fy * fy * (3.0 - 2.0 * fy)
        row0 = lat[xi][:, yi] * (1.0 - fy) + lat[xi][:, yi + 1] * fy
        row1 = lat[xi + 1][:, yi] * (1.0 - fy) + lat[xi + 1][:, yi + 1] * fy
        out += amp * (row0 * (1.0 - fx) + row1 * fx)
        tot += amp
        amp *= 0.5
    return out / tot


# ---- sky ---------------------------------------------------------------------

def sky_surface(size: tuple[int, int], body_id: str) -> pygame.Surface:
    """Opaque scattering-sky gradient with horizon glow, dither, and a
    baked soft sun. Fade over space with set_alpha()."""
    k = (int(size[0]), int(size[1]), _key(body_id))
    cached = _SKY_CACHE.get(k)
    if cached is not None:
        return cached
    w, h = k[0], k[1]
    pal = sky_palette(body_id)
    t = np.linspace(0.0, 1.0, h)
    zen = np.asarray(pal.zenith, float)
    mid = np.asarray(pal.mid, float)
    hor = np.asarray(pal.horizon, float)
    u1 = np.clip(t / 0.62, 0.0, 1.0) ** 1.25
    u2 = np.clip((t - 0.62) / 0.38, 0.0, 1.0) ** 1.10
    col = zen[None, :] * (1.0 - u1[:, None]) + mid[None, :] * u1[:, None]
    col = col * (1.0 - u2[:, None]) + hor[None, :] * u2[:, None]
    col += np.exp(-(((1.0 - t) / 0.085) ** 2))[:, None] \
        * np.asarray(pal.glow, float)[None, :] * 0.45
    col_u8 = np.clip(col, 0.0, 255.0)
    rng = np.random.default_rng(_seed("sky:" + k[2]))
    arr = np.tile(col_u8[None, :, :], (w, 1, 1)).astype(np.int16)
    arr += rng.integers(-2, 3, (w, h, 1), dtype=np.int16)   # de-banding dither
    surf = pygame.Surface((w, h))
    pygame.surfarray.blit_array(surf, np.clip(arr, 0, 255).astype(np.uint8))
    if pal.sun_r > 0:                                       # baked soft sun
        r = pal.sun_r * 3
        d = 2 * r
        ax = np.arange(d, dtype=float) - (r - 0.5)
        rr = np.hypot(ax[:, None], ax[None, :]) / pal.sun_r
        glow = np.clip(np.exp(-(rr - 1.0) * 1.9), 0.0, 1.0)
        glow[rr <= 1.0] = 1.0
        sun = pygame.Surface((d, d), pygame.SRCALPHA)
        srgb = pygame.surfarray.pixels3d(sun)
        srgb[...] = (255, 250, 236)
        del srgb
        sa = pygame.surfarray.pixels_alpha(sun)
        sa[...] = (glow * 235.0 + 0.5).astype(np.uint8)
        del sa
        surf.blit(sun, (int(w * 0.70) - r, int(h * 0.16) - r))
    _SKY_CACHE[k] = surf
    return surf


# ---- terrain -----------------------------------------------------------------

def ridge_layers(body_id: str, w: int) -> list[tuple[pygame.Surface, float]]:
    """Two parallax ridge silhouettes (far hazy, near dark), each
    RIDGE_PAD wider than the screen. Returns [(surface, parallax), ...]
    far-to-near; blit at x = -((scroll*parallax) % RIDGE_PAD),
    y = horizon_y - surface_height."""
    k = (_key(body_id), int(w))
    cached = _RIDGE_CACHE.get(k)
    if cached is not None:
        return cached
    gp = ground_palette(body_id)
    sp = sky_palette(body_id)
    rw = int(w) + RIDGE_PAD
    layers: list[tuple[pygame.Surface, float]] = []
    for li, (hgt, fac) in enumerate(RIDGE_LAYERS):
        rng = np.random.default_rng(_seed(f"ridge:{k[0]}:{li}"))
        line = _fbm1(rng, rw, octaves=5, base=5 + 3 * li)
        crest = (0.18 + 0.55 * line) * hgt
        if gp.atmo and li == 0:         # aerial perspective on the far layer
            top = tuple(int(gp.base[c] * 0.45 + sp.horizon[c] * 0.55)
                        for c in range(3))
        elif li == 0:
            top = tuple(int(c * 0.62) for c in gp.base)
        else:
            top = tuple(int(gp.base[c] * 0.55 + gp.dark[c] * 0.45)
                        for c in range(3))
        bot = tuple(int(c * 0.55) for c in top)
        surf = pygame.Surface((rw, hgt), pygame.SRCALPHA)
        ys = np.arange(hgt, dtype=float)[None, :]
        top_y = (hgt - crest)[:, None]
        cov = np.clip(ys - top_y + 0.5, 0.0, 1.0)           # AA crest edge
        depth = np.clip((ys - top_y) / np.maximum(crest[:, None], 1.0),
                        0.0, 1.0)
        rgb = pygame.surfarray.pixels3d(surf)
        for c in range(3):
            rgb[:, :, c] = (top[c] + (bot[c] - top[c]) * depth + 0.5
                            ).astype(np.uint8)
        del rgb
        alpha = pygame.surfarray.pixels_alpha(surf)
        alpha[...] = (cov * 255.0 + 0.5).astype(np.uint8)
        del alpha
        layers.append((surf, fac))
    _RIDGE_CACHE[k] = layers
    return layers


def ground_strip(body_id: str, w: int, h: int = GROUND_STRIP_H) -> pygame.Surface:
    """Textured ground band: low-frequency albedo patches + speckle +
    depth shading, with a lit 2 px crest at the top edge. Tile it
    horizontally; fill anything deeper with ground_palette().dark."""
    k = (_key(body_id), int(w), int(h))
    cached = _GROUND_CACHE.get(k)
    if cached is not None:
        return cached
    rng = np.random.default_rng(_seed("ground:" + k[0]))
    gp = ground_palette(body_id)
    base = np.asarray(gp.base, float)
    dark = np.asarray(gp.dark, float)
    speck = np.asarray(gp.speck, float)
    patches = _fbm2(rng, w, h, octaves=4, base=5)
    fine = rng.random((w, h))
    alb = base[None, None, :] * (0.78 + 0.44 * patches)[..., None]
    pmask = np.clip((0.42 - patches) / 0.16, 0.0, 1.0)
    alb = alb * (1.0 - pmask[..., None]) \
        + dark[None, None, :] * pmask[..., None]
    smask = (fine > 0.985)[..., None]
    alb = np.where(smask, speck[None, None, :], alb)
    alb *= (1.0 + (fine[..., None] - 0.5) * 0.16)
    depth = (np.arange(h, dtype=float) / max(1, h - 1))[None, :, None]
    alb *= (1.0 - 0.50 * depth ** 1.2)
    alb[:, 0:2, :] = np.clip(alb[:, 0:2, :] * 1.30 + 14.0, 0.0, 255.0)
    surf = pygame.Surface((w, h))
    pygame.surfarray.blit_array(surf, np.clip(alb, 0.0, 255.0)
                                .astype(np.uint8))
    _GROUND_CACHE[k] = surf
    return surf


# ---- the launch pad complex ---------------------------------------------------

PAD_W, PAD_H = 420, 230
PAD_GROUND_Y = 196          # apron top row inside the sprite


def pad_complex() -> pygame.Surface:
    """The KSC-style pad: concrete apron + flame trench, lattice service
    tower with crane arm, tank farm, hangar with lit windows, lightning
    masts and floodlights. Blit at (pad_x - PAD_W//2,
    ground_y - PAD_GROUND_Y - 12) so the apron sits just under the
    vehicle base."""
    if _PAD_CACHE:
        return _PAD_CACHE[0]
    s = pygame.Surface((PAD_W, PAD_H), pygame.SRCALPHA)
    cx = PAD_W // 2

    # soft ground shadow under the whole works
    sh = pygame.Surface((360, 26), pygame.SRCALPHA)
    pygame.draw.ellipse(sh, (0, 0, 0, 70), sh.get_rect())
    s.blit(sh, (cx - 180, PAD_GROUND_Y - 4))

    # concrete apron with expansion joints + flame trench
    apron = pygame.Rect(cx - 170, PAD_GROUND_Y, 340, 22)
    pygame.draw.rect(s, (96, 98, 104), apron, border_radius=3)
    pygame.draw.line(s, (134, 136, 142), (apron.left + 2, apron.top),
                     (apron.right - 3, apron.top), 2)
    for jx in range(apron.left + 24, apron.right - 8, 36):
        pygame.draw.line(s, (72, 74, 80), (jx, apron.top + 3),
                         (jx, apron.bottom - 3), 1)
    pygame.draw.ellipse(s, (26, 26, 30), (cx - 36, PAD_GROUND_Y + 6, 72, 15))
    pygame.draw.ellipse(s, (12, 12, 14), (cx - 26, PAD_GROUND_Y + 9, 52, 9))

    # service tower (lattice) + crane arm toward the vehicle
    tx = cx + 44
    for ty in range(28, PAD_GROUND_Y - 10, 11):
        pygame.draw.line(s, (96, 100, 110), (tx, ty), (tx + 13, ty + 11), 2)
        pygame.draw.line(s, (96, 100, 110), (tx + 13, ty), (tx, ty + 11), 2)
    pygame.draw.line(s, (120, 124, 134), (tx, 24), (tx, PAD_GROUND_Y + 2), 3)
    pygame.draw.line(s, (120, 124, 134), (tx + 13, 24),
                     (tx + 13, PAD_GROUND_Y + 2), 3)
    pygame.draw.line(s, (110, 114, 124), (tx - 26, 56), (tx + 2, 56), 3)
    pygame.draw.line(s, (110, 114, 124), (tx - 26, 92), (tx + 2, 92), 3)
    pygame.draw.rect(s, (104, 108, 118), (tx - 3, 18, 19, 7))
    pygame.draw.circle(s, (255, 90, 80), (tx + 6, 14), 3)

    # tank farm (left): two spheres + a horizontal cylinder
    for bx, by, br in ((cx - 116, PAD_GROUND_Y - 16, 17),
                       (cx - 78, PAD_GROUND_Y - 13, 13)):
        pygame.draw.circle(s, (166, 170, 178), (bx, by), br)
        pygame.draw.circle(s, (210, 214, 222), (bx - br // 3, by - br // 3),
                           max(2, br // 3))
        pygame.draw.line(s, (90, 92, 98), (bx - br + 3, PAD_GROUND_Y),
                         (bx + br - 3, PAD_GROUND_Y), 3)
    pygame.draw.rect(s, (148, 152, 160),
                     (cx - 158, PAD_GROUND_Y - 14, 34, 14),
                     border_radius=7)
    pygame.draw.line(s, (192, 196, 204), (cx - 154, PAD_GROUND_Y - 11),
                     (cx - 128, PAD_GROUND_Y - 11), 2)

    # hangar (right): block + roofline + door seams + lit windows
    hg = pygame.Rect(cx + 92, PAD_GROUND_Y - 46, 86, 46)
    pygame.draw.rect(s, (70, 75, 86), hg)
    pygame.draw.rect(s, (96, 102, 114), (hg.left - 3, hg.top - 6,
                                         hg.width + 6, 8), border_radius=3)
    door = pygame.Rect(hg.left + 20, hg.top + 12, 40, 34)
    pygame.draw.rect(s, (52, 56, 66), door)
    for dx in range(door.left + 6, door.right, 7):
        pygame.draw.line(s, (44, 48, 56), (dx, door.top + 1),
                         (dx, door.bottom - 1), 1)
    for wx in (hg.left + 6, hg.left + 70, hg.left + 78):
        pygame.draw.rect(s, (255, 214, 140), (wx, hg.top + 8, 4, 5))

    # lightning masts + floodlight pylons
    for mx in (cx - 184, cx + 186):
        pygame.draw.line(s, (88, 92, 102), (mx, 52), (mx, PAD_GROUND_Y), 2)
        pygame.draw.line(s, (88, 92, 102), (mx - 6, 70), (mx + 6, 70), 2)
        pygame.draw.circle(s, (140, 144, 152), (mx, 50), 3)
        pygame.draw.circle(s, (255, 90, 80), (mx, 46), 2)
    for fx in (cx - 60, cx + 110):
        pygame.draw.line(s, (84, 88, 96), (fx, PAD_GROUND_Y - 58),
                         (fx, PAD_GROUND_Y), 2)
        pygame.draw.line(s, (104, 108, 116), (fx - 7, PAD_GROUND_Y - 58),
                         (fx + 7, PAD_GROUND_Y - 58), 3)
        for lx in (fx - 5, fx + 5):
            pygame.draw.circle(s, (255, 240, 200), (lx, PAD_GROUND_Y - 60), 2)

    _PAD_CACHE.append(s)
    return s
