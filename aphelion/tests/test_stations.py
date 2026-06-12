"""Stations (06 §3): spin gravity pinned to the worked table, the 200 t
ring spin-up example, balance bands, port capture/E8, the fee law,
MMOD, and boiloff."""

import pytest

from aphelion.sim.stations.keeping import (
    boiloff_kg, mmod_p_pen, stationkeeping_ms_yr, whipple_coverage)
from aphelion.sim.stations.ports import burn_load_ok, can_mate, capture
from aphelion.sim.stations.spin import (
    a_spin, balance, comfort, moment_of_inertia, r_for, spinup_prop_kg,
    spinup_time_s, v_rim)


def test_spin_design_table_anchors():
    """06 §3.1: 1 g @ 4 rpm → r 55.9 m (v_rim 23.4); 0.38 g @ 2 rpm →
    84.6 m; lunar bolo 0.17 g @ 4 rpm → 9.2 m."""
    assert r_for(9.80665, 4.0) == pytest.approx(55.9, abs=0.1)
    assert v_rim(4.0, 55.9) == pytest.approx(23.4, abs=0.1)
    assert r_for(3.71, 2.0) == pytest.approx(84.6, abs=0.2)
    assert r_for(1.62, 4.0) == pytest.approx(9.2, abs=0.1)
    assert a_spin(4.0, 55.9) == pytest.approx(9.81, abs=0.02)


def test_ring_spinup_worked_example():
    """200 t ring at r = 56 m: I = 6.27e8 kg·m²; 800 N of rim RCS →
    spin-up 5,864 s and 1,595 kg of storables (06 §3.2)."""
    i = moment_of_inertia([(200_000.0, 56.0)])
    assert i == pytest.approx(6.27e8, rel=0.001)
    assert spinup_time_s(i, 4.0, 800.0 * 56.0) == pytest.approx(
        5_864.0, abs=15.0)
    assert spinup_prop_kg(i, 4.0, 56.0, 300.0) == pytest.approx(
        1_595.0, abs=15.0)


def test_comfort_rules_and_e9():
    ring = comfort(4.0, 55.9)            # the 1 g design anchor
    assert not ring["e9"]
    assert ring["adapt_days"] == 7.0     # 2–4 rpm adaptation band
    assert ring["productivity"] == 1.0
    assert ring["decon_regime"] == "none"
    fast = comfort(6.0, 25.0)            # ~1 g at 6 rpm: legal but harsh
    assert not fast["e9"] and fast["productivity"] == pytest.approx(0.85)
    # at the table's exact 24.8 m the gradient rule trips too: stacks
    assert comfort(6.0, 24.8)["productivity"] == pytest.approx(0.80)
    assert comfort(6.5, 20.0)["e9"]      # > 6 rpm crewed = E9
    bolo = comfort(4.0, 9.2)             # lunar bolo accepts rule 5+6
    assert bolo["productivity"] == pytest.approx(0.90)
    assert bolo["decon_regime"] == "half"


def test_balance_bands():
    assert balance(0.5, 56.0) == "ok"
    assert balance(1.5, 56.0) == "wobble"      # > 0.02·r
    assert balance(6.0, 56.0) == "despin"      # > 0.10·r


def test_ports_e8_capture_and_burn_loads():
    assert can_mate("S", "S") and not can_mate("S", "L")
    assert capture("S", 0.08) == "captured"
    assert capture("S", 0.15) == "bounce"
    assert capture("S", 0.60) == "damage"
    assert capture("L", 0.08) == "bounce"      # L closes at ≤ 0.05
    assert capture("L", 0.08, magnetic=True) == "captured"
    # Build B: 30 t payload at 3.42 m/s² = 103 kN — fine through a DK-L,
    # would rip a DK-S off the stack
    ok_l, load = burn_load_ok("L", 30.0, 3.42)
    assert ok_l and load == pytest.approx(102.6, abs=0.5)
    assert not burn_load_ok("S", 30.0, 3.42)[0]
    # W6 wobble halves the rating
    assert not burn_load_ok("L", 30.0, 3.42, derate=0.5)[0] \
        or load <= 400.0


def test_stationkeeping_fee_law():
    assert stationkeeping_ms_yr("core:earth", 250.0) == 25.0
    assert stationkeeping_ms_yr("core:earth", 400.0) == pytest.approx(
        20.0)
    assert stationkeeping_ms_yr("core:earth", 450.0) == pytest.approx(
        6.32, abs=0.1)                          # log-linear between
    assert stationkeeping_ms_yr("core:earth", 700.0) == 2.0
    assert stationkeeping_ms_yr("core:earth", lpoint="L2") == 4.0
    assert stationkeeping_ms_yr("core:earth", lpoint="L5") == 0.0
    assert stationkeeping_ms_yr("core:moon", 50.0) == 5.0


def test_mmod_and_boiloff():
    """Φ=1e-4/m²/yr over 100 m² bare for a year ≈ 1%; a stuffed Whipple
    cuts it 50×. Unpowered LH2 vents ~0.5%/day; ZBO holds it."""
    assert mmod_p_pen(1e-4, 100.0, 365.25) == pytest.approx(0.00995,
                                                            abs=2e-4)
    assert mmod_p_pen(1e-4, 100.0, 365.25, eta=0.98) == pytest.approx(
        0.0002, abs=2e-5)
    exposed, frac = whipple_coverage(
        40.0, [{"covers_m2": 10.0, "whipple_eta": 0.98}] * 3)
    assert exposed == pytest.approx(10.0 + 0.6, abs=0.01)
    assert frac == pytest.approx(0.75)
    assert boiloff_kg("Hydrogen", 4_000.0, 30.0,
                      zbo_powered=False) == pytest.approx(558.0, abs=5.0)
    assert boiloff_kg("Hydrogen", 4_000.0, 30.0, zbo_powered=True) == 0.0
    assert boiloff_kg("NTO", 1_000.0, 30.0, False) == 0.0  # storable
