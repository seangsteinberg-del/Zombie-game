"""Vessel-art tests: every core part renders sprite + thumb, sizing follows
the part data, caches return identical objects, output is deterministic."""

import math
import os

import pytest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from aphelion.content.loader import default_data_dir, load_packs
from aphelion.content.validate import validate
from aphelion.render import vessel_art
from aphelion.render.vessel_art import (
    app_icon, craft_icon, part_sprite, part_thumb, plume, vessel_sprite)


@pytest.fixture(scope="module")
def db():
    d = load_packs(default_data_dir())
    validate(d)
    return d


def test_every_part_renders_sprite_and_thumb(db):
    assert len(db.parts) == 30           # 14 engines + 15 tanks + payload
    for pid, part in db.parts.items():
        spr = part_sprite(part, pid)
        assert isinstance(spr, pygame.Surface)
        assert spr.get_flags() & pygame.SRCALPHA
        w, h = spr.get_size()
        assert 0 < w <= 512 and 0 < h <= 512
        thumb = part_thumb(part, pid)
        assert thumb.get_size() == (28, 28)
        assert thumb.get_flags() & pygame.SRCALPHA


def test_tank_size_follows_capacity(db):
    big = part_sprite(db.parts["core:tank_depot"], "core:tank_depot", 6.0)
    small = part_sprite(db.parts["core:tank_ml_s"], "core:tank_ml_s", 6.0)
    assert big.get_height() > small.get_height()
    assert big.get_width() > small.get_width()


def test_engine_size_follows_thrust(db):
    big = part_sprite(db.parts["core:engine_m2256"], "core:engine_m2256", 10.0)
    small = part_sprite(db.parts["core:engine_ml24"], "core:engine_ml24", 10.0)
    assert big.get_width() > small.get_width()
    assert big.get_height() > small.get_height()


def test_part_sprite_cache_returns_same_object(db):
    a = part_sprite(db.parts["core:tank_ml_m"], "core:tank_ml_m")
    b = part_sprite(db.parts["core:tank_ml_m"], "core:tank_ml_m")
    assert a is b
    t1 = part_thumb(db.parts["core:tank_ml_m"], "core:tank_ml_m")
    t2 = part_thumb(db.parts["core:tank_ml_m"], "core:tank_ml_m")
    assert t1 is t2


def test_part_sprite_deterministic(db):
    pid = "core:engine_k845"
    first = pygame.image.tobytes(part_sprite(db.parts[pid], pid), "RGBA")
    vessel_art._PART_CACHE.clear()
    second = pygame.image.tobytes(part_sprite(db.parts[pid], pid), "RGBA")
    assert first == second


def test_vessel_sprite_two_stage_taller_than_one(db):
    lower = ["core:engine_m733", "core:engine_m733", "core:tank_ml_xl"]
    upper = ["core:engine_mv815", "core:tank_ml_m", "core:payload_2t"]
    one = vessel_sprite(db, [lower])
    two = vessel_sprite(db, [lower, upper])
    assert two.get_height() > one.get_height()
    assert two.get_height() <= 440
    assert two.get_width() <= 512
    assert two.get_flags() & pygame.SRCALPHA
    assert vessel_sprite(db, [lower, upper]) is two


def test_craft_icon_sectors_and_burning():
    a = craft_icon(0.0)
    assert a.get_size() == (36, 36)
    assert a.get_flags() & pygame.SRCALPHA
    assert craft_icon(0.01) is a         # same 15-degree sector -> cached
    b = craft_icon(math.pi / 2)
    assert b is not a
    flame = craft_icon(0.0, burning=True)
    assert (pygame.image.tobytes(flame, "RGBA")
            != pygame.image.tobytes(a, "RGBA"))


def test_plume_frames_cached_and_sized():
    p0 = plume(64, 16, 0.0)
    assert p0.get_size() == (16, 64)
    assert p0.get_flags() & pygame.SRCALPHA
    assert plume(64, 16, 0.05) is p0     # same animation frame (8 total)
    assert plume(64, 16, 0.5) is not p0


def test_app_icon():
    icon = app_icon()
    assert icon.get_size() == (32, 32)
    assert icon.get_flags() & pygame.SRCALPHA
    assert app_icon() is icon
