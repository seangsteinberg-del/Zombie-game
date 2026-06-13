"""EVA walk mode: deterministic terrain, body-true jump physics (six
times higher on the Moon), the suit clock, and interaction geometry."""

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pytest

from aphelion.game.eva import (
    ANOMALY_X_M, EvaState, SCOOPS_PER_EVA, SUIT_O2_S, module_positions,
    terrain_line)

G_MOON = 1.62
G_EARTH = 9.81


def test_terrain_deterministic_and_graded_flat_at_pad():
    a = terrain_line("core:sec_moon_10", 8.0)
    b = terrain_line("core:sec_moon_10", 8.0)
    assert (a == b).all()
    c = terrain_line("core:sec_mars_07", 8.0)
    assert (a != c).any()
    w = EvaState("core:sec_moon_10", 8.0, G_MOON, "V")
    assert abs(w.ground_at(0.0)) < 0.05          # the pad is graded
    assert abs(w.ground_at(10.0)) < 0.6
    relief = [abs(w.ground_at(x)) for x in range(200, 900, 50)]
    assert max(relief) > 1.0                     # real hills out there


def test_jump_apex_scales_with_gravity():
    moon = EvaState("core:sec_moon_10", 8.0, G_MOON, "V")
    earth = EvaState("core:sec_earth_01", 2.0, G_EARTH, "V")
    assert moon.jump_apex_m() == pytest.approx(
        earth.jump_apex_m() * G_EARTH / G_MOON)
    assert moon.jump_apex_m() > 3.0              # a real lunar leap
    # integrate a jump: walker leaves the ground and comes back down
    moon.step(0.0, 0, False, True)
    assert moon.airborne
    top = 0.0
    for _ in range(8_000):
        moon.step(0.01, 0, False, False)
        top = max(top, moon.y - moon.ground_at(moon.x))
        if not moon.airborne:
            break
    assert not moon.airborne
    assert top == pytest.approx(moon.jump_apex_m(), rel=0.05)


def test_walking_covers_ground_and_animates():
    w = EvaState("core:sec_moon_10", 8.0, G_MOON, "V")
    x0 = w.x
    for _ in range(100):
        w.step(0.02, 1, False, False)
    assert w.x - x0 == pytest.approx(1.6 * 2.0, rel=0.05)
    assert w.dist_walked > 3.0
    assert w.frame > 0.0
    for _ in range(100):
        w.step(0.02, -1, True, False)            # run back
    assert w.facing == -1


def test_suit_clock_and_scoops():
    w = EvaState("core:sec_moon_10", 8.0, G_MOON, "V")
    assert w.o2_s == SUIT_O2_S and w.scoops_left == SCOOPS_PER_EVA
    w.step(10.0, 0, False, False)
    assert w.o2_s == pytest.approx(SUIT_O2_S - 10.0)
    assert 0.0 < w.o2_frac < 1.0


def test_suit_consumables_deplete_and_limit():
    w = EvaState("core:sec_moon_10", 8.0, G_MOON, "V")
    b0, f0 = w.batt_wh, w.feedwater_kg
    # idle for a while: battery and feedwater drop, scrubber loads
    for _ in range(600):
        w.step(1.0, 0, False, False)
    assert w.batt_wh < b0 and w.feedwater_kg < f0 and w.co2_load_kg > 0.0
    st = w.suit_status()
    assert set(st["clocks"]) == {"O2", "PWR", "H2O", "CO2"}
    assert st["limit_s"] <= w.o2_s                       # min of the four
    # running drains cooling far faster than resting (exertion scaling)
    rest = EvaState("core:sec_moon_10", 8.0, G_MOON, "V")
    runr = EvaState("core:sec_moon_10", 8.0, G_MOON, "V")
    for _ in range(120):
        rest.step(0.5, 0, False, False)
        runr.step(0.5, 1, True, False)
    assert runr.feedwater_kg < rest.feedwater_kg


def test_lamp_loads_the_battery():
    dark = EvaState("core:sec_moon_10", 8.0, G_MOON, "V")
    lit = EvaState("core:sec_moon_10", 8.0, G_MOON, "V")
    lit.lamp_on = True
    for _ in range(300):
        dark.step(1.0, 0, False, False)
        lit.lamp_on = True
        lit.step(1.0, 0, False, False)
    assert lit.batt_wh < dark.batt_wh                    # the lamp costs power


def test_recharge_tops_off_every_consumable():
    w = EvaState("core:sec_moon_10", 8.0, G_MOON, "V")
    for _ in range(800):
        w.step(1.0, 1, True, False)
    w.recharge_suit()
    assert w.o2_s == SUIT_O2_S and w.co2_load_kg == 0.0
    from aphelion.game.eva import SUIT_BATT_WH, SUIT_FEEDWATER_KG
    assert w.batt_wh == SUIT_BATT_WH
    assert w.feedwater_kg == SUIT_FEEDWATER_KG


def test_interaction_geometry():
    w = EvaState("core:sec_moon_10", 8.0, G_MOON, "V")
    w.x = 1.0
    assert w.near(0.0)                            # at the lander
    assert not w.near(ANOMALY_X_M)
    pos = module_positions(["solar_array", "drill_ice", "hab_module"])
    assert list(pos) == [0, 1, 2]
    assert pos[0] >= 20.0 and pos[2] > pos[1] > pos[0]
