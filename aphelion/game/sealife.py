"""THE LIVING SEAS — the underwater life + discovery layer for the DIVE
scene (submarines under Titan's methane seas and the water oceans of
Europa / Enceladus).

This is a HARD-REALISM astrobiology ladder, not an aquarium. Titan seas
are liquid methane at 94 K (no swimming animals — only abiotic spectacle
and ambiguous prebiotic chemistry); Europa / Enceladus host a subsurface
WATER ocean where, very rarely and very deep, something motile lives near
the hydrothermal vents. The ladder escalates the "wtf":

  Tier 0  ambient (abiotic but gorgeous): drifting organics / methane
          snow, N2 effervescence plumes, thermokarst terraces, mineral
          chimneys, and (water) hydrothermal vent fields with shimmering
          thermal distortion.
  Tier 1  biosignature: methanogenic-disequilibrium chemical gradients
          the science bench flags, and microbial mats on vent chimneys
          that fluoresce only under the UV lamp.
  Tier 2  motile life (Europa / Enceladus, deep, rare): filter-feeder
          swarms that school (boids), drift with the current, scatter
          from the headlights, and creep toward RTG warmth in the dark.
  Tier 3  THE CONTACT (once per campaign): a large sonar return that
          paces the sub at the ragged edge of headlight range and is
          never fully seen. Massive science + a FIRST Chronicle entry.

Doctrine (11 §4.11, DECISIONS F34): ambiguous organics ONLY — the
biology question is never answered; every payout is "chemistry / sonar",
never "aliens". The orchestrator wires the science payouts into
sim.research and the Tier-3 first into game.alerts.Chronicle.

DETERMINISM (13 §1.1): every spawn count, position and behaviour seed is
`zlib.crc32` of a stable key (site_id, cell index, kind) — never the
non-deterministic builtin, NO wall clock. Entities are plain
save-friendly dicts; the behaviours are pure update functions stepping
them in place.

API (spawn / update / draw separation):
  populate(body, site_id, depth_m, x_m, floor_m=None) -> entities (cell)
  maybe_contact(body, site_id, sub_depth, sub_x, face, seed, seen) -> ent
  step(entities, dt, sub_x, sub_depth, lights_on, rtg_we, uv_on=False)
        -> events  [('sonar_contact', cls, eid),
                    ('discovery', tier, sci, dsc_id, eid)]
The renderer (render.marine_art) consumes the same plain-dict entities.
"""

from __future__ import annotations

import math
import zlib

# ---- world facts -------------------------------------------------------------

OCEAN_BY_BODY: dict[str, str] = {
    "core:titan": "methane",        # 94 K liquid CH4/C2H6 — no animals
    "core:europa": "water",         # subsurface water ocean — vents
    "core:enceladus": "water",      # south-polar plume ocean — vents
}
# the staged-organics discovery each ocean feeds (11 §5 dsc table)
DSC_BY_BODY: dict[str, str] = {
    "core:titan": "dsc14",          # Titan Sea Floor Survey (arc II)
    "core:europa": "dsc11",         # Europa Ocean Water (arc I)
    "core:enceladus": "dsc12",      # Enceladus Plume Sampling
}

# science payout by tier (orchestrator -> research.earn_science). Modest
# vs the dsc tranches (11 §5) — these are the in-dive "you saw it" award.
SCI_BY_TIER: dict[int, float] = {0: 0.0, 1: 60.0, 2: 220.0, 3: 1_500.0}

CELL_W_M = 80.0                     # one ecology cell along the section
SONAR_RANGE_M = 130.0               # acoustic return radius (sonar blip)
ID_RANGE_M = 26.0                   # headlight / UV visual-ID radius
SENSOR_RANGE_M = 34.0               # science-bench chemistry sniff radius
UV_LAMP_RANGE_M = 30.0              # UV fluorescence excitation radius

# Tier-3 contact (once per campaign)
CONTACT_MIN_DEPTH_M = 180.0         # only the deep dark, water oceans
CONTACT_STANDOFF_M = 34.0           # it holds the ragged beam edge
CONTACT_REVEAL_DWELL_S = 14.0       # sonar dwell before the FIRST fires
CONTACT_SPAWN_P = 0.55             # per deep cell, gated by the seed


def ocean_of(body: str) -> str | None:
    """The ocean phase for a body id, or None if it has no sea."""
    return OCEAN_BY_BODY.get(body)


