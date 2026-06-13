"""V5 vehicle entity layer: build bills off real shelves, V-5 drive
energy (LRV anchor), V-24 wear accrual, RTG never-strand, brick events,
save round-trip."""

import pytest

from aphelion.game.motorpool import (
    GroundVehicle, build_bill_t, can_build, debit_build, row_stats,
    service_bill_t)

G_MOON = 1.62


class _Buf:
    def __init__(self, level):
        self.level = level


class _Net:
    def __init__(self, **kg):
        self.buffers = {k: _Buf(v) for k, v in kg.items()}


class _Base:
    def __init__(self, **kg):
        self.net = _Net(**kg)


def _lrv() -> GroundVehicle:
    gv = GroundVehicle(vid=1, catalog_id="core:rvr_lrv", name="LRV-1",
                       body="core:moon", site_id="site:peary",
                       pack_kwh=8.7, energy_kwh=7.83, rtg_we=0.0)
    gv.dry_t = 0.21
    gv.cargo_t = 0.46                  # crew + samples -> 670 kg gross
    return gv


def test_lrv_drive_energy_anchor():
    """V-5 anchor: 670 kg gross, Moon regolith, 8 km/h, 150 W hotel ->
    ~0.089 kWh/km (the 10 §2.1 LRV calibration row)."""
    gv = _lrv()
    assert gv.mass_t == pytest.approx(0.67, abs=0.01)
    e = gv.e_km(G_MOON, "regolith", v_kmh=8.0, hotel_kw=0.15)
    assert e == pytest.approx(0.089, abs=0.008)
    e0 = gv.energy_kwh
    assert gv.drive(10.0, G_MOON, "regolith", v_kmh=8.0, hotel_kw=0.15)
    assert e0 - gv.energy_kwh == pytest.approx(10.0 * e, rel=1e-6)
    assert gv.odo_km == 10.0


def test_wear_accrues_per_v24a():
    """100 km wheels on Moon regolith = 0.6% condition (V-24a x dust)."""
    gv = _lrv()
    gv.energy_kwh = 99.0
    gv.drive(100.0, G_MOON, "regolith", dust_body="moon")
    assert 1.0 - gv.cond == pytest.approx(0.006, rel=1e-6)


def test_battery_strands_but_rtg_does_not():
    gv = _lrv()
    gv.energy_kwh = 0.05
    assert not gv.drive(10.0, G_MOON)          # refused, nothing spent
    assert gv.odo_km == 0.0
    gv.rtg_we = 110.0
    assert gv.drive(10.0, G_MOON)              # RTG: range unlimited


def test_brick_event_30pct():
    gv = _lrv()
    gv.brick()
    assert gv.pack_kwh == pytest.approx(8.7 * 0.7)
    assert gv.bricked_events == 1


def test_build_bill_and_shelf_gate():
    bill = build_bill_t(0.21)                  # LRV-class
    assert bill["MachineParts"] == pytest.approx(0.063)
    assert bill["Electronics"] == pytest.approx(0.0105)
    rich = _Base(MachineParts=80_000.0, Electronics=20_000.0)
    ok, _ = can_build(rich, 0.21)
    assert ok
    debit_build(rich, 0.21)
    assert rich.net.buffers["MachineParts"].level == pytest.approx(
        80_000.0 - 63.0)
    poor = _Base(MachineParts=10.0, Electronics=20_000.0)
    ok, why = can_build(poor, 0.21)
    assert not ok and "MachineParts" in why


def test_service_bill_scales_with_missing_condition():
    full = service_bill_t(22.0, 0.0)           # HAUL40 fully worn
    assert full["MachineParts"] == pytest.approx(6.6)
    assert full["Electronics"] == pytest.approx(1.1)
    half = service_bill_t(22.0, 0.5)
    assert half["MachineParts"] == pytest.approx(3.3)


def test_save_roundtrip():
    gv = _lrv()
    gv.drive(5.0, G_MOON)
    gv2 = GroundVehicle.from_dict(gv.to_dict())
    assert gv2.to_dict() == gv.to_dict()


def test_row_stats_parses_catalog_idioms():
    st = row_stats({"dry_t": 3.0, "power": "STO-SS 100 kWh (0.4 t)",
                    "crew": 2})
    assert st["pack_kwh"] == pytest.approx(100.0)
    assert st["crewed"] and st["rtg_we"] == 0.0
    st2 = row_stats({"dry_t": 1.0, "power": "NUK-RTG-M + 2 kWh buffer"})
    assert st2["rtg_we"] > 0.0
