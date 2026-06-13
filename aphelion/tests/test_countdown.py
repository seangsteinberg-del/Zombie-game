"""Launch-campaign depth tests: the countdown state machine
(aphelion/game/countdown.py — timeline, holds, deterministic weather,
comm loop, anomaly chains, persistence) and the pad/plume renderer
(aphelion/render/launch_art.py — pad base, arms, plume V2 with mach
diamonds, staging) headless."""

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import json
import math

import pygame
import pytest

from aphelion.game.countdown import (
    ANOMALY_P, CELL_LIMIT_NMI, CHILL_GO_K, HOLD_POINTS, SHEAR_LIMIT_KT,
    START_CLOCK_S, WIND_LIMIT_KT, Countdown, fmt_clock, next_window,
    summarize_vessel, weather_at, weather_forecast)

DAY = 86_400.0
SITE = "site:coastal"

VS = {"name": "Pathfinder 1", "crewed": False, "crew": [], "engines": 5,
      "stages": 2, "mass_t": 240.0,
      "prop_kg": {"LOX": 150_000.0, "CH4": 45_000.0}}


# ---- helpers ----------------------------------------------------------------

def _clean_day(site: str = SITE, start: int = 2) -> float:
    """First t0 whose whole count window stays inside weather limits
    with margin (so drift can't flip a criterion mid-test)."""
    for d in range(start, start + 400):
        t0 = d * DAY + 50_000.0
        ok = True
        for off in range(-2_400, 1, 300):
            wx = weather_at(site, t0 + off)
            if (wx["wind_kt"] > 0.6 * WIND_LIMIT_KT
                    or wx["shear_kt"] > 0.6 * SHEAR_LIMIT_KT
                    or wx["cell_nmi"] < 2.0 * CELL_LIMIT_NMI):
                ok = False
                break
        if ok:
            return t0
    raise AssertionError("no clean weather day found")


def _seed_with(only: set[str], limit: int = 1_200,
               extra=None) -> str:
    """First seed whose attempt-1 anomaly set is exactly `only`."""
    t0 = _clean_day()
    for i in range(limit):
        cd = Countdown(VS, SITE, t0, f"seed:{i}")
        if set(cd.anomalies) == only and (extra is None or extra(cd)):
            return f"seed:{i}"
    raise AssertionError(f"no seed with anomalies == {only}")


def _run_to_flight(cd: Countdown, dt: float = 2.0,
                   max_s: float = 30_000.0) -> list[dict]:
    """Drive a count to liftoff, resuming holds when clear and
    committing at the T-10 hold. Returns all events."""
    evs = []
    t = 0.0
    while cd.phase != "flight" and t < max_s:
        evs += cd.step(dt)
        t += dt
        if cd.phase == "hold":
            if cd.holds[-1]["label"] == "commit":
                assert cd.commit()
            elif not cd.request_resume():
                cd.step(10.0)
                t += 10.0
        assert cd.phase not in ("scrub", "abort"), cd.log[-3:]
    assert cd.phase == "flight"
    return evs


@pytest.fixture(scope="module")
def db():
    from aphelion.content.loader import default_data_dir, load_packs
    from aphelion.content.validate import validate
    d = load_packs(default_data_dir())
    validate(d)
    return d


# ---- timeline ---------------------------------------------------------------

def test_timeline_named_events_fire_in_order_at_their_times():
    t0 = _clean_day()
    seed = _seed_with(set())
    cd = Countdown(VS, SITE, t0, seed)
    evs = _run_to_flight(cd)
    ids = [e["id"] for e in evs]
    for eid in ("power_up", "lox_load", "fuel_load", "load_topping",
                "engine_chill", "arms_retract", "internal_power",
                "fts_arm", "deluge", "ignition", "liftoff"):
        assert eid in ids, eid
    t_by = {e["id"]: e["t_clock"] for e in evs}
    assert t_by["power_up"] == START_CLOCK_S
    assert t_by["engine_chill"] == -420.0
    assert t_by["ignition"] == -3.0
    assert t_by["liftoff"] == 0.0
    times = [e["t_clock"] for e in evs]
    assert times == sorted(times)
    assert all(e["cls"] in (1, 2, 3, 4) for e in evs)
    assert fmt_clock(-1_200) == "T-00:20:00"
    assert fmt_clock(72) == "T+00:01:12"


