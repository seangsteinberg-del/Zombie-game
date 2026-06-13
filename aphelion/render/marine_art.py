"""THE LIVING SEAS — MISSION FILM underwater renderer (10 §2.7 DIVE).

Documentary deep-sea footage, not an aquarium. Near-black murk; creatures
are SILHOUETTE-FIRST and lit ONLY by the sub's headlight cone, the RTG
glow, or their own bioluminescence — which is the one sanctioned bloom
emitter (ART-DIRECTION §2.3). Light attenuates exponentially with depth
and with distance down the beam; backscatter motes hang in the cone.

Companion to :mod:`aphelion.game.sealife` — it draws the same plain-dict
entities that the ecology sim steps. Pure pygame, no GL. Radial glow
sprites are cached; the silhouettes are cheap per-frame polygons (a
handful per cell) so they can react to the live light field.

Entry point:
  draw_entities(surf, entities, cam, beam_geom, t)
where
  cam       = {"x0", "depth", "ppm", "cx", "cy"}  world->screen
  beam_geom = {"x", "y", "dir", "reach", "half"}  headlight cone (px)
"""

from __future__ import annotations

import math

import pygame

_GLOW_CACHE: dict = {}

# cold water-world key light vs warm Titan-methane key light
_LIT = {"water": (152, 204, 224), "methane": (176, 168, 132)}
_MURK = {"water": (7, 13, 17), "methane": (16, 20, 16)}
# bioluminescence (the allowed bloom source)
_BIO_MAT = (84, 224, 168)          # microbial fluorescence, cyan-green
_BIO_SWARM = (120, 198, 232)       # filter-feeder pale blue
_VENT_HOT = (208, 120, 66)         # hydrothermal mineral glow
_CONTACT_EDGE = (60, 96, 108)      # the thing at the beam edge


# ---- glow sprites (additive radial falloff) ---------------------------------

def _glow(radius: int, color: tuple, soft: float = 1.8) -> pygame.Surface:
    """A cached additive radial glow — the only bloom we allow."""
    radius = max(2, int(radius))
    key = (radius, color, round(soft, 2))
    got = _GLOW_CACHE.get(key)
    if got is not None:
        return got
    d = radius * 2
    s = pygame.Surface((d, d), pygame.SRCALPHA)
    for r in range(radius, 0, -1):
        f = (1.0 - r / radius) ** soft
        a = int(210 * f)
        c = (min(255, color[0]), min(255, color[1]), min(255, color[2]), a)
        pygame.draw.circle(s, c, (radius, radius), r)
    _GLOW_CACHE[key] = s
    return s


def _blit_glow(surf, cx, cy, radius, color, soft=1.8):
    g = _glow(radius, color, soft)
    surf.blit(g, (int(cx - g.get_width() / 2), int(cy - g.get_height() / 2)),
              special_flags=pygame.BLEND_ADD)


# ---- the light field ---------------------------------------------------------

def _depth_murk(depth_m: float) -> float:
    """Exponential extinction of any ambient light with depth (the murk
    deepens to near-black). 1.0 at the surface → ~0 by ~220 m."""
    return math.exp(-max(0.0, depth_m) / 95.0)


def _beam_lit(beam: dict, px: float, py: float) -> float:
    """How strongly the headlight cone lights a screen point [0, 1].
    Inverse-square down the axis, soft cosine across the cone, zero
    behind the sub."""
    if not beam:
        return 0.0
    u = (px - beam["x"]) * beam.get("dir", 1)      # along-beam (forward+)
    reach = max(1.0, beam.get("reach", 1.0))
    if u <= 0.0 or u >= reach:
        return 0.0
    f = u / reach
    half = beam.get("half", 30.0) * (0.16 + 0.84 * f)
    v = abs(py - beam["y"])
    if v >= half:
        return 0.0
    axial = (1.0 - f) ** 1.5
    lateral = math.cos((v / half) * (math.pi * 0.5)) ** 1.2
    return axial * lateral


def _shade(base, lit_col, lit, extra=0.0):
    """Blend the murk-dark silhouette toward the key-light colour by the
    local light factor (+ optional self-illumination)."""
    k = min(1.0, lit + extra)
    return tuple(int(base[c] + (lit_col[c] - base[c]) * k) for c in range(3))


# ---- per-kind silhouettes ----------------------------------------------------

