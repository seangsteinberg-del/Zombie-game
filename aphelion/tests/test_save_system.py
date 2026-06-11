"""Save system v1 tests (13 §3.15): exact round-trip, divergence-free
resume (load + advance == never-saved + advance), version gate, and golden
save #1 — the Phase 2 DoD fixture that every future schema must keep
loading (the campaign's history is the test corpus).
"""

import math
from pathlib import Path

import pytest

from aphelion.content.loader import default_data_dir, load_packs
from aphelion.content.validate import validate
from aphelion.core.rng import RngRegistry
from aphelion.sim.habitat.lsc import DAY, build_iss_grade_hab
from aphelion.sim.orbits.kepler import Elements, elements_to_state
from aphelion.sim.vessels.vessel import Vessel
from aphelion.save.serialize import (
    SCHEMA_VERSION,
    build_save,
    elements_from_dict,
    elements_to_dict,
    ledger_from_dict,
    ledger_to_dict,
    read_save,
    vessel_from_dict,
    vessel_to_dict,
    write_save,
)

GOLDEN = Path(__file__).parent / "golden" / "golden1.sav"


@pytest.fixture(scope="module")
def db():
    d = load_packs(default_data_dir())
    validate(d)
    return d


def _scenario(db):
    """Golden scenario: lander parked in LLO + a crewed lunar-night hab."""
    el = Elements(mu=4.9028e12, alpha=1.0 / 1.8374e6, e=0.0007,
                  varpi=1.1, tau=-321.5, s=1.0)
    lander = Vessel(db, [
        Vessel.fueled_row(db, "core:engine_ml111"),
        Vessel.fueled_row(db, "core:tank_ml_s"),
        Vessel.fueled_row(db, "core:payload_2t"),
    ], stage_plan=[[0, 1, 2]], cd_a_m2=0.0)
    hab = build_iss_grade_hab(crew=2, water_store=120.0, o2_store=40.0,
                              food_store=25.0, battery_kwh=60.0,
                              supply_kw=2.5)
    rng = RngRegistry(20490101)
    rng.stream("failures", 1).random(5)
    return el, lander, hab, rng


def test_roundtrip_exact(db, tmp_path):
    el, lander, hab, rng = _scenario(db)
    save = build_save(t=1_234.5, vessels={"lander": lander},
                      orbits={"lander": el}, ledgers={"hab": hab}, rng=rng)
    path = tmp_path / "test.sav"
    write_save(path, save)
    loaded = read_save(path)

    el2 = elements_from_dict(loaded["orbits"]["lander"])
    assert el2 == el                       # bit-exact element round-trip
    v2 = vessel_from_dict(loaded["vessels"]["lander"], db)
    assert v2.total_mass_kg() == lander.total_mass_kg()
    assert v2.stage_plan == lander.stage_plan
    hab2 = ledger_from_dict(loaded["ledgers"]["hab"])
    for res in hab.buffers:
        assert hab2.buffers[res].level == hab.buffers[res].level
    rng2 = RngRegistry.from_state(loaded["rng"])
    assert rng2.stream("failures", 1).random(4).tolist() == \
        rng.stream("failures", 1).random(4).tolist()


def test_resume_is_divergence_free(db, tmp_path):
    """Load-then-advance must equal never-saved-advance exactly: saves are
    state snapshots; nothing may be lost in the round trip."""
    _, _, hab_a, _ = _scenario(db)
    _, _, hab_b, _ = _scenario(db)

    hab_a.advance(0.0, 3.0 * DAY)
    save = build_save(t=3.0 * DAY, ledgers={"hab": hab_a})
    path = tmp_path / "mid.sav"
    write_save(path, save)
    hab_resumed = ledger_from_dict(read_save(path)["ledgers"]["hab"])

    hab_resumed.advance(3.0 * DAY, 10.0 * DAY)
    hab_b.advance(0.0, 3.0 * DAY)
    hab_b.advance(3.0 * DAY, 10.0 * DAY)
    for res in hab_b.buffers:
        assert hab_resumed.buffers[res].level == pytest.approx(
            hab_b.buffers[res].level, rel=1e-12, abs=1e-12)


def test_version_gate(tmp_path):
    save = build_save(t=0.0)
    save["schema_version"] = 999
    path = tmp_path / "future.sav"
    write_save(path, save)
    with pytest.raises(ValueError, match="unsupported"):
        read_save(path)


def test_golden_save_1_loads(db):
    """GOLDEN SAVE #1 (Phase 2 DoD). Regenerate ONLY with a schema
    migration: python tools/gen_golden.py"""
    assert GOLDEN.exists(), "golden fixture missing — run tools/gen_golden.py"
    save = read_save(GOLDEN)
    assert save["schema_version"] == SCHEMA_VERSION
    assert save["propagator"] == "patched_conics"
    el = elements_from_dict(save["orbits"]["lander"])
    rx, ry, _, _ = elements_to_state(el, save["t"])
    assert math.isfinite(rx) and math.isfinite(ry)
    hab = ledger_from_dict(save["ledgers"]["hab"])
    events = hab.advance(save["t"], save["t"] + 14.0 * DAY)
    critical = {"Oxygen", "Water", "FoodRations"}
    assert not any(e.kind == "buffer_empty" and e.subject in critical
                   for e in events)
