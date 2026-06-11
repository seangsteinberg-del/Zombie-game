"""Solar system v2 (03): sector/region/anomaly content integrity,
land-anywhere site synthesis, radiation field anchors (DECISIONS A4),
the SPE storm schedule, Mars climate (C24), conjunction geometry and
survey awards."""

import math
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pytest

from aphelion.content.loader import default_data_dir, load_packs
from aphelion.content.validate import validate
from aphelion.game.sectors import (
    BODY_OPS, EDL_SIGMA_KM, LEGACY_SITE_SECTOR, landable, sector_site,
    sectors_of)
from aphelion.sim.environment.mars_climate import (
    MarsWeather, f_climate, f_dust, ls_deg, p_site_factor,
    soiling_rate_per_sol)
from aphelion.sim.environment.space_env import (
    SpeSchedule, T_SOLAR_MAX, comet_activity, conjunction_blackout,
    earth_belt_msv_day, f_cycle, jupiter_belt_msv_day, R_E_KM, R_J_KM,
    saturn_belt_msv_day, spe_rate_per_year)
from aphelion.sim.research import ResearchState

YEAR = 365.25 * 86_400.0


@pytest.fixture(scope="module")
def db():
    d = load_packs(default_data_dir())
    validate(d)
    return d


# ---- content integrity (03 §1.7-1.8, §2) -------------------------------------

def test_sector_pack_shape(db):
    sectors = db.by_type("sectors")
    regions = db.by_type("regions")
    anomalies = db.by_type("anomalies")
    assert len(sectors) >= 176                  # the curated canon target
    assert len(regions) == 52
    assert len(anomalies) == 50
    # every operable body carries sectors; counts match the bible
    counts = {b: len(sectors_of(db, b)) for b in BODY_OPS}
    assert counts["core:mercury"] == 10
    assert counts["core:moon"] == 14
    assert counts["core:mars"] == 18
    assert counts["core:titan"] == 12
    assert counts["core:venus"] == 12           # 8 surface + 4 cloud bands
    assert all(n >= 1 for n in counts.values())


def test_region_exoticism_canon(db):
    regions = {r["code"]: r for r in db.by_type("regions").values()}
    assert regions["EUR-OCEAN"]["x"] == 14.0    # the cap
    assert regions["TIT-SEAFLOOR"]["x"] == 14.0
    assert regions["MOO-FARPOLE"]["x"] == 4.0
    assert regions["ENC-SPT"]["x"] == 12.0
    assert regions["EAR-ORB-LEO"]["x"] == 1.0
    assert max(r["x"] for r in regions.values()) == 14.0


def test_anomaly_catalog(db):
    anomalies = db.by_type("anomalies")
    a34 = anomalies["core:an34"]                # Europa ocean jackpot
    assert a34["gb"] == 200.0
    a01 = anomalies["core:an01"]                # Apollo 11
    assert a01["heritage"] is True
    placed = [a for a in anomalies.values() if a["sector"] != "orbit"]
    assert len(placed) >= 40                    # most are surface-placed


def test_legacy_sites_map_to_sectors(db):
    sectors = db.by_type("sectors")
    for sid, sec_id in LEGACY_SITE_SECTOR.items():
        assert sec_id in sectors, (sid, sec_id)


# ---- land anywhere (S-7) -------------------------------------------------------

def test_every_landable_sector_synthesizes_a_site(db):
    n = 0
    for sec_id, sec in db.by_type("sectors").items():
        if not landable(sec) or sec["body"] not in BODY_OPS:
            continue
        site = sector_site(db, sec_id)
        assert site["ascent_dv"] > 0.0
        assert site["land_dv"] > 0.0
        assert site["solar"] >= 0.0
        assert site["kind"]
        assert site["x"] >= 1.0
        assert site["edl_sigma_km"] > 0.0
        n += 1
    assert n >= 150                             # the open solar system


def test_site_solar_rules(db):
    # PSR: dark. PEL: 0.85 rim light. Venus cloud: band f_atm, needs gondola
    cabeus = sector_site(db, "core:sec_moon_11")
    assert cabeus["solar"] == 0.0
    shackleton = sector_site(db, "core:sec_moon_10")
    assert shackleton["solar"] == pytest.approx(0.85, abs=0.01)
    assert shackleton["day_s"] is None
    havoc = sector_site(db, "core:sec_venus_10")
    assert havoc["requires_part"] == "core:gondola_havoc"
    assert havoc["aero"] is True
    assert havoc["solar"] == pytest.approx(0.45 / 0.723 ** 2, rel=0.01)
    # Titan is honest: f_atm 0.10 at 9.6 AU is nearly nothing
    titan = sector_site(db, "core:sec_titan_04")
    assert titan["solar"] < 0.02


def test_dock_mode_class_a(db):
    bennu = sector_site(db, "core:sec_bennu_01")
    assert bennu["landing_class"] == "A"
    assert bennu["land_dv"] <= 10.0
    assert EDL_SIGMA_KM["A"] < EDL_SIGMA_KM["C"] < EDL_SIGMA_KM["D"]


def test_gas_giants_not_landable(db):
    for sec in sectors_of(db, "core:jupiter"):
        assert not landable(sec)


# ---- radiation fields (S-8, DECISIONS A4 anchors EXACT) -------------------------

