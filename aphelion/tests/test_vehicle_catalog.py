"""10 §1 vehicle catalog as data: the whole pack BOOT-validates, every
item passes VEHICLE_SCHEMA, per-section counts match the §1.1–§1.10
tables, and canon anchors are pinned (RVR-LRV §1.1, RVR-CRAWL §1.1,
HOP-P §1.5/DECISIONS A8, DIR-T §1.7, SUB-T §1.8, CRYO-E §1.8,
WHL-MESH §1.2, CTL-A3 §1.9).

The two TBD-Pass-2 placeholder rows are deliberately NOT encoded
(DECISIONS C20: stats land Pass 2/Phase 5):
  - (LEG-ATH)     §1.2 legged set, ATHLETE anchor  -> locomotion count 7
  - (ROV-E-ABYSS) §1.8 ocean-floor variant, H4 hull -> marine count 5
"""

import pytest

from aphelion.content.loader import default_data_dir, load_packs
from aphelion.content.schema import TYPE_SCHEMAS, VEHICLE_KINDS
from aphelion.content.validate import _check_fields, validate


@pytest.fixture(scope="module")
def db():
    d = load_packs(default_data_dir())
    validate(d)
    return d


@pytest.fixture(scope="module")
def veh(db):
    """Catalog-id index (spec row ids, e.g. 'RVR-LRV')."""
    return {v["catalog_id"]: v for v in db.by_type("vehicles").values()}


# ---- pack integrity --------------------------------------------------------

def test_pack_boot_validates():
    """13 §3.4: loading + validating the full pack must raise nothing."""
    d = load_packs(default_data_dir())
    validate(d)


def test_vehicles_type_registered():
    assert "vehicles" in TYPE_SCHEMAS


def test_every_item_passes_vehicle_schema(db):
    items = db.by_type("vehicles")
    assert items, "vehicles pack is empty"
    for item_id, raw in items.items():
        _check_fields("vehicles", item_id, raw, db.sources[item_id])
        assert item_id.startswith("core:")
        assert raw["kind"] in VEHICLE_KINDS


def test_catalog_ids_unique(db, veh):
    assert len(veh) == len(db.by_type("vehicles")) == 61


# ---- section counts (recounted from 10 §1.1-§1.10) -------------------------

@pytest.mark.parametrize("kind, count", [
    ("rover", 8),               # §1.1
    ("locomotion", 7),          # §1.2 (8 rows minus LEG-ATH placeholder)
    ("aero_marine_part", 11),   # §1.3
    ("utility", 6),             # §1.4
    ("hopper", 4),              # §1.5
    ("aircraft", 7),            # §1.6
    ("balloon", 5),             # §1.7
    ("marine", 5),              # §1.8 (6 rows minus ROV-E-ABYSS placeholder)
    ("control_kit", 3),         # §1.9
    ("bay", 5),                 # §1.10
])
def test_section_counts(db, kind, count):
    got = [v for v in db.by_type("vehicles").values() if v["kind"] == kind]
    assert len(got) == count, kind


# ---- canon spot pins --------------------------------------------------------

def test_rvr_lrv(veh):
    """§1.1: Apollo LRV — 0.21 t dry, VC-1, crew 2, 88 km on AgZn."""
    lrv = veh["RVR-LRV"]
    assert lrv["dry_t"] == pytest.approx(0.21)
    assert lrv["vclass"] == "VC-1"
    assert lrv["crew"] == 2
    assert lrv["range_km"] == pytest.approx(88.0)
    assert lrv["e_km_kwh"] == pytest.approx(0.089)


def test_rvr_crawl_is_vc5(veh):
    """§1.0/§1.1: Mercury crawler rides the VC-5 platform chassis."""
    assert veh["RVR-CRAWL"]["vclass"] == "VC-5"
    assert veh["RVR-CRAWL"]["corridor_crr"] == pytest.approx(0.06)


def test_hop_p_a8_overlay(veh):
    """§1.5 + DECISIONS A8: HOP-P on ML-111 (355 s) — 8 t prop,
    1,778 m/s = 3481·ln(20/12) tank-full."""
    hop = veh["HOP-P"]
    assert hop["prop_cap_t"] == pytest.approx(8.0)
    assert hop["engine_id"] == "ML-111"
    assert hop["dv_ms"] == pytest.approx(1778.0)
    assert hop["abort_reserve_frac"] == pytest.approx(0.20)


def test_dir_t_titan_railroad(veh):
    """§1.7: DIR-T nets 10 t payload at 0.027 kWh/t-km."""
    dir_t = veh["DIR-T"]
    assert dir_t["payload_t"] == pytest.approx(10.0)
    assert dir_t["e_t_km_kwh"] == pytest.approx(0.027)
    assert dir_t["cd"] == pytest.approx(0.05)


def test_sub_t(veh):
    """§1.8: SUB-T on NUK-RTG-S ×3 ≈ 330 We, rated 300 m depth."""
    sub = veh["SUB-T"]
    assert sub["rtg_id"] == "NUK-RTG-S"
    assert sub["rtg_count"] == 3
    assert sub["power_we"] == pytest.approx(330.0)
    assert sub["depth_m"] == pytest.approx(300.0)


def test_cryo_e_speculative_100kwt(veh):
    """§1.8: CRYO-E at the 100 kWt core is T4 [SPECULATIVE]."""
    cryo = veh["CRYO-E"]
    assert cryo["power_kwt"] == pytest.approx(100.0)
    assert cryo["speculative"] is True
    assert cryo["rate_m_day"] == pytest.approx(100.0)


def test_whl_mesh(veh):
    """§1.2: WHL-MESH A_contact 0.05 m²/set (feeds V-1a), clearance
    0.35 m (feeds V-0a)."""
    whl = veh["WHL-MESH"]
    assert whl["a_contact_m2"] == pytest.approx(0.05)
    assert whl["clearance_m"] == pytest.approx(0.35)


def test_ctl_a3_grants_autonav(veh):
    """§1.9: CTL-A3 grants AUTONAV (0.5× v_max, 24/7)."""
    assert "AUTONAV" in veh["CTL-A3"]["grants"]
    assert veh["CTL-A3"]["mass_kg"] == pytest.approx(35.0)


def test_speculative_rows_exact(veh):
    """§1.6/§1.8: exactly AIR-T2, BARGE-T, ROV-E and CRYO-E (at
    100 kWt) carry the [SPECULATIVE] flag."""
    spec = {cid for cid, v in veh.items() if v.get("speculative")}
    assert spec == {"AIR-T2", "BARGE-T", "ROV-E", "CRYO-E"}
