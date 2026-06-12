"""10 §2.1 calibration anchors — these MUST hold: the LRV's 88 km, the
SEV's 170/293/425 km ladder, Curiosity's 0.3 km/h crawl, the 18 t
hauler's 2.9 kWh/km, the Earth e-truck sanity row, and the worked
ground-pressure checks."""

import pytest

from aphelion.sim.vehicles.locomotion import (
    ETA_DRIVE_T1, TERRAIN, d_stop_m, e_km_kwh, embedding_risk, f_roll_n,
    p_ground_pa, range_km, rtg_cruise_ms, theta_max_deg, v_max_ms)

G_MOON = 1.62
G_MARS = 3.71


def test_lrv_reproduces_88_km():
    """Apollo LRV: 670 kg gross on the Moon -> 163 N -> 0.089 kWh/km
    with the 0.15 kW hotel at 8 km/h -> 88 km on 8.7 kWh AgZn × 0.9."""
    f = f_roll_n(TERRAIN["regolith"].crr, 670.0, G_MOON)
    assert f == pytest.approx(163.0, abs=1.0)
    e = e_km_kwh(f, 150.0, 8.0, eta_drive=ETA_DRIVE_T1)
    assert e == pytest.approx(0.089, abs=0.002)
    assert range_km(8.7, e, primary=True) == pytest.approx(88.0, abs=2.0)


def test_sev_range_ladder():
    """RVR-PRESS (3.6 t gross, 1.56 kW hotel, 10 km/h): raw 0.50 /
    track 0.29 / road 0.20 kWh/km -> 170/293/425 km on 100 kWh × 0.85."""
    hotel = 1_560.0
    es = {}
    for key, target in (("regolith", 0.50), ("compacted", 0.29),
                        ("road", 0.20)):
        f = f_roll_n(TERRAIN[key].crr, 3_600.0, G_MOON)
        es[key] = e_km_kwh(f, hotel, 10.0)
        assert es[key] == pytest.approx(target, abs=0.015)
    assert range_km(100.0, es["regolith"]) == pytest.approx(170.0, abs=8)
    assert range_km(100.0, es["compacted"]) == pytest.approx(293.0,
                                                             abs=10)
    assert range_km(100.0, es["road"]) == pytest.approx(425.0, abs=10)


def test_mars_rtg_rover_crawls():
    """Curiosity-class: 110 We − 60 W avionics through a T1 drivetrain
    against 371 N -> ~0.09 m/s ≈ 0.3 km/h, range unlimited."""
    f = f_roll_n(TERRAIN["duricrust"].crr, 1_000.0, G_MARS)
    assert f == pytest.approx(371.0, abs=1.0)
    v = rtg_cruise_ms(50.0, f)
    assert v == pytest.approx(0.0876, abs=0.003)
    assert v * 3.6 == pytest.approx(0.32, abs=0.02)


def test_hauler_and_earth_sanity():
    """18 t Mars hauler on duricrust: 6.68 kN -> 2.9 kWh/km (T1 drive).
    Earth road sanity: ~0.034 kWh/gross-t·km ≈ real e-trucks."""
    f = f_roll_n(TERRAIN["duricrust"].crr, 18_000.0, G_MARS)
    assert f == pytest.approx(6_678.0, abs=10.0)
    assert e_km_kwh(f, 60.0, 15.0, eta_drive=ETA_DRIVE_T1) == \
        pytest.approx(2.9, abs=0.06)
    f_t = f_roll_n(TERRAIN["earth_road"].crr, 1_000.0, 9.81)
    assert e_km_kwh(f_t, 0.0, 60.0, eta_drive=ETA_DRIVE_T1) == \
        pytest.approx(0.034, abs=0.002)


def test_ground_pressure_worked_checks():
    """§1.2: LRV ÷4 mesh 5.4 kPa ≪ 25 ✓; 1 t rover ÷6 rigid 15.5 kPa
    fails DUNE's 7 by design; 60 t crawler ÷12 tracks 37 kPa."""
    assert p_ground_pa(670.0, G_MOON, 4, 0.05) == pytest.approx(
        5_430.0, abs=50.0)
    p_rigid = p_ground_pa(1_000.0, G_MARS, 6, 0.04)
    assert p_rigid == pytest.approx(15_460.0, abs=100.0)
    assert embedding_risk("dune", p_rigid)            # Spirit's killer
    assert not embedding_risk("duricrust", p_rigid)
    assert p_ground_pa(60_000.0, G_MOON, 12, 0.22) == pytest.approx(
        36_800.0, rel=0.02)


def test_v6_v7_v8():
    """Traction limit, stopping distance, the √g speed governor (Moon
    12.8/36.6 km/h raw/road)."""
    assert theta_max_deg(0.6, 0.15) == pytest.approx(24.2, abs=0.3)
    # 10 km/h on lunar regolith: long stop at one-sixth g
    assert d_stop_m(10.0 / 3.6, 0.6, G_MOON) == pytest.approx(3.97,
                                                              abs=0.1)
    assert v_max_ms(G_MOON, "raw") * 3.6 == pytest.approx(12.8, abs=0.2)
    assert v_max_ms(G_MOON, "road") * 3.6 == pytest.approx(36.6,
                                                           abs=0.3)
    assert v_max_ms(G_MARS, "raw") * 3.6 == pytest.approx(19.4, abs=0.3)
