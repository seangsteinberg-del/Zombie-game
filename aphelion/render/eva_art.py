"""EVA-scale procedural art: the hero astronaut (walk cycle, gold visor,
PLSS pack), planted flags and the anomaly marker. Drawn at 4x and
smoothscaled like base_art; everything cached and deterministic.

ART-DIRECTION §1.2: NASA-white suit shaded by a real light direction
(sun high-left), INTERNATIONAL ORANGE accents, dark gold-tinted visor
with one hard reflection, graphite hardware, and a contact shadow under
the boots — nothing floats."""

from __future__ import annotations

import math

import pygame

_SUIT = (225, 227, 233)          # NASA white, mid tone
_SUIT_HI = (246, 247, 250)       # sunlit crown
_SUIT_SH = (172, 176, 188)       # shade side
_SUIT_DK = (124, 128, 142)       # deep folds, seams, far limbs
_VISOR = (40, 32, 22)            # gold-tinted glass, near-black
_VISOR_GOLD = (112, 84, 42)      # the tint where light grazes it
_PLSS = (192, 196, 204)
_ACCENT = (214, 84, 38)          # international orange
_ACCENT_SH = (150, 56, 24)
_GRAPHITE = (54, 57, 66)
_GRAPHITE_HI = (104, 108, 120)

_CACHE: dict = {}


