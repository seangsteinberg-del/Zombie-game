"""Content pipeline + canon body pack tests: loader rules, validator
invariants, and spot checks against the 03 §4.1/4.2/4.3 canon tables."""

import json
import math

import pytest

from aphelion.content.loader import ContentError, default_data_dir, load_packs
from aphelion.content.validate import validate
from aphelion.core.units import AU, SECONDS_PER_DAY
from aphelion.sim.orbits.ephemeris import build_frame_tree, load_solar_system
from aphelion.sim.orbits.kepler import elements_to_state


@pytest.fixture(scope="module")
def db():
    d = load_packs(default_data_dir())
    validate(d)
    return d


@pytest.fixture(scope="module")
def tree(db):
    return build_frame_tree(db)


# ---- pack integrity ------------------------------------------------------

def test_pack_loads_37_bodies(db):
    assert len(db.bodies) == 37


def test_exactly_one_root(db):
    roots = [i for i, b in db.bodies.items() if b["parent"] is None]
    assert roots == ["core:sun"]


def test_all_parents_exist(db):
    for item_id, body in db.bodies.items():
        if body["parent"] is not None:
            assert body["parent"] in db.bodies, item_id


# ---- canon spot checks (03 §4.1 r_SOI column) ------------------------------

@pytest.mark.parametrize("body_id, soi_km", [
    ("core:earth", 9.24e5),
    ("core:moon", 66_200),
    ("core:mars", 5.77e5),
    ("core:jupiter", 4.82e7),
    ("core:saturn", 5.48e7),
    ("core:europa", 9_730),
    ("core:titan", 43_300),
    ("core:enceladus", 490),
    ("core:charon", 8_440),
    ("core:psyche", 18_400),
])
def test_soi_matches_canon_table(db, body_id, soi_km):
    assert db.bodies[body_id]["soi_m"] / 1e3 == pytest.approx(soi_km, rel=0.02)


@pytest.mark.parametrize("body_id", [
    "core:phobos", "core:deimos", "core:bennu", "core:ryugu", "core:itokawa",
    "core:eros", "core:apophis", "core:67p", "core:halley", "core:arrokoth",
])
def test_dock_mode_bodies_have_no_soi(db, body_id):
    assert db.bodies[body_id]["soi_m"] == 0.0


def test_retrograde_senses(db):
    assert db.bodies["core:halley"]["elements"]["sense"] == -1
    assert db.bodies["core:triton"]["elements"]["sense"] == -1


# ---- orbital sanity against published periods ------------------------------

@pytest.mark.parametrize("body_id, period_days, tol_days", [
    ("core:earth", 365.26, 0.2),
    ("core:mars", 686.98, 0.7),
    ("core:jupiter", 4_332.6, 10.0),     # 11.862 yr
    ("core:moon", 27.322, 0.05),
    ("core:titan", 15.945, 0.05),
    ("core:io", 1.769, 0.01),
    ("core:charon", 6.387, 0.02),
])
def test_periods_match_canon(tree, body_id, period_days, tol_days):
    el = tree.body(body_id).elements
    assert el.period / SECONDS_PER_DAY == pytest.approx(period_days, abs=tol_days)


def test_earth_starts_near_perihelion_longitude(tree):
    """M0 = 357.5 deg: Earth is 2.5 deg before perihelion at epoch."""
    el = tree.body("core:earth").elements
    rx, ry, _, _ = elements_to_state(el, 0.0)
    r = math.hypot(rx, ry)
    # near perihelion: r close to a(1-e)
    assert r == pytest.approx(el.a * (1 - el.e), rel=2e-4)


def test_moon_distance_from_earth_sane(tree):
    rx, ry, _, _ = tree.state_in_parent("core:moon", 0.0)
    r = math.hypot(rx, ry)
    assert 3.56e8 < r < 4.07e8     # perigee..apogee envelope


def test_pluto_charon_chain(tree):
    assert tree.chain("core:charon") == ["core:sun", "core:pluto", "core:charon"]


