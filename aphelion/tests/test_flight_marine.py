"""10 §2.4/2.7/2.8 fixtures: Ingenuity at 335 W, the per-body hover
indices (Titan 0.025 = the logistics layer; Mars cargo aviation
deliberately impossible), the SUB-T 330 W closure, V-21 depth law, and
the cryobot's 100 m/day."""

import pytest

from aphelion.sim.environment.buoyancy import venus_lift_kg_m3
from aphelion.sim.vehicles.flight import (
    hover_index, p_cruise_w, p_hover_w, stall_index, v_stall_ms)
from aphelion.sim.vehicles.marine import (
    cryobot_descent_m_day, drag_n, e_melt_j_m3, floats, p_prop_w,
    pressure_pa)


def test_ingenuity_335w_fixture():
    """V-14 calibration: 1.8 kg, A 1.15 m², ρ 0.016, g 3.71, η 0.29 +
    25 W avionics ≈ 335 W."""
    p = p_hover_w(1.8, 3.71, 0.016, 1.15)
    assert p == pytest.approx(335.0, abs=10.0)


def test_per_body_feasibility_indices():
    """§2.4 table: Mars datum hover 2.0 / stall 5.4 (scouts only);
    Venus 54 km 0.93 (Earth-like); Titan 0.025 (40× cheaper than
    Earth)."""
    assert hover_index(3.71, 0.016) == pytest.approx(2.0, abs=0.1)
    assert stall_index(3.71, 0.016) == pytest.approx(5.4, abs=0.2)
    assert hover_index(8.87, 1.05) == pytest.approx(0.93, abs=0.03)
    assert hover_index(1.35, 5.3) == pytest.approx(0.025, abs=0.003)
    assert stall_index(1.35, 5.3) == pytest.approx(0.18, abs=0.01)


def test_titan_cargo_plane_numbers():
    """AIR-T3: 8 t gross, S 60, C_Lmax 1.8 → stall 6.1 m/s; cruise
    40 m/s on L/D 20 needs ~28.8 kW."""
    assert v_stall_ms(8_000.0, 1.35, 5.3, 60.0, cl_max=1.8) == \
        pytest.approx(6.1, abs=0.2)
    assert p_cruise_w(8_000.0, 1.35, 40.0, l_over_d=20.0) == \
        pytest.approx(28_800.0, rel=0.02)


def test_venus_canon_station_lift():
    """§4.2 reconciliation: 54 km / 60 kPa / 300 K → sizing lift 0.35."""
    assert venus_lift_kg_m3() == pytest.approx(0.35, abs=0.05)


def test_sub_t_closure_330w():
    """§2.7: 1.1 m² frontal, Cd 0.10, 1 m/s in 550 kg/m³ sea → ~30 N →
    ~50 W prop; +280 W hotel = 330 W = three RTG-S."""
    d = drag_n(550.0, 0.10, 1.1, 1.0)
    assert d == pytest.approx(30.0, abs=1.0)
    assert p_prop_w(d, 1.0) == pytest.approx(50.0, abs=2.0)
    assert pressure_pa(300.0) == pytest.approx(368_700.0, rel=0.01)
    assert floats(2_000.0, 4.0, 550.0)          # BOAT-T with cargo
    assert not floats(2_200.0, 4.0, 550.0)      # past the 0.95 margin


def test_cryobot_100m_day():
    """V-22/23: 546 MJ/m³ ideal × k_loss 3; Ø 0.26 m at 100 kWt →
    ~100 m/day → 15 km in ~150 d."""
    assert e_melt_j_m3(1.0) == pytest.approx(546e6, rel=0.01)
    a = 3.14159 * 0.13 ** 2
    v = cryobot_descent_m_day(100_000.0, a)
    assert v == pytest.approx(100.0, abs=5.0)
    assert 15_000.0 / v == pytest.approx(150.0, abs=10.0)
