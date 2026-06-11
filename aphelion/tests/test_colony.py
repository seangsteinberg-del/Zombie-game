"""Chunk E (depth update): the colony — base art, residents with real
effects, module toggling, alerts, day/night solar scheduling, batteries,
and the refuel-from-base loop that finally closes ISRU."""

import os

import pytest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from aphelion.core.rng import RngRegistry
from aphelion.game.basebuild import CATALOG, add_module, starter_network
from aphelion.game.crew import CrewMember
from aphelion.game.sites import SITES
from aphelion.main import BaseSite
from aphelion.render.base_art import (module_sprite, sky_strip,
                                      terrain_strip, walker_sprite)
from aphelion.sim.economy import Program
from aphelion.sim.research import ResearchState

DAY = 86_400.0


def _base(site_id="site:peary"):
    return BaseSite("T Base", 0.0, RngRegistry(7), site_id=site_id)


def test_every_catalog_module_has_art():
    pygame.init()
    for key in CATALOG:
        spr = module_sprite(key)
        assert spr.get_width() > 0
        # the sprite actually draws something
        assert pygame.transform.average_color(spr)[3] > 0 or any(
            spr.get_at((x, y)).a > 0
            for x in range(0, spr.get_width(), 7)
            for y in range(0, spr.get_height(), 7))


def test_terrain_and_sky_strips():
    pygame.init()
    for kind in ("psr_ice", "mars_ice", "aerostat", "methane_lake",
                 "ice_burrow"):
        surf, ridge = terrain_strip("site:x" + kind, kind, 320, 120)
        assert surf.get_size() == (320, 120) and len(ridge) == 320
        sky_day = sky_strip(kind, 64, 64, 1.0)
        sky_night = sky_strip(kind, 64, 64, 0.0)
        assert sky_day.get_at((32, 60)) != sky_night.get_at((32, 60)) or \
            kind in ("psr_ice", "ice_burrow")          # airless stays dark
    w = walker_sprite("V. Ainsworth", 0)
    assert w.get_width() > 0


def test_resident_engineer_speeds_repairs_and_labor():
    b = _base()
    crew = {"J": CrewMember("J", "engineer", 2)}
    b.crew = ["J"]
    assert b.engineer_skill(crew) == 2
    assert b.repair_turnaround(crew) < BaseSite.REPAIR_TURNAROUND
    b.build("drill_ice", 0.0, ResearchState(), Program(funds=1e9))
    b.apply_crew_effects(crew)
    drill = next(m for m in b.net.modules
                 if m.module_id.startswith("drill_ice"))
    assert drill.f_labor == pytest.approx(1.10)


def test_toggle_module_off_and_on():
    b = _base()
    sid = b.net.modules[0].module_id
    assert "shut down" in b.toggle_module(sid, 0.0)
    assert b.net.modules[0].state == "OFF"
    assert "ONLINE" in b.toggle_module(sid, 1.0)


def test_daynight_scheduling_kills_solar_at_night():
    b = _base("site:jezero")               # Mars: 88,775 s day
    day_s = SITES["site:jezero"]["day_s"]
    b.advance(0.25 * day_s)                # mid-day
    assert b.daylight(0.25 * day_s) == 1.0
    b.advance(0.75 * day_s)                # mid-night
    assert b.daylight(0.75 * day_s) == 0.0
    sol = next(m for m in b.net.modules
               if m.module_id.startswith("solar_array"))
    assert sol.state == "OFF"              # terminator boundary fired
    b.advance(1.1 * day_s)                 # sunrise again
    assert sol.state == "RUNNING"


def test_battery_buffer_exists_and_pack_extends_it():
    b = _base()
    bat = b.net.buffers["Battery"]
    cap0 = bat.capacity
    ok, msg = b.build("battery_pack", 0.0, ResearchState(),
                      Program(funds=1e9))
    assert ok, msg
    assert b.net.buffers["Battery"].capacity == pytest.approx(cap0 + 400.0)


def test_alert_reports_failures():
    b = _base()
    b.build("drill_ice", 0.0, ResearchState(), Program(funds=1e9))
    drill = next(m for m in b.net.modules
                 if m.module_id.startswith("drill_ice"))
    drill.state = "FAILED"
    assert "FAILED" in (b.alert(0.0) or "")


def test_event_log_is_bounded():
    from aphelion.sim.ledger.network import LedgerEvent
    b = _base()
    b.events = [LedgerEvent(0.0, "x", "y")] * 500
    b.advance(1.0)
    assert len(b.events) <= BaseSite.LOG_CAP


def test_founding_pour_and_refuel_roundtrip():
    # the ISRU loop closes: banked oxygen flows back into a lander's tanks
    b = _base()
    b.net.buffers["Oxygen"].level = 20_000.0
    b.net.buffers["Methane"].level = 6_000.0
    from aphelion.content.loader import default_data_dir, load_packs
    from aphelion.sim.vessels.vessel import Vessel
    db = load_packs(default_data_dir())
    row = Vessel.fueled_row(db, "core:tank_ml_m")
    for res in row.fill:
        row.fill[res] *= 0.1               # nearly dry tank
    v = Vessel(db, [row], stage_plan=[[0]])
    tank = v.part(row)["tank"]
    cap_kg = tank["capacity_t"] * 1_000.0
    moved = 0.0
    for res, share in tank["mixture"].items():
        buf = b.net.buffers.get(res)
        if buf is None:
            continue
        room = cap_kg * share - row.fill.get(res, 0.0)
        take = min(room, buf.level)
        buf.level -= take
        row.fill[res] = row.fill.get(res, 0.0) + take
        moved += take
    assert moved > 1_000.0
    assert b.net.buffers["Oxygen"].level < 20_000.0
    assert sum(row.fill.values()) == pytest.approx(cap_kg, rel=0.01)
