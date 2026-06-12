"""05 chains IN PLAY: fab modules run as ledger transformers off the
generated catalog, the labor pool prices f_labor, wear degrades
throughput until PM draws real parts, failed fabs wait on spares, and
the RX-22 reclaims repair scrap."""

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pytest

from aphelion.core.rng import RngRegistry
from aphelion.game.basebuild import CATALOG, add_module
from aphelion.game.crew import CrewMember
from aphelion.game.sites import SITES
from aphelion.main import BaseSite

DAY = 86_400.0


def _base():
    return BaseSite("Forge Base", 0.0, RngRegistry(11),
                    site_id="site:peary")


def _add(b, key, serial=1):
    mod = add_module(b.net, key, SITES[b.site_id], serial)
    b.built.append(key)
    return mod


def test_fab_catalog_entries_generated_from_chains():
    """The ledger entries derive from chains.py — stoich, power, and
    §4.6 maintenance all single-sourced."""
    f = CATALOG["fab_foundry_mill"]
    assert f["primary"][0] == "MetalStock"
    assert f["primary"][1] * DAY == pytest.approx(5_000.0)   # 5 t/day
    assert f["power_kw"] == pytest.approx(160.0, abs=1.0)
    assert f["inputs"]["Aluminum"] == pytest.approx(0.55 / 0.96)
    assert f["maint"] == "foundry_mill" and f["mass_t"] == 25.0
    assert f["labor_day"] == (pytest.approx(2.0), pytest.approx(12.0))
    e = CATALOG["fab_elec_assy"]
    assert e["inputs"]["Wafers"] == pytest.approx(0.01)
    assert CATALOG["bot_worker"]["robot"] is True


def test_foundry_runs_on_local_metals_and_labor():
    b = _base()
    _add(b, "reactor_100")
    foundry = _add(b, "fab_foundry_mill")
    for res, kg in (("Aluminum", 20_000.0), ("IronSteel", 12_000.0),
                    ("Titanium", 4_000.0)):
        b.net.buffers[res].level = kg
    crew = {"E": CrewMember("E", "engineer", 2), "P": CrewMember("P", "pilot", 1)}
    b.crew = ["E", "P"]
    _add(b, "bot_worker", 1)
    _add(b, "bot_mule", 2)
    b.apply_crew_effects(crew)
    # pool: 16 crew-h vs 2 needed; 16 robot-h vs 12 — fully staffed
    assert foundry.f_labor == pytest.approx(1.0)
    b.advance(2.0 * DAY, crew)
    made = b.net.buffers["MetalStock"].level
    assert made > 7_000.0                      # ~5 t/day at f≈1


def test_labor_pool_starves_unstaffed_fabs():
    b = _base()
    _add(b, "reactor_100")
    foundry = _add(b, "fab_foundry_mill")
    b.crew = []
    b.apply_crew_effects({})
    assert foundry.f_labor == 0.0              # nobody on site = no shift


def test_wear_pm_and_degraded():
    b = _base()
    foundry = _add(b, "fab_foundry_mill")
    foundry.state = "RUNNING"
    # no MachineParts in storage: wear runs straight through 0.5
    b.cond[foundry.module_id] = 0.56
    notes = b.step_wear(800.0, dusty=True)     # 800 h dusty = −0.133
    assert b.cond[foundry.module_id] < 0.5
    assert foundry.f_condition < 1.0
    assert any("DEGRADED" in n for n in notes)
    # stock the shelves: PM fires and pulls condition back up
    b.net.buffers["MachineParts"].level = 1_000.0
    b.net.buffers["Polymers"].level = 1_000.0
    notes2 = b.step_wear(1.0, dusty=True)
    assert any("PM on" in n for n in notes2)
    assert b.cond[foundry.module_id] > 0.5
    assert b.net.buffers["MachineParts"].level < 1_000.0   # 40 kg drawn


def test_failed_fab_waits_on_spares_then_repairs():
    b = _base()
    foundry = _add(b, "fab_foundry_mill")
    foundry.state = "FAILED"
    b.pending_repairs.append((1_000.0, foundry.module_id))
    b.advance(2_000.0)
    assert foundry.state == "FAILED"           # no parts in storage
    assert b.pending_repairs                   # re-queued for tomorrow
    b.net.buffers["MachineParts"].level = 5_000.0
    b.net.buffers["Electronics"].level = 5_000.0
    b.net.buffers["StructuralParts"].level = 5_000.0
    b.net.buffers["Polymers"].level = 5_000.0
    b.advance(b.pending_repairs[0][0] + 10.0)
    assert foundry.state != "FAILED"
    assert b.net.buffers["MachineParts"].level < 5_000.0


def test_recycler_reclaims_repair_scrap():
    b = _base()
    _add(b, "recycler")
    for res in ("MachineParts", "IronSteel", "Aluminum"):
        if res not in b.net.buffers:
            from aphelion.game.basebuild import ensure_buffers
            ensure_buffers(b.net, {"inputs": {res: 1}, "outputs": {}})
    b.net.buffers["MachineParts"].level = 100.0
    fe0 = b.net.buffers["IronSteel"].level
    assert b._debit_parts({"MachineParts": 100.0})
    # 80% of 100 kg returns: 55 kg IronSteel + 25 kg Aluminum + 20 Regolith
    assert b.net.buffers["IronSteel"].level - fe0 == pytest.approx(55.0)
    assert b.net.buffers["Aluminum"].level == pytest.approx(25.0)


def test_cond_survives_save(tmp_path):
    from aphelion.content.loader import default_data_dir, load_packs
    from aphelion.game.crew import CrewMember as CM
    from aphelion.save.campaign import (read_campaign, snapshot_campaign,
                                        write_campaign)
    from aphelion.sim.economy import Program
    from aphelion.sim.orbits.ephemeris import load_solar_system
    from aphelion.sim.research import ResearchState
    db, tree = load_solar_system()
    b = _base()
    foundry = _add(b, "fab_foundry_mill")
    b.cond[foundry.module_id] = 0.42
    snap = snapshot_campaign(
        t=0.0, vessels=[], active_idx=0, next_vid=1,
        program=Program(funds=1.0), research=ResearchState(), crew={},
        visited=set(), bases=[b], tutorial_done=True)
    path = tmp_path / "wear.aph"
    write_campaign(path, snap)
    got = read_campaign(path, db, tree)
    assert got["bases"][0]["cond"][foundry.module_id] == \
        pytest.approx(0.42)