def depth_band(depth_m: float) -> str:
    """Three bands gate the encounter tables: the photic-ish shallows,
    the mid water, and the deep dark where life and THE CONTACT live."""
    if depth_m < 60.0:
        return "shallow"
    if depth_m < 150.0:
        return "mid"
    return "deep"


# ---- deterministic rng (zlib.crc32 of stable keys only) ----------------------

def _crc(*parts) -> int:
    return zlib.crc32("|".join(str(p) for p in parts).encode())


def _u01(*parts) -> float:
    """Deterministic float in [0, 1)."""
    return (_crc(*parts) & 0xFFFFFF) / float(0x1000000)


def _between(lo: float, hi: float, *parts) -> float:
    return lo + (hi - lo) * _u01(*parts)


def cell_of(x_m: float) -> int:
    """The ecology-cell index containing a world x (metres)."""
    return int(math.floor(x_m / CELL_W_M))


# ---- the encounter tables (per ocean, per depth band) ------------------------
# Each spec: kind, tier, sonar class (or None), detect mode, sci tier,
# count range (min,max inclusive), spawn probability. detect modes:
#   "visual"  needs headlights + within ID_RANGE
#   "uv"      needs UV lamp + within UV_LAMP_RANGE (fluorescence)
#   "sensor"  science bench, within SENSOR_RANGE (no light needed)
#   None      ambient spectacle, never "discovered"
_Spec = dict

ENCOUNTER: dict[str, dict[str, list[_Spec]]] = {
    "methane": {
        "shallow": [
            {"kind": "organic_drift", "tier": 0, "sonar": None,
             "detect": None, "n": (3, 6), "p": 1.0},
            {"kind": "n2_plume", "tier": 0, "sonar": "diffuse",
             "detect": "visual", "n": (0, 1), "p": 0.45},
        ],
        "mid": [
            {"kind": "organic_drift", "tier": 0, "sonar": None,
             "detect": None, "n": (3, 6), "p": 1.0},
            {"kind": "n2_plume", "tier": 0, "sonar": "diffuse",
             "detect": "visual", "n": (0, 1), "p": 0.6},
            {"kind": "chem_gradient", "tier": 1, "sonar": "diffuse",
             "detect": "sensor", "n": (0, 1), "p": 0.35},
        ],
        "deep": [
            {"kind": "organic_drift", "tier": 0, "sonar": None,
             "detect": None, "n": (2, 5), "p": 1.0},
            {"kind": "mineral_chimney", "tier": 0, "sonar": "point",
             "detect": "visual", "n": (0, 2), "p": 0.55},
            {"kind": "thermokarst", "tier": 0, "sonar": "point",
             "detect": "visual", "n": (0, 1), "p": 0.4},
            {"kind": "chem_gradient", "tier": 1, "sonar": "diffuse",
             "detect": "sensor", "n": (0, 1), "p": 0.4},
            {"kind": "microbial_mat", "tier": 1, "sonar": None,
             "detect": "uv", "n": (0, 1), "p": 0.25},
        ],
    },
    "water": {
        "shallow": [
            {"kind": "organic_drift", "tier": 0, "sonar": None,
             "detect": None, "n": (3, 6), "p": 1.0},
        ],
        "mid": [
            {"kind": "organic_drift", "tier": 0, "sonar": None,
             "detect": None, "n": (3, 6), "p": 1.0},
            {"kind": "chem_gradient", "tier": 1, "sonar": "diffuse",
             "detect": "sensor", "n": (0, 1), "p": 0.35},
        ],
        "deep": [
            {"kind": "organic_drift", "tier": 0, "sonar": None,
             "detect": None, "n": (2, 5), "p": 1.0},
            {"kind": "vent_field", "tier": 0, "sonar": "diffuse",
             "detect": "visual", "n": (0, 2), "p": 0.6},
            {"kind": "vent_chimney", "tier": 0, "sonar": "point",
             "detect": "visual", "n": (0, 2), "p": 0.55},
            {"kind": "microbial_mat", "tier": 1, "sonar": None,
             "detect": "uv", "n": (0, 1), "p": 0.4},
            {"kind": "chem_gradient", "tier": 1, "sonar": "diffuse",
             "detect": "sensor", "n": (0, 1), "p": 0.45},
            {"kind": "filter_swarm", "tier": 2, "sonar": "moving",
             "detect": "visual", "n": (0, 1), "p": 0.22},
        ],
    },
}


