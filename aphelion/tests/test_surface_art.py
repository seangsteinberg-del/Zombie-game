"""LOOK update chunk B: surface-scene art — scattering skies, parallax
ridges, fBM ground strips and the pad complex are deterministic, cached,
and body-keyed."""

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from aphelion.render.surface_art import (
    GROUND_STRIP_H, PAD_GROUND_Y, PAD_H, PAD_W, RIDGE_PAD, ground_palette,
    ground_strip, pad_complex, ridge_layers, sky_surface)

pygame.init()
SIZE = (320, 180)


def _bytes(s: pygame.Surface) -> bytes:
    return pygame.image.tobytes(s, "RGBA")


def test_sky_cached_opaque_and_body_keyed():
    a = sky_surface(SIZE, "core:earth")
    assert a is sky_surface(SIZE, "core:earth")          # cache hit
    assert a.get_size() == SIZE
    mars = sky_surface(SIZE, "core:mars")
    assert _bytes(a) != _bytes(mars)                     # palettes differ
    # zenith darker than horizon (scattering ramp, not a flat fill)
    top = a.get_at((10, 4))
    bottom = a.get_at((10, SIZE[1] - 4))
    assert sum(bottom[:3]) > sum(top[:3])


def test_ground_strip_deterministic_and_lit_at_crest():
    g1 = ground_strip("core:moon", SIZE[0])
    g2 = ground_strip("core:moon", SIZE[0])
    assert g1 is g2
    assert g1.get_size() == (SIZE[0], GROUND_STRIP_H)
    crest = g1.get_at((40, 0))
    deep = g1.get_at((40, GROUND_STRIP_H - 1))
    assert sum(crest[:3]) > sum(deep[:3])                # depth shading
    assert _bytes(g1) != _bytes(ground_strip("core:mars", SIZE[0]))


def test_ridge_layers_far_to_near():
    layers = ridge_layers("core:mars", SIZE[0])
    assert len(layers) == 2
    (far, f_fac), (near, n_fac) = layers
    assert f_fac < n_fac                                 # far moves slower
    assert far.get_width() == SIZE[0] + RIDGE_PAD
    assert far.get_height() > near.get_height()
    assert far.get_at((5, 0)).a == 0                     # sky above the crest


def test_pad_complex_shape_and_cache():
    p = pad_complex()
    assert p is pad_complex()
    assert p.get_size() == (PAD_W, PAD_H)
    assert 0 < PAD_GROUND_Y < PAD_H
    assert p.get_at((2, 2)).a == 0                       # transparent corner
    # the apron row is opaque concrete
    assert p.get_at((PAD_W // 2 - 100, PAD_GROUND_Y + 8)).a > 200


def test_ground_palette_fallback():
    assert ground_palette("core:nonexistent_rock") is ground_palette("x:y")
    assert ground_palette("core:earth").atmo
    assert not ground_palette("core:moon").atmo
