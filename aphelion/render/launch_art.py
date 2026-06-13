"""Launch-pad and ascent dressing for the flown launch: animated swing
arms + crew access arm, hold-down release, cryo vent wisps and tank
frost, ignition deluge steam and flame-trench glow, the altitude-aware
PLUME V2 with mach diamonds, and staging debris.

MISSION FILM discipline (design/ART-DIRECTION.md): key light from the
upper right (matches surface_art's baked sun), gradients + grain on
every surface (§1.2 — no flat fill), contact/AO shadows where things
meet (§2.5), international-orange accents only, and the engine plume is
the bloom hero of the frame (§2.3 — additive core, everything else
plain alpha). Methalox burns BLUE-white with warm mach diamonds; RP-1
burns orange — palette switches on the fuel name.

All draw functions are STATELESS given (surface, geometry, params, t):
particles are slot-based — each slot's birth time is quantized from t
and its kinematics are closed-form, so a replayed t replays the exact
frame (13 determinism; seeds via zlib.crc32, never hash()).

Anchoring matches main.py's pad blit exactly: pad_complex() goes at
(pad_x - PAD_W//2, ground_y - PAD_GROUND_Y - 12); PadGeom(pad_x,
ground_y) derives every attachment point from those constants.
"""

from __future__ import annotations

import math
import zlib
from dataclasses import dataclass

import numpy as np
import pygame

from aphelion.render.surface_art import PAD_GROUND_Y, PAD_W, pad_complex

_RGB = tuple[int, int, int]

_SHADOW = (8, 10, 14)
_ORANGE = (224, 84, 30)
_STEEL_LIT = (150, 154, 162)
_STEEL = (104, 108, 118)
_STEEL_DK = (66, 70, 78)

# fuel -> (mid, edge, diamond) plume palettes; core is near-white
PLUME_PALS: dict[str, tuple[_RGB, _RGB, _RGB]] = {
    "ch4": ((164, 192, 255), (66, 92, 214), (255, 238, 205)),
    "lh2": ((196, 214, 255), (120, 150, 240), (255, 246, 224)),
    "rp1": ((255, 188, 96), (216, 92, 24), (255, 244, 215)),
}

# pad-sprite local anchors (pad_complex coordinate system)
_PAD_CX = PAD_W // 2                  # vehicle centerline, local x
_TOWER_XL = _PAD_CX + 44              # service-tower left chord
_ARM_LEVELS = (70, 114)               # erased static-arm rows
_ARM_ERASE = ((_PAD_CX + 16, 67, _TOWER_XL - 4, 81),
              (_PAD_CX + 16, 111, _TOWER_XL - 4, 123))

_CACHE: dict[tuple, pygame.Surface] = {}
_PAD_BASE: list[pygame.Surface] = []


def _seed(key: str) -> int:
    return zlib.crc32(key.encode("utf-8")) & 0xFFFFFFFF


def _r01(key: str) -> float:
    return _seed(key) / 4294967296.0


def _smooth(u: float) -> float:
    u = max(0.0, min(1.0, u))
    return u * u * (3.0 - 2.0 * u)


@dataclass(frozen=True, slots=True)
class PadGeom:
    """Screen-space pad anchor: pad_x = vehicle centerline x,
    ground_y = terrain line the vehicle base sits on (main.py)."""
    pad_x: int
    ground_y: int

    @property
    def blit_xy(self) -> tuple[int, int]:
        return (self.pad_x - PAD_W // 2,
                self.ground_y - PAD_GROUND_Y - 12)

    @property
    def deck_y(self) -> int:
        return self.ground_y - 12       # apron top row on screen

    @property
    def tower_x(self) -> int:
        return self.pad_x + (_TOWER_XL - _PAD_CX)

    def arm_y(self, i: int) -> int:
        return self.blit_xy[1] + _ARM_LEVELS[i]


# ---- pad base (static arms erased; launch_art animates its own) -----------

def pad_base() -> pygame.Surface:
    """pad_complex() with the baked-in umbilical arms removed so the
    animated arms below own that silhouette. Cached copy; the original
    sprite is never mutated. Stub hinges are left at the tower chord."""
    if _PAD_BASE:
        return _PAD_BASE[0]
    s = pad_complex().copy()
    for x0, y0, x1, y1 in _ARM_ERASE:
        s.fill((0, 0, 0, 0), (x0, y0, x1 - x0, y1 - y0))
    _PAD_BASE.append(s)
    return _PAD_BASE[0]


def draw_pad_base(surf: pygame.Surface, geom: PadGeom) -> None:
    surf.blit(pad_base(), geom.blit_xy)


# ---- soft sprites ----------------------------------------------------------

