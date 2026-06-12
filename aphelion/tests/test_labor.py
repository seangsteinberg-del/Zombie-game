"""Automation ladder (05 §2): the F-2 light-lag table pinned, the EVA
cost rule, crew-for-robot substitution, the A3 crossover, and the χ
closure checks."""

import pytest

from aphelion.sim.industry.labor import (
    ETA_EVA, ROBOTS, TELEOP_REFUSE_ETA, a3_output_h_day, chi_import_t_yr,
    eva_sortie_cost, f_labor, supervision_crew_h, teleop_eta,
    teleop_output_h_day)


def test_f2_lightlag_table():
    """§2: same-site ≈1.0; Earth→Moon 0.91; Earth→Mars best 0.063,
    worst 0.009 — both refused for standing orders."""
    assert teleop_eta(0.1) > 0.99
    assert teleop_eta(2.6) == pytest.approx(0.906, abs=0.005)
    eta_mars = teleop_eta(6.2 * 60.0)
    assert eta_mars == pytest.approx(0.063, abs=0.002)
    assert teleop_eta(44.6 * 60.0) == pytest.approx(0.009, abs=0.001)
    assert eta_mars < TELEOP_REFUSE_ETA


def test_a3_crossover_beats_mars_teleop():
    """Mars-from-Earth teleop ≈ 0.5 robot-h/day vs A3 = 8.4."""
    assert teleop_output_h_day(6.2 * 60.0) == pytest.approx(0.5, abs=0.05)
    assert a3_output_h_day() == pytest.approx(8.4)


def test_eva_cost_rule():
    c = eva_sortie_cost()
    assert c["crew_h"] == 25.0 and c["productive_h"] == 13.0
    assert ETA_EVA == pytest.approx(0.52)
    assert c["Oxygen_kg"] == pytest.approx(1.18)
    assert c["Water_kg"] == pytest.approx(5.2)


def test_f_labor_substitution_and_floor():
    # fully staffed
    assert f_labor(4.0, 16.0, 4.0, 16.0) == 1.0
    # robots can't cover crew: zero crew = zero output on a crew entry
    assert f_labor(4.0, 16.0, 0.0, 99.0) == 0.0
    # spare crew substitutes robot-h 1:1
    assert f_labor(4.0, 16.0, 12.0, 8.0) == 1.0
    # half the robots, no spare crew
    assert f_labor(4.0, 16.0, 4.0, 8.0) == 0.5
    # wafer-fab floor: min 10% of total hours must be crew
    assert f_labor(2_000.0, 20_000.0, 1_100.0, 20_900.0,
                   min_crew_frac=0.10) == pytest.approx(0.5)
    # A1 supervision charge
    assert supervision_crew_h(16.0, "A1") == pytest.approx(1.6)
    assert supervision_crew_h(16.0, "A2") == 0.0


def test_chi_closure_checks():
    """§2 checks: χ=0.90, 120 t dusty complex → 0.48 t/yr; χ=0.98,
    250 t seed → 0.2 t/yr."""
    assert chi_import_t_yr(0.90, 120.0, 0.04) == pytest.approx(0.48)
    assert chi_import_t_yr(0.98, 250.0, 0.04) == pytest.approx(0.2)
    assert len(ROBOTS) == 5
