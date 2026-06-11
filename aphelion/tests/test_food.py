"""Food & agriculture (08 §3): starvation ledger, crop cycles and the
establishment lag, fresh-store cap + dry overflow, closure anchors."""

import pytest

from aphelion.sim.habitat.food import (
    AREA_FULL_DIET_M2, BODY_RESERVE_KCAL, CROPS, CrewEnergy, Greenhouse,
    RATIONS, full_diet_layout)


def test_starvation_clock_is_30_to_45_days():
    """Zero intake at nominal activity: dead in ~36 days; heavy labor
    starves faster (08 §3.2)."""
    c = CrewEnergy()
    days = 0
    while not c.dead:
        c.step_day(0.0, activity=1.0)
        days += 1
    assert 30 <= days <= 45
    hard = CrewEnergy()
    days_hard = 0
    while not hard.dead:
        hard.step_day(0.0, activity=1.6)
        days_hard += 1
    assert days_hard < days
    # eating refills the reserve, capped at the body maximum
    fed = CrewEnergy(50_000.0)
    fed.step_day(6_000.0)
    assert fed.reserve == pytest.approx(53_500.0)
    fed.step_day(1e9)
    assert fed.reserve == BODY_RESERVE_KCAL


def test_establishment_lag_then_yield():
    """A fresh potato bed feeds nobody for 95 days, then delivers the
    canon 250 kcal/m²/day (08 §3.3/3.4)."""
    g = Greenhouse(20.0)
    assert g.plant("potato", 20.0)
    assert not g.plant("potato", 1.0)        # area is real
    for _ in range(94):
        out = g.step_day(crew_n=1)
        assert out["kcal"] == 0.0
        assert out["power_kw"] == pytest.approx(20.0 * 0.28)
    out = g.step_day(crew_n=1)
    assert out["kcal"] == pytest.approx(20.0 * 250.0)
    assert out["ammonia_kg"] == pytest.approx(20 * 250 / 4_000 * 0.03)
    # blight restarts the whole cycle
    g.blight("potato")
    assert g.step_day(crew_n=1)["kcal"] == 0.0


def test_fresh_cap_overflow_dries_to_rations():
    g = Greenhouse(40.0)
    g.plant("potato", 40.0)
    g.beds["potato"][1] = 95.0                # mature
    for _ in range(30):
        g.step_day(crew_n=1)
    # 10,000 kcal/day against a 14-day × 2,500 cap: overflow banked dry
    assert g.fresh_kcal == pytest.approx(14 * 2_500.0)
    assert g.dry_overflow_kg > 60.0
    got = g.eat_fresh(3_000.0)
    assert got == 3_000.0
    assert g.take_dry_kg() > 60.0
    assert g.take_dry_kg() == 0.0


def test_full_diet_layout_hits_canon_margin():
    """40 m²/crew template ≈ 6,300 kcal/day steady ≈ 2.5× requirement;
    eta_food caps at 0.95 (never 1.0)."""
    lay = full_diet_layout(1)
    assert sum(lay.values()) == pytest.approx(AREA_FULL_DIET_M2)
    g = Greenhouse(AREA_FULL_DIET_M2)
    for crop, a in lay.items():
        assert g.plant(crop, a)
        g.beds[crop][1] = CROPS[crop][1]      # mature everything
    steady = g.step_day(crew_n=1)["kcal"]
    assert steady == pytest.approx(6_295.0, rel=0.05)
    assert g.eta_food(1) == 0.95
    # agronomist bonus is real but bounded
    more = Greenhouse(AREA_FULL_DIET_M2)
    for crop, a in lay.items():
        more.plant(crop, a)
        more.beds[crop][1] = CROPS[crop][1]
    assert more.step_day(1, agronomist_level=3)["kcal"] == pytest.approx(
        steady * 1.24, rel=0.01)


def test_ration_forms_canon():
    assert RATIONS["FD-DEHY"]["kg_day"] == 0.62
    assert RATIONS["FD-DEHY"]["prep_water"] == 1.2
    assert RATIONS["FD-PKG"]["kg_day"] == 1.83
    assert RATIONS["FD-EMRG"]["morale"] < 0
    assert RATIONS["FD-FRESH"]["morale"] == 12.0


def test_greenhouse_persistence_roundtrip():
    g = Greenhouse(30.0)
    g.plant("lettuce", 10.0)
    g.step_day(2)
    d = g.to_dict()
    g2 = Greenhouse.from_dict(d)
    assert g2.beds["lettuce"][0] == 10.0
    assert g2.area_m2 == 30.0
