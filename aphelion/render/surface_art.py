"""Surface-scene dressing for the flown verbs (ascent/descent): scattering
sky gradients with a baked sun, parallax ridge silhouettes, fBM ground
strips, and the launch-pad complex. All procedural (numpy + pygame.draw),
deterministic (seeded by body id), headless-safe (plain Surfaces, no
display), and cached at module level — every public call is O(1) after the
first hit.

MISSION FILM discipline (design/ART-DIRECTION.md): the sky bakes its sun at
(0.70 w, 0.16 h), so the key light comes from the UPPER RIGHT in every
surface frame and all shading agrees with it — ridge rim light on sun-side
slopes, ground micro-relief embossing, cylinder speculars, and every cast /
contact shadow falling LEFT. No surface bigger than ~40 px is a flat fill
(gradient + seeded grain throughout); emitters (hangar windows, floodlight
lamps, beacons) are the only things that glow.

The sky is a three-stop nonlinear gradient (zenith -> mid -> horizon) with
a desaturated haze shelf, a warm exponential horizon glow, and per-pixel
int16 dither so the 24-bit ramp doesn't band (720p bands without it — keep
the dither). Callers fade it over the starfield with set_alpha(rho^0.35),
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

# the baked sun lives at this frame fraction -> key light from upper right
_SUN_XF, _SUN_YF = 0.70, 0.16
_ORANGE = (224, 84, 30)                      # international orange accent
_SHADOW_RGB = (8, 10, 14)

_SKY_CACHE: dict[tuple, pygame.Surface] = {}
_GROUND_CACHE: dict[tuple, pygame.Surface] = {}
_RIDGE_CACHE: dict[tuple, list[tuple[pygame.Surface, float]]] = {}
_PAD_CACHE: list[pygame.Surface] = []
_SUN_SPRITES: dict[int, pygame.Surface] = {}


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
          base: int = 4, tile_x: bool = False) -> np.ndarray:
    """Seeded 2-D value-noise fBM in [0, 1], shape (w, h). With tile_x the
    field wraps horizontally with period w (the ground strip is blitted
    twice with that period — a non-periodic field shows a hard seam)."""
    out = np.zeros((w, h))
    amp, tot = 1.0, 0.0
    for octave in range(octaves):
        cw = base * (2 ** octave)
        ch = max(2, int(cw * h / max(w, 1)))
        lat = rng.random((cw + 1, ch + 1))
        if tile_x:
            lat[cw, :] = lat[0, :]
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

def _sun_sprite(sun_r: int) -> pygame.Surface:
    """Photographic sun: small near-white disc, warm gaussian bloom, a soft
    anamorphic horizontal streak and a faint vertical diffraction spike —
    the camera-artifact treatment from the art bible, not a flat ball."""
    cached = _SUN_SPRITES.get(sun_r)
    if cached is not None:
        return cached
    half = int(sun_r * 5.0)
    d = 2 * half
    dx = (np.arange(d, dtype=float) - (half - 0.5))[:, None]   # axis 0 = x
    dy = (np.arange(d, dtype=float) - (half - 0.5))[None, :]
    rr = np.hypot(dx, dy) / float(sun_r)
    a = np.clip((0.97 - rr) / 0.46, 0.0, 1.0) ** 1.5           # soft-limb disc
    a = a + 0.50 * np.exp(-np.maximum(rr - 0.55, 0.0) ** 2 / 0.50)
    a = a + 0.15 * np.exp(-rr / 2.3)                           # wide bloom
    a = a + 0.13 * (np.exp(-(dy / (0.26 * sun_r)) ** 2)        # anamorphic
                    * np.exp(-np.abs(dx) / (2.6 * sun_r)))
    a = a + 0.07 * (np.exp(-(dx / (0.10 * sun_r)) ** 2)        # diffraction
                    * np.exp(-np.abs(dy) / (1.2 * sun_r)))
    a = np.clip(a, 0.0, 1.0)
    sun = pygame.Surface((d, d), pygame.SRCALPHA)
    core = np.clip((0.95 - rr) / 0.55, 0.0, 1.0)[..., None]
    warm = np.array((255.0, 232.0, 192.0))
    white = np.array((255.0, 252.0, 244.0))
    rgb = pygame.surfarray.pixels3d(sun)
    rgb[...] = (warm[None, None, :]
                + (white - warm)[None, None, :] * core + 0.5).astype(np.uint8)
    del rgb
    alpha = pygame.surfarray.pixels_alpha(sun)
    alpha[...] = (a * 248.0 + 0.5).astype(np.uint8)
    del alpha
    _SUN_SPRITES[sun_r] = sun
    return sun


def sky_surface(size: tuple[int, int], body_id: str) -> pygame.Surface:
    """Opaque scattering-sky gradient: three nonlinear stops, deepened
    high-altitude zenith, a desaturated aerial-haze shelf over the horizon,
    a warm horizon glow, int16 de-banding dither, and the baked sun with
    directional bloom. Fade over space with set_alpha()."""
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
    glow = np.asarray(pal.glow, float)
    u1 = np.clip(t / 0.62, 0.0, 1.0) ** 1.25
    u2 = np.clip((t - 0.62) / 0.38, 0.0, 1.0) ** 1.10
    col = zen[None, :] * (1.0 - u1[:, None]) + mid[None, :] * u1[:, None]
    col = col * (1.0 - u2[:, None]) + hor[None, :] * u2[:, None]
    # high-altitude darkening: the top of frame reads as thin air
    u0 = np.clip(t / 0.34, 0.0, 1.0)
    col *= (0.72 + 0.28 * (u0 * u0 * (3.0 - 2.0 * u0)))[:, None]
    # desaturated haze shelf pooled above the horizon (aerial perspective)
    hazec = 0.52 * hor + 0.33 * np.array((234.0, 236.0, 239.0)) + 0.15 * glow
    col += np.exp(-(((1.0 - t) / 0.21) ** 1.6))[:, None] * hazec[None, :] * 0.30
    # warm horizon glow
    col += np.exp(-(((1.0 - t) / 0.085) ** 2))[:, None] * glow[None, :] * 0.42
    col_u8 = np.clip(col, 0.0, 255.0)
    rng = np.random.default_rng(_seed("sky:" + k[2]))
    arr = np.tile(col_u8[None, :, :], (w, 1, 1)).astype(np.int16)
    arr += rng.integers(-2, 3, (w, h, 1), dtype=np.int16)   # de-banding dither
    surf = pygame.Surface((w, h))
    pygame.surfarray.blit_array(surf, np.clip(arr, 0, 255).astype(np.uint8))
    if pal.sun_r > 0:
        sun = _sun_sprite(pal.sun_r)
        surf.blit(sun, (int(w * _SUN_XF) - sun.get_width() // 2,
                        int(h * _SUN_YF) - sun.get_height() // 2))
    _SKY_CACHE[k] = surf
    return surf


# ---- terrain -----------------------------------------------------------------

def ridge_layers(body_id: str, w: int) -> list[tuple[pygame.Surface, float]]:
    """Two parallax ridge silhouettes (far hazy, near dark), each
    RIDGE_PAD wider than the screen. Returns [(surface, parallax), ...]
    far-to-near; blit at x = -((scroll*parallax) % RIDGE_PAD),
    y = horizon_y - surface_height.

    Aerial perspective fades the far layer toward the sky (haze pools at
    its base) on atmo worlds; sun-side slopes carry a warm crest rim light
    and a brighter flank, and both layers get fBM material grain."""
    k = (_key(body_id), int(w))
    cached = _RIDGE_CACHE.get(k)
    if cached is not None:
        return cached
    gp = ground_palette(body_id)
    sp = sky_palette(body_id)
    base = np.asarray(gp.base, float)
    darkc = np.asarray(gp.dark, float)
    horc = np.asarray(sp.horizon, float)
    glowc = np.asarray(sp.glow, float)
    rw = int(w) + RIDGE_PAD
    layers: list[tuple[pygame.Surface, float]] = []
    for li, (hgt, fac) in enumerate(RIDGE_LAYERS):
        rng = np.random.default_rng(_seed(f"ridge:{k[0]}:{li}"))
        line = _fbm1(rng, rw, octaves=5, base=5 + 3 * li)
        crest = (0.18 + 0.55 * line) * hgt
        slope = np.gradient(crest)              # d(height)/dx, up-positive
        sunlit = np.clip(-slope * 2.4, -1.0, 1.0)   # right flanks face sun
        if li == 0 and gp.atmo:                 # far ridge dissolves in haze
            top = 0.36 * base + 0.64 * horc
            bot = 0.20 * base + 0.80 * (0.86 * horc + 0.14 * glowc)
        elif li == 0:                           # airless: stark, no fade
            top = 0.72 * base
            bot = 0.42 * base
        else:
            top = 0.60 * base + 0.40 * darkc
            if gp.atmo:
                top = 0.90 * top + 0.10 * horc
            bot = 0.85 * darkc
        ys = np.arange(hgt, dtype=float)[None, :]
        top_y = (hgt - crest)[:, None]
        cov = np.clip(ys - top_y + 0.5, 0.0, 1.0)           # AA crest edge
        depth = np.clip((ys - top_y) / np.maximum(crest[:, None], 1.0),
                        0.0, 1.0)
        rgbf = top[None, None, :] + (bot - top)[None, None, :] \
            * depth[..., None]
        # flank shading agrees with the sun (subtler on the hazy far layer)
        flank = 0.05 if li == 0 else 0.11
        rgbf *= (1.0 + flank * sunlit)[:, None, None]
        # material grain — never a flat fill
        grain = _fbm2(rng, rw, hgt, octaves=4, base=14)
        rgbf *= (0.94 + 0.12 * grain)[..., None]
        # crest rim light on sun-side slopes only
        rim_band = np.clip(1.0 - (ys - top_y) / 2.6, 0.0, 1.0) * cov
        rim_s = np.clip(-slope * 3.2, 0.0, 1.0)[:, None]
        if gp.atmo:
            rim_c = 0.55 * glowc + 0.45 * np.array((255.0, 250.0, 240.0))
        else:
            rim_c = np.array((232.0, 236.0, 243.0))         # cold vacuum rim
        rim_w = (0.30 if li == 0 else 0.80) * rim_band * rim_s
        rgbf = rgbf + (rim_c[None, None, :] - rgbf) * rim_w[..., None]
        surf = pygame.Surface((rw, hgt), pygame.SRCALPHA)
        rgb = pygame.surfarray.pixels3d(surf)
        rgb[...] = (np.clip(rgbf, 0.0, 255.0) + 0.5).astype(np.uint8)
        del rgb
        alpha = pygame.surfarray.pixels_alpha(surf)
        alpha[...] = (cov * 255.0 + 0.5).astype(np.uint8)
        del alpha
        layers.append((surf, fac))
    _RIDGE_CACHE[k] = layers
    return layers


def ground_strip(body_id: str, w: int, h: int = GROUND_STRIP_H) -> pygame.Surface:
    """Packed-soil / regolith band: fBM albedo patches, micro-relief
    embossed by the sun direction (lit from upper right), pebbles with
    anti-sun shadow pixels, grain, depth shading that dissolves into
    ground_palette().dark, and a broken sun-lit brink at the top edge.
    Tile it horizontally; fill anything deeper with ground_palette().dark."""
    k = (_key(body_id), int(w), int(h))
    cached = _GROUND_CACHE.get(k)
    if cached is not None:
        return cached
    rng = np.random.default_rng(_seed("ground:" + k[0]))
    gp = ground_palette(body_id)
    base = np.asarray(gp.base, float)
    dark = np.asarray(gp.dark, float)
    speck = np.asarray(gp.speck, float)
    patches = _fbm2(rng, w, h, octaves=4, base=5, tile_x=True)
    relief = _fbm2(rng, w, h, octaves=5, base=16, tile_x=True)
    fine = rng.random((w, h))
    alb = base[None, None, :] * (0.80 + 0.40 * patches)[..., None]
    pmask = np.clip((0.42 - patches) / 0.16, 0.0, 1.0)
    alb = alb * (1.0 - pmask[..., None]) \
        + dark[None, None, :] * pmask[..., None]
    # micro-relief: emboss with the key light from the upper right
    # (x-gradient wraps so the emboss tiles with the strip)
    d_dx = (np.roll(relief, -1, axis=0) - np.roll(relief, 1, axis=0)) * 0.5
    d_dy = np.gradient(relief, axis=1)
    shade = np.clip(1.0 + (-0.80 * d_dx + 0.60 * d_dy) * 18.0, 0.74, 1.28)
    alb *= shade[..., None]
    # pebbles: lit speck + a shadow pixel on the anti-sun (lower-left) side
    sp = fine > 0.9935
    sh = np.roll(sp, (-1, 1), axis=(0, 1)) & ~sp
    alb = np.where(sh[..., None], alb * 0.60, alb)
    alb = np.where(sp[..., None], speck[None, None, :] * 0.94, alb)
    # soil grain
    alb *= (1.0 + (fine[..., None] - 0.5) * 0.08)
    depth = (np.arange(h, dtype=float) / max(1, h - 1))[None, :, None]
    alb *= (1.0 - 0.50 * depth ** 1.2)
    # the deepest rows dissolve into the under-fill so the seam vanishes
    m = np.clip((depth - 0.78) / 0.22, 0.0, 1.0) * 0.85
    alb = alb * (1.0 - m) + dark[None, None, :] * m
    # broken sun-lit brink (modulated by the albedo patches, not a stripe)
    for row, fall in enumerate((1.0, 0.55, 0.25)):
        lit = 1.0 + (0.14 + 0.30 * patches[:, row]) * fall
        alb[:, row, :] = np.clip(alb[:, row, :] * lit[:, None] + 9.0 * fall,
                                 0.0, 255.0)
    surf = pygame.Surface((w, h))
    pygame.surfarray.blit_array(surf, np.clip(alb, 0.0, 255.0)
                                .astype(np.uint8))
    _GROUND_CACHE[k] = surf
    return surf


# ---- the launch pad complex ---------------------------------------------------

PAD_W, PAD_H = 420, 230
PAD_GROUND_Y = 196          # apron top row inside the sprite


def _gauss_ellipse(w: int, h: int, a: int,
                   rgb: _RGB = _SHADOW_RGB) -> pygame.Surface:
    """Soft gaussian ellipse sprite (contact shadows, soot stains)."""
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    dx = ((np.arange(w, dtype=float) - (w - 1) / 2.0) / max(w * 0.5, 1.0))
    dy = ((np.arange(h, dtype=float) - (h - 1) / 2.0) / max(h * 0.5, 1.0))
    g = np.exp(-(dx[:, None] ** 2 + dy[None, :] ** 2) * 2.6)
    rgbv = pygame.surfarray.pixels3d(s)
    rgbv[...] = rgb
    del rgbv
    al = pygame.surfarray.pixels_alpha(s)
    al[...] = (g * a + 0.5).astype(np.uint8)
    del al
    return s


def _contact(s: pygame.Surface, cx: float, cy: float, w: int, h: int,
             a: int = 80) -> None:
    """Contact shadow under a standing object, nudged anti-sun (left)."""
    s.blit(_gauss_ellipse(w, h, a), (int(cx - w / 2 - 2), int(cy - h / 2)))


def _poly_shadow(s: pygame.Surface, pts: list[tuple[int, int]],
                 a: int) -> None:
    """Alpha-blended cast-shadow polygon (draw.* would overwrite alpha)."""
    ov = pygame.Surface(s.get_size(), pygame.SRCALPHA)
    pygame.draw.polygon(ov, (*_SHADOW_RGB, a), pts)
    s.blit(ov, (0, 0))


def _glow_dot(s: pygame.Surface, x: int, y: int, r: float, rgb: _RGB,
              a: int) -> None:
    """Soft emitter halo (the ONLY bright-glow device on the pad)."""
    d = max(4, int(r * 6))
    spr = pygame.Surface((d, d), pygame.SRCALPHA)
    ax = np.arange(d, dtype=float) - (d - 1) / 2.0
    rr = np.hypot(ax[:, None], ax[None, :]) / max(r, 0.5)
    g = np.exp(-rr * rr / 2.2)
    rgbv = pygame.surfarray.pixels3d(spr)
    rgbv[...] = rgb
    del rgbv
    al = pygame.surfarray.pixels_alpha(spr)
    al[...] = (g * a + 0.5).astype(np.uint8)
    del al
    s.blit(spr, (x - d // 2, y - d // 2))


def _panel(w: int, h: int, top: _RGB, bot: _RGB, rng: np.random.Generator,
           grain: float = 2.5, streak: float = 0.0) -> pygame.Surface:
    """Opaque material panel: vertical gradient + per-column weather
    streaks + per-pixel grain. The §1.2 'never a flat fill' workhorse."""
    t = np.linspace(0.0, 1.0, h)[None, :, None]
    col = (np.asarray(top, float)[None, None, :] * (1.0 - t)
           + np.asarray(bot, float)[None, None, :] * t)
    col = np.repeat(col, w, axis=0)
    if streak > 0.0:
        ns = _fbm1(rng, w, octaves=3, base=8)
        col *= (1.0 + (ns - 0.5) * streak)[:, None, None]
    if grain > 0.0:
        col += rng.uniform(-grain, grain, (w, h, 1))
    s = pygame.Surface((w, h))
    pygame.surfarray.blit_array(s, np.clip(col, 0.0, 255.0)
                                .astype(np.uint8))
    return s


def _cyl_field(w: int, h: int, base: np.ndarray, rng: np.random.Generator,
               peak: float = 0.30) -> np.ndarray:
    """Cylinder shading field (w, h, 3): lambert roll-off across the width
    with the lit band & specular line displaced toward the sun side."""
    xs = np.linspace(-1.0, 1.0, w)
    lit = 0.36 + 0.74 * np.clip(1.0 - ((xs - peak) / 1.12) ** 2, 0.0, 1.0)
    spec = np.exp(-((xs - peak - 0.10) / 0.085) ** 2)
    vert = 1.05 - 0.16 * np.linspace(0.0, 1.0, h)
    lum = lit[:, None] * vert[None, :]
    col = base[None, None, :] * lum[..., None]
    col += (np.array((255.0, 252.0, 246.0)) * spec[:, None, None] * 0.34)
    col += rng.uniform(-2.0, 2.0, (w, h, 1))
    return col


def _blit_field(s: pygame.Surface, xy: tuple[int, int],
                col: np.ndarray) -> None:
    tmp = pygame.Surface(col.shape[:2])
    pygame.surfarray.blit_array(tmp, np.clip(col, 0.0, 255.0)
                                .astype(np.uint8))
    s.blit(tmp, xy)


def pad_complex() -> pygame.Surface:
    """The KSC-style pad, MACHINE-layer treatment: gradient-and-grain
    concrete apron with expansion joints, crawler tracks and tire stains; a
    scorched flame trench; a box-lattice service tower with strut shading,
    umbilical arms and an international-orange crane; tank-farm cylinders
    with displaced speculars; a hangar with lit windows; floodlight poles
    casting light pools; lightning masts with red beacons — and a contact
    shadow under every single thing. Blit at (pad_x - PAD_W//2,
    ground_y - PAD_GROUND_Y - 12) so the apron sits just under the
    vehicle base."""
    if _PAD_CACHE:
        return _PAD_CACHE[0]
    rng = np.random.default_rng(_seed("pad-complex"))
    s = pygame.Surface((PAD_W, PAD_H), pygame.SRCALPHA)
    cx = PAD_W // 2
    G = PAD_GROUND_Y

    # ---- ground shadow under the whole works (anchors the complex)
    s.blit(_gauss_ellipse(372, 28, 60), (cx - 190, G - 7))

    # ---- concrete apron: gradient + grain + streaks, lit brink, joints
    ap_l, ap_r, ap_h = cx - 170, cx + 170, 22
    s.blit(_panel(ap_r - ap_l, ap_h, (119, 121, 126), (82, 84, 90),
                  rng, 3.0, 0.10), (ap_l, G))
    ov = pygame.Surface((PAD_W, PAD_H), pygame.SRCALPHA)
    pygame.draw.line(ov, (176, 178, 182, 200), (ap_l + 1, G), (ap_r - 2, G), 1)
    pygame.draw.line(ov, (8, 10, 14, 80), (ap_l, G + ap_h - 1),
                     (ap_r - 1, G + ap_h - 1), 1)
    pygame.draw.line(ov, (8, 10, 14, 60), (ap_l, G + 1), (ap_l, G + ap_h - 1), 2)
    pygame.draw.line(ov, (8, 10, 14, 60), (ap_r - 1, G + 1),
                     (ap_r - 1, G + ap_h - 1), 2)
    for jx in range(ap_l + 26, ap_r - 10, 38):          # expansion joints
        if abs(jx - cx) < 46:
            continue                                    # trench interrupts
        pygame.draw.line(ov, (28, 30, 36, 120), (jx, G + 2), (jx, G + ap_h - 2), 1)
        pygame.draw.line(ov, (162, 164, 170, 55), (jx + 1, G + 2),
                         (jx + 1, G + ap_h - 2), 1)
    pygame.draw.line(ov, (28, 30, 36, 55), (ap_l + 4, G + 13),
                     (ap_r - 5, G + 13), 1)             # pour joint
    for ty in (G + 8, G + 12):                          # crawler tracks
        pygame.draw.line(ov, (22, 24, 28, 46), (cx + 30, ty), (cx + 128, ty), 2)
    for _ in range(7):                                  # tire/weather stains
        sx = int(rng.uniform(ap_l + 18, ap_r - 40))
        sw = int(rng.uniform(14, 34))
        sy = G + int(rng.uniform(4, ap_h - 7))
        pygame.draw.ellipse(ov, (14, 16, 20, int(rng.uniform(16, 34))),
                            (sx, sy, sw, 4))
    s.blit(ov, (0, 0))

    # ---- flame trench: soot stain, recessed pit, lit lip, hazard stripes
    s.blit(_gauss_ellipse(168, 24, 92), (cx - 86, G - 3))      # scorch
    tw = 38
    pit = _panel(2 * tw, 12, (34, 34, 38), (8, 8, 10), rng, 2.0)
    s.blit(pit, (cx - tw, G + 5))
    ov = pygame.Surface((PAD_W, PAD_H), pygame.SRCALPHA)
    pygame.draw.line(ov, (150, 152, 156, 190), (cx - tw, G + 4),
                     (cx + tw - 1, G + 4), 1)                  # sun-lit lip
    pygame.draw.line(ov, (0, 0, 0, 130), (cx - tw, G + 6),
                     (cx + tw - 1, G + 6), 1)                  # inner shadow
    for ex, dxn in ((cx - tw, -1), (cx + tw - 1, 1)):          # soot streaks
        for i in range(3):
            yy = G + 7 + i * 3
            pygame.draw.line(ov, (10, 10, 12, 60), (ex, yy),
                             (ex + dxn * (16 - i * 4), yy), 1)
    pygame.draw.line(ov, (*_ORANGE, 210), (cx - tw - 16, G), (cx - tw - 4, G), 2)
    pygame.draw.line(ov, (*_ORANGE, 210), (cx + tw + 4, G), (cx + tw + 16, G), 2)
    s.blit(ov, (0, 0))
    for px_ in (cx - tw - 11, cx + tw + 3):                    # hold-downs
        _contact(s, px_ + 4, G + 1, 14, 5, 70)
        s.blit(_panel(8, 7, (128, 130, 136), (88, 90, 96), rng, 2.0),
               (px_, G - 7))

    # ---- pipe run: tank farm manifold into the trench
    ov = pygame.Surface((PAD_W, PAD_H), pygame.SRCALPHA)
    pygame.draw.line(ov, (66, 68, 74, 255), (cx - 118, G + 4), (cx - 44, G + 4), 2)
    pygame.draw.line(ov, (138, 140, 146, 170), (cx - 118, G + 3),
                     (cx - 44, G + 3), 1)
    for vx in (cx - 117, cx - 95, cx - 60):
        pygame.draw.line(ov, (66, 68, 74, 255), (vx, G - 1), (vx, G + 4), 2)
    s.blit(ov, (0, 0))

    # ---- tank farm (left): vertical cylinders, orange bands, spec lines
    alu = np.array((174.0, 178.0, 185.0))
    for tx0, twd, tht in ((cx - 132, 30, 56), (cx - 96, 24, 44)):
        _contact(s, tx0 + twd / 2, G + 2, twd + 18, 8, 95)
        body = _cyl_field(twd, tht, alu, rng)
        body[:, 6:9, :] = (body[:, 6:9, :] * 0.25
                           + np.array(_ORANGE, float)[None, None, :] * 0.75)
        _blit_field(s, (tx0, G - tht), body)
        cap = pygame.Surface((twd, 7), pygame.SRCALPHA)
        pygame.draw.ellipse(cap, (199, 203, 210), (0, 0, twd, 7))
        pygame.draw.ellipse(cap, (222, 226, 233),
                            (int(twd * 0.55), 1, max(3, twd // 5), 2))
        s.blit(cap, (tx0, G - tht - 3))
        ov = pygame.Surface((PAD_W, PAD_H), pygame.SRCALPHA)
        pygame.draw.line(ov, (8, 10, 14, 90), (tx0 + 1, G - 1),
                         (tx0 + twd - 2, G - 1), 2)            # base AO ring
        pygame.draw.line(ov, (120, 124, 130, 200),               # ladder
                         (tx0 + twd - 4, G - tht + 4), (tx0 + twd - 4, G - 2), 1)
        pygame.draw.line(ov, (96, 100, 106, 255),                # vent pipe
                         (tx0 + 5, G - tht - 3), (tx0 + 5, G - tht - 9), 1)
        s.blit(ov, (0, 0))
    # horizontal run tank on saddles
    hx0, hw_, hh_ = cx - 166, 28, 12
    _contact(s, hx0 + hw_ / 2, G + 2, hw_ + 12, 6, 80)
    hbody = np.transpose(_cyl_field(hh_, hw_, alu * 0.94, rng, peak=-0.35),
                         (1, 0, 2))
    _blit_field(s, (hx0, G - hh_), hbody)
    ov = pygame.Surface((PAD_W, PAD_H), pygame.SRCALPHA)
    pygame.draw.ellipse(ov, (120, 124, 132, 255), (hx0 - 2, G - hh_, 5, hh_))
    pygame.draw.ellipse(ov, (60, 62, 68, 255),
                        (hx0 + hw_ - 3, G - hh_, 5, hh_))
    for sx_ in (hx0 + 4, hx0 + hw_ - 7):
        pygame.draw.rect(ov, (58, 60, 66, 255), (sx_, G - 2, 4, 3))
    s.blit(ov, (0, 0))

    # ---- service tower (right of vehicle): box lattice + orange crane
    txl, txr = cx + 44, cx + 58
    top_y = 30
    _contact(s, (txl + txr) / 2, G + 3, 48, 10, 95)
    _poly_shadow(s, [(txl - 2, G + 1), (txr + 2, G + 1),
                     (txr - 30, G + 17), (txl - 36, G + 17)], 38)
    for ty in range(top_y + 8, G - 8, 12):              # strut-shaded bays
        pygame.draw.line(s, (138, 142, 152), (txl + 1, ty + 11),
                         (txr - 1, ty), 2)              # sun-catching diag
        pygame.draw.line(s, (84, 88, 98), (txl + 1, ty),
                         (txr - 1, ty + 11), 2)         # shaded diag
        pygame.draw.line(s, (104, 108, 118), (txl, ty), (txr, ty), 1)
    pygame.draw.line(s, (92, 96, 106), (txl, top_y - 4), (txl, G + 2), 3)
    pygame.draw.line(s, (74, 78, 88), (txl + 2, top_y - 4), (txl + 2, G + 2), 1)
    pygame.draw.line(s, (134, 138, 148), (txr, top_y - 4), (txr, G + 2), 3)
    pygame.draw.line(s, (165, 169, 179), (txr + 1, top_y - 4), (txr + 1, G + 2), 1)
    ov = pygame.Surface((PAD_W, PAD_H), pygame.SRCALPHA)
    for py_ in (64, 108, 152):                          # work decks
        pygame.draw.rect(ov, (150, 154, 162, 255), (txl - 4, py_, txr - txl + 10, 3))
        pygame.draw.line(ov, (8, 10, 14, 110), (txl - 4, py_ + 3),
                         (txr + 6, py_ + 3), 2)         # deck drop shadow
    for ay, ay2 in ((70, 76), (114, 119)):              # umbilical arms
        pygame.draw.line(ov, (112, 116, 126, 255), (txl, ay), (cx + 18, ay2), 2)
        pygame.draw.line(ov, (70, 74, 84, 200), (txl, ay + 2),
                         (cx + 18, ay2 + 2), 1)
        pygame.draw.circle(ov, (150, 154, 162, 255), (txl, ay), 2)
    s.blit(ov, (0, 0))
    s.blit(_panel(20, 12, (126, 130, 140), (94, 98, 108), rng, 2.0),
           (txl - 3, top_y - 12))                       # head house
    pygame.draw.line(s, (168, 172, 180), (txl - 3, top_y - 12),
                     (txl + 16, top_y - 12), 1)
    jib_tip = cx - 32
    pygame.draw.line(s, _ORANGE, (txr + 2, top_y - 8),
                     (jib_tip, top_y - 2), 3)           # crane jib
    pygame.draw.line(s, (130, 90, 60), (jib_tip, top_y - 1),
                     (txr + 2, top_y - 5), 1)           # jib underside shade
    pygame.draw.line(s, (96, 100, 110), (txl + 6, top_y - 20),
                     (txl + 6, top_y - 10), 1)          # crane mast
    pygame.draw.line(s, (140, 144, 152), (txl + 6, top_y - 20),
                     (jib_tip + 6, top_y - 4), 1)       # tie rod
    pygame.draw.line(s, (40, 42, 48), (jib_tip + 2, top_y - 2),
                     (jib_tip + 2, top_y + 18), 2)      # hook cable
    pygame.draw.rect(s, _ORANGE, (jib_tip, top_y + 18, 5, 6))   # hook block
    pygame.draw.line(s, (130, 70, 40), (jib_tip, top_y + 18),
                     (jib_tip, top_y + 23), 1)          # block shaded side
    pygame.draw.line(s, (255, 160, 110), (jib_tip + 4, top_y + 18),
                     (jib_tip + 4, top_y + 23), 1)      # block lit side
    pygame.draw.rect(s, (88, 92, 102), (txr + 4, top_y - 7, 8, 6))  # counter
    pygame.draw.circle(s, (255, 74, 60), (txl + 6, top_y - 22), 2)  # beacon
    _glow_dot(s, txl + 6, top_y - 22, 3.4, (255, 90, 70), 90)

    # ---- hangar (right): gradient wall, parapet, recessed door, windows
    hg_l, hg_w, hg_t = cx + 92, 86, G - 44
    _poly_shadow(s, [(hg_l - 1, G + 1), (hg_l - 26, G + 15), (hg_l - 1, G + 15)], 36)
    s.blit(_panel(hg_w, 44, (97, 101, 109), (63, 67, 75), rng, 2.5, 0.08),
           (hg_l, hg_t))
    ov = pygame.Surface((PAD_W, PAD_H), pygame.SRCALPHA)
    for vx in range(hg_l + 5, hg_l + hg_w - 3, 6):      # corrugation
        pygame.draw.line(ov, (30, 32, 38, 26), (vx, hg_t + 2), (vx, G - 2), 1)
    pygame.draw.line(ov, (8, 10, 14, 90), (hg_l, G - 1),
                     (hg_l + hg_w - 1, G - 1), 2)       # base AO
    s.blit(ov, (0, 0))
    s.blit(_panel(hg_w + 6, 9, (132, 136, 144), (104, 108, 116), rng, 2.0),
           (hg_l - 3, hg_t - 8))                        # parapet band
    pygame.draw.line(s, (172, 174, 180), (hg_l - 3, hg_t - 8),
                     (hg_l + hg_w + 2, hg_t - 8), 1)
    ov = pygame.Surface((PAD_W, PAD_H), pygame.SRCALPHA)
    pygame.draw.line(ov, (8, 10, 14, 90), (hg_l - 3, hg_t + 1),
                     (hg_l + hg_w + 2, hg_t + 1), 1)    # parapet drop shadow
    s.blit(ov, (0, 0))
    door = pygame.Rect(hg_l + 22, G - 34, 42, 34)
    dpan = _panel(door.w, door.h, (40, 42, 48), (58, 62, 70), rng, 1.8)
    s.blit(dpan, door.topleft)
    ov = pygame.Surface((PAD_W, PAD_H), pygame.SRCALPHA)
    for dx_ in range(door.left + 6, door.right, 7):     # door seams
        pygame.draw.line(ov, (30, 32, 38, 200), (dx_, door.top + 2),
                         (dx_, door.bottom - 1), 1)
    pygame.draw.line(ov, (0, 0, 0, 110), (door.left, door.top),
                     (door.right - 1, door.top), 2)     # recess inner shadow
    pygame.draw.line(ov, (130, 134, 142, 200), (door.right - 1, door.top),
                     (door.right - 1, door.bottom - 1), 1)  # lit lip
    pygame.draw.rect(ov, (*_ORANGE, 230),
                     (door.left, door.top - 3, door.w, 3))  # header stripe
    s.blit(ov, (0, 0))
    for i, wx in enumerate((hg_l + 7, hg_l + 15, hg_l + 70, hg_l + 78)):
        pygame.draw.rect(s, (255, 216, 150), (wx, hg_t + 5, 5, 4))
        pygame.draw.rect(s, (255, 238, 196), (wx + 1, hg_t + 6, 2, 2))
        _glow_dot(s, wx + 2, hg_t + 7, 4.0, (255, 214, 150), 46)
    pygame.draw.rect(s, (44, 46, 52), (hg_l + 72, G - 12, 8, 12))  # crew door
    pygame.draw.line(s, (120, 124, 132), (hg_l + 80, G - 12), (hg_l + 80, G - 1), 1)

    # ---- lightning masts (far ends, on the soil)
    for mx in (cx - 184, cx + 186):
        _contact(s, mx, G + 2, 28, 7, 70)
        ov = pygame.Surface((PAD_W, PAD_H), pygame.SRCALPHA)
        pygame.draw.line(ov, (8, 10, 14, 36), (mx - 2, G + 3),
                         (mx - 46, G + 13), 2)          # long cast shadow
        pygame.draw.line(ov, (70, 74, 84, 56), (mx, 66), (mx - 15, G + 2), 1)
        pygame.draw.line(ov, (70, 74, 84, 56), (mx, 66), (mx + 15, G + 2), 1)
        s.blit(ov, (0, 0))
        pygame.draw.line(s, (86, 90, 100), (mx, 58), (mx, G), 2)
        pygame.draw.line(s, (132, 136, 146), (mx + 1, 58), (mx + 1, G), 1)
        pygame.draw.line(s, (96, 100, 110), (mx, 46), (mx, 58), 1)
        pygame.draw.line(s, (96, 100, 110), (mx - 6, 76), (mx + 6, 76), 1)
        pygame.draw.circle(s, (255, 74, 60), (mx, 44), 2)
        _glow_dot(s, mx, 44, 3.2, (255, 90, 70), 80)

    # ---- floodlight poles on the apron + light pools (emitters)
    for fx in (cx - 60, cx + 76):
        _contact(s, fx, G + 3, 18, 6, 85)
        ov = pygame.Surface((PAD_W, PAD_H), pygame.SRCALPHA)
        pygame.draw.line(ov, (8, 10, 14, 40), (fx - 1, G + 2),
                         (fx - 22, G + 12), 2)          # pole cast shadow
        s.blit(ov, (0, 0))
        pygame.draw.line(s, (72, 76, 84), (fx, G - 60), (fx, G), 2)
        pygame.draw.line(s, (118, 122, 130), (fx + 1, G - 60), (fx + 1, G), 1)
        pygame.draw.line(s, (98, 102, 110), (fx - 8, G - 60), (fx + 8, G - 60), 3)
        pygame.draw.line(s, (150, 154, 162), (fx - 8, G - 62), (fx + 8, G - 62), 1)
        for lx in (fx - 5, fx + 5):
            pygame.draw.circle(s, (255, 246, 216), (lx, G - 64), 2)
        _glow_dot(s, fx, G - 64, 5.0, (255, 240, 200), 78)
        pool = pygame.Surface((56, 16))
        pdx = ((np.arange(56, dtype=float) - 27.5) / 28.0)
        pdy = ((np.arange(16, dtype=float) - 7.5) / 8.0)
        pg = np.exp(-(pdx[:, None] ** 2 + pdy[None, :] ** 2) * 2.2)
        pcol = (pg[..., None] * np.array((38.0, 33.0, 19.0)))
        pygame.surfarray.blit_array(pool, pcol.astype(np.uint8))
        s.blit(pool, (fx - 28, G + 1), special_flags=pygame.BLEND_RGB_ADD)

    _PAD_CACHE.append(s)
    return s