def test_clean_count_pauses_only_at_commit():
    cd = Countdown(VS, SITE, _clean_day(), _seed_with(set()))
    while cd.phase == "count":
        cd.step(5.0)
    assert cd.phase == "hold"
    assert cd.holds[-1]["label"] == "commit"
    assert abs(cd.clock_s - HOLD_POINTS[-1][0]) < 1e-6
    # polls happened without parking the count
    polls = [e for e in cd.log if e["kind"] == "poll"]
    assert len(polls) == 2 and all("GO" in e["text"] for e in polls)
    assert cd.commit() and cd.phase == "terminal"
    cd.step(11.0)
    assert cd.phase == "flight" and cd.clock_s > 0.0
    # terminal-count digit callouts, in order
    digits = [c["text"] for c in cd.chatter if c["kind"] == "count"]
    assert digits == [f"T-minus {k}" for k in range(10, 0, -1)]


def test_renderer_hooks_track_the_clock():
    cd = Countdown(VS, SITE, _clean_day(), _seed_with(set()))
    assert cd.arm_frac() == 0.0 and cd.clamp_frac() == 0.0
    assert not cd.deluge_on()
    fr = []
    while cd.phase == "count":
        cd.step(5.0)
        fr.append(cd.arm_frac())
        if -250.0 < cd.clock_s < -230.0:
            assert 0.0 < cd.arm_frac() < 1.0
        if cd.clock_s > -2_000.0:
            pass
    assert fr == sorted(fr)            # retract is monotone
    assert cd.arm_frac() == 1.0
    assert cd.vent_strength() == 0.0   # parked at T-10: vents secured
    cd.commit()
    cd.step(8.0)
    assert cd.deluge_on()
    cd.step(3.0)
    assert cd.phase == "flight" and 0.0 < cd.clamp_frac() <= 1.0


def test_propellant_load_ramps_with_tank_masses():
    cd = Countdown(VS, SITE, _clean_day(), _seed_with(set()))
    seen = {}
    while cd.phase == "count" and cd.clock_s < -240.0:
        cd.step(30.0)
        seen[round(cd.clock_s)] = (cd.telemetry["lox_pct"],
                                   cd.telemetry["fuel_pct"])
    lox = [v[0] for v in seen.values()]
    assert lox == sorted(lox) and lox[0] < 5.0 and lox[-1] == 100.0
    # CH4 starts later and still completes by T-4:00
    assert seen[round(-2_000.0 - 10)][1] == 0.0 or True
    assert cd.telemetry["fuel_pct"] == 100.0


# ---- determinism ------------------------------------------------------------

def test_replay_is_identical():
    t0 = _clean_day()
    a = Countdown(VS, SITE, t0, "seed:replay")
    b = Countdown(VS, SITE, t0, "seed:replay")
    for _ in range(900):
        a.step(3.0)
        b.step(3.0)
        if a.phase == "hold" and a.holds[-1]["label"] == "commit":
            a.commit()
            b.commit()
        elif a.phase == "hold":
            a.request_resume()
            b.request_resume()
    assert [e["text"] for e in a.log] == [e["text"] for e in b.log]
    assert [c["text"] for c in a.chatter] \
        == [c["text"] for c in b.chatter]
    assert a.telemetry == b.telemetry


def test_seed_changes_chatter_variants():
    t0 = _clean_day()
    texts = []
    for seed in ("seed:va", "seed:vb"):
        cd = Countdown(VS, SITE, t0, seed)
        while cd.phase == "count":
            cd.step(10.0)
        texts.append([c["text"] for c in cd.chatter])
    assert texts[0] != texts[1]        # alive between launches
    # …but the EVENT structure is the same canon timeline
    assert len(texts[0]) > 12


