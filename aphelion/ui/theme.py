"""UI theme (12 §5; ART-DIRECTION §1.3 "mission-control glass"): the whole
HUD/screen visual language. Dark translucent glass, thin rules, ONE amber
accent family for attention/interactive, desaturated cyan reserved for
nav/orbital values; status reads through brightness + context, never neon.
Panels, gauges, chips, icon glyphs, crew portraits and toasts are 100%
procedural (pygame.draw + numpy), headless-safe (plain SRCALPHA surfaces,
no display), deterministic (blake2b-seeded), and aggressively cached at
module level. The HUD whispers; the world speaks.
"""

from __future__ import annotations

import hashlib
import math

import numpy as np
import pygame

# -- palette (ART-DIRECTION §1.3 + §3; binding constants) ---------------------
# Text never pure white (#E8E4DA max) and never glows; amber is the single
# attention/interactive family (#FFB000-ish, pulled down to whisper on glass);
# cyan is desaturated and ONLY for nav/orbital geometry; good/warn/danger stay
# distinguishable by hue but live at low saturation.
SPACE_BG = (6, 8, 14)
PANEL_FILL = (10, 12, 17, 225)        # near-neutral dark glass
PANEL_EDGE = (60, 64, 72)             # graphite hairline, not blue chrome
ACCENT = (138, 186, 198)              # desaturated cyan: nav/orbital only
GOOD = (142, 192, 156)                # sage, reads by brightness not neon
WARN = (216, 158, 92)                 # amber-orange, same family as GOLD
DANGER = (212, 122, 110)              # muted brick, still unmistakable
GOLD = (226, 168, 80)                 # THE amber accent (headers, funds, keys)
TEXT = (214, 210, 200)                # warm off-white, under #E8E4DA ceiling
TEXT_DIM = (126, 124, 118)            # warm-neutral secondary

COLORS: dict[str, tuple] = {
    "space_bg": SPACE_BG,
    "panel_fill": PANEL_FILL,
    "panel_edge": PANEL_EDGE,
    "accent": ACCENT,
    "good": GOOD,
    "warn": WARN,
    "danger": DANGER,
    "gold": GOLD,
    "text": TEXT,
    "text_dim": TEXT_DIM,
}

_FONTS: dict[str, pygame.font.Font] = {}
_PANEL_CACHE: dict[tuple, pygame.Surface] = {}
_BAR_CACHE: dict[tuple, pygame.Surface] = {}
_CHIP_CACHE: dict[tuple, pygame.Surface] = {}
_ICON_CACHE: dict[tuple, pygame.Surface] = {}
_PORTRAIT_CACHE: dict[tuple, pygame.Surface] = {}
_TOAST_CACHE: dict[tuple, pygame.Surface] = {}
_TEXT_CACHE: dict[tuple, tuple[pygame.Surface, pygame.Surface | None]] = {}


def _mix(a: tuple, b: tuple, t: float) -> tuple[int, int, int]:
    """Linear blend of two RGB(A) colors' RGB channels."""
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def _seed(s: str) -> int:
    """Stable 64-bit seed from an id string (13 §3: no wall-clock RNG)."""
    return int.from_bytes(hashlib.blake2b(s.encode(), digest_size=8).digest(), "little")


# UI text wears a modern grotesk (Bahnschrift is a DIN; ships with Win10+),
# while data columns stay monospace on purpose — padded f-string rows align
# only in a fixed-pitch face. SysFont takes a fallback chain.
_UI_FACE = "bahnschrift,segoeuisemibold,segoeui,notosans,dejavusans"
_MONO_FACE = "consolas,cascadiamono,dejavusansmono"


def init_fonts() -> dict[str, pygame.font.Font]:
    """Lazy, cached font set; safe to call every frame. ``small``/``body``
    are monospace (column data); the ``ui*`` faces are proportional and
    carry every header, menu, banner, footer and label."""
    if not _FONTS:
        pygame.font.init()
        _FONTS["small"] = pygame.font.SysFont(_MONO_FACE, 13)
        _FONTS["body"] = pygame.font.SysFont(_MONO_FACE, 14)
        _FONTS["title"] = pygame.font.SysFont(_UI_FACE, 17, bold=True)
        _FONTS["big"] = pygame.font.SysFont(_UI_FACE, 22, bold=True)
        _FONTS["ui_small"] = pygame.font.SysFont(_UI_FACE, 14)
        _FONTS["ui"] = pygame.font.SysFont(_UI_FACE, 16)
        _FONTS["ui_title"] = pygame.font.SysFont(_UI_FACE, 20, bold=True)
        _FONTS["ui_big"] = pygame.font.SysFont(_UI_FACE, 30, bold=True)
        _FONTS["ui_huge"] = pygame.font.SysFont(_UI_FACE, 48, bold=True)
    return _FONTS


