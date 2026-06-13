"""Procedural part & vessel sprites (14 §2 palette, §3.2 world vector
layer, §4.2 propellant-family catalog; 12 §5.7 icon grammar).

ART-DIRECTION "MISSION FILM" pass (§1.2 machine layer): hulls are
NASA-white/aluminium with per-column cylindrical shading, axial light
gradient and film grain; panel seams, hoop welds and rivet rows; gold MLI
foil bands on cryo tanks; international-orange interstage rings; engines
are graphite bells with regen-cooling hoops, a gimbal/plumbing head and a
hot-metal mouth; crew parts are white capsules with a charred heatshield,
RCS ports and tiny window emitters. Light always comes from high-left.

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

# MISSION FILM machine-layer materials (ART-DIRECTION §1.2).
_ORANGE = (221, 86, 38)          # international orange
_HULL = (208, 211, 216)          # NASA white, slightly cool
_ALU = (170, 175, 182)           # bare aluminium
_GRAPHITE = (56, 60, 68)
_MLI = (186, 142, 62)            # gold foil, shadow side
_MLI_HI = (244, 206, 118)        # gold foil, lit side

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


def _shade(col: tuple[int, int, int], f: float) -> tuple[int, int, int]:
    return tuple(max(0, min(255, int(c * f))) for c in col)


def _finish(surf: pygame.Surface, rng: np.random.Generator,
            top: float = 1.05, bot: float = 0.86,
            grain: float = 2.2) -> None:
    """ART-DIRECTION §1.2/§3: axial light gradient + subtle film grain on
    every opaque pixel — no surface ships as a flat fill."""
    alpha = pygame.surfarray.array_alpha(surf)
    arr = pygame.surfarray.pixels3d(surf)
    h = arr.shape[1]
    g = np.linspace(top, bot, max(h, 1))[np.newaxis, :, np.newaxis]
    noise = rng.normal(0.0, grain, size=arr.shape[:2])[:, :, np.newaxis]
    out = np.clip(arr.astype(np.float64) * g + noise, 0.0, 255.0)
    mask = (alpha > 0)[:, :, np.newaxis]
    arr[...] = np.where(mask, out, arr).astype(np.uint8)
    del arr


def _contact_band(surf: pygame.Surface, x: int, y: int, w: int, h: int,
                  alpha: int = 100) -> None:
    """Soft fading occlusion band — the contact shadow one part casts on
    the part below it (rule zero of depth, ART-DIRECTION §2.5)."""
    if w <= 0 or h <= 0:
        return
    band = pygame.Surface((w, h), pygame.SRCALPHA)
    for r in range(h):
        a = int(alpha * (1.0 - r / h))
        pygame.draw.line(band, (0, 0, 0, a), (0, r), (w - 1, r))
    surf.blit(band, (x, y))


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


def _is_cryo(mixture: dict[str, float]) -> bool:
    return bool({"Oxygen", "Hydrogen", "Methane"} & set(mixture))


# -- part builders -------------------------------------------------------


def _build_engine(part: dict, part_id: str, ppm: float) -> pygame.Surface:
    eng = part["engine"]
    fam = _engine_family(eng.get("propellant", {}))
    base, hi = _BELL_COLORS[fam]
    d_m, l_m = _engine_dims_m(part)
    W, H = _fit(d_m * ppm, l_m * ppm, 14.0, 18.0, 256.0)
    # supersample x3 for a smooth machined-bell silhouette, then downscale
    S = 3
    w, h = W * S, H * S
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    rng = _rng(part_id)
    cx = w / 2.0

    # family identity folded into a graphite/metal skin (§1.2 materials)
    skin = tuple(int(0.46 * c + 0.54 * n)
                 for c, n in zip(base, (112, 116, 124)))
    skin_hi = tuple(int(0.42 * c + 0.58 * n)
                    for c, n in zip(hi, (206, 212, 222)))
    skin_dk = _shade(skin, 0.40)

    # gimbal mount: graphite beam, ball joint, twin actuator struts
    mw, mh = max(2 * S, int(0.20 * w)), max(S, int(0.07 * h))
    mount = pygame.Rect(int(cx - mw / 2), 0, mw, mh + S)
    pygame.draw.rect(surf, (70, 76, 88), mount)
    pygame.draw.rect(surf, (96, 102, 114),
                     pygame.Rect(mount.left, 0, mount.width,
                                 max(1, mount.height // 3)))
    pygame.draw.rect(surf, (34, 38, 46), mount, max(1, S // 2))

    pw = max(4 * S, int(0.52 * w))
    head = pygame.Rect(int(cx - pw / 2), mh, pw, max(3 * S, int(0.25 * h)))
    for sx in (-1, 1):                # actuator struts to the head shoulders
        pygame.draw.line(surf, (148, 154, 166),
                         (int(cx + sx * mw * 0.45), S),
                         (int(cx + sx * pw * 0.40),
                          head.top + int(0.35 * head.height)), S)
    pygame.draw.circle(surf, (140, 146, 158),
                       (int(cx), head.top + S), max(2, int(0.07 * w)))
    pygame.draw.circle(surf, (50, 54, 64),
                       (int(cx), head.top + S), max(2, int(0.07 * w)), 1)

    # powerhead: top-lit graphite block, turbopump volute, seeded plumbing
    pygame.draw.rect(surf, (54, 58, 68), head)
    pygame.draw.rect(surf, (70, 75, 86),
                     pygame.Rect(head.left, head.top, head.width,
                                 head.height // 2))
    pygame.draw.line(surf, (26, 28, 34), (head.left + 1, head.top),
                     (head.right - 2, head.top), S)   # AO under the mount
    pygame.draw.rect(surf, (30, 34, 42), head, max(1, S // 2))
    tp = (head.left + int(0.30 * head.width),
          head.top + int(0.58 * head.height))
    pygame.draw.circle(surf, (134, 140, 152), tp, max(2, int(0.09 * w)))
    pygame.draw.circle(surf, (58, 62, 72), tp, max(2, int(0.09 * w)), 1)
    for _ in range(2 + int(rng.integers(0, 2))):
        px = head.left + 2 * S + int(rng.integers(
            0, max(1, head.width - 4 * S)))
        pygame.draw.line(surf, (150, 158, 170),
                         (px, head.top + 2 * S), (px, head.bottom - S), S)
        ey = head.top + 2 * S + int(rng.integers(
            0, max(1, head.height - 4 * S)))
        pygame.draw.line(surf, (118, 124, 136), (px, ey),
                         (min(px + 3 * S, head.right - 2 * S), ey), S)
    if fam == "ntr":                  # hazard chevrons over the powerhead
        for k, x in enumerate(range(head.left + S, head.right - S, 4 * S)):
            col = WARN if k % 2 == 0 else (24, 24, 26)
            pygame.draw.line(surf, col, (x, head.bottom - 2 * S),
                             (min(x + 3 * S, head.right - 2 * S),
                              head.top + S), 2 * S)

    # bell: same outer profile as the sizing contract, finely sampled
    y_t, y_e = head.bottom, h - 1
    hw_t, hw_e = max(1.5 * S, 0.13 * w), w / 2.0 - S
    n_p = 24
    prof = [(y_t + (y_e - y_t) * t, hw_t + (hw_e - hw_t) * t ** 0.7)
            for t in (i / (n_p - 1.0) for i in range(n_p))]
    left = [(cx - hw, y) for y, hw in prof]
    right = [(cx + hw, y) for y, hw in prof]
    pygame.draw.polygon(surf, skin, left + right[::-1])

    ov = pygame.Surface((w, h), pygame.SRCALPHA)
    # specular highlight band, sun high-left; broad shade on the right limb
    pygame.draw.polygon(ov, (*skin_hi, 165),
                        [(cx - hw * 0.62, y) for y, hw in prof]
                        + [(cx - hw * 0.24, y) for y, hw in prof][::-1])
    pygame.draw.polygon(ov, (0, 0, 0, 92),
                        [(cx + hw * 0.42, y) for y, hw in prof]
                        + [(cx + hw, y) for y, hw in prof][::-1])
    # powerhead contact shadow falling onto the bell shoulder
    for r in range(max(2, int(0.035 * h))):
        a = int(110 * (1.0 - r / max(2, int(0.035 * h))))
        yy = y_t + r
        hwr = hw_t + (hw_e - hw_t) * ((yy - y_t) / max(1, y_e - y_t)) ** 0.7
        pygame.draw.line(ov, (0, 0, 0, a), (cx - hwr, yy), (cx + hwr, yy))
    # regen-cooling hoops + one bright stiffener ring along the profile
    for tf in (0.16, 0.32, 0.47, 0.62, 0.78, 0.92):
        idx = int(tf * (n_p - 1))
        yy, hwr = prof[idx]
        pygame.draw.line(ov, (0, 0, 0, 52),
                         (cx - hwr + S, yy), (cx + hwr - S, yy))
    yy, hwr = prof[int(0.55 * (n_p - 1))]
    pygame.draw.line(ov, (*skin_hi, 120),
                     (cx - hwr + S, yy + 1), (cx + hwr - S, yy + 1))
    # hot-metal wash low on the bell (radiative-cooled section)
    pygame.draw.polygon(ov, (120, 64, 40, 36),
                        [(cx - hw, y) for y, hw in prof[int(0.72 * n_p):]]
                        + [(cx + hw, y)
                           for y, hw in prof[int(0.72 * n_p):]][::-1])
    surf.blit(ov, (0, 0))

    edge = _shade(skin, 0.34)
    pygame.draw.lines(surf, edge, False, left, S - 1)
    pygame.draw.lines(surf, edge, False, right, S - 1)
    # bright machined lip right at the exit plane
    pygame.draw.line(surf, skin_hi, (cx - hw_e + S, y_e - S),
                     (cx + hw_e - S, y_e - S), max(1, S // 2))

    # throat: dark slot with a faint hot glow seam under the powerhead
    pygame.draw.ellipse(surf, (16, 17, 22),
                        pygame.Rect(int(cx - hw_t), y_t - 1,
                                    max(2, int(2 * hw_t)),
                                    max(2, int(0.04 * h))))
    glow = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.ellipse(glow, (216, 120, 60, 70),
                        pygame.Rect(int(cx - hw_t * 0.7),
                                    y_t + max(1, int(0.01 * h)),
                                    max(2, int(1.4 * hw_t)),
                                    max(2, int(0.025 * h))))
    surf.blit(glow, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)

    # exit mouth: near-black interior, residual hot-metal core, lit lip
    mouth_h = max(2, int(0.05 * h))
    mouth = pygame.Rect(int(cx - hw_e) + 1, h - mouth_h - 1,
                        max(2, int(2 * hw_e) - 2), mouth_h)
    pygame.draw.ellipse(surf, (13, 13, 17), mouth)
    pygame.draw.ellipse(surf, (52, 28, 20), mouth.inflate(
        -int(mouth.width * 0.36), -max(1, int(mouth.height * 0.36))))
    pygame.draw.ellipse(surf, skin_dk, mouth, max(1, S // 2))
    pygame.draw.arc(surf, skin_hi, mouth, math.pi * 0.55, math.pi * 1.45,
                    max(1, S // 2))

    out = pygame.transform.smoothscale(surf, (W, H))
    _finish(out, rng, top=1.05, bot=0.90, grain=2.0)
    return out


def _build_tank(part: dict, part_id: str, ppm: float) -> pygame.Surface:
    mixture = part["tank"]["mixture"]
    d_m, body_m = _tank_dims_m(part)
    W, H = _fit(d_m * ppm, (body_m + 0.36 * d_m) * ppm, 12.0, 18.0, 320.0)
    surf = pygame.Surface((W, H), pygame.SRCALPHA)
    rng = _rng(part_id)
    dome = max(2, int(round(0.18 * W)))
    body_top, body_bot = dome, H - dome
    body_h = max(1, body_bot - body_top)

    # NASA-white cylinder, column by column: sun high-left puts a specular
    # band left of centre, the right limb falls to shadow with a faint
    # bounce rim (rounded-dome capsule silhouette preserved)
    for x in range(W):
        u = (x + 0.5) / W
        bulge = math.sqrt(max(0.0, 1.0 - (2.0 * u - 1.0) ** 2))
        lum = (0.30 + 0.60 * bulge ** 0.85
               + 0.26 * math.exp(-((u - 0.30) / 0.12) ** 2)
               + 0.06 * math.exp(-((u - 0.96) / 0.05) ** 2))
        col = _shade(_HULL, min(1.25, lum))
        dy = int(round(dome * (1.0 - bulge)))
        pygame.draw.line(surf, col, (x, dy), (x, H - 1 - dy))

    # gold MLI foil band on cryo sections, shaded by the same cylinder math
    mli_rect = None
    if _is_cryo(mixture) and body_h >= 10:
        bh = max(3, int(0.16 * body_h))
        by = body_top + int(0.56 * body_h)
        mli_rect = pygame.Rect(0, by, W, bh)
        for x in range(W):
            u = (x + 0.5) / W
            bulge = math.sqrt(max(0.0, 1.0 - (2.0 * u - 1.0) ** 2))
            lum = (0.34 + 0.56 * bulge ** 0.85
                   + 0.30 * math.exp(-((u - 0.30) / 0.12) ** 2))
            gold = tuple(int(a + (b - a) * min(1.0, lum))
                         for a, b in zip(_shade(_MLI, 0.55), _MLI_HI))
            pygame.draw.line(surf, gold, (x, by), (x, by + bh - 1))

    # axial light gradient + film grain before the crisp detail pass
    _finish(surf, rng, top=1.06, bot=0.84, grain=2.4)

    ov = pygame.Surface((W, H), pygame.SRCALPHA)
    # dome separation seams: dark joint + lit lip (recess idiom)
    pygame.draw.line(ov, (0, 0, 0, 70), (1, body_top), (W - 2, body_top))
    pygame.draw.line(ov, (255, 255, 255, 34),
                     (1, body_top + 1), (W - 2, body_top + 1))
    pygame.draw.line(ov, (0, 0, 0, 70), (1, body_bot), (W - 2, body_bot))
    pygame.draw.line(ov, (255, 255, 255, 36),
                     (1, body_bot - 1), (W - 2, body_bot - 1))

    # vertical panel seams with a lit edge (only when girth allows)
    if W >= 16:
        for fu in sorted(rng.uniform(0.22, 0.78,
                                     size=1 + int(W >= 26))):
            sx = int(fu * W)
            pygame.draw.line(ov, (0, 0, 0, 40),
                             (sx, body_top + 1), (sx, body_bot - 1))
            pygame.draw.line(ov, (255, 255, 255, 24),
                             (sx + 1, body_top + 1), (sx + 1, body_bot - 1))

    # hoop welds (seeded placement) with rivet rows
    n_welds = 2 + int(rng.integers(0, 2))
    for f in sorted(rng.uniform(0.16, 0.88, size=n_welds)):
        y = body_top + int(f * body_h)
        if mli_rect and mli_rect.top - 1 <= y <= mli_rect.bottom:
            continue
        pygame.draw.line(ov, (0, 0, 0, 72), (1, y), (W - 2, y))
        pygame.draw.line(ov, (255, 255, 255, 46), (1, y + 1), (W - 2, y + 1))
        if W >= 18:
            for rx in range(3, W - 2, 3):
                ov.set_at((rx, y - 1), (0, 0, 0, 80))

    # MLI quilting + taped edges over the foil band
    if mli_rect:
        pygame.draw.line(ov, (0, 0, 0, 90), (1, mli_rect.top),
                         (W - 2, mli_rect.top))
        pygame.draw.line(ov, (0, 0, 0, 90), (1, mli_rect.bottom - 1),
                         (W - 2, mli_rect.bottom - 1))
        for qx in range(2, W - 1, 3):
            pygame.draw.line(ov, (0, 0, 0, 46), (qx, mli_rect.top + 1),
                             (qx, mli_rect.bottom - 2))
        if mli_rect.height >= 6:
            my = mli_rect.top + mli_rect.height // 2
            pygame.draw.line(ov, (0, 0, 0, 40), (1, my), (W - 2, my))

    # contents marking ring near the top dome (desaturated, engineering
    # decal rather than candy stripe) + dark keylines
    band = tuple(int(0.58 * c + 0.42 * 148) for c in _content_color(mixture))
    bh2 = max(2, int(0.045 * H))
    by2 = body_top + max(2, int(0.07 * body_h))
    pygame.draw.rect(ov, (*band, 235), pygame.Rect(1, by2, W - 2, bh2))
    pygame.draw.line(ov, (0, 0, 0, 90), (1, by2 - 1), (W - 2, by2 - 1))
    pygame.draw.line(ov, (0, 0, 0, 90), (1, by2 + bh2), (W - 2, by2 + bh2))
    surf.blit(ov, (0, 0))

    # stenciled catalog id (graphite paint on the white hull)
    if W >= 20 and H >= 30:
        text = str(part.get("catalog_id", part.get("tier", "T0")))
        label = _font(9).render(text, True, (84, 88, 98))
        if label.get_width() <= W - 6:
            lx = int(W / 2 - label.get_width() / 2 + rng.integers(-1, 2))
            surf.blit(label, (lx, by2 + bh2 + max(2, int(0.06 * body_h))))
    return surf


def _structure_dims(part: dict, ppm: float) -> tuple[int, int]:
    d_m = min(6.0, 1.2 + 0.9 * float(part.get("mass_t", 1.0)) ** (1.0 / 3.0))
    return _fit(d_m * ppm, 2.1 * d_m * ppm, 12.0, 18.0, 256.0)


def _build_fairing(part: dict, part_id: str, ppm: float) -> pygame.Surface:
    W, H = _structure_dims(part, ppm)
    S = 3
    w, h = W * S, H * S
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    rng = _rng(part_id)
    cx, hw_e, shoulder = w / 2.0, w / 2.0 - S, 0.72
    n_p = 25
    prof = [(1.0 + (i / (n_p - 1.0)) * (h - 2.0),
             hw_e * min(1.0, ((i / (n_p - 1.0)) / shoulder) ** 0.62))
            for i in range(n_p)]
    left = [(cx - hw, y) for y, hw in prof]
    right = [(cx + hw, y) for y, hw in prof]
    pygame.draw.polygon(surf, (218, 221, 226), left + right[::-1])

    ov = pygame.Surface((w, h), pygame.SRCALPHA)
    # sun high-left: specular band + shaded right limb
    pygame.draw.polygon(ov, (255, 255, 255, 85),
                        [(cx - hw * 0.55, y) for y, hw in prof]
                        + [(cx - hw * 0.18, y) for y, hw in prof][::-1])
    pygame.draw.polygon(ov, (0, 0, 0, 60),
                        [(cx + hw * 0.42, y) for y, hw in prof]
                        + [(cx + hw, y) for y, hw in prof][::-1])
    # graphite nose cap on the ogive tip
    pygame.draw.polygon(ov, (84, 90, 100, 235),
                        [(cx - hw, y) for y, hw in prof[:4]]
                        + [(cx + hw, y) for y, hw in prof[:4]][::-1])
    # vertical jettison seam with lit edge
    pygame.draw.line(ov, (0, 0, 0, 56), (cx, prof[2][0]), (cx, h - 2), S // 2)
    pygame.draw.line(ov, (255, 255, 255, 30),
                     (cx + S // 2 + 1, prof[3][0]), (cx + S // 2 + 1, h - 2))
    # ring frames + rivet rows at seeded stations
    for ff in sorted(rng.uniform(0.34, 0.72, size=2)):
        idx = int(ff * (n_p - 1))
        yy, hwr = prof[idx]
        pygame.draw.line(ov, (0, 0, 0, 60),
                         (cx - hwr + S, yy), (cx + hwr - S, yy), S // 2)
        pygame.draw.line(ov, (255, 255, 255, 36),
                         (cx - hwr + S, yy + S // 2 + 1),
                         (cx + hwr - S, yy + S // 2 + 1))
        for rx in range(int(cx - hwr) + 2 * S, int(cx + hwr) - S, 3 * S):
            pygame.draw.circle(ov, (0, 0, 0, 80), (rx, int(yy) - S), S // 2)
    # international-orange band near the base (separation marking)
    sy = int(0.80 * h) + int(rng.integers(-1, 2)) * S
    bh = max(2 * S, int(0.06 * h))
    band_rect = pygame.Rect(0, sy, w, bh)
    for yy in range(band_rect.top, band_rect.bottom):
        t = (yy - 1.0) / (h - 2.0)
        hwr = hw_e * min(1.0, (t / shoulder) ** 0.62)
        pygame.draw.line(ov, (*_ORANGE, 240), (cx - hwr + 1, yy),
                         (cx + hwr - 1, yy))
    pygame.draw.line(ov, (0, 0, 0, 90), (S, sy - 1), (w - S, sy - 1))
    pygame.draw.line(ov, (0, 0, 0, 90), (S, sy + bh), (w - S, sy + bh))
    surf.blit(ov, (0, 0))

    sil = (140, 146, 158)
    pygame.draw.lines(surf, sil, False, left, max(1, S // 2))
    pygame.draw.lines(surf, sil, False, right, max(1, S // 2))

    out = pygame.transform.smoothscale(surf, (W, H))
    _finish(out, rng, top=1.05, bot=0.88, grain=2.0)
    return out


def _build_capsule(part: dict, part_id: str, ppm: float) -> pygame.Surface:
    """Crew capsule: white cone, charred heatshield band, RCS ports, tiny
    window emitters, orange hatch ring (ART-DIRECTION §1.2)."""
    W, H = _structure_dims(part, ppm)
    S = 3
    w, h = W * S, H * S
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    rng = _rng(part_id)
    cx = w / 2.0

    ring_h = max(2 * S, int(0.09 * h))
    shield_h = max(2 * S, int(0.09 * h))
    nose_hw = 0.24 * w
    base_hw = w / 2.0 - S
    cone_top, cone_bot = ring_h, h - shield_h

    # docking ring drum (graphite) with a lit top face
    dr = pygame.Rect(int(cx - nose_hw * 0.82), 0,
                     int(nose_hw * 1.64), ring_h)
    pygame.draw.rect(surf, (86, 92, 102), dr)
    pygame.draw.rect(surf, (122, 128, 140),
                     pygame.Rect(dr.left, 0, dr.width, max(1, ring_h // 3)))
    pygame.draw.rect(surf, (38, 42, 50), dr, max(1, S // 2))

    # white pressure cone
    cone = [(cx - nose_hw, cone_top), (cx + nose_hw, cone_top),
            (cx + base_hw, cone_bot), (cx - base_hw, cone_bot)]
    pygame.draw.polygon(surf, (215, 218, 223), cone)
    ov = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.polygon(ov, (255, 255, 255, 85),
                        [(cx - nose_hw * 0.55, cone_top),
                         (cx - nose_hw * 0.10, cone_top),
                         (cx - base_hw * 0.10, cone_bot),
                         (cx - base_hw * 0.55, cone_bot)])
    pygame.draw.polygon(ov, (0, 0, 0, 60),
                        [(cx + nose_hw * 0.45, cone_top),
                         (cx + nose_hw, cone_top),
                         (cx + base_hw, cone_bot),
                         (cx + base_hw * 0.45, cone_bot)])
    # docking-ring contact shadow on the cone shoulder
    for r in range(max(2, int(0.03 * h))):
        a = int(110 * (1.0 - r / max(2, int(0.03 * h))))
        t = r / max(1.0, cone_bot - cone_top)
        hwr = nose_hw + (base_hw - nose_hw) * t
        pygame.draw.line(ov, (0, 0, 0, a),
                         (cx - hwr, cone_top + r), (cx + hwr, cone_top + r))
    # panel seam ring across the cone
    my = cone_top + int(0.52 * (cone_bot - cone_top))
    tm = (my - cone_top) / max(1.0, cone_bot - cone_top)
    hwm = nose_hw + (base_hw - nose_hw) * tm
    pygame.draw.line(ov, (0, 0, 0, 56), (cx - hwm + S, my),
                     (cx + hwm - S, my))
    pygame.draw.line(ov, (255, 255, 255, 36), (cx - hwm + S, my + 1),
                     (cx + hwm - S, my + 1))
    surf.blit(ov, (0, 0))

    # windows: two small offset panes, dark glass in graphite frames with a
    # faint warm cabin glint (emitters) — asymmetric so the cone never
    # reads as a face
    wr = max(2, int(0.026 * w))
    for wx_f, wy_f in ((-0.145, 0.22), (-0.01, 0.27)):
        wx = int(cx + wx_f * w)
        wy = cone_top + int(wy_f * (cone_bot - cone_top))
        frame = pygame.Rect(wx - wr - 1, wy - wr - 1, 2 * wr + 2, 2 * wr + 2)
        pygame.draw.rect(surf, (120, 126, 138), frame)        # raised sill
        pygame.draw.rect(surf, (54, 58, 68), frame, 1)
        pygame.draw.rect(surf, (20, 25, 34), frame.inflate(-2, -2))
        surf.set_at((frame.left + 2, frame.top + 2), (226, 206, 162))
    # side hatch: international-orange outline, recessed, offset right
    hw2, hh2 = int(0.13 * w), int(0.16 * (cone_bot - cone_top))
    hatch = pygame.Rect(int(cx + 0.04 * w),
                        cone_top + int(0.42 * (cone_bot - cone_top)),
                        hw2, hh2)
    hov = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.rect(hov, (0, 0, 0, 50), hatch)
    pygame.draw.rect(hov, (*_ORANGE, 235), hatch, max(1, S // 2))
    surf.blit(hov, (0, 0))
    # RCS port pairs with soot streaks, low on the cone
    ry = cone_bot - int(0.14 * (cone_bot - cone_top))
    tr = (ry - cone_top) / max(1.0, cone_bot - cone_top)
    hwr2 = nose_hw + (base_hw - nose_hw) * tr
    rov = pygame.Surface((w, h), pygame.SRCALPHA)
    for sx in (-1, 1):
        rx = int(cx + sx * (hwr2 - 2.5 * S))
        for k in range(2):
            pygame.draw.circle(rov, (22, 22, 26),
                               (rx, ry - k * 2 * S), max(1, S // 2) + 1)
        pygame.draw.polygon(rov, (40, 36, 34, 70),
                            [(rx - S, ry - 5 * S), (rx + S, ry - 5 * S),
                             (rx, ry)])
    surf.blit(rov, (0, 0))

    # heatshield: charred ablator, lit separation lip above it
    pygame.draw.polygon(surf, (66, 52, 44),
                        [(cx - base_hw, cone_bot), (cx + base_hw, cone_bot),
                         (cx + base_hw * 0.88, h - 1),
                         (cx - base_hw * 0.88, h - 1)])
    pygame.draw.polygon(surf, (40, 31, 26),
                        [(cx - base_hw * 0.96, cone_bot + shield_h * 0.45),
                         (cx + base_hw * 0.96, cone_bot + shield_h * 0.45),
                         (cx + base_hw * 0.88, h - 1),
                         (cx - base_hw * 0.88, h - 1)])
    pygame.draw.line(surf, (236, 238, 242),
                     (cx - base_hw + S, cone_bot - 1),
                     (cx + base_hw - S, cone_bot - 1))
    pygame.draw.line(surf, (24, 20, 18),
                     (cx - base_hw + S, cone_bot),
                     (cx + base_hw - S, cone_bot))

    sil = (130, 136, 148)
    pygame.draw.lines(surf, sil, False,
                      [(cx - nose_hw, cone_top), (cx - base_hw, cone_bot)],
                      max(1, S // 2))
    pygame.draw.lines(surf, sil, False,
                      [(cx + nose_hw, cone_top), (cx + base_hw, cone_bot)],
                      max(1, S // 2))

    out = pygame.transform.smoothscale(surf, (W, H))
    _finish(out, rng, top=1.05, bot=0.90, grain=2.0)
    return out


# -- public API ----------------------------------------------------------


def part_sprite(part: dict, part_id: str,
                px_per_m: float = 4.0) -> pygame.Surface:
    """Side-view sprite for one catalog part, sized from its real data.

    Engines render nozzle-down (gimbal mount at the top), tanks as shaded
    NASA-white capsules with welds/panel seams and an MLI band on cryo
    sections, crew parts as capsules with a heatshield, everything else
    as a white fairing cone with an orange base band.
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
    elif kind == "crew":
        surf = _build_capsule(part, part_id, px_per_m)
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
    """4 fins in side view: 2 outer silhouettes + 2 foreshortened center.
    Graphite skins with a lit leading edge and a root contact shadow."""
    fin_h = max(8, int(0.45 * max(8, bot - top)))
    hw = max(2, hull_w // 2)
    for sx in (-1, 1):                # projected front/back pair, darker
        xi = cx + sx * max(1, hw // 4)
        pygame.draw.polygon(surf, (40, 44, 52),
                            [(xi, bot - int(fin_h * 0.7)), (xi, bot),
                             (xi + sx * max(2, int(fin_w * 0.4)), bot)])
    ao = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
    for sx in (-1, 1):                # outer silhouette pair
        x0 = cx + sx * (hw - 1)
        pts = [(x0, bot - fin_h), (x0, bot), (x0 + sx * fin_w, bot)]
        pygame.draw.polygon(surf, (64, 70, 80), pts)
        # darker lower half = the fin shading agrees with top-light
        pygame.draw.polygon(surf, (50, 55, 64),
                            [(x0, bot - fin_h // 3), (x0, bot),
                             (x0 + sx * fin_w, bot)])
        # lit leading edge + root contact shadow on the hull
        pygame.draw.line(surf, (148, 154, 166), pts[0],
                         (x0 + sx * fin_w, bot))
        pygame.draw.line(ao, (0, 0, 0, 80), (x0 - sx, bot - fin_h + 1),
                         (x0 - sx, bot - 1))
    surf.blit(ao, (0, 0))


def vessel_sprite(db, stack: list[list[str]],
                  px_per_m: float = 3.0) -> pygame.Surface:
    """The assembled rocket, bottom stage at the bottom of the image.

    stack is the builder's bottom-first stage list of part ids; db.parts[pid]
    yields the part dict. Per stage: payload/structures on top, tanks below
    them, engines clustered side by side underneath; an international-orange
    interstage ring joins stages; the bottom stage grows 4 fins when it
    clusters 2+ engines. Stage bases cast contact shadows on their engine
    clusters; the upper hull takes a stencil name + flag decal when girth
    allows. The result is auto-scaled to fit within ~440 px height.
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

    name_zone: tuple[int, int, int] | None = None
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
        if i == len(stages) - 1 and tank:
            name_zone = (tank_top, y, dims[i][2])
        if i == 0 and fins:
            _draw_fins(surf, cx, dims[0][2], tank_top, y, fin_w)
        ew = sum(s.get_width() for s in eng) + gap * max(0, len(eng) - 1)
        x = cx - ew // 2
        eng_top = y
        for spr in eng:                # engines clustered side by side
            surf.blit(spr, (x, y))
            x += spr.get_width() + gap
        if eng and dims[i][3] >= 10:   # stage base shades its engine bay
            _contact_band(surf, cx - ew // 2, eng_top, ew,
                          max(2, int(0.12 * dims[i][3])), alpha=110)
        y += dims[i][3]
        if i > 0:                      # international-orange interstage
            rw = max(8, int(0.85 * min(dims[i][2] or dims[i][0],
                                       dims[i - 1][2] or dims[i - 1][0])))
            ring = pygame.Rect(cx - rw // 2, y, rw, ring_h)
            pygame.draw.rect(surf, _shade(_ORANGE, 0.92), ring)
            pygame.draw.line(surf, _shade(_ORANGE, 1.25),
                             (ring.left + 1, ring.top + 1),
                             (ring.right - 2, ring.top + 1))
            for tx in range(ring.left + 2, ring.right - 1, 3):
                pygame.draw.line(surf, _shade(_ORANGE, 0.62),
                                 (tx, ring.top + 2), (tx, ring.bottom - 2))
            pygame.draw.line(surf, (26, 24, 26),
                             (ring.left, ring.top),
                             (ring.right - 1, ring.top))
            pygame.draw.line(surf, (26, 24, 26),
                             (ring.left, ring.bottom - 1),
                             (ring.right - 1, ring.bottom - 1))
            y += ring_h

    # stencil vessel name + flag decal idiom on the upper hull (§1.2)
    if name_zone is not None:
        t0, t1, hull_w = name_zone
        zone_h = t1 - t0
        if hull_w >= 16 and zone_h >= 44:
            lab = _font(8).render("APHELION", True, (86, 90, 100))
            lab = pygame.transform.rotate(lab, -90)
            if (lab.get_height() <= zone_h - 10
                    and lab.get_width() <= hull_w - 6):
                surf.blit(lab, (cx - lab.get_width() // 2
                                - max(1, hull_w // 6),
                                t0 + (zone_h - lab.get_height()) // 2))
            if hull_w >= 22:
                fx = cx + max(2, hull_w // 6)
                fy = t0 + max(4, zone_h // 5)
                pygame.draw.rect(surf, (230, 232, 236), (fx, fy, 5, 2))
                pygame.draw.rect(surf, _ORANGE, (fx, fy + 2, 5, 2))
                pygame.draw.rect(surf, (66, 72, 84), (fx, fy + 4, 5, 2))
                pygame.draw.rect(surf, (32, 34, 40),
                                 pygame.Rect(fx - 1, fy - 1, 7, 8), 1)

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
    for top in (ccy - hw - phh, ccy + hw):     # solar panel pair: dark glass
        rect = pygame.Rect(int(ccx - 0.12 * length - pw / 2), int(top),
                           pw, phh)
        pygame.draw.rect(base, (24, 38, 56), rect)
        pygame.draw.rect(base, (92, 138, 164), rect, 1)
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
    pygame.draw.polygon(base, (206, 212, 220), hull)
    pygame.draw.lines(base, (108, 124, 140), True, hull)
    pygame.draw.polygon(base, (240, 244, 250),
                        [(nose_x, ccy), (ccx + 0.3 * length, ccy - 0.55 * hw),
                         (ccx + 0.3 * length, ccy + 0.55 * hw)])
    # graphite engine nub at the tail
    pygame.draw.rect(base, (62, 68, 78),
                     pygame.Rect(int(tail_x - 0.08 * length),
                                 int(ccy - 0.5 * hw),
                                 max(1, int(0.08 * length)), max(1, int(hw))))

    # pygame rotates CCW on screen; screen headings grow clockwise (y-down).
    rot = pygame.transform.rotate(base, -15.0 * sector)
    out = pygame.Surface((c, c), pygame.SRCALPHA)
    out.blit(rot, ((c - rot.get_width()) // 2, (c - rot.get_height()) // 2))
    _ICON_CACHE[key] = out
    return out


def plume(length_px: int, width_px: int, phase01: float) -> pygame.Surface:
    """Animated exhaust plume frame, nozzle at the top, flowing down.

    Layered translucent sheath/mid/core, white-hot core fading through
    orange to transparent, Prandtl-Pack shock diamonds down the core and a
    bright exit-plane flash (the plume is THE bloom hero, ART-DIRECTION
    §5); flicker is driven by phase01 in [0, 1) quantized to 8
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
    core_len = lp
    for lf, wf, col, alpha in ((1.00, 0.50, (255, 146, 64), 70),
                               (0.74, 0.34, (255, 202, 116), 150),
                               (0.44, 0.17, (255, 248, 228), 235)):
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
        core_len = ln

    # soften the layer banding into a gaseous falloff (half-res bounce)
    surf = pygame.transform.smoothscale(
        pygame.transform.smoothscale(surf, (max(2, wp // 2),
                                            max(2, lp // 2))), (wp, lp))

    hot = pygame.Surface((wp, lp), pygame.SRCALPHA)
    # shock diamonds spaced down the core, dimming with distance
    n_d = max(1, int(core_len / max(5.0, 1.45 * wp)))
    for k in range(min(n_d, 6)):
        t = (k + 0.55) / (n_d + 0.55)
        yy = int(t * core_len)
        bw = max(1.0, wp * 0.15 * (1.0 - 0.6 * t))
        bh = max(2, int(bw * 2.4))
        a = int(190 * (1.0 - 0.6 * t)
                * (0.86 + 0.14 * math.sin(math.tau * (f + 0.37 * k))))
        pygame.draw.ellipse(hot, (255, 246, 222, max(0, a)),
                            pygame.Rect(int(wp / 2.0 - bw),
                                        max(0, yy - bh // 2),
                                        max(2, int(2 * bw)), bh))
    # exit-plane flash right at the nozzle lip
    pygame.draw.ellipse(hot, (255, 252, 238, 235),
                        pygame.Rect(int(wp * 0.30), 0,
                                    max(2, int(wp * 0.40)),
                                    max(2, int(0.05 * lp))))
    surf.blit(hot, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
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