# ---- entity construction -----------------------------------------------------

def _detect_range(detect: str | None) -> float:
    return {"visual": ID_RANGE_M, "uv": UV_LAMP_RANGE_M,
            "sensor": SENSOR_RANGE_M}.get(detect or "", 0.0)


def _make_entity(spec: _Spec, eid: str, x: float, z: float,
                 ocean: str, dsc: str | None) -> dict:
    """Build one plain-dict entity from a table spec + a placement."""
    tier = spec["tier"]
    e = {
        "id": eid,
        "kind": spec["kind"],
        "tier": tier,
        "ocean": ocean,
        "x": float(x), "z": float(z),
        "vx": 0.0, "vz": 0.0,
        "phase": _u01(eid, "ph") * math.tau,
        "sonar": spec["sonar"],
        "detect": spec["detect"],
        "id_range": _detect_range(spec["detect"]),
        "sci": SCI_BY_TIER[tier] if spec["detect"] else 0.0,
        "dsc": dsc if (spec["detect"] and tier >= 1) else None,
        "pinged": False,
        "discovered": False,
        "glow": False,
        # per-kind size hints the renderer reads (metres)
        "size": _between(*_SIZE_M.get(spec["kind"], (0.4, 0.8)),
                         eid, "sz"),
    }
    if spec["kind"] == "filter_swarm":
        e["members"] = _make_swarm_members(eid, x, z)
        e["current"] = [_between(-0.18, 0.18, eid, "cu"),
                        _between(-0.05, 0.05, eid, "cv")]
    return e


# rough silhouette scale per kind (metres) — feeds marine_art sizing
_SIZE_M: dict[str, tuple] = {
    "organic_drift": (0.25, 0.7),
    "n2_plume": (1.2, 2.4),
    "mineral_chimney": (3.0, 7.0),
    "vent_chimney": (4.0, 9.0),
    "vent_field": (8.0, 16.0),
    "thermokarst": (5.0, 11.0),
    "chem_gradient": (4.0, 8.0),
    "microbial_mat": (1.2, 2.6),
    "filter_swarm": (5.0, 9.0),
    "contact": (16.0, 26.0),
}

SWARM_MIN, SWARM_MAX = 6, 12        # members per filter-feeder school


def _make_swarm_members(eid: str, cx: float, cz: float) -> list[dict]:
    n = SWARM_MIN + int(_u01(eid, "n") * (SWARM_MAX - SWARM_MIN + 1))
    members = []
    for i in range(n):
        members.append({
            "x": cx + _between(-3.0, 3.0, eid, i, "x"),
            "z": cz + _between(-2.0, 2.0, eid, i, "z"),
            "vx": _between(-0.1, 0.1, eid, i, "vx"),
            "vz": _between(-0.05, 0.05, eid, i, "vz"),
            "ph": _u01(eid, i, "p") * math.tau,
        })
    return members


# ---- populate: deterministic entities for one ecology cell -------------------

def populate(body: str, site_id: str, depth_m: float, x_m: float,
             floor_m: float | None = None) -> list[dict]:
    """Spawn the ecology of the cell containing ``x_m`` (10 §2.7 DIVE).

    ``depth_m`` is the SEAFLOOR depth at the cell (the orchestrator's
    `_floor_m(x)`), used to gate the encounter band and anchor floor
    features; ``floor_m`` overrides it if the caller separates the two.
    Returns fresh plain-dict entities; deterministic per (site, cell).
    Bodies with no sea return an empty list.
    """
    ocean = ocean_of(body)
    if ocean is None:
        return []
    floor = float(floor_m if floor_m is not None else depth_m)
    band = depth_band(floor)
    dsc = DSC_BY_BODY.get(body)
    cell = cell_of(x_m)
    x0 = cell * CELL_W_M
    out: list[dict] = []
    for spec in ENCOUNTER[ocean][band]:
        if _u01(site_id, cell, spec["kind"], "gate") >= spec["p"]:
            continue
        nlo, nhi = spec["n"]
        count = nlo + int(_u01(site_id, cell, spec["kind"], "n")
                          * (nhi - nlo + 1))
        for i in range(count):
            eid = f"{site_id}:{cell}:{spec['kind']}:{i}"
            x = x0 + _between(2.0, CELL_W_M - 2.0, eid, "px")
            z = _place_depth(spec["kind"], floor, eid)
            out.append(_make_entity(spec, eid, x, z, ocean, dsc))
    return out


