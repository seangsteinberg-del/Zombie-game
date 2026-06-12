"""Procedural colony art (depth update): the base is a PLACE, not a table.

Per-site-kind terrain strips and skies (seeded fBM, day/night aware) and
one drawn sprite per buildable module in game.basebuild.CATALOG — all
pygame.draw primitives rendered at 2x and smoothscaled, cached at module
level, zero asset files. The base scene composes these and animates the
cheap parts (status lights, tank fills, fan angles, drill bob, walkers).
"""

from __future__ import annotations

import math

import numpy as np
import pygame

from aphelion.render.body_art import _fbm
from aphelion.ui.theme import _mix, _seed

_TERRAIN_CACHE: dict[tuple, tuple[pygame.Surface, list[int]]] = {}
_SKY_CACHE: dict[tuple, pygame.Surface] = {}
_MODULE_CACHE: dict[tuple, pygame.Surface] = {}
_WALKER_CACHE: dict[tuple, pygame.Surface] = {}

# ground lo/hi, sky day, sky night, airless (stars always)
_KIND_PAL = {
    "psr_ice": ((86, 88, 100), (148, 152, 166), (10, 12, 20),
                (6, 8, 14), True),
    "mars_ice": ((116, 64, 42), (176, 112, 76), (188, 128, 96),
                 (26, 14, 16), False),
    "aerostat": ((208, 182, 142), (242, 222, 184), (238, 198, 132),
                 (52, 38, 30), False),
    "methane_lake": ((82, 64, 42), (122, 100, 62), (164, 122, 72),
                     (18, 16, 20), False),
    "ice_burrow": ((156, 168, 186), (214, 226, 240), (12, 14, 22),
                   (6, 8, 14), True),
}
_METAL = (158, 166, 180)
_METAL_DARK = (96, 104, 118)
_PANEL_BLUE = (52, 86, 150)


def kind_palette(kind: str):
    return _KIND_PAL.get(kind, _KIND_PAL["psr_ice"])


def sky_strip(kind: str, w: int, h: int, daylight: float) -> pygame.Surface:
    """Vertical sky gradient lerped night->day; stars when dark/airless."""
    key = (kind, w, h, round(daylight, 2))
    hit = _SKY_CACHE.get(key)
    if hit is not None:
        return hit
    lo, hi, day, night, airless = kind_palette(kind)
    dl = 0.0 if airless else max(0.0, min(1.0, daylight))
    top = _mix(night, day, dl * 0.55)
    bot = _mix(night, day, dl)
    g = np.linspace(0.0, 1.0, h)[:, None]
    col = ((1.0 - g) * np.array(top, dtype=float)
           + g * np.array(bot, dtype=float))
    surf = pygame.Surface((w, h))
    pygame.surfarray.blit_array(
        surf, np.repeat(col[None, :, :], w, axis=0).astype("uint8"))
    if airless or dl < 0.35:
        rng = np.random.default_rng(_seed(kind + "stars"))
        n = 90
        xs = rng.integers(0, w, n)
        ys = rng.integers(0, int(h * 0.9), n)
        for x, y in zip(xs, ys):
            v = int(rng.integers(110, 220) * (1.0 - dl))
            if v > 30:
                surf.set_at((int(x), int(y)), (v, v, min(255, v + 18)))
    if len(_SKY_CACHE) > 24:
        _SKY_CACHE.clear()
    _SKY_CACHE[key] = surf
    return surf


