"""10 §2.9 fixtures: V-24a wheel/track wear with the tracks terrain
cap, V-24b rotor wear, V-24c hull wear with sea-state interpolation
and effervescence, V-24d thermal cycling, the Venus-surface skip, and
the 05-horizon sanity haul. Separate from test_wear.py (the 05
base-module F-7 layer) per DECISIONS A5."""

import pytest

from aphelion.sim.vehicles.wear import (
    FIELD_SPARES_MULT, FIELD_TIME_MULT, dc_hull, dc_rotors,
    dc_thermal_cycles, dc_wheels, field_repair_cost, sea_state_mult,
    skips_km_wear)


def test_wheels_moon_regolith_and_mars_road():
    """V-24a: 100 km wheels on Moon regolith = 0.4% × 1.0 × 1.5 =
    0.006; Mars road = 0.4% × 0.5 × 1.0 = 0.002; linear in km."""
    assert dc_wheels(100.0, "regolith", "moon") == pytest.approx(0.006)
    assert dc_wheels(100.0, "road", "mars") == pytest.approx(0.002)
    assert dc_wheels(250.0, "regolith", "moon") == \
        pytest.approx(2.5 * dc_wheels(100.0, "regolith", "moon"))


def test_tracks_chaos_terrain_cap():
    """V-24a: tracks cap terrain_mult at 1.5 — CHAOS on the Moon is
    0.6% × 1.5 × 1.5 = 0.0135, NOT 0.018."""
    assert dc_wheels(100.0, "chaos", "moon", tracks=True) == \
        pytest.approx(0.0135)
    assert dc_wheels(100.0, "chaos", "moon", tracks=True) != \
        pytest.approx(0.018)


def test_rotors_titan_and_venus_cloud():
    """V-24b: 10 fl-h on Titan = 0.3% × 0.7 = 0.0021; Venus-cloud
    rotorcraft = 0.3% × 2.0 = 0.006 (acid, not dust)."""
    assert dc_rotors(10.0, "titan") == pytest.approx(0.0021)
    assert dc_rotors(10.0, "venus_cloud") == pytest.approx(0.006)


def test_hull_sea_states_and_effervescence():
    """V-24c: 10 dive-h at state 0 = 0.002; state 4 = ×2.0 → 0.004;
    state 3 interpolates ×1.5; state 1 with effervescence = ×1.2 →
    0.0024."""
    assert dc_hull(10.0, sea_state=0) == pytest.approx(0.002)
    assert dc_hull(10.0, sea_state=4) == pytest.approx(0.004)
    assert sea_state_mult(3) == pytest.approx(1.5)
    assert dc_hull(10.0, sea_state=1, effervescence=True) == \
        pytest.approx(0.0024)


def test_thermal_cycles_and_venus_surface_skip():
    """V-24d: 0.1% per survival-band night → 10 cycles = 0.010; Venus
    SURFACE vehicles skip V-24 entirely (09 H-5 clocks)."""
    assert dc_thermal_cycles(10) == pytest.approx(0.010)
    assert skips_km_wear("venus_surface") is True
    assert skips_km_wear("mars") is False


def test_moon_haul_inside_05_mtbf_horizon():
    """V-24a sanity: a 1,000-km Moon regolith haul drops C by 0.06 —
    wheels need service well inside the 05 MTBF horizon."""
    dc = dc_wheels(1_000.0, "regolith", "moon")
    assert dc == pytest.approx(0.06)
    assert 0.05 < dc < 0.07


def test_field_repair_multipliers():
    """10 §2.9 service costs: field repair = ×3 spares, ×2 time
    (garage = full repair rate)."""
    assert FIELD_SPARES_MULT == pytest.approx(3.0)
    assert FIELD_TIME_MULT == pytest.approx(2.0)
    spares, time_h = field_repair_cost(0.010, 4.0)
    assert spares == pytest.approx(0.030)
    assert time_h == pytest.approx(8.0)
