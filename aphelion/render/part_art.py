"""Drydock part art (MISSION FILM hardware layer): every rocket part drawn
as real, identifiable spaceflight hardware instead of a flat class-coloured
box. Side-view, nose-up / nozzle-down, sized to the part's grid footprint.

House style shared with vehicle_art: engineered shapes, cylinder shading
(lit from upper-left), graphite engines, sooty kerolox vs frosty cryo tanks,
sparing international-orange + gold-MLI accents, dark glass with a catch-light.
Sprites are cached per (catalog_id, cell_px); the drydock scene blits them on
the grid and owns the floor contact shadow.

Dispatch is by catalog_id prefix first (EN-/TK-/HB-/ST-/PW-/UT-/DK-/CG-/AR-/
WS-/RCS-/TH-/SP-/FD-), then class/flags, then a class-tinted machined fallback
so nothing is ever a plain rectangle."""

from __future__ import annotations

import math

import pygame

_CACHE: dict = {}

# --- palette -----------------------------------------------------------
_ALU_LO = (150, 156, 168)
_ALU_HI = (216, 222, 232)
_STEEL_LO = (110, 116, 130)
_STEEL_HI = (176, 184, 198)
_GRAPHITE_LO = (40, 44, 54)
_GRAPHITE_HI = (84, 90, 104)
_SOOT = (26, 26, 30)
_ORANGE = (208, 96, 44)
_GOLD = (190, 158, 86)
_GOLD_HI = (224, 196, 130)
_GLASS = (22, 32, 46)
_GLASS_LIT = (120, 170, 210)
_FRAME = (24, 27, 34)
_LED_AMBER = (212, 150, 60)

# propellant family -> (tank body lo, hi, accent band, frosty?)
_PROP = {
    "kerolox":   ((196, 198, 200), (236, 238, 240), (150, 130, 92), False),
    "methalox":  ((188, 200, 210), (232, 242, 248), (150, 180, 196), True),
    "hydrolox":  ((196, 212, 224), (240, 248, 252), (150, 186, 214), True),
    "hypergol":  ((180, 168, 150), (218, 208, 188), (196, 132, 64), False),
    "xenon":     ((150, 156, 168), (206, 212, 222), (150, 120, 196), False),
    "water":     ((178, 196, 210), (224, 238, 246), (96, 150, 200), False),
    "nitrogen":  ((176, 182, 192), (220, 226, 234), (120, 150, 170), False),
    "generic":   ((170, 176, 186), (216, 222, 230), (130, 140, 156), False),
}


def _prop_family(spec: dict) -> str:
    """Classify a tank/engine propellant into a visual family."""
    src = spec.get("tank", {}).get("mixture") or \
        spec.get("engine", {}).get("propellant") or {}
    keys = {k.lower() for k in src}
    if "xenon" in keys:
        return "xenon"
    if "hydrogen" in keys:
        return "hydrolox"
    if "methane" in keys:
        return "methalox"
    if "rp1" in keys or "kerosene" in keys:
        return "kerolox"
    if "water" in keys:
        return "water"
    if keys & {"mmh", "nto", "hydrazine", "n2o4", "udmh"}:
        return "hypergol"
    if "nitrogen" in keys:
        return "nitrogen"
    return "generic"


# --- shading helpers ---------------------------------------------------
def _lerp(a, b, t):
    return tuple(int(a[c] + (b[c] - a[c]) * t) for c in range(3))


def _vgrad(s, rect, top, bot):
    x, y, w, h = (int(v) for v in rect)
    if w <= 0 or h <= 0:
        return
    col = pygame.Surface((1, h))
    for i in range(h):
        col.set_at((0, i), _lerp(top, bot, i / max(1, h - 1)))
    s.blit(pygame.transform.scale(col, (w, h)), (x, y))


def _cyl(w, h, lo, hi, peak=0.36):
    """A vertical-cylinder shade: bright specular highlight near `peak`
    across the width, falling to `lo` at both edges. Returns a Surface."""
    w, h = max(1, int(w)), max(1, int(h))
    row = pygame.Surface((w, 1))
    for x in range(w):
        f = x / max(1, w - 1)
        k = 1.0 - min(1.0, (abs(f - peak) / 0.62) ** 1.25)
        row.set_at((x, 0), _lerp(lo, hi, k))
    return pygame.transform.scale(row, (w, h))


def _dome(s, cx, cy, rw, rh, lo, hi, top=True):
    """An elliptical tank dome cap, shaded like the cylinder."""
    rw, rh = max(2, int(rw)), max(2, int(rh))
    band = _cyl(rw * 2, rh * 2, lo, hi)
    mask = pygame.Surface((rw * 2, rh * 2), pygame.SRCALPHA)
    pygame.draw.ellipse(mask, (255, 255, 255, 255), (0, 0, rw * 2, rh * 2))
    cap = band.convert_alpha()
    cap.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    rect = cap.get_rect(center=(int(cx), int(cy)))
    if top:
        s.blit(cap, (rect.x, rect.y), (0, 0, rw * 2, rh))
    else:
        s.blit(cap, (rect.x, rect.y + rh), (0, rh, rw * 2, rh))