def _spire(surf, sx, sy, h, w, e, lit_fn, murk, lit_col, t, smoker):
    """One craggy mineral/vent spire: a dark tapering silhouette that
    reads against the murk by a faint cold rim, an AO-dark core, and —
    for a hydrothermal vent — a SMALL deep-red ember at the orifice with
    a dark rising smoker plume (no glowing-lamp ball)."""
    base_lit = lit_fn(sx, sy)
    # rock floor: a touch above the murk so the spire reads as a SOLID
    # mass against near-black water (not an invisible same-as-bg fill)
    rock = tuple(min(255, c + 16) for c in murk)
    body = _shade(rock, lit_col, base_lit * 0.55)
    rim_c = _shade(rock, lit_col, 0.22 + base_lit * 0.5)   # cold edge
    sway = 0.05 * math.sin(t * 0.8 + e["phase"])
    seg = 9
    left, right = [], []
    for i in range(seg + 1):
        f = i / seg
        yy = sy - h * f
        half = (w * 0.5) * (1.0 - 0.62 * f) \
            + abs(math.sin(f * 7.0 + e["phase"])) * 1.4 + 1.0
        dx = sway * h * f
        left.append((sx - half + dx, yy))
        right.append((sx + half + dx, yy))
    pygame.draw.polygon(surf, body, left + right[::-1])
    # AO core seam for volume
    pygame.draw.polygon(
        surf, _shade(murk, lit_col, base_lit * 0.3),
        [(p[0] + (q[0] - p[0]) * 0.28, p[1])
         for p, q in zip(left, right)]
        + [(q[0] - (q[0] - p[0]) * 0.28, q[1])
           for p, q in zip(left, right)][::-1])
    pygame.draw.lines(surf, rim_c, False, left, 1)         # windward rim
    if smoker:
        gx = sx + sway * h
        # dark smoker plume FIRST (behind the ember), normal alpha
        for k in range(7):
            pf = (t * 0.30 + k * 0.14 + e["phase"]) % 1.0
            py = sy - h - pf * h
            spread = 2.0 + pf * w * 0.7
            a = int(42 * (1.0 - pf))
            if a <= 0:
                continue
            pl = pygame.Surface((int(spread * 2 + 4), int(spread * 2 + 4)),
                                pygame.SRCALPHA)
            pygame.draw.circle(pl, (52, 44, 40, a),
                               (int(spread + 2), int(spread + 2)),
                               int(spread))
            surf.blit(pl, (gx - spread - 2 + math.sin(pf * 5 + k) * 4,
                           py - spread))
        # small deep-red ember venting at the orifice (not a lamp)
        _blit_glow(surf, gx, sy - h + h * 0.03, max(2.0, w * 0.16),
                   (96, 30, 12), 3.0)


def _draw_chimney(surf, e, sx, sy, ppm, lit_fn, murk, lit_col, t):
    """A vent chimney / evaporite spire, or a vent FIELD (a cluster of
    smaller spires) — abiotic Tier-0 spectacle."""
    h = max(10.0, e["size"] * ppm)
    smoker = e["kind"] in ("vent_chimney", "vent_field")
    if e["kind"] == "vent_field":
        # a low cluster of three spires across a wider base
        for k, off in enumerate((-0.36, 0.0, 0.34)):
            sh = h * (0.55 + 0.18 * (k % 2))
            sw = max(4.0, sh * 0.42)
            _spire(surf, sx + off * h, sy, sh, sw,
                   {"size": e["size"], "phase": e["phase"] + k * 1.7},
                   lit_fn, murk, lit_col, t, smoker)
    else:
        _spire(surf, sx, sy, h, max(5.0, h * 0.42), e,
               lit_fn, murk, lit_col, t, smoker)


def _draw_terrace(surf, e, sx, sy, ppm, lit_fn, murk, lit_col, t):
    """Thermokarst terracing: stepped sediment shelf, a low silhouette."""
    w = max(10.0, e["size"] * ppm)
    base_lit = lit_fn(sx, sy)
    col = _shade(murk, lit_col, base_lit * 0.6)
    steps = 3
    for i in range(steps):
        sw = w * (1.0 - i * 0.22)
        sh = 3.0 + i * 1.5
        rect = (sx - sw / 2, sy - i * 4 - sh, sw, sh + 2)
        pygame.draw.rect(surf, _shade(col, lit_col, 0.05 * i), rect,
                         border_radius=2)


