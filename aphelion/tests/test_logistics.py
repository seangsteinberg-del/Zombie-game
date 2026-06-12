"""05 §3.2–3.3 validation targets: the three F-3 worked examples MUST
reproduce, the Pelican family cycles, the F-6 ladder (Longhaul's 32%
bare-loss check), and the mass-driver anchors."""

import pytest

from aphelion.sim.industry.logistics import (
    MD_THROUGHPUT_T_DAY, MD_WHITELIST, boiloff_frac, gear_ratio,
    lander_cycle, md_duty_avg_mw, md_energy_kwh_per_kg, md_muzzle_peak_mw,
    md_shot_mj, md_track_length_m, prop_for_dv_eff, sep_thrust_n,
    sep_trip_days)


def test_f3_worked_examples():
    """§3.3 table: Pallet 21.9 t, Drayage 10.0 t Xe / ~227 d, Longhaul
    56.5 t H2."""
    pallet = prop_for_dv_eff(4.5, 6.0, 4_200.0, 380.0)
    assert pallet == pytest.approx(21.9, abs=0.1)
    assert gear_ratio(6.0, pallet) == pytest.approx(0.27, abs=0.01)

    dray = prop_for_dv_eff(8.0, 20.0, 8_400.0, 2_800.0)
    assert dray == pytest.approx(10.0, abs=0.1)
    f = sep_thrust_n(300.0, 2_800.0)
    assert f == pytest.approx(14.2, abs=0.2)
    assert sep_trip_days(dray, f, 2_800.0) == pytest.approx(227.0,
                                                            abs=10.0)
    assert gear_ratio(20.0, dray) == pytest.approx(2.0, abs=0.05)

    longhaul = prop_for_dv_eff(22.0, 40.0, 5_720.0, 900.0)
    assert longhaul == pytest.approx(56.5, abs=0.2)
    assert gear_ratio(40.0, longhaul) == pytest.approx(0.71, abs=0.01)


def test_pelican_cycles():
    """§3.7: orbit-refueled Pelican 37.6 t/cycle (G 0.32); hydrolox
    22.0; Mars surface-refueled 49.9 (descent 4.22 + ascent 45.63)."""
    p = lander_cycle(9.0, 6.0, 6.0, 1_900.0, 1_850.0, 320.0)
    assert p.ascent_t == pytest.approx(12.86, abs=0.05)
    assert p.descent_t == pytest.approx(24.75, abs=0.1)
    assert p.total_t == pytest.approx(37.6, abs=0.15)
    assert p.gear == pytest.approx(0.32, abs=0.01)

    ph = lander_cycle(9.0, 6.0, 6.0, 1_900.0, 1_850.0, 445.0)
    assert ph.total_t == pytest.approx(22.0, abs=0.2)

    pm = lander_cycle(10.0, 6.0, 2.0, 700.0, 4_000.0, 320.0,
                      surface_refuel=True)
    assert pm.descent_t == pytest.approx(4.22, abs=0.05)
    assert pm.ascent_t == pytest.approx(45.63, abs=0.2)
    assert pm.total_t == pytest.approx(49.9, abs=0.25)


def test_f6_ladder_and_longhaul_zbo_rationale():
    """Longhaul closes ONLY because of ZBO: bare H2 loses ~32% over the
    259-day leg; depot-grade ~2.6%."""
    assert boiloff_frac("h2_bare", 259.0) == pytest.approx(0.322,
                                                           abs=0.01)
    assert boiloff_frac("h2_depot", 259.0) == pytest.approx(0.026,
                                                            abs=0.002)
    assert boiloff_frac("h2_depot", 259.0, zbo=True) == 0.0
    assert boiloff_frac("storable", 1_000.0) == 0.0
    assert boiloff_frac("o2ch4_shielded", 30.0) == pytest.approx(
        0.009, abs=0.001)


def test_mass_driver_anchors():
    """§3.2 lunar baseline: 3.2 km track, 1.45 kWh/kg, 52 MJ shots,
    2.6 MW duty, ~41 MW muzzle peak, 43.2 t/day."""
    assert md_track_length_m(2_500.0, 100.0) == pytest.approx(3_187.0,
                                                              abs=5.0)
    assert md_energy_kwh_per_kg(2_500.0) == pytest.approx(1.447,
                                                          abs=0.01)
    assert md_shot_mj(10.0, 2_500.0) == pytest.approx(52.1, abs=0.2)
    assert md_duty_avg_mw(10.0, 2_500.0) == pytest.approx(2.6, abs=0.05)
    assert md_muzzle_peak_mw(10.0, 2_500.0) == pytest.approx(40.9,
                                                             abs=0.5)
    assert MD_THROUGHPUT_T_DAY == pytest.approx(43.2)
    assert "Electronics" not in MD_WHITELIST     # finished goods fly
    assert "Water" in MD_WHITELIST               # sealed canisters
