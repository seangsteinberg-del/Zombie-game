"""Chunk A (depth update): UI foundation — duration formatting, selection
chrome, the new audio micro-cues, and the ascent input-safety constants."""

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from aphelion.ui.theme import fmt_duration, row_glow


def test_fmt_duration_bands():
    assert fmt_duration(12) == "12s"
    assert fmt_duration(38 * 60 + 12) == "38m 12s"
    assert fmt_duration(3 * 3600 + 240) == "3h 04m"
    assert fmt_duration(2 * 86_400 + 4 * 3600 + 11 * 60) == "2d 04:11"
    assert fmt_duration(365.25 * 86_400 + 112 * 86_400).startswith("1y 112d")
    assert fmt_duration(-90).startswith("-")


def test_row_glow_cached_surface():
    pygame.init()
    a = row_glow(200, 24)
    b = row_glow(200, 24)
    assert a is b                      # cache hit
    assert a.get_size() == (200, 24)
    assert a.get_at((1, 12)).a > 0     # leading edge is visible


def test_audio_has_micro_cues():
    from aphelion.ui.audio import AudioCues
    cues = AudioCues()
    if cues.ok:                        # dummy driver may still init mixer
        assert "tick" in cues._snd and "warn" in cues._snd
    cues.play("tick")                  # never raises, even when not ok


def test_ascent_revert_window_constant():
    from aphelion.main import _REVERT_WINDOW_S
    assert 5.0 <= _REVERT_WINDOW_S <= 60.0
