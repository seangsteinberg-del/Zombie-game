"""ISRU v2 (04): the expanded machine/plant catalog — mass balance to
±1% on every transformer (vented streams accounted), canonical energy
figures, tech gating, geology gating, and the headline production chains
(lunar LOX, Mars methalox, ilmenite steel, MRE, Titan hydrocarbons)."""

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pytest

from aphelion.content.loader import default_data_dir, load_packs
from aphelion.core.rng import RngRegistry
from aphelion.game.basebuild import CATALOG, catalog_for_kind
from aphelion.game.sectors import sector_site
from aphelion.game.sites import SITES
from aphelion.main import BaseSite
from aphelion.sim.economy import Program
from aphelion.sim.research import ResearchState

DAY = 86_400.0

# bases-at-sectors need the site registry that main() builds at boot
_db = load_packs(default_data_dir())
for _sid in ("core:sec_moon_01", "core:sec_moon_07"):
    SITES.setdefault(_sid, sector_site(_db, _sid))


def _rs(*nodes):
    rs = ResearchState()
    rs.unlocked.update(nodes)
    return rs


def test_catalog_breadth():
    """The base catalog is a real industry now, not five machines."""
    assert len(CATALOG) >= 30
    transformers = [k for k, m in CATALOG.items() if m["primary"]]
    assert len(transformers) >= 22


def test_every_transformer_conserves_mass():
    """04's binding rule: inputs = outputs (+vented) to ±1% per kg of
    primary product."""
    for key, m in CATALOG.items():
        if not m["primary"]:
            continue
        mass_in = sum(m["inputs"].values())
        mass_out = sum(m["outputs"].values()) + sum(
            m.get("vented", {}).values())
        if mass_in == 0.0:                  # pure extraction/intake
            assert mass_out >= 1.0, key
            continue
        assert abs(mass_in - mass_out) / mass_in < 0.011, (
            key, mass_in, mass_out)


def test_canonical_energy_figures():
    """kWe = canonical kWh/kg × nominal rate / 24 h (04 §3.4)."""
    pem = CATALOG["electrolyzer"]
    rate_h2o_day = pem["primary"][1] * DAY * pem["inputs"]["Water"]
    assert pem["power_kw"] == pytest.approx(5.6 * rate_h2o_day / 24.0,
                                            rel=0.02)
    sab = CATALOG["sabatier"]
    assert sab["power_kw"] == pytest.approx(
        0.2 * sab["primary"][1] * DAY / 24.0, rel=0.1)
    assert sab["heat_kw"] < 0.0             # net exotherm to the ledger
    mre = CATALOG["mre_cell"]
    assert mre["power_kw"] == pytest.approx(35.0 * 250.0 / 24.0, rel=0.01)


def test_tier_gating_is_broad():
    gated = {m["tech"] for m in CATALOG.values() if m["tech"]}
    assert len(gated) >= 12                 # many distinct tree nodes


def test_geology_gating():
    psr = catalog_for_kind("psr_ice")
    lake = catalog_for_kind("methane_lake")
    cloud = catalog_for_kind("aerostat")
    rock = catalog_for_kind("regolith")
    assert "drill_ice" in psr and "lake_pump" not in psr
    assert "lake_pump" in lake and "drill_ice" not in lake
    assert "venus_intake" in cloud and "venus_intake" not in rock
    assert "mond_refinery" in rock          # M-type asteroid refining
    assert "solar_array" in psr and "solar_array" in lake


def test_ilmenite_line_makes_steel_and_oxygen():
    """Moon regolith -> O2 + IronSteel (RX-07 with folded beneficiation)."""
    base = BaseSite("Mare Base", 0.0, RngRegistry(3),
                    site_id="core:sec_moon_01")
    program = Program(funds=2e9)
    rs = _rs("core:tech_is02_regolith_excavation",
             "core:tech_is05_polar_ice_mining",
             "core:tech_is08_ilmenite_reduction",
             "core:tech_pw05_fission_surface")
    for key in ("bucket_wheel", "ilmenite_line", "reactor_100",
                "yard_extension"):
        ok, msg = base.build(key, 0.0, rs, program)
        assert ok, msg
    base.advance(30.0 * DAY)
    assert base.net.buffers["Oxygen"].level > 1_000.0
    assert base.net.buffers["IronSteel"].level > 3_000.0
    assert base.net.buffers["Regolith"].capacity >= 2_000_000.0


def test_mre_runs_on_any_regolith():
    base = BaseSite("Highland Base", 0.0, RngRegistry(5),
                    site_id="core:sec_moon_07")
    program = Program(funds=2e9)
    rs = _rs("core:tech_is02_regolith_excavation",
             "core:tech_is05_polar_ice_mining",
             "core:tech_is13_molten_regolith",
             "core:tech_pw05_fission_surface")
    for key in ("bucket_wheel", "mre_cell", "reactor_100", "reactor_100",
                "reactor_100", "reactor_100", "yard_extension"):
        ok, msg = base.build(key, 0.0, rs, program)
        assert ok, msg
    base.advance(20.0 * DAY)
    assert base.net.buffers["Oxygen"].level > 2_000.0
    assert base.net.buffers["IronSteel"].level > 1_400.0


