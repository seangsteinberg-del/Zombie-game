"""Deep-space backdrop and the luminous post pass (90-14 §1 VD-P3
"painterly depth behind the glass", §3.2 layers 1-2, §3.3 post stack).

This is the pure-pygame SOFTWARE path of 90-14 §3: a nebula/starfield
backdrop pre-rendered ONCE at init and blitted in exactly two calls per
frame (base + parallax nebula tile), a smoothscale fake-HDR bloom with
zero per-frame Surface allocations, a cached vignette, and cached SOI
boundary rings. All art is procedural and deterministic — numpy rng from
explicit seeds, no pygame.display, plain SRCALPHA surfaces only.
"""

from __future__ import annotations

import math

import numpy as np
import pygame

from aphelion.render.camera import Camera

# 90-14 palette (binding)
SPACE_BG: tuple[int, int, int] = (6, 8, 14)
ACCENT: tuple[int, int, int] = (140, 235, 255)

_GRADIENT_BOTTOM = (8, 12, 26)                  # "slightly bluer" foot
_CLOUD_COLORS = ((62, 56, 96), (44, 84, 92), (96, 62, 52))  # indigo/teal/rust
_BAND_STAR_TINT = (0.82, 0.90, 1.0)
_BRIGHT_STAR_TINTS = ((0.85, 0.92, 1.0),        # blue-white
                      (1.00, 1.00, 0.97),       # white
                      (1.00, 0.86, 0.62))       # amber
_HAZE_RGB = (96, 112, 150)
NEBULA_PARALLAX = 0.05          # backdrop px per screen-px of camera pan
SOI_RING_MAX_RADIUS_PX = 2000


def _radial_blob(radius: int, color: tuple[int, int, int],
                 peak_alpha: int) -> pygame.Surface:
    """Soft radial-gradient disc: alpha falls (1 - r)^2 from peak to 0."""
    d = 2 * radius
    ax = np.arange(d, dtype=np.float64) - (radius - 0.5)
    rr = np.hypot(ax[:, None], ax[None, :]) / radius
    a = (np.clip(1.0 - rr, 0.0, 1.0) ** 2) * peak_alpha
    spr = pygame.Surface((d, d), pygame.SRCALPHA)
    rgb = pygame.surfarray.pixels3d(spr)
    rgb[...] = color
    del rgb
    alpha = pygame.surfarray.pixels_alpha(spr)
    alpha[...] = (a + 0.5).astype(np.uint8)
    del alpha
    return spr


