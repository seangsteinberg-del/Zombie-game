"""V5 vehicle sprites (MISSION FILM machine layer): side-view ground
vehicles + the Titan submarine, built from engineered shapes — hull
gradients, wheel/bogie detail, international-orange accents, gold MLI
on cryo gear, dark glass visors/ports. The DRIVE/DIVE scenes blit these
over the tile worlds; contact shadows are drawn by the scene (it knows
the ground line). Cached per (catalog_id, px_per_m, facing)."""

from __future__ import annotations

import math

import pygame

_CACHE: dict = {}

_HULL_LO = (148, 154, 166)
_HULL_HI = (214, 220, 230)
_GRAPHITE = (64, 70, 82)
_ORANGE = (208, 96, 44)
_GOLD = (188, 156, 84)
_GLASS = (28, 38, 52)


def _vgrad(s, rect, top, bot):
    x, y, w, h = rect
    col = pygame.Surface((1, max(1, h)))
    for i in range(h):
        f = i / max(1, h - 1)
        col.set_at((0, i), tuple(int(top[c] + (bot[c] - top[c]) * f)
                                 for c in range(3)))
    s.blit(pygame.transform.scale(col, (w, h)), (x, y))


def _wheel(s, cx, cy, r, mesh=True):
    pygame.draw.circle(s, (26, 30, 38), (cx, cy), r)
    pygame.draw.circle(s, (96, 102, 114), (cx, cy), r, max(2, r // 5))
    if mesh:
        for k in range(6):
            a = k * math.pi / 3.0
            pygame.draw.line(s, (96, 102, 114), (cx, cy),
                             (cx + int((r - 2) * math.cos(a)),
                              cy + int((r - 2) * math.sin(a))), 2)
    pygame.draw.circle(s, (140, 146, 158), (cx, cy), max(2, r // 4))


def _rover_cart(s, w, h, ppm):
    """LRV-class: open frame, two seats, dish antenna, mesh wheels."""
    gy = h - int(0.45 * ppm)                        # axle line
    fr = int(0.32 * ppm)                            # wheel radius
    _vgrad(s, (int(0.30 * ppm), gy - int(0.55 * ppm),
               int(2.5 * ppm), int(0.22 * ppm)), _HULL_HI, _HULL_LO)
    pygame.draw.rect(s, _GRAPHITE, (int(0.30 * ppm), gy - int(0.36 * ppm),
                                    int(2.5 * ppm), int(0.10 * ppm)))
    for sx in (0.85, 1.55):                         # seat frames
        x = int(sx * ppm)
        pygame.draw.rect(s, _GOLD, (x, gy - int(0.95 * ppm),
                                    int(0.34 * ppm), int(0.42 * ppm)),
                         border_radius=3)
        pygame.draw.rect(s, _GRAPHITE, (x, gy - int(0.95 * ppm),
                                        int(0.34 * ppm), int(0.42 * ppm)),
                         2, border_radius=3)
    pygame.draw.line(s, (170, 176, 188), (int(2.45 * ppm), gy - int(0.55 * ppm)),
                     (int(2.65 * ppm), gy - int(1.25 * ppm)), 3)
    pygame.draw.circle(s, (225, 228, 235),
                       (int(2.70 * ppm), gy - int(1.30 * ppm)),
                       int(0.18 * ppm), 3)          # dish
    pygame.draw.rect(s, _ORANGE, (int(0.30 * ppm), gy - int(0.40 * ppm),
                                  int(0.45 * ppm), int(0.07 * ppm)))
    _wheel(s, int(0.62 * ppm), gy, fr)
    _wheel(s, int(2.42 * ppm), gy, fr)


def _rover_press(s, w, h, ppm):
    """SEV-class pressurized cabin: white body, dark glass nose, ports."""
    gy = h - int(0.50 * ppm)
    body = (int(0.25 * ppm), gy - int(1.55 * ppm),
            int(3.6 * ppm), int(1.35 * ppm))
    _vgrad(s, body, _HULL_HI, _HULL_LO)
    pygame.draw.rect(s, _GRAPHITE, body, 2, border_radius=8)
    pygame.draw.rect(s, _GLASS, (body[0] + body[2] - int(0.78 * ppm),
                                 body[1] + int(0.14 * ppm),
                                 int(0.62 * ppm), int(0.62 * ppm)),
                     border_radius=6)               # cockpit glass
    pygame.draw.rect(s, (120, 170, 210),
                     (body[0] + body[2] - int(0.74 * ppm),
                      body[1] + int(0.18 * ppm),
                      int(0.20 * ppm), int(0.10 * ppm)),
                     border_radius=2)               # glass catch-light
    for px in range(3):                             # portholes
        pygame.draw.circle(s, _GLASS,
                           (body[0] + int((0.55 + px * 0.75) * ppm),
                            body[1] + int(0.45 * ppm)), int(0.14 * ppm))
    pygame.draw.rect(s, _ORANGE, (body[0], body[1] + body[3] - int(0.18 * ppm),
                                  body[2], int(0.09 * ppm)))
    for line_x in range(body[0] + int(0.9 * ppm),
                        body[0] + body[2], int(0.9 * ppm)):
        pygame.draw.line(s, (120, 126, 140), (line_x, body[1] + 3),
                         (line_x, body[1] + body[3] - 3), 1)
    fr = int(0.34 * ppm)
    for wx in (0.75, 1.85, 2.95):
        _wheel(s, int(wx * ppm + 0.25 * ppm), gy, fr, mesh=False)


def _hauler(s, w, h, ppm):
    """HAUL-class: cab + flatbed + big wheels, work lights."""
    gy = h - int(0.55 * ppm)
    pygame.draw.rect(s, _GRAPHITE, (int(0.30 * ppm), gy - int(0.62 * ppm),
                                    int(4.4 * ppm), int(0.18 * ppm)))
    _vgrad(s, (int(0.30 * ppm), gy - int(0.92 * ppm),
               int(4.4 * ppm), int(0.30 * ppm)), (110, 116, 128), (84, 90, 102))
    cab = (int(3.85 * ppm), gy - int(1.55 * ppm),
           int(0.95 * ppm), int(0.95 * ppm))
    _vgrad(s, cab, _HULL_HI, _HULL_LO)
    pygame.draw.rect(s, _GRAPHITE, cab, 2, border_radius=5)
    pygame.draw.rect(s, _GLASS, (cab[0] + int(0.45 * ppm), cab[1] + 4,
                                 int(0.42 * ppm), int(0.4 * ppm)),
                     border_radius=4)
    pygame.draw.rect(s, _ORANGE, (cab[0], cab[1] + cab[3] - 7, cab[2], 5))
    pygame.draw.circle(s, (255, 236, 190), (cab[0] + cab[2] - 4,
                                            cab[1] + int(0.5 * ppm)), 3)
    fr = int(0.42 * ppm)
    for wx in (0.85, 1.95, 3.05, 4.15):
        _wheel(s, int(wx * ppm), gy, fr, mesh=False)


def _submarine(s, w, h, ppm):
    """SUB-T: graphite pressure hull, dorsal fin mast, prop, ballast."""
    gy = h // 2
    hull = (int(0.2 * ppm), gy - int(0.55 * ppm),
            int(5.4 * ppm), int(1.1 * ppm))
    _vgrad(s, hull, (88, 96, 110), (52, 58, 70))
    pygame.draw.ellipse(s, (38, 44, 56), hull, 3)
    pygame.draw.ellipse(s, (118, 126, 140),
                        (hull[0] + 4, hull[1] + 4, hull[2] - 8,
                         int(0.30 * ppm)), 2)       # top catch-light
    pygame.draw.polygon(s, (70, 78, 92), (
        (int(2.4 * ppm), hull[1]), (int(2.9 * ppm), hull[1] - int(0.6 * ppm)),
        (int(3.3 * ppm), hull[1])))                 # dorsal fin (SUB-FIN)
    pygame.draw.circle(s, (255, 200, 120), (int(3.0 * ppm),
                                            hull[1] - int(0.5 * ppm)), 3)
    for px in range(3):                             # viewports
        pygame.draw.circle(s, (160, 220, 240),
                           (int((0.9 + px * 0.5) * ppm), gy),
                           int(0.09 * ppm))
    pygame.draw.rect(s, _ORANGE, (int(4.4 * ppm), gy - int(0.1 * ppm),
                                  int(0.5 * ppm), int(0.2 * ppm)))
    for blade in (-1, 1):                           # prop
        pygame.draw.ellipse(s, (130, 138, 152),
                            (int(5.55 * ppm), gy - (int(0.34 * ppm)
                                                    if blade < 0 else 0),
                             int(0.16 * ppm), int(0.34 * ppm)))


_DRAWERS = {
    "rvr_lrv": (_rover_cart, 3.0, 2.0),
    "rvr_scout": (_rover_cart, 3.0, 2.0),
    "rvr_mule": (_rover_cart, 3.0, 2.0),
    "rvr_press": (_rover_press, 4.2, 2.2),
    "rvr_haul10": (_hauler, 5.2, 2.2),
    "rvr_haul40": (_hauler, 5.2, 2.2),
    "rvr_crawl": (_hauler, 5.2, 2.2),
    "sub_t": (_submarine, 6.0, 2.4),
    "boat_t": (_submarine, 6.0, 2.4),
}


def vehicle_sprite(catalog_id: str, ppm: float,
                   facing: int = 1) -> pygame.Surface:
    """Side-view sprite at ppm px/m, facing +1 right / -1 left."""
    kind = catalog_id.rsplit(":", 1)[-1]
    drawer, wm, hm = _DRAWERS.get(kind, _DRAWERS["rvr_press"])
    key = (kind, int(ppm * 4), facing)
    got = _CACHE.get(key)
    if got is None:
        w, h = int(wm * ppm) + 4, int(hm * ppm) + 4
        s = pygame.Surface((w, h), pygame.SRCALPHA)
        drawer(s, w, h, ppm)
        if facing < 0:
            s = pygame.transform.flip(s, True, False)
        _CACHE[key] = got = s
    return got


def headlight_beam(ppm: float, facing: int = 1) -> pygame.Surface:
    """Additive forward light cone for night driving / dark seas."""
    key = ("beam", int(ppm * 4), facing)
    got = _CACHE.get(key)
    if got is None:
        w, h = int(6.0 * ppm), int(2.6 * ppm)
        s = pygame.Surface((w, h))
        for i in range(w):
            f = i / w
            half = int((0.18 + 0.85 * f) * ppm)
            val = int(46 * (1.0 - f) ** 1.4)
            pygame.draw.line(s, (val, max(0, val - 6), max(0, val - 14)),
                             (i, h // 2 - half), (i, h // 2 + half))
        if facing < 0:
            s = pygame.transform.flip(s, True, False)
        _CACHE[key] = got = s
    return got
