"""10 §1.0/§1.1 fixtures: chassis grid/cap table, integrated cutoffs,
V-0a/V-0b/V-0c/V-0d validation, the tilt-warn icon (hazard row 1), the
four V-1a worked ground-pressure checks, the overhaul cost rule, and
the §1.4 UTL-CRANE lift law."""

import math

import pytest

from aphelion.sim.vehicles import marine, powerplant
from aphelion.sim.vehicles.chassis import (
    CHASSIS, FLOAT_MARGIN, crane_lift_t, h_com_loaded, is_integrated,
    overhaul_bill_t, tilt_warn_rad, v0a_clearance, v0a_rock_warn,
    v0b_ok, v0b_theta_tip_rad, v0c_ok, v0d_power_closure)
from aphelion.sim.vehicles.locomotion import TERRAIN, p_ground_pa


def test_chassis_grid_and_caps_exact():
    """10 §1.0: VC-1 2×2/0.8 t · VC-2 4×2/3 t · VC-3 6×3/12 t ·
    VC-4 10×4/60 t · VC-5 16×5/300 t."""
    assert CHASSIS["VC-1"].grid == (2, 2)
    assert CHASSIS["VC-1"].gross_cap_t == pytest.approx(0.8)
    assert CHASSIS["VC-2"].grid == (4, 2)
    assert CHASSIS["VC-2"].gross_cap_t == pytest.approx(3.0)
    assert CHASSIS["VC-3"].grid == (6, 3)
    assert CHASSIS["VC-3"].gross_cap_t == pytest.approx(12.0)
    assert CHASSIS["VC-4"].grid == (10, 4)
    assert CHASSIS["VC-4"].gross_cap_t == pytest.approx(60.0)
    assert CHASSIS["VC-5"].grid == (16, 5)
    assert CHASSIS["VC-5"].gross_cap_t == pytest.approx(300.0)
    assert [c.label for c in CHASSIS.values()] == \
        ["cart", "light", "medium", "heavy", "platform"]


def test_integrated_cutoffs():
    """10 §1.0: sub-100 kg integrated (99 yes, 100 no); zero-g drones
    to 300 kg (UTL-CDRONE 250 kg yes)."""
    assert is_integrated(99.0)
    assert not is_integrated(100.0)
    assert is_integrated(250.0, zero_g_drone=True)      # UTL-CDRONE 0.25 t
    assert not is_integrated(301.0, zero_g_drone=True)


def test_v0a_clearance_and_rock_warn():
    """V-0a: lowest non-locomotion cell ≥ set clearance; rock_abundance
    only warns, never refuses."""
    assert v0a_clearance(0.35, 0.30)        # WHL-RIGID clearance 0.30 m
    assert v0a_clearance(0.30, 0.30)        # boundary passes
    assert not v0a_clearance(0.25, 0.30)
    assert v0a_rock_warn(0.25)
    assert not v0a_rock_warn(0.02)


def test_v0b_tip_over_and_tilt_warn():
    """V-0b: track 2.0 m / h_COM 1.0 m → θ_tip = atan(1.0) = 45°;
    passes 2σ for σ 20° (40°), fails σ 25° (50°); hazard row 1 tilt
    icon at θ_tip − 5° = 40°."""
    theta = v0b_theta_tip_rad(2.0, 1.0)
    assert theta == pytest.approx(math.radians(45.0))
    assert v0b_ok(theta, math.radians(20.0))
    assert not v0b_ok(theta, math.radians(25.0))
    assert tilt_warn_rad(theta) == pytest.approx(math.radians(40.0))


def test_v0b_h_com_recompute_on_cargo_load():
    """V-0b rider: h_COM recomputed live on cargo load — high cargo
    raises h_COM and shrinks θ_tip."""
    h = h_com_loaded(1_000.0, 1.0, 1_000.0, 2.0)
    assert h == pytest.approx(1.5)
    theta_loaded = v0b_theta_tip_rad(2.0, h)
    assert theta_loaded < v0b_theta_tip_rad(2.0, 1.0)
    # crane tip check = V-0b with the load at the boom tip (§1.4)
    assert theta_loaded == pytest.approx(math.atan(1.0 / 1.5))


