"""Procedural part & vessel sprites (14 §2 palette, §3.2 world vector
layer, §4.2 propellant-family catalog; 12 §5.7 icon grammar).

Everything is drawn with pygame.draw / surfarray / numpy at build time — no
image or font assets, no display calls (plain SRCALPHA surfaces, so the
module is headless-safe). Sizes derive from the part's real data: tank
girth/length from capacity over mixture bulk density (cylinder at a
per-family aspect ratio), engine bell diameter from sqrt(thrust) widened by
vacuum expansion (1 - Isp_sl/Isp_vac). Minor cosmetic variation (weld-line
placement, pipe routing) is seeded from a stable hash of the part id, so
two builds of the same id are pixel-identical. Every entry point memoizes
into a module-level cache: generation may be slow once, lookups are O(1).
"""

from __future__ import annotations

import hashlib
import math

import numpy as np
import pygame

# 14 §2 binding palette (canonical constants; UI modules may import these).
SPACE_BG = (6, 8, 14)
PANEL_FILL = (10, 16, 28, 220)
PANEL_EDGE = (42, 58, 85)
ACCENT = (140, 235, 255)
GOOD = (120, 255, 170)
WARN = (255, 200, 90)
DANGER = (255, 110, 110)
GOLD = (255, 215, 130)
TEXT = (200, 210, 224)
TEXT_DIM = (110, 122, 140)

# Engine bell (base, highlight) per propellant family (14 §4.2 catalog).
_BELL_COLORS: dict[str, tuple[tuple[int, int, int], tuple[int, int, int]]] = {
    "hydrolox": ((176, 192, 214), (228, 238, 252)),
    "kerolox": ((168, 124, 66), (224, 180, 110)),
    "methalox": ((74, 138, 140), (140, 206, 206)),
    "hypergolic": ((116, 118, 72), (168, 170, 116)),
    "ntr": ((128, 132, 140), (190, 196, 206)),
    "ion": ((132, 104, 182), (190, 164, 236)),
}

# Tank contents band tint by the defining (non-oxidizer) resource.
_CONTENT_COLORS: dict[str, tuple[int, int, int]] = {
    "Oxygen": (170, 225, 240),     # LOX pale cyan
    "Hydrogen": (215, 230, 255),   # LH2 near-white blue
    "Methane": (90, 200, 190),     # teal
    "RP1": (235, 180, 90),         # amber
    "NTO": (150, 150, 80),         # olive
    "MMH": (150, 150, 80),
    "Water": (110, 170, 230),
    "Nitrogen": (140, 160, 175),
    "Xenon": (170, 130, 220),      # violet
}

# Bulk densities (kg/m^3) for tank volume sizing; gases at COPV pressure.
_DENSITY_KG_M3: dict[str, float] = {
    "Oxygen": 1141.0, "Hydrogen": 71.0, "Methane": 423.0, "RP1": 810.0,
    "NTO": 1440.0, "MMH": 880.0, "Water": 1000.0, "Nitrogen": 280.0,
    "Xenon": 1600.0,
}

_PLUME_FRAMES = 8
_ICON_SECTORS = 24

_PART_CACHE: dict[tuple[str, float], pygame.Surface] = {}
_THUMB_CACHE: dict[tuple[str, int], pygame.Surface] = {}
_VESSEL_CACHE: dict[tuple, pygame.Surface] = {}
_ICON_CACHE: dict[tuple[int, int, bool], pygame.Surface] = {}
_PLUME_CACHE: dict[tuple[int, int, int], pygame.Surface] = {}
_APP_ICON: list[pygame.Surface] = []
_FONTS: dict[int, pygame.font.Font] = {}


def _rng(seed_id: str) -> np.random.Generator:
    seed = int.from_bytes(
        hashlib.blake2b(seed_id.encode(), digest_size=8).digest(), "little")
    return np.random.default_rng(seed)


def _font(size: int) -> pygame.font.Font:
    if size not in _FONTS:
        if not pygame.font.get_init():
            pygame.font.init()
        _FONTS[size] = pygame.font.SysFont("consolas", size)
    return _FONTS[size]


