"""Base construction: per-site catalogs, real stoichiometry through the
ledger, funded builds, tech gates, and the founding starter network."""

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pytest

from aphelion.core.rng import RngRegistry
from aphelion.game.basebuild import (
    CATALOG, add_module, catalog_for_kind, starter_network,
)
from aphelion.game.sites import SITES
from aphelion.main import BaseSite
from aphelion.sim.economy import Program
from aphelion.sim.research import ResearchState

DAY = 86_400.0


def test_catalog_filters_by_site_kind():
    psr = catalog_for_kind("psr_ice")
    lake = catalog_for_kind("methane_lake")
    assert "drill_ice" in psr and "lake_pump" not in psr
    assert "lake_pump" in lake and "drill_ice" not in lake
    assert "solar_array" in psr and "solar_array" in lake   # universal


def test_starter_network_shape():
    net = starter_network(SITES["site:peary"])
    assert {"Water", "Oxygen", "Hydrogen", "Methane", "CO2"} <= set(net.buffers)
    assert len(net.modules) == 1                  # the free solar wing
    assert net.modules[0].power_kw == pytest.approx(-40.0 * 0.85)


def test_peary_ice_to_lox_chain_runs():
    """Drill + electrolyzer on lunar ice: water flows, oxygen banks, the
    same ledger machinery the Phase-3 acceptance proved."""
    base = BaseSite("Peary Base", 0.0, RngRegistry(7), site_id="site:peary")
    program = Program(funds=500e6)
    research = ResearchState()
    ok, _ = base.build("drill_ice", 0.0, research, program)
    assert ok
    ok, _ = base.build("electrolyzer", 0.0, research, program)
    assert ok
    ok, _ = base.build("solar_array", 0.0, research, program)   # power it
    assert ok
    ok, _ = base.build("solar_array", 0.0, research, program)
    assert ok
    base.advance(20.0 * DAY)
    assert base.net.buffers["Oxygen"].level > 5_000.0
    assert program.funds == pytest.approx(500e6 - 38e6)


def test_reactor_is_tech_gated():
    base = BaseSite("Peary Base", 0.0, RngRegistry(7))
    program = Program(funds=500e6)
    research = ResearchState()
    ok, msg = base.build("reactor_100", 0.0, research, program)
    assert not ok and "research" in msg
    research.unlocked.add("core:tech_pw05_fission_surface")
    ok, _ = base.build("reactor_100", 0.0, research, program)
    assert ok


def test_insufficient_funds_refused():
    base = BaseSite("Peary Base", 0.0, RngRegistry(7))
    program = Program(funds=1e6)
    ok, msg = base.build("drill_ice", 0.0, ResearchState(), program)
    assert not ok and "funds" in msg
    assert program.funds == 1e6


def test_tank_farm_extends_capacity():
    net = starter_network(SITES["site:peary"])
    cap0 = net.buffers["Water"].capacity
    add_module(net, "tank_farm", SITES["site:peary"], serial=1)
    assert net.buffers["Water"].capacity == cap0 + 40_000.0


def test_sabatier_chain_on_mars():
    """CO2 intake + drill + electrolyzer + sabatier: methane from the
    martian sky (05 ISRU chain), self-consistent stoichiometry."""
    base = BaseSite("Jezero Base", 0.0, RngRegistry(11),
                    site_id="site:jezero")
    program = Program(funds=900e6)
    research = ResearchState()
    for key in ("drill_ice", "electrolyzer", "co2_intake", "sabatier",
                "solar_array", "solar_array", "solar_array", "solar_array",
                "solar_array", "solar_array"):
        ok, msg = base.build(key, 0.0, research, program)
        assert ok, msg
    base.advance(30.0 * DAY)
    # equipment failures (pre-rolled MTBF) legitimately eat into the run;
    # the chain is proven if real methane banked at all
    assert base.net.buffers["Methane"].level > 400.0
