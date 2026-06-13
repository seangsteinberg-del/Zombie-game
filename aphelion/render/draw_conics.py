"""Conic polyline rendering (13 §3.13): batched true-anomaly sampling in
numpy (one vectorized eval per conic, <= 256 points), Cohen-Sutherland
clipping in float64 camera space to viewport + guard band BEFORE int
conversion (13 §3.7: SDL truncates to C int; a solar-zoom endpoint can be
1e14 px away), LOD rule: < 8 px subtense -> 2-point tick; < 2 px -> cull.
"""

from __future__ import annotations

import math

import numpy as np
import pygame

from aphelion.render.camera import Camera
from aphelion.sim.orbits.kepler import Elements

MAX_SAMPLES = 256
GUARD_BAND_PX = 8_192.0
LOD_TICK_PX = 8.0
LOD_CULL_PX = 2.0


def sample_conic(el: Elements, n: int = MAX_SAMPLES,
                 r_max: float | None = None) -> np.ndarray:
    """(n, 2) float64 positions along the conic in its frame.

    Ellipse: full closed loop. Hyperbola/near-parabola: true anomaly swept to
    the r_max cutoff (callers pass the SOI radius or a screen-extent bound).
    """
    n = min(n, MAX_SAMPLES)
    p = el.p
    if el.e < 1.0:
        nu = np.linspace(0.0, 2.0 * math.pi, n)
    else:
        if r_max is None or r_max <= 0.0:
            r_max = 1.0e3 * p
        cos_lim = (p / r_max - 1.0) / el.e
        nu_lim = math.acos(max(min(cos_lim, 1.0), -1.0))
        if n % 2 == 0:
            n -= 1     # odd count: the periapsis vertex (nu = 0) is a sample
        nu = np.linspace(-nu_lim, nu_lim, n)
    r = p / (1.0 + el.e * np.cos(nu))
    theta = el.varpi + el.s * nu
    return np.stack([r * np.cos(theta), r * np.sin(theta)], axis=1)


# Cohen-Sutherland outcodes
_INSIDE, _LEFT, _RIGHT, _BOTTOM, _TOP = 0, 1, 2, 4, 8


def _outcode(x: float, y: float, xmin: float, ymin: float,
             xmax: float, ymax: float) -> int:
    code = _INSIDE
    if x < xmin:
        code |= _LEFT
    elif x > xmax:
        code |= _RIGHT
    if y < ymin:
        code |= _BOTTOM
    elif y > ymax:
        code |= _TOP
    return code


def clip_segment(x0: float, y0: float, x1: float, y1: float,
                 xmin: float, ymin: float, xmax: float, ymax: float,
                 ) -> tuple[float, float, float, float] | None:
    """Cohen-Sutherland in float64. None = fully outside."""
    c0 = _outcode(x0, y0, xmin, ymin, xmax, ymax)
    c1 = _outcode(x1, y1, xmin, ymin, xmax, ymax)
    while True:
        if not (c0 | c1):
            return (x0, y0, x1, y1)
        if c0 & c1:
            return None
        c_out = c0 if c0 else c1
        if c_out & _TOP:
            x = x0 + (x1 - x0) * (ymax - y0) / (y1 - y0)
            y = ymax
        elif c_out & _BOTTOM:
            x = x0 + (x1 - x0) * (ymin - y0) / (y1 - y0)
            y = ymin
        elif c_out & _RIGHT:
            y = y0 + (y1 - y0) * (xmax - x0) / (x1 - x0)
            x = xmax
        else:
            y = y0 + (y1 - y0) * (xmin - x0) / (x1 - x0)
            x = xmin
        if c_out == c0:
            x0, y0, c0 = x, y, _outcode(x, y, xmin, ymin, xmax, ymax)
        else:
            x1, y1, c1 = x, y, _outcode(x, y, xmin, ymin, xmax, ymax)