def _fit(w: float, h: float, min_w: float, min_h: float,
         max_dim: float) -> tuple[int, int]:
    """Uniformly scale (w, h) px up to the minimums, then down to the cap."""
    scale = max(1.0, min_w / w, min_h / h)
    w, h = w * scale, h * scale
    over = max(w, h) / max_dim
    if over > 1.0:
        w, h = w / over, h / over
    return max(int(round(w)), 6), max(int(round(h)), 8)


# -- physical sizing -----------------------------------------------------


def _engine_family(propellant: dict[str, float]) -> str:
    if "RP1" in propellant:
        return "kerolox"
    if "Methane" in propellant:
        return "methalox"
    if "NTO" in propellant or "MMH" in propellant:
        return "hypergolic"
    if "Xenon" in propellant or "Argon" in propellant:
        return "ion"
    if "Hydrogen" in propellant and "Oxygen" in propellant:
        return "hydrolox"
    if "Hydrogen" in propellant:
        return "ntr"                  # pure-H2 expansion = nuclear thermal
    return "hypergolic"


def _engine_dims_m(part: dict) -> tuple[float, float]:
    """(exit diameter, overall length) from thrust + vacuum expansion."""
    eng = part["engine"]
    kn = float(eng["thrust_kN"])
    vac = min(max(1.0 - eng.get("isp_sl_s", eng["isp_s"]) / eng["isp_s"],
                  0.0), 1.0)
    d = 0.042 * math.sqrt(kn) * (1.0 + 0.7 * vac)
    d = min(max(d, 0.5), 5.0)
    return d, 1.7 * d + 0.45


def _mixture_density(mixture: dict[str, float]) -> float:
    inv = sum(frac / _DENSITY_KG_M3.get(res, 1000.0)
              for res, frac in mixture.items())
    return 1.0 / inv if inv > 0.0 else 1000.0


def _tank_aspect(mixture: dict[str, float]) -> float:
    if "Xenon" in mixture or "Nitrogen" in mixture:
        return 1.5                    # squat COPV bottles
    if set(mixture) == {"Hydrogen"}:
        return 3.0                    # deep-cryo LH2 runs long
    return 2.4


def _tank_dims_m(part: dict) -> tuple[float, float]:
    """(diameter, body length) of the capacity cylinder at family aspect."""
    tank = part["tank"]
    vol = tank["capacity_t"] * 1_000.0 / _mixture_density(tank["mixture"])
    aspect = _tank_aspect(tank["mixture"])
    d = (4.0 * vol / (math.pi * aspect)) ** (1.0 / 3.0)
    d = min(max(d, 0.9), 9.0)
    body = min(max(vol / (math.pi * (d / 2.0) ** 2), 0.9 * d), 30.0)
    return d, body


def _content_color(mixture: dict[str, float]) -> tuple[int, int, int]:
    fuels = {res: frac for res, frac in mixture.items() if res != "Oxygen"}
    res = max(fuels, key=fuels.get) if fuels else "Oxygen"
    return _CONTENT_COLORS.get(res, (150, 160, 175))


# -- part builders -------------------------------------------------------