def _puff_sprite(r: int, rgb: _RGB, warm_side: float = 0.0,
                 key: str = "puff") -> pygame.Surface:
    """Lumpy cloud puff: 3-lobe gaussian with grain — never a perfect
    circle. warm_side > 0 lights the LEFT lobe (flame side) warm."""
    k = ("puff", r, rgb, round(warm_side, 2), key)
    hit = _CACHE.get(k)
    if hit is not None:
        return hit
    d = 2 * r
    rng = np.random.default_rng(_seed(f"{key}|{r}"))
    ax = np.arange(d, dtype=float) - (d - 1) / 2.0
    xx, yy = ax[:, None], ax[None, :]
    a = np.zeros((d, d))
    for i in range(3):
        ox = (rng.random() - 0.5) * r * 0.8
        oy = (rng.random() - 0.5) * r * 0.55
        rr = np.hypot(xx - ox, yy - oy) / (r * (0.55 + 0.25
                                                * rng.random()))
        a += np.exp(-rr * rr * 1.7)
    a = np.clip(a / a.max(), 0.0, 1.0) ** 1.25
    a *= 1.0 + 0.16 * (rng.random((d, d)) - 0.5)     # grain
    s = pygame.Surface((d, d), pygame.SRCALPHA)
    rgbv = pygame.surfarray.pixels3d(s)
    base = np.asarray(rgb, float)[None, None, :]
    # self-shadowed underside + sun/flame-lit crown
    lit = 1.0 + 0.22 * np.clip(-yy / r, -1.0, 1.0)
    if warm_side > 0.0:
        warm = np.asarray((255.0, 196.0, 132.0))
        w = warm_side * np.clip((-xx / r + 0.4) * 0.6, 0.0, 1.0)
        base = base * (1.0 - w[..., None]) + warm * w[..., None]
    rgbv[...] = np.clip(base * lit[..., None], 0.0, 255.0
                        ).astype(np.uint8)
    del rgbv
    al = pygame.surfarray.pixels_alpha(s)
    al[...] = (np.clip(a, 0.0, 1.0) * 255.0).astype(np.uint8)
    del al
    _CACHE[k] = s
    return s


def _glow_sprite(r: int, rgb: _RGB) -> pygame.Surface:
    """Soft alpha blob for NORMAL blits (shadows, soft masses)."""
    k = ("glow", r, rgb)
    hit = _CACHE.get(k)
    if hit is not None:
        return hit
    d = 2 * r
    ax = np.arange(d, dtype=float) - (d - 1) / 2.0
    rr = np.hypot(ax[:, None], ax[None, :]) / r
    a = np.exp(-rr * rr * 2.4)
    s = pygame.Surface((d, d), pygame.SRCALPHA)
    rgbv = pygame.surfarray.pixels3d(s)
    rgbv[...] = rgb
    del rgbv
    al = pygame.surfarray.pixels_alpha(s)
    al[...] = (a * 255.0).astype(np.uint8)
    del al
    _CACHE[k] = s
    return s


def _add_sprite(r: int, rgb: _RGB, inten: float) -> pygame.Surface:
    """Emitter halo for ADDITIVE blits: the falloff is baked into the
    RGB itself (BLEND_RGB_ADD ignores alpha and set_alpha — a flat-RGB
    sprite would add an opaque square). inten quantized for caching."""
    q = max(0, min(16, int(round(inten * 16))))
    k = ("addglow", r, rgb, q)
    hit = _CACHE.get(k)
    if hit is not None:
        return hit
    d = 2 * r
    ax = np.arange(d, dtype=float) - (d - 1) / 2.0
    rr = np.hypot(ax[:, None], ax[None, :]) / r
    g = np.exp(-rr * rr * 2.4) * (q / 16.0)
    s = pygame.Surface((d, d))
    rgbv = pygame.surfarray.pixels3d(s)
    rgbv[...] = (np.asarray(rgb, float)[None, None, :]
                 * g[..., None]).astype(np.uint8)
    del rgbv
    _CACHE[k] = s
    return s


# ---- swing arms + crew access arm -----------------------------------------

def arm_tip(geom: PadGeom, level: int, frac: float) -> tuple[int, int]:
    """Screen tip position of arm `level` (0 = crew, 1 = umbilical) at
    retract fraction frac (0 attached .. 1 stowed at the tower)."""
    y = geom.arm_y(level)
    x_on = geom.pad_x + 9
    x_off = geom.tower_x - 4
    u = _smooth(frac)
    # the swing reads as an arc: the tip sags then lifts as it comes home
    return (int(x_on + (x_off - x_on) * u),
            int(y + 5.0 * math.sin(math.pi * u)))


