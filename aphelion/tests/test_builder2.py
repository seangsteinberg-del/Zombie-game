"""Builder 2.0 (depth update): categories/filtering, mid-stack editing,
thrust-weighted stage stats, real part pricing, fairing drag, blueprints."""

import os

import pytest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from aphelion.content.loader import default_data_dir, load_packs
from aphelion.content.validate import validate
from aphelion.main import Builder
from aphelion.render.vessel_art import vessel_frontal_area, vessel_metrics
from aphelion.sim.economy import part_cost_usd, vessel_cost_usd
from aphelion.sim.research import ResearchState
from aphelion.sim.vessels.vessel import G0, Vessel


@pytest.fixture(scope="module")
def db():
    d = load_packs(default_data_dir())
    validate(d)
    return d


def test_catalog_is_grouped_with_headers(db):
    b = Builder(db, ResearchState())
    kinds = [k for k, _ in b.entries]
    assert "header" in kinds and "part" in kinds
    assert b.entries[0][0] == "header"            # opens with a group label
    assert b.entries[b.cursor][0] == "part"       # cursor never on a header


def test_filter_cycling_narrows_catalog(db):
    b = Builder(db, ResearchState())
    full = len(b.catalog)
    b.cycle_filter(+1)                            # -> engine
    assert 0 < len(b.catalog) < full
    assert all(db.parts[p]["type"] == "engine" for p in b.catalog)
    for _ in range(len(b.CATS) - 1):
        b.cycle_filter(+1)
    assert len(b.catalog) == full                 # wrapped back to ALL


def test_mid_stack_remove_and_split(db):
    b = Builder(db, ResearchState())
    for pid in ("core:engine_m733", "core:tank_ml_xl", "core:engine_mv815",
                "core:tank_ml_m"):
        assert b.select(pid)
        b.add()
    assert b.stack == [["core:engine_m733", "core:tank_ml_xl",
                        "core:engine_mv815", "core:tank_ml_m"]]
    b.focus = "stack"
    b.stack_cursor = 2                            # the vacuum engine row
    b.split_stage()
    assert b.stack == [["core:engine_m733", "core:tank_ml_xl"],
                       ["core:engine_mv815", "core:tank_ml_m"]]
    b.stack_cursor = 1                            # XL tank
    b.remove()
    assert b.stack[0] == ["core:engine_m733"]


def test_stage_stats_thrust_weighted_isp(db):
    # one big low-Isp booster + one small high-Isp sustainer: the naive
    # arithmetic mean overstates dv; thrust-weighting must match hand math
    rows = [Vessel.fueled_row(db, p) for p in
            ("core:engine_k845", "core:engine_mv815", "core:tank_ml_l")]
    v = Vessel(db, rows, stage_plan=[[0, 1, 2]])
    s = v.stage_stats()[0]
    e1 = db.parts["core:engine_k845"]["engine"]
    e2 = db.parts["core:engine_mv815"]["engine"]
    f1, f2 = e1["thrust_kN"] * 1e3, e2["thrust_kN"] * 1e3
    mdot = f1 / (G0 * e1["isp_s"]) + f2 / (G0 * e2["isp_s"])
    import math
    m0 = v.total_mass_kg()
    expect = (f1 + f2) / mdot * math.log(m0 / (m0 - s["prop_kg"]))
    assert s["dv_vac"] == pytest.approx(expect, rel=1e-9)
    assert s["burn_s"] == pytest.approx(s["prop_kg"] / mdot, rel=1e-9)
    assert 0.0 < s["dv_sl"] < s["dv_vac"]         # back-pressure costs dv


def test_part_pricing_tiers_and_types(db):
    t0_tank = part_cost_usd(db.parts["core:tank_ml_s"])
    big_engine = part_cost_usd(db.parts["core:engine_k845"])
    capsule = part_cost_usd(db.parts["core:capsule_vela"])
    assert big_engine > t0_tank                   # engines out-price sheet metal
    assert capsule > t0_tank
    # tier multiplies: the T2 Raptor-V outprices a same-thrust-class T0
    rap = part_cost_usd(db.parts["core:engine_mv2530"])
    assert rap > big_engine * 0.5


def test_vessel_cost_and_frontal_area(db):
    b = Builder(db, ResearchState())
    for pid in ("core:engine_m733", "core:tank_ml_xl"):
        assert b.select(pid)
        b.add()
    b.new_stage()
    for pid in ("core:tank_ml_m", "core:capsule_vela"):
        assert b.select(pid)
        b.add()
    v = b.build_vessel()
    assert v is not None
    assert b.price(v) == pytest.approx(vessel_cost_usd(v))
    # capsule nose earns the fairing discount vs a blunt tank top
    area_capsule = vessel_frontal_area(db, b.stack)
    blunt = [list(b.stack[0]), ["core:tank_ml_m"]]
    area_blunt = vessel_frontal_area(db, blunt)
    h, d = vessel_metrics(db, b.stack)
    assert area_capsule > 0.8 and h > 5.0 and d > 1.0
    assert v.cd_a_m2 == pytest.approx(area_capsule)
    assert area_capsule < area_blunt / 0.7 + 1e-9


def test_blueprint_roundtrip_via_load_stack(db):
    b = Builder(db, ResearchState())
    for pid in ("core:engine_m733", "core:tank_ml_xl"):
        assert b.select(pid)
        b.add()
    saved = [list(s) for s in b.stack]
    b2 = Builder(db, ResearchState())
    assert b2.load_stack(saved + [["core:not_a_part"]])
    assert b2.stack == saved                      # unknown ids dropped


def test_crew_capacity_counts_seats(db):
    b = Builder(db, ResearchState())
    assert b.crew_capacity() == 0
    assert b.select("core:capsule_vela")
    b.add()
    assert b.crew_capacity() == 2
