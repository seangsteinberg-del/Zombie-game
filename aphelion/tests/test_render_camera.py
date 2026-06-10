"""Render math tests: the floating-origin choke point (13 §3.7 mandates a
Neptune-orbit fixture asserting residual < 0.5 px), Cohen-Sutherland
clipping, conic sampling, and an offscreen draw smoke test."""

import math
import os

import numpy as np
import pytest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

from aphelion.render.camera import Camera, ZoomLayer, LAYER_Z_RANGE
from aphelion.render.draw_conics import (
    clip_polyline,
    clip_segment,
    sample_conic,
)
from aphelion.sim.orbits.kepler import Elements, state_to_elements
from aphelion.sim.orbits import transfers as tr

MU_EARTH = 3.986_004_418e14
NEPTUNE_R = 4.495e12        # heliocentric distance, m


# ---- floating origin (the binding Neptune fixture) -------------------------

def test_neptune_fixture_residual_subpixel():
    """Subtract-first in float64, narrow after: residual must be < 0.5 px at
    maximum INTERIOR zoom even at Neptune's heliocentric distance."""
    cam = Camera(1920, 1080, "neptune_orbit", zoom=128.0, layer=ZoomLayer.INTERIOR)
    cam.follow(NEPTUNE_R, 0.0)
    # A point 10 m from the camera center, at Neptune distance from origin.
    sx, sy = cam.world_to_screen(NEPTUNE_R + 10.0, 3.0)
    # Narrowing the camera-local result to float32 afterwards stays sub-pixel:
    sx32, sy32 = np.float32(sx), np.float32(sy)
    assert abs(float(sx32) - (960.0 + 1280.0)) < 0.5
    assert abs(float(sy32) - (540.0 - 384.0)) < 0.5


def test_wrong_order_transform_would_shake():
    """Demonstrate the bug the choke point prevents: scale-then-subtract in
    float32 produces hundreds of km of error at Neptune."""
    zoom = 128.0
    p = np.float32(NEPTUNE_R + 10.0) * np.float32(zoom)
    c = np.float32(NEPTUNE_R) * np.float32(zoom)
    wrong = float(p - c)
    correct = 10.0 * zoom
    assert abs(wrong - correct) > 1_000.0     # catastrophically wrong


def test_world_screen_roundtrip():
    cam = Camera(1280, 720, "sun", zoom=2.0e-9, layer=ZoomLayer.SYSTEM)
    cam.follow(1.0e11, -3.0e10)
    x, y = 1.4e11, 2.2e10
    sx, sy = cam.world_to_screen(x, y)
    bx, by = cam.screen_to_world(sx, sy)
    assert bx == pytest.approx(x, rel=1e-12)
    assert by == pytest.approx(y, rel=1e-12)


def test_batch_transform_matches_scalar():
    cam = Camera(1280, 720, "sun", zoom=1.0e-9, layer=ZoomLayer.SYSTEM)
    cam.follow(5.0e10, 5.0e10)
    pts = np.array([[0.0, 0.0], [1.0e11, -2.0e10], [-3.0e11, 4.0e11]])
    batch = cam.world_to_screen_np(pts)
    for i in range(len(pts)):
        sx, sy = cam.world_to_screen(pts[i, 0], pts[i, 1])
        assert batch[i, 0] == pytest.approx(sx)
        assert batch[i, 1] == pytest.approx(sy)


def test_zoom_clamped_to_layer_range():
    cam = Camera(1280, 720, "sun", zoom=1.0e-7, layer=ZoomLayer.SYSTEM)
    cam.zoom_in(400)
    assert cam.zoom <= LAYER_Z_RANGE[ZoomLayer.SYSTEM][1]
    cam.zoom_out(400)
    assert cam.zoom >= LAYER_Z_RANGE[ZoomLayer.SYSTEM][0]