def _draw_cloud(surf, e, sx, sy, ppm, lit_fn, murk, lit_col, t):
    """Chemical-disequilibrium cloud: a faint translucent diffuse haze
    that only shows where the beam grazes it."""
    r = max(6.0, e["size"] * ppm)
    base_lit = lit_fn(sx, sy)
    if base_lit < 0.03 and not e.get("discovered"):
        return
    a = int(38 * base_lit + (22 if e.get("discovered") else 0))
    breath = 1.0 + 0.12 * math.sin(t * 0.5 + e["phase"])
    layer = pygame.Surface((int(r * 2.4), int(r * 2.0)), pygame.SRCALPHA)
    col = _shade(murk, lit_col, 0.4)
    for k in range(3):
        rr = int(r * breath * (0.6 + 0.2 * k))
        pygame.draw.circle(layer, (*col, max(0, a - k * 8)),
                           (int(r * 1.2 + math.sin(e["phase"] + k) * 4),
                            int(r)), rr)
    surf.blit(layer, (sx - layer.get_width() / 2,
                      sy - layer.get_height() / 2),
              special_flags=pygame.BLEND_ADD)


def _draw_mat(surf, e, sx, sy, ppm, lit_fn, murk, lit_col, t):
    """A microbial mat crusting a chimney: a dark lobate patch in white
    light that FLUORESCES cyan-green only when the UV lamp paints it
    (sealife sets e['glow'])."""
    w = max(5.0, e["size"] * ppm)
    base_lit = lit_fn(sx, sy)
    col = _shade(murk, lit_col, base_lit * 0.5)
    lobes = 5
    for i in range(lobes):
        a = e["phase"] + i * (math.tau / lobes)
        lx = sx + math.cos(a) * w * 0.4
        ly = sy + math.sin(a) * w * 0.28
        pygame.draw.circle(surf, col, (int(lx), int(ly)),
                           max(2, int(w * 0.28)))
    if e.get("glow"):
        pulse = 0.7 + 0.3 * math.sin(t * 2.0 + e["phase"])
        for i in range(lobes):
            a = e["phase"] + i * (math.tau / lobes)
            lx = sx + math.cos(a) * w * 0.4
            ly = sy + math.sin(a) * w * 0.28
            _blit_glow(surf, lx, ly, max(3, w * 0.3 * pulse), _BIO_MAT, 2.0)


def _draw_plume(surf, e, sx, sy, ppm, lit_fn, murk, lit_col, t):
    """N2 effervescence: a rising bubble column, brightest in the beam."""
    h = max(10.0, e["size"] * ppm * 4.0)
    for k in range(10):
        pf = (t * 0.5 + k * 0.11 + e["phase"]) % 1.0
        by = sy - pf * h
        bx = sx + math.sin(pf * 7 + k + e["phase"]) * (3 + pf * 5)
        lit = lit_fn(bx, by)
        rad = 1 + (k % 3)
        a = int((28 + 90 * lit) * (1.0 - pf * 0.6))
        if a <= 0:
            continue
        bub = pygame.Surface((rad * 2 + 2, rad * 2 + 2), pygame.SRCALPHA)
        pygame.draw.circle(bub, (*_shade(murk, lit_col, lit), a),
                           (rad + 1, rad + 1), rad)
        surf.blit(bub, (bx - rad, by - rad),
                  special_flags=pygame.BLEND_ADD)


def _draw_drift(surf, e, sx, sy, ppm, lit_fn, murk, lit_col, t):
    """Drifting organics / marine snow: a small clump that only catches
    the eye when the headlight grazes it."""
    lit = lit_fn(sx, sy)
    if lit < 0.04:
        return
    r = max(1.0, e["size"] * ppm * 0.5)
    a = int(150 * lit)
    flick = 0.6 + 0.4 * math.sin(t * 3.0 + e["phase"])
    _blit_glow(surf, sx, sy, max(2, r * 1.6), _shade(murk, lit_col, 1.0),
               2.4)
    sp = pygame.Surface((int(r * 2 + 2), int(r * 2 + 2)), pygame.SRCALPHA)
    pygame.draw.circle(sp, (*lit_col, int(a * flick)),
                       (int(r + 1), int(r + 1)), int(r))
    surf.blit(sp, (sx - r, sy - r))