def clip_polyline(points_px: np.ndarray, width: int, height: int,
                  guard: float = GUARD_BAND_PX) -> list[list[tuple[float, float]]]:
    """Clip a screen-space polyline into drawable chains, every vertex within
    viewport + guard band (safe for SDL int conversion).

    Outcodes are computed ONCE per vertex (vectorized) instead of twice per
    segment, and the full Cohen-Sutherland refinement runs only for the
    rare boundary-crossing segments — a fully on-screen orbit (the common
    case) never enters the clip loop. Output is identical to the naive
    per-segment clip."""
    if len(points_px) < 2:
        return []
    xmin, ymin = -guard, -guard
    xmax, ymax = width + guard, height + guard
    xs = points_px[:, 0]
    ys = points_px[:, 1]
    codes = np.zeros(len(points_px), dtype=np.int32)
    codes |= (xs < xmin).astype(np.int32) * _LEFT
    codes |= (xs > xmax).astype(np.int32) * _RIGHT
    codes |= (ys < ymin).astype(np.int32) * _BOTTOM
    codes |= (ys > ymax).astype(np.int32) * _TOP
    cl = codes.tolist()                       # python ints: fast scalar ops
    chains: list[list[tuple[float, float]]] = []
    current: list[tuple[float, float]] = []
    for i in range(len(points_px) - 1):
        c0, c1 = cl[i], cl[i + 1]
        if not (c0 | c1):                     # trivial accept: no clipping
            if not current:
                current = [(xs[i], ys[i])]
            current.append((xs[i + 1], ys[i + 1]))
            continue
        if c0 & c1:                           # trivial reject
            if len(current) >= 2:
                chains.append(current)
            current = []
            continue
        seg = clip_segment(xs[i], ys[i], xs[i + 1], ys[i + 1],
                           xmin, ymin, xmax, ymax)
        if seg is None:
            if len(current) >= 2:
                chains.append(current)
            current = []
            continue
        x0, y0, x1, y1 = seg
        if not current:
            current = [(x0, y0)]
        elif current[-1] != (x0, y0):
            if len(current) >= 2:
                chains.append(current)
            current = [(x0, y0)]
        current.append((x1, y1))
    if len(current) >= 2:
        chains.append(current)
    return chains


def conic_screen_subtense_px(el: Elements, cam: Camera) -> float:
    """Approximate on-screen size for the LOD rule: major axis (ellipse) or
    2x periapsis distance (hyperbola), in px."""
    if el.e < 1.0:
        extent = 2.0 * abs(el.a)
    else:
        extent = 2.0 * abs(el.periapsis)
    return extent * cam.zoom


def draw_conic(surface: pygame.Surface, el: Elements, cam: Camera,
               color: tuple[int, int, int], r_max: float | None = None,
               closed: bool | None = None,
               origin: tuple[float, float] = (0.0, 0.0),
               glow: bool = False,
               fade_from: tuple[float, float] | None = None) -> int:
    """Sample, transform through the choke point, clip, draw. `origin` shifts
    the conic's frame center within the camera frame (moon orbits drawn in a
    heliocentric view). Returns the number of chains drawn (0 = culled).

    F0.8: `glow` under-strokes a 3 px soft halo so orbits read as light,
    not wireframe; `fade_from` (screen px of the craft) renders the path
    with luminance falling off along the orbit away from the craft — the
    signature "where am I going" gradient."""
    subtense = conic_screen_subtense_px(el, cam)
    if subtense < LOD_CULL_PX:
        return 0
    if subtense < LOD_TICK_PX:
        pts = sample_conic(el, n=2, r_max=r_max)
    else:
        pts = sample_conic(el, r_max=r_max)
    if origin != (0.0, 0.0):
        pts = pts + np.asarray(origin, dtype=np.float64)
    px = cam.world_to_screen_np(pts)
    if closed is None:
        closed = el.e < 1.0
    if closed:
        px = np.vstack([px, px[:1]])
    chains = clip_polyline(px, cam.width, cam.height)
    if fade_from is not None:
        fx, fy = fade_from
        for chain in chains:
            cpts = np.asarray(chain)
            n = len(cpts)
            d2 = (cpts[:, 0] - fx) ** 2 + (cpts[:, 1] - fy) ** 2
            i0 = int(np.argmin(d2))
            for i in range(n - 1):
                k = abs(i - i0)
                if closed:
                    k = min(k, n - k)
                f = 0.28 + 0.72 * math.exp(-k / (0.20 * max(n, 2)))
                c = tuple(int(ch * f) for ch in color)
                a, b = cpts[i], cpts[i + 1]
                if glow:
                    pygame.draw.line(surface,
                                     tuple(int(v * 0.40) for v in c),
                                     a, b, 3)
                pygame.draw.aaline(surface, c, a, b)
        return len(chains)
    for chain in chains:
        if glow:
            pygame.draw.lines(surface,
                              tuple(int(v * 0.35) for v in color),
                              False, chain, 3)
        pygame.draw.aalines(surface, color, False, chain)
    return len(chains)