# ---- loader rules -----------------------------------------------------------

def test_collision_without_patch_flag_rejected(tmp_path):
    for pack, fname in (("core", "thing.json"), ("zmod", "thing2.json")):
        d = tmp_path / pack / "bodies"
        d.mkdir(parents=True)
    a = {"id": "core:x", "parent": None, "mu_m3s2": 1e10, "radius_m": 1e5,
         "rotation_period_s": 1.0, "soi_m": None, "elements": None}
    (tmp_path / "core" / "bodies" / "x.json").write_text(json.dumps(a))
    b = dict(a)     # same id from another pack, no patch flag
    (tmp_path / "zmod" / "bodies" / "x.json").write_text(json.dumps(b))
    with pytest.raises(ContentError, match="patch"):
        load_packs(tmp_path)


def test_mod_id_must_match_pack_prefix(tmp_path):
    d = tmp_path / "core" / "bodies"
    d.mkdir(parents=True)
    bad = {"id": "other:x", "parent": None, "mu_m3s2": 1e10, "radius_m": 1e5,
           "rotation_period_s": 1.0, "soi_m": None, "elements": None}
    (d / "x.json").write_text(json.dumps(bad))
    with pytest.raises(ContentError, match="must start with"):
        load_packs(tmp_path)


def test_patch_overrides_shallow(tmp_path):
    for pack in ("core", "zmod"):
        (tmp_path / pack / "bodies").mkdir(parents=True)
    base = {"id": "core:x", "parent": None, "mu_m3s2": 1e10, "radius_m": 1e5,
            "rotation_period_s": 1.0, "soi_m": None, "elements": None}
    (tmp_path / "core" / "bodies" / "x.json").write_text(json.dumps(base))
    patch = {"id": "core:x", "patch": True, "radius_m": 2e5}
    (tmp_path / "zmod" / "bodies" / "x.json").write_text(json.dumps(patch))
    db = load_packs(tmp_path)
    assert db.bodies["core:x"]["radius_m"] == 2e5
    assert db.bodies["core:x"]["mu_m3s2"] == 1e10


def test_validator_rejects_soi_drift(tmp_path):
    (tmp_path / "core" / "bodies").mkdir(parents=True)
    sun = {"id": "core:sun", "parent": None, "mu_m3s2": 1.327e20,
           "radius_m": 6.957e8, "rotation_period_s": 1.0,
           "soi_m": None, "elements": None}
    bad = {"id": "core:planet", "parent": "core:sun", "mu_m3s2": 3.986e14,
           "radius_m": 6.371e6, "rotation_period_s": 86_400.0,
           "soi_m": 5.0e8,    # wrong: Laplace gives ~9.24e8
           "elements": {"a_m": 1.496e11, "e": 0.0167, "lon_peri_rad": 1.7959,
                        "t_peri_s": -383_000.0, "sense": 1}}
    (tmp_path / "core" / "bodies" / "sun.json").write_text(json.dumps(sun))
    (tmp_path / "core" / "bodies" / "p.json").write_text(json.dumps(bad))
    db = load_packs(tmp_path)
    with pytest.raises(ContentError, match="deviates"):
        validate(db)


def test_recipe_mass_balance_enforced(tmp_path):
    (tmp_path / "core" / "recipes").mkdir(parents=True)
    bad = {"id": "core:recipe/leaky", "module": "core:module/x", "tier": "T1",
           "inputs_t": {"CO2": 2.75, "Hydrogen": 0.50},
           "outputs_t": {"Methane": 1.00},
           "byproducts_t": {"Water": 1.00},     # should be 2.25
           "energy_kWh_per_t": 200}
    (tmp_path / "core" / "recipes" / "r.json").write_text(json.dumps(bad))
    db = load_packs(tmp_path)
    with pytest.raises(ContentError, match="mass balance"):
        validate(db)


def test_load_solar_system_end_to_end():
    db, tree = load_solar_system()
    assert tree.root == "core:sun"
    assert len(tree.children("core:jupiter")) == 4