def _draw_swarm(surf, e, sx, sy, ppm, lit_fn, murk, lit_col, t):
    """A schooling filter-feeder swarm: each member a tiny silhouette
    with a faint self-glow; the school reads as a shimmering cloud that
    flares where the beam crosses it (and scatters from it — the motion
    is in sealife.step)."""
    ppm_v = e.get("_ppm", ppm)
    for m in e["members"]:
        mx = sx + (m["x"] - e["x"]) * ppm_v
        my = sy + (m["z"] - e["z"]) * ppm_v
        lit = lit_fn(mx, my)
        beat = 0.55 + 0.45 * math.sin(m["ph"])
        ang = math.atan2(m["vz"], m["vx"])
        # a small fusiform silhouette oriented along travel
        bl = 2.0 * beat + 2.0
        dx, dy = math.cos(ang) * bl, math.sin(ang) * bl
        col = _shade(murk, lit_col, min(1.0, lit * 1.1))
        pygame.draw.line(surf, col, (mx - dx, my - dy), (mx + dx, my + dy),
                         max(1, int(1.5 * beat + 1)))
        # faint bioluminescent core (the allowed bloom) — a touch
        # brighter in the dark than under the white beam
        glow_r = (1.4 + 0.9 * beat) * (1.0 + 0.5 * (1.0 - lit))
        _blit_glow(surf, mx, my, glow_r, _BIO_SWARM, 2.4)


