"""UI theme tests (12 §5): palette constants, font cache, panel chrome,
gauges, chips, icon glyphs, seeded portraits, toasts, and draw_text."""

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from aphelion.ui import theme

ICON_NAMES = (
    "oxygen", "water", "hydrogen", "power", "funds", "science", "radiation",
    "crew", "contract", "engine", "tank", "warning", "clock", "warp", "dv",
    "signal", "lock", "check",
)


def _bytes(s: pygame.Surface) -> bytes:
    return pygame.image.tobytes(s, "RGBA")


def test_palette_exact():
    assert theme.COLORS["space_bg"] == (6, 8, 14)
    assert theme.COLORS["panel_fill"] == (10, 16, 28, 220)
    assert theme.COLORS["panel_edge"] == (42, 58, 85)
    assert theme.COLORS["accent"] == (140, 235, 255)
    assert theme.COLORS["good"] == (120, 255, 170)
    assert theme.COLORS["warn"] == (255, 200, 90)
    assert theme.COLORS["danger"] == (255, 110, 110)
    assert theme.COLORS["gold"] == (255, 215, 130)
    assert theme.COLORS["text"] == (200, 210, 224)
    assert theme.COLORS["text_dim"] == (110, 122, 140)


def test_fonts_lazy_and_cached():
    fonts = theme.init_fonts()
    assert set(fonts) == {"small", "body", "title", "big"}
    again = theme.init_fonts()
    assert again is fonts
    assert all(again[k] is fonts[k] for k in fonts)
    assert fonts["big"].get_height() > fonts["small"].get_height()


def test_panel_size_alpha_and_cache():
    p = theme.panel(220, 140, "Life Support")
    assert p.get_size() == (220, 140)
    assert p.get_flags() & pygame.SRCALPHA
    assert theme.panel(220, 140, "Life Support") is p          # cached object
    assert theme.panel(220, 140) is not p                      # title in key
    assert _bytes(theme.panel(220, 140)) != _bytes(p)


def test_panel_corner_notches_clipped():
    p = theme.panel(200, 100)
    w, h = p.get_size()
    assert p.get_at((0, 0)).a == 0                             # TL notch
    assert p.get_at((w - 1, h - 1)).a == 0                     # BR notch
    assert p.get_at((w // 2, h // 2)).a > 0                    # body present


def test_bar_clamps_frac():
    g = theme.COLORS["good"]
    assert theme.bar(120, 12, -0.5, g) is theme.bar(120, 12, 0.0, g)
    assert theme.bar(120, 12, 1.7, g) is theme.bar(120, 12, 1.0, g)
    full = theme.bar(120, 12, 1.0, g)
    empty = theme.bar(120, 12, 0.0, g)
    assert full.get_size() == (120, 12)
    assert full.get_flags() & pygame.SRCALPHA
    assert _bytes(full) != _bytes(empty)


def test_chip_scales_with_text():
    short = theme.chip("OK", theme.COLORS["good"])
    long = theme.chip("LOW PROPELLANT", theme.COLORS["warn"])
    assert short.get_flags() & pygame.SRCALPHA
    assert long.get_width() > short.get_width()
    assert long.get_height() == short.get_height()
    assert theme.chip("OK", theme.COLORS["good"]) is short     # cached


def test_all_icons_render_and_cache():
    for name in ICON_NAMES:
        ic = theme.icon(name, 16)
        assert ic.get_size() == (16, 16)
        assert ic.get_flags() & pygame.SRCALPHA
        assert ic.get_bounding_rect().width > 0                # non-empty glyph
        assert theme.icon(name, 16) is ic
    unknown = theme.icon("definitely_not_a_glyph", 16)
    assert unknown.get_bounding_rect().width > 0               # grey-dot fallback
    assert theme.icon("power", 24).get_size() == (24, 24)


def test_portrait_deterministic():
    a1 = _bytes(theme.portrait("Valeri Kovac"))
    theme._PORTRAIT_CACHE.clear()                              # defeat the cache
    a2 = _bytes(theme.portrait("Valeri Kovac"))
    assert a1 == a2


def test_portraits_differ_across_names_and_cache():
    p = theme.portrait("Jeb Armstead", 40)
    assert p.get_size() == (40, 40)
    assert p.get_flags() & pygame.SRCALPHA
    assert theme.portrait("Jeb Armstead", 40) is p             # cached object
    others = [theme.portrait(n, 40) for n in ("Ada Okafor", "Lin Mwangi", "Sam Petrov")]
    blobs = {_bytes(s) for s in (p, *others)}
    assert len(blobs) == 4                                     # visibly distinct


def test_toast_kinds_and_width():
    for kind in ("info", "paid", "alarm", "science"):
        t = theme.toast_surface("Contract complete", kind)
        assert t.get_flags() & pygame.SRCALPHA
        assert t.get_height() > 16
    short = theme.toast_surface("Hi", "info")
    long = theme.toast_surface("Hi there, much longer toast", "info")
    assert long.get_width() > short.get_width()
    assert theme.toast_surface("Hi", "info") is short          # cached


def test_draw_text_returns_width_and_blits():
    surf = pygame.Surface((200, 30), pygame.SRCALPHA)
    w = theme.draw_text(surf, 4, 4, "DELTA-V", theme.COLORS["accent"])
    assert isinstance(w, int) and w > 0
    assert surf.get_bounding_rect().width > 0                  # pixels landed
    w2 = theme.draw_text(surf, 4, 4, "DELTA-V", theme.COLORS["accent"], shadow=False)
    assert w2 == w