def _place_depth(kind: str, floor: float, eid: str) -> float:
    """Where in the water column this kind sits. Floor-anchored things
    (vents, chimneys, mats, terraces) hug the bottom; drifters and
    plumes fill the column above it."""
    if kind in ("vent_field", "vent_chimney", "mineral_chimney",
                "thermokarst", "microbial_mat"):
        return max(2.0, floor - _between(0.0, 2.0, eid, "dz"))
    if kind == "n2_plume":              # rises from the floor
        return max(4.0, floor - _between(0.0, floor * 0.4, eid, "dz"))
    # drifters / chem clouds / swarms: mid-to-deep column
    return max(3.0, _between(0.35, 0.95, eid, "dz") * floor)


# ---- Tier 3: THE CONTACT (once per campaign, emergent) -----------------------

def maybe_contact(body: str, site_id: str, sub_depth: float,
                  sub_x: float, face: int, campaign_seed,
                  seen: bool) -> dict | None:
    """Roll for the Tier-3 contact at the sub's current deep cell.

    Returns a contact entity to splice into the active set, or None.
    Fires only in a WATER ocean, below ``CONTACT_MIN_DEPTH_M``, when the
    campaign has not yet seen it (``seen`` from the save), and the
    deterministic per-(seed, cell) gate passes. The orchestrator marks
    ``seen`` the moment this returns non-None so it never recurs.
    """
    if seen or ocean_of(body) != "water":
        return None
    if sub_depth < CONTACT_MIN_DEPTH_M:
        return None
    cell = cell_of(sub_x)
    if _u01(campaign_seed, site_id, cell, "contact") >= CONTACT_SPAWN_P:
        return None
    side = int(face) if face else 1              # paces the forward edge
    eid = f"{site_id}:contact:{cell}"
    return {
        "id": eid,
        "kind": "contact",
        "tier": 3,
        "ocean": "water",
        "x": sub_x + side * CONTACT_STANDOFF_M,
        "z": sub_depth + _between(-3.0, 3.0, eid, "z"),
        "vx": 0.0, "vz": 0.0,
        "phase": _u01(eid, "ph") * math.tau,
        "sonar": "moving",
        "detect": "sonar",               # never visually identified
        "id_range": 0.0,
        "sci": SCI_BY_TIER[3],
        "dsc": DSC_BY_BODY.get(body),
        "pinged": False,
        "discovered": False,
        "reveal": False,
        "glow": False,
        "dwell": 0.0,
        "side": side,
        "size": _between(*_SIZE_M["contact"], eid, "sz"),
    }


# ---- behaviours: pure update functions (no clock, no rng) --------------------

def _dist(e: dict, sx: float, sz: float) -> float:
    return math.hypot(e["x"] - sx, e["z"] - sz)


def _upd_static(e: dict, dt: float, c: dict) -> None:
    """Floor features: only the animation phase advances (shimmer)."""
    e["phase"] += dt * 1.4


def _upd_drift(e: dict, dt: float, c: dict) -> None:
    """Marine snow / drifting organics: a slow deterministic settle with
    a sinusoidal sway, plus the cell current (no random walk)."""
    e["phase"] += dt * 0.8
    e["vx"] = 0.12 * math.sin(e["phase"]) + 0.04
    e["vz"] = 0.06                       # gentle sink (heavier than fluid)
    e["x"] += e["vx"] * dt
    e["z"] += e["vz"] * dt


def _upd_plume(e: dict, dt: float, c: dict) -> None:
    """N2 effervescence column: bubbles rise; the head wobbles."""
    e["phase"] += dt * 2.2
    e["x"] += 0.08 * math.sin(e["phase"]) * dt


def _upd_cloud(e: dict, dt: float, c: dict) -> None:
    """Chemical-disequilibrium cloud: breathes, drifts with current."""
    e["phase"] += dt * 0.5
    e["x"] += 0.05 * math.sin(e["phase"] * 0.7) * dt


# --- Tier 2 swarm: boids + environment steering -------------------------------

SWARM_SPEED = 0.55                  # m/s cruise of a filter feeder
SWARM_SCATTER_R = 16.0              # headlights spook them within this
SWARM_WARMTH_R = 40.0              # RTG warmth felt within this
_W_COH, _W_SEP, _W_ALI = 0.5, 1.1, 0.25
_W_LIGHT, _W_WARMTH = 2.6, 0.8