def _build_engine(part: dict, part_id: str, ppm: float) -> pygame.Surface:
    eng = part["engine"]
    fam = _engine_family(eng.get("propellant", {}))
    base, hi = _BELL_COLORS[fam]
    d_m, l_m = _engine_dims_m(part)
    W, H = _fit(d_m * ppm, l_m * ppm, 14.0, 18.0, 256.0)
    surf = pygame.Surface((W, H), pygame.SRCALPHA)
    rng = _rng(part_id)
    cx = W / 2.0

    # gimbal mount
    mw, mh = max(2, int(0.20 * W)), max(1, int(0.07 * H))
    pygame.draw.rect(surf, (66, 74, 90),
                     pygame.Rect(int(cx - mw / 2), 0, mw, mh + 1))

    # powerhead box with piping
    pw = max(4, int(0.52 * W))
    head = pygame.Rect(int(cx - pw / 2), mh, pw, max(3, int(0.25 * H)))
    pygame.draw.rect(surf, (50, 56, 68), head)
    pygame.draw.rect(surf, PANEL_EDGE, head, 1)
    for _ in range(2 + int(rng.integers(0, 2))):
        px = head.left + 2 + int(rng.integers(0, max(1, head.width - 4)))
        pygame.draw.line(surf, (96, 106, 122),
                         (px, head.top + 2), (px, head.bottom - 2))
        ey = head.top + 2 + int(rng.integers(0, max(1, head.height - 4)))
        pygame.draw.line(surf, (96, 106, 122),
                         (px, ey), (min(px + 3, head.right - 2), ey))
    if fam == "ntr":                  # hazard chevrons over the powerhead
        for k, x in enumerate(range(head.left + 1, head.right - 1, 4)):
            col = WARN if k % 2 == 0 else (24, 24, 26)
            pygame.draw.line(surf, col, (x, head.bottom - 2),
                             (min(x + 3, head.right - 2), head.top + 1), 2)

    # bell: curved trapezoid, throat to exit lip
    y_t, y_e = head.bottom, H - 1
    hw_t, hw_e = max(1.5, 0.13 * W), W / 2.0 - 1.0
    prof = [(y_t + (y_e - y_t) * t, hw_t + (hw_e - hw_t) * t ** 0.7)
            for t in (i / 11.0 for i in range(12))]
    left = [(cx - hw, y) for y, hw in prof]
    right = [(cx + hw, y) for y, hw in prof]
    pygame.draw.polygon(surf, base, left + right[::-1])
    hi_layer = pygame.Surface((W, H), pygame.SRCALPHA)
    pygame.draw.polygon(hi_layer, (*hi, 110),
                        [(cx - hw * 0.55, y) for y, hw in prof]
                        + [(cx - hw * 0.22, y) for y, hw in prof][::-1])
    surf.blit(hi_layer, (0, 0))
    edge = tuple(int(c * 0.55) for c in base)
    pygame.draw.lines(surf, edge, False, left)
    pygame.draw.lines(surf, edge, False, right)

    # inner dark throat + exit-mouth interior with a lit rim
    pygame.draw.ellipse(surf, (16, 17, 22),
                        pygame.Rect(int(cx - hw_t), y_t - 1,
                                    max(2, int(2 * hw_t)),
                                    max(2, int(0.04 * H))))
    mouth_h = max(2, int(0.05 * H))
    mouth = pygame.Rect(int(cx - hw_e) + 1, H - mouth_h - 1,
                        max(2, int(2 * hw_e) - 2), mouth_h)
    pygame.draw.ellipse(surf, (14, 15, 20), mouth)
    pygame.draw.ellipse(surf, tuple(min(255, int(c * 1.25)) for c in base),
                        mouth, 1)
    return surf


def _build_tank(part: dict, part_id: str, ppm: float) -> pygame.Surface:
    mixture = part["tank"]["mixture"]
    d_m, body_m = _tank_dims_m(part)
    W, H = _fit(d_m * ppm, (body_m + 0.36 * d_m) * ppm, 12.0, 18.0, 320.0)
    surf = pygame.Surface((W, H), pygame.SRCALPHA)
    rng = _rng(part_id)
    dome = max(2, int(round(0.18 * W)))
    body_top, body_bot = dome, H - dome
    body_h = max(1, body_bot - body_top)

    # cylindrical shading column by column (rounded-dome capsule silhouette)
    hull = (104.0, 112.0, 128.0)
    for x in range(W):
        u = (x + 0.5) / W
        bulge = math.sqrt(max(0.0, 1.0 - (2.0 * u - 1.0) ** 2))
        lum = (0.40 + 0.58 * bulge
               + 0.22 * math.exp(-((u - 0.36) / 0.10) ** 2))
        col = tuple(int(min(255.0, c * lum)) for c in hull)
        dy = int(round(dome * (1.0 - bulge)))
        pygame.draw.line(surf, col, (x, dy), (x, H - 1 - dy))

    # subtle top-lit axial gradient (surfarray pass)
    arr = pygame.surfarray.pixels3d(surf)
    grad = np.linspace(1.06, 0.86, H)
    arr[...] = np.clip(arr * grad[np.newaxis, :, np.newaxis],
                       0.0, 255.0).astype(np.uint8)
    del arr

    # hoop weld lines (seeded placement)
    n_welds = 2 + int(rng.integers(0, 2))
    for f in sorted(rng.uniform(0.18, 0.85, size=n_welds)):
        y = body_top + int(f * body_h)
        pygame.draw.line(surf, (62, 68, 82), (1, y), (W - 2, y))
        pygame.draw.line(surf, (138, 146, 160), (1, y + 1), (W - 2, y + 1))

    # contents band near the top dome
    band = _content_color(mixture)
    bh = max(2, int(0.05 * H))
    by = body_top + max(1, int(0.10 * body_h))
    pygame.draw.rect(surf, band, pygame.Rect(1, by, W - 2, bh))
    pygame.draw.rect(surf, tuple(int(c * 0.55) for c in band),
                     pygame.Rect(1, by, W - 2, bh), 1)

    # stenciled tier text
    if W >= 18 and H >= 28:
        label = _font(9).render(str(part.get("tier", "T0")), True, TEXT_DIM)
        if label.get_width() <= W - 4:
            lx = int(W / 2 - label.get_width() / 2 + rng.integers(-1, 2))
            surf.blit(label, (lx, body_top + int(0.60 * body_h)))
    return surf