class Nebula:
    """Pre-rendered deep-space backdrop (built once, ~100 ms budget).

    Static layer: dark vertical gradient + diagonal milky-way haze band
    with ~900 dim stars + ~140 brighter fixed stars (a handful with
    cross-spike glints). Parallax layer: 2-3 large soft nebula clouds on
    a tileable surface, pre-tiled 2x2 so the per-frame wrap is a single
    area-blit. draw() is always exactly 2 blits, zero regeneration.
    """

    def __init__(self, size: tuple[int, int], seed: int = 2049) -> None:
        self._w, self._h = int(size[0]), int(size[1])
        rng = np.random.default_rng(seed)
        self._base = self._build_base(rng)
        tile = self._build_nebula_tile(rng)
        self._tile2 = pygame.Surface((2 * self._w, 2 * self._h),
                                     pygame.SRCALPHA)
        for ox in (0, self._w):
            for oy in (0, self._h):
                # RGBA_MAX onto an all-zero dest is an exact RGBA copy
                # (a plain blit would alpha-multiply the translucent tile).
                self._tile2.blit(tile, (ox, oy),
                                 special_flags=pygame.BLEND_RGBA_MAX)

    # -- build (init only) -------------------------------------------------

    def _build_base(self, rng: np.random.Generator) -> pygame.Surface:
        w, h = self._w, self._h
        base = pygame.Surface((w, h), pygame.SRCALPHA)
        # (a) vertical gradient, SPACE_BG -> slightly bluer
        t = np.linspace(0.0, 1.0, h)
        rgb = pygame.surfarray.pixels3d(base)
        for c in range(3):
            row = SPACE_BG[c] + (_GRADIENT_BOTTOM[c] - SPACE_BG[c]) * t
            rgb[:, :, c] = (row + 0.5).astype(np.uint8)[None, :]
        del rgb
        alpha = pygame.surfarray.pixels_alpha(base)
        alpha[...] = 255
        del alpha

        # (c) milky-way band: haze quad at 1/8 res, smoothscaled up
        ax_, ay_ = -0.1 * w, 0.10 * h
        bx_, by_ = 1.1 * w, 0.90 * h
        dx, dy = bx_ - ax_, by_ - ay_
        norm = math.hypot(dx, dy)
        sigma = 0.16 * h
        lw, lh = max(2, w // 8), max(2, h // 8)
        gx = (np.arange(lw) + 0.5) * (w / lw)
        gy = (np.arange(lh) + 0.5) * (h / lh)
        dist = np.abs((gx[:, None] - ax_) * dy - (gy[None, :] - ay_) * dx) / norm
        haze_a = np.exp(-((dist / sigma) ** 2)) * 15.0
        haze = pygame.Surface((lw, lh), pygame.SRCALPHA)
        hrgb = pygame.surfarray.pixels3d(haze)
        hrgb[...] = _HAZE_RGB
        del hrgb
        halpha = pygame.surfarray.pixels_alpha(haze)
        halpha[...] = (haze_a + 0.5).astype(np.uint8)
        del halpha
        base.blit(pygame.transform.smoothscale(haze, (w, h)), (0, 0))

        rgb = pygame.surfarray.pixels3d(base)
        # ... and ~900 tiny dim stars scattered along the band
        n = 900
        u = rng.uniform(-0.05, 1.05, n)
        perp = rng.normal(0.0, 0.55, n) * sigma
        ux, uy = dx / norm, dy / norm
        sx = ax_ + u * dx - perp * uy
        sy = ay_ + u * dy + perp * ux
        xi = np.round(sx).astype(np.int64)
        yi = np.round(sy).astype(np.int64)
        v = rng.uniform(22.0, 80.0, n)
        m = (xi >= 0) & (xi < w) & (yi >= 0) & (yi < h)
        xi, yi, v = xi[m], yi[m], v[m]
        for c, tint in enumerate(_BAND_STAR_TINT):
            rgb[xi, yi, c] = np.maximum(rgb[xi, yi, c],
                                        (v * tint).astype(np.uint8))

        # (d) ~140 brighter fixed stars with slight color variation
        nb = 140
        bx = rng.integers(4, w - 4, nb)
        by = rng.integers(4, h - 4, nb)
        bv = rng.uniform(90.0, 230.0, nb)
        tint_idx = rng.integers(0, len(_BRIGHT_STAR_TINTS), nb)
        tints = np.asarray(_BRIGHT_STAR_TINTS)
        for c in range(3):
            rgb[bx, by, c] = np.maximum(
                rgb[bx, by, c], (bv * tints[tint_idx, c]).astype(np.uint8))
        # a handful get subtle cross-spike glints
        for k in range(min(8, nb)):
            x, y, vk = int(bx[k]), int(by[k]), float(bv[k])
            tint = _BRIGHT_STAR_TINTS[int(tint_idx[k])]
            for off, fall in ((1, 0.55), (2, 0.32), (3, 0.16)):
                val = [int(min(255.0, vk * fall * tc)) for tc in tint]
                for ddx, ddy in ((off, 0), (-off, 0), (0, off), (0, -off)):
                    for c in range(3):
                        if rgb[x + ddx, y + ddy, c] < val[c]:
                            rgb[x + ddx, y + ddy, c] = val[c]
        del rgb
        return base

    def _build_nebula_tile(self, rng: np.random.Generator) -> pygame.Surface:
        """(b) 2-3 clouds of ~120 seeded translucent blobs each, drawn at
        1/4 res with wrap (tileable) and smoothscaled up for softness."""
        w, h = self._w, self._h
        qw, qh = max(1, w // 4), max(1, h // 4)
        cloud = pygame.Surface((qw, qh), pygame.SRCALPHA)
        sprites: dict[tuple[int, tuple[int, int, int], int],
                      pygame.Surface] = {}
        n_clouds = int(rng.integers(2, 4))
        for i in range(n_clouds):
            color = _CLOUD_COLORS[i % len(_CLOUD_COLORS)]
            ccx = rng.uniform(0.0, qw)
            ccy = rng.uniform(0.0, qh)
            sx = qw * rng.uniform(0.14, 0.24)
            sy = qh * rng.uniform(0.16, 0.30)
            for _ in range(120):
                px = (ccx + rng.normal(0.0, sx)) % qw
                py = (ccy + rng.normal(0.0, sy)) % qh
                r = max(3, int(rng.uniform(0.10, 0.30) * min(qw, qh)))
                a = int(rng.integers(2, 6))            # alpha 2-5
                key = (r, color, a)
                spr = sprites.get(key)
                if spr is None:
                    spr = sprites[key] = _radial_blob(r, color, a)
                x0, y0 = px - r, py - r
                d = 2 * r
                for ox in (-qw, 0, qw):                # wrap so the tile
                    if x0 + ox + d <= 0 or x0 + ox >= qw:
                        continue                        # stays seamless
                    for oy in (-qh, 0, qh):
                        if y0 + oy + d <= 0 or y0 + oy >= qh:
                            continue
                        cloud.blit(spr, (round(x0 + ox), round(y0 + oy)))
        return pygame.transform.smoothscale(cloud, (w, h))

    # -- per frame ----------------------------------------------------------

    def draw(self, screen: pygame.Surface, cam: Camera | None = None) -> None:
        """Two blits: static base, then the nebula tile parallax-shifted
        by a tiny factor of the camera center (wrapped via the 2x2 tile)."""
        screen.blit(self._base, (0, 0))
        ox = oy = 0
        if cam is not None:
            z = float(getattr(cam, "zoom", 1.0))
            ox = int((float(cam.cx) * z * NEBULA_PARALLAX) % self._w)
            oy = int((float(cam.cy) * z * NEBULA_PARALLAX) % self._h)
        screen.blit(self._tile2, (0, 0),
                    pygame.Rect(ox, oy, self._w, self._h))


class Bloom:
    """Fake-HDR glow (90-14 §3.3): downscale, soft-knee threshold in
    numpy, two smoothscale down/up roundtrips as the blur, additive
    re-composite. All work surfaces preallocated — zero per-frame
    Surface allocations; ~1-2 ms at 1280x720 with scale=4.
    """

    def __init__(self, size: tuple[int, int], scale: int = 4,
                 threshold: int = 110, strength: float = 0.8) -> None:
        w, h = int(size[0]), int(size[1])
        self._size = (w, h)
        sw, sh = max(1, w // int(scale)), max(1, h // int(scale))
        tw, th = max(1, sw // 2), max(1, sh // 2)
        self._small = pygame.Surface((sw, sh), pygame.SRCALPHA)
        self._tiny = pygame.Surface((tw, th), pygame.SRCALPHA)
        self._full = pygame.Surface((w, h), pygame.SRCALPHA)
        # soft knee as a per-channel LUT: subtract threshold, multiply by
        # a gain mapping a full 255 channel to strength * 255, clip.
        gain = float(strength) * 255.0 / max(1.0, 255.0 - float(threshold))
        self._lut = np.clip((np.arange(256) - float(threshold)) * gain,
                            0.0, 255.0).astype(np.uint8)

    def apply(self, screen: pygame.Surface) -> None:
        if screen.get_size() != self._size:
            raise ValueError(
                f"Bloom built for {self._size}, got {screen.get_size()}")
        sm = pygame.transform.smoothscale
        small_size = self._small.get_size()
        tiny_size = self._tiny.get_size()
        sm(screen, small_size, self._small)
        # threshold: channels at or below the knee map to 0, so only
        # bright pixels survive into the blur passes
        arr = pygame.surfarray.pixels3d(self._small)
        arr[...] = self._lut[arr]
        del arr
        # blur: two down/up smoothscale roundtrips
        sm(self._small, tiny_size, self._tiny)
        sm(self._tiny, small_size, self._small)
        sm(self._small, tiny_size, self._tiny)
        sm(self._tiny, small_size, self._small)
        sm(self._small, self._size, self._full)
        screen.blit(self._full, (0, 0), special_flags=pygame.BLEND_ADD)


_VIGNETTE_CACHE: dict[tuple[int, int], pygame.Surface] = {}


def vignette(size: tuple[int, int]) -> pygame.Surface:
    """Cached radial vignette: transparent center -> ~70-alpha corners,
    generated at 1/8 res with numpy and smoothscaled up."""
    key = (int(size[0]), int(size[1]))
    cached = _VIGNETTE_CACHE.get(key)
    if cached is not None:
        return cached
    w, h = key
    lw, lh = max(2, w // 8), max(2, h // 8)
    nx = np.linspace(-1.0, 1.0, lw)
    ny = np.linspace(-1.0, 1.0, lh)
    d = np.hypot(nx[:, None], ny[None, :]) / math.sqrt(2.0)
    a = np.clip((d - 0.35) / 0.65, 0.0, 1.0) ** 1.8 * 70.0
    low = pygame.Surface((lw, lh), pygame.SRCALPHA)   # RGB stays black
    alpha = pygame.surfarray.pixels_alpha(low)
    alpha[...] = (a + 0.5).astype(np.uint8)
    del alpha
    surf = pygame.transform.smoothscale(low, (w, h))
    _VIGNETTE_CACHE[key] = surf
    return surf


_SOI_RING_CACHE: dict[tuple[int, tuple[int, ...]], pygame.Surface] = {}


def soi_ring(radius_px: int,
             color: tuple[int, int, int] = ACCENT) -> pygame.Surface | None:
    """Cached faint dashed circle (peak alpha ~50) with a soft 2 px glow
    halo for SOI boundary display. Returns None above the 2000 px cap."""
    r = int(radius_px)
    if r > SOI_RING_MAX_RADIUS_PX:
        return None
    r = max(r, 6)
    key = (r, tuple(int(c) for c in color))
    cached = _SOI_RING_CACHE.get(key)
    if cached is not None:
        return cached
    pad = 4
    c0 = float(r + pad)
    surf = pygame.Surface((2 * (r + pad), 2 * (r + pad)), pygame.SRCALPHA)
    dash, gap = 10.0, 7.0
    n_dash = max(8, int(2.0 * math.pi * r / (dash + gap)))
    step = 2.0 * math.pi / n_dash
    arc = step * dash / (dash + gap)
    # widest-first: each narrower pass overwrites the halo center
    # (pygame.draw writes RGBA directly on SRCALPHA surfaces)
    for width, alpha in ((5, 10), (3, 22), (1, 50)):
        col = (*key[1], alpha)
        for i in range(n_dash):
            th0 = i * step
            n_pts = max(3, int(r * arc / 4.0) + 2)
            pts = [(c0 + r * math.cos(th0 + arc * j / (n_pts - 1)),
                    c0 - r * math.sin(th0 + arc * j / (n_pts - 1)))
                   for j in range(n_pts)]
            pygame.draw.lines(surf, col, False, pts, width)
    _SOI_RING_CACHE[key] = surf
    return surf
