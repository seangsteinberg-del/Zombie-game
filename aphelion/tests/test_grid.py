"""Drydock 2.0 grid datamodel (06 §2.1/§2.14): footprints, derived
joints under the node rules, and validation E1–E5."""

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pytest

from aphelion.content.loader import default_data_dir, load_packs
from aphelion.sim.vessels.grid import (
    GridVessel, PART_CAP, axial_rating_kn)


@pytest.fixture(scope="module")
def parts():
    return load_packs(default_data_dir()).by_type("parts")


def stack3(parts) -> GridVessel:
    """Capsule on a methalox tank on a Raptor — the canonical mini-stack."""
    v = GridVessel()
    v.add("core:engine_m2256", parts["core:engine_m2256"], 0, 0)   # 2×3
    v.add("core:tank_ml_m", parts["core:tank_ml_m"], 0, 3)         # 2×4
    v.add("core:capsule_vela", parts["core:capsule_vela"], 0, 7)   # 2×3
    return v


def test_stack_joints_and_ratings(parts):
    v = stack3(parts)
    js = v.joints()
    kinds = sorted(j.kind for j in js)
    assert kinds == ["stack", "stack"]
    # engine stack node rates max(1200, 1.25·F_vac) = 1.25·2394 ≈ 2993
    assert axial_rating_kn(parts["core:engine_m2256"]) == pytest.approx(
        1.25 * 2394.0)
    assert v.validate() == []          # command capsule, connected, clean


def test_e1_e2_disconnected_and_uncommanded(parts):
    v = GridVessel()
    v.add("core:tank_ml_m", parts["core:tank_ml_m"], 0, 0)
    v.add("core:tank_ml_m", parts["core:tank_ml_m"], 10, 0)  # floating
    codes = [c for c, _ in v.validate()]
    assert "E1" in codes and "E2" in codes


def test_e3_decoupler_must_split_in_two(parts):
    v = stack3(parts)
    # a proper decoupler between tank and capsule: splits exactly in two
    v.move(2, 0, 8)                                        # capsule up 1
    v.add("core:st_dc2", parts["core:st_dc2"], 0, 7)       # 2×1 between
    assert ("E3", 3) not in v.validate()
    # a dangling decoupler bolted to the side splits nothing
    v.add("core:st_dc2", parts["core:st_dc2"], 2, 3)
    assert ("E3", 4) in v.validate()


def test_e4_overlap_but_fairing_interior_exempt(parts):
    v = stack3(parts)
    v.add("core:tank_ml_s", parts["core:tank_ml_s"], 1, 4)  # overlaps tank
    assert any(c == "E4" for c, _ in v.validate())
    # payload INSIDE a fairing is legal and joined to it
    f = GridVessel()
    f.add("core:probe_longshot", parts["core:probe_longshot"], 1, 4)
    f.add("core:st_fr3", parts["core:st_fr3"], 0, 0)        # 3×9, int 3×8
    assert f.container_of(0) == 1
    assert not any(c == "E4" for c, _ in f.validate())
    assert any(j.kind == "interior" for j in f.joints())


def test_e5_plume_and_vented_interstage(parts):
    v = GridVessel()
    v.add("core:capsule_vela", parts["core:capsule_vela"], 0, 9)
    v.add("core:engine_m2256", parts["core:engine_m2256"], 0, 6)
    v.add("core:tank_ml_s", parts["core:tank_ml_s"], 0, 2)  # in the plume
    assert any(c == "E5" for c, _ in v.validate())
    # hot-staging through a vented interstage is the legal version
    v.add("core:st_is_v", parts["core:st_is_v"], 0, 4)
    assert not any(c == "E5" for c, _ in v.validate())
    # RCS quads are surface-mount and plume-exempt
    r = GridVessel()
    r.add("core:capsule_vela", parts["core:capsule_vela"], 0, 0)
    r.add("core:rcs_hyp", parts["core:rcs_hyp"], 2, 1)      # side-mounted
    assert any(j.kind == "radial" for j in r.joints())
    assert not any(c == "E5" for c, _ in r.validate())


def test_no_bottom_rule_engines_hang_nothing(parts):
    v = GridVessel()
    v.add("core:engine_m2256", parts["core:engine_m2256"], 0, 4)
    v.add("core:tank_ml_s", parts["core:tank_ml_s"], 0, 2)  # below engine
    # touching faces but engines expose no bottom node: not a stack joint
    assert not any(j.kind == "stack" for j in v.joints())


def test_part_cap_refused(parts):
    v = GridVessel()
    g1 = parts["core:st_g1"]
    for i in range(PART_CAP):
        assert v.add("core:st_g1", g1, i % 40, i // 40) is not None
    assert v.add("core:st_g1", g1, 50, 50) is None


def test_dry_mass_com_and_roundtrip(parts):
    v = stack3(parts)
    assert v.dry_mass_t() == pytest.approx(
        1.63 + 0.72 + parts["core:capsule_vela"]["mass_t"])
    cx, cy = v.com()
    assert cx == pytest.approx(1.0)    # symmetric 2-wide stack
    assert 0.0 < cy < 10.0
    d = v.to_dict()
    db = load_packs(default_data_dir())
    v2 = GridVessel.from_dict(d, db)
    assert v2.to_dict() == d
    assert v2.validate() == v.validate()