def test_v0c_float_mirrors_marine():
    """V-0c: 2.0 t skiff on 4 m³ floats in ρ_sea 550 (limit 2,090 kg);
    2.2 t does not. chassis keeps a local mirror of marine.floats()."""
    assert v0c_ok(2_000.0, 4.0, 550.0)
    assert not v0c_ok(2_200.0, 4.0, 550.0)
    assert FLOAT_MARGIN == pytest.approx(marine.FLOAT_MARGIN)
    assert v0c_ok(2_000.0, 4.0, 550.0) == marine.floats(2_000.0, 4.0, 550.0)
    assert v0c_ok(2_200.0, 4.0, 550.0) == marine.floats(2_200.0, 4.0, 550.0)


def test_v0d_delegates_to_powerplant():
    """V-0d is shared law owned by powerplant.power_closure — chassis
    imports it, never duplicates it."""
    assert v0d_power_closure is powerplant.power_closure
    ok, margin = v0d_power_closure(19_000.0, 2_000.0, 25_000.0)
    assert ok and margin == pytest.approx(4_000.0)


def test_v1a_science_rover_on_rigid_wheels():
    """V-1a (a): 1 t rover ÷6 WHL-RIGID (0.04 m²/set), Mars g 3.71 →
    ~15.5 kPa: fails DUNE bearing 7 by design, clears duricrust 80."""
    p_kpa = p_ground_pa(1_000.0, 3.71, 6, 0.04) / 1_000.0
    assert p_kpa == pytest.approx(15.5, abs=1.5)
    assert p_kpa > TERRAIN["dune"].bearing_kpa          # Spirit's killer
    assert p_kpa < TERRAIN["duricrust"].bearing_kpa


def test_v1a_lrv_on_mesh_wheels():
    """V-1a (b): LRV 670 kg gross ÷4 WHL-MESH (0.05 m²), Moon g 1.62 →
    ~5.4 kPa ≪ regolith 25."""
    p_kpa = p_ground_pa(670.0, 1.62, 4, 0.05) / 1_000.0
    assert p_kpa == pytest.approx(5.4, abs=1.5)
    assert p_kpa < TERRAIN["regolith"].bearing_kpa


def test_v1a_hauler_niti_vs_tracks():
    """V-1a (c): 18 t hauler ÷6 WHL-NITI (0.06 m²), Mars → ~185 kPa
    exceeds duricrust 80; mount 4 TRK-STD (0.50 m²) → ~33 kPa ok."""
    p_niti_kpa = p_ground_pa(18_000.0, 3.71, 6, 0.06) / 1_000.0
    assert p_niti_kpa == pytest.approx(185.0, abs=1.5)
    assert p_niti_kpa > TERRAIN["duricrust"].bearing_kpa
    p_trk_kpa = p_ground_pa(18_000.0, 3.71, 4, 0.50) / 1_000.0
    assert p_trk_kpa == pytest.approx(33.0, abs=1.5)
    assert p_trk_kpa < TERRAIN["duricrust"].bearing_kpa


def test_v1a_crawler_on_tracks():
    """V-1a (d): RVR-CRAWL 60 t ÷12 TRK-STD (0.50 m²), Mercury g 3.70
    → ~37 kPa vs compacted corridor 150 ok."""
    p_kpa = p_ground_pa(60_000.0, 3.70, 12, 0.50) / 1_000.0
    assert p_kpa == pytest.approx(37.0, abs=1.5)
    assert p_kpa < TERRAIN["compacted"].bearing_kpa


def test_overhaul_bill_haul40():
    """10 §1.0 cost note (the ONLY cost rule 10 owns): 22 t RVR-HAUL40
    overhaul = 0.66 t MachineParts + 0.11 t Electronics."""
    bill = overhaul_bill_t(22.0)
    assert bill["MachineParts"] == pytest.approx(0.66)
    assert bill["Electronics"] == pytest.approx(0.11)
    assert set(bill) == {"MachineParts", "Electronics"}


def test_crane_lift_law():
    """§1.4 UTL-CRANE: m_max = 12 t·(1.62/g) — Moon 12 t, Mars 5.24 t."""
    assert crane_lift_t(1.62) == pytest.approx(12.0)
    assert crane_lift_t(3.71) == pytest.approx(5.24, abs=0.01)
