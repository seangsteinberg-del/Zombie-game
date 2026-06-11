"""Builder (Engineer screen) logic tests: catalog gating, stack/stage
assembly, live stats, pricing, and the launch-integration vessel."""

import os

import pytest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from aphelion.content.loader import default_data_dir, load_packs
from aphelion.content.validate import validate
from aphelion.main import Builder
from aphelion.sim.research import ResearchState


@pytest.fixture(scope="module")
def db():
    d = load_packs(default_data_dir())
    validate(d)
    return d


def test_catalog_lists_full_parts_pack(db):
    b = Builder(db, ResearchState())
    assert len(b.catalog) == 33    # 14 engines + 15 tanks + payload + 3 crew


def test_research_gating_in_builder(db):
    rs = ResearchState()
    b = Builder(db, rs)
    assert b.locked("core:engine_ml111")          # gated by isru_large
    assert not b.locked("core:engine_m733")
    b.cursor = b.catalog.index("core:engine_ml111")
    b.add()
    assert b.stack == [[]]                        # refused
    rs.earn_science(10_000.0)
    rs.earn_eng_data(10_000.0)
    rs.unlock(db, "core:tech_isru_large")
    b.add()
    assert b.stack == [["core:engine_ml111"]]


def test_stack_stages_and_stats(db):
    b = Builder(db, ResearchState())
    for pid in ("core:engine_m733", "core:engine_m733", "core:tank_ml_xl"):
        b.cursor = b.catalog.index(pid)
        b.add()
    b.new_stage()
    for pid in ("core:engine_mv815", "core:tank_ml_m", "core:payload_2t"):
        b.cursor = b.catalog.index(pid)
        b.add()
    v = b.build_vessel()
    assert v is not None
    stats = v.stage_stats()
    assert len(stats) == 2
    assert stats[0]["twr"] > 1.0                  # it can lift off
    assert sum(s["dv_vac"] for s in stats) > 8_000.0
    assert b.price(v) > 0.0


def test_remove_and_empty_guard(db):
    b = Builder(db, ResearchState())
    assert b.build_vessel() is None
    b.cursor = b.catalog.index("core:tank_ml_s")
    b.add()
    b.remove()
    assert b.build_vessel() is None
