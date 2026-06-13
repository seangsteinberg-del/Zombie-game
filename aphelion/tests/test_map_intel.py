"""Chunk C (depth update): map intelligence — apsis clocks, stable frame
colors, and the transfer-window math behind the planner overlay."""

import math
import os

import pytest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from aphelion.main import (_frame_color, _next_apsis_times, _transfer_window,
                           _wrap_pi)
from aphelion.sim.orbits.kepler import state_to_elements

MU_E = 3.986_004_418e14
MU_S = 1.327_124_4e20
AU = 1.495_978_707e11


def test_next_apsis_times_bracket_now():
    r = 6_771e3
    v = math.sqrt(MU_E / r) * 1.1          # elliptic, periapsis at t=0
    el = state_to_elements(r, 0.0, 0.0, v, 0.0, MU_E)
    t_now = el.period * 2.3
    t_pe, t_ap = _next_apsis_times(el, t_now)
    assert t_now < t_pe <= t_now + el.period + 1.0
    assert t_now < t_ap <= t_now + el.period + 1.0
    frac = (t_pe - el.tau) / el.period
    assert abs(frac - round(frac)) < 1e-6          # an exact periapsis pass
    assert abs(abs(t_pe - t_ap) - el.period / 2.0) < 1.0


def test_frame_color_stable_and_distinct():
    a = _frame_color("core:moon")
    assert a == _frame_color("core:moon")           # deterministic
    assert a != _frame_color("core:earth")          # (with these ids)
    assert all(0 <= c <= 255 for c in a)


def test_transfer_window_earth_mars_canon():
    r1, r2 = 1.0 * AU, 1.523_679 * AU
    wait, t_tr, phase_req = _transfer_window(MU_S, r1, r2, 0.0)
    # canon Earth->Mars Hohmann: ~259 days transit, ~44 deg required lead
    assert t_tr / 86_400.0 == pytest.approx(259.0, abs=4.0)
    assert math.degrees(phase_req) == pytest.approx(44.3, abs=1.5)
    syn = 2.0 * math.pi / abs(math.sqrt(MU_S / r2 ** 3)
                              - math.sqrt(MU_S / r1 ** 3))
    assert 0.0 <= wait < syn
    # departing AT the window: the wait must be ~0 or ~one synodic period
    wait0, _, _ = _transfer_window(MU_S, r1, r2, phase_req)
    assert min(wait0, abs(wait0 - syn)) < 86_400.0


def test_transfer_window_phase_converges():
    # propagate both planets through the computed wait: the phase angle
    # must equal the required lead at departure (the whole point)
    r1, r2 = 1.0 * AU, 5.2044 * AU
    phase_now = _wrap_pi(2.1)
    wait, _, phase_req = _transfer_window(MU_S, r1, r2, phase_now)
    n_o = math.sqrt(MU_S / r1 ** 3)
    n_t = math.sqrt(MU_S / r2 ** 3)
    phase_at_dep = _wrap_pi(phase_now + (n_t - n_o) * wait)
    assert phase_at_dep == pytest.approx(_wrap_pi(phase_req), abs=1e-6)


# ---- O wiring: NAV-panel corridor advisor (01 §1.6) -------------------------

from types import SimpleNamespace  # noqa: E402

from aphelion.main import _corridor_advice  # noqa: E402
from aphelion.sim.environment.atmosphere import interface_altitude  # noqa: E402

MU_MARS = 4.282_837e13
R_MARS = 3.3895e6


def _mars_arrival_el(gamma_deg: float, v_i: float = 5_600.0):
    """Arrival conic with the given entry angle at the Mars interface
    (the canon test_phase5 state: 5.6 km/s, judged against beta 300)."""
    r_i = R_MARS + interface_altitude("core:mars")
    alpha = 2.0 / r_i - v_i * v_i / MU_MARS
    h = r_i * v_i * math.cos(math.radians(gamma_deg))
    eps = 0.5 * v_i * v_i - MU_MARS / r_i
    e = math.sqrt(max(1.0 + 2.0 * eps * h * h / (MU_MARS * MU_MARS), 0.0))
    return SimpleNamespace(alpha=alpha, periapsis=h * h / MU_MARS / (1.0 + e))


def test_corridor_advice_mars_go_and_steep():
    # 9.1 deg sits inside the pinned 8.83-9.42 capture band -> GO
    lines = _corridor_advice("core:mars", MU_MARS, R_MARS,
                             _mars_arrival_el(9.1), 300.0, 2.5e6)
    assert lines and lines[0][1] in ("go", "warn")
    assert "GO" in lines[0][0] and "corridor" in lines[0][0]
    # 7.0 deg skips out (phase-5 pin) -> danger, called SHALLOW
    shallow = _corridor_advice("core:mars", MU_MARS, R_MARS,
                               _mars_arrival_el(7.0), 300.0, 2.5e6)
    assert shallow and shallow[0][1] == "danger"
    assert "SHALLOW" in shallow[0][0]
    # an impossibly low TPS rating must raise the burn-up line
    burned = _corridor_advice("core:mars", MU_MARS, R_MARS,
                              _mars_arrival_el(9.1), 300.0, 1.0)
    assert any("WILL BURN UP" in ln for ln, _ in burned)


def test_corridor_advice_flyby_names_the_window():
    # periapsis 400 km up: vacuum flyby -> advise the Pe window to aim for
    el = _mars_arrival_el(9.1)
    el.periapsis = R_MARS + 400e3
    lines = _corridor_advice("core:mars", MU_MARS, R_MARS, el, 300.0, 2.5e6)
    assert lines and lines[0][1] == "warn"
    assert "AEROCAPTURE window" in lines[0][0]
    assert "HIGH" in lines[0][0]


def test_corridor_advice_silent_without_atmosphere():
    el = _mars_arrival_el(9.1)
    assert _corridor_advice("core:moon", 4.9e12, 1.737e6, el,
                            300.0, 2.5e6) == []