def test_jupiter_belt_anchors_exact():
    assert jupiter_belt_msv_day(5.9 * R_J_KM) == pytest.approx(36_000.0)
    assert jupiter_belt_msv_day(9.4 * R_J_KM) == pytest.approx(5_400.0, rel=1e-3)
    assert jupiter_belt_msv_day(15.0 * R_J_KM) == pytest.approx(160.0, rel=1e-3)
    assert jupiter_belt_msv_day(31.0 * R_J_KM) == 0.0
    assert jupiter_belt_msv_day(3.0 * R_J_KM) == 36_000.0   # Io clamp


def test_earth_belt_piecewise():
    assert earth_belt_msv_day(1.0 * R_E_KM) == 0.0
    assert earth_belt_msv_day(1.6 * R_E_KM) == pytest.approx(150.0)
    assert earth_belt_msv_day(2.5 * R_E_KM) == pytest.approx(10.0)
    assert earth_belt_msv_day(4.5 * R_E_KM) == pytest.approx(50.0)
    assert earth_belt_msv_day(9.0 * R_E_KM) == 0.0


def test_saturn_belt_and_titan_outside():
    assert saturn_belt_msv_day(7.9 * 58_232.0) == 1.0
    assert saturn_belt_msv_day(21.0 * 58_232.0) == 0.0      # Titan orbit


def test_solar_cycle_clamp_and_phase():
    for t in (0.0, 3.0 * YEAR, T_SOLAR_MAX, 20.0 * YEAR):
        assert 0.65 <= f_cycle(t) <= 1.35
    assert f_cycle(T_SOLAR_MAX) == pytest.approx(0.65)      # max = quiet GCR
    assert f_cycle(T_SOLAR_MAX + 5.5 * YEAR) == pytest.approx(1.35)
    assert spe_rate_per_year(T_SOLAR_MAX) == pytest.approx(4.0)
    assert spe_rate_per_year(T_SOLAR_MAX + 5.5 * YEAR) == pytest.approx(0.5)


def test_spe_schedule_deterministic_and_capped():
    a, b = SpeSchedule(1234), SpeSchedule(1234)
    evs_a = a._events_for_year(8) + a._events_for_year(9)
    evs_b = b._events_for_year(8) + b._events_for_year(9)
    assert evs_a == evs_b
    other = SpeSchedule(99)._events_for_year(8)
    assert other != evs_a or other == []        # different seed differs
    for t0, dur, dose in evs_a:
        assert 6 * 3_600.0 <= dur <= 48 * 3_600.0
        assert dose <= 2_000.0                  # S-8b cap
    # warnings precede onsets by the 45-min window
    if evs_a:
        t0 = evs_a[0][0]
        assert a.warning(t0 - 10 * 60.0) is not None
        assert a.active(t0 + 1.0) is not None


def test_conjunction_superior_only():
    # observer at (1,0) AU, sun at origin, target behind the sun
    assert conjunction_blackout((1.0, 0.0), (0.0, 0.0), (-1.52, 0.005))
    # inferior conjunction (target between observer and sun): never blocks
    assert not conjunction_blackout((1.0, 0.0), (0.0, 0.0), (0.5, 0.001))
    # wide separation: no blackout
    assert not conjunction_blackout((1.0, 0.0), (0.0, 0.0), (0.0, 1.52))


def test_comet_activity_clamp():
    assert comet_activity(3.0) == pytest.approx(0.0)
    assert comet_activity(1.0) == 8.0                      # clamped
    assert 0.0 < comet_activity(2.0) < 8.0


# ---- Mars climate (S-9, DECISIONS C24) ------------------------------------------

def test_mars_climate_clamps_and_phase():
    for t in (0.0, 0.3 * YEAR, 2.0 * YEAR, 11.7 * YEAR):
        assert 0.0 <= ls_deg(t) < 360.0
        assert 0.50 <= f_climate(50_000.0, t) <= 1.50      # the C24 band
        assert 0.85 <= p_site_factor(t) <= 1.15
    assert f_dust(0.0) == 1.0
    assert f_dust(9.0) == pytest.approx(0.04)              # storm floor
    assert f_dust(4.0, olympus=True) > f_dust(4.0)         # AN-14 perk
    assert soiling_rate_per_sol(True) == 10 * soiling_rate_per_sol(False)


def test_mars_weather_deterministic():
    a, b = MarsWeather(777), MarsWeather(777)
    ts = [i * 0.21 * YEAR for i in range(40)]
    assert [a.tau(t) for t in ts] == [b.tau(t) for t in ts]
    assert [a.global_storm_active(t) for t in ts] \
        == [b.global_storm_active(t) for t in ts]
    # tau never below the seasonal baseline
    for t in ts:
        assert a.tau(t) >= 0.3 - 1e-9


def test_mars_global_storm_eventually_happens():
    wx = MarsWeather(5)
    hit = any(wx.global_storm_active(t)
              for t in [i * 30 * 86_400.0 for i in range(12 * 20)])
    assert hit                                  # p=0.33/Mars-year over ~30 y


# ---- survey awards (S-10 / 11 §3.1) ---------------------------------------------

def test_survey_awards_one_shot():
    rs = ResearchState()
    assert rs.award_survey("orbital", "MAR-ORB", 5.0) == 75.0   # 15·X
    assert rs.award_survey("orbital", "MAR-ORB", 5.0) == 0.0
    assert rs.award_survey("ground", "MAR-SURF", 5.0) == 50.0   # 10·X
    assert rs.science == 125.0