def test_system_local_handoff_hysteresis():
    cam = Camera(1000, 1000, "sun", zoom=1.0e-7, layer=ZoomLayer.SYSTEM)
    r_soi = 9.24e8
    # SOI subtends 2*9.24e8*1e-7 = 184.8 px = 18% -> no handoff
    assert not cam.update_system_local_handoff(r_soi, "earth", "sun")
    cam.zoom = 4.0e-7    # 739 px = 74% > 60% -> LOCAL
    assert cam.update_system_local_handoff(r_soi, "earth", "sun")
    assert cam.layer is ZoomLayer.LOCAL and cam.frame_id == "earth"
    # 74% > 40%: stays LOCAL (hysteresis)
    assert not cam.update_system_local_handoff(r_soi, "earth", "sun")
    cam.zoom = 2.0e-7    # 37% < 40% -> back to SYSTEM
    assert cam.update_system_local_handoff(r_soi, "earth", "sun")
    assert cam.layer is ZoomLayer.SYSTEM and cam.frame_id == "sun"


# ---- clipping ---------------------------------------------------------------

def test_clip_segment_inside_outside_crossing():
    assert clip_segment(10, 10, 20, 20, 0, 0, 100, 100) == (10, 10, 20, 20)
    assert clip_segment(-50, -50, -10, -10, 0, 0, 100, 100) is None
    clipped = clip_segment(-50, 50, 150, 50, 0, 0, 100, 100)
    assert clipped == (0, 50, 100, 50)


def test_clip_polyline_huge_coordinates_safe():
    # Endpoints far beyond SDL's int range must be clipped, not passed through
    pts = np.array([[ -1.0e14, 360.0], [1.0e14, 360.0], [1.0e14, 1.0e14]])
    chains = clip_polyline(pts, 1280, 720)
    for chain in chains:
        for x, y in chain:
            assert abs(x) < 1.0e5 and abs(y) < 1.0e5


# ---- conic sampling ----------------------------------------------------------

def test_sample_ellipse_radii_on_conic():
    el = state_to_elements(6.678e6, 0.0, 0.0, 1.2 * tr.circular_speed(MU_EARTH, 6.678e6),
                           0.0, MU_EARTH)
    pts = sample_conic(el, n=64)
    p = el.p
    for x, y in pts:
        r = math.hypot(x, y)
        nu_r = p / r - 1.0
        assert abs(nu_r) <= el.e + 1e-9     # every sample satisfies the conic eq


def test_sample_hyperbola_bounded_by_rmax():
    v_esc = tr.escape_velocity(MU_EARTH, 6.678e6)
    el = state_to_elements(6.678e6, 0.0, 0.0, 1.3 * v_esc, 0.0, MU_EARTH)
    r_max = 5.0e8
    pts = sample_conic(el, n=128, r_max=r_max)
    radii = np.hypot(pts[:, 0], pts[:, 1])
    assert radii.max() <= r_max * 1.000001
    assert radii.min() == pytest.approx(el.periapsis, rel=1e-6)


# ---- offscreen draw smoke test ----------------------------------------------

def test_draw_conic_offscreen():
    import pygame
    from aphelion.render.draw_conics import draw_conic

    pygame.init()
    surface = pygame.Surface((640, 360))
    cam = Camera(640, 360, "earth", zoom=2.0e-5, layer=ZoomLayer.LOCAL)
    el = state_to_elements(6.678e6, 0.0, 0.0, tr.circular_speed(MU_EARTH, 6.678e6),
                           0.0, MU_EARTH)
    chains = draw_conic(surface, el, cam, (255, 0, 0))
    assert chains >= 1
    # Something non-background was actually drawn
    arr = pygame.surfarray.pixels3d(surface)
    assert int(arr[..., 0].max()) > 0


def test_draw_conic_lod_cull():
    import pygame
    from aphelion.render.draw_conics import draw_conic

    pygame.init()
    surface = pygame.Surface((640, 360))
    cam = Camera(640, 360, "sun", zoom=1.6e-10, layer=ZoomLayer.SYSTEM)
    el = state_to_elements(6.678e6, 0.0, 0.0, tr.circular_speed(MU_EARTH, 6.678e6),
                           0.0, MU_EARTH)   # LEO orbit at system zoom: invisible
    assert draw_conic(surface, el, cam, (255, 0, 0)) == 0
