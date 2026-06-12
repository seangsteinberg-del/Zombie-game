"""Spares economy (05 §3.4): F-7 wear, F-8 hazard, F-9 budget anchors,
the §4.6 table, cannibalization, and the blueprint laws F-10/11/12."""

import numpy as np
import pytest

from aphelion.sim.industry.chains import FAB_MODULES
from aphelion.sim.industry.wear import (
    MAINT, MAINT_OF_MODULE, after_pm, cannibalize, death_spiral,
    e_design_h, fail_rate_per_h, fleet_spares_mult, labor_mult,
    m_spares_t_yr, roll_failure, wear_dc)


def test_f7_wear_and_pm():
    # at u=1 a module spends its whole L_wear in exactly L_wear hours
    assert wear_dc(1.0, 8_000.0, 8_000.0) == pytest.approx(1.0)
    assert wear_dc(0.5, 1_000.0, 8_000.0) == pytest.approx(0.0625)
    assert wear_dc(1.0, 100.0, 8_000.0, dust=True) == pytest.approx(
        2.0 * 100.0 / 8_000.0)
    assert after_pm(0.9) == 1.0 and after_pm(0.5) == 0.75


def test_f8_hazard_law():
    assert fail_rate_per_h(2_000.0, 1.0) == pytest.approx(1 / 2_000.0)
    assert fail_rate_per_h(2_000.0, 0.5) == pytest.approx(1.5 / 2_000.0)
    assert fail_rate_per_h(2_000.0, 1.0, dust=True) == pytest.approx(
        1 / 1_200.0)
    assert fail_rate_per_h(2_000.0, 1.0, commissioned=False) \
        == pytest.approx(3 / 2_000.0)
    rng = np.random.default_rng(7)
    rolls = [roll_failure(rng, 10.0, MAINT["machine_shop"].split)
             for _ in range(400)]
    minors = sum(1 for r in rolls if r["severity"] == "minor")
    assert 360 <= minors <= 396                  # ~95%
    major = next(r for r in rolls if r["severity"] == "major")
    assert sum(major["parts"].values()) == pytest.approx(0.1)  # 1% of 10 t
    assert 24.0 <= major["labor_h"] <= 40.0


def test_f9_budget_and_table():
    assert m_spares_t_yr(120.0, "dusty") == pytest.approx(4.8)
    assert m_spares_t_yr(100.0, "orbital") == pytest.approx(2.0)
    assert m_spares_t_yr(100.0, "clean") == pytest.approx(3.0)
    assert MAINT["wafer_fab"].mtbf_h == 400          # deliberate
    assert len(MAINT) == 17
    # every §1.6 fab module except the bundled complexes maps to a row
    for mid in FAB_MODULES:
        if mid in ("fab_auto_complex", "fab_replicator_seed"):
            continue                                 # pro-rata bundles
        assert MAINT_OF_MODULE[mid] in MAINT
    for row in MAINT.values():
        assert sum(row.split) == pytest.approx(1.0)


def test_spiral_and_cannibalization():
    assert death_spiral(5.0, 1.0, 2.0, 1.0)
    assert not death_spiral(3.9, 1.0, 2.0, 1.0)
    parts, c_after = cannibalize(20.0, 0.9, MAINT["machine_shop"].split)
    assert sum(parts.values()) == pytest.approx(0.2)
    assert c_after == pytest.approx(0.6)


def test_blueprint_laws():
    """F-10: 100 t ship ≈ 630 eng-h. F-11: 85% Wright curve, floor 0.4.
    F-12: 5 identical hulls pool spares to √5 ≈ 2.24×; one-offs pay 5×."""
    assert e_design_h(100.0) == pytest.approx(634.0, abs=5.0)
    assert labor_mult(2) == pytest.approx(0.850, abs=0.003)
    assert labor_mult(1_000) == 0.4
    assert fleet_spares_mult(5, 1.0) == pytest.approx(2.236, abs=0.01)
    assert fleet_spares_mult(5, 0.0) == pytest.approx(5.0)