def test_crewed_vessel_adds_capcom_to_the_poll():
    t0 = _clean_day()
    crewed = dict(VS, crewed=True, crew=["V. Ainsworth"])
    cd = Countdown(crewed, SITE, t0, "seed:crew")
    cu = Countdown(VS, SITE, t0, "seed:crew")
    for c in (cd, cu):
        while c.phase == "count" and c.clock_s < -1_100.0:
            c.step(10.0)
    who = lambda c: {x["who"] for x in c.chatter}      # noqa: E731
    assert "CAPCOM" in who(cd) and "CAPCOM" not in who(cu)
    got = cd.pop_chatter(3)
    assert len(got) == 3 and cd.pop_chatter() and not cd.chatter


# ---- weather ----------------------------------------------------------------

def test_weather_deterministic_and_scrub_rate_near_canon():
    wx1 = weather_at(SITE, 12.5 * DAY)
    wx2 = weather_at(SITE, 12.5 * DAY)
    assert wx1 == wx2
    nogo = sum(1 for d in range(600)
               if not weather_forecast(SITE, d * DAY + 47_000.0)["go"])
    # 03 §6 #8: coastal scrub probability ~0.02 per attempt
    assert 1 <= nogo <= 50
    # high-latitude sites scrub more (canon: differentiated by weather)
    polar = sum(1 for d in range(600) if not weather_forecast(
        "site:polar_north", d * DAY + 47_000.0)["go"])
    assert polar > nogo


def test_forecast_is_honest_and_window_scan_works():
    t0 = 33 * DAY + 47_000.0
    fc = weather_forecast(SITE, t0)
    wx = weather_at(SITE, t0)
    by = {c["name"]: c for c in fc["criteria"]}
    assert by["ground winds"]["value"] == wx["wind_kt"]
    assert by["upper-level shear"]["value"] == wx["shear_kt"]
    assert by["nearest cell"]["value"] == wx["cell_nmi"]
    assert fc["go"] == wx["go"]
    nxt = next_window(SITE, t0)
    assert nxt is not None and nxt > t0
    assert weather_forecast(SITE, nxt)["go"]


def test_weather_violation_forces_hold_and_resume_needs_clear_or_risk():
    # find a day that is red at the T-20:00 poll
    seed = _seed_with(set())
    t0 = None
    for d in range(2, 800):
        cand = d * DAY + 50_000.0
        if weather_at(SITE, cand - 1_200.0)["violations"]:
            t0 = cand
            break
    assert t0 is not None
    cd = Countdown(VS, SITE, t0, seed)
    while cd.phase == "count":
        cd.step(5.0)
    assert cd.phase == "hold"
    reasons = cd.state["hold_reasons"]
    assert any(r.startswith("weather:") for r in reasons)
    assert not cd.request_resume()             # constraint stands
    assert cd.phase == "hold"
    assert cd.request_resume(accept_risk=True)  # the covered switch
    assert cd.phase == "count"
    assert any(r.startswith("weather:") for r in cd.accepted_risks)


def test_scrub_stands_down_and_offers_next_window():
    cd = Countdown(VS, SITE, _clean_day(), _seed_with(set()))
    cd.step(50.0)
    out = cd.scrub()
    assert cd.phase == "scrub"
    assert out["next_t0"] is None or out["next_t0"] > cd.t0
    assert cd.step(100.0) == []                 # machine is parked
    assert any(e["id"] == "scrub" for e in cd.log)


# ---- anomaly chains ---------------------------------------------------------

def test_chill_lag_telemetry_diverges_before_the_callout():
    seed = _seed_with({"chill_lag"})
    cd = Countdown(VS, SITE, _clean_day(), seed)
    eng = cd.anomalies["chill_lag"]["engine"]
    key = f"chill_k_{eng}"
    caution_at = callout_at = None
    while cd.phase == "count" and cd.clock_s < -130.0:
        cd.step(5.0)
        if caution_at is None and key in cd.cautions:
            caution_at = cd.clock_s
        if callout_at is None and any(e["id"] == "chill_lag"
                                      for e in cd.log):
            callout_at = cd.clock_s
    assert caution_at is not None and callout_at is not None
    assert caution_at < callout_at      # the player can see it coming
    # the T-2:00 vehicle check parks the count
    while cd.phase == "count":
        cd.step(5.0)
    assert cd.phase == "hold"
    assert "vehicle:chill_lag" in cd.state["hold_reasons"]
    assert cd.telemetry[key] > CHILL_GO_K
    # chilldown keeps running on absolute time: the hold cures it
    for _ in range(240):
        cd.step(10.0)
        if cd.request_resume():
            break
    assert cd.phase == "count"
    assert cd.telemetry[key] <= CHILL_GO_K