def _limb(s: pygame.Surface, a: tuple, b: tuple, w: int,
          back: bool = False) -> None:
    """One suit limb segment: cylinder read — dark base, lit core, thin
    highlight on the sun (upper-left) side."""
    dark = _SUIT_DK if back else _SUIT_SH
    main = _SUIT_SH if back else _SUIT
    lite = _SUIT if back else _SUIT_HI
    pygame.draw.line(s, dark, a, b, w)
    pygame.draw.line(s, main, (a[0] - 1, a[1] - 1), (b[0] - 1, b[1] - 1),
                     max(2, w - 4))
    pygame.draw.line(s, lite, (a[0] - w // 4, a[1] - 2),
                     (b[0] - w // 4, b[1] - 2), max(1, w // 4))


def _boot(s: pygame.Surface, x: float, y: float, back: bool = False) -> None:
    col = _SUIT_SH if back else _SUIT
    pygame.draw.ellipse(s, col, (x - 9, y - 7, 24, 10))
    pygame.draw.rect(s, _GRAPHITE, (x - 9, y - 1, 24, 4), border_radius=2)
    pygame.draw.line(s, _SUIT_DK if back else _SUIT_SH,
                     (x - 7, y + 1), (x + 13, y + 1), 1)
    if not back:
        pygame.draw.line(s, _SUIT_HI, (x - 5, y - 5), (x + 9, y - 5), 2)


def astronaut(phase: int, facing: int, airborne: bool = False,
              h_px: int = 34) -> pygame.Surface:
    """Walk-cycle astronaut, side view. phase 0..3; facing ±1."""
    key = ("walker", phase & 3, facing, airborne, h_px)
    got = _CACHE.get(key)
    if got is not None:
        return got
    w2, h2 = 96, 136                      # 4x canvas
    s = pygame.Surface((w2, h2), pygame.SRCALPHA)
    ph = phase & 3
    swing = [-14, 0, 14, 0][ph] if not airborne else 20
    sw_a = [10, 0, -10, 0][ph] if not airborne else -16
    hip = (44, 88)
    ground_y = 126

    # contact shadow FIRST — the boots press on the regolith (rule zero)
    if not airborne:
        pygame.draw.ellipse(s, (0, 0, 0, 42), (10, 123, 76, 9))
        pygame.draw.ellipse(s, (0, 0, 0, 80), (19, 122, 58, 10))

    # far arm (behind pack and torso)
    sh_b = (40, 52)
    elb_b = (43 - sw_a * 0.4, 68)
    hnd_b = (41 - sw_a, 84)
    _limb(s, sh_b, elb_b, 11, back=True)
    _limb(s, elb_b, hnd_b, 10, back=True)
    pygame.draw.circle(s, _SUIT_DK, (int(hnd_b[0]), int(hnd_b[1])), 6)

    # legs (far leg first)
    for leg, dx in ((0, -swing), (1, swing)):
        back = leg == 0
        knee = (hip[0] + dx * 0.45, hip[1] + 20)
        if airborne:
            fy = h2 - 18 - leg * 8
        else:
            fy = ground_y - (4 if (ph in (1, 3) and leg == 0) else 0)
        foot = (hip[0] + dx, fy)
        _limb(s, hip, knee, 15, back=back)
        pygame.draw.circle(s, _SUIT_DK if back else _SUIT_SH,
                           (int(knee[0]), int(knee[1])), 6)
        _limb(s, knee, foot, 13, back=back)
        _boot(s, foot[0], foot[1], back=back)
        # orange thigh band (crew ID accent)
        bx = hip[0] + (knee[0] - hip[0]) * 0.55
        by = hip[1] + (knee[1] - hip[1]) * 0.55
        pygame.draw.line(s, _ACCENT_SH if back else _ACCENT,
                         (bx - 6, by), (bx + 6, by), 4)

    # PLSS backpack: gradient slab, panel lines, antenna, orange handle
    pygame.draw.rect(s, (148, 152, 164), (6, 36, 24, 54), border_radius=4)
    pygame.draw.rect(s, _PLSS, (7, 37, 21, 50), border_radius=4)
    pygame.draw.rect(s, (212, 216, 224), (7, 37, 21, 12), border_radius=4)
    pygame.draw.rect(s, (160, 164, 176), (7, 75, 21, 12), border_radius=4)
    for ly in (52, 62, 72):
        pygame.draw.line(s, (138, 142, 154), (9, ly), (26, ly), 2)
    pygame.draw.rect(s, _GRAPHITE, (9, 31, 17, 6), border_radius=2)
    pygame.draw.line(s, _GRAPHITE, (12, 31), (12, 18), 2)
    pygame.draw.rect(s, _ACCENT, (7, 44, 3, 22))

    # torso: white shell, sun gradient, seam shadow against the pack
    pygame.draw.rect(s, _SUIT_SH, (26, 42, 40, 52), border_radius=13)
    pygame.draw.rect(s, _SUIT, (26, 42, 38, 50), border_radius=12)
    pygame.draw.rect(s, _SUIT_HI, (28, 43, 32, 14), border_radius=10)
    pygame.draw.rect(s, _SUIT_SH, (26, 78, 38, 14), border_radius=8)
    pygame.draw.line(s, _SUIT_DK, (28, 46), (28, 86), 2)
    pygame.draw.rect(s, _SUIT_DK, (26, 86, 38, 7), border_radius=4)
    # chest stripe + display/control module (graphite, lip highlight)
    pygame.draw.rect(s, _ACCENT, (28, 50, 34, 5))
    pygame.draw.rect(s, _ACCENT_SH, (28, 53, 34, 2))
    pygame.draw.rect(s, _GRAPHITE, (42, 60, 18, 13), border_radius=2)
    pygame.draw.line(s, _GRAPHITE_HI, (43, 61), (58, 61), 1)
    pygame.draw.circle(s, (208, 168, 92), (47, 66), 2)
    pygame.draw.circle(s, (90, 94, 106), (54, 66), 2)

    # near arm with orange band and glove
    sh_f = (52, 52)
    elb_f = (56 + sw_a * 0.4, 68)
    hnd_f = (54 + sw_a, 84)
    _limb(s, sh_f, elb_f, 12)
    pygame.draw.circle(s, _SUIT_SH, (int(elb_f[0]), int(elb_f[1])), 5)
    _limb(s, elb_f, hnd_f, 11)
    bx = sh_f[0] + (elb_f[0] - sh_f[0]) * 0.4
    by = sh_f[1] + (elb_f[1] - sh_f[1]) * 0.4
    pygame.draw.line(s, _ACCENT, (bx - 6, by), (bx + 6, by), 4)
    pygame.draw.circle(s, _SUIT, (int(hnd_f[0]), int(hnd_f[1])), 6)
    pygame.draw.line(s, _SUIT_DK, (hnd_f[0] - 5, hnd_f[1] - 4),
                     (hnd_f[0] + 5, hnd_f[1] - 4), 2)

    # neck ring, helmet shell, gold visor with one hard reflection
    pygame.draw.rect(s, _GRAPHITE, (40, 38, 20, 6), border_radius=3)
    pygame.draw.line(s, _GRAPHITE_HI, (42, 39), (58, 39), 1)
    pygame.draw.circle(s, _SUIT_SH, (50, 24), 20)
    pygame.draw.circle(s, _SUIT, (48, 22), 18)
    pygame.draw.circle(s, _SUIT_HI, (43, 16), 7)
    pygame.draw.circle(s, (110, 114, 126), (58, 25), 13)     # visor rim
    pygame.draw.circle(s, _VISOR, (58, 25), 11)
    pygame.draw.circle(s, _VISOR_GOLD, (59, 21), 7)          # grazing gold
    pygame.draw.circle(s, _VISOR, (59, 27), 8)               # glass falls dark
    pygame.draw.ellipse(s, (232, 222, 198), (60, 17, 6, 4))  # reflection
    pygame.draw.circle(s, (252, 248, 240), (64, 19), 1)
    # helmet lamp (a genuine emitter — the only bright speck)
    pygame.draw.rect(s, _GRAPHITE, (56, 5, 11, 7), border_radius=2)
    pygame.draw.line(s, _GRAPHITE_HI, (57, 6), (65, 6), 1)
    pygame.draw.circle(s, (255, 232, 184), (66, 8), 2)

    out = pygame.transform.smoothscale(s, (int(w2 * h_px / h2), h_px))
    if facing < 0:
        out = pygame.transform.flip(out, True, False)
    _CACHE[key] = out
    return out


_FLIGHT = (92, 112, 138)         # flight-suit blue-grey
_FLIGHT_HI = (132, 154, 182)
_FLIGHT_SH = (60, 76, 98)
_SKIN = (226, 182, 146)
_SKIN_SH = (190, 144, 112)
_HAIR = (58, 46, 38)


def _flimb(s, a, b, w, back=False):
    dark = _FLIGHT_SH if back else _FLIGHT_SH
    main = _FLIGHT_SH if back else _FLIGHT
    lite = _FLIGHT if back else _FLIGHT_HI
    pygame.draw.line(s, dark, a, b, w)
    pygame.draw.line(s, main, (a[0] - 1, a[1] - 1), (b[0] - 1, b[1] - 1),
                     max(2, w - 3))
    pygame.draw.line(s, lite, (a[0] - w // 4, a[1] - 1),
                     (b[0] - w // 4, b[1] - 1), max(1, w // 4))


def crew_indoor(phase: int, facing: int, airborne: bool = False,
                h_px: int = 34) -> pygame.Surface:
    """Shirtsleeve crew member (no suit) for pressurised interiors: flight
    suit, bare head with a headset — same walk cycle as the EVA astronaut."""
    key = ("indoor", phase & 3, facing, h_px)
    got = _CACHE.get(key)
    if got is not None:
        return got
    w2, h2 = 96, 136
    s = pygame.Surface((w2, h2), pygame.SRCALPHA)
    ph = phase & 3
    swing = [-12, 0, 12, 0][ph]
    sw_a = [8, 0, -8, 0][ph]
    hip = (44, 86)
    ground_y = 126
    pygame.draw.ellipse(s, (0, 0, 0, 42), (16, 123, 64, 8))
    pygame.draw.ellipse(s, (0, 0, 0, 78), (24, 122, 48, 9))
    # far arm
    sh_b, elb_b = (42, 52), (44 - sw_a * 0.4, 68)
    hnd_b = (42 - sw_a, 84)
    _flimb(s, sh_b, elb_b, 8, back=True)
    _flimb(s, elb_b, hnd_b, 7, back=True)
    pygame.draw.circle(s, _SKIN_SH, (int(hnd_b[0]), int(hnd_b[1])), 4)
    # legs
    for leg, dx in ((0, -swing), (1, swing)):
        back = leg == 0
        knee = (hip[0] + dx * 0.45, hip[1] + 20)
        fy = ground_y - (4 if (ph in (1, 3) and leg == 0) else 0)
        foot = (hip[0] + dx, fy)
        _flimb(s, hip, knee, 12, back=back)
        pygame.draw.circle(s, _FLIGHT_SH if back else _FLIGHT,
                           (int(knee[0]), int(knee[1])), 5)
        _flimb(s, knee, foot, 10, back=back)
        pygame.draw.ellipse(s, (40, 42, 50),
                            (int(foot[0]) - 8, int(foot[1]) - 4, 20, 8))
    # torso: flight suit, zipper, mission patch + name tag
    pygame.draw.rect(s, _FLIGHT_SH, (28, 44, 36, 48), border_radius=10)
    pygame.draw.rect(s, _FLIGHT, (28, 44, 34, 46), border_radius=9)
    pygame.draw.rect(s, _FLIGHT_HI, (30, 45, 28, 12), border_radius=8)
    pygame.draw.line(s, _FLIGHT_SH, (45, 46), (45, 88), 1)
    pygame.draw.rect(s, _ACCENT, (30, 50, 9, 5))            # mission patch
    pygame.draw.rect(s, (210, 214, 222), (48, 58, 12, 3))  # name tag
    # near arm
    sh_f, elb_f = (52, 52), (56 + sw_a * 0.4, 68)
    hnd_f = (54 + sw_a, 84)
    _flimb(s, sh_f, elb_f, 9)
    _flimb(s, elb_f, hnd_f, 8)
    pygame.draw.circle(s, _SKIN, (int(hnd_f[0]), int(hnd_f[1])), 4)
    # head: skin, hair cap, headset, an eye
    pygame.draw.circle(s, _SKIN_SH, (51, 30), 12)
    pygame.draw.circle(s, _SKIN, (50, 28), 11)
    pygame.draw.circle(s, _HAIR, (48, 23), 11)             # hair
    pygame.draw.circle(s, _SKIN, (53, 30), 9)              # carve the face
    pygame.draw.circle(s, _SKIN_SH, (60, 30), 1)           # nose
    pygame.draw.circle(s, _GRAPHITE, (57, 28), 1)          # eye
    pygame.draw.arc(s, _GRAPHITE, (39, 15, 23, 23), 0.3, math.pi - 0.1, 2)
    pygame.draw.circle(s, (44, 48, 56), (55, 33), 2)       # earpiece
    pygame.draw.line(s, _GRAPHITE_HI, (55, 33), (61, 34), 1)  # mic boom
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
    s = pygame.Surface((72, 120), pygame.SRCALPHA)
    # contact shadow at the pole base — the flag is PLANTED
    pygame.draw.ellipse(s, (0, 0, 0, 70), (3, 112, 20, 6))
    # aluminium pole: shade side, body, sun-side glint, finial
    pygame.draw.rect(s, (104, 108, 118), (13, 8, 2, 108))
    pygame.draw.rect(s, (186, 190, 200), (10, 8, 3, 108))
    pygame.draw.line(s, (226, 230, 238), (10, 8), (10, 114), 1)
    pygame.draw.circle(s, (212, 216, 226), (12, 6), 3)
    pygame.draw.line(s, (150, 154, 164), (14, 10), (66, 14), 2)  # batten
    # cloth: international orange, lit top edge, one soft fold, white band
    pygame.draw.polygon(s, _ACCENT, [(15, 11), (66, 14), (65, 36), (15, 40)])
    pygame.draw.polygon(s, (236, 122, 64),
                        [(15, 11), (66, 14), (66, 21), (15, 18)])
    pygame.draw.polygon(s, (234, 236, 240),
                        [(15, 22), (66, 25), (66, 30), (15, 28)])
    pygame.draw.polygon(s, (90, 40, 20, 44),
                        [(37, 13), (43, 14), (40, 38), (34, 39)])
    pygame.draw.line(s, _ACCENT_SH, (15, 40), (65, 36), 2)
    out = pygame.transform.smoothscale(s, (int(36 * h_px / 60), h_px))
    _CACHE[key] = out
    return out


def anomaly_marker(t: float, size: int = 26) -> pygame.Surface:
    """Pulsing survey diamond over an unvisited anomaly site (instrument
    layer: amber line work on glass, no fill, no glow)."""
    pulse = 0.62 + 0.38 * math.sin(t * 3.0)
    s = pygame.Surface((size, size), pygame.SRCALPHA)
    c = size // 2
    r = int(c * (0.55 + 0.35 * pulse))
    pts = [(c, c - r), (c + r, c), (c, c + r), (c - r, c)]
    a = int(120 + 100 * pulse)
    pygame.draw.polygon(s, (255, 196, 90, max(0, (a - 96) // 4)), pts)
    pygame.draw.polygon(s, (255, 196, 90, a), pts, 2)
    tick = max(2, size // 9)
    for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0)):
        pygame.draw.line(s, (255, 196, 90, a),
                         (c + dx * (r + 1), c + dy * (r + 1)),
                         (c + dx * (r + tick), c + dy * (r + tick)), 1)
    pygame.draw.circle(s, (255, 196, 90, 230), (c, c), 2)
    return s