def _build_fairing(part: dict, part_id: str, ppm: float) -> pygame.Surface:
    d_m = min(6.0, 1.2 + 0.9 * float(part.get("mass_t", 1.0)) ** (1.0 / 3.0))
    W, H = _fit(d_m * ppm, 2.1 * d_m * ppm, 12.0, 18.0, 256.0)
    surf = pygame.Surface((W, H), pygame.SRCALPHA)
    rng = _rng(part_id)
    cx, hw_e, shoulder = W / 2.0, W / 2.0 - 1.0, 0.72
    prof = [(1.0 + (i / 12.0) * (H - 2.0),
             hw_e * min(1.0, ((i / 12.0) / shoulder) ** 0.62))
            for i in range(13)]
    left = [(cx - hw, y) for y, hw in prof]
    right = [(cx + hw, y) for y, hw in prof]
    pygame.draw.polygon(surf, (222, 226, 233), left + right[::-1])
    hi_layer = pygame.Surface((W, H), pygame.SRCALPHA)
    pygame.draw.polygon(hi_layer, (255, 255, 255, 70),
                        [(cx - hw * 0.5, y) for y, hw in prof]
                        + [(cx - hw * 0.2, y) for y, hw in prof][::-1])
    surf.blit(hi_layer, (0, 0))
    pygame.draw.lines(surf, (150, 156, 168), False, left)
    pygame.draw.lines(surf, (150, 156, 168), False, right)
    # grey stripe near the base (seeded one-pixel jitter)
    sy = int(0.80 * H) + int(rng.integers(-1, 2))
    pygame.draw.rect(surf, (118, 126, 140),
                     pygame.Rect(1, sy, W - 2, max(2, int(0.06 * H))))
    return surf


# -- public API ----------------------------------------------------------


def part_sprite(part: dict, part_id: str,
                px_per_m: float = 4.0) -> pygame.Surface:
    """Side-view sprite for one catalog part, sized from its real data.

    Engines render nozzle-down (gimbal mount at the top), tanks as shaded
    capsules with a contents band, structures as a white fairing cone.
    """
    key = (part_id, round(px_per_m, 3))
    hit = _PART_CACHE.get(key)
    if hit is not None:
        return hit
    kind = part.get("type")
    if kind == "engine" and "engine" in part:
        surf = _build_engine(part, part_id, px_per_m)
    elif kind == "tank" and "tank" in part:
        surf = _build_tank(part, part_id, px_per_m)
    else:
        surf = _build_fairing(part, part_id, px_per_m)
    _PART_CACHE[key] = surf
    return surf


