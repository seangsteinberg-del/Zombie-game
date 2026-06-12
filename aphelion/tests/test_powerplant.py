"""10 §2.2 fixtures: V-9 methalox 0.83 kWh/kg, V-10 Titan O2-breather
1.04 kWh/kg, the per-kg UI ladder, usable pack fractions, the 273 K Li
charge gate, recharge paths, and the V-0d RVR-CRAWL / RVR-HAUL40
closure anchors."""

import pytest

from aphelion.sim.vehicles.locomotion import (
    TERRAIN, f_roll_n, p_drive_w)
from aphelion.sim.vehicles.powerplant import (
    OF_RATIO, PER_KG_KWH, RFC_KWH_E_PER_KG, STORAGE, SWAP_PALLET,
    breather_kwh, can_charge, methalox_kwh, methalox_split, o2_for_kwh,
    power_closure, reactants_for_kwh, umbilical_hours, usable_kwh)


def test_v9_methalox():
    """V-9: 1 kg CH4 + 4 kg O2 → 0.83 kWh_mech per kg reactants
    (η 0.30)."""
    assert methalox_kwh(5.0) == pytest.approx(4.15)
    assert reactants_for_kwh(0.83) == pytest.approx(1.0)
    assert OF_RATIO == pytest.approx(4.0)
    ch4, o2 = methalox_split(5.0)
    assert ch4 == pytest.approx(1.0)        # 1 kg CH4 burns with 4 kg O2
    assert o2 == pytest.approx(4.0)


def test_v10_breather_and_ladder():
    """V-10: 1 kg O2 → 1.04 kWh_mech; UI ladder ordering battery_t1 <
    methalox < titan_o2 < rfc."""
    assert breather_kwh(1.0) == pytest.approx(1.04)
    assert o2_for_kwh(1.04) == pytest.approx(1.0)
    assert (PER_KG_KWH["battery_t1"] < PER_KG_KWH["methalox"]
            < PER_KG_KWH["titan_o2"] < PER_KG_KWH["rfc"])


def test_storage_catalog_and_usable():
    """§2.2 / 09 rows: STO-LI 150, STO-SS 250, STO-LS 350 surge,
    STO-RFC 2.0 kWh_e/kg reactants; usable 0.85 / 0.9."""
    assert STORAGE["STO-LI"]["wh_kg"] == pytest.approx(150.0)
    assert STORAGE["STO-SS"]["wh_kg"] == pytest.approx(250.0)
    assert STORAGE["STO-LS"]["wh_kg"] == pytest.approx(350.0)
    assert STORAGE["STO-LS"]["surge"]
    assert STORAGE["STO-RFC"]["kwh_e_per_kg_reactants"] == \
        pytest.approx(2.0)
    assert RFC_KWH_E_PER_KG == pytest.approx(2.0)
    assert usable_kwh(100.0) == pytest.approx(85.0)
    assert usable_kwh(100.0, rechargeable=False) == pytest.approx(90.0)


def test_recharge_and_charge_gate():
    """§2.2 recharge: umbilical at pack max rate; 300 kWh / 1.2 t /
    10 min swap pallet; Li packs cannot charge < 273 K."""
    assert umbilical_hours(100.0, 10.0) == pytest.approx(10.0)
    assert SWAP_PALLET["kwh"] == pytest.approx(300.0)
    assert SWAP_PALLET["mass_t"] == pytest.approx(1.2)
    assert SWAP_PALLET["minutes"] == pytest.approx(10.0)
    assert SWAP_PALLET["where"] == "garage"
    assert can_charge(273.0)
    assert not can_charge(272.9)


def test_rvr_crawl_closure_anchor():
    """V-0d / 10 §1.1: Mercury crawler 60 t @ g 3.70, 3.7 km/h, η 0.72:
    compacted Crr 0.06 → ~19 kW drive, closes against 25 kWe; raw
    regolith Crr 0.15 → ~48 kW, out of budget — requires compacted
    terminator corridor."""
    v_ms = 3.7 / 3.6
    f_track = f_roll_n(TERRAIN["compacted"].crr, 60_000.0, 3.70)   # V-1
    p_track = p_drive_w(f_track, v_ms)                             # V-4
    assert p_track == pytest.approx(19_000.0, abs=1_500.0)
    ok, margin = power_closure(p_track, 2_000.0, 25_000.0)
    assert ok and margin > 0.0

    f_raw = f_roll_n(TERRAIN["regolith"].crr, 60_000.0, 3.70)
    p_raw = p_drive_w(f_raw, v_ms)
    assert p_raw == pytest.approx(48_000.0, abs=3_000.0)
    ok_raw, margin_raw = power_closure(p_raw, 2_000.0, 25_000.0)
    assert not ok_raw and margin_raw < 0.0


def test_rvr_haul40_tankage_anchor():
    """V-9 / 10 §1.1: RVR-HAUL40 9.6 kWh/km full × 100 km = 960 kWh →
    ~1.2 t reactants per 100 km."""
    assert reactants_for_kwh(9.6 * 100.0) == \
        pytest.approx(1_157.0, rel=0.05)