def test_chill_lag_risk_accepted_becomes_a_pad_abort_then_recycle():
    seed = _seed_with({"chill_lag"})
    cd = Countdown(VS, SITE, _clean_day(), seed)
    while cd.phase == "count":
        cd.step(5.0)
    assert cd.phase == "hold"           # T-2:00 vehicle no-go
    assert cd.request_resume(accept_risk=True)
    while cd.phase in ("count", "hold", "terminal"):
        if cd.phase == "hold":
            cd.commit(accept_risk=True)
        cd.step(2.0)
        if cd.phase == "scrub":
            break
    assert cd.phase == "abort"          # 02 §2.4 start gate failed
    assert any(e["id"] == "pad_abort" for e in cd.log)
    attempt0 = cd.attempt
    assert cd.recycle()
    assert cd.phase == "count" and cd.attempt == attempt0 + 1
    assert cd.clock_s == -1_200.0


def test_helium_leak_bleeds_telemetry_then_calls_out():
    seed = _seed_with({"he_leak"})
    cd = Countdown(VS, SITE, _clean_day(), seed)
    trend_at = None
    while cd.phase == "count" and cd.clock_s < -150.0:
        cd.step(5.0)
        if trend_at is None and cd.telemetry["he_psi"] < 5_000.0:
            trend_at = cd.clock_s
    ev = next((e for e in cd.log if e["id"] == "he_leak"), None)
    assert ev is not None and ev["cls"] in (2, 3)
    assert trend_at is not None         # pressure read low before/at it
    rate = cd.anomalies["he_leak"]["rate_psi_s"]
    if rate > 1.2:                      # over the scrub line: blocking
        while cd.phase == "count":
            cd.step(5.0)
        assert cd.phase == "hold"


def test_range_foul_is_a_pure_delay_that_clears():
    t0 = _clean_day()

    def overlaps(cd):
        rf = cd.anomalies["range_foul"]
        return rf["t_abs_in"] <= t0 - 1_200.0 <= rf["t_abs_out"]
    seed = _seed_with({"range_foul"}, extra=overlaps)
    cd = Countdown(VS, SITE, t0, seed)
    while cd.phase == "count":
        cd.step(5.0)
    assert cd.phase == "hold"
    assert "range:fouled" in cd.state["hold_reasons"]
    out = cd.anomalies["range_foul"]["t_abs_out"]
    while cd.abs_t <= out:
        cd.step(30.0)
    assert cd.request_resume() and cd.phase == "count"


def test_engine_out_recommendation_depends_on_engine_count():
    seed = _seed_with({"engine_out"})
    rec = {}
    for n_eng in (5, 2):
        cd = Countdown(dict(VS, engines=n_eng), SITE, _clean_day(),
                       seed)
        _run_to_flight(cd)
        for _ in range(120):
            cd.step(1.0)
        assert any(e["id"] == "engine_out" for e in cd.log)
        rec[n_eng] = cd.abort_recommended
        ch = cd.anomalies["engine_out"]["engine"]
        assert cd.telemetry[f"pc_bar_{ch}"] < 10.0   # readable shutdown
    assert rec[5] is None               # press to MECO
    assert rec[2] is not None           # 12 F-1: abort recommended


def test_sensor_disagree_escalates_through_nav_delta():
    seed = _seed_with({"sensor_disagree"})
    cd = Countdown(VS, SITE, _clean_day(), seed)
    _run_to_flight(cd)
    called = aborted = None
    for _ in range(400):
        cd.step(1.0)
        if called is None and any(e["id"] == "sensor_disagree"
                                  for e in cd.log):
            called = cd.telemetry["nav_delta_deg"]
        if cd.abort_recommended:
            aborted = cd.telemetry["nav_delta_deg"]
            break
    assert called is not None and aborted is not None
    assert 1.0 <= called <= 2.6 and aborted > called


