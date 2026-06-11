"""Procedural celestial-body sprites for the map view (13 §3.13; art
direction addendum — dark hard-sci-fi, KSP-map-view clarity).

Every visual is generated at runtime from numpy + pygame.surfarray — no
image or font assets, no display calls (plain SRCALPHA surfaces only).
Shading is vectorized over a coordinate grid: sphere normal
z = sqrt(1 - x^2 - y^2), lambert-ish light = clamp(nx*lx + ny*ly + nz*0.55)
gamma-corrected, multiplied into a per-body albedo texture, with limb
darkening (z^0.45) and a thin bright rim on the lit edge. Per-class seeded
detail: craters for airless rock, warped horizontal bands for gas giants
(6-10 bands, Great Red Spot on Jupiter), continents + clouds + ice caps for
Earth, polar caps for Mars, ridged crack lines for Europa, etc.

Surface-geometry contract (binding for callers):
  * body_sprite returns a SQUARE surface LARGER than the requested diameter
    with the body centered — SPRITE_SCALE (1.35x) for plain and atmosphere
    bodies (the margin holds the additive atmosphere halo ring),
    RING_SPRITE_SCALE (2.4x) for ringed bodies (Saturn), SUN_SPRITE_SCALE
    (2.2x) for the star's corona. Blit centered on the body position.
  * Diameters are bucketed to ~24 logarithmic steps (bucket_diameter) and
    sun_angle to 16 sectors, so nearby requests share one cached surface:
    generation cost is paid once per key, lookups are O(1) dict hits.

Determinism: all noise comes from numpy.random.default_rng seeded by a
blake2b hash of the body id — no random module, no wall clock. Unknown ids
fall back by parent/size (from the data pack registry) to a sensible class.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pygame

SPRITE_SCALE = 1.35           # plain + atmosphere-halo bodies
RING_SPRITE_SCALE = 2.4       # ringed bodies (rings span ~2.26 body radii)
SUN_SPRITE_SCALE = 2.2        # star corona extent

_MAX_SPRITE_PX = 512          # hard cap on returned surface edge
_D_MIN = 4.0
_D_STEPS = 24
_LOG_STEP = math.log(_MAX_SPRITE_PX / _D_MIN) / _D_STEPS
_SECTORS = 16
_SECTOR = math.tau / _SECTORS

_RGB = tuple[int, int, int]


@dataclass(frozen=True, slots=True)
class BodyPalette:
    """Per-body art parameters. kind selects the albedo generator."""
    kind: str                       # star|gas|earth|mars|hazy|cratered|icy|lined|mottled
    base: _RGB
    shade: _RGB
    accent: _RGB
    atmo: _RGB | None = None        # halo tint, None = airless
    atmo_h: float = 0.0             # halo e-fold thickness, fraction of radius
    rings: _RGB | None = None       # ring tint, None = no rings
    detail: float = 1.0             # texture contrast / crater density scale
    feature: bool = False           # kind-specific landmark (GRS, Io spots, ...)


# ---- the canon palette table (covers all 37 pack bodies) -------------------

PALETTES: dict[str, BodyPalette] = {
    "sun":       BodyPalette("star", (255, 244, 210), (255, 170, 60), (255, 210, 120)),
    "mercury":   BodyPalette("cratered", (148, 134, 118), (54, 46, 40), (190, 178, 160), detail=1.2),
    "venus":     BodyPalette("hazy", (226, 202, 158), (148, 120, 86), (244, 228, 192),
                             atmo=(240, 218, 164), atmo_h=0.24),
    "earth":     BodyPalette("earth", (30, 84, 160), (8, 18, 40), (70, 134, 72),
                             atmo=(112, 172, 255), atmo_h=0.20),
    "moon":      BodyPalette("cratered", (146, 144, 140), (52, 51, 49), (186, 184, 178), detail=1.3),
    "mars":      BodyPalette("mars", (178, 100, 58), (62, 30, 18), (232, 226, 218),
                             atmo=(216, 158, 116), atmo_h=0.10),
    "phobos":    BodyPalette("cratered", (104, 94, 84), (38, 33, 29), (140, 130, 118), detail=1.5),
    "deimos":    BodyPalette("cratered", (118, 108, 96), (44, 39, 34), (152, 142, 128), detail=1.2),
    "jupiter":   BodyPalette("gas", (198, 166, 124), (122, 86, 58), (192, 98, 58),
                             atmo=(224, 196, 150), atmo_h=0.10, feature=True),
    "io":        BodyPalette("mottled", (214, 186, 84), (112, 80, 30), (234, 142, 58), feature=True),
    "europa":    BodyPalette("lined", (218, 214, 204), (98, 94, 88), (164, 110, 84)),
    "ganymede":  BodyPalette("mottled", (142, 130, 114), (56, 49, 42), (180, 170, 152)),
    "callisto":  BodyPalette("cratered", (112, 100, 88), (40, 35, 30), (156, 146, 130), detail=1.4),
    "saturn":    BodyPalette("gas", (218, 196, 148), (146, 120, 80), (236, 218, 170),
                             atmo=(232, 212, 160), atmo_h=0.09, rings=(212, 192, 152), detail=0.7),
    "enceladus": BodyPalette("icy", (234, 238, 242), (124, 132, 142), (204, 218, 228)),
    "titan":     BodyPalette("hazy", (208, 146, 62), (98, 60, 24), (230, 178, 96),
                             atmo=(230, 164, 72), atmo_h=0.24),
    "uranus":    BodyPalette("gas", (170, 216, 220), (96, 140, 148), (200, 234, 236),
                             atmo=(182, 226, 228), atmo_h=0.13, detail=0.25),
    "neptune":   BodyPalette("gas", (64, 104, 214), (24, 40, 98), (150, 190, 255),
                             atmo=(104, 150, 255), atmo_h=0.15, detail=0.5),
    "miranda":   BodyPalette("icy", (160, 162, 166), (66, 68, 72), (206, 208, 212)),
    "titania":   BodyPalette("icy", (152, 146, 140), (62, 58, 54), (196, 188, 180)),
    "oberon":    BodyPalette("cratered", (124, 114, 106), (46, 42, 38), (164, 152, 142)),
    "triton":    BodyPalette("icy", (192, 182, 172), (82, 74, 66), (222, 202, 186),
                             atmo=(176, 198, 220), atmo_h=0.06),
    "pluto":     BodyPalette("mottled", (198, 172, 142), (76, 58, 44), (228, 212, 188),
                             atmo=(160, 190, 222), atmo_h=0.06),
    "charon":    BodyPalette("cratered", (138, 132, 128), (52, 48, 46), (126, 90, 70)),
    "ceres":     BodyPalette("cratered", (140, 134, 126), (50, 47, 43), (240, 240, 230), feature=True),
    "vesta":     BodyPalette("cratered", (160, 148, 130), (60, 54, 46), (198, 188, 170), detail=1.3),
    "hygiea":    BodyPalette("cratered", (106, 102, 98), (36, 34, 32), (140, 136, 130), detail=1.2),
    "psyche":    BodyPalette("mottled", (154, 150, 154), (62, 60, 66), (200, 198, 206)),
    "eris":      BodyPalette("icy", (226, 224, 218), (110, 108, 102), (244, 242, 238)),
    "eros":      BodyPalette("cratered", (142, 128, 110), (52, 46, 38), (178, 164, 144), detail=1.6),
    "itokawa":   BodyPalette("cratered", (152, 144, 128), (56, 52, 44), (188, 180, 164), detail=1.6),
    "bennu":     BodyPalette("cratered", (70, 68, 66), (22, 21, 20), (104, 102, 100), detail=1.7),
    "ryugu":     BodyPalette("cratered", (76, 72, 68), (24, 22, 21), (110, 106, 102), detail=1.7),
    "apophis":   BodyPalette("cratered", (132, 122, 108), (48, 44, 38), (168, 158, 142), detail=1.5),
    "halley":    BodyPalette("cratered", (92, 88, 84), (30, 28, 27), (130, 126, 120), detail=1.5),
    "67p":       BodyPalette("cratered", (96, 92, 88), (32, 30, 29), (134, 130, 124), detail=1.6),
    "arrokoth":  BodyPalette("mottled", (176, 132, 98), (74, 52, 36), (210, 168, 130)),
}

# fallback classes for ids outside the table, chosen by parent/size
_FALLBACK: dict[str, BodyPalette] = {
    "gas":      BodyPalette("gas", (150, 186, 196), (70, 98, 110), (190, 220, 228),
                            atmo=(160, 200, 210), atmo_h=0.12, detail=0.5),
    "rock":     BodyPalette("cratered", (140, 134, 126), (50, 47, 43), (180, 174, 164), detail=1.2),
    "ice":      BodyPalette("icy", (200, 204, 210), (88, 92, 98), (230, 234, 240)),
    "asteroid": BodyPalette("cratered", (110, 102, 92), (38, 35, 31), (146, 138, 126), detail=1.6),
}

# ---- caches (the public functions are O(1) after first generation) ---------

_SPRITE_CACHE: dict[tuple[str, int, int], pygame.Surface] = {}
_SUN_CACHE: dict[int, pygame.Surface] = {}
_MARKER_CACHE: dict[tuple[str, int], pygame.Surface] = {}
_PALETTE_CACHE: dict[str, BodyPalette] = {}
_REGISTRY: dict[str, tuple[str | None, float]] | None = None


# ---- seeding, registry, palette lookup -------------------------------------

def _seed(body_id: str) -> int:
    return int.from_bytes(
        hashlib.blake2b(body_id.encode(), digest_size=8).digest(), "little")


def _registry() -> dict[str, tuple[str | None, float]]:
    """id -> (parent, radius_m) read once from the data packs (fail-soft)."""
    global _REGISTRY
    if _REGISTRY is None:
        reg: dict[str, tuple[str | None, float]] = {}
        data_dir = Path(__file__).resolve().parents[2] / "data"
        for path in sorted(data_dir.glob("*/bodies/*.json")):
            try:
                doc = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            bid = doc.get("id")
            if isinstance(bid, str):
                reg[bid] = (doc.get("parent"), float(doc.get("radius_m") or 0.0))
        _REGISTRY = reg
    return _REGISTRY


def _palette_for(body_id: str) -> BodyPalette:
    pal = _PALETTE_CACHE.get(body_id)
    if pal is not None:
        return pal
    pal = PALETTES.get(body_id.rsplit(":", 1)[-1])
    if pal is None:
        entry = _registry().get(body_id)
        if entry is None:
            pal = _FALLBACK["asteroid"]
        else:
            parent, radius_m = entry
            if parent is None:
                pal = PALETTES["sun"]
            elif radius_m >= 2.0e7:
                pal = _FALLBACK["gas"]
            elif radius_m >= 8.0e5:
                pal = _FALLBACK["rock"]
            elif radius_m >= 2.0e5:
                pal = _FALLBACK["ice"]
            else:
                pal = _FALLBACK["asteroid"]
    _PALETTE_CACHE[body_id] = pal
    return pal


# ---- numpy helpers ----------------------------------------------------------

def _c(rgb: _RGB) -> np.ndarray:
    return np.asarray(rgb, dtype=np.float64) / 255.0


def _lerp(a: np.ndarray, b: np.ndarray, t: np.ndarray | float) -> np.ndarray:
    return a + (b - a) * t


def _smooth(t: np.ndarray) -> np.ndarray:
    t = np.clip(t, 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def _upsample(grid: np.ndarray, size: int) -> np.ndarray:
    """Bilinear (n+1)x(n+1) lattice -> size x size."""
    n = grid.shape[0] - 1
    t = np.linspace(0.0, n, size)
    i = np.minimum(t.astype(np.intp), n - 1)
    f = t - i
    rows = grid[i, :] * (1.0 - f)[:, None] + grid[i + 1, :] * f[:, None]
    return rows[:, i] * (1.0 - f)[None, :] + rows[:, i + 1] * f[None, :]


def _fbm(rng: np.random.Generator, size: int, octaves: int = 4,
         base_cells: int = 3) -> np.ndarray:
    """Seeded value-noise fBM in [0, 1], vectorized (no per-pixel loops)."""
    out = np.zeros((size, size))
    amp, total = 1.0, 0.0
    for octave in range(octaves):
        cells = base_cells * (2 ** octave)
        out += amp * _upsample(rng.random((cells + 1, cells + 1)), size)
        total += amp
        amp *= 0.5
    return out / total


def _over(rgb: np.ndarray, a: np.ndarray, src_rgb: np.ndarray,
          src_a: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Straight-alpha 'over' composite, src on top of (rgb, a)."""
    sa = src_a[..., None]
    out_a = src_a + a * (1.0 - src_a)
    out_rgb = (src_rgb * sa + rgb * a[..., None] * (1.0 - sa)) \
        / np.maximum(out_a[..., None], 1e-6)
    return out_rgb, out_a


