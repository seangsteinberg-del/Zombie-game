"""EVA-scale procedural art: the hero astronaut (walk cycle, helmet visor,
PLSS pack), planted flags and the anomaly marker. Drawn at 2x and
smoothscaled like base_art; everything cached and deterministic."""

from __future__ import annotations

import math

import pygame

_SUIT = (226, 228, 234)
_SUIT_SH = (168, 172, 184)
_VISOR = (255, 196, 90)
_PLSS = (190, 194, 202)
_ACCENT = (200, 60, 50)

_CACHE: dict = {}


def astronaut(phase: int, facing: int, airborne: bool = False,
              h_px: int = 34) -> pygame.Surface:
    """Walk-cycle astronaut, side view. phase 0..3; facing ±1."""
    key = ("walker", phase & 3, facing, airborne, h_px)
    got = _CACHE.get(key)
    if got is not None:
        return got
    w2, h2 = 48, 68                       # 2x canvas
    s = pygame.Surface((w2, h2), pygame.SRCALPHA)
    swing = [-7, 0, 7, 0][phase & 3] if not airborne else 10
    # legs (back first)
    hip = (22, 44)
    for leg, dx in ((0, -swing), (1, swing)):
        col = _SUIT_SH if leg == 0 else _SUIT
        knee = (hip[0] + dx * 0.45, hip[1] + 10)
        foot = (hip[0] + dx, h2 - 4 if not airborne else h2 - 9 - leg * 4)
        pygame.draw.line(s, col, hip, knee, 7)
        pygame.draw.line(s, col, knee, foot, 6)
        pygame.draw.ellipse(s, col, (foot[0] - 5, foot[1] - 3, 11, 6))
    # torso
    pygame.draw.rect(s, _SUIT, (13, 22, 19, 25), border_radius=7)
    pygame.draw.rect(s, _SUIT_SH, (13, 38, 19, 9), border_radius=4)
    # PLSS backpack (behind, opposite facing)
    pygame.draw.rect(s, _PLSS, (4, 20, 10, 22), border_radius=3)
    pygame.draw.line(s, _SUIT_SH, (8, 24), (8, 38), 2)
    # arm (front)
    sw_a = [5, 0, -5, 0][phase & 3] if not airborne else -8
    shoulder = (24, 26)
    elbow = (27 + sw_a * 0.4, 34)
    hand = (26 + sw_a, 42)
    pygame.draw.line(s, _SUIT, shoulder, elbow, 6)
    pygame.draw.line(s, _SUIT, elbow, hand, 5)
    # helmet
    pygame.draw.circle(s, _SUIT, (24, 13), 11)
    pygame.draw.circle(s, (30, 30, 36), (27, 13), 7)
    pygame.draw.circle(s, _VISOR, (27, 13), 6)
    pygame.draw.circle(s, (255, 240, 200), (29, 11), 2)
    # red commander stripe
    pygame.draw.rect(s, _ACCENT, (13, 28, 3, 14), border_radius=1)
    out = pygame.transform.smoothscale(s, (int(w2 * h_px / h2), h_px))
    if facing < 0:
        out = pygame.transform.flip(out, True, False)
    _CACHE[key] = out
    return out


def flag(h_px: int = 30) -> pygame.Surface:
    key = ("flag", h_px)
    got = _CACHE.get(key)
    if got is not None:
        return got
    s = pygame.Surface((36, 60), pygame.SRCALPHA)
    pygame.draw.line(s, (200, 204, 214), (6, 4), (6, 58), 3)
    pygame.draw.polygon(s, _ACCENT, [(8, 4), (34, 9), (8, 18)])
    pygame.draw.polygon(s, (255, 255, 255), [(8, 8), (24, 10), (8, 13)])
    out = pygame.transform.smoothscale(s, (int(36 * h_px / 60), h_px))
    _CACHE[key] = out
    return out


def anomaly_marker(t: float, size: int = 26) -> pygame.Surface:
    """Pulsing survey diamond over an unvisited anomaly site."""
    pulse = 0.62 + 0.38 * math.sin(t * 3.0)
    s = pygame.Surface((size, size), pygame.SRCALPHA)
    c = size // 2
    r = int(c * (0.55 + 0.35 * pulse))
    pts = [(c, c - r), (c + r, c), (c, c + r), (c - r, c)]
    pygame.draw.polygon(s, (255, 196, 90, int(120 + 100 * pulse)), pts, 2)
    pygame.draw.circle(s, (255, 196, 90, 230), (c, c), 2)
    return s