def _upd_swarm(e: dict, dt: float, c: dict) -> None:
    """A schooling filter-feeder swarm — each member steers by boids
    rules (cohesion / separation / alignment) plus the environment: the
    cell current, fleeing the headlight pool, and creeping toward RTG
    warmth in the dark. Per-entity steering (Tier-2 mandate)."""
    members = e["members"]
    cur = e.get("current", [0.0, 0.0])
    n = len(members)
    # flock centroid + mean velocity (one pass)
    cx = sum(m["x"] for m in members) / n
    cz = sum(m["z"] for m in members) / n
    mvx = sum(m["vx"] for m in members) / n
    mvz = sum(m["vz"] for m in members) / n
    sx, sz = c["sub_x"], c["sub_depth"]
    lights, rtg = c["lights_on"], c["rtg_we"]
    for m in members:
        ax = (cx - m["x"]) * _W_COH + (mvx - m["vx"]) * _W_ALI + cur[0]
        az = (cz - m["z"]) * _W_COH + (mvz - m["vz"]) * _W_ALI + cur[1]
        # separation from close neighbours
        for o in members:
            if o is m:
                continue
            dx, dz = m["x"] - o["x"], m["z"] - o["z"]
            d2 = dx * dx + dz * dz
            if 1e-4 < d2 < 4.0:
                inv = _W_SEP / d2
                ax += dx * inv
                az += dz * inv
        # environment: flee the headlight pool, seek RTG warmth
        dxs, dzs = m["x"] - sx, m["z"] - sz
        ds = math.hypot(dxs, dzs) + 1e-6
        if lights and ds < SWARM_SCATTER_R:
            f = _W_LIGHT * (1.0 - ds / SWARM_SCATTER_R)
            ax += (dxs / ds) * f
            az += (dzs / ds) * f
        elif rtg > 0.0 and ds < SWARM_WARMTH_R:
            f = _W_WARMTH * (rtg / 330.0) * (1.0 - ds / SWARM_WARMTH_R)
            ax -= (dxs / ds) * f
            az -= (dzs / ds) * f
        m["vx"] += ax * dt
        m["vz"] += az * dt
        # clamp speed
        sp = math.hypot(m["vx"], m["vz"])
        if sp > SWARM_SPEED:
            k = SWARM_SPEED / sp
            m["vx"] *= k
            m["vz"] *= k
        m["x"] += m["vx"] * dt
        m["z"] += m["vz"] * dt
        m["ph"] += dt * 3.0
    # the swarm's nominal position tracks its centroid (sonar/draw anchor)
    e["x"], e["z"] = cx, cz
    e["vx"], e["vz"] = mvx, mvz


def _upd_contact(e: dict, dt: float, c: dict) -> None:
    """THE CONTACT: holds station at the ragged edge of the headlight
    cone, weaving, matching the sub's depth lazily. It accumulates sonar
    dwell while it shadows the sub; past the threshold the FIRST fires
    (handled in :func:`step`). It never closes to ID range."""
    e["phase"] += dt * 0.45
    sx, sz = c["sub_x"], c["sub_depth"]
    side = e.get("side", -1)
    # target: standoff to one side of the sub, weaving in depth
    tx = sx + side * CONTACT_STANDOFF_M
    tz = sz + 6.0 * math.sin(e["phase"])
    # ease toward the target (slow, massive — never darts)
    e["vx"] += (0.4 * (tx - e["x"]) - e["vx"]) * min(1.0, dt * 0.6)
    e["vz"] += (0.4 * (tz - e["z"]) - e["vz"]) * min(1.0, dt * 0.6)
    e["x"] += e["vx"] * dt
    e["z"] += e["vz"] * dt
    # dwell only accrues while the sub stays in the deep dark near it
    if c["sub_depth"] >= CONTACT_MIN_DEPTH_M and _dist(e, sx, sz) < \
            SONAR_RANGE_M:
        e["dwell"] += dt
        if e["dwell"] >= CONTACT_REVEAL_DWELL_S:
            e["reveal"] = True
    else:
        e["dwell"] = max(0.0, e["dwell"] - dt * 0.5)