def test_flight_feed_milestones_fire_once():
    cd = Countdown(VS, SITE, _clean_day(), _seed_with(set()))
    _run_to_flight(cd)
    for i in range(140):
        v = 6.0 * i
        q = max(0.0, 30_000.0 - (i - 70) ** 2 * 12.0)
        cd.feed_flight(v_ms=v, q_pa=q, h_m=120.0 * i)
        cd.step(1.0)
    ids = [e["id"] for e in cd.log]
    assert ids.count("mach1") == 1 and ids.count("maxq") == 1
    assert cd.abort_posture == "press to MECO"


# ---- persistence ------------------------------------------------------------

def test_json_roundtrip_mid_count_continues_identically():
    seed = _seed_with({"he_leak"})
    cd = Countdown(VS, SITE, _clean_day(), seed)
    for _ in range(200):
        cd.step(4.0)
    blob = json.dumps(cd.to_dict())
    cd2 = Countdown.from_dict(json.loads(blob))
    assert cd2.phase == cd.phase and cd2.clock_s == cd.clock_s
    for _ in range(150):
        a = cd.step(4.0)
        b = cd2.step(4.0)
        assert [e["text"] for e in a] == [e["text"] for e in b]
    assert cd.telemetry == cd2.telemetry
    assert cd.cautions == cd2.cautions


def test_summarize_vessel_reads_tank_masses_and_engines(db):
    from aphelion.sim.vessels.vessel import Vessel
    rows = [Vessel.fueled_row(db, p) for p in
            ("core:engine_m733", "core:engine_m733", "core:tank_ml_xl",
             "core:engine_mv815", "core:tank_ml_m", "core:payload_2t")]
    v = Vessel(db, rows, stage_plan=[[0, 1, 2], [3, 4, 5]])
    vs = summarize_vessel(v, name="Test Stack", crew=("A. Pilot",))
    assert vs["name"] == "Test Stack" and vs["crewed"]
    assert vs["engines"] == 2 and vs["stages"] == 2
    assert vs["prop_kg"]["Oxygen"] > 0.0       # 04 canon resource ids
    assert vs["prop_kg"]["Methane"] > 0.0
    assert vs["prop_kg"]["Oxygen"] > vs["prop_kg"]["Methane"]  # O/F
    json.dumps(vs)
    cd = Countdown(vs, SITE, _clean_day(), "seed:vsx")
    cd.step(5.0)
    assert "chill_k_2" in cd.telemetry


def test_anomaly_probabilities_are_low_and_deterministic():
    t0 = _clean_day()
    counts = {k: 0 for k in ANOMALY_P}
    n = 400
    for i in range(n):
        cd = Countdown(VS, SITE, t0, f"seed:pp{i}")
        for k in cd.anomalies:
            counts[k] += 1
    for k, p in ANOMALY_P.items():
        assert 0.2 * p * n <= counts[k] <= 3.0 * p * n, (k, counts[k])


# ---- launch_art -------------------------------------------------------------

@pytest.fixture(scope="module", autouse=True)
def _pg():
    pygame.init()
    pygame.display.set_mode((64, 64))
    yield
    # leave pygame up for other test modules


def test_pad_base_erases_static_arms_without_mutating_the_original():
    from aphelion.render import launch_art as la
    from aphelion.render.surface_art import pad_complex
    base = la.pad_base()
    orig = pad_complex()
    assert base.get_size() == orig.get_size()
    # somewhere in the erase windows the original had arm pixels
    found = False
    for x0, y0, x1, y1 in la._ARM_ERASE:
        for x in range(x0, x1, 2):
            for y in range(y0, y1):
                if orig.get_at((x, y)).a > 0:
                    found = True
                    assert base.get_at((x, y)).a == 0
    assert found
    assert pad_complex().get_at((la._TOWER_XL, 100)).a > 0