def terrain_strip(site_id: str, kind: str, w: int,
                  h: int) -> tuple[pygame.Surface, list[int]]:
    """(surface, ridge_y per column): seeded ground band with relief
    shading; methane_lake gets a liquid horizon band on the right."""
    key = (site_id, kind, w, h)
    hit = _TERRAIN_CACHE.get(key)
    if hit is not None:
        return hit
    lo, hi, _, _, airless = kind_palette(kind)
    rng = np.random.default_rng(_seed(site_id))
    noise = _fbm(rng, 256, octaves=4, base_cells=4)
    row = noise[64]                       # one fBM row as the height line
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    ridge: list[int] = []
    lake_from = int(w * 0.68) if kind == "methane_lake" else w + 1
    for x in range(w):
        nv = float(row[int(x / max(w - 1, 1) * 255)])
        ry = int(h * 0.30 + nv * h * 0.28)
        ridge.append(ry)
        shade = _mix(lo, hi, 0.35 + 0.5 * (1.0 - nv))
        pygame.draw.line(surf, shade, (x, ry), (x, h))
        pygame.draw.line(surf, _mix(shade, (255, 255, 255), 0.25),
                         (x, ry), (x, min(ry + 2, h)))
    if kind == "methane_lake":
        lake_y = max(ridge[lake_from:]) if lake_from < w else h
        for x in range(lake_from, w):
            pygame.draw.line(surf, (26, 34, 44), (x, lake_y), (x, h))
            ridge[x] = lake_y
        for i in range(5):                # specular shimmer bands
            yy = lake_y + 6 + i * 9
            if yy < h:
                pygame.draw.line(surf, (44, 58, 74),
                                 (lake_from + 4, yy), (w - 6, yy))
    # scatter boulders / ice chunks
    for _ in range(26):
        bx = int(rng.integers(0, w))
        if bx >= lake_from:
            continue
        by = ridge[bx] + int(rng.integers(6, max(7, h - ridge[bx] - 2)))
        r = int(rng.integers(1, 4))
        pygame.draw.circle(surf, _mix(lo, (0, 0, 0), 0.25), (bx, by), r)
        pygame.draw.circle(surf, _mix(hi, (255, 255, 255), 0.1),
                           (bx - r // 3, by - r // 3), max(1, r - 1))
    if len(_TERRAIN_CACHE) > 12:
        _TERRAIN_CACHE.clear()
    _TERRAIN_CACHE[key] = (surf, ridge)
    return surf, ridge


def _at2x(draw_fn, w: int, h: int) -> pygame.Surface:
    big = pygame.Surface((w * 2, h * 2), pygame.SRCALPHA)
    draw_fn(big, w * 2, h * 2)
    return pygame.transform.smoothscale(big, (w, h))


def _skid(s, w, h, col=_METAL_DARK):
    pygame.draw.rect(s, col, (int(w * 0.08), h - 10, int(w * 0.84), 6),
                     border_radius=3)
    pygame.draw.rect(s, col, (int(w * 0.16), h - 18, 8, 12))
    pygame.draw.rect(s, col, (int(w * 0.78), h - 18, 8, 12))


def _d_drill(s, w, h):
    _skid(s, w, h)
    top = int(h * 0.10)
    cx = w // 2
    for y0, y1 in ((top, h - 18),):
        pygame.draw.line(s, _METAL, (cx - 14, y0), (cx - 14, y1), 4)
        pygame.draw.line(s, _METAL, (cx + 14, y0), (cx + 14, y1), 4)
        for i in range(6):
            yy = top + i * (y1 - y0) // 6
            pygame.draw.line(s, _METAL_DARK, (cx - 14, yy),
                             (cx + 14, yy + (y1 - y0) // 6), 2)
            pygame.draw.line(s, _METAL_DARK, (cx + 14, yy),
                             (cx - 14, yy + (y1 - y0) // 6), 2)
    pygame.draw.rect(s, _METAL, (cx - 20, top - 8, 40, 14), border_radius=4)
    pygame.draw.polygon(s, (210, 216, 228),
                        [(cx - 5, h - 20), (cx + 5, h - 20), (cx, h - 4)])


def _d_electrolyzer(s, w, h):
    _skid(s, w, h)
    body = pygame.Rect(int(w * 0.14), int(h * 0.34), int(w * 0.72),
                       int(h * 0.46))
    pygame.draw.rect(s, _METAL, body, border_radius=8)
    pygame.draw.rect(s, _METAL_DARK, body, 3, border_radius=8)
    for i in range(3):                    # bubbler windows
        pygame.draw.circle(s, (120, 200, 240),
                           (body.x + 18 + i * 22, body.y + 18), 7)
    pygame.draw.rect(s, _METAL_DARK,
                     (body.right - 10, body.y - 16, 8, 20))
    pygame.draw.rect(s, _METAL_DARK, (body.x + 4, body.y - 10, 8, 14))


def _d_sabatier(s, w, h):
    _skid(s, w, h)
    cyl = pygame.Rect(int(w * 0.10), int(h * 0.42), int(w * 0.80),
                      int(h * 0.30))
    pygame.draw.rect(s, _METAL, cyl, border_radius=14)
    pygame.draw.rect(s, _METAL_DARK, cyl, 3, border_radius=14)
    for i in range(5):                    # reactor fins
        fx = cyl.x + 10 + i * (cyl.w - 20) // 4
        pygame.draw.line(s, (220, 150, 90), (fx, cyl.y - 8),
                         (fx, cyl.bottom + 8), 3)
    pygame.draw.circle(s, (255, 170, 90), (cyl.centerx, cyl.centery), 6)


def _d_co2(s, w, h):
    _skid(s, w, h)
    cx, cy = w // 2, int(h * 0.46)
    pygame.draw.circle(s, _METAL, (cx, cy), int(w * 0.30))
    pygame.draw.circle(s, _METAL_DARK, (cx, cy), int(w * 0.30), 3)
    for k in range(4):                    # fan blades
        a = k * math.pi / 2 + 0.5
        pygame.draw.line(s, _METAL_DARK, (cx, cy),
                         (cx + int(w * 0.24 * math.cos(a)),
                          cy + int(w * 0.24 * math.sin(a))), 5)
    pygame.draw.circle(s, (220, 226, 236), (cx, cy), 5)


def _d_pump(s, w, h):
    _skid(s, w, h)
    house = pygame.Rect(int(w * 0.10), int(h * 0.40), int(w * 0.36),
                        int(h * 0.40))
    pygame.draw.rect(s, _METAL, house, border_radius=6)
    pygame.draw.rect(s, _METAL_DARK, house, 3, border_radius=6)
    pygame.draw.line(s, _METAL, (house.right, house.y + 8),
                     (w - 8, house.y + 14), 6)        # pier arm
    pts = [(w - 10, house.y + 16), (w - 10, h - 8)]
    pygame.draw.lines(s, (70, 90, 110), False, pts, 4)  # hose into liquid


def _d_solar(s, w, h):
    pygame.draw.line(s, _METAL_DARK, (w // 2, h - 8), (w // 2, h // 2), 5)
    for side in (-1, 1):
        panel = pygame.Rect(0, 0, int(w * 0.42), int(h * 0.34))
        panel.center = (w // 2 + side * int(w * 0.26), int(h * 0.36))
        pygame.draw.rect(s, _PANEL_BLUE, panel, border_radius=3)
        pygame.draw.rect(s, (150, 190, 255), panel, 2, border_radius=3)
        for i in range(1, 3):
            pygame.draw.line(s, (120, 160, 230),
                             (panel.x, panel.y + i * panel.h // 3),
                             (panel.right, panel.y + i * panel.h // 3), 1)
        for i in range(1, 4):
            pygame.draw.line(s, (120, 160, 230),
                             (panel.x + i * panel.w // 4, panel.y),
                             (panel.x + i * panel.w // 4, panel.bottom), 1)
    _skid(s, w, h)


def _d_reactor(s, w, h):
    _skid(s, w, h)
    drum = pygame.Rect(int(w * 0.22), int(h * 0.30), int(w * 0.56),
                       int(h * 0.50))
    pygame.draw.rect(s, _METAL_DARK, drum, border_radius=10)
    pygame.draw.rect(s, (60, 66, 78), drum, 3, border_radius=10)
    for i in range(4):                    # cooling fins
        fy = drum.y + 8 + i * (drum.h - 16) // 3
        pygame.draw.line(s, _METAL, (drum.x - 8, fy), (drum.right + 8, fy), 3)
    pygame.draw.circle(s, (130, 240, 170), drum.center, 8)
    pygame.draw.rect(s, (240, 200, 80),
                     (drum.x, drum.bottom - 8, drum.w, 5))


def _d_hab(s, w, h):
    _skid(s, w, h)
    dome = pygame.Rect(int(w * 0.12), int(h * 0.26), int(w * 0.76),
                       int(h * 0.60))
    pygame.draw.ellipse(s, _METAL, dome)
    pygame.draw.ellipse(s, _METAL_DARK, dome, 3)
    for i in range(3):                    # lit windows
        pygame.draw.rect(s, (255, 224, 140),
                         (dome.x + 16 + i * 20, dome.centery, 10, 8),
                         border_radius=2)
    pygame.draw.rect(s, _METAL_DARK,
                     (dome.centerx - 8, dome.bottom - 14, 16, 16),
                     border_radius=3)


def _d_tanks(s, w, h):
    _skid(s, w, h)
    for i, r in enumerate((int(w * 0.16),) * 3):
        cx = int(w * 0.20) + i * int(w * 0.30)
        cy = h - 22 - r
        pygame.draw.circle(s, _METAL, (cx, cy), r)
        pygame.draw.circle(s, _METAL_DARK, (cx, cy), r, 3)
        pygame.draw.circle(s, (220, 228, 240),
                           (cx - r // 3, cy - r // 3), max(2, r // 4))


def _d_battery(s, w, h):
    _skid(s, w, h)
    box = pygame.Rect(int(w * 0.16), int(h * 0.40), int(w * 0.68),
                      int(h * 0.40))
    pygame.draw.rect(s, _METAL_DARK, box, border_radius=6)
    pygame.draw.rect(s, (60, 66, 78), box, 3, border_radius=6)
    for i in range(4):                    # cell stripes
        pygame.draw.rect(s, (110, 220, 140),
                         (box.x + 8 + i * (box.w - 16) // 4, box.y + 8,
                          (box.w - 24) // 4, box.h - 16), border_radius=3)
    pygame.draw.polygon(s, (255, 230, 120),
                        [(box.centerx + 2, box.y - 14),
                         (box.centerx - 8, box.y + 4),
                         (box.centerx, box.y + 4),
                         (box.centerx - 2, box.y + 16),
                         (box.centerx + 8, box.y - 2),
                         (box.centerx, box.y - 2)])


def _d_radiator(s, w, h):
    _skid(s, w, h)
    for side in (-1, 1):
        panel = pygame.Rect(0, 0, int(w * 0.40), int(h * 0.46))
        panel.center = (w // 2 + side * int(w * 0.24), int(h * 0.42))
        pygame.draw.rect(s, (228, 232, 240), panel, border_radius=3)
        pygame.draw.rect(s, _METAL_DARK, panel, 2, border_radius=3)
        for i in range(1, 5):
            pygame.draw.line(s, (190, 196, 210),
                             (panel.x, panel.y + i * panel.h // 5),
                             (panel.right, panel.y + i * panel.h // 5), 1)
    pygame.draw.line(s, _METAL_DARK, (w // 2, h - 8), (w // 2, h // 3), 5)


def _d_lab(s, w, h):
    _skid(s, w, h)
    box = pygame.Rect(int(w * 0.14), int(h * 0.40), int(w * 0.56),
                      int(h * 0.40))
    pygame.draw.rect(s, _METAL, box, border_radius=6)
    pygame.draw.rect(s, _METAL_DARK, box, 3, border_radius=6)
    pygame.draw.rect(s, (140, 235, 255), (box.x + 10, box.y + 10,
                                          box.w - 20, 10), border_radius=3)
    cx = int(w * 0.80)
    pygame.draw.line(s, _METAL_DARK, (cx, box.y), (cx, box.y - 18), 3)
    pygame.draw.arc(s, (220, 226, 236),
                    pygame.Rect(cx - 12, box.y - 34, 24, 20),
                    math.pi * 0.15, math.pi * 0.85, 3)


def _d_foundry(s, w, h):
    """05 fab family: a long mill shed with a hot pour glow + stack."""
    _skid(s, w, h)
    shed = pygame.Rect(int(w * 0.08), int(h * 0.36), int(w * 0.84),
                       int(h * 0.44))
    pygame.draw.rect(s, _METAL, shed, border_radius=6)
    pygame.draw.rect(s, _METAL_DARK, shed, 3, border_radius=6)
    pygame.draw.polygon(s, _METAL_DARK,                   # sawtooth roof
                        [(shed.x, shed.y), (shed.x + shed.w // 3,
                                            shed.y - 12),
                         (shed.x + shed.w // 3, shed.y),
                         (shed.x + 2 * shed.w // 3, shed.y - 12),
                         (shed.x + 2 * shed.w // 3, shed.y),
                         (shed.right, shed.y - 12), (shed.right, shed.y)])
    pygame.draw.rect(s, (255, 150, 60),                   # pour glow door
                     (shed.x + 8, shed.bottom - 22, 18, 18))
    pygame.draw.rect(s, _METAL_DARK, (shed.right - 18, shed.y - 26, 9, 28))


def _d_robot(s, w, h):
    """A small wheeled worker robot parked by its charge post."""
    base_y = int(h * 0.80)
    pygame.draw.rect(s, _METAL_DARK, (int(w * 0.62), base_y - 34, 6, 34))
    pygame.draw.circle(s, (120, 220, 160), (int(w * 0.62) + 3,
                                            base_y - 36), 4)
    body = pygame.Rect(int(w * 0.22), base_y - 26, int(w * 0.30), 18)
    pygame.draw.rect(s, _METAL, body, border_radius=5)
    pygame.draw.rect(s, _METAL_DARK, body, 2, border_radius=5)
    for wx in (body.x + 6, body.right - 6):
        pygame.draw.circle(s, _METAL_DARK, (wx, base_y - 4), 6)
    pygame.draw.line(s, _METAL_DARK, (body.centerx, body.y),
                     (body.centerx + 12, body.y - 14), 3)   # arm
    pygame.draw.circle(s, (255, 190, 90), (body.centerx + 13,
                                           body.y - 15), 3)


def _d_recycler(s, w, h):
    """RX-22: a sorting hopper over the reclaimed-stock bins."""
    _skid(s, w, h)
    hop = pygame.Rect(int(w * 0.18), int(h * 0.34), int(w * 0.34),
                      int(h * 0.30))
    pygame.draw.polygon(s, _METAL, [(hop.x, hop.y), (hop.right, hop.y),
                                    (hop.centerx + 8, hop.bottom),
                                    (hop.centerx - 8, hop.bottom)])
    pygame.draw.polygon(s, _METAL_DARK,
                        [(hop.x, hop.y), (hop.right, hop.y),
                         (hop.centerx + 8, hop.bottom),
                         (hop.centerx - 8, hop.bottom)], 3)
    for i, col in enumerate(((150, 150, 160), (200, 120, 70),
                             (110, 170, 110))):
        pygame.draw.rect(s, col, (int(w * 0.58) + i * 11,
                                  int(h * 0.62), 9, 16))


_DRAWERS = {
    "drill_ice": _d_drill, "electrolyzer": _d_electrolyzer,
    "sabatier": _d_sabatier, "co2_intake": _d_co2, "lake_pump": _d_pump,
    "solar_array": _d_solar, "reactor_100": _d_reactor,
    "hab_module": _d_hab, "tank_farm": _d_tanks,
    "battery_pack": _d_battery, "radiator_wing": _d_radiator,
    "science_lab": _d_lab,
    "fab_foundry_mill": _d_foundry, "fab_machine_shop": _d_foundry,
    "fab_chem_plant": _d_sabatier, "fab_elec_assy": _d_lab,
    "fab_assembly_hall": _d_foundry, "fab_waam": _d_foundry,
    "fab_wafer_fab": _d_lab, "fab_printer_poly": _d_lab,
    "fab_printer_lpbf": _d_lab,
    "recycler": _d_recycler, "bot_worker": _d_robot, "bot_mule": _d_robot,
}


def module_sprite(key: str, w: int = 88, h: int = 96) -> pygame.Surface:
    """The drawn structure for one CATALOG module key."""
    ck = (key, w, h)
    hit = _MODULE_CACHE.get(ck)
    if hit is not None:
        return hit
    drawer = _DRAWERS.get(key, _d_electrolyzer)
    surf = _at2x(drawer, w, h)
    _MODULE_CACHE[ck] = surf
    return surf


def walker_sprite(name: str, frame: int, size: int = 18) -> pygame.Surface:
    """A two-frame suited colonist, tinted per crew member."""
    ck = (name, frame % 2, size)
    hit = _WALKER_CACHE.get(ck)
    if hit is not None:
        return hit
    rng = np.random.default_rng(_seed(name))
    suit = ((205, 92, 60), (72, 108, 178), (108, 138, 92), (148, 118, 178),
            (186, 158, 72))[int(rng.integers(5))]

    def draw(s, w, h):
        cx = w // 2
        pygame.draw.circle(s, (230, 234, 242), (cx, int(h * 0.22)),
                           int(h * 0.16))
        pygame.draw.rect(s, suit, (cx - int(w * 0.18), int(h * 0.32),
                                   int(w * 0.36), int(h * 0.38)),
                         border_radius=4)
        spread = int(w * 0.16) if frame % 2 == 0 else int(w * 0.06)
        for side in (-1, 1):
            pygame.draw.line(s, suit, (cx, int(h * 0.66)),
                             (cx + side * spread, h - 2), 4)

    surf = _at2x(draw, size, size + 4)
    _WALKER_CACHE[ck] = surf
    return surf
