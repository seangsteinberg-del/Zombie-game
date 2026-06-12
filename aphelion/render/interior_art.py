"""Walkable interiors v2 (F0.5, the "stunning" directive): a side-view
cutaway of the pressure hull floating in space — stars behind, a real
shell with ribs and end-caps, human-scale rooms (3.2 m clear, not the
old 8 m gymnasium), quilted wall padding, baked warm light pools,
glowing consoles, and per-function set dressing: a Dragon-class capsule
reads as a cockpit (couches, MFD bank, portholes), a greenhouse glows
magenta over real foliage rows, a machine shop has a tool wall.

Rendered once at 48 px/m and cached; `strip_scaled` caches the
smoothscaled blit too (no per-frame transform cost). Same room pitch in
metres as v1 (12 m), so walker math in main is unchanged.
"""

from __future__ import annotations

import math
import random
import zlib

import pygame

PPM = 48                       # px per metre (was 24 — double detail)
ROOM_M = 12.0
ROOM_W = int(ROOM_M * PPM)     # 576
ROOM_H = 256
SPACE_TOP = 22                 # star margin above the hull
HULL_T = 8                     # shell thickness
CEIL_BAND = 24                 # conduits / fixtures band
FLOOR_Y = 214                  # walking line
DECK_H = 14
CEIL_Y = SPACE_TOP + HULL_T + CEIL_BAND          # 54: top of clear space

_WALL_TOP = (52, 60, 76)
_WALL_BOT = (38, 44, 58)
_PANEL = (64, 74, 92)
_PANEL_DARK = (48, 56, 72)
_TRIM = (112, 126, 152)
_HULL = (70, 80, 98)
_HULL_DARK = (34, 40, 52)
_DECK = (78, 88, 106)
_DECK_DARK = (58, 66, 82)
_WARM = (255, 226, 160)
_SCREEN = (96, 210, 182)
_SCREEN_BLUE = (120, 190, 255)
_GROW = (232, 122, 255)
_SPACE = (5, 7, 12)

_CACHE: dict = {}

HABITABLE = ("hab_module", "hab_rigid", "hab_inflatable", "regolith_vault",
             "basalt_hab", "med_bay", "greenhouse", "bio_farm",
             "machine_shop", "science_lab")


def vessel_rooms(vessel) -> list[tuple[str, str, str]]:
    """(room_kind, name, info) per pressurized part of a flying stack —
    any row with a [hab] or [crew] table earns a walkable room. Crew
    capsules read as a FLIGHT DECK (couches + MFD bank), not a hab."""
    out = []
    for r in vessel.rows:
        p = vessel.part(r)
        hab = p.get("hab")
        crew_t = p.get("crew")
        if not hab and not crew_t:
            continue
        if hab and hab.get("grow_m2"):
            kind = "greenhouse"
            info = f"{hab['grow_m2']:,.0f} m² under grow-lights"
        elif hab and hab.get("lab"):
            kind = "science_lab"
            info = f"{hab.get('v_press_m3', 0):,.0f} m³ of benches"
        elif crew_t and not (hab and hab.get("sleeps")):
            kind = "flight_deck"
            info = f"seats {crew_t.get('capacity', 2)}"
        elif (hab and hab.get("sleeps")) or crew_t:
            kind = "hab_module"
            sleeps = (hab or {}).get("sleeps") or (crew_t or {}).get(
                "capacity", 0)
            info = (f"sleeps {sleeps}"
                    + (f" · {hab['v_press_m3']:,.0f} m³" if hab else ""))
        else:
            kind = "machine_shop"
            info = f"{(hab or {}).get('v_press_m3', 0):,.0f} m³ pressurized"
        out.append((kind, p.get("name", r.part_id), info))
    return out


# ---- small paint helpers -----------------------------------------------------------

def _vgrad(s: pygame.Surface, rect, top, bot) -> None:
    x, y, w, h = rect
    col = pygame.Surface((1, max(1, h)))
    for i in range(h):
        f = i / max(1, h - 1)
        col.set_at((0, i), tuple(int(top[c] + (bot[c] - top[c]) * f)
                                 for c in range(3)))
    s.blit(pygame.transform.scale(col, (w, h)), (x, y))


