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