def part_thumb(part: dict, part_id: str, size: int = 28) -> pygame.Surface:
    """Square catalog thumbnail: the part sprite centered in size x size."""
    key = (part_id, int(size))
    hit = _THUMB_CACHE.get(key)
    if hit is not None:
        return hit
    spr = part_sprite(part, part_id, 6.0)
    w, h = spr.get_size()
    f = min((size - 2) / w, (size - 2) / h, 1.0)
    if f < 1.0:
        spr = pygame.transform.smoothscale(
            spr, (max(1, int(w * f)), max(1, int(h * f))))
    thumb = pygame.Surface((size, size), pygame.SRCALPHA)
    thumb.blit(spr, ((size - spr.get_width()) // 2,
                     (size - spr.get_height()) // 2))
    _THUMB_CACHE[key] = thumb
    return thumb


def _draw_fins(surf: pygame.Surface, cx: int, hull_w: int,
               top: int, bot: int, fin_w: int) -> None:
    """4 fins in side view: 2 outer silhouettes + 2 foreshortened center."""
    fin_h = max(8, int(0.45 * max(8, bot - top)))
    hw = max(2, hull_w // 2)
    for sx in (-1, 1):                # projected front/back pair, darker
        xi = cx + sx * max(1, hw // 4)
        pygame.draw.polygon(surf, (48, 54, 66),
                            [(xi, bot - int(fin_h * 0.7)), (xi, bot),
                             (xi + sx * max(2, int(fin_w * 0.4)), bot)])
    for sx in (-1, 1):                # outer silhouette pair
        x0 = cx + sx * (hw - 1)
        pts = [(x0, bot - fin_h), (x0, bot), (x0 + sx * fin_w, bot)]
        pygame.draw.polygon(surf, (70, 78, 92), pts)
        pygame.draw.lines(surf, (112, 122, 138), True, pts)


def vessel_sprite(db, stack: list[list[str]],
                  px_per_m: float = 3.0) -> pygame.Surface:
    """The assembled rocket, bottom stage at the bottom of the image.

    stack is the builder's bottom-first stage list of part ids; db.parts[pid]
    yields the part dict. Per stage: payload/structures on top, tanks below
    them, engines clustered side by side underneath; a darker interstage
    ring joins stages; the bottom stage grows 4 fins when it clusters 2+
    engines. The result is auto-scaled to fit within ~440 px height.
    """
    key = (tuple(tuple(stage) for stage in stack), round(px_per_m, 3))
    hit = _VESSEL_CACHE.get(key)
    if hit is not None:
        return hit

    stages: list[tuple[list, list, list]] = []
    for stage in stack:
        eng: list = []
        tank: list = []
        struct: list = []
        for pid in stage:
            part = db.parts[pid]
            spr = part_sprite(part, pid, px_per_m)
            {"engine": eng, "tank": tank}.get(part.get("type"),
                                              struct).append(spr)
        stages.append((eng, tank, struct))
    if not any(e or t or s for e, t, s in stages):
        empty = pygame.Surface((8, 8), pygame.SRCALPHA)
        _VESSEL_CACHE[key] = empty
        return empty

    gap, ring_h = 2, 5
    dims = []                          # (block_w, block_h, hull_w, engine_h)
    for eng, tank, struct in stages:
        ew = sum(s.get_width() for s in eng) + gap * max(0, len(eng) - 1)
        eh = max((s.get_height() for s in eng), default=0)
        hull_w = max((s.get_width() for s in tank + struct), default=ew)
        stack_h = sum(s.get_height() for s in tank + struct)
        dims.append((max(ew, hull_w), stack_h + eh, hull_w, eh))
    fins = len(stages[0][0]) >= 2
    fin_w = max(6, int(0.5 * dims[0][2])) if fins else 0
    total_w = max(d[0] for d in dims) + 2 * fin_w + (2 if fins else 0)
    total_h = sum(d[1] for d in dims) + ring_h * (len(stages) - 1)
    surf = pygame.Surface((max(total_w, 1), max(total_h, 1)),
                          pygame.SRCALPHA)
    cx = total_w // 2

    y = 0
    for i in range(len(stages) - 1, -1, -1):
        eng, tank, struct = stages[i]
        for spr in struct:             # payload/fairing tops the stage
            surf.blit(spr, (cx - spr.get_width() // 2, y))
            y += spr.get_height()
        tank_top = y
        for spr in tank:
            surf.blit(spr, (cx - spr.get_width() // 2, y))
            y += spr.get_height()
        if i == 0 and fins:
            _draw_fins(surf, cx, dims[0][2], tank_top, y, fin_w)
        ew = sum(s.get_width() for s in eng) + gap * max(0, len(eng) - 1)
        x = cx - ew // 2
        for spr in eng:                # engines clustered side by side
            surf.blit(spr, (x, y))
            x += spr.get_width() + gap
        y += dims[i][3]
        if i > 0:                      # darker interstage ring
            rw = max(8, int(0.85 * min(dims[i][2] or dims[i][0],
                                       dims[i - 1][2] or dims[i - 1][0])))
            ring = pygame.Rect(cx - rw // 2, y, rw, ring_h)
            pygame.draw.rect(surf, (26, 32, 44), ring)
            pygame.draw.rect(surf, PANEL_EDGE, ring, 1)
            y += ring_h

    f = min(1.0, 440.0 / surf.get_height(), 500.0 / surf.get_width())
    if f < 1.0:
        surf = pygame.transform.smoothscale(
            surf, (max(1, int(surf.get_width() * f)),
                   max(1, int(surf.get_height() * f))))
    _VESSEL_CACHE[key] = surf
    return surf


def _part_dims_m(part: dict) -> tuple[float, float]:
    """(diameter, length) for ANY part, using the same sizing the art uses
    — so the aero cross-section below matches what the player sees."""
    if "engine" in part:
        return _engine_dims_m(part)
    if "tank" in part:
        d, body = _tank_dims_m(part)
        return d, body
    # structure / crew block: scale with mass like _build_fairing does
    d = min(max(1.2 + 0.35 * math.sqrt(part.get("mass_t", 1.0)), 1.0), 6.0)
    return d, 1.4 * d


def vessel_metrics(db, stack: list[list[str]]) -> tuple[float, float]:
    """(overall height m, max diameter m) of the assembled stack."""
    height = 0.0
    dia = 0.0
    for stage in stack:
        eng_h = 0.0
        for pid in stage:
            part = db.parts[pid]
            d, length = _part_dims_m(part)
            if "engine" in part:
                eng_h = max(eng_h, length)
            else:
                height += length
            dia = max(dia, d)
        height += eng_h
    return height, dia


def vessel_frontal_area(db, stack: list[list[str]]) -> float:
    """Aero reference area (Cd*A proxy) from the stack's real max diameter.
    A pointed nose (topmost part of the TOP stage is a structure fairing or
    crew capsule) earns a 0.7 shape discount; a blunt tank/engine nose does
    not. Returns m² for Vessel(cd_a_m2=...)."""
    _, dia = vessel_metrics(db, stack)
    if dia <= 0.0:
        return 3.2
    area = math.pi * (dia / 2.0) ** 2 * 0.5         # Cd 0.5 baseline
    top_stage = next((s for s in reversed(stack) if s), None)
    if top_stage:
        nose = db.parts[top_stage[-1]]
        if nose.get("type") in ("structure", "crew"):
            area *= 0.7
    return max(0.8, area)


def craft_icon(heading_rad: float, size: int = 18,
               burning: bool = False) -> pygame.Surface:
    """In-flight map marker, nose along heading_rad (screen coords, y-down).

    Heading is quantized to 24 sectors for the cache; the returned surface
    is (2*size, 2*size) so any rotation fits without clipping.
    """
    sector = int(round((heading_rad % math.tau)
                       / (math.tau / _ICON_SECTORS))) % _ICON_SECTORS
    key = (sector, int(size), bool(burning))
    hit = _ICON_CACHE.get(key)
    if hit is not None:
        return hit

    s = int(size)
    c = 2 * s
    base = pygame.Surface((c, c), pygame.SRCALPHA)
    ccx = ccy = c / 2.0
    length, hw = 0.92 * s, 0.20 * s
    nose_x, tail_x = ccx + length / 2.0, ccx - length / 2.0

    pw, phh = max(2, int(0.34 * s)), max(2, int(0.16 * s))
    for top in (ccy - hw - phh, ccy + hw):     # solar panel pair
        rect = pygame.Rect(int(ccx - 0.12 * length - pw / 2), int(top),
                           pw, phh)
        pygame.draw.rect(base, (36, 64, 96), rect)
        pygame.draw.rect(base, ACCENT, rect, 1)
    if burning:                                # additive flame at the tail
        fl = 0.5 * s
        flame = pygame.Surface((c, c), pygame.SRCALPHA)
        pygame.draw.polygon(flame, (255, 168, 70, 230),
                            [(tail_x, ccy - 0.6 * hw),
                             (tail_x, ccy + 0.6 * hw), (tail_x - fl, ccy)])
        pygame.draw.polygon(flame, (255, 240, 210, 255),
                            [(tail_x, ccy - 0.3 * hw),
                             (tail_x, ccy + 0.3 * hw),
                             (tail_x - 0.55 * fl, ccy)])
        base.blit(flame, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
    hull = [(nose_x, ccy), (ccx + 0.15 * length, ccy - hw),
            (tail_x, ccy - 0.7 * hw), (tail_x, ccy + 0.7 * hw),
            (ccx + 0.15 * length, ccy + hw)]
    pygame.draw.polygon(base, (205, 232, 244), hull)
    pygame.draw.lines(base, ACCENT, True, hull)
    pygame.draw.polygon(base, (245, 250, 255),
                        [(nose_x, ccy), (ccx + 0.3 * length, ccy - 0.55 * hw),
                         (ccx + 0.3 * length, ccy + 0.55 * hw)])

    # pygame rotates CCW on screen; screen headings grow clockwise (y-down).
    rot = pygame.transform.rotate(base, -15.0 * sector)
    out = pygame.Surface((c, c), pygame.SRCALPHA)
    out.blit(rot, ((c - rot.get_width()) // 2, (c - rot.get_height()) // 2))
    _ICON_CACHE[key] = out
    return out


def plume(length_px: int, width_px: int, phase01: float) -> pygame.Surface:
    """Animated exhaust plume frame, nozzle at the top, flowing down.

    Layered translucent triangles, white-hot core fading through orange to
    transparent; flicker is driven by phase01 in [0, 1) quantized to 8
    deterministic cached frames (NOT wall time, per 14 VD-P2).
    """
    lp = int(min(max(length_px, 4), 500))
    wp = int(min(max(width_px, 4), 160))
    frame = int((phase01 % 1.0) * _PLUME_FRAMES) % _PLUME_FRAMES
    key = (lp, wp, frame)
    hit = _PLUME_CACHE.get(key)
    if hit is not None:
        return hit

    rng = _rng(f"plume:{lp}:{wp}:{frame}")
    f = frame / _PLUME_FRAMES
    surf = pygame.Surface((wp, lp), pygame.SRCALPHA)
    for lf, wf, col, alpha in ((1.00, 0.50, (255, 118, 40), 60),
                               (0.70, 0.32, (255, 178, 80), 120),
                               (0.40, 0.16, (255, 244, 214), 215)):
        flick = (0.88 + 0.10 * math.sin(math.tau
                                        * (f + float(rng.uniform(0.0, 0.25))))
                 + float(rng.uniform(-0.04, 0.04)))
        ln = max(3, int(lp * lf * flick))
        hw = max(1.0, wp * wf)
        left, right = [], []
        for j in range(8):
            t = j / 7.0
            w_t = hw * (1.0 - t ** 1.4)
            wob = (math.sin(math.tau * (2.2 * t + f)) * hw * 0.12 * t
                   + float(rng.uniform(-0.5, 0.5)))
            yy = min(lp - 1, int(t * ln))
            left.append((wp / 2.0 - w_t + wob, yy))
            right.append((wp / 2.0 + w_t + wob, yy))
        layer = pygame.Surface((wp, lp), pygame.SRCALPHA)
        pygame.draw.polygon(layer, (*col, alpha), left + right[::-1])
        surf.blit(layer, (0, 0))
    _PLUME_CACHE[key] = surf
    return surf


def app_icon() -> pygame.Surface:
    """32x32 taskbar icon: dark disc, cyan orbit, white craft, gold sun."""
    if _APP_ICON:
        return _APP_ICON[0]
    surf = pygame.Surface((32, 32), pygame.SRCALPHA)
    pygame.draw.circle(surf, SPACE_BG, (16, 16), 15)
    pygame.draw.circle(surf, PANEL_EDGE, (16, 16), 15, 1)
    pygame.draw.ellipse(surf, ACCENT, pygame.Rect(3, 9, 26, 14), 1)
    pygame.draw.circle(surf, GOLD, (16, 16), 2)
    pygame.draw.circle(surf, (245, 248, 255), (29, 16), 1)
    _APP_ICON.append(surf)
    return surf