def _glow(s: pygame.Surface, cx: int, cy: int, r: int, color,
          strength: float = 1.0) -> None:
    """Additive radial pool — the GL bloom pass loves these."""
    key = ("glow", r, color, round(strength, 2))
    g = _CACHE.get(key)
    if g is None:
        g = pygame.Surface((2 * r, 2 * r))
        for i in range(r, 0, -2):
            f = (1.0 - i / r) ** 2 * strength
            pygame.draw.circle(
                g, tuple(min(255, int(c * f)) for c in color), (r, r), i)
        _CACHE[key] = g
    s.blit(g, (cx - r, cy - r), special_flags=pygame.BLEND_ADD)


def _screen_panel(s, x, y, w, h, color=_SCREEN, lines=3,
                  rng: random.Random | None = None) -> None:
    pygame.draw.rect(s, (16, 22, 32), (x - 3, y - 3, w + 6, h + 6),
                     border_radius=4)
    pygame.draw.rect(s, tuple(c // 5 for c in color), (x, y, w, h),
                     border_radius=2)
    rr = rng or random
    for i in range(lines):
        ly = y + 4 + i * max(4, (h - 8) // max(1, lines))
        lw = int(w * (0.35 + 0.55 * rr.random()))
        pygame.draw.line(s, color, (x + 3, ly), (x + 3 + lw, ly), 2)
    _glow(s, x + w // 2, y + h // 2, max(w, 26), color, 0.5)


def _rivets(s, x0, x1, y, step=24):
    for x in range(x0, x1, step):
        pygame.draw.circle(s, (30, 36, 48), (x, y), 2)


# ---- the shared room shell ---------------------------------------------------------

def _room_shell(s: pygame.Surface, x0: int, rng: random.Random,
                vault: bool = False) -> None:
    # interior wall: vertical falloff + quilted padding panels
    iw_y0, iw_y1 = SPACE_TOP + HULL_T, FLOOR_Y
    if vault:
        _vgrad(s, (x0, iw_y0, ROOM_W, iw_y1 - iw_y0), (66, 58, 50),
               (44, 38, 33))
        for i in range(5):                          # sintered courses
            cy = iw_y0 + 18 + i * 30 + rng.randint(-3, 3)
            pygame.draw.line(s, (38, 33, 28), (x0, cy), (x0 + ROOM_W, cy), 3)
    else:
        _vgrad(s, (x0, iw_y0, ROOM_W, iw_y1 - iw_y0), _WALL_TOP, _WALL_BOT)
        for px in range(x0 + 14, x0 + ROOM_W - 30, 64):  # quilt panels
            ph = FLOOR_Y - CEIL_Y - 14
            pygame.draw.rect(s, _PANEL, (px, CEIL_Y + 6, 52, ph),
                             border_radius=8)
            pygame.draw.rect(s, _PANEL_DARK, (px, CEIL_Y + 6, 52, ph),
                             width=2, border_radius=8)
            pygame.draw.line(s, _PANEL_DARK, (px + 26, CEIL_Y + 10),
                             (px + 26, CEIL_Y + ph - 2), 2)
            _rivets(s, px + 6, px + 50, CEIL_Y + 12, 38)
    # ceiling band: conduits + cable runs
    _vgrad(s, (x0, SPACE_TOP + HULL_T, ROOM_W, CEIL_BAND),
           (44, 50, 64), (36, 42, 54))
    for cy, col in ((SPACE_TOP + HULL_T + 6, (88, 98, 118)),
                    (SPACE_TOP + HULL_T + 12, (66, 76, 94)),
                    (SPACE_TOP + HULL_T + 17, (120, 110, 84))):
        pygame.draw.line(s, col, (x0, cy), (x0 + ROOM_W, cy), 3)
    # deck: plating + treads + shadow under the walls
    _vgrad(s, (x0, FLOOR_Y, ROOM_W, DECK_H), _DECK, _DECK_DARK)
    pygame.draw.line(s, _TRIM, (x0, FLOOR_Y), (x0 + ROOM_W, FLOOR_Y), 3)
    for px in range(x0 + 10, x0 + ROOM_W, 34):
        pygame.draw.line(s, _DECK_DARK, (px, FLOOR_Y + 4),
                         (px + 16, FLOOR_Y + 4), 2)
    sh = pygame.Surface((ROOM_W, 18), pygame.SRCALPHA)
    sh.fill((0, 0, 0, 46))
    s.blit(sh, (x0, FLOOR_Y - 18))
    # two ceiling light fixtures with pooled warm light
    for fx in (x0 + ROOM_W // 4, x0 + 3 * ROOM_W // 4):
        pygame.draw.rect(s, (200, 184, 140),
                         (fx - 36, SPACE_TOP + HULL_T + CEIL_BAND - 5, 72, 5),
                         border_radius=2)
        pygame.draw.rect(s, _WARM,
                         (fx - 32, SPACE_TOP + HULL_T + CEIL_BAND - 3, 64, 3))
        _glow(s, fx, CEIL_Y + 26, 120, (110, 96, 60), 0.9)
        _glow(s, fx, FLOOR_Y - 8, 90, (70, 62, 42), 0.6)
    # structural ribs at the room joints
    pygame.draw.rect(s, _HULL_DARK, (x0 + ROOM_W - 7, SPACE_TOP, 7,
                                     FLOOR_Y + DECK_H - SPACE_TOP + HULL_T))
    pygame.draw.rect(s, _HULL, (x0 + ROOM_W - 10, SPACE_TOP, 4,
                                FLOOR_Y + DECK_H - SPACE_TOP + HULL_T))
    # open hatchway highlight at the joint
    hx = x0 + ROOM_W - 7
    pygame.draw.ellipse(s, (24, 28, 38),
                        (hx - 8, FLOOR_Y - 112, 22, 112))
    pygame.draw.ellipse(s, _TRIM, (hx - 8, FLOOR_Y - 112, 22, 112), 3)


def _porthole(s, cx, cy, r, rng):
    pygame.draw.circle(s, (28, 34, 46), (cx, cy), r + 6)
    pygame.draw.circle(s, _TRIM, (cx, cy), r + 6, 3)
    pygame.draw.circle(s, (8, 10, 18), (cx, cy), r)
    for _ in range(7):
        a, d = rng.random() * 6.283, rng.random() * (r - 3)
        px, py = cx + d * math.cos(a), cy + d * math.sin(a)
        c = rng.choice(((230, 235, 255), (190, 200, 230), (255, 240, 210)))
        s.set_at((int(px), int(py)), c)
    pygame.draw.arc(s, (150, 170, 210),
                    (cx - r, cy - r, 2 * r, 2 * r), 0.6, 1.7, 2)


# ---- per-function set dressing ----------------------------------------------------

def _flight_deck(s, x0, rng):
    """Dragon-class cockpit: reclined couches, a glowing MFD bank,
    switch rows, portholes — the user's benchmark room."""
    _porthole(s, x0 + 88, CEIL_Y + 34, 22, rng)
    _porthole(s, x0 + ROOM_W - 150, CEIL_Y + 34, 22, rng)
    # instrument panel spanning the upper mid-wall
    px, pw = x0 + 150, 250
    pygame.draw.rect(s, (30, 38, 52), (px, CEIL_Y + 8, pw, 64),
                     border_radius=8)
    pygame.draw.rect(s, (52, 62, 80), (px, CEIL_Y + 8, pw, 64),
                     width=2, border_radius=8)
    _screen_panel(s, px + 12, CEIL_Y + 18, 64, 40, _SCREEN_BLUE, 4, rng)
    _screen_panel(s, px + 94, CEIL_Y + 18, 64, 40, _SCREEN, 3, rng)
    _screen_panel(s, px + 176, CEIL_Y + 18, 60, 40, (255, 196, 110), 3, rng)
    for i in range(10):                              # switch row
        sx = px + 14 + i * 23
        pygame.draw.rect(s, (180, 190, 205), (sx, CEIL_Y + 64, 5, 4))
    # two reclined couches
    for i in range(2):
        bx = x0 + 170 + i * 130
        pygame.draw.polygon(s, (88, 100, 122), (
            (bx, FLOOR_Y), (bx + 14, FLOOR_Y - 44), (bx + 40, FLOOR_Y - 58),
            (bx + 78, FLOOR_Y - 50), (bx + 84, FLOOR_Y - 38),
            (bx + 64, FLOOR_Y - 34), (bx + 30, FLOOR_Y - 26),
            (bx + 22, FLOOR_Y)))
        pygame.draw.polygon(s, (120, 134, 158), (
            (bx + 14, FLOOR_Y - 44), (bx + 40, FLOOR_Y - 58),
            (bx + 78, FLOOR_Y - 50), (bx + 76, FLOOR_Y - 44),
            (bx + 40, FLOOR_Y - 50), (bx + 18, FLOOR_Y - 38)))
        pygame.draw.rect(s, (210, 120, 90), (bx + 44, FLOOR_Y - 56, 18, 7),
                         border_radius=3)            # harness pad
    # hand controller pedestal
    pygame.draw.line(s, _TRIM, (x0 + 120, FLOOR_Y), (x0 + 120, FLOOR_Y - 30), 5)
    pygame.draw.circle(s, (200, 90, 70), (x0 + 120, FLOOR_Y - 34), 7)


def _bunks(s, x0, rng):
    for i in range(2):
        bx = x0 + 56 + i * 230
        for level in range(2):
            by = FLOOR_Y - 52 - level * 64
            pygame.draw.rect(s, (54, 62, 80), (bx - 6, by - 34, 152, 90),
                             border_radius=8)        # alcove
            pygame.draw.rect(s, (84, 96, 118), (bx, by, 140, 16),
                             border_radius=5)        # mattress
            pygame.draw.rect(s, (168, 186, 214), (bx + 6, by + 2, 30, 11),
                             border_radius=4)        # pillow
            pygame.draw.rect(s, (122, 96, 70), (bx + 44, by + 3, 88, 10),
                             border_radius=4)        # blanket
            _glow(s, bx + 124, by - 12, 30, (96, 84, 52), 0.8)
            pygame.draw.circle(s, _WARM, (bx + 124, by - 14), 3)
    # lockers
    for j in range(3):
        lx = x0 + ROOM_W - 132 + j * 34
        pygame.draw.rect(s, (70, 80, 98), (lx, FLOOR_Y - 92, 28, 92),
                         border_radius=3)
        pygame.draw.rect(s, (48, 56, 72), (lx, FLOOR_Y - 92, 28, 92), 2,
                         border_radius=3)
        pygame.draw.circle(s, _TRIM, (lx + 22, FLOOR_Y - 46), 2)


def _planters(s, x0, rng):
    for tier in range(2):
        ty = FLOOR_Y - 26 - tier * 64
        for i in range(3):
            px = x0 + 44 + i * 162
            pygame.draw.rect(s, (60, 48, 36), (px, ty - 14, 132, 16),
                             border_radius=4)
            pygame.draw.rect(s, (44, 35, 26), (px, ty - 14, 132, 16), 2,
                             border_radius=4)
            for j in range(6):
                stem = px + 12 + j * 20 + rng.randint(-3, 3)
                h = rng.randint(18, 34)
                pygame.draw.line(s, (52, 122, 58), (stem, ty - 14),
                                 (stem, ty - 14 - h), 2)
                for leaf in range(3):
                    la = rng.random() * 2.4 + 0.4
                    ly = ty - 14 - h * (0.4 + 0.2 * leaf)
                    pygame.draw.ellipse(
                        s, (70 + rng.randint(0, 40), 160 + rng.randint(0, 30),
                            74), (stem - 9 + 9 * math.cos(la), ly, 11, 6))
            led_y = ty - 64
            pygame.draw.rect(s, _GROW, (px + 4, led_y, 124, 4),
                             border_radius=2)
            _glow(s, px + 66, led_y + 26, 78, (96, 40, 110), 1.0)
    pygame.draw.line(s, (90, 110, 130), (x0 + 20, FLOOR_Y - 4),
                     (x0 + ROOM_W - 20, FLOOR_Y - 4), 2)   # irrigation run


def _med(s, x0, rng):
    pygame.draw.rect(s, (200, 206, 216), (x0 + 70, FLOOR_Y - 44, 150, 14),
                     border_radius=6)
    pygame.draw.rect(s, (140, 148, 162), (x0 + 78, FLOOR_Y - 30, 8, 30))
    pygame.draw.rect(s, (140, 148, 162), (x0 + 200, FLOOR_Y - 30, 8, 30))
    pygame.draw.rect(s, (236, 240, 248), (x0 + 78, FLOOR_Y - 52, 36, 9),
                     border_radius=3)
    _screen_panel(s, x0 + 260, CEIL_Y + 30, 70, 44, (110, 230, 150), 1, rng)
    ecg = [(x0 + 264 + i * 6,
            CEIL_Y + 52 - (14 if i % 5 == 2 else rng.randint(0, 4)))
           for i in range(11)]
    pygame.draw.lines(s, (160, 255, 190), False, ecg, 2)
    pygame.draw.rect(s, (214, 64, 64), (x0 + 392, CEIL_Y + 26, 40, 40),
                     border_radius=6)
    pygame.draw.rect(s, (250, 250, 250), (x0 + 408, CEIL_Y + 32, 8, 28))
    pygame.draw.rect(s, (250, 250, 250), (x0 + 398, CEIL_Y + 42, 28, 8))


def _shop(s, x0, rng):
    pygame.draw.rect(s, (66, 74, 90), (x0 + 60, CEIL_Y + 14, 200, 86),
                     border_radius=6)                # tool wall
    pygame.draw.rect(s, (50, 58, 72), (x0 + 60, CEIL_Y + 14, 200, 86), 2,
                     border_radius=6)
    for i in range(5):                               # hanging tools
        tx = x0 + 78 + i * 38
        pygame.draw.line(s, (170, 178, 192), (tx, CEIL_Y + 26),
                         (tx, CEIL_Y + 48 + (i % 3) * 8), 4)
        pygame.draw.circle(s, (190, 198, 212), (tx, CEIL_Y + 26), 4)
    pygame.draw.rect(s, (92, 100, 116), (x0 + 60, FLOOR_Y - 46, 180, 46))
    pygame.draw.rect(s, (120, 130, 148), (x0 + 60, FLOOR_Y - 52, 180, 8),
                     border_radius=3)                # bench top
    pygame.draw.rect(s, (150, 110, 70), (x0 + 84, FLOOR_Y - 62, 26, 12))
    for i in range(2):                               # crates
        cx = x0 + ROOM_W - 200 + i * 74
        pygame.draw.rect(s, (108, 92, 62), (cx, FLOOR_Y - 40, 62, 40),
                         border_radius=3)
        pygame.draw.line(s, (84, 70, 46), (cx, FLOOR_Y - 20),
                         (cx + 62, FLOOR_Y - 20), 2)
    for i in range(8):                               # hazard chevrons
        hx = x0 + 300 + i * 22
        pygame.draw.polygon(s, (220, 180, 60) if i % 2 == 0 else (40, 44, 54),
                            ((hx, FLOOR_Y + 3), (hx + 11, FLOOR_Y + 3),
                             (hx + 22, FLOOR_Y + 11), (hx + 11, FLOOR_Y + 11)))
    # robot arm
    ax = x0 + ROOM_W - 90
    pygame.draw.line(s, (96, 104, 120), (ax, FLOOR_Y), (ax, FLOOR_Y - 64), 7)
    pygame.draw.line(s, (120, 130, 148), (ax, FLOOR_Y - 64),
                     (ax - 34, FLOOR_Y - 88), 5)
    pygame.draw.circle(s, (255, 190, 90), (ax - 38, FLOOR_Y - 92), 6)
    _glow(s, ax - 38, FLOOR_Y - 92, 26, (120, 86, 36), 0.8)


def _lab(s, x0, rng):
    pygame.draw.rect(s, (92, 100, 116), (x0 + 50, FLOOR_Y - 44, 230, 44))
    pygame.draw.rect(s, (124, 134, 152), (x0 + 50, FLOOR_Y - 50, 230, 8),
                     border_radius=3)
    for i in range(5):                               # vials
        vx = x0 + 66 + i * 34
        col = rng.choice(((120, 220, 255), (255, 170, 120), (170, 255, 140),
                          (240, 140, 220)))
        pygame.draw.rect(s, col, (vx, FLOOR_Y - 70, 12, 20), border_radius=4)
        _glow(s, vx + 6, FLOOR_Y - 60, 18, tuple(c // 3 for c in col), 0.9)
    pygame.draw.rect(s, (60, 70, 86), (x0 + 300, FLOOR_Y - 88, 110, 88),
                     border_radius=6)                # glovebox
    pygame.draw.rect(s, (24, 30, 42), (x0 + 310, FLOOR_Y - 78, 90, 40),
                     border_radius=4)
    pygame.draw.circle(s, (140, 150, 168), (x0 + 330, FLOOR_Y - 32), 12, 4)
    pygame.draw.circle(s, (140, 150, 168), (x0 + 374, FLOOR_Y - 32), 12, 4)
    _screen_panel(s, x0 + 444, CEIL_Y + 26, 80, 50, _SCREEN_BLUE, 4, rng)


def _airlock(s, x0, rng):
    """A real airlock: round hatch with a wheel, caution stripes, suit
    rack with two suits, status lamp."""
    hx, hy, hr = x0 + 96, FLOOR_Y - 64, 56
    pygame.draw.rect(s, (150, 66, 50), (hx - hr - 14, hy - hr - 14,
                                        2 * hr + 28, 2 * hr + 14 + 64),
                     border_radius=10)               # door leaf
    pygame.draw.rect(s, (108, 46, 36), (hx - hr - 14, hy - hr - 14,
                                        2 * hr + 28, 2 * hr + 14 + 64),
                     width=3, border_radius=10)
    pygame.draw.circle(s, (62, 30, 24), (hx, hy), hr)
    pygame.draw.circle(s, (190, 180, 150), (hx, hy), hr, 4)
    pygame.draw.circle(s, (190, 180, 150), (hx, hy), 22, 4)     # wheel
    for a in range(4):
        ang = a * math.pi / 2 + 0.4
        pygame.draw.line(s, (190, 180, 150),
                         (hx + 20 * math.cos(ang), hy + 20 * math.sin(ang)),
                         (hx + hr * 0.86 * math.cos(ang),
                          hy + hr * 0.86 * math.sin(ang)), 4)
    for i in range(7):                               # caution stripes
        sx = x0 + 24 + i * 26
        pygame.draw.polygon(s, (220, 180, 60) if i % 2 == 0 else (44, 40, 36),
                            ((sx, FLOOR_Y + 3), (sx + 13, FLOOR_Y + 3),
                             (sx + 26, FLOOR_Y + 11), (sx + 13, FLOOR_Y + 11)))
    pygame.draw.circle(s, (120, 230, 130), (hx + hr + 26, hy - hr + 4), 5)
    _glow(s, hx + hr + 26, hy - hr + 4, 20, (40, 110, 46), 1.0)
    # suit rack
    for i in range(2):
        sx = x0 + 300 + i * 90
        pygame.draw.rect(s, (52, 60, 76), (sx - 26, CEIL_Y + 18, 64, 130),
                         border_radius=8)
        pygame.draw.circle(s, (226, 230, 238), (sx + 6, CEIL_Y + 44), 15)
        pygame.draw.rect(s, (40, 46, 58), (sx - 2, CEIL_Y + 38, 17, 11),
                         border_radius=4)            # visor
        pygame.draw.rect(s, (216, 220, 230), (sx - 10, CEIL_Y + 60, 33, 52),
                         border_radius=9)            # torso
        pygame.draw.rect(s, (196, 200, 212), (sx - 8, CEIL_Y + 112, 12, 30),
                         border_radius=5)
        pygame.draw.rect(s, (196, 200, 212), (sx + 9, CEIL_Y + 112, 12, 30),
                         border_radius=5)
    _screen_panel(s, x0 + 470, CEIL_Y + 30, 64, 40, (255, 196, 110), 2, rng)


_PROPS = {"hab_module": _bunks, "hab_rigid": _bunks,
          "hab_inflatable": _bunks, "regolith_vault": _bunks,
          "basalt_hab": _bunks, "greenhouse": _planters,
          "bio_farm": _planters, "med_bay": _med,
          "machine_shop": _shop, "science_lab": _lab,
          "flight_deck": _flight_deck}


def _stars(s: pygame.Surface, rng: random.Random) -> None:
    w, h = s.get_size()
    for _ in range(w // 6):
        x, y = rng.randrange(w), rng.randrange(h)
        b = rng.randint(90, 235)
        s.set_at((x, y), (b, b, min(255, b + rng.randint(0, 25))))


def room_strip(rooms: tuple[str, ...]) -> pygame.Surface:
    """The whole interior as one cached strip: a pressure hull floating
    against the stars — airlock + one dressed room per module."""
    key = ("strip2", rooms)
    got = _CACHE.get(key)
    if got is not None:
        return got
    rng = random.Random(zlib.crc32(repr(rooms).encode()))
    n = len(rooms) + 1
    w = n * ROOM_W
    s = pygame.Surface((w, ROOM_H))
    s.fill(_SPACE)
    _stars(s, rng)
    # hull shell: top + bottom skins with end caps
    pygame.draw.rect(s, _HULL_DARK, (0, SPACE_TOP - 2, w, HULL_T + 4),
                     border_radius=6)
    pygame.draw.rect(s, _HULL, (0, SPACE_TOP, w, HULL_T))
    pygame.draw.line(s, (118, 130, 152), (0, SPACE_TOP + 1),
                     (w, SPACE_TOP + 1), 2)          # sun-caught edge
    hull_b = FLOOR_Y + DECK_H
    pygame.draw.rect(s, _HULL_DARK, (0, hull_b, w, HULL_T + 4),
                     border_radius=6)
    pygame.draw.rect(s, _HULL, (0, hull_b, w, HULL_T - 2))
    for x in range(0, w, ROOM_W // 2):               # hull weld seams
        pygame.draw.line(s, (52, 60, 76), (x, SPACE_TOP),
                         (x, SPACE_TOP + HULL_T), 1)
    _airlock_done = False
    _room_shell(s, 0, rng)
    _airlock(s, 0, rng)
    for i, kind in enumerate(rooms):
        x0 = (i + 1) * ROOM_W
        sub_rng = random.Random(zlib.crc32(f"{kind}|{i}".encode()))
        _room_shell(s, x0, sub_rng,
                    vault=(kind in ("regolith_vault", "basalt_hab")))
        _PROPS.get(kind, _shop)(s, x0, sub_rng)
    _CACHE[key] = s
    return s


def strip_scaled(rooms: tuple[str, ...], scale: float) -> pygame.Surface:
    """Cached smoothscale — the per-frame cost is one blit."""
    key = ("scaled2", rooms, round(scale, 2))
    got = _CACHE.get(key)
    if got is None:
        s = room_strip(rooms)
        got = pygame.transform.smoothscale(
            s, (int(s.get_width() * scale), int(s.get_height() * scale)))
        _CACHE[key] = got
    return got


def space_backdrop(size: tuple[int, int]) -> pygame.Surface:
    """Deep-space star field behind the hull cutaway (parallax slab,
    1.5x window width)."""
    key = ("backdrop", size)
    got = _CACHE.get(key)
    if got is None:
        rng = random.Random(0x5EA5)
        got = pygame.Surface((int(size[0] * 1.5), size[1]))
        got.fill(_SPACE)
        for _ in range(220):
            x = rng.randrange(got.get_width())
            y = rng.randrange(got.get_height())
            b = rng.randint(60, 200)
            got.set_at((x, y), (b, b, min(255, b + 20)))
            if b > 170:
                got.set_at((min(x + 1, got.get_width() - 1), y),
                           (b // 2, b // 2, b // 2))
        _CACHE[key] = got
    return got
