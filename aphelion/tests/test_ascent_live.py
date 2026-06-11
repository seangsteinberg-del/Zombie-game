"""Live (interactive) ascent: the PROG autopilot must reach orbit inside
the canon loss band on the proven two-stage test vehicle; manual mode
must obey the player (no auto-staging, stick pitch); pad clamps hold."""

import math
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pytest

from aphelion.content.loader import default_data_dir, load_packs
from aphelion.content.validate import validate
from aphelion.core.units import SIM_DT
from aphelion.sim.flight.ascent_live import LiveAscent
from aphelion.sim.orbits.ephemeris import load_solar_system
from aphelion.sim.vessels.vessel import Vessel

MU_E = 3.986004418e14
R_E = 6.371e6
T_ROT = 86_164.1


@pytest.fixture(scope="module")
def db():
    d = load_packs(default_data_dir())
    validate(d)
    return d


def _two_stage(db) -> Vessel:
    rows, plan = [], []
    s1 = ["core:engine_m733", "core:engine_m733", "core:tank_ml_xl"]
    s2 = ["core:engine_mv815", "core:tank_ml_m", "core:payload_2t"]
    for stage in (s1, s2):
        idxs = []
        for pid in stage:
            idxs.append(len(rows))
            rows.append(Vessel.fueled_row(db, pid))
        plan.append(idxs)
    return Vessel(db, rows, stage_plan=plan, cd_a_m2=3.2)


def _run(live: LiveAscent, seconds: float) -> None:
    for _ in range(int(seconds / SIM_DT)):
        live.step(SIM_DT)
        if live.outcome is not None:
            return


def test_pad_clamp_before_ignition(db):
    live = LiveAscent.from_pad(_two_stage(db), "core:earth", MU_E, R_E, T_ROT)
    _run(live, 5.0)
    assert live.h == pytest.approx(0.0, abs=1.0)
    assert live.outcome is None


def test_prog_autopilot_reaches_orbit_in_canon_band(db):
    live = LiveAscent.from_pad(_two_stage(db), "core:earth", MU_E, R_E, T_ROT)
    live.ignite()
    _run(live, 2_500.0)
    assert live.outcome == "orbit"
    assert live.peri_km > 120.0
    # canon integrated band (01 section 3.10 as amended): 8,700-9,600
    assert 8_500.0 < live.dv_int < 9_700.0
    assert live.dv_remaining == pytest.approx(
        live.total_dv - live.dv_int, abs=1.0)


def test_manual_mode_does_not_autostage(db):
    live = LiveAscent.from_pad(_two_stage(db), "core:earth", MU_E, R_E, T_ROT)
    live.prog = False
    live.pitch_manual_deg = 90.0
    live.ignite()
    _run(live, 400.0)
    # stage 1 burns out; without SPACE the vehicle must NOT have staged
    assert live.stages_spent == 0
    assert any("FLAMEOUT" in e for e in live.events)
    staged = live.stage()
    assert staged and live.stages_spent == 1


def test_throttle_cut_means_freefall(db):
    live = LiveAscent.from_pad(_two_stage(db), "core:earth", MU_E, R_E, T_ROT)
    live.ignite()
    _run(live, 30.0)
    h0 = live.h
    live.prog = False
    live.throttle_cmd = 0.0
    _run(live, 8.0)
    assert live.throttle_eff == 0.0
    # ballistic: still moving but engines silent — dv_int frozen
    dv0 = live.dv_int
    _run(live, 4.0)
    assert live.dv_int == pytest.approx(dv0, abs=1e-6)
    assert live.h != h0


def test_cannot_stage_away_the_whole_vehicle(db):
    """Regression: spamming SPACE staged away every row -> mass 0 ->
    ZeroDivisionError in step()."""
    live = LiveAscent.from_pad(_two_stage(db), "core:earth", MU_E, R_E, T_ROT)
    live.ignite()
    _run(live, 5.0)
    assert live.stage() is True          # booster away
    assert live.stage() is False         # the last stage IS the vehicle
    assert live.vessel.total_mass_kg() > 0.0
    _run(live, 5.0)                      # must not raise
    assert live.outcome != "lost" or live.h < 0  # no breakup from staging


def test_q_telemetry_peaks_in_atmosphere(db):
    live = LiveAscent.from_pad(_two_stage(db), "core:earth", MU_E, R_E, T_ROT)
    live.ignite()
    q_max = 0.0
    for _ in range(int(200.0 / SIM_DT)):
        live.step(SIM_DT)
        q_max = max(q_max, live.q)
    assert q_max > 5_000.0            # went through real max-q
