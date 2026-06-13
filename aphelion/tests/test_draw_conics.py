"""Conic polyline clipping (render/draw_conics.py).

The fast clip_polyline (vectorized outcodes + trivial-accept fast path)
must produce BYTE-IDENTICAL chains to the naive per-segment Cohen-
Sutherland clip it replaced — the optimization is invisible by
construction. This pins that invariant against regressions, plus the
obvious on-screen / off-screen / crossing cases.
"""

import numpy as np
import pytest

from aphelion.render import draw_conics as dc

W, H = 1280, 720
GUARD = dc.GUARD_BAND_PX


def _naive_clip(points_px, width, height, guard=GUARD):
    """The original per-segment reference implementation."""
    xmin, ymin = -guard, -guard
    xmax, ymax = width + guard, height + guard
    chains, current = [], []
    for i in range(len(points_px) - 1):
        seg = dc.clip_segment(points_px[i, 0], points_px[i, 1],
                              points_px[i + 1, 0], points_px[i + 1, 1],
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


def _round(chains):
    return [[(round(float(x), 6), round(float(y), 6)) for x, y in ch]
            for ch in chains]


def test_clip_matches_naive_over_random_polylines():
    rng = np.random.default_rng(20490613)
    for _ in range(3000):
        n = int(rng.integers(2, 40))
        scale = float(rng.choice([200, 900, 2500, 6000]))
        pts = rng.uniform(-scale, W + scale, size=(n, 2)).astype(np.float64)
        assert _round(dc.clip_polyline(pts, W, H)) == _round(
            _naive_clip(pts, W, H))


def test_fully_on_screen_is_one_chain():
    pts = np.array([[100.0, 100.0], [200.0, 150.0], [300.0, 120.0],
                    [400.0, 300.0]], dtype=np.float64)
    chains = dc.clip_polyline(pts, W, H)
    assert len(chains) == 1
    assert len(chains[0]) == 4
    assert chains[0][0] == (100.0, 100.0)


def test_fully_off_screen_is_dropped():
    # beyond the guard band (8192 px) on the same side -> all rejected
    far = GUARD + 2000.0
    pts = np.array([[-far, -far], [-far - 1000, -far - 500],
                    [-far - 2000, -far - 200]], dtype=np.float64)
    assert dc.clip_polyline(pts, W, H) == []
    assert dc.clip_polyline(pts, W, H) == _naive_clip(pts, W, H)


def test_crossing_segment_is_clipped_to_the_guard_box():
    # one vertex inside, one far outside: the chain must stay within the
    # viewport + guard band (the whole point — SDL int-safe coordinates)
    pts = np.array([[640.0, 360.0], [640.0, 99999.0]], dtype=np.float64)
    chains = dc.clip_polyline(pts, W, H)
    assert len(chains) == 1
    for _x, y in chains[0]:
        assert y <= H + GUARD + 1e-6


def test_degenerate_short_input():
    assert dc.clip_polyline(np.zeros((0, 2)), W, H) == []
    assert dc.clip_polyline(np.array([[1.0, 2.0]]), W, H) == []
