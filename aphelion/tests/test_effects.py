"""FX safety: the particle pool must survive huge/non-finite screen
coordinates (regression: pygame.draw.circle raised 'center argument must
be a pair of numbers' when a burn was emitted while the camera was
focused far from the craft)."""

import math
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from aphelion.ui.effects import Particles


def _screen():
    pygame.init()
    return pygame.Surface((320, 200))


def test_huge_emit_coords_do_not_crash():
    s = _screen()
    p = Particles()
    p.emit_burn(4.5e10, -3.0e12, 1.0, 0.0)      # off-screen by lightyears
    p.update_draw(s, 0.016)                      # must not raise


def test_nonfinite_emit_refused():
    s = _screen()
    p = Particles()
    p.emit_burn(math.nan, 100.0, 1.0, 0.0)
    p.emit_burn(math.inf, math.inf, 0.0, 1.0)
    p.update_draw(s, 0.016)
    assert not (p.age < p.life).any()            # nothing was admitted


def test_normal_emit_still_draws():
    s = _screen()
    p = Particles()
    p.emit_burn(160.0, 100.0, 1.0, 0.0)
    before = pygame.surfarray.array3d(s).sum()
    p.update_draw(s, 0.016)
    assert pygame.surfarray.array3d(s).sum() > before


def test_drifted_out_particles_are_culled_not_fatal():
    s = _screen()
    p = Particles()
    p.emit_burn(160.0, 100.0, 1.0, 0.0)
    p.pos[:, 0] = 9.9e18                         # simulate runaway drift
    p.update_draw(s, 0.016)                      # must not raise
