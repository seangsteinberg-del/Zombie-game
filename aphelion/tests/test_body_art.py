"""Procedural body-sprite tests (13 §3.13; art direction addendum): every
pack body renders headless, surface geometry follows the documented
scale/bucket contract, sprites are 32-bit SRCALPHA, caching returns the
same object, and generation is deterministic across cache clears."""

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import json
import math
from pathlib import Path

import pygame
import pytest

from aphelion.render import body_art
from aphelion.render.body_art import (
    PALETTES,
    RING_SPRITE_SCALE,
    SPRITE_SCALE,
    SUN_SPRITE_SCALE,
    body_sprite,
    bucket_diameter,
    marker_dot,
    sprite_scale,
    sun_sprite,
)

_BODIES_DIR = Path(__file__).resolve().parents[2] / "data" / "core" / "bodies"
ALL_IDS = sorted(json.loads(p.read_text(encoding="utf-8"))["id"]
                 for p in _BODIES_DIR.glob("*.json"))


def _expected_edge(body_id: str, diameter_px: int) -> int:
    return int(round(bucket_diameter(diameter_px) * sprite_scale(body_id)))


# ---- every canon body renders ----------------------------------------------

def test_pack_body_list_loaded():
    assert len(ALL_IDS) == 37
    assert "core:sun" in ALL_IDS and "core:saturn" in ALL_IDS


@pytest.mark.parametrize("bid", ALL_IDS)
def test_every_body_renders_at_64px(bid):
    surf = body_sprite(bid, 64, sun_angle=0.7)
    assert isinstance(surf, pygame.Surface)
    assert surf.get_flags() & pygame.SRCALPHA
    assert surf.get_bitsize() == 32
    edge = _expected_edge(bid, 64)
    assert surf.get_size() == (edge, edge)
    # body centered: opaque-ish center, fully transparent corner
    cx = edge // 2
    assert surf.get_at((cx, cx)).a == 255
    assert surf.get_at((0, 0)).a == 0


# ---- geometry contract -------------------------------------------------------

def test_sprite_scales_and_halo_margin():
    assert sprite_scale("core:moon") == SPRITE_SCALE
    assert sprite_scale("core:earth") == SPRITE_SCALE      # halo fits in 1.35x
    assert sprite_scale("core:saturn") == RING_SPRITE_SCALE
    assert sprite_scale("core:sun") == SUN_SPRITE_SCALE
    # earth has an atmosphere halo: alpha present just outside the limb
    surf = body_sprite("core:earth", 96)
    edge = surf.get_width()
    d = bucket_diameter(96)
    px_outside = edge // 2 + int(d * 0.55)                 # r ~ 1.1 radii
    assert surf.get_at((px_outside, edge // 2)).a > 0
    # the moon is airless: same spot is empty space
    surf_moon = body_sprite("core:moon", 96)
    edge_m = surf_moon.get_width()
    assert surf_moon.get_at((edge_m // 2 + int(d * 0.55), edge_m // 2)).a == 0


def test_saturn_rings_visible_beyond_disc():
    surf = body_sprite("core:saturn", 64)
    edge = surf.get_width()
    d = bucket_diameter(64)
    c = edge // 2
    ring_px = c + int(1.8 * d * 0.5)                       # inside ring band
    assert surf.get_at((ring_px, c)).a > 30
    assert surf.get_width() > body_sprite("core:moon", 64).get_width()


# ---- caching + determinism ---------------------------------------------------

def test_cache_returns_identical_object():
    a = body_sprite("core:mars", 96, sun_angle=0.10)
    b = body_sprite("core:mars", 97, sun_angle=0.12)       # same buckets
    assert a is b
    assert marker_dot("core:venus", 3) is marker_dot("core:venus", 3)
    assert sun_sprite(64) is sun_sprite(64)


def test_deterministic_across_cache_clear():
    first = pygame.image.tobytes(body_sprite("core:earth", 96, 0.9), "RGBA")
    body_art._SPRITE_CACHE.clear()
    body_art._SUN_CACHE.clear()
    second = pygame.image.tobytes(body_sprite("core:earth", 96, 0.9), "RGBA")
    assert first == second
    s1 = pygame.image.tobytes(sun_sprite(72), "RGBA")
    body_art._SUN_CACHE.clear()
    assert s1 == pygame.image.tobytes(sun_sprite(72), "RGBA")


# ---- shading + sun-angle buckets ----------------------------------------------

def test_lit_side_faces_sun_and_angle_buckets():
    surf = body_sprite("core:moon", 128, sun_angle=0.0)    # sun toward +x
    arr = pygame.surfarray.array3d(surf).astype(float)
    alpha = pygame.surfarray.array_alpha(surf)
    c = surf.get_width() // 2
    right = arr[c:][alpha[c:] > 200].mean()
    left = arr[:c][alpha[:c] > 200].mean()
    assert right > left * 1.2
    # within one 16-sector bucket: the very same cached surface
    assert surf is body_sprite("core:moon", 128, sun_angle=0.05)
    # opposite sector: different surface, different pixels
    flipped = body_sprite("core:moon", 128, sun_angle=math.pi)
    assert flipped is not surf
    assert pygame.image.tobytes(flipped, "RGBA") != \
        pygame.image.tobytes(surf, "RGBA")


# ---- sun sprite ---------------------------------------------------------------

def test_sun_sprite_core_and_corona():
    surf = sun_sprite(64)
    d = bucket_diameter(64)
    edge = int(round(d * SUN_SPRITE_SCALE))
    assert surf.get_size() == (edge, edge)
    c = edge // 2
    center = surf.get_at((c, c))
    assert center.a == 255
    assert center.r > 230 and center.g > 230               # white-hot core
    corona_px = c + int(1.5 * d * 0.5 / 1.0)               # r ~ 1.5 core radii
    corona = surf.get_at((min(corona_px, edge - 1), c))
    assert 0 < corona.a < 255                              # soft falloff
    assert surf.get_at((0, 0)).a == 0
    assert body_sprite("core:sun", 64) is surf             # star delegates


# ---- marker dots ----------------------------------------------------------------

def test_marker_dot_geometry_and_color():
    surf = marker_dot("core:mars", 3)
    assert surf.get_size() == (8, 8)
    assert surf.get_flags() & pygame.SRCALPHA
    center = surf.get_at((4, 4))
    assert center.a > 200
    assert (center.r, center.g, center.b) == PALETTES["mars"].base
    assert surf.get_at((0, 0)).a == 0                      # AA edge, clear corner


# ---- fallback classes ------------------------------------------------------------

def test_unknown_id_falls_back_sanely():
    surf = body_sprite("mods:slagball_7", 48)              # not in any pack
    assert isinstance(surf, pygame.Surface)
    assert body_art._palette_for("mods:slagball_7").kind == "cratered"
    # registry-driven classes: big radius -> gas giant w/ atmosphere halo scale
    body_art._registry()["mods:bloatworld"] = ("core:sun", 3.0e7)
    assert body_art._palette_for("mods:bloatworld").kind == "gas"
    assert sprite_scale("mods:bloatworld") == SPRITE_SCALE