_TRACKED_CACHE: dict[tuple, pygame.Surface] = {}


def tracked(text: str, font: str = "ui_title", color: tuple = TEXT,
            tracking: int = 2) -> pygame.Surface:
    """Letterspaced text (modern display-caps look), cached per key."""
    key = (text, font, tuple(color[:3]), tracking)
    cached = _TRACKED_CACHE.get(key)
    if cached is not None:
        return cached
    f = init_fonts()[font]
    imgs = [f.render(ch, True, color[:3]) for ch in text]
    w = sum(i.get_width() for i in imgs) + tracking * max(0, len(imgs) - 1)
    h = max((i.get_height() for i in imgs), default=1)
    surf = pygame.Surface((max(1, w), h), pygame.SRCALPHA)
    x = 0
    for i in imgs:
        surf.blit(i, (x, 0))
        x += i.get_width() + tracking
    _TRACKED_CACHE[key] = surf
    return surf


# -- panel chrome -------------------------------------------------------------

def panel(w: int, h: int, title: str | None = None) -> pygame.Surface:
    """Glass panel plate: vertical-gradient translucent body, hairline
    edge with a soft inner top sheen, clipped TL/BR corner notches, and an
    optional letterspaced header band with an accent underline."""
    key = (w, h, title)
    cached = _PANEL_CACHE.get(key)
    if cached is not None:
        return cached
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    body = pygame.Rect(0, 0, w, h)
    notch = max(6, min(12, w // 6, h // 6))
    # body: subtle vertical gradient, lighter glass at the top (§1.3: dark
    # translucent glass — near-neutral, the blue cast lives in the world)
    top = (14, 17, 25, 230)
    bot = (7, 9, 14, 220)
    grad = pygame.Surface((1, max(2, h)), pygame.SRCALPHA)
    for yy in range(h):
        t = yy / max(1, h - 1)
        grad.set_at((0, yy), tuple(int(top[i] + (bot[i] - top[i]) * t)
                                   for i in range(4)))
    grad = pygame.transform.scale(grad, (w, h))
    mask = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.rect(mask, (255, 255, 255, 255), body, border_radius=7)
    grad.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
    surf.blit(grad, (0, 0))
    if title is not None:
        band_h = 26
        band = pygame.Surface((w - 2, band_h), pygame.SRCALPHA)
        for yy in range(band_h):                      # graphite, not blue
            t = yy / max(1, band_h - 1)
            band.fill((int(19 + 6 * (1 - t)), int(22 + 7 * (1 - t)),
                       int(29 + 8 * (1 - t)), 234),
                      pygame.Rect(0, yy, w - 2, 1))
        bmask = pygame.Surface((w - 2, band_h), pygame.SRCALPHA)
        pygame.draw.rect(bmask, (255, 255, 255, 255),
                         pygame.Rect(0, 0, w - 2, band_h),
                         border_top_left_radius=7, border_top_right_radius=7)
        band.blit(bmask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
        surf.blit(band, (1, 1))
        pygame.draw.line(surf, _mix(PANEL_EDGE, GOLD, 0.15),
                         (1, band_h), (w - 2, band_h))
        img = tracked(title.upper(), "ui_small", GOLD, 2)
        tx = notch + 6
        surf.blit(img, (tx, 1 + (band_h - img.get_height()) // 2))
        pygame.draw.line(surf, (*GOLD, 90),
                         (tx, band_h - 3), (tx + img.get_width(), band_h - 3))
    # inner top sheen (reduced — glass, not gloss) + hairline edge
    pygame.draw.line(surf, (255, 255, 255, 14), (notch + 2, 1), (w - 9, 1))
    pygame.draw.rect(surf, PANEL_EDGE, body, width=1, border_radius=7)
    # clipped corner notches (TL / BR); pygame.draw writes alpha directly
    pygame.draw.polygon(surf, (0, 0, 0, 0), [(0, 0), (notch, 0), (0, notch)])
    pygame.draw.polygon(surf, (0, 0, 0, 0),
                        [(w, h), (w - notch - 1, h), (w, h - notch - 1)])
    pygame.draw.line(surf, _mix(PANEL_EDGE, (255, 255, 255), 0.12),
                     (notch, 0), (0, notch))
    pygame.draw.line(surf, PANEL_EDGE, (w - 1 - notch, h - 1), (w - 1, h - 1 - notch))
    _PANEL_CACHE[key] = surf
    return surf


def bar(w: int, h: int, frac: float, color: tuple,
        back: tuple = (40, 50, 70)) -> pygame.Surface:
    """Bevelled gauge: gradient fill with a bright cap line, hatched empty
    part. ``frac`` is clamped to [0, 1] and quantized for the cache."""
    f = min(1.0, max(0.0, float(frac)))
    key = (w, h, round(f, 3), tuple(color[:3]), tuple(back[:3]))
    cached = _BAR_CACHE.get(key)
    if cached is not None:
        return cached
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    rad = max(2, h // 2 - 1)
    track = pygame.Rect(0, 0, w, h)
    pygame.draw.rect(surf, (*_mix(back, (0, 0, 0), 0.45), 235), track,
                     border_radius=rad)
    pygame.draw.rect(surf, (*_mix(back, (255, 255, 255), 0.10), 255), track,
                     width=1, border_radius=rad)
    fill_w = round((w - 2) * f)
    if fill_w > 2:
        fill = pygame.Surface((fill_w, h - 2), pygame.SRCALPHA)
        for yy in range(h - 2):                  # vertical sheen on the fill
            t = yy / max(1, h - 3)
            shade = _mix(_mix(color, (255, 255, 255), 0.38 * (1.0 - t)),
                         (0, 0, 0), 0.22 * t)
            fill.fill((*shade, 255), pygame.Rect(0, yy, fill_w, 1))
        fmask = pygame.Surface((fill_w, h - 2), pygame.SRCALPHA)
        pygame.draw.rect(fmask, (255, 255, 255, 255),
                         pygame.Rect(0, 0, fill_w, h - 2),
                         border_radius=max(1, rad - 1))
        fill.blit(fmask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
        surf.blit(fill, (1, 1))
        # luminous cap at the leading edge
        cap = _mix(color, (255, 255, 255), 0.8)
        pygame.draw.rect(surf, (*cap, 230),
                         pygame.Rect(max(1, fill_w - 1), 1, 2, h - 2),
                         border_radius=1)
        pygame.draw.rect(surf, (*color[:3], 60),
                         pygame.Rect(max(0, fill_w - 4), 0, 8, h),
                         border_radius=2)
    _BAR_CACHE[key] = surf
    return surf


def chip(text: str, color: tuple, font: pygame.font.Font | None = None) -> pygame.Surface:
    """Pill-shaped tag, §1.3 restraint: dark translucent glass fill, 1px
    neutral graphite rim, text in the quiet palette (semantic hue pulled
    toward TEXT — status reads through brightness + context, not neon).
    Chips recede; the world speaks."""
    key = (text, tuple(color[:3]), None if font is None else id(font))
    cached = _CHIP_CACHE.get(key)
    if cached is not None:
        return cached
    f = font if font is not None else init_fonts()["ui_small"]
    img = f.render(text, True, _mix(color, TEXT, 0.35))
    w, h = img.get_width() + 12, img.get_height() + 4
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    r = h // 2
    pygame.draw.rect(surf, (11, 13, 17, 200), pygame.Rect(0, 0, w, h), border_radius=r)
    pygame.draw.rect(surf, (58, 61, 68), pygame.Rect(0, 0, w, h), width=1, border_radius=r)
    surf.blit(img, (6, 2))
    _CHIP_CACHE[key] = surf
    return surf


# -- icon glyphs (drawn at 4x, smoothscaled down for crisp AA edges) ----------

def _g_oxygen(s: pygame.Surface, n: int) -> None:
    lw = max(2, n // 10)
    pygame.draw.circle(s, ACCENT, (int(n * 0.42), int(n * 0.42)), int(n * 0.20), lw)
    pygame.draw.circle(s, ACCENT, (int(n * 0.68), int(n * 0.66)), int(n * 0.12), max(2, lw - 2))


def _g_water(s: pygame.Surface, n: int) -> None:
    c = (126, 168, 210)                  # desaturated — §1.3 no neon
    cx = n // 2
    pygame.draw.circle(s, c, (cx, int(n * 0.62)), int(n * 0.28))
    pygame.draw.polygon(s, c, [(cx, int(n * 0.08)),
                               (cx - int(n * 0.26), int(n * 0.55)),
                               (cx + int(n * 0.26), int(n * 0.55))])
    pygame.draw.circle(s, _mix(c, (255, 255, 255), 0.6),
                       (cx - int(n * 0.1), int(n * 0.58)), max(2, n // 16))


def _g_hydrogen(s: pygame.Surface, n: int) -> None:
    c = (204, 210, 218)                  # cool pale grey, under white ceiling
    cy = n // 2
    pygame.draw.circle(s, c, (int(n * 0.34), cy), int(n * 0.13))
    pygame.draw.circle(s, c, (int(n * 0.66), cy), int(n * 0.13))


def _g_power(s: pygame.Surface, n: int) -> None:
    pygame.draw.polygon(s, WARN, [(int(n * 0.55), int(n * 0.06)),
                                  (int(n * 0.22), int(n * 0.55)),
                                  (int(n * 0.45), int(n * 0.55)),
                                  (int(n * 0.38), int(n * 0.94)),
                                  (int(n * 0.78), int(n * 0.40)),
                                  (int(n * 0.52), int(n * 0.40))])


def _g_funds(s: pygame.Surface, n: int) -> None:
    lw = max(2, n // 10)
    cx = cy = n // 2
    pygame.draw.circle(s, GOLD, (cx, cy), int(n * 0.42), lw)
    d = int(n * 0.15)
    pygame.draw.arc(s, GOLD, pygame.Rect(cx - d, cy - 2 * d, 2 * d, 2 * d),
                    math.pi * 0.2, math.pi * 1.2, lw)
    pygame.draw.arc(s, GOLD, pygame.Rect(cx - d, cy, 2 * d, 2 * d),
                    math.pi * 1.2, math.pi * 2.2, lw)
    pygame.draw.line(s, GOLD, (cx, cy - int(2.4 * d)), (cx, cy + int(2.4 * d)), lw)


def _g_science(s: pygame.Surface, n: int) -> None:
    lw = max(2, n // 10)
    cx = n // 2
    nk = int(n * 0.07)
    pygame.draw.polygon(s, (*ACCENT, 110), [(int(n * 0.30), int(n * 0.62)),
                                            (int(n * 0.70), int(n * 0.62)),
                                            (int(n * 0.78), int(n * 0.78)),
                                            (int(n * 0.22), int(n * 0.78))])
    pygame.draw.polygon(s, ACCENT, [(cx - nk, int(n * 0.10)), (cx - nk, int(n * 0.38)),
                                    (int(n * 0.18), int(n * 0.82)),
                                    (int(n * 0.82), int(n * 0.82)),
                                    (cx + nk, int(n * 0.38)), (cx + nk, int(n * 0.10))], lw)


def _g_radiation(s: pygame.Surface, n: int) -> None:
    cx = cy = n // 2
    r1, r2 = n * 0.13, n * 0.40
    pygame.draw.circle(s, WARN, (cx, cy), int(n * 0.07))
    for base in (90, 210, 330):
        pts = []
        for a in range(base - 30, base + 31, 6):
            rad = math.radians(a)
            pts.append((cx + r1 * math.cos(rad), cy - r1 * math.sin(rad)))
        for a in range(base + 30, base - 31, -6):
            rad = math.radians(a)
            pts.append((cx + r2 * math.cos(rad), cy - r2 * math.sin(rad)))
        pygame.draw.polygon(s, WARN, pts)


def _g_crew(s: pygame.Surface, n: int) -> None:
    c = (218, 216, 210)                  # warm off-white (#E8E4DA ceiling)
    cx = n // 2
    pygame.draw.circle(s, c, (cx, int(n * 0.34)), int(n * 0.17))
    pygame.draw.ellipse(s, c, pygame.Rect(cx - int(n * 0.30), int(n * 0.55),
                                          int(n * 0.60), int(n * 0.55)))


def _g_contract(s: pygame.Surface, n: int) -> None:
    lw = max(2, n // 10)
    cx = n // 2
    cy = int(n * 0.38)
    pygame.draw.polygon(s, GOLD, [(cx - int(n * 0.16), int(n * 0.55)),
                                  (cx - int(n * 0.28), int(n * 0.92)),
                                  (cx - int(n * 0.05), int(n * 0.78))])
    pygame.draw.polygon(s, GOLD, [(cx + int(n * 0.16), int(n * 0.55)),
                                  (cx + int(n * 0.28), int(n * 0.92)),
                                  (cx + int(n * 0.05), int(n * 0.78))])
    pygame.draw.circle(s, GOLD, (cx, cy), int(n * 0.26), lw)
    pygame.draw.circle(s, GOLD, (cx, cy), int(n * 0.10))


def _g_engine(s: pygame.Surface, n: int) -> None:
    c = (190, 200, 215)
    lw = max(2, n // 10)
    cx = n // 2
    pygame.draw.rect(s, c, pygame.Rect(cx - int(n * 0.14), int(n * 0.08),
                                       int(n * 0.28), int(n * 0.12)))
    pygame.draw.polygon(s, c, [(cx - int(n * 0.10), int(n * 0.20)),
                               (cx + int(n * 0.10), int(n * 0.20)),
                               (cx + int(n * 0.30), int(n * 0.85)),
                               (cx - int(n * 0.30), int(n * 0.85))], lw)
    pygame.draw.line(s, WARN, (cx - int(n * 0.20), int(n * 0.80)),
                     (cx + int(n * 0.20), int(n * 0.80)), lw)


def _g_tank(s: pygame.Surface, n: int) -> None:
    c = (190, 200, 215)
    lw = max(2, n // 10)
    cx = n // 2
    pygame.draw.rect(s, c, pygame.Rect(cx - int(n * 0.20), int(n * 0.08),
                                       int(n * 0.40), int(n * 0.84)),
                     lw, border_radius=int(n * 0.20))
    pygame.draw.line(s, c, (cx - int(n * 0.18), n // 2), (cx + int(n * 0.18), n // 2), lw)


def _g_warning(s: pygame.Surface, n: int) -> None:
    lw = max(2, n // 10)
    cx = n // 2
    pygame.draw.polygon(s, WARN, [(cx, int(n * 0.08)),
                                  (int(n * 0.92), int(n * 0.88)),
                                  (int(n * 0.08), int(n * 0.88))], lw)
    pygame.draw.line(s, WARN, (cx, int(n * 0.35)), (cx, int(n * 0.62)), lw)
    pygame.draw.circle(s, WARN, (cx, int(n * 0.75)), max(2, int(lw * 0.8)))


def _g_clock(s: pygame.Surface, n: int) -> None:
    c = TEXT
    lw = max(2, n // 10)
    cx = cy = n // 2
    pygame.draw.circle(s, c, (cx, cy), int(n * 0.40), lw)
    pygame.draw.line(s, c, (cx, cy), (cx, int(n * 0.22)), lw)
    pygame.draw.line(s, c, (cx, cy), (cx + int(n * 0.22), cy + int(n * 0.10)), lw)
    pygame.draw.circle(s, c, (cx, cy), max(2, lw))


def _g_warp(s: pygame.Surface, n: int) -> None:
    cy = n // 2
    for ox in (0, int(n * 0.32)):
        pygame.draw.polygon(s, ACCENT, [(int(n * 0.12) + ox, int(n * 0.15)),
                                        (int(n * 0.44) + ox, cy),
                                        (int(n * 0.12) + ox, int(n * 0.85)),
                                        (int(n * 0.26) + ox, int(n * 0.85)),
                                        (int(n * 0.58) + ox, cy),
                                        (int(n * 0.26) + ox, int(n * 0.15))])


def _g_dv(s: pygame.Surface, n: int) -> None:
    lw = max(2, n // 10)
    pygame.draw.polygon(s, ACCENT, [(n // 2, int(n * 0.12)),
                                    (int(n * 0.85), int(n * 0.85)),
                                    (int(n * 0.15), int(n * 0.85))], lw)


def _g_signal(s: pygame.Surface, n: int) -> None:
    lw = max(2, n // 10)
    x0, y0 = int(n * 0.18), int(n * 0.82)
    pygame.draw.circle(s, ACCENT, (x0, y0), int(n * 0.07))
    for rf in (0.30, 0.50, 0.70):
        r = int(n * rf)
        pygame.draw.arc(s, ACCENT, pygame.Rect(x0 - r, y0 - r, 2 * r, 2 * r),
                        0.08, math.pi / 2 - 0.08, lw)


def _g_lock(s: pygame.Surface, n: int) -> None:
    c = (190, 200, 215)
    lw = max(2, n // 10)
    cx = n // 2
    sh = int(n * 0.20)
    pygame.draw.arc(s, c, pygame.Rect(cx - sh, int(n * 0.10), 2 * sh, 2 * sh),
                    0.0, math.pi, lw)
    pygame.draw.line(s, c, (cx - sh + lw // 2, int(n * 0.30)),
                     (cx - sh + lw // 2, int(n * 0.46)), lw)
    pygame.draw.line(s, c, (cx + sh - lw // 2, int(n * 0.30)),
                     (cx + sh - lw // 2, int(n * 0.46)), lw)
    pygame.draw.rect(s, c, pygame.Rect(cx - int(n * 0.28), int(n * 0.46),
                                       int(n * 0.56), int(n * 0.42)),
                     border_radius=max(2, n // 16))
    pygame.draw.circle(s, (30, 38, 52), (cx, int(n * 0.62)), max(2, n // 12))


def _g_check(s: pygame.Surface, n: int) -> None:
    lw = max(3, n // 8)
    pygame.draw.line(s, GOOD, (int(n * 0.14), int(n * 0.55)),
                     (int(n * 0.40), int(n * 0.80)), lw)
    pygame.draw.line(s, GOOD, (int(n * 0.40), int(n * 0.80)),
                     (int(n * 0.86), int(n * 0.18)), lw)


def _g_dot(s: pygame.Surface, n: int) -> None:
    pygame.draw.circle(s, TEXT_DIM, (n // 2, n // 2), int(n * 0.18))


_GLYPHS: dict[str, object] = {
    "oxygen": _g_oxygen, "water": _g_water, "hydrogen": _g_hydrogen,
    "power": _g_power, "funds": _g_funds, "science": _g_science,
    "radiation": _g_radiation, "crew": _g_crew, "contract": _g_contract,
    "engine": _g_engine, "tank": _g_tank, "warning": _g_warning,
    "clock": _g_clock, "warp": _g_warp, "dv": _g_dv, "signal": _g_signal,
    "lock": _g_lock, "check": _g_check,
}


def icon(name: str, size: int = 16) -> pygame.Surface:
    """Procedural glyph; drawn at 4x and smoothscaled down. Unknown names
    fall back to a grey dot."""
    key = (name, size)
    cached = _ICON_CACHE.get(key)
    if cached is not None:
        return cached
    big = pygame.Surface((size * 4, size * 4), pygame.SRCALPHA)
    _GLYPHS.get(name, _g_dot)(big, size * 4)            # type: ignore[operator]
    surf = pygame.transform.smoothscale(big, (size, size))
    _ICON_CACHE[key] = surf
    return surf


# -- crew portraits -----------------------------------------------------------

_SKIN = ((244, 212, 184), (224, 184, 150), (198, 148, 110), (160, 110, 80), (118, 82, 60))
_HAIR = ((40, 36, 34), (92, 62, 40), (176, 134, 72), (202, 194, 186), (150, 58, 40))
_SUIT = ((205, 92, 60), (72, 108, 178), (108, 138, 92), (148, 118, 178), (186, 158, 72))
_EYE = ((26, 36, 58), (40, 80, 122), (48, 92, 52))


def portrait(name: str, size: int = 40) -> pygame.Surface:
    """Seeded 8x8 pixel-art crew bust, nearest-neighbor upscaled, in a
    rounded PANEL_EDGE frame. Deterministic per name."""
    key = (name, size)
    cached = _PORTRAIT_CACHE.get(key)
    if cached is not None:
        return cached
    rng = np.random.default_rng(_seed(name))
    skin = _SKIN[int(rng.integers(5))]
    hair = _HAIR[int(rng.integers(5))]
    style = int(rng.integers(5))
    suit = _SUIT[int(rng.integers(5))]
    eye = _EYE[int(rng.integers(3))]
    px = pygame.Surface((8, 8), pygame.SRCALPHA)
    px.fill((16, 22, 34, 255))
    for yy in range(2, 6):                              # face block + ears
        for xx in range(2, 6):
            px.set_at((xx, yy), skin)
    px.set_at((1, 3), skin)
    px.set_at((6, 3), skin)
    px.set_at((2, 3), eye)                              # eye row
    px.set_at((5, 3), eye)
    mouth = _mix(skin, (0, 0, 0), 0.35)
    px.set_at((3, 5), mouth)
    px.set_at((4, 5), mouth)
    hair_cells: dict[int, tuple[tuple[int, int], ...]] = {
        0: (),                                           # bald
        1: ((2, 1), (3, 1), (4, 1), (5, 1)),             # short crop
        2: ((2, 0), (3, 0), (4, 0), (5, 0),              # full
            (1, 1), (2, 1), (3, 1), (4, 1), (5, 1), (6, 1), (1, 2), (6, 2)),
        3: ((1, 1), (2, 1), (3, 1), (4, 1), (1, 2), (2, 2)),  # side sweep
        4: ((2, 0), (4, 0), (5, 0), (2, 1), (3, 1), (4, 1), (5, 1)),  # spiky
    }
    for cell in hair_cells[style]:
        px.set_at(cell, hair)
    collar = _mix(suit, (255, 255, 255), 0.3)
    for xx in range(8):                                  # suit shoulders
        px.set_at((xx, 6), suit)
        px.set_at((xx, 7), suit)
    px.set_at((3, 6), collar)
    px.set_at((4, 6), collar)
    surf = pygame.transform.scale(px, (size, size))      # nearest-neighbor
    radius = max(3, size // 8)
    mask = pygame.Surface((size, size), pygame.SRCALPHA)
    pygame.draw.rect(mask, (255, 255, 255, 255), pygame.Rect(0, 0, size, size),
                     border_radius=radius)
    surf.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
    pygame.draw.rect(surf, PANEL_EDGE, pygame.Rect(0, 0, size, size),
                     width=1, border_radius=radius)
    _PORTRAIT_CACHE[key] = surf
    return surf


# -- formatting & selection chrome --------------------------------------------

def fmt_duration(seconds: float) -> str:
    """Human-readable duration: '38m 12s', '2d 04:11', '1y 112d'."""
    s = abs(float(seconds))
    sign = "-" if seconds < 0 else ""
    if s < 60.0:
        return f"{sign}{s:.0f}s"
    if s < 3_600.0:
        return f"{sign}{int(s // 60)}m {int(s % 60):02d}s"
    if s < 86_400.0:
        return f"{sign}{int(s // 3600)}h {int(s % 3600 // 60):02d}m"
    if s < 365.25 * 86_400.0:
        d = int(s // 86_400)
        rem = s - d * 86_400
        return f"{sign}{d}d {int(rem // 3600):02d}:{int(rem % 3600 // 60):02d}"
    y = int(s // (365.25 * 86_400))
    d = int((s - y * 365.25 * 86_400) // 86_400)
    return f"{sign}{y}y {d}d"


_GLOW_CACHE: dict[tuple, pygame.Surface] = {}


def row_glow(w: int, h: int, color: tuple = ACCENT) -> pygame.Surface:
    """Selected-row highlight bar: translucent tint + 2px leading edge."""
    key = (w, h, tuple(color[:3]))
    cached = _GLOW_CACHE.get(key)
    if cached is not None:
        return cached
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.rect(surf, (*color[:3], 28), pygame.Rect(0, 0, w, h),
                     border_radius=4)
    pygame.draw.rect(surf, (*color[:3], 90), pygame.Rect(0, 0, 3, h),
                     border_top_left_radius=4, border_bottom_left_radius=4)
    _GLOW_CACHE[key] = surf
    return surf


# -- key-hint footer ----------------------------------------------------------

_KEYCAP_CACHE: dict[str, pygame.Surface] = {}
_FOOTER_CACHE: dict[tuple, pygame.Surface] = {}
FOOTER_H = 30


def keycap(label: str) -> pygame.Surface:
    """Keyboard-key cap, §1.3: graphite plate, hairline edge, quiet label
    with a whisper of amber (keys are interactive — amber's territory)."""
    cached = _KEYCAP_CACHE.get(label)
    if cached is not None:
        return cached
    img = init_fonts()["ui_small"].render(label, True, _mix(GOLD, TEXT, 0.55))
    w, h = img.get_width() + 10, img.get_height() + 4
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.rect(surf, (26, 28, 33, 235), pygame.Rect(0, 0, w, h),
                     border_radius=4)
    pygame.draw.rect(surf, (72, 75, 82), pygame.Rect(0, 0, w, h),
                     width=1, border_radius=4)
    pygame.draw.line(surf, (255, 255, 255, 18), (3, 1), (w - 4, 1))
    surf.blit(img, (5, 2))
    _KEYCAP_CACHE[label] = surf
    return surf


def footer(w: int, hints: str) -> pygame.Surface:
    """Bottom hint strip: gradient glass band of keycap + action pairs.
    ``hints`` is the legacy text format — groups separated by runs of 3+
    spaces, each group "KEY action words"."""
    key = (w, hints)
    cached = _FOOTER_CACHE.get(key)
    if cached is not None:
        return cached
    h = FOOTER_H
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    for yy in range(h):                            # neutral graphite glass
        t = yy / max(1, h - 1)
        surf.fill((int(9 + 5 * t), int(11 + 5 * t), int(14 + 7 * t),
                   int(205 + 40 * t)), pygame.Rect(0, yy, w, 1))
    pygame.draw.line(surf, (*_mix(PANEL_EDGE, GOLD, 0.12), 170),
                     (0, 0), (w, 0))
    f = init_fonts()["ui_small"]
    x = 12
    groups = [g.strip() for g in hints.split("   ") if g.strip()]
    for g in groups:
        parts = g.split(" ", 1)
        cap = keycap(parts[0])
        cy = (h - cap.get_height()) // 2
        if x + cap.get_width() > w - 8:
            break
        surf.blit(cap, (x, cy))
        x += cap.get_width() + 5
        if len(parts) > 1:
            img = f.render(parts[1], True, TEXT_DIM)
            if x + img.get_width() > w - 4:
                break
            surf.blit(img, (x, (h - img.get_height()) // 2))
            x += img.get_width()
        x += 18
    _FOOTER_CACHE[key] = surf
    return surf


# -- toasts & text ------------------------------------------------------------

def toast_surface(text: str, kind: str = "info") -> pygame.Surface:
    """Notification pill: kind-keyed icon + colored text on panel chrome."""
    key = (text, kind)
    cached = _TOAST_CACHE.get(key)
    if cached is not None:
        return cached
    color = {"info": ACCENT, "paid": GOLD, "alarm": WARN, "science": ACCENT}.get(kind, ACCENT)
    icon_name = {"paid": "funds", "alarm": "warning", "science": "science"}.get(kind)
    if icon_name is not None:
        ic = icon(icon_name, 16)
    else:                                                # info: accent dot
        ic = pygame.Surface((16, 16), pygame.SRCALPHA)
        pygame.draw.circle(ic, ACCENT, (8, 8), 4)
    img = init_fonts()["ui"].render(text, True, color)
    h = max(16, img.get_height()) + 12
    w = 14 + 16 + 8 + img.get_width() + 14
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.rect(surf, PANEL_FILL, pygame.Rect(0, 0, w, h), border_radius=h // 2)
    pygame.draw.rect(surf, PANEL_EDGE, pygame.Rect(0, 0, w, h), width=1,
                     border_radius=h // 2)
    surf.blit(ic, (14, (h - 16) // 2))
    surf.blit(img, (14 + 16 + 8, (h - img.get_height()) // 2))
    _TOAST_CACHE[key] = surf
    return surf


def draw_text(surface: pygame.Surface, x: int, y: int, text: str,
              color: tuple = TEXT, font: str | pygame.font.Font = "body",
              shadow: bool = True) -> int:
    """Blit text with a 1px drop shadow; returns the rendered width."""
    f = init_fonts()[font] if isinstance(font, str) else font
    key = (text, tuple(color[:3]), font if isinstance(font, str) else id(f), shadow)
    cached = _TEXT_CACHE.get(key)
    if cached is None:
        img = f.render(text, True, color[:3])
        sh = f.render(text, True, (0, 0, 0)) if shadow else None
        if len(_TEXT_CACHE) > 4096:                      # bound the cache
            _TEXT_CACHE.clear()
        cached = _TEXT_CACHE[key] = (img, sh)
    img, sh = cached
    if sh is not None:
        surface.blit(sh, (x + 1, y + 1))
    surface.blit(img, (x, y))
    return img.get_width()