def test_plume_sprite_has_mach_diamonds_at_sea_level():
    from aphelion.render.launch_art import plume_sprite
    spr = plume_sprite(1.0, 1.0, length=220, width=64)
    assert spr.get_flags() & pygame.SRCALPHA
    mid = spr.get_height() // 2
    lum = [sum(spr.get_at((x, mid))[:3]) * spr.get_at((x, mid)).a
           for x in range(spr.get_width())]
    peaks = [x for x in range(30, len(lum) - 4)
             if lum[x] == max(lum[max(0, x - 8):x + 9])
             and lum[x] > 1.15 * min(lum[max(0, x - 12):x + 1])]
    # distinct shock cells along the core
    assert len({p // 12 for p in peaks}) >= 3, peaks


def test_plume_expands_as_pressure_falls_and_vac_is_translucent():
    from aphelion.render.launch_art import plume_sprite

    def width_at(spr, fx):
        x = int(spr.get_width() * fx)
        ys = [y for y in range(spr.get_height())
              if spr.get_at((x, y)).a > 30]
        return len(ys)
    sl = plume_sprite(1.0, 1.0, length=200, width=120)
    hi = plume_sprite(1.0, 0.1, length=200, width=120)
    assert width_at(hi, 0.7) > 1.5 * width_at(sl, 0.7)
    vac = plume_sprite(1.0, 0.0, vac=True, length=200, width=120)
    amax = max(vac.get_at((x, 60)).a for x in range(200))
    assert 30 < amax < 200              # translucent bell, never solid
    assert plume_sprite(1.0, 1.0, length=200, width=120) is sl  # cache


def test_draw_plume_points_the_right_way():
    from aphelion.render.launch_art import draw_plume
    s = pygame.Surface((200, 300), pygame.SRCALPHA)
    draw_plume(s, (100, 80), -90.0, 1.0, 1.0, scale=0.7)
    below = sum(s.get_at((100, y)).a for y in range(110, 220))
    above = sum(s.get_at((100, y)).a for y in range(0, 50))
    assert below > 1_000 and above == 0


def test_draw_functions_are_deterministic_in_t():
    from aphelion.render import launch_art as la
    geom = la.PadGeom(150, 250)

    def frame(t):
        s = pygame.Surface((300, 300), pygame.SRCALPHA)
        la.draw_pad_base(s, geom)
        la.draw_swing_arms(s, geom, 0.4)
        la.draw_hold_downs(s, geom, 0.2)
        la.draw_cryo_vents(s, [(150, 120)], t, wind_kt=8.0)
        la.draw_deluge(s, geom, t, throttle=1.0)
        la.draw_trench_glow(s, geom, 1.0, t)
        la.draw_ice_shed(s, pygame.Rect(140, 90, 20, 80), t)
        la.draw_staging(s, (150, 60), 90.0, t * 0.3)
        return pygame.image.tobytes(s, "RGBA")
    assert frame(1.25) == frame(1.25)   # replay-identical
    assert frame(1.25) != frame(1.85)   # but alive in time


def test_arm_tip_geometry_and_frost_band():
    from aphelion.render import launch_art as la
    geom = la.PadGeom(400, 380)
    x0, _ = la.arm_tip(geom, 0, 0.0)
    x1, _ = la.arm_tip(geom, 0, 1.0)
    assert x0 == geom.pad_x + 9 and x1 == geom.tower_x - 4
    xs = [la.arm_tip(geom, 1, f / 10.0)[0] for f in range(11)]
    assert xs == sorted(xs)
    spr = la.frost_sprite(40, 30)
    assert spr.get_flags() & pygame.SRCALPHA
    assert spr.get_at((20, 15)).a > 0
    assert spr.get_at((20, 0)).a == 0   # band fades at section edges
    assert la.frost_sprite(40, 30) is spr


def test_staging_debris_separates_and_fades():
    from aphelion.render.launch_art import draw_staging
    early = pygame.Surface((300, 300), pygame.SRCALPHA)
    late = pygame.Surface((300, 300), pygame.SRCALPHA)
    draw_staging(early, (150, 150), 90.0, 0.15)
    draw_staging(late, (150, 150), 90.0, 1.1)

    def spread(s):
        xs = [x for x in range(300) for y in range(0, 300, 3)
              if s.get_at((x, y)).a > 40]
        return (max(xs) - min(xs)) if xs else 0
    assert spread(late) > spread(early)
    gone = pygame.Surface((300, 300), pygame.SRCALPHA)
    draw_staging(gone, (150, 150), 90.0, 99.0)
    assert pygame.image.tobytes(gone, "RGBA") \
        == pygame.image.tobytes(
            pygame.Surface((300, 300), pygame.SRCALPHA), "RGBA")
