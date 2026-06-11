"""Dose v2 (08 §4.2): two-channel shielding, two accumulators (career mSv
vs acute mGy), ARS bands, REID, and the 600 mSv NASA anchor."""

import pytest

from aphelion.sim.habitat.dose import (
    ARS_BANDS, CAREER_CAUTION_MSV, CAREER_LIMIT_MSV, CrewDose, ars_band,
    f_gcr, f_spe, quality_factor, reid_fraction)


def test_career_anchor_is_600():
    assert CAREER_LIMIT_MSV == 600.0
    assert CAREER_CAUTION_MSV == 400.0
    d = CrewDose(450.0)
    assert d.caution and not d.over_limit
    assert CrewDose(601.0).over_limit


def test_storm_shelter_doctrine():
    """σ=35 water walls: GCR only halved, SPE nearly eliminated — thin
    hull for cruise, thick shelter for storms (08 worked example)."""
    assert f_gcr(35.0) == pytest.approx(0.52, abs=0.01)
    assert f_spe(35.0) == pytest.approx(0.054, abs=0.005)
    assert f_gcr(1.0) == pytest.approx(0.98, abs=0.01)
    assert f_spe(1.0) == pytest.approx(0.92, abs=0.01)


def test_deep_floor_decay_a3():
    """30 m of belt rock ≈ 4,500 g/cm² → f_GCR ≈ 0.009 (Earth-class)."""
    assert f_gcr(4_500.0) == pytest.approx(0.009, abs=0.002)


def test_quality_factor_split():
    """GCR (Q≈3) drives career ~3× harder than acute; SPE adds equally."""
    assert quality_factor("core:moon") == 3.0
    assert quality_factor("core:europa") == 1.0
    d = CrewDose()
    d.accrue("deep_space", days=10.0)            # 18 mSv effective GCR
    assert d.accumulated_msv == pytest.approx(18.0)
    assert d.acute_mgy() == pytest.approx(6.0)   # absorbed = /Q


def test_acute_window_rolls_24h():
    d = CrewDose()
    t0 = 100.0 * 86_400.0
    d.accrue_event_msv(300.0, t=t0)              # storm lump, Q=1
    assert d.acute_mgy(t0) == pytest.approx(300.0)
    assert ars_band(d.acute_mgy(t0))[0] == "prodromal"
    # 36 h later the window has rolled clear
    assert d.acute_mgy(t0 + 1.5 * 86_400.0) == pytest.approx(0.0)
    assert d.ars(t0 + 1.5 * 86_400.0) is None
    # career dose, by contrast, is forever
    assert d.accumulated_msv == pytest.approx(300.0)


def test_ars_band_ladder():
    assert ars_band(100.0) is None
    assert ars_band(600.0)[0] == "prodromal"
    assert ars_band(1_500.0)[0] == "mild"
    name, pen, death_p, _rec = ars_band(2_500.0)
    assert name == "severe" and pen == 1.0 and death_p > 0.0
    assert ars_band(5_000.0)[0] == "ld50"
    assert ars_band(7_000.0)[0] == "lethal"
    # bands are sorted descending by threshold
    assert [b[0] for b in ARS_BANDS] == sorted(
        (b[0] for b in ARS_BANDS), reverse=True)


def test_reid_roll_basis():
    """Each +100 mSv ≈ +0.5% lifetime fatal-cancer probability."""
    assert reid_fraction(600.0) == pytest.approx(0.03)
    assert CrewDose(200.0).reid() == pytest.approx(0.01)


def test_storm_behind_shelter_is_survivable():
    """A capped worst-case 2,000 mSv SPE behind a σ=35 shelter leaves
    ~108 mGy — below the 250 prodromal threshold. Shelters work."""
    d = CrewDose()
    got = d.accrue_event_msv(2_000.0, areal_g_cm2=35.0, t=0.0)
    assert got == pytest.approx(108.0, abs=10.0)
    assert d.ars(0.0) is None