_UPDATERS = {
    "organic_drift": _upd_drift,
    "n2_plume": _upd_plume,
    "mineral_chimney": _upd_static,
    "vent_chimney": _upd_static,
    "vent_field": _upd_static,
    "thermokarst": _upd_static,
    "microbial_mat": _upd_static,
    "chem_gradient": _upd_cloud,
    "filter_swarm": _upd_swarm,
    "contact": _upd_contact,
}


# ---- step: advance the ecology + emit discovery events ------------------------

def step(entities: list[dict], dt: float, sub_x: float, sub_depth: float,
         lights_on: bool, rtg_we: float, uv_on: bool = False) -> list:
    """Advance every entity by ``dt`` and return the events the
    orchestrator wires to research / Chronicle.

    Events (each fires AT MOST once per entity):
      ('sonar_contact', cls, eid)         — acoustic return entered range
      ('discovery', tier, sci, dsc, eid)  — confirmed by light / UV /
                                            bench / sonar dwell (Tier 3)
    Sonar is acoustic (no light needed); a visual/UV/bench ID is a
    separate, closer event — so a blip can pace you long before you
    name it. The Tier-3 'discovery' should be logged by the caller as a
    FIRST_ Chronicle entry (12 §4) and paid as big science (11 §5).
    """
    ctx = {"sub_x": sub_x, "sub_depth": sub_depth,
           "lights_on": lights_on, "rtg_we": rtg_we, "uv_on": uv_on}
    events: list = []
    for e in entities:
        upd = _UPDATERS.get(e["kind"])
        if upd is not None:
            upd(e, dt, ctx)
        d = _dist(e, sub_x, sub_depth)
        # acoustic blip (once)
        if e["sonar"] and not e["pinged"] and d <= SONAR_RANGE_M:
            e["pinged"] = True
            events.append(("sonar_contact", e["sonar"], e["id"]))
        # UV fluorescence is a live visual state the renderer reads
        if e["detect"] == "uv":
            e["glow"] = uv_on and d <= UV_LAMP_RANGE_M
        # confirmed identification (once)
        if not e["discovered"] and _can_identify(e, ctx, d):
            e["discovered"] = True
            if e["sci"] > 0.0:
                events.append(("discovery", e["tier"], e["sci"],
                               e["dsc"], e["id"]))
    return events


def _can_identify(e: dict, c: dict, d: float) -> bool:
    """Has the sub confirmed this entity by its detection mode?"""
    mode = e["detect"]
    if mode == "visual":
        return c["lights_on"] and d <= e["id_range"]
    if mode == "uv":
        return c["uv_on"] and d <= e["id_range"]
    if mode == "sensor":
        return d <= e["id_range"]
    if mode == "sonar":                 # Tier-3 contact: dwell reveal
        return bool(e.get("reveal"))
    return False


# ---- small helpers for the HUD / Chronicle text ------------------------------

_LABELS = {
    "organic_drift": "drifting organics",
    "n2_plume": "N2 effervescence plume",
    "mineral_chimney": "evaporite chimney",
    "vent_chimney": "hydrothermal chimney",
    "vent_field": "hydrothermal vent field",
    "thermokarst": "thermokarst terrace",
    "chem_gradient": "methanogenic disequilibrium",
    "microbial_mat": "fluorescing microbial mat",
    "filter_swarm": "motile filter-feeder swarm",
    "contact": "UNIDENTIFIED LARGE CONTACT",
}
# the abiotic counter-hypothesis travels with every organics readout
# (11 §4.11 / DECISIONS F34 — never promise life)
_COUNTER = {
    1: "abiotic serpentinization / photochemistry cannot be excluded",
    2: "advective particulate aggregate; biological origin unconfirmed",
    3: "acoustic artefact or unmodelled density layer not excluded",
}


def label(entity: dict) -> str:
    return _LABELS.get(entity["kind"], entity["kind"])


def chronicle_text(entity: dict) -> str:
    """A doctrine-safe one-liner for a discovery (Chronicle / toast)."""
    base = label(entity)
    tier = entity["tier"]
    if tier == 0:
        return f"Surveyed {base}."
    note = _COUNTER.get(tier, "origin uncertain")
    if tier == 3:
        return (f"FIRST sonar contact with a large moving body — "
                f"never resolved on the headlights. ({note}.)")
    return f"Biosignature logged: {base} — {note}."


def is_first(entity: dict) -> bool:
    """Tier-3 discoveries become FIRST_ Chronicle entries (12 §4)."""
    return entity["tier"] >= 3
