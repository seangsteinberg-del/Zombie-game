"""Tile site-worlds (S-7c + director directive): deterministic strata,
visible ice/ore veins by site kind, caves, digging at canon rates, and
persistent edits."""

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import numpy as np

from aphelion.game.tileworld import (
    AIR, BEDROCK, DIG_S, H_TILES, ICE, ORE, REGOLITH, ROCK, SKY_ROWS,
    TILE_KG, TILE_M, TileWorld, W_TILES, generate)


def test_world_deterministic_per_sector():
    a = generate("core:sec_moon_10", 8.0, "psr_ice")
    b = generate("core:sec_moon_10", 8.0, "psr_ice")
    assert (a == b).all()
    c = generate("core:sec_mars_07", 8.0, "mars_ice")
    assert (a != c).any()


def test_strata_order_and_bedrock_floor():
    g = generate("core:sec_moon_07", 6.0, "regolith")
    # bedrock seals the bottom
    assert (g[:, -4:] == BEDROCK).all()
    # somewhere a column shows air over regolith over rock
    found = False
    for x in range(0, W_TILES, 64):
        col = g[x]
        kinds = [t for t in col if t != AIR]
        if (len(kinds) > 20 and kinds[0] == REGOLITH
                and ROCK in kinds[:60]):
            found = True
            break
    assert found


def test_icy_worlds_carry_visible_ice_lenses():
    icy = generate("core:sec_moon_11", 8.0, "psr_ice")
    dry = generate("core:sec_moon_01", 2.0, "regolith")
    assert (icy == ICE).sum() > (dry == ICE).sum() * 2
    assert (dry == ORE).sum() > 200            # mare rock carries veins


def test_caves_exist_underground():
    g = generate("core:sec_moon_06", 8.0, "regolith")   # Marius Hills
    underground_air = 0
    for x in range(0, W_TILES, 16):
        col = g[x]
        solid = np.nonzero(col != AIR)[0]
        if len(solid):
            underground_air += int((col[solid[0]:] == AIR).sum())
    assert underground_air > 100                # somewhere to spelunk


def test_dig_yields_and_persistence():
    w = TileWorld("core:sec_moon_10", 8.0, "psr_ice")
    x = 120.0
    y = w.surface_y(x)
    assert not w.solid(x, y + 0.6)              # head room above ground
    assert w.solid(x, y - 0.6)                  # ground below the feet
    t, secs = w.dig(x, y - 0.6)
    assert t in (REGOLITH, ROCK, ICE, ORE)
    assert secs == DIG_S[t] and TILE_KG[t] > 0
    assert not w.solid(x, y - 0.6)              # the hole is real
    # edits persist through a reload via the dug list
    dug = w.dug_list()
    w2 = TileWorld("core:sec_moon_10", 8.0, "psr_ice", dug=dug)
    assert not w2.solid(x, y - 0.6)
    # dig to bedrock is refused
    t_b, s_b = w2.dig(x, w2.row_to_y(H_TILES - 1))
    assert t_b == BEDROCK and s_b == 0.0


def test_surface_matches_walk_terrain():
    """The tile surface is the SAME heightline the EVA walker used."""
    from aphelion.game.eva import EvaState
    w = TileWorld("core:sec_moon_10", 8.0, "psr_ice")
    e = EvaState("core:sec_moon_10", 8.0, 1.62, "V")
    for x in (0.0, 50.0, 200.0, -300.0):
        assert abs(w.surface_y(x) - e.ground_at(x)) <= 2.5 * TILE_M


def test_world_size_is_terraria_scale():
    assert W_TILES * TILE_M == 2_048.0          # a real afternoon of walking
    assert (H_TILES - SKY_ROWS) * TILE_M == 160.0


# ---- the walker in the tile world (W part 3b) -----------------------------

def test_walker_falls_into_shafts_and_walls_block():
    import pytest

    from aphelion.game.eva import EvaState
    w = TileWorld("core:sec_moon_10", 8.0, "psr_ice")
    e = EvaState("core:sec_moon_10", 8.0, 1.62, "V", tiles=w)
    assert e.y == pytest.approx(w.surface_y(e.x), abs=0.01)
    # dig a 2.5 m shaft one column wide, two metres ahead
    x_sh = e.x + 2.0
    for _ in range(5):
        w.dig(x_sh, w.surface_y(x_sh) - 0.25)
    fell = False
    for _ in range(1_000):                       # walk right, drop in
        e.step(0.02, 1, False, False)
        if e.airborne:
            fell = True
            break
    assert fell
    for _ in range(2_000):                       # settle on the floor
        e.step(0.01, 0, False, False)
        if not e.airborne:
            break
    assert not e.airborne
    # a 2.5 m face is not walkable: the wall blocks
    x_before = e.x
    for _ in range(60):
        e.step(0.02, 1, False, False)
    assert abs(e.x - x_before) < 0.6


def test_roof_stops_the_jump():
    from aphelion.game.eva import EvaState
    w = TileWorld("core:sec_moon_01", 2.0, "regolith")
    e = EvaState("core:sec_moon_01", 2.0, 1.62, "V", tiles=w)
    w.grid[w.col(e.x), w.row(e.y + 2.4)] = ROCK  # a slab overhead
    y0 = e.y
    e.step(0.0, 0, False, True)
    top = e.y
    for _ in range(800):
        e.step(0.01, 0, False, False)
        top = max(top, e.y)
        if not e.airborne:
            break
    assert top - y0 < 1.0                        # vs a 3+ m lunar apex
    assert not e.airborne


def test_dig_target_and_dig_down_drops_one_tile():
    import pytest

    from aphelion.game.eva import EvaState
    w = TileWorld("core:sec_moon_10", 8.0, "psr_ice")
    e = EvaState("core:sec_moon_10", 8.0, 1.62, "V", tiles=w)
    assert e.dig_target(False) is None           # graded pad: open ground
    tx, ty = e.dig_target(True)                  # underfoot, always
    assert w.solid(tx, ty)
    y0 = e.y
    t1, s1 = w.dig(tx, ty)
    assert s1 > 0.0
    e.step(0.02, 0, False, False)
    assert e.y == pytest.approx(y0 - TILE_M, abs=0.01)


def test_walker_traverses_natural_terrain():
    """Risers ≤ 2 tiles are walked; the hills don't trap the suit."""
    from aphelion.game.eva import EvaState
    w = TileWorld("core:sec_moon_10", 8.0, "psr_ice")
    e = EvaState("core:sec_moon_10", 8.0, 1.62, "V", tiles=w)
    for i in range(4_000):
        jump = (not e.airborne) and i % 400 == 0  # hop the odd tall step
        e.step(0.02, 1, True, jump)
    assert e.x > 80.0
    assert e.dist_walked > 60.0
