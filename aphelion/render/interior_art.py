"""Walkable hab interiors: a side-view cutaway strip, one room per built
habitable module, drawn procedurally in the colony's idiom — bunks in the
habs, planters under grow-lights in the greenhouse, the med bay's cross,
bare sintered rock in a regolith vault. Cached per (built tuple)."""

from __future__ import annotations

import pygame

ROOM_W = 288          # px per room (12 m at 24 px/m)
ROOM_H = 224
FLOOR_Y = 196         # walking line inside the strip

_WALL = (44, 52, 66)
_WALL_LIT = (58, 68, 86)
_FLOOR = (70, 78, 94)
_TRIM = (108, 122, 146)
_GLOW = (255, 224, 150)

_CACHE: dict = {}

HABITABLE = ("hab_module", "hab_rigid", "hab_inflatable", "regolith_vault",
             "basalt_hab", "med_bay", "greenhouse", "bio_farm",
             "machine_shop", "science_lab")


def _room_base(s: pygame.Surface, x0: int, vault: bool = False) -> None:
    wall = (62, 56, 50) if vault else _WALL
    pygame.draw.rect(s, wall, (x0, 0, ROOM_W, ROOM_H))
    if vault:
        for i in range(7):                       # sintered courses
            pygame.draw.line(s, (50, 45, 40), (x0, 28 * i),
                             (x0 + ROOM_W, 28 * i), 2)
    else:
        for px in range(x0 + 8, x0 + ROOM_W, 48):   # wall panels
            pygame.draw.rect(s, _WALL_LIT, (px, 16, 40, FLOOR_Y - 32),
                             border_radius=4)
    pygame.draw.rect(s, _FLOOR, (x0, FLOOR_Y, ROOM_W, ROOM_H - FLOOR_Y))
    pygame.draw.line(s, _TRIM, (x0, FLOOR_Y), (x0 + ROOM_W, FLOOR_Y), 3)
    # ceiling light bar
    pygame.draw.rect(s, _GLOW, (x0 + 60, 6, ROOM_W - 120, 5),
                     border_radius=2)
    # bulkhead between rooms
    pygame.draw.rect(s, (30, 36, 46), (x0 + ROOM_W - 6, 0, 6, ROOM_H))
    pygame.draw.rect(s, _TRIM, (x0 + ROOM_W - 8, FLOOR_Y - 78, 10, 78),
                     border_radius=3)            # hatch frame


def _bunks(s, x0):
    for i in range(2):
        bx = x0 + 28 + i * 110
        pygame.draw.rect(s, (84, 96, 116), (bx, FLOOR_Y - 64, 84, 14),
                         border_radius=4)
        pygame.draw.rect(s, (84, 96, 116), (bx, FLOOR_Y - 28, 84, 14),
                         border_radius=4)
        pygame.draw.line(s, _TRIM, (bx + 4, FLOOR_Y - 64), (bx + 4, FLOOR_Y), 3)
        pygame.draw.rect(s, (140, 170, 210), (bx + 8, FLOOR_Y - 62, 22, 9),
                         border_radius=3)        # pillow glow


def _planters(s, x0):
    for i in range(3):
        px = x0 + 26 + i * 84
        pygame.draw.rect(s, (70, 56, 40), (px, FLOOR_Y - 30, 64, 30),
                         border_radius=3)
        for j in range(4):
            stem = px + 8 + j * 15
            pygame.draw.line(s, (60, 130, 60), (stem, FLOOR_Y - 30),
                             (stem, FLOOR_Y - 52), 2)
            pygame.draw.circle(s, (88, 180, 88), (stem, FLOOR_Y - 54), 5)
        pygame.draw.rect(s, (240, 180, 255), (px + 2, 30, 60, 4))  # grow light


def _med(s, x0):
    pygame.draw.rect(s, (210, 214, 222), (x0 + 40, FLOOR_Y - 46, 96, 18),
                     border_radius=5)            # exam bed
    pygame.draw.rect(s, (210, 60, 60), (x0 + 170, 40, 34, 34),
                     border_radius=4)
    pygame.draw.rect(s, (250, 250, 250), (x0 + 183, 46, 8, 22))
    pygame.draw.rect(s, (250, 250, 250), (x0 + 176, 53, 22, 8))


def _shop(s, x0):
    pygame.draw.rect(s, (96, 104, 120), (x0 + 30, FLOOR_Y - 40, 110, 40))
    pygame.draw.rect(s, (130, 140, 158), (x0 + 36, FLOOR_Y - 52, 30, 12))
    pygame.draw.circle(s, (255, 190, 90), (x0 + 180, FLOOR_Y - 58), 7)
    pygame.draw.line(s, (80, 88, 102), (x0 + 180, FLOOR_Y - 51),
                     (x0 + 180, FLOOR_Y), 5)     # robot arm post


def _lab(s, x0):
    pygame.draw.rect(s, (96, 104, 120), (x0 + 26, FLOOR_Y - 38, 130, 38))
    for i in range(3):
        pygame.draw.rect(s, (120, 220, 255),
                         (x0 + 36 + i * 36, FLOOR_Y - 56, 14, 18),
                         border_radius=3)        # sample jars


def _console(s, x0):
    cx = x0 + ROOM_W - 64
    pygame.draw.rect(s, (26, 34, 48), (cx, FLOOR_Y - 64, 40, 30),
                     border_radius=4)
    pygame.draw.rect(s, (90, 200, 160), (cx + 4, FLOOR_Y - 60, 32, 14),
                     border_radius=2)
    pygame.draw.line(s, _TRIM, (cx + 20, FLOOR_Y - 34), (cx + 20, FLOOR_Y), 4)


_PROPS = {"hab_module": _bunks, "hab_rigid": _bunks,
          "hab_inflatable": _bunks, "regolith_vault": _bunks,
          "basalt_hab": _bunks, "greenhouse": _planters,
          "bio_farm": _planters, "med_bay": _med,
          "machine_shop": _shop, "science_lab": _lab}


def room_strip(rooms: tuple[str, ...]) -> pygame.Surface:
    """The whole interior as one cached strip: airlock + one room per
    habitable module, in build order."""
    key = ("strip", rooms)
    got = _CACHE.get(key)
    if got is not None:
        return got
    n = len(rooms) + 1                            # +1 airlock
    s = pygame.Surface((n * ROOM_W, ROOM_H))
    # airlock room
    _room_base(s, 0)
    pygame.draw.rect(s, (180, 80, 60), (24, FLOOR_Y - 92, 64, 92),
                     border_radius=6)             # outer door
    pygame.draw.circle(s, (240, 220, 160), (56, FLOOR_Y - 48), 9, 3)
    pygame.draw.rect(s, (140, 150, 168), (110, FLOOR_Y - 60, 34, 60),
                     border_radius=4)             # suit rack
    for i, kind in enumerate(rooms):
        x0 = (i + 1) * ROOM_W
        _room_base(s, x0, vault=(kind in ("regolith_vault", "basalt_hab")))
        _PROPS.get(kind, _shop)(s, x0)
        _console(s, x0)
    _CACHE[key] = s
    return s
