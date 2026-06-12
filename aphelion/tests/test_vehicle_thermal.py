"""10 §2.3 fixtures: the V-11 Titan cab anchor (6 kW aerogel / 15 kW
bare, MLI shorted in atmosphere), the SUB-T 2.4 kW closure under 3×
RTG-S waste heat, hibernation survival power and the brutal 354 h
battery-only lunar night, the STO-WADI hold band, the 273/233 K
battery brick rules, and the 09 H-5 endurance clocks."""

import math

import pytest

from aphelion.sim.vehicles.thermal import (
    CHARGE_MIN_K, DAMAGE_K, WADI_HOLD_K, WADI_TRICKLE_BAND_K,
    battery_brick_events, endurance_clock_h, lunar_night_kwh,
    p_survival_w, q_loss_w)


def test_titan_cab_v11_anchor():
    """V-11: 30 m² cab at ΔT 200 K → 6 kW aerogel / 15 kW bare; MLI is
    vacuum-only (shorts to bare in atmosphere; 1.8 kW in vacuum)."""
    assert q_loss_w("aerogel", 30.0, 290.0, 90.0) == pytest.approx(6_000.0)
    assert q_loss_w("bare", 30.0, 290.0, 90.0) == pytest.approx(15_000.0)
    assert q_loss_w("mli", 30.0, 290.0, 90.0, in_atmosphere=True) == \
        pytest.approx(q_loss_w("bare", 30.0, 290.0, 90.0))
    assert q_loss_w("mli", 30.0, 290.0, 90.0) == pytest.approx(1_800.0)


def test_sub_t_rtg_waste_heat_closure():
    """V-11 cross-check: ~12 m² aerogel hull at ΔT 200 K → ~2.4 kW,
    covered by the 3× RTG-S units' ~6 kWt waste heat."""
    q = q_loss_w("aerogel", 12.0, 293.0, 93.0)
    assert q == pytest.approx(2_400.0)
    assert q < 6_000.0


def test_hibernation_survival_and_lunar_night():
    """V-11 + V-5a 25 W floor: 8 m² MLI rover at ΔT 190 K in vacuum →
    ~481 W; over the 354 h lunar night that is >100 kWh from the pack —
    the pull toward wadis and RTGs."""
    p = p_survival_w("mli", 8.0, 290.0, 100.0)
    assert p == pytest.approx(481.0, abs=5.0)
    assert lunar_night_kwh(p) > 100.0


def test_wadi_band():
    """STO-WADI holds ≥ ~245 K: clears the 233 K damage line, and the
    ~30 K pack trickle-heat reaches the 273 K charge threshold."""
    assert WADI_HOLD_K > DAMAGE_K
    assert WADI_HOLD_K + WADI_TRICKLE_BAND_K >= CHARGE_MIN_K + 2.0


def test_battery_brick_rules():
    """Failure table row 3: <233 K unpowered >6 h, or any transfer
    attempt <273 K → −30% capacity/event."""
    assert battery_brick_events(230.0, 6.1) == pytest.approx(0.70)
    assert battery_brick_events(230.0, 5.0) == pytest.approx(1.0)
    assert battery_brick_events(270.0, 0.0, attempted_transfer=True) == \
        pytest.approx(0.70)
    assert battery_brick_events(274.0, 0.0, attempted_transfer=True) == \
        pytest.approx(1.0)


def test_h5_endurance_clocks():
    """09 H-5: Venus surface tier 0 = 2.1 h (Venera-13 127 min); T3
    SiC = 1440 h; Mercury twilight outruns the terminator forever."""
    assert endurance_clock_h("venus_surface", 0) == pytest.approx(2.1)
    assert endurance_clock_h("venus_surface", 3) == 1_440.0
    assert endurance_clock_h("mercury_noon", 2) == pytest.approx(8.0)
    assert endurance_clock_h("mercury_noon", 5) == 1_440.0
    assert math.isinf(endurance_clock_h("mercury_twilight"))
    assert math.isinf(endurance_clock_h("mars_surface"))
