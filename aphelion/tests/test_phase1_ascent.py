"""PHASE 1 ascent acceptance (01 §3.10, canon owner; 13 §4.7 row): a
TWR-1.3 liftoff, 2-stage methalox vehicle reaches LEO-300 for 8,900-9,300
m/s integrated dv, gravity loss 1,100-1,500, drag 50-150, steering 100-400,
and the loss identity closes to < 50 m/s. Plus vessel-model unit tests.
"""

import math

import pytest

from aphelion.content.loader import default_data_dir, load_packs
from aphelion.content.validate import validate
from aphelion.core.units import G0
from aphelion.sim.flight.ascent import AscentParams, fly_ascent
from aphelion.sim.vessels.vessel import PartRow, Vessel

MU_EARTH = 3.986_004_418e14
R_EARTH = 6.371e6
EARTH_DAY = 86_164.1


@pytest.fixture(scope="module")
def db():
    d = load_packs(default_data_dir())
    validate(d)
    return d


def build_two_stage(db) -> Vessel:
    """S1: 3x M-733 + XL tank (sea-level TWR ~1.76, throttle-capped to 1.3
    by guidance per the acceptance config). S2: MV-815 + L tank + 2 t
    payload (upper-stage initial acceleration ~2 g, Centaur-class)."""
    rows = [
        Vessel.fueled_row(db, "core:engine_m733"),     # 0
        Vessel.fueled_row(db, "core:engine_m733"),     # 1
        Vessel.fueled_row(db, "core:tank_ml_xl"),      # 2
        Vessel.fueled_row(db, "core:engine_mv815"),    # 3
        Vessel.fueled_row(db, "core:tank_ml_m"),       # 4
        Vessel.fueled_row(db, "core:payload_2t"),      # 5
        Vessel.fueled_row(db, "core:payload_2t"),      # 6
    ]
    return Vessel(db, rows, stage_plan=[[0, 1, 2], [3, 4, 5, 6]], cd_a_m2=3.2)


# ---- vessel model -----------------------------------------------------------

def test_vessel_masses(db):
    v = build_two_stage(db)
    # dry: 2*0.75 + 4.8 + 0.9 + 0.72 + 2*2.0 = 11.92 t; prop: 80 + 12 = 92 t
    assert v.dry_mass_kg() == pytest.approx(11_920.0)
    assert v.total_mass_kg() == pytest.approx(103_920.0)
    assert v.active_propellant_kg() == pytest.approx(80_000.0)


def test_vessel_stage_stats(db):
    v = build_two_stage(db)
    stats = v.stage_stats()
    assert len(stats) == 2
    # stage 1: ve*ln(m0/m1) with vac isp 329
    m0 = 103_920.0
    dv1 = 329.0 * G0 * math.log(m0 / (m0 - 80_000.0))
    assert stats[0]["dv_vac"] == pytest.approx(dv1, rel=1e-9)
    # stage 2 alone: 17.62 t wet, 5.62 t dry
    dv2 = 367.0 * G0 * math.log(17_620.0 / 5_620.0)
    assert stats[1]["dv_vac"] == pytest.approx(dv2, rel=1e-9)
    # capacity exceeds the nominal flight's ~8,763 m/s spend (thin but real
    # ~90 m/s reserve — the acceptance flight proves closure)
    assert dv1 + dv2 > 8_800.0


def test_vessel_staging_drops_rows(db):
    v = build_two_stage(db)
    v.stage()
    assert len(v.rows) == 4
    assert [r.part_id for r in v.rows] == [
        "core:engine_mv815", "core:tank_ml_m", "core:payload_2t",
        "core:payload_2t"]
    assert v.active_propellant_kg() == pytest.approx(12_000.0)


def test_drain_propellant(db):
    v = build_two_stage(db)
    got = v.drain_propellant(1_000.0)
    assert got == pytest.approx(1_000.0)
    assert v.active_propellant_kg() == pytest.approx(79_000.0)


# ---- THE ascent acceptance --------------------------------------------------

@pytest.fixture(scope="module")
def flight(db):
    vessel = build_two_stage(db)
    return fly_ascent(vessel, "core:earth", MU_EARTH, R_EARTH, EARTH_DAY,
                      AscentParams())


def test_ascent_reaches_leo300(flight):
    assert flight.reached_orbit, "\n".join(flight.log)
    assert flight.periapsis_m > 270e3
    assert flight.apoapsis_m == pytest.approx(300e3, abs=30e3)


def test_ascent_integrated_dv_in_canon_band(flight):
    # 01 §3.10 band (post Phase-1 erratum): 8,700-9,300 m/s integrated
    assert 8_700.0 <= flight.dv_integrated <= 9_300.0, (
        f"integrated {flight.dv_integrated:.0f} m/s; "
        f"grav {flight.dv_gravity:.0f}, drag {flight.dv_drag:.0f}, "
        f"steer {flight.dv_steering:.0f}\n" + "\n".join(flight.log))


def test_ascent_loss_components_in_band(flight):
    assert 1_100.0 <= flight.dv_gravity <= 1_500.0
    assert 50.0 <= flight.dv_drag <= 150.0
    # 2D-idealized forced-profile guidance (01 §3.10 erratum): <= 100 m/s
    assert flight.dv_steering <= 100.0


def test_ascent_loss_identity_closes(flight):
    assert abs(flight.identity_residual) < 50.0