def _bolts(s, x0, y0, x1, n, col=(60, 64, 74), r=1):
    for i in range(n):
        x = int(x0 + (x1 - x0) * (i + 0.5) / n)
        pygame.draw.circle(s, col, (x, int(y0)), r)


def _rings(s, x, w, ys, col):
    for y in ys:
        pygame.draw.line(s, col, (int(x), int(y)), (int(x + w), int(y)), 1)


# --- cylinder body (tanks, habs, stages) -------------------------------
def _cyl_body(s, w, h, lo, hi, *, dome_f=0.42, frost=False, rings=True):
    """A pressurised cylinder with elliptical domes top & bottom."""
    dome_h = max(2, int(w * dome_f))
    bx, by, bw, bh = 1, dome_h // 2, w - 2, h - dome_h
    s.blit(_cyl(bw, bh, lo, hi), (bx, by))
    _dome(s, w / 2, by, bw / 2, dome_h / 2 + 1, lo, hi, top=True)
    _dome(s, w / 2, by + bh, bw / 2, dome_h / 2 + 1, _lerp(lo, (0, 0, 0), 0.18),
          hi, top=False)
    if rings and bh > 22:
        n = max(2, int(bh / 26))
        _rings(s, bx, bw, [by + bh * (i + 1) / (n + 1) for i in range(n)],
               _lerp(lo, (0, 0, 0), 0.30))
    if frost:                                   # cryo condensation sheen
        fr = pygame.Surface((bw, bh), pygame.SRCALPHA)
        for _ in range(0):
            pass
        for yy in range(0, bh, 3):
            a = int(40 * (yy / max(1, bh)))
            pygame.draw.line(fr, (235, 244, 250, a), (0, yy), (bw, yy))
        s.blit(fr, (bx, by))
    # left-edge core shadow + right rim line for roundness
    pygame.draw.line(s, _lerp(lo, (0, 0, 0), 0.5), (bx, by), (bx, by + bh), 1)
    pygame.draw.line(s, _lerp(hi, (255, 255, 255), 0.2),
                     (int(bx + bw * 0.34), by), (int(bx + bw * 0.34), by + bh), 1)


# --- ENGINES -----------------------------------------------------------
def _bell(s, w, h, *, soot, metal_lo, metal_hi, y0=0.0, y1=1.0,
          throat_f=0.30, exit_f=0.94):
    """A regen-cooled bell nozzle filling the vertical span [y0,y1]·h."""
    ty, ey = h * y0, h * y1
    tw, ew = w * throat_f, w * exit_f
    left, right = [], []
    steps = 14
    for i in range(steps + 1):
        t = i / steps
        y = ty + (ey - ty) * t
        hw = (tw + (ew - tw) * (t ** 1.7)) / 2
        left.append((w / 2 - hw, y))
        right.append((w / 2 + hw, y))
    poly = left + right[::-1]
    pygame.draw.polygon(s, metal_lo, poly)
    # metallic sheen: a narrower inset polygon lighter on the lit side
    inset = [(w / 2 + (x - w / 2) * 0.62, y) for x, y in left] + \
            [(w / 2 + (x - w / 2) * 0.62, y) for x, y in right][::-1]
    pygame.draw.polygon(s, metal_hi, inset)
    # shadowed throat interior
    innr = [(w / 2 + (x - w / 2) * 0.34, y) for x, y in left] + \
           [(w / 2 + (x - w / 2) * 0.34, y) for x, y in right][::-1]
    pygame.draw.polygon(s, soot, innr)
    # regen cooling channels
    for i in range(1, 7):
        f = i / 7
        pts = [(w / 2 + (left[k][0] - w / 2) * (0.34 + 0.6 * f), left[k][1])
               for k in range(len(left))]
        if len(pts) > 1:
            pygame.draw.lines(s, _lerp(metal_lo, (0, 0, 0), 0.25), False, pts, 1)
    # exit lip ring
    pygame.draw.line(s, metal_hi, (w / 2 - ew / 2, ey - 1),
                     (w / 2 + ew / 2, ey - 1), max(1, int(h * 0.02)))