def test_titan_hydrocarbon_chain():
    """Sea pump fills methane + nitrogen; Haber makes ammonia from sea
    nitrogen + electrolyzer hydrogen would need water — assert the pump
    and intake streams themselves."""
    base = BaseSite("Ligeia Base", 0.0, RngRegistry(9),
                    site_id="site:titan_shore")
    program = Program(funds=2e9)
    rs = _rs("core:tech_hb07_titan_outpost",
             "core:tech_is19_titan_hydrocarbons",
             "core:tech_pw04_kilopower")
    for key in ("lake_pump", "titan_intake", "reactor_kilo", "reactor_kilo",
                "tank_farm"):
        ok, msg = base.build(key, 0.0, rs, program)
        assert ok, msg
    base.advance(10.0 * DAY)
    assert base.net.buffers["Methane"].level > 30_000.0
    assert base.net.buffers["Nitrogen"].level > 10_000.0


def test_storable_propellant_chain_exists():
    """B11: hypergolics are produced, never age out — MMH + NTO plants
    exist with balanced recipes."""
    mmh, nto = CATALOG["mmh_loop"], CATALOG["nto_plant"]
    assert mmh["primary"][0] == "MMH" and nto["primary"][0] == "NTO"
    assert mmh["inputs"]["Ammonia"] == pytest.approx(0.74)
    assert nto["inputs"]["Oxygen"] == pytest.approx(0.70)


def test_construction_pipeline_deploy_to_commission():
    """07 §2.3: ISRU-built structures consume LOCAL materials and only
    come online after the build schedule elapses."""
    base = BaseSite("Vault Base", 0.0, RngRegistry(13),
                    site_id="core:sec_moon_07")
    program = Program(funds=2e9)
    rs = _rs("core:tech_is02_regolith_excavation",
             "core:tech_is05_polar_ice_mining",
             "core:tech_hb03_regolith_printing",
             "core:tech_is09b_materials_chem",
             "core:tech_pw05_fission_surface")
    # no regolith banked yet: the vault refuses
    ok, msg = base.build("regolith_vault", 0.0, rs, program)
    assert not ok and "materials" in msg
    # mine sinter feed + fiber first
    for key in ("bucket_wheel", "reactor_100", "yard_extension",
                "basalt_furnace"):
        ok, msg = base.build(key, 0.0, rs, program)
        assert ok, msg
    base.advance(3.0 * DAY)
    assert base.net.buffers["Regolith"].level > 150_000.0
    assert base.net.buffers["BasaltFiber"].level > 700.0
    t0 = base.last_t
    ok, msg = base.build("regolith_vault", t0, rs, program)
    assert ok and "DEPLOYING" in msg
    vault = next(m for m in base.net.modules
                 if m.module_id.startswith("regolith_vault"))
    assert vault.state == "OFF"
    base.advance(t0 + 30.0 * DAY)
    assert vault.state == "OFF"              # 60-day print, halfway
    base.advance(t0 + 61.0 * DAY)
    assert vault.state == "RUNNING"          # commissioned
    assert any(e.kind == "commissioned" for e in base.events)
    assert base.beds() == 5                  # the vault's berths count


def test_food_chain_greenhouse():
    """Farms: a greenhouse turns water + CO2 + power into FoodRations
    and oxygen (08 agriculture, HAB-06)."""
    base = BaseSite("Agri Base", 0.0, RngRegistry(21),
                    site_id="site:jezero")
    program = Program(funds=2e9)
    rs = _rs("core:tech_is05_polar_ice_mining",
             "core:tech_is06_mars_atmo_processing",
             "core:tech_ls04_greenhouse", "core:tech_is09b_materials_chem",
             "core:tech_is02_regolith_excavation",
             "core:tech_pw05_fission_surface")
    for key in ("drill_ice", "co2_intake", "bucket_wheel", "glass_furnace",
                "reactor_100", "reactor_100", "yard_extension"):
        ok, msg = base.build(key, 0.0, rs, program)
        assert ok, msg
    base.advance(3.0 * DAY)                  # bank glass for the dome
    ok, msg = base.build("greenhouse", base.last_t, rs, program)
    assert ok, msg
    base.advance(base.last_t + 40.0 * DAY)
    assert base.net.buffers["FoodRations"].level > 100.0
    assert base.net.buffers["Oxygen"].level > 100.0


def test_machine_shop_makes_maintenance_currency():
    mod = CATALOG["machine_shop"]
    assert mod["primary"][0] == "MachineParts"
    assert mod["tech"] == "core:tech_in01_workshop"
    mill = CATALOG["struct_mill"]
    assert mill["primary"][0] == "StructuralParts"


def test_he3_kiln_is_speculative_endgame():
    kiln = CATALOG["he3_kiln"]
    assert kiln["tech"] == "core:tech_is20_he3_kiln"
    # byproducts dwarf the helium-3 — that is the canon point
    assert kiln["outputs"]["Hydrogen"] > 1_000.0
    assert kiln["primary"][1] * DAY == pytest.approx(0.014)