def draw_swing_arms(surf: pygame.Surface, geom: PadGeom,
                    frac: float) -> None:
    """The crew access arm (upper, with white room) and the propellant
    umbilical (lower) swinging from vehicle to tower. frac 0 = mated,
    1 = retracted. Draw AFTER pad_base and the vehicle."""
    tx = geom.tower_x
    for level in (1, 0):
        y = geom.arm_y(level)
        tip_x, tip_y = arm_tip(geom, level, frac)
        # truss boom: shaded underside, sun-lit top chord, hatching
        pts = [(tx, y - 3), (tip_x, tip_y - 2),
               (tip_x, tip_y + 2), (tx, y + 4)]
        pygame.draw.polygon(surf, _STEEL_DK, pts)
        pygame.draw.line(surf, _STEEL_LIT, (tx, y - 3),
                         (tip_x, tip_y - 2), 1)
        pygame.draw.line(surf, (30, 32, 38), (tx, y + 3),
                         (tip_x, tip_y + 1), 1)
        n_h = max(2, abs(tx - tip_x) // 7)
        for i in range(1, n_h):
            u = i / n_h
            hx = int(tx + (tip_x - tx) * u)
            hy0 = int(y - 2 + (tip_y - y) * u)
            pygame.draw.line(surf, _STEEL, (hx, hy0),
                             (hx + 3, hy0 + 4), 1)
        # hinge collar at the tower chord
        pygame.draw.rect(surf, _STEEL, (tx - 2, y - 4, 4, 9))
        pygame.draw.line(surf, _STEEL_LIT, (tx + 1, y - 4),
                         (tx + 1, y + 4), 1)
        if level == 0:
            # white room: NASA-white box w/ gradient + orange header
            wr = pygame.Rect(tip_x - 9, tip_y - 7, 10, 12)
            for row in range(wr.h):
                v = 206 - int(34 * row / wr.h)
                pygame.draw.line(surf, (v, v + 2, v + 5),
                                 (wr.x, wr.y + row),
                                 (wr.right - 1, wr.y + row))
            pygame.draw.rect(surf, _ORANGE, (wr.x, wr.y, wr.w, 2))
            pygame.draw.rect(surf, (26, 28, 34),
                             (wr.x + 2, wr.y + 4, 3, 6))     # doorway
            pygame.draw.line(surf, (8, 10, 14),
                             (wr.x, wr.bottom - 1),
                             (wr.right - 1, wr.bottom - 1), 1)
        else:
            # umbilical plate + drooping cryo lines to the vehicle
            pygame.draw.rect(surf, _STEEL, (tip_x - 3, tip_y - 4, 4, 8))
            pygame.draw.line(surf, _STEEL_LIT, (tip_x - 3, tip_y - 4),
                             (tip_x, tip_y - 4), 1)
            if frac < 0.55:
                sag = int(4 + 7 * (1.0 - frac))
                mx = (tip_x - 5 + geom.pad_x) // 2
                for off, col in ((0, (72, 76, 86)), (1, (40, 42, 50))):
                    pygame.draw.lines(
                        surf, col, False,
                        [(tip_x - 3, tip_y + 2 + off),
                         (mx, tip_y + 2 + sag + off),
                         (geom.pad_x + 6, tip_y + 1 + off)], 1)


def draw_hold_downs(surf: pygame.Surface, geom: PadGeom,
                    frac: float) -> None:
    """Hold-down clamps at the vehicle base; frac 0 closed -> 1 thrown
    open at release. Contact-shadowed onto the apron."""
    y = geom.deck_y
    u = _smooth(frac)
    for side in (-1, 1):
        bx = geom.pad_x + side * 13
        sh = _glow_sprite(7, _SHADOW)
        sh.set_alpha(90)
        surf.blit(sh, (bx - 7, y - 3))
        ang = u * 1.05
        dx = math.sin(ang) * 9 * side
        dy = -math.cos(ang) * 9
        base = (bx, y + 1)
        tip = (int(bx - side * 4 + dx), int(y - 8 + dy + 9 * u))
        pygame.draw.line(surf, _STEEL_DK, base, tip, 4)
        pygame.draw.line(surf, _STEEL_LIT,
                         (base[0] + 1, base[1] - 1),
                         (tip[0] + 1, tip[1]), 1)
        pygame.draw.line(surf, _ORANGE, tip,
                         (tip[0] + side * 2, tip[1] + 2), 2)
        pygame.draw.rect(surf, _STEEL, (bx - 3, y - 1, 6, 4))
        pygame.draw.line(surf, (30, 32, 38), (bx - 3, y + 2),
                         (bx + 2, y + 2), 1)


# ---- cryo behavior ----------------------------------------------------------

def draw_cryo_vents(surf: pygame.Surface, points, t: float,
                    wind_kt: float = 6.0, strength: float = 1.0) -> None:
    """Continuous LOX boil-off wisps from each (x, y) vent point,
    drifting downwind. Slot-based and stateless: same t, same frame."""
    if strength <= 0.0:
        return
    drift = max(-30.0, min(30.0, wind_kt)) * 1.1
    for pi, (px, py) in enumerate(points):
        for slot in range(4):
            period = 1.30 + 0.22 * _r01(f"vent|{pi}|{slot}")
            phase = period * _r01(f"ventp|{pi}|{slot}")
            age = (t + phase) % period
            u = age / period
            jx = (_r01(f"ventx|{pi}|{slot}|{int((t + phase) / period)}")
                  - 0.5) * 5.0
            x = px + jx + drift * u * u + 3.0 * u * math.sin(
                6.0 * u + slot)
            y = py - 7.0 * u + 2.5 * u * u * (drift * 0.12)
            r = int(2 + 9 * u)
            if r < 2:
                continue
            spr = _puff_sprite(r, (226, 231, 240),
                               key=f"vent{slot % 2}")
            a = int(105 * strength * (1.0 - u) * (0.4 + 0.6 * u))
            spr.set_alpha(a)
            surf.blit(spr, (int(x) - r, int(y) - r))


def frost_sprite(w: int, h: int, key: str = "frost") -> pygame.Surface:
    """Cryo frost/ice sheen band: blue-white value-noise with vertical
    run streaks and a sun-side sheen. SRCALPHA; tile/scale to the tank
    section rect."""
    k = ("frost", w, h, key)
    hit = _CACHE.get(k)
    if hit is not None:
        return hit
    rng = np.random.default_rng(_seed(f"{key}|{w}x{h}"))
    # cheap 2-octave value noise
    field = np.zeros((w, h))
    for cells, amp in ((6, 1.0), (14, 0.5), (30, 0.25)):
        lat = rng.random((cells + 1, max(2, cells * h // max(w, 1)) + 1))
        xs = np.linspace(0, lat.shape[0] - 1.001, w)
        ys = np.linspace(0, lat.shape[1] - 1.001, h)
        xi, yi = xs.astype(int), ys.astype(int)
        fx, fy = (xs - xi)[:, None], (ys - yi)[None, :]
        v00 = lat[xi][:, yi]
        v10 = lat[xi + 1][:, yi]
        v01 = lat[xi][:, yi + 1]
        v11 = lat[xi + 1][:, yi + 1]
        field += amp * ((v00 * (1 - fx) + v10 * fx) * (1 - fy)
                        + (v01 * (1 - fx) + v11 * fx) * fy)
    field /= field.max()
    # vertical melt-run streaks
    runs = rng.random(w)[:, None] * np.ones((1, h))
    streak = np.clip((runs - 0.86) * 6.0, 0.0, 1.0)
    ys = np.linspace(0.0, 1.0, h)[None, :]
    streak = streak * np.clip(ys * 3.0, 0.0, 1.0)
    a = np.clip(field * 0.85 + streak * 0.5, 0.0, 1.0)
    # band fades at top/bottom edges (frost pools mid-tank)
    a *= np.clip(np.sin(ys * math.pi) * 1.5, 0.0, 1.0)
    xs = np.linspace(-1.0, 1.0, w)[:, None]
    sheen = np.exp(-((xs - 0.45) / 0.34) ** 2)          # sun side
    rgb = (np.asarray((226.0, 236.0, 248.0))[None, None, :]
           * (0.86 + 0.14 * field[..., None])
           + sheen[..., None] * np.asarray((26.0, 22.0, 14.0)))
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    rgbv = pygame.surfarray.pixels3d(s)
    rgbv[...] = np.clip(rgb, 0.0, 255.0).astype(np.uint8)
    del rgbv
    al = pygame.surfarray.pixels_alpha(s)
    al[...] = (a * 200.0).astype(np.uint8)
    del al
    _CACHE[k] = s
    return s


def draw_frost(surf: pygame.Surface, rect: pygame.Rect,
               strength: float = 1.0, key: str = "frost") -> None:
    if strength <= 0.0 or rect.w < 2 or rect.h < 2:
        return
    spr = frost_sprite(rect.w, rect.h, key)
    spr.set_alpha(int(255 * min(1.0, strength)))
    surf.blit(spr, rect.topleft)


def draw_ice_shed(surf: pygame.Surface, rect: pygame.Rect, t: float,
                  rate: float = 1.0, key: str = "ice") -> None:
    """Ice shards shaking off the tank rect (ignition/liftoff).
    Closed-form ballistics per slot — stateless and deterministic."""
    if rate <= 0.0:
        return
    g = 420.0
    n = 16
    for slot in range(n):
        period = (0.55 + 0.5 * _r01(f"{key}|p|{slot}")) / max(rate, 0.1)
        phase = period * _r01(f"{key}|ph|{slot}")
        age = (t + phase) % period
        gen = int((t + phase) / period)
        u0 = _r01(f"{key}|x|{slot}|{gen}")
        side = -1 if u0 < 0.5 else 1
        x0 = rect.x + (2 + 3 * _r01(f"{key}|e|{slot}|{gen}")
                       if side < 0 else rect.w - 5
                       - 3 * _r01(f"{key}|e|{slot}|{gen}"))
        y0 = rect.y + rect.h * _r01(f"{key}|y|{slot}|{gen}")
        vx = side * (8.0 + 26.0 * _r01(f"{key}|v|{slot}|{gen}"))
        x = x0 + vx * age
        y = y0 + 0.5 * g * age * age + 14.0 * age
        life = 1.0
        a = int(210 * max(0.0, 1.0 - age / life))
        if a <= 0:
            continue
        ln = 2 + int(2 * _r01(f"{key}|l|{slot}|{gen}"))
        tumble = age * (6.0 + 6.0 * _r01(f"{key}|w|{slot}|{gen}"))
        dx = math.cos(tumble) * ln
        dy = math.sin(tumble) * ln
        ov = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
        pygame.draw.line(ov, (232, 240, 250, a), (int(x), int(y)),
                         (int(x + dx), int(y + dy)), 2)
        pygame.draw.line(ov, (130, 142, 160, a // 2),
                         (int(x + 1), int(y + 1)),
                         (int(x + dx + 1), int(y + dy + 1)), 1)
        surf.blit(ov, (0, 0))


# ---- ignition: deluge, steam, trench glow -----------------------------------

def draw_trench_glow(surf: pygame.Surface, geom: PadGeom,
                     throttle: float, t: float) -> None:
    """Flame-trench bounce light — a genuine emitter (bloom legal)."""
    if throttle <= 0.0:
        return
    flick = 0.84 + 0.10 * math.sin(t * 47.0) + 0.06 * math.sin(t * 23.0)
    base = throttle * flick
    core = _add_sprite(26, (255, 214, 150), 0.75 * base)
    surf.blit(core, (geom.pad_x - 26, geom.deck_y - 16),
              special_flags=pygame.BLEND_RGB_ADD)
    wide = _add_sprite(64, (255, 168, 92), 0.32 * base)
    surf.blit(wide, (geom.pad_x - 64, geom.deck_y - 36),
              special_flags=pygame.BLEND_RGB_ADD)
    # warm spill along the apron, both directions out of the trench
    spill = _add_sprite(40, (255, 190, 120), 0.22 * base)
    for side in (-1, 1):
        surf.blit(spill, (geom.pad_x + side * 60 - 40,
                          geom.deck_y - 26),
                  special_flags=pygame.BLEND_RGB_ADD)


def draw_deluge(surf: pygame.Surface, geom: PadGeom, t_since: float,
                throttle: float = 1.0) -> None:
    """Deluge water + the billowing steam sheet rolling out of the
    flame trench both ways. Layered lumpy puffs, lit warm on the trench
    side while the engines burn; cool white above. Stateless in t."""
    if t_since < 0.0:
        return
    y = geom.deck_y
    grow = min(1.0, t_since / 2.2)            # cloud establishes ~2 s
    warm = 0.65 * throttle
    # back layer first (high, cool), then front rolls (low, warm)
    for layer, (h_up, a_top, tint) in enumerate((
            (1.45, 76, (208, 212, 220)),
            (1.0, 104, (225, 228, 234)),
            (0.62, 128, (240, 242, 246)))):
        for side in (-1, 1):
            for slot in range(12):
                period = 1.7 + 0.9 * _r01(f"st|{layer}|{side}|{slot}")
                phase = period * _r01(f"stp|{layer}|{side}|{slot}")
                age = (t_since * 0.9 + phase) % period
                u = age / period
                reach = (24 + 130 * grow) * (0.10 + 0.90 * u)
                x = geom.pad_x + side * (8 + reach
                                         + 7 * math.sin(slot * 2.2))
                rise = (10 + 46 * grow * h_up) * (u ** 1.4) \
                    + 8 * math.sin(slot * 1.7)
                r = int((8 + 26 * u + 12 * grow) * (0.8 + 0.25 * h_up))
                spr = _puff_sprite(
                    max(3, r), tint,
                    warm_side=warm * max(0.0, 1.0 - u) if side > 0
                    else 0.0, key=f"steam{slot % 3}{side}")
                if side < 0:
                    spr = pygame.transform.flip(spr, True, False)
                a = int(a_top * (1.0 - u * u) * min(1.0, t_since * 2.0))
                if a <= 2:
                    continue
                spr.set_alpha(a)
                surf.blit(spr, (int(x) - r, int(y - 2 - rise) - r))
    # water jets arcing into the trench from both rails (drawn last,
    # they sit in front of the steam wall): tapered ribbons with a
    # bright spine, wobbling, with spray bursts where they land
    ov = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
    for side in (-1, 1):
        x0 = geom.pad_x + side * 46
        for j in range(3):
            jr = _r01(f"jet|{side}|{j}")
            arc = 17.0 + 5.0 * jr
            run = 30.0 + 7.0 * jr
            pts, pts_hi = [], []
            for k in range(11):
                u = k / 10.0
                wob = math.sin(t_since * 15.0 + k * 0.9 + j * 2.1) \
                    * 0.8 * u
                jx = x0 - side * (u * run) + wob
                jy = y - 5 - arc * math.sin(math.pi * min(u, 0.99)
                                            ) - j * 2
                pts.append((jx, jy))
                pts_hi.append((jx, jy - 1))
            for seg in range(10):
                a = int(165 * (1.0 - 0.45 * seg / 10.0))
                pygame.draw.line(ov, (208, 224, 240, a),
                                 pts[seg], pts[seg + 1], 3)
                pygame.draw.line(ov, (244, 250, 255, a),
                                 pts_hi[seg], pts_hi[seg + 1], 1)
        # spray burst where the curtain lands in the trench
        bx = x0 - side * 32
        pulse = 0.8 + 0.2 * math.sin(t_since * 11.0 + side)
        spr = _puff_sprite(7, (236, 244, 252), key="spray")
        spr.set_alpha(int(140 * pulse))
        ov.blit(spr, (int(bx) - 7, y - 14))
    surf.blit(ov, (0, 0))


# ---- PLUME V2 ---------------------------------------------------------------

def _plume_field(L: int, W: int, throttle: float, p_ratio: float,
                 fuel: str, vac: bool) -> tuple[np.ndarray, np.ndarray]:
    """(rgb, alpha) fields for a plume pointing +x. Sea level: tight
    column with mach diamonds. Altitude: the column feathers and
    flares as ambient pressure dies (pass p_ratio = p_amb/p_sl).
    Vacuum stage: wide translucent bell."""
    mid, edge, diam = PLUME_PALS.get(fuel, PLUME_PALS["ch4"])
    xs = np.linspace(0.0, 1.0, L)[:, None]
    ys = (np.arange(W, dtype=float) - (W - 1) / 2.0)[None, :]
    # soft windows so the sprite NEVER shows its own rectangle
    win_x = np.clip((1.0 - xs) / 0.10, 0.0, 1.0) \
        * np.clip(xs / 0.012 + 0.65, 0.0, 1.0)
    win_y = np.clip((W * 0.5 - np.abs(ys)) / 2.5, 0.0, 1.0)
    if vac:
        # wide translucent bell: fast expansion, no shock structure
        r0 = W * 0.06
        w = np.maximum(r0 + (W * 0.5 - 1.0 - r0) * xs ** 0.8, 1.0)
        rad = np.abs(ys) / w
        body = np.clip(1.0 - rad, 0.0, 1.0) ** 1.4
        fade = np.clip(1.0 - xs * 0.95, 0.0, 1.0) ** 1.1
        core = np.exp(-(ys / (w * 0.26)) ** 2) \
            * np.clip(1.0 - xs * 1.7, 0.0, 1.0)
        inten = np.clip(body * fade * 0.8 + core * 1.1, 0.0, 1.2) \
            * (0.55 + 0.45 * throttle)
        alpha = np.clip(inten, 0.0, 1.0) * 0.66 * win_x * win_y
    else:
        flare = (1.0 - p_ratio) ** 1.5
        spread = 0.45 + 2.6 * flare
        r0 = W * 0.22
        w = np.minimum(r0 * (0.94 + spread * xs ** 1.15),
                       W * 0.5 - 1.0)
        rad = np.abs(ys) / w
        body = np.clip(1.0 - rad, 0.0, 1.0) ** 1.6
        axial = 0.32 + 0.68 * np.exp(-xs * (2.0 + 1.4 * p_ratio))
        inten = body * axial
        # mach diamonds: bright shock-cell lozenges along the core with
        # dimmed gaps between; contrast dies and the cells stretch as
        # the ambient pressure falls away (pass p_amb/p_sl)
        contrast = max(0.0, p_ratio - 0.05) ** 0.5
        core_m = np.clip(1.0 - rad / 0.62, 0.0, 1.0) \
            * np.exp(-xs * 1.5)
        if contrast > 0.02:
            d0 = 0.10 + 0.08 * (1.0 - p_ratio)
            dia = np.zeros_like(inten)
            xk, k = 0.085, 0
            while xk < 0.95 and k < 8:
                amp = contrast * (0.78 ** k)
                tri = np.clip(1.0 - np.abs(xs - xk) / (0.46 * d0),
                              0.0, 1.0) ** 1.15
                lat = np.clip(1.0 - rad / 0.60, 0.0, 1.0) ** 1.8
                dia += amp * tri * lat
                xk += d0 * (1.0 + 0.13 * k)
                k += 1
            inten = inten * (1.0 - 0.45 * contrast * core_m) \
                + dia * 1.2
        inten = inten + core_m * np.exp(-xs * 9.0) * 0.85  # exit blaze
        inten = np.clip(inten, 0.0, 1.8)
        alpha = np.clip(inten * (1.15 - 0.40 * xs), 0.0, 1.0) \
            * (0.62 + 0.38 * throttle) * win_x * win_y
    # color ramp: white core -> mid -> cool edge; diamonds push warm
    u = np.clip(inten, 0.0, 1.0)
    white = np.asarray((236.0, 243.0, 255.0)) if vac \
        else np.asarray((255.0, 252.0, 246.0))
    midc = np.asarray(mid, float)
    edgec = np.asarray(edge, float)
    hi = np.clip((u - 0.55) / 0.45, 0.0, 1.0) ** 1.1
    lo = np.clip(u / 0.55, 0.0, 1.0)
    rgb = (edgec[None, None, :] * (1.0 - lo[..., None])
           + midc[None, None, :] * lo[..., None])
    rgb = rgb * (1.0 - hi[..., None]) + white[None, None, :] \
        * hi[..., None]
    if not vac:
        dwarm = np.asarray(diam, float)
        over = np.clip(inten - 1.0, 0.0, 0.6) / 0.6
        rgb = rgb * (1.0 - over[..., None]) + dwarm[None, None, :] \
            * over[..., None]
    return rgb, np.clip(alpha, 0.0, 1.0)


def plume_sprite(throttle: float, p_ratio: float, *, fuel: str = "ch4",
                 vac: bool = False, length: int = 150,
                 width: int = 44) -> pygame.Surface:
    """Cached plume sprite pointing +x, nozzle at (0, width/2).
    Quantized on (throttle, p_ratio) so warp/ascent doesn't rebuild
    every frame."""
    tq = round(max(0.0, min(1.0, throttle)) * 10) / 10.0
    pq = round(max(0.0, min(1.0, p_ratio)) * 20) / 20.0
    L = max(24, int(length))
    W = max(12, int(width) | 1)
    k = ("plume", tq, pq, fuel, vac, L, W)
    hit = _CACHE.get(k)
    if hit is not None:
        return hit
    rgb, a = _plume_field(L, W, tq, pq, fuel, vac)
    s = pygame.Surface((L, W), pygame.SRCALPHA)
    rgbv = pygame.surfarray.pixels3d(s)
    rgbv[...] = np.clip(rgb, 0.0, 255.0).astype(np.uint8)
    del rgbv
    al = pygame.surfarray.pixels_alpha(s)
    al[...] = (a * 255.0).astype(np.uint8)
    del al
    if len(_CACHE) > 160:
        _CACHE.clear()
        _CACHE[k] = s
    else:
        _CACHE[k] = s
    return s


def draw_plume(surf: pygame.Surface, nozzle: tuple[float, float],
               angle_deg: float, throttle: float, p_ratio: float, *,
               gimbal_deg: float = 0.0, scale: float = 1.0,
               t: float = 0.0, fuel: str = "ch4",
               vac: bool = False) -> None:
    """The engine plume, MISSION FILM's bloom hero. angle_deg is the
    EXHAUST direction in screen coords (0 = +x right, 90 = up); gimbal
    deflects it. Length/width breathe with a deterministic flicker."""
    if throttle <= 0.0:
        return
    flick = 1.0 + 0.040 * math.sin(t * 53.0) + 0.025 * math.sin(
        t * 31.0 + 1.3)
    L = int((150 + 110 * throttle) * scale * flick
            * (1.0 + 0.9 * (1.0 - p_ratio) * (0.0 if vac else 1.0)))
    W = int(130 * scale) if vac else int(
        (46 + 90 * (1.0 - p_ratio)) * scale)
    spr = plume_sprite(throttle, p_ratio, fuel=fuel, vac=vac,
                       length=L, width=W)
    ang = angle_deg + gimbal_deg
    rot = pygame.transform.rotozoom(spr, ang, 1.0)
    # nozzle anchor: rotate the (center -> nozzle) vector. rotozoom's
    # positive angle is CCW in math coords = CCW on screen with y down
    # handled by negating the y component.
    rad = math.radians(ang)
    # pygame's positive rotation is visually CCW: screen-space rotation
    # of a vector (x, y) is (x cos + y sin, -x sin + y cos)
    vx, vy = -L / 2.0 + 1.0, 0.0
    rx = vx * math.cos(rad) + vy * math.sin(rad)
    ry = -vx * math.sin(rad) + vy * math.cos(rad)
    cx = nozzle[0] - rx
    cy = nozzle[1] - ry
    surf.blit(rot, (int(cx - rot.get_width() / 2.0),
                    int(cy - rot.get_height() / 2.0)))
    # additive throat glow — the emitter the GL bloom keys on
    gr = max(4, int((7 + 7 * throttle) * scale))
    glow = _add_sprite(gr, (255, 244, 224) if not vac
                       else (210, 224, 255),
                       0.8 * throttle * (0.5 if vac else 1.0) * flick)
    dx = math.cos(rad) * gr * 0.6
    dy = -math.sin(rad) * gr * 0.6
    surf.blit(glow, (int(nozzle[0] + dx) - gr, int(nozzle[1] + dy) - gr),
              special_flags=pygame.BLEND_RGB_ADD)


# ---- staging debris ---------------------------------------------------------

def draw_staging(surf: pygame.Surface, pos: tuple[float, float],
                 axis_deg: float, t_since: float, *,
                 scale: float = 1.0, key: str = "sep") -> None:
    """Stage separation: pyro flash, tumbling interstage/fairing
    halves falling away perpendicular to the flight axis, ice/dust
    puffs at the sep plane. axis_deg = vehicle axis (0 right, 90 up).
    Stateless in t_since."""
    if t_since < 0.0 or t_since > 6.0:
        return
    rad = math.radians(axis_deg)
    ax, ay = math.cos(rad), -math.sin(rad)          # axis, screen
    px, py = -ay, ax                                # perpendicular
    # pyro flash (first ~0.25 s): ring + spark streaks, additive
    if t_since < 0.25:
        a = math.exp(-t_since / 0.075)
        gr = max(4, int(16 * scale))
        fl = _add_sprite(gr, (255, 240, 214), 0.9 * a)
        surf.blit(fl, (int(pos[0]) - gr, int(pos[1]) - gr),
                  special_flags=pygame.BLEND_RGB_ADD)
        ov = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
        for i in range(8):
            th = i * math.pi / 4.0 + 0.3
            r1 = (6 + 34 * t_since / 0.25) * scale
            sx = pos[0] + math.cos(th) * r1
            sy = pos[1] + math.sin(th) * r1
            pygame.draw.line(ov, (255, 226, 180, int(220 * a)),
                             (int(pos[0] + math.cos(th) * r1 * 0.55),
                              int(pos[1] + math.sin(th) * r1 * 0.55)),
                             (int(sx), int(sy)), 1)
        surf.blit(ov, (0, 0))
    # two shell halves: kicked apart, decelerating along the axis
    # (the live stage pulls ahead), tumbling as they go
    for side, wkey in ((-1, "a"), (1, "b")):
        kick = (26.0 + 14.0 * _r01(f"{key}|k|{wkey}")) * scale
        drop = 34.0 * scale
        x = pos[0] + px * side * kick * t_since \
            - ax * drop * t_since * (0.4 + 0.45 * t_since)
        y = pos[1] + py * side * kick * t_since \
            - ay * drop * t_since * (0.4 + 0.45 * t_since)
        om = (2.4 + 1.6 * _r01(f"{key}|w|{wkey}")) * (1 if side > 0
                                                      else -1)
        th = math.radians(axis_deg) + om * t_since
        ln = 13.0 * scale
        wd = 4.0 * scale
        c, s_ = math.cos(th), math.sin(th)
        pts = []
        for ex, ey in ((-ln, -wd), (ln, -wd), (ln + 2 * scale, 0),
                       (ln, wd), (-ln, wd)):
            pts.append((int(x + ex * c - ey * s_),
                        int(y + ex * s_ + ey * c)))
        fade = max(0.0, 1.0 - t_since / 6.0)
        ov = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
        pygame.draw.polygon(ov, (132, 138, 148, int(235 * fade)), pts)
        pygame.draw.line(ov, (196, 202, 212, int(235 * fade)),
                         pts[0], pts[1], 1)              # sun-lit edge
        pygame.draw.line(ov, (40, 44, 52, int(235 * fade)),
                         pts[4], pts[3], 1)              # shaded edge
        surf.blit(ov, (0, 0))
    # sep-plane ice/dust puffs
    for i in range(6):
        u0 = _r01(f"{key}|pf|{i}")
        life = 0.9 + 0.5 * u0
        if t_since > life:
            continue
        u = t_since / life
        th = u0 * 2.0 * math.pi
        d = (4.0 + 26.0 * u) * scale
        r = max(2, int((3 + 9 * u) * scale))
        spr = _puff_sprite(r, (224, 228, 236), key=f"sep{i % 2}")
        spr.set_alpha(int(120 * (1.0 - u)))
        surf.blit(spr, (int(pos[0] + math.cos(th) * d) - r,
                        int(pos[1] + math.sin(th) * d * 0.6) - r))