def _eng_chem(s, w, h, spec):
    fam = _prop_family(spec)
    soot = _SOOT if fam == "kerolox" else _lerp(_SOOT, (60, 50, 44), 0.6)
    # powerhead / turbopumps up top
    ph = max(3, int(h * 0.24))
    _vgrad(s, (int(w * 0.18), 0, int(w * 0.64), ph), _GRAPHITE_HI, _GRAPHITE_LO)
    pygame.draw.rect(s, _FRAME, (int(w * 0.18), 0, int(w * 0.64), ph), 1)
    for fx in (0.32, 0.68):
        pygame.draw.circle(s, _GRAPHITE_LO, (int(w * fx), int(ph * 0.55)),
                           max(2, int(w * 0.12)))
        pygame.draw.circle(s, (120, 126, 138), (int(w * fx), int(ph * 0.55)),
                           max(2, int(w * 0.12)), 1)
    # plumbing down the side
    pygame.draw.line(s, (140, 130, 110), (int(w * 0.2), ph),
                     (int(w * 0.3), int(h * 0.5)), 1)
    _bell(s, w, h, soot=soot, metal_lo=_GRAPHITE_LO, metal_hi=(150, 150, 156),
          y0=0.22, y1=0.99)


def _eng_solid(s, w, h, spec):
    # composite casing + nose cap + small nozzle stub
    _cyl_body(s, w, int(h * 0.86), (190, 192, 196), (236, 238, 240),
              dome_f=0.5, rings=True)
    pygame.draw.polygon(s, (170, 172, 178), [
        (w * 0.5, -1), (w * 0.12, h * 0.1), (w * 0.88, h * 0.1)])
    # segment joints (field joints)
    for i in range(1, 4):
        y = int(h * 0.86 * (0.2 + 0.2 * i))
        pygame.draw.line(s, (120, 122, 128), (1, y), (w - 1, y), 1)
    _bell(s, w, h, soot=(40, 34, 30), metal_lo=(150, 150, 156),
          metal_hi=(190, 190, 196), y0=0.84, y1=1.0, throat_f=0.4, exit_f=0.72)


def _eng_electric(s, w, h, spec):
    # housing + annular/grid discharge chamber (unlit in the bay)
    _vgrad(s, (1, 1, w - 2, int(h * 0.6)), _GRAPHITE_HI, _GRAPHITE_LO)
    pygame.draw.rect(s, _FRAME, (1, 1, w - 2, int(h * 0.6)), 1)
    cx, cy = w / 2, h * 0.74
    rr = min(w, h) * 0.30
    pygame.draw.circle(s, (30, 30, 40), (int(cx), int(cy)), int(rr))
    pygame.draw.circle(s, (90, 70, 130), (int(cx), int(cy)), int(rr), 1)
    pygame.draw.circle(s, (60, 50, 90), (int(cx), int(cy)), int(rr * 0.5))
    _GOLD and pygame.draw.line(s, _GOLD, (int(w * 0.2), int(h * 0.2)),
                               (int(w * 0.2), int(h * 0.5)), 1)


def _eng_ntr(s, w, h, spec):
    # reactor pressure vessel + bell, pale (no soot)
    _cyl_body(s, w, int(h * 0.6), _STEEL_LO, _STEEL_HI, dome_f=0.5, rings=True)
    pygame.draw.rect(s, _GOLD, (int(w * 0.1), int(h * 0.5), int(w * 0.8), 2))
    _bell(s, w, h, soot=(44, 46, 52), metal_lo=(120, 124, 132),
          metal_hi=(176, 180, 188), y0=0.56, y1=1.0)


def _eng_rcs(s, w, h, spec):
    # quad thruster cluster on a stub
    pygame.draw.rect(s, _GRAPHITE_LO, (int(w * 0.38), int(h * 0.3),
                                       int(w * 0.24), int(h * 0.5)))
    for ang in (-0.7, 0.7):
        ex = w / 2 + math.sin(ang) * w * 0.34
        pygame.draw.polygon(s, (150, 152, 158), [
            (w / 2, h * 0.34), (ex, h * 0.12),
            (ex + math.cos(ang) * 2, h * 0.24)])
    pygame.draw.circle(s, _LED_AMBER, (int(w / 2), int(h * 0.5)), 1)