def _add(rgb: np.ndarray, a: np.ndarray, g_rgb: np.ndarray,
         g_a: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Additive glow in premultiplied space (atmosphere halo, corona)."""
    out_a = np.clip(a + g_a * (1.0 - a), 0.0, 1.0)
    prem = rgb * a[..., None] + g_rgb * g_a[..., None]
    out_rgb = prem / np.maximum(out_a[..., None], 1e-6)
    return np.clip(out_rgb, 0.0, 1.0), out_a


def _to_surface(rgb: np.ndarray, a: np.ndarray) -> pygame.Surface:
    size = rgb.shape[0]
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    px = pygame.surfarray.pixels3d(surf)
    px[:] = (np.clip(rgb, 0.0, 1.0) * 255.0 + 0.5).astype(np.uint8)
    del px
    pa = pygame.surfarray.pixels_alpha(surf)
    pa[:] = (np.clip(a, 0.0, 1.0) * 255.0 + 0.5).astype(np.uint8)
    del pa
    return surf


def _stamp_craters(rng: np.random.Generator, alb: np.ndarray, x: np.ndarray,
                   y: np.ndarray, n: int, depth: float = 0.30,
                   rim: float = 0.22, rmin: float = 0.03,
                   rmax: float = 0.13) -> None:
    """Darken bowls + brighten rims for n seeded craters (in-place)."""
    for _ in range(n):
        cr = rmin + (rmax - rmin) * float(rng.random()) ** 2
        rad = math.sqrt(float(rng.random())) * 0.92
        th = float(rng.random()) * math.tau
        cx, cy = rad * math.cos(th), rad * math.sin(th)
        rel = ((x - cx) ** 2 + (y - cy) ** 2) / (cr * cr)
        bowl = np.clip(1.0 - rel, 0.0, 1.0)
        ridge = np.exp(-((np.sqrt(rel) - 1.0) ** 2) * 16.0)
        alb *= (1.0 - depth * bowl ** 0.7 + rim * ridge)[..., None]


# ---- per-class albedo generators (all return (size,size,3) in 0..1) --------

def _alb_gas(rng: np.random.Generator, x: np.ndarray, y: np.ndarray,
             lat: np.ndarray, size: int, pal: BodyPalette) -> np.ndarray:
    base, shade, accent = _c(pal.base), _c(pal.shade), _c(pal.accent)
    n_bands = int(6 + rng.integers(0, 5))                       # 6-10 bands
    bands = np.empty((n_bands, 3))
    contrast = min(1.0, pal.detail * 1.2)
    for i in range(n_bands):                        # alternate light / dark
        if i % 2 == 0:
            col = _lerp(base, shade, 0.05 + 0.25 * float(rng.random()))
        else:
            col = _lerp(base, shade, 0.55 + 0.40 * float(rng.random()))
        if float(rng.random()) < 0.30:
            col = _lerp(col, accent, 0.30)
        bands[i] = _lerp(base, col, contrast)
    warp = (_fbm(rng, size, 4, 3) - 0.5) * pal.detail           # flow noise
    pos = np.clip((lat * 0.5 + 0.5) * (n_bands - 1) + warp * 2.2,
                  0.0, n_bands - 1.001)
    i0 = pos.astype(np.intp)
    f = _smooth((pos - i0 - 0.5) * 3.5 + 0.5)       # plateaus, crisp edges
    alb = bands[i0] * (1.0 - f)[..., None] \
        + bands[np.minimum(i0 + 1, n_bands - 1)] * f[..., None]
    alb *= 1.0 + ((_fbm(rng, size, 5, 6) - 0.5) * 0.10 * pal.detail)[..., None]
    if pal.feature:                                             # Great Red Spot
        sx = -0.55 + 0.35 * float(rng.random())
        sy = 0.28 + 0.18 * float(rng.random())
        blob = np.exp(-(((x - sx) / 0.26) ** 2 + ((lat - sy) / 0.13) ** 2))
        alb = _lerp(alb, accent, np.clip(blob * 1.5, 0.0, 1.0)[..., None] * 0.85)
    return np.clip(alb, 0.0, 1.0)


def _alb_earth(rng: np.random.Generator, x: np.ndarray, y: np.ndarray,
               lat: np.ndarray, size: int, pal: BodyPalette) -> np.ndarray:
    ocean, deep, land = _c(pal.base), _c(pal.shade), _c(pal.accent)
    cont = _fbm(rng, size, 5, 3)
    moist = _fbm(rng, size, 4, 4)
    cloud = _fbm(rng, size, 5, 4)
    alb = _lerp(_lerp(deep, ocean, 0.4), ocean,
                _smooth((cont - 0.30) / 0.25)[..., None])
    land_col = _lerp(land, np.array([0.66, 0.58, 0.38]),
                     _smooth((moist - 0.55) / 0.18)[..., None])
    alb = _lerp(alb, land_col, _smooth((cont - 0.55) / 0.05)[..., None])
    cap = _smooth((np.abs(lat) - 0.80 - (cont - 0.5) * 0.08) / 0.05)
    alb = _lerp(alb, np.array([0.93, 0.95, 0.98]), cap[..., None])
    cm = _smooth((cloud - 0.55) / 0.14) * 0.9
    return np.clip(_lerp(alb, np.array([0.97, 0.98, 1.0]), cm[..., None]),
                   0.0, 1.0)


def _alb_mars(rng: np.random.Generator, x: np.ndarray, y: np.ndarray,
              lat: np.ndarray, size: int, pal: BodyPalette) -> np.ndarray:
    base, shade, cap_col = _c(pal.base), _c(pal.shade), _c(pal.accent)
    mott = _fbm(rng, size, 5, 3)
    dark = _fbm(rng, size, 4, 4)
    alb = base * (1.0 + (mott - 0.5)[..., None] * 0.5)
    alb = _lerp(alb, shade, (_smooth((0.42 - dark) / 0.10) * 0.55)[..., None])
    _stamp_craters(rng, alb, x, y, max(6, size // 14),
                   depth=0.18, rim=0.12, rmax=0.09)
    cap = _smooth((np.abs(lat) - 0.76 - (mott - 0.5) * 0.12) / 0.04)
    return np.clip(_lerp(alb, cap_col, cap[..., None]), 0.0, 1.0)


def _alb_hazy(rng: np.random.Generator, x: np.ndarray, y: np.ndarray,
              lat: np.ndarray, size: int, pal: BodyPalette) -> np.ndarray:
    base, shade, accent = _c(pal.base), _c(pal.shade), _c(pal.accent)
    n = _fbm(rng, size, 4, 2)
    sweep = 0.5 + 0.5 * np.sin((lat * 1.6 + (n - 0.5) * 1.3) * 4.2)
    alb = _lerp(base, accent, (sweep * 0.5)[..., None])
    alb = _lerp(alb, shade,
                np.clip(_fbm(rng, size, 3, 2) - 0.5, 0.0, None)[..., None] * 0.3)
    return np.clip(alb * (1.0 + (n - 0.5)[..., None] * 0.08), 0.0, 1.0)


def _alb_cratered(rng: np.random.Generator, x: np.ndarray, y: np.ndarray,
                  lat: np.ndarray, size: int, pal: BodyPalette) -> np.ndarray:
    base, shade, accent = _c(pal.base), _c(pal.shade), _c(pal.accent)
    mott = _fbm(rng, size, 5, 3)
    maria = _fbm(rng, size, 4, 2)
    alb = base * (1.0 + (mott - 0.5)[..., None] * 0.45)
    alb = _lerp(alb, shade, (_smooth((0.40 - maria) / 0.08) * 0.5)[..., None])
    n = int(np.clip(size * 0.35 * pal.detail, 10, 70))
    _stamp_craters(rng, alb, x, y, n)
    if pal.feature:                                 # Ceres-style bright spots
        for _ in range(int(2 + rng.integers(0, 3))):
            cr = 0.02 + 0.03 * float(rng.random())
            cx = (float(rng.random()) - 0.5) * 1.2
            cy = (float(rng.random()) - 0.5) * 1.2
            rel = ((x - cx) ** 2 + (y - cy) ** 2) / (cr * cr)
            spot = np.clip(1.0 - rel, 0.0, 1.0) ** 0.6
            alb = _lerp(alb, accent, (spot * 0.9)[..., None])
    return np.clip(alb, 0.0, 1.0)


def _alb_icy(rng: np.random.Generator, x: np.ndarray, y: np.ndarray,
             lat: np.ndarray, size: int, pal: BodyPalette) -> np.ndarray:
    base, shade, accent = _c(pal.base), _c(pal.shade), _c(pal.accent)
    mott = _fbm(rng, size, 4, 3)
    flow = _fbm(rng, size, 5, 5)
    alb = base * (1.0 + (mott - 0.5)[..., None] * 0.18)
    alb = _lerp(alb, accent, (_smooth((flow - 0.60) / 0.10) * 0.25)[..., None])
    alb = _lerp(alb, shade, (_smooth((0.34 - mott) / 0.08) * 0.25)[..., None])
    _stamp_craters(rng, alb, x, y, max(4, size // 16),
                   depth=0.15, rim=0.10, rmax=0.08)
    return np.clip(alb, 0.0, 1.0)


def _alb_lined(rng: np.random.Generator, x: np.ndarray, y: np.ndarray,
               lat: np.ndarray, size: int, pal: BodyPalette) -> np.ndarray:
    base, _shade, accent = _c(pal.base), _c(pal.shade), _c(pal.accent)
    alb = base * (1.0 + (_fbm(rng, size, 4, 3) - 0.5)[..., None] * 0.12)
    for cells in (4, 7):                            # two crack scales (Europa)
        c = _fbm(rng, size, 5, cells)
        lines = np.exp(-((c - 0.5) ** 2) * 700.0)
        alb = _lerp(alb, accent, np.clip(lines, 0.0, 1.0)[..., None] * 0.45)
    return np.clip(alb, 0.0, 1.0)


def _alb_mottled(rng: np.random.Generator, x: np.ndarray, y: np.ndarray,
                 lat: np.ndarray, size: int, pal: BodyPalette) -> np.ndarray:
    base, shade, accent = _c(pal.base), _c(pal.shade), _c(pal.accent)
    a1 = _fbm(rng, size, 5, 3)
    b1 = _fbm(rng, size, 4, 5)
    alb = _lerp(np.broadcast_to(base, (size, size, 3)).copy(), shade,
                _smooth((0.45 - a1) / 0.12)[..., None])
    alb = _lerp(alb, accent, (_smooth((b1 - 0.60) / 0.10) * 0.8)[..., None])
    if pal.feature:                                 # Io volcanic hot spots
        for _ in range(int(8 + rng.integers(0, 7))):
            cr = 0.02 + 0.05 * float(rng.random())
            rad = math.sqrt(float(rng.random())) * 0.85
            th = float(rng.random()) * math.tau
            cx, cy = rad * math.cos(th), rad * math.sin(th)
            rel = ((x - cx) ** 2 + (y - cy) ** 2) / (cr * cr)
            dot = np.clip(1.0 - rel, 0.0, 1.0) ** 0.8
            ring = np.exp(-((np.sqrt(rel) - 1.3) ** 2) * 6.0)
            alb = _lerp(alb, shade, (dot * 0.8)[..., None])
            alb = _lerp(alb, accent, (ring * 0.35)[..., None])
    return np.clip(alb, 0.0, 1.0)


_ALBEDO = {
    "gas": _alb_gas,
    "earth": _alb_earth,
    "mars": _alb_mars,
    "hazy": _alb_hazy,
    "cratered": _alb_cratered,
    "icy": _alb_icy,
    "lined": _alb_lined,
    "mottled": _alb_mottled,
}


# ---- renderers --------------------------------------------------------------

def _render_rings(rng: np.random.Generator, x: np.ndarray, y: np.ndarray,
                  d: int, pal: BodyPalette) -> tuple[np.ndarray, np.ndarray]:
    """Tilted ring ellipse with a Cassini-style gap and radial density noise."""
    tilt = 0.34
    q = np.sqrt(x * x + (y / tilt) ** 2)            # radius in the ring plane
    px = d * 0.5                                    # pixels per body radius
    inner, gap0, gap1, outer = 1.45, 1.84, 1.94, 2.26

    def aa(t: np.ndarray) -> np.ndarray:            # 1-px AA edge ramp
        return np.clip(t * px, 0.0, 1.0)

    band = aa(q - inner) * aa(outer - q)
    band *= 1.0 - aa(q - gap0) * aa(gap1 - q)       # the gap
    dens = np.interp((q - inner) / (outer - inner),
                     np.linspace(0.0, 1.0, 24), 0.55 + 0.45 * rng.random(24))
    ring_a = np.clip(band * dens * 0.8, 0.0, 1.0)
    grad = 0.85 + 0.3 * np.clip((q - inner) / (outer - inner), 0.0, 1.0)
    ring_rgb = np.clip(_c(pal.rings) * grad[..., None], 0.0, 1.0)
    return ring_rgb, ring_a


def _render_body(body_id: str, pal: BodyPalette, d: int,
                 sun_angle: float) -> pygame.Surface:
    rng = np.random.default_rng(_seed(body_id))
    scale = RING_SPRITE_SCALE if pal.rings else SPRITE_SCALE
    size = int(round(d * scale))
    ax = ((np.arange(size) + 0.5) / size * 2.0 - 1.0) * scale   # body radius=1
    x, y = ax[:, None], ax[None, :]                 # surfarray [x][y], y down
    rr = x * x + y * y
    r = np.sqrt(rr)
    nz = np.sqrt(np.clip(1.0 - rr, 0.0, 1.0))       # sphere normal z
    # orthographic screen y IS sin(latitude); a slight x^2 bow fakes axial tilt
    lat = np.clip(y * (1.0 + 0.18 * x * x), -1.0, 1.0)
    cov = np.clip((1.0 - r) * (d * 0.5) + 0.5, 0.0, 1.0)        # AA limb

    lx, ly = math.cos(sun_angle), math.sin(sun_angle)
    toward = x * lx + y * ly
    lam = np.clip(toward + nz * 0.55, 0.0, 1.0)     # lambert-ish
    lit = (lam ** 0.85) * (nz ** 0.45)              # gamma + limb darkening

    alb = _ALBEDO[pal.kind](rng, x, y, lat, size, pal)
    col = alb * lit[..., None] + _c(pal.shade) * ((1.0 - lit) * 0.16)[..., None]
    facing = np.clip(toward / np.maximum(r, 1e-6), 0.0, 1.0)
    rim = np.exp(-(((r - 0.965) * d / 2.4) ** 2))   # thin rim on the lit edge
    rim_col = _c(pal.atmo) if pal.atmo else np.clip(_c(pal.base) * 0.6 + 0.4,
                                                    0.0, 1.0)
    col = np.clip(col + (rim * facing ** 1.5 * 0.5)[..., None] * rim_col,
                  0.0, 1.0)

    rgb = np.zeros((size, size, 3))
    a = np.zeros((size, size))
    if pal.rings:                                   # far half behind the limb
        ring_rgb, ring_a = _render_rings(rng, x, y, d, pal)
        rgb, a = _over(rgb, a, ring_rgb, np.where(y < 0.0, ring_a, 0.0))
    rgb, a = _over(rgb, a, col, cov)
    if pal.atmo:                                    # additive halo past limb
        glow = np.exp(-np.clip(r - 1.0, 0.0, None) / max(pal.atmo_h, 1e-3))
        glow *= np.clip((r - 1.0) * (d * 0.5) + 0.5, 0.0, 1.0)
        glow *= np.clip((scale - 0.04 - r) / 0.10, 0.0, 1.0)    # fade at edge
        glow *= (0.45 + 0.55 * facing) * 0.8
        rgb, a = _add(rgb, a, _c(pal.atmo), glow)
    if pal.rings:                                   # near half over the disc
        rgb, a = _over(rgb, a, ring_rgb, np.where(y >= 0.0, ring_a, 0.0))
    return _to_surface(rgb, a)


def _render_sun(d: int) -> pygame.Surface:
    rng = np.random.default_rng(_seed("core:sun"))
    size = int(round(d * SUN_SPRITE_SCALE))
    ax = ((np.arange(size) + 0.5) / size * 2.0 - 1.0) * SUN_SPRITE_SCALE
    x, y = ax[:, None], ax[None, :]
    r = np.sqrt(x * x + y * y)
    core_a = np.clip((1.0 - r) * (d * 0.5) + 0.5, 0.0, 1.0)
    grain = _fbm(rng, size, 4, 6)
    core_rgb = _lerp(np.array([1.0, 0.99, 0.94]), np.array([1.0, 0.86, 0.52]),
                     (np.clip(r, 0.0, 1.0) ** 2)[..., None])
    core_rgb *= 1.0 + ((grain - 0.5) * 0.08)[..., None]

    t = np.clip(r - 1.0, 0.0, None)
    theta = np.arctan2(y, x)
    spike = np.zeros_like(r)
    for _ in range(int(5 + rng.integers(0, 4))):    # 5-8 seeded flare spikes
        a0 = float(rng.random()) * math.tau
        width = 0.05 + 0.10 * float(rng.random())
        amp = 0.35 + 0.55 * float(rng.random())
        dth = np.angle(np.exp(1j * (theta - a0)))
        spike += amp * np.exp(-((dth / width) ** 2))
    corona = np.exp(-t * 2.8) * (1.0 + spike * np.exp(-t * 1.6) * 0.9)
    corona *= np.clip((SUN_SPRITE_SCALE - 0.05 - r) / 0.18, 0.0, 1.0)
    corona = np.clip(corona, 0.0, 1.0) * 0.95
    cor_rgb = _lerp(np.array([1.0, 0.92, 0.62]), np.array([1.0, 0.55, 0.20]),
                    np.clip(t / 1.1, 0.0, 1.0)[..., None])

    a = core_a + (1.0 - core_a) * corona
    rgb = cor_rgb * (1.0 - core_a[..., None]) + core_rgb * core_a[..., None]
    return _to_surface(np.clip(rgb, 0.0, 1.0), a)


# ---- public API --------------------------------------------------------------

def bucket_diameter(diameter_px: int) -> int:
    """Snap a pixel diameter to one of ~24 log-spaced buckets (cache key)."""
    d = min(max(float(diameter_px), _D_MIN), float(_MAX_SPRITE_PX))
    b = round(math.log(d / _D_MIN) / _LOG_STEP)
    return int(round(_D_MIN * math.exp(b * _LOG_STEP)))


def sprite_scale(body_id: str) -> float:
    """Returned-surface edge / body diameter for this body (see module doc)."""
    pal = _palette_for(body_id)
    if pal.kind == "star":
        return SUN_SPRITE_SCALE
    return RING_SPRITE_SCALE if pal.rings else SPRITE_SCALE


def body_sprite(body_id: str, diameter_px: int,
                sun_angle: float = 0.0) -> pygame.Surface:
    """Lit, textured sphere sprite. The surface is sprite_scale(body_id) times
    the (bucketed) diameter, body centered; sun_angle is the direction TO the
    sun in screen space (radians, y down), bucketed to 16 sectors. Stars
    ignore sun_angle and delegate to sun_sprite."""
    pal = _palette_for(body_id)
    if pal.kind == "star":
        return sun_sprite(diameter_px)
    scale = RING_SPRITE_SCALE if pal.rings else SPRITE_SCALE
    d = min(bucket_diameter(diameter_px), int(_MAX_SPRITE_PX / scale))
    sector = int(round(sun_angle / _SECTOR)) % _SECTORS
    key = (body_id, d, sector)
    surf = _SPRITE_CACHE.get(key)
    if surf is None:
        surf = _render_body(body_id, pal, d, sector * _SECTOR)
        _SPRITE_CACHE[key] = surf
    return surf


def sun_sprite(diameter_px: int) -> pygame.Surface:
    """White-hot core + yellow-orange corona (surface is 2.2x the bucketed
    core diameter) with seeded flare spikes."""
    d = min(bucket_diameter(diameter_px), int(_MAX_SPRITE_PX / SUN_SPRITE_SCALE))
    surf = _SUN_CACHE.get(d)
    if surf is None:
        surf = _render_sun(d)
        _SUN_CACHE[d] = surf
    return surf


def marker_dot(body_id: str, r_px: int) -> pygame.Surface:
    """Anti-aliased disc in the body's base color with a 1px darker rim, for
    bodies subtending < ~5 px. Surface edge is 2*r_px + 2."""
    r = max(1, int(r_px))
    key = (body_id, r)
    surf = _MARKER_CACHE.get(key)
    if surf is None:
        pal = _palette_for(body_id)
        size = 2 * r + 2
        ax = np.arange(size) + 0.5 - size / 2.0
        dist = np.hypot(ax[:, None], ax[None, :])
        cov = np.clip(r - dist + 0.5, 0.0, 1.0)
        rim = _smooth((dist - (r - 1.4)) / 1.2)
        base = _c(pal.base)
        col = _lerp(np.broadcast_to(base, (size, size, 3)).copy(),
                    base * 0.45, rim[..., None])
        surf = _to_surface(col, cov)
        _MARKER_CACHE[key] = surf
    return surf