def _draw_contact(surf, e, sx, sy, ppm, lit_fn, murk, lit_col, t):
    """THE CONTACT: a vast fusiform body holding the ragged edge of the
    cone. Never fully resolved — a translucent looming mass that FADES
    OUT toward its far end, a faint cold dorsal rim, and a slow
    bioluminescent pulse running its flank. The one Tier-3 wtf."""
    w = max(60.0, e["size"] * ppm)
    h = w * 0.40
    seg = 14
    top, bot = [], []
    for i in range(seg + 1):
        f = i / seg
        xx = -w / 2 + w * f
        taper = math.sin(f * math.pi) ** 0.65
        wob = math.sin(f * 5 + t * 0.5 + e["phase"]) * h * 0.05
        top.append((xx, -h * 0.5 * taper + wob))
        bot.append((xx, h * 0.5 * taper + wob))
    pad = 12
    tw, th = int(w + pad * 2), int(h + pad * 2)
    layer = pygame.Surface((tw, th), pygame.SRCALPHA)
    ox, oy = w / 2 + pad, h / 2 + pad
    poly = [(p[0] + ox, p[1] + oy) for p in top] \
        + [(p[0] + ox, p[1] + oy) for p in bot[::-1]]
    # body: a cold steel-dark mass, lifted enough above the murk to read
    # as a presence (not a void), with a brighter dorsal half for volume
    pygame.draw.polygon(layer, (26, 42, 54, 168), poly)
    belly = [(p[0] + ox, max(p[1], 0) + oy) for p in bot]
    pygame.draw.polygon(
        layer, (15, 25, 33, 130),
        [(p[0] + ox, oy) for p in top] + belly[::-1])
    # faint cold dorsal rim
    pygame.draw.lines(layer, (92, 130, 148, 186), False,
                      [(p[0] + ox, p[1] + oy) for p in top], 2)
    # the far end (tail, the side AWAY from the sub) dissolves into murk:
    # a horizontal alpha ramp keyed to which side the sub sits on
    side = e.get("side", -1)
    ramp = pygame.Surface((tw, th), pygame.SRCALPHA)
    for xx in range(tw):
        f = xx / tw
        # the end TOWARD the sub stays solid; the leading end dissolves
        vis = (1.0 - f) if side > 0 else f
        a = int(255 * min(1.0, 0.5 + 0.8 * vis))
        ramp.fill((255, 255, 255, a), (xx, 0, 1, th))
    layer.blit(ramp, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    surf.blit(layer, (sx - ox, sy - oy))
    # a row of dim bioluminescent photophores along the sub-facing flank
    # (the soft pulsing lights are the one thing you actually SEE)
    base_x = sx - side * w * 0.16
    for k in range(3):
        lx = base_x - side * k * w * 0.13
        ly = sy + h * 0.16 + math.sin(t * 0.6 + e["phase"] + k) * h * 0.05
        a = 0.5 + 0.5 * math.sin(t * 1.3 + k * 1.7 + e["phase"])
        _blit_glow(surf, lx, ly, max(3.0, h * 0.11 * (0.7 + 0.5 * a)),
                   (38, 74, 90), 3.0)


_DRAWERS = {
    "vent_chimney": _draw_chimney,
    "mineral_chimney": _draw_chimney,
    "vent_field": _draw_chimney,
    "thermokarst": _draw_terrace,
    "chem_gradient": _draw_cloud,
    "microbial_mat": _draw_mat,
    "n2_plume": _draw_plume,
    "organic_drift": _draw_drift,
    "filter_swarm": _draw_swarm,
    "contact": _draw_contact,
}
# back-to-front paint order (smaller = further back)
_ZORDER = {
    "contact": 0, "vent_field": 1, "thermokarst": 1,
    "vent_chimney": 2, "mineral_chimney": 2, "chem_gradient": 3,
    "microbial_mat": 4, "n2_plume": 5, "organic_drift": 6,
    "filter_swarm": 7,
}


# ---- backscatter (motes hanging in the beam) ---------------------------------

def draw_backscatter(surf, beam_geom, t, n: int = 60) -> None:
    """Suspended motes lit inside the headlight cone — the volumetric
    feel of a real ROV light. Deterministic drift, additive."""
    if not beam_geom:
        return
    bx, by = beam_geom["x"], beam_geom["y"]
    reach = beam_geom.get("reach", 120.0)
    d = beam_geom.get("dir", 1)
    for i in range(n):
        f = ((i * 0.6180339 + t * 0.03) % 1.0)
        u = f * reach
        half = beam_geom.get("half", 30.0) * (0.16 + 0.84 * f)
        v = (math.sin(i * 12.9898 + t * 0.2) * 0.9) * half
        px = bx + d * u
        py = by + v
        lit = _beam_lit(beam_geom, px, py)
        if lit <= 0.02:
            continue
        a = int(70 * lit * (0.5 + 0.5 * math.sin(t * 2 + i)))
        if a <= 0:
            continue
        r = 1 + (i % 2)
        mote = pygame.Surface((r * 2 + 2, r * 2 + 2), pygame.SRCALPHA)
        pygame.draw.circle(mote, (150, 188, 200, a), (r + 1, r + 1), r)
        surf.blit(mote, (px - r, py - r), special_flags=pygame.BLEND_ADD)


# ---- the entry point ---------------------------------------------------------

def draw_entities(surf, entities, cam: dict, beam_geom: dict,
                  t: float) -> None:
    """Paint the ecology back-to-front, lit only by the headlight cone,
    RTG glow and bioluminescence. ``cam`` maps world (x metres, z depth
    metres) to screen; ``beam_geom`` is the headlight cone in px."""
    x0 = cam["x0"]
    depth = cam["depth"]
    ppm = cam["ppm"]
    cx, cy = cam["cx"], cam["cy"]
    murk_k = _depth_murk(depth)
    w_px = surf.get_width()
    h_px = surf.get_height()

    def lit_fn(px, py):
        # headlight cone + a faint RTG ambient pool near the sub
        b = _beam_lit(beam_geom, px, py)
        if beam_geom:
            dr = math.hypot(px - beam_geom["x"], py - beam_geom["y"])
            b += 0.18 * math.exp(-dr / (6.0 * ppm))      # RTG warmth glow
        return min(1.0, b)

    for e in sorted(entities, key=lambda e: _ZORDER.get(e["kind"], 5)):
        sx = cx + (e["x"] - x0) * ppm
        sy = cy + (e["z"] - depth) * ppm
        if e["kind"] != "contact" and (
                sx < -120 or sx > w_px + 120
                or sy < -120 or sy > h_px + 120):
            continue
        ocean = e.get("ocean", "water")
        murk = _MURK.get(ocean, _MURK["water"])
        key = _LIT.get(ocean, _LIT["water"])
        # ambient murk dims the key light with depth
        lit_col = tuple(int(murk[c] + (key[c] - murk[c])
                            * (0.35 + 0.65 * murk_k)) for c in range(3))
        drawer = _DRAWERS.get(e["kind"])
        if drawer is None:
            continue
        if e["kind"] == "filter_swarm":
            e["_ppm"] = ppm
        drawer(surf, e, sx, sy, ppm, lit_fn, murk, lit_col, t)