# --- TANKS -------------------------------------------------------------
def _tank(s, w, h, spec):
    fam = _prop_family(spec)
    lo, hi, band, frost = _PROP[fam]
    if w <= h * 1.4 and min(w, h) <= 16 and fam == "xenon":
        # COPV sphere for small high-pressure stores
        pygame.draw.circle(s, lo, (w // 2, h // 2), min(w, h) // 2 - 1)
        s.blit(_cyl(w - 2, h - 2, lo, hi), (1, 1),
               special_flags=0) if False else None
        gl = _cyl(min(w, h) - 2, min(w, h) - 2, lo, hi)
        mask = pygame.Surface(gl.get_size(), pygame.SRCALPHA)
        pygame.draw.circle(mask, (255, 255, 255, 255),
                           (gl.get_width() // 2, gl.get_height() // 2),
                           gl.get_width() // 2)
        gl = gl.convert_alpha()
        gl.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        s.blit(gl, ((w - gl.get_width()) // 2, (h - gl.get_height()) // 2))
        pygame.draw.circle(s, band, (w // 2, h // 2), min(w, h) // 2 - 1, 1)
        return
    _cyl_body(s, w, h, lo, hi, frost=frost)
    # propellant identity band near the top dome
    by = max(3, int(w * 0.42 * 0.5)) + 3
    pygame.draw.rect(s, band, (int(w * 0.16), by, int(w * 0.68),
                               max(2, int(h * 0.04))))
    if frost and h > 30:                          # a few frost runs
        for fx in (0.28, 0.55, 0.74):
            pygame.draw.line(s, (236, 244, 250),
                             (int(w * fx), int(h * 0.3)),
                             (int(w * fx), int(h * 0.82)), 1)


# --- CREW / HAB --------------------------------------------------------
def _capsule(s, w, h, spec):
    # gumdrop frustum, windows, hatch, ablative base
    top = [(w * 0.30, h * 0.06), (w * 0.70, h * 0.06),
           (w * 0.94, h * 0.82), (w * 0.06, h * 0.82)]
    pygame.draw.polygon(s, _ALU_LO, top)
    inset = [(w * 0.30 + (x - w / 2) * 0.0 + (w / 2 - x) * -0.0, y)
             for x, y in top]
    # specular: lighter left strip
    pygame.draw.polygon(s, _ALU_HI, [
        (w * 0.34, h * 0.08), (w * 0.5, h * 0.08),
        (w * 0.58, h * 0.8), (w * 0.30, h * 0.8)])
    pygame.draw.polygon(s, _FRAME, top, 1)
    # heat-shield base
    pygame.draw.polygon(s, (54, 46, 44), [
        (w * 0.06, h * 0.82), (w * 0.94, h * 0.82),
        (w * 0.78, h * 0.99), (w * 0.22, h * 0.99)])
    # MLI gold band
    pygame.draw.line(s, _GOLD, (w * 0.1, h * 0.74), (w * 0.9, h * 0.74),
                     max(1, int(h * 0.02)))
    # windows
    for wx in (0.42, 0.6):
        r = pygame.Rect(int(w * wx), int(h * 0.24), max(3, int(w * 0.13)),
                        max(3, int(h * 0.1)))
        pygame.draw.rect(s, _GLASS, r, border_radius=2)
        pygame.draw.line(s, _GLASS_LIT, (r.x + 1, r.y + 1),
                         (r.right - 2, r.y + 1))
    # hatch
    pygame.draw.rect(s, _lerp(_ALU_LO, (0, 0, 0), 0.2),
                     (int(w * 0.34), int(h * 0.42), int(w * 0.2),
                      int(h * 0.26)), 1, border_radius=2)


def _hab(s, w, h, spec, *, glow=(255, 224, 170), portholes=True, mli=True):
    cid = spec.get("catalog_id", "")
    inflatable = "INF" in cid
    lo, hi = (196, 198, 202), (236, 240, 244)
    if inflatable:                                 # bulged fabric segments
        seg = max(2, int(h / max(1, round(h / 26))))
        y = 1
        while y < h - 1:
            sh = min(seg, h - 1 - y)
            s.blit(_cyl(w - 2, sh, (208, 204, 196), (244, 242, 236),
                        peak=0.4), (1, y))
            pygame.draw.line(s, (170, 166, 158), (1, y), (w - 1, y), 1)
            y += sh
        pygame.draw.rect(s, _FRAME, (1, 1, w - 2, h - 2), 1)
    else:
        _cyl_body(s, w, h, lo, hi, rings=True)
    if mli:
        for fy in (0.16, 0.86):
            pygame.draw.line(s, _GOLD, (w * 0.08, h * fy), (w * 0.92, h * fy),
                             max(1, int(h * 0.015)))
    if portholes and h > 16:
        n = max(1, int(h / 34))
        for i in range(n):
            cy = int(h * (0.3 + 0.42 * (i + 0.5) / n))
            pygame.draw.circle(s, _GLASS, (w // 2, cy), max(2, int(w * 0.14)))
            pygame.draw.circle(s, (90, 96, 110), (w // 2, cy),
                               max(2, int(w * 0.14)), 1)
            pygame.draw.circle(s, glow, (w // 2, cy), max(1, int(w * 0.07)))


def _greenhouse(s, w, h, spec):
    _hab(s, w, h, spec, glow=(150, 220, 150))
    # green grow-light glow strip down the middle
    gl = pygame.Surface((max(2, int(w * 0.22)), int(h * 0.6)), pygame.SRCALPHA)
    gl.fill((120, 210, 120, 60))
    s.blit(gl, (int(w * 0.39), int(h * 0.2)))


def _cupola(s, w, h, spec):
    pygame.draw.rect(s, _STEEL_LO, (1, int(h * 0.55), w - 2, int(h * 0.45)))
    # faceted dome window
    cx = w / 2
    for k in range(-2, 3):
        x = cx + k * w * 0.16
        pygame.draw.polygon(s, _GLASS, [
            (x - w * 0.09, h * 0.55), (x + w * 0.09, h * 0.55),
            (cx + (x - cx) * 0.4, h * 0.06)])
    pygame.draw.line(s, _GLASS_LIT, (w * 0.3, h * 0.5), (w * 0.55, h * 0.5))
    pygame.draw.rect(s, _STEEL_HI, (1, int(h * 0.52), w - 2, 2))


def _airlock(s, w, h, spec):
    _cyl_body(s, w, h, _STEEL_LO, _STEEL_HI, rings=False)
    # round hatch + handwheel + caution
    pygame.draw.circle(s, (70, 74, 86), (w // 2, h // 2), int(min(w, h) * 0.3))
    pygame.draw.circle(s, (150, 154, 164), (w // 2, h // 2),
                       int(min(w, h) * 0.3), 2)
    pygame.draw.circle(s, _GOLD, (w // 2, h // 2), int(min(w, h) * 0.12), 2)
    for fy in (0.08, 0.92):
        for i in range(0, w, 8):
            pygame.draw.line(s, _ORANGE, (i, int(h * fy)),
                             (i + 4, int(h * fy)), 2)


# --- STRUCTURE ---------------------------------------------------------
def _fairing(s, w, h, spec):
    # translucent ogive cutaway shell so nested payload shows through
    cx = w / 2
    sh = max(1, int(h * 0.28))                     # shoulder height
    left = [(1, h - 1), (1, sh)]
    right = [(w - 1, h - 1), (w - 1, sh)]
    nose = []
    steps = 10
    for i in range(steps + 1):
        t = i / steps
        ang = math.pi * (1 - t)
        x = cx + math.cos(ang) * (w / 2 - 1)
        y = sh - math.sin(t * math.pi / 2) * sh * 0.95
        nose.append((x, max(0, y)))
    poly = left + nose + right[::-1]
    shell = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.polygon(shell, (200, 206, 216, 60), poly)
    pygame.draw.lines(shell, (150, 156, 168, 220), False,
                      left + nose + right[::-1][:1], 2)
    pygame.draw.line(shell, (150, 156, 168, 220), (w - 1, h - 1), (w - 1, sh), 2)
    pygame.draw.line(shell, (120, 126, 140, 160), (cx, 1), (cx, h - 1), 1)
    s.blit(shell, (0, 0))


def _truss(s, w, h, spec):
    col = (150, 156, 168)
    pygame.draw.line(s, col, (2, 0), (2, h), 2)
    pygame.draw.line(s, col, (w - 3, 0), (w - 3, h), 2)
    seg = max(10, int(w))
    y = 0
    while y < h:
        pygame.draw.line(s, _lerp(col, (0, 0, 0), 0.2), (2, y),
                         (w - 3, y + seg), 1)
        pygame.draw.line(s, _lerp(col, (0, 0, 0), 0.2), (w - 3, y),
                         (2, y + seg), 1)
        pygame.draw.line(s, col, (2, y + seg), (w - 3, y + seg), 1)
        y += seg


def _decoupler(s, w, h, spec):
    _vgrad(s, (1, 1, w - 2, h - 2), (150, 130, 90), (120, 100, 64))
    pygame.draw.rect(s, _FRAME, (1, 1, w - 2, h - 2), 1)
    # separation plane (dashed) + explosive bolts
    midy = h // 2
    for i in range(0, w, 6):
        pygame.draw.line(s, (40, 30, 18), (i, midy), (i + 3, midy), 1)
    _bolts(s, 4, midy, w - 4, max(3, w // 8), col=_ORANGE, r=max(1, h // 8))


def _girder(s, w, h, spec):
    # I-beam / strongback column
    fw = max(2, int(w * 0.26))
    _vgrad(s, (0, 0, fw, h), _STEEL_HI, _STEEL_LO)
    _vgrad(s, (w - fw, 0, fw, h), _STEEL_HI, _STEEL_LO)
    _vgrad(s, (w // 2 - 1, 0, 2, h), _STEEL_HI, _STEEL_LO)
    for y in range(4, h, 12):
        pygame.draw.line(s, (60, 64, 74), (0, y), (fw, y), 1)
        pygame.draw.line(s, (60, 64, 74), (w - fw, y), (w, y), 1)


def _fin(s, w, h, spec):
    pygame.draw.polygon(s, _ALU_LO, [
        (1, 1), (int(w * 0.5), 1), (w - 1, h - 1), (1, h - 1)])
    pygame.draw.polygon(s, _ALU_HI, [
        (1, 1), (int(w * 0.34), 1), (int(w * 0.5), h * 0.5), (1, h * 0.6)])
    pygame.draw.polygon(s, _FRAME, [
        (1, 1), (int(w * 0.5), 1), (w - 1, h - 1), (1, h - 1)], 1)


def _adapter(s, w, h, spec):
    pygame.draw.polygon(s, _ALU_LO, [
        (int(w * 0.16), 0), (int(w * 0.84), 0), (w - 1, h - 1), (1, h - 1)])
    s.blit(_cyl(int(w * 0.68), h, _ALU_LO, _ALU_HI), (int(w * 0.16), 0),
           (0, 0, int(w * 0.68), h))
    pygame.draw.polygon(s, _FRAME, [
        (int(w * 0.16), 0), (int(w * 0.84), 0), (w - 1, h - 1), (1, h - 1)], 1)


# --- POWER / UTILITY / SHIELD -----------------------------------------
def _solar(s, w, h, spec):
    pygame.draw.rect(s, _GOLD, (0, 0, w, h), border_radius=2)
    cells = pygame.Rect(1, 1, w - 2, h - 2)
    pygame.draw.rect(s, (28, 36, 64), cells)
    step = max(3, int(min(w, h) / 4))
    for x in range(cells.x, cells.right, step):
        pygame.draw.line(s, (60, 80, 130), (x, cells.y), (x, cells.bottom), 1)
    for y in range(cells.y, cells.bottom, step):
        pygame.draw.line(s, (60, 80, 130), (cells.x, y), (cells.right, y), 1)
    pygame.draw.rect(s, (90, 120, 190), cells, 1)


def _reactor(s, w, h, spec):
    _cyl_body(s, w, int(h * 0.8), _STEEL_LO, _STEEL_HI, dome_f=0.5)
    # radiator fins at the base
    for i in range(3):
        y = int(h * 0.8) + i * max(2, int(h * 0.06))
        pygame.draw.line(s, (120, 126, 138), (2, y), (w - 2, y), 1)
    pygame.draw.rect(s, _lerp(_ORANGE, (0, 0, 0), 0.3),
                     (int(w * 0.3), int(h * 0.4), int(w * 0.4), 2))


def _box(s, w, h, spec, *, accent=_LED_AMBER):
    _vgrad(s, (1, 1, w - 2, h - 2), _GRAPHITE_HI, _GRAPHITE_LO)
    pygame.draw.rect(s, _FRAME, (1, 1, w - 2, h - 2), 1)
    for y in range(3, h - 2, 4):                   # louvers
        pygame.draw.line(s, (54, 58, 68), (3, y), (w - 3, y), 1)
    pygame.draw.circle(s, accent, (w - 4, 4), 1)


def _dish(s, w, h, spec):
    pygame.draw.line(s, _STEEL_LO, (w // 2, h - 1), (w // 2, int(h * 0.4)), 2)
    pygame.draw.arc(s, (220, 224, 232),
                    (1, 0, w - 2, int(h * 0.8)), math.pi * 0.1, math.pi * 0.9, 2)
    pygame.draw.arc(s, (150, 156, 168),
                    (3, 2, w - 6, int(h * 0.7)), math.pi * 0.1, math.pi * 0.9, 1)
    pygame.draw.circle(s, (90, 96, 110), (w // 2, int(h * 0.3)), max(1, w // 12))


def _radiator(s, w, h, spec):
    pygame.draw.rect(s, (40, 44, 54), (1, 1, w - 2, h - 2))
    for x in range(2, w - 1, max(2, w // 6)):
        pygame.draw.line(s, (140, 146, 158), (x, 1), (x, h - 1), 1)
    pygame.draw.rect(s, _FRAME, (1, 1, w - 2, h - 2), 1)


def _heatshield(s, w, h, spec):
    # wide shallow concave ablator (PICA), char radials
    pygame.draw.polygon(s, (96, 60, 44), [
        (0, 1), (w, 1), (int(w * 0.82), h - 1), (int(w * 0.18), h - 1)])
    pygame.draw.arc(s, (60, 38, 30), (0, -h, w, h * 2),
                    math.pi * 1.15, math.pi * 1.85, 2)
    for fx in (0.3, 0.5, 0.7):
        pygame.draw.line(s, (70, 44, 34), (int(w * fx), 2),
                         (int(w * (0.4 + (fx - 0.5) * 0.4)), h - 2), 1)


def _docking(s, w, h, spec):
    pygame.draw.rect(s, _STEEL_LO, (1, 1, w - 2, h - 2))
    cx, cy = w // 2, h // 2
    pygame.draw.circle(s, (40, 44, 54), (cx, cy), int(min(w, h) * 0.42))
    pygame.draw.circle(s, (170, 176, 188), (cx, cy), int(min(w, h) * 0.42), 1)
    for a in range(0, 360, 90):                    # capture petals
        x = cx + math.cos(math.radians(a)) * min(w, h) * 0.28
        y = cy + math.sin(math.radians(a)) * min(w, h) * 0.28
        pygame.draw.circle(s, (120, 126, 138), (int(x), int(y)), 1)


def _cargo(s, w, h, spec):
    _vgrad(s, (1, 1, w - 2, h - 2), (138, 142, 152), (104, 108, 120))
    pygame.draw.rect(s, _FRAME, (1, 1, w - 2, h - 2), 1)
    for x in range(4, w - 2, max(4, w // 5)):      # corrugation
        pygame.draw.line(s, (84, 88, 100), (x, 2), (x, h - 2), 1)
    pygame.draw.rect(s, _ORANGE, (2, 2, max(3, w // 6), max(3, h // 6)))


def _legs(s, w, h, spec):
    pygame.draw.rect(s, _STEEL_LO, (int(w * 0.4), 0, int(w * 0.2), int(h * 0.4)))
    pygame.draw.line(s, (170, 176, 188), (w // 2, int(h * 0.4)),
                     (int(w * 0.08), h - 1), 2)
    pygame.draw.line(s, (170, 176, 188), (w // 2, int(h * 0.4)),
                     (int(w * 0.92), h - 1), 2)
    pygame.draw.line(s, (120, 126, 138), (int(w * 0.3), int(h * 0.6)),
                     (int(w * 0.08), h - 1), 1)


def _chute(s, w, h, spec):
    _box(s, w, h, spec)
    pygame.draw.arc(s, (210, 214, 222), (1, 1, w - 2, h), math.pi, math.pi * 2, 1)


def _generic(s, w, h, spec):
    cls = spec.get("class", "STRUCT")
    base = {"STRUCT": (130, 134, 144), "ELEC": (120, 124, 134),
            "MECH": (120, 116, 130), "SHIELD": (120, 140, 146),
            "HAB": (170, 174, 182), "TANK": (170, 176, 186),
            "ENGINE": (90, 90, 96)}.get(cls, (130, 134, 144))
    _vgrad(s, (1, 1, w - 2, h - 2), _lerp(base, (255, 255, 255), 0.22), base)
    pygame.draw.rect(s, _FRAME, (1, 1, w - 2, h - 2), 1)
    _bolts(s, 3, 4, w - 3, max(2, w // 8))
    _bolts(s, 3, h - 4, w - 3, max(2, w // 8))


# --- dispatch ----------------------------------------------------------
def _drawer_for(spec: dict):
    cid = spec.get("catalog_id", "")
    cls = spec.get("class", "")
    if spec.get("rcs") or cid.startswith("RCS"):
        return _eng_rcs
    if cls == "ENGINE" or cid.startswith("EN"):
        if spec.get("solid"):
            return _eng_solid
        if cid.startswith(("EN-ION", "EN-HALL", "EN-MPD", "EN-VAS")):
            return _eng_electric
        if cid.startswith("EN-NTR"):
            return _eng_ntr
        return _eng_chem
    if cid.startswith("TK") or cls == "TANK":
        return _tank
    if cid.startswith("HB-CAP") or spec.get("command_source") and \
            spec.get("type") == "crew" and (spec.get("size", [9])[0] <= 3):
        return _capsule
    if cid.startswith("HB-GRN"):
        return _greenhouse
    if cid.startswith("HB-CUP"):
        return _cupola
    if cid.startswith("HB-AIR"):
        return _airlock
    if cid.startswith(("HB", "SP-HAB", "SP-RING")) or cls == "HAB":
        return _hab
    if cid.startswith("ST-FR") or spec.get("fairing_interior"):
        return _fairing
    if cid.startswith(("ST-TR", "SP-ARM")) or spec.get("nodes") == "interior":
        return _truss
    if spec.get("decoupler") or cid.startswith(("ST-DC", "ST-RD")):
        return _decoupler
    if cid.startswith("ST-FIN"):
        return _fin
    if cid.startswith(("ST-IS", "FD", "AR-GON", "CG-CON")):
        return _adapter
    if cid.startswith(("ST-G", "ST-KEEL", "ST-BF", "SP-ARM")):
        return _girder
    if cid.startswith("PW-SA"):
        return _solar
    if cid.startswith(("PW-RTG", "PW-KP", "PW-FSP", "PW-NEP", "PW-FC")):
        return _reactor
    if cid.startswith("TH-RAD"):
        return _radiator
    if cid.startswith("UT-DISH"):
        return _dish
    if cid.startswith(("UT-HS", "AR-SHELL", "WS")):
        return _heatshield
    if cid.startswith("DK"):
        return _docking
    if cid.startswith("CG"):
        return _cargo
    if cid.startswith(("ST-LL",)):
        return _legs
    if cid.startswith(("UT-CHUTE", "AR-CHUTE")):
        return _chute
    if cid.startswith(("PW-BAT", "UT-AV", "UT-PROBE", "UT-CMG", "SP-HUB",
                       "SP-TETHER", "DK-ARM")):
        return _box
    return _generic


def occupied_cells(parts) -> set:
    """Set of (x,y) grid cells filled by placed parts (for ghost validity)."""
    occ = set()
    for p in parts:
        for dx in range(int(p.spec.get("size", [1, 1])[0])):
            for dy in range(int(p.spec.get("size", [1, 1])[1])):
                occ.add((p.x + dx, p.y + dy))
    return occ


# --- the assembly bay backdrop ----------------------------------------
def draw_bay(surf, area, floor_y, rocket_l, rocket_r, top_y):
    """Lit Vehicle Assembly Building: graded wall, floor pad, two service
    gantry towers flanking the stack, soft work-light pools. Drawn behind
    the parts. `area`=(x,y,w,h) build region; rocket_l/r=stack px extents."""
    ax, ay, aw, ah = area
    # back wall: cool steel gradient, darker up top
    _vgrad(surf, (ax, ay, aw, ah), (18, 22, 30), (30, 34, 44))
    # faint structural ribs on the back wall
    for rx in range(ax + 40, ax + aw, 96):
        pygame.draw.line(surf, (24, 28, 38), (rx, ay), (rx, floor_y), 1)
    for ry in range(ay + 40, floor_y, 80):
        pygame.draw.line(surf, (24, 28, 38), (ax, ry), (ax + aw, ry), 1)
    # floor slab
    pygame.draw.rect(surf, (12, 14, 20), (ax, floor_y, aw, ah - (floor_y - ay)))
    _vgrad(surf, (ax, floor_y, aw, 26), (40, 44, 54), (16, 18, 26))
    pygame.draw.line(surf, (70, 76, 88), (ax, floor_y), (ax + aw, floor_y), 1)
    # flame-trench / pad centre line
    cxm = (rocket_l + rocket_r) // 2
    pygame.draw.rect(surf, (20, 22, 30),
                     (cxm - 26, floor_y + 4, 52, 8), border_radius=3)
    # two service gantry towers, just outside the stack, behind it
    g_top = max(ay + 16, top_y - 8)
    for gx, side in ((rocket_l - 30, -1), (rocket_r + 30, 1)):
        gx = max(ax + 8, min(ax + aw - 16, gx))
        _gantry(surf, gx, g_top, floor_y, side)
    # warm work-light pools on the floor (additive, bloom-legal emitter)
    glow = pygame.Surface((aw, 80), pygame.SRCALPHA)
    for lx in (rocket_l - 30, cxm, rocket_r + 30):
        pygame.draw.ellipse(glow, (90, 70, 36, 26),
                            (lx - ax - 70, 4, 140, 60))
    surf.blit(glow, (ax, floor_y - 30), special_flags=pygame.BLEND_RGB_ADD)


def _gantry(surf, x, y_top, y_bot, side):
    """A lattice service tower with access arms, a head crane and amber
    work lights — present but not competing with the stack."""
    w = 17
    col = (62, 66, 78)
    xo = x + side * w
    # two legs + dense cross-bracing
    pygame.draw.line(surf, col, (x, y_top), (x, y_bot), 2)
    pygame.draw.line(surf, col, (xo, y_top), (xo, y_bot), 2)
    step = 22
    y = y_top
    while y < y_bot - step:
        pygame.draw.line(surf, (44, 48, 58), (x, y), (xo, y + step), 1)
        pygame.draw.line(surf, (44, 48, 58), (xo, y), (x, y + step), 1)
        pygame.draw.line(surf, col, (x, y), (xo, y), 1)
        y += step
    # retractable access arms reaching toward the stack
    for ay_ in range(y_top + 26, y_bot - 18, 62):
        pygame.draw.line(surf, (78, 82, 96), (x, ay_),
                         (x - side * 30, ay_), 2)
        pygame.draw.circle(surf, (96, 102, 116), (x - side * 30, ay_), 2)
        pygame.draw.circle(surf, _LED_AMBER, (x - side * 30, ay_), 1)
    # hammerhead crane jib over the top
    jib_y = y_top - 2
    pygame.draw.line(surf, col, (xo, jib_y), (x - side * 44, jib_y), 2)
    pygame.draw.line(surf, (44, 48, 58), (xo, jib_y), (x - side * 22, jib_y - 12), 1)
    hook_x = x - side * 30
    pygame.draw.line(surf, (96, 102, 116), (hook_x, jib_y), (hook_x, jib_y + 14), 1)


def part_sprite(spec: dict, cell_px: int) -> pygame.Surface:
    """Side-view hardware sprite sized to the part footprint at cell_px."""
    cid = spec.get("catalog_id", "?")
    w_c, h_c = spec.get("size", [1, 1])
    key = (cid, int(cell_px))
    got = _CACHE.get(key)
    if got is None:
        w, h = max(4, int(w_c) * cell_px), max(4, int(h_c) * cell_px)
        s = pygame.Surface((w, h), pygame.SRCALPHA)
        try:
            _drawer_for(spec)(s, w, h, spec)
        except Exception:
            _generic(s, w, h, spec)
        _CACHE[key] = got = s
    return got


def clear_cache():
    _CACHE.clear()
