"""EVA walk mode (the marquee surface layer): a side-view astronaut on a
deterministic fBM terrain line, with body-true gravity (you really do jump
six times higher on the Moon), a real suit clock, and interaction ranges
for the lander, base modules, anomalies, flags and sample scoops.

Sim-only: rendering lives in main's eva scene; physics here is testable
headless. Terrain is seeded by (sector id) — the same hills every visit
(S-7c persistence).
"""

from __future__ import annotations

import hashlib
import math

import numpy as np

WALK_MS = 1.6                 # suit walk speed, m/s
RUN_MS = 3.4
JUMP_MS = 3.2                 # vertical leap speed in the suit
SUIT_O2_S = 6.0 * 3_600.0     # primary-O2 endurance (08 ls03; EMU class)
# the rest of the EMU consumable set (08 §4.7) — each has its own clock, and
# your safe-return time is the MINIMUM across all four, not just oxygen.
SUIT_BATT_WH = 430.0          # suit battery energy (fans, pumps, comms, heat)
SUIT_BASE_W = 53.0            # nominal electrical draw
SUIT_LAMP_W = 26.0            # helmet lamp adder (night / underground)
SUIT_FEEDWATER_KG = 3.0      # sublimator feedwater, sublimed to space to cool
SUIT_COOL_KGPH = 0.40        # nominal cooling draw at rest
SUIT_CO2_CAP_KG = 1.48       # METOX/LiOH canister CO2 capacity
SUIT_CO2_KGPH = 0.042        # metabolic CO2 at rest (~1 kg/day)
SUIT_PRESS_KPA = 29.6        # suit pressure, 4.3 psia pre-breathe setpoint
# metabolic exertion multiplier — moving and (worse) running drive cooling,
# CO2 and a little O2 harder; this is what makes the limiter shift in play
EXERT_IDLE = 1.0
EXERT_WALK = 1.5
EXERT_RUN = 2.4
INTERACT_RANGE_M = 4.0
SCOOPS_PER_EVA = 3
STEP_UP_M = 1.05              # max riser a suited walker climbs (2 tiles)
BODY_LO_M = 0.3               # wall probes: shin and chest heights
BODY_HI_M = 1.3
HELMET_M = 1.7

_TERRAIN_N = 4_096            # heightline samples
_TERRAIN_SPAN_M = 2_048.0     # metres covered; wraps beyond
_FLAT_HALF_M = 40.0           # graded pad around the lander


def _seed(s: str) -> int:
    return int.from_bytes(hashlib.blake2b(s.encode(), digest_size=8).digest(),
                          "little")


def terrain_line(sector_id: str, slope_sigma: float) -> np.ndarray:
    """Deterministic heightline (metres) — fBM value noise scaled by the
    sector's slope class, graded flat near the origin pad."""
    rng = np.random.default_rng(_seed("eva:" + sector_id))
    h = np.zeros(_TERRAIN_N)
    amp, n = 1.0, 8
    total = 0.0
    for _ in range(5):
        pts = rng.uniform(-1.0, 1.0, n + 1)
        xs = np.linspace(0.0, n, _TERRAIN_N)
        i0 = np.floor(xs).astype(int)
        f = xs - i0
        f = f * f * (3.0 - 2.0 * f)               # smoothstep
        h += amp * ((1.0 - f) * pts[i0] + f * pts[np.minimum(i0 + 1, n)])
        total += amp
        amp *= 0.5
        n *= 2
    h = h / total * (2.0 + slope_sigma * 1.8)      # metres of relief
    # grade the pad flat (construction crews did it before you landed)
    xm = (np.arange(_TERRAIN_N) / _TERRAIN_N - 0.5) * _TERRAIN_SPAN_M
    fade = np.clip((np.abs(xm) - _FLAT_HALF_M) / 60.0, 0.0, 1.0)
    return h * fade


class EvaState:
    """One astronaut on the surface. step() is fixed-dt friendly."""

    def __init__(self, sector_id: str, slope_sigma: float, g: float,
                 member: str, tiles=None) -> None:
        self.sector_id = sector_id
        self.g = max(0.03, g)          # dock-mode worlds still settle
        self.member = member
        self.terrain = terrain_line(sector_id, slope_sigma)
        self.tiles = tiles             # TileWorld (duck-typed) or None
        rng = np.random.default_rng(_seed("rocks:" + sector_id))
        self.rocks = [(float(rng.uniform(-900.0, 900.0)),
                       float(rng.uniform(0.2, 1.1)))
                      for _ in range(70)]
        self.x = 6.0                   # metres; lander pad at origin
        self.y = tiles.surface_y(6.0) if tiles else self.ground_at(6.0)
        self.vy = 0.0
        self.facing = 1
        self.airborne = False
        self.o2_s = SUIT_O2_S
        # the rest of the EMU consumable set
        self.batt_wh = SUIT_BATT_WH
        self.feedwater_kg = SUIT_FEEDWATER_KG
        self.co2_load_kg = 0.0         # scrubber loading toward saturation
        self.lamp_on = False           # helmet lamp (set by the scene)
        self.exertion = EXERT_IDLE     # last step's metabolic multiplier
        self.scoops_left = SCOOPS_PER_EVA
        self.dist_walked = 0.0
        self.frame = 0.0               # animation phase

    # -- terrain ---------------------------------------------------------
    def ground_at(self, x_m: float) -> float:
        u = (x_m / _TERRAIN_SPAN_M + 0.5) % 1.0
        i = u * (_TERRAIN_N - 1)
        i0 = int(i)
        f = i - i0
        t = self.terrain
        return float((1.0 - f) * t[i0] + f * t[min(i0 + 1, _TERRAIN_N - 1)])

    # -- physics ----------------------------------------------------------
    def step(self, dt: float, move: int, run: bool, jump: bool) -> None:
        """move in {-1,0,1}; returns nothing — read state after."""
        if self.tiles is not None:
            self._step_tiles(dt, move, run, jump)
            self.o2_s = max(0.0, self.o2_s - dt)
            self._suit_consume(dt, move, run)
            return
        speed = RUN_MS if run else WALK_MS
        if move:
            self.facing = move
            # airborne drift is half control (suit RCS-less)
            self.x += move * speed * dt * (0.5 if self.airborne else 1.0)
            if not self.airborne:
                self.dist_walked += speed * dt
                self.frame += dt * (9.0 if run else 6.0)
        if jump and not self.airborne:
            self.vy = JUMP_MS
            self.airborne = True
        if self.airborne:
            self.vy -= self.g * dt
            self.y += self.vy * dt
            gy = self.ground_at(self.x)
            if self.y <= gy and self.vy <= 0.0:
                self.y = gy
                self.vy = 0.0
                self.airborne = False
        else:
            self.y = self.ground_at(self.x)
        self.o2_s = max(0.0, self.o2_s - dt)
        self._suit_consume(dt, move, run)

    def _step_tiles(self, dt: float, move: int, run: bool,
                    jump: bool) -> None:
        """Tile-world physics: walls block, risers ≤ 2 tiles are walked,
        shafts and ledges drop you, roofs stop your jump. The body is one
        column wide with shin/chest probes ahead of the facing edge."""
        w = self.tiles
        speed = RUN_MS if run else WALK_MS
        if move:
            self.facing = move
            nx = self.x + move * speed * dt * (0.5 if self.airborne else 1.0)
            lead = nx + move * 0.35
            if self.airborne:
                if not (w.solid(lead, self.y + BODY_LO_M)
                        or w.solid(lead, self.y + BODY_HI_M)):
                    self.x = nx
            else:
                floor_new = w.ground_below(lead, self.y + STEP_UP_M)
                rise = floor_new - self.y
                if rise <= STEP_UP_M \
                        and not w.solid(lead, floor_new + 0.4) \
                        and not w.solid(lead, floor_new + 1.4):
                    self.x = nx
                    if floor_new > self.y:        # climb the riser
                        self.y = floor_new
                    self.dist_walked += speed * dt
                    self.frame += dt * (9.0 if run else 6.0)
        if jump and not self.airborne:
            self.vy = JUMP_MS
            self.airborne = True
        if self.airborne:
            self.vy -= self.g * dt
            ny = self.y + self.vy * dt
            if self.vy > 0.0 and w.solid(self.x, ny + HELMET_M):
                self.vy = 0.0                     # helmet meets the roof
                ny = self.y
            floor = w.ground_below(self.x, self.y + 0.05)
            if ny <= floor and self.vy <= 0.0:
                self.y = floor
                self.vy = 0.0
                self.airborne = False
            else:
                self.y = ny
        else:
            floor = w.ground_below(self.x, self.y + 0.05)
            if self.y - floor > STEP_UP_M:        # ledge / your own shaft
                self.airborne = True
            else:
                self.y = floor

    @property
    def o2_frac(self) -> float:
        return self.o2_s / SUIT_O2_S

    # -- suit consumables (the EMU clock set) -------------------------------
    def _suit_consume(self, dt: float, move: int, run: bool) -> None:
        """Burn battery, sublimator feedwater and scrubber capacity. Cooling
        and CO2 scale with exertion; the lamp adds an electrical load."""
        exert = (EXERT_RUN if run else EXERT_WALK) if move else EXERT_IDLE
        self.exertion = exert
        draw_w = SUIT_BASE_W + (SUIT_LAMP_W if self.lamp_on else 0.0)
        self.batt_wh = max(0.0, self.batt_wh - draw_w * dt / 3_600.0)
        self.feedwater_kg = max(
            0.0, self.feedwater_kg - SUIT_COOL_KGPH * exert * dt / 3_600.0)
        self.co2_load_kg = min(
            SUIT_CO2_CAP_KG,
            self.co2_load_kg + SUIT_CO2_KGPH * exert * dt / 3_600.0)

    def idle_burn(self, seconds: float) -> None:
        """Advance the consumable clocks by extra sim seconds (the EVA scene
        runs faster than wall-clock; O2 is burned separately by the caller)."""
        self._suit_consume(seconds, 1 if self.exertion > EXERT_IDLE else 0,
                           self.exertion >= EXERT_RUN)

    def recharge_suit(self) -> None:
        """Back at the lander: top off every consumable."""
        self.o2_s = SUIT_O2_S
        self.batt_wh = SUIT_BATT_WH
        self.feedwater_kg = SUIT_FEEDWATER_KG
        self.co2_load_kg = 0.0

    def suit_status(self) -> dict:
        """The four-clock readout. Each entry: (fraction 0..1, seconds left).
        'limit' is the consumable that ends the walk first, in seconds."""
        exert = max(self.exertion, EXERT_IDLE)
        draw_w = SUIT_BASE_W + (SUIT_LAMP_W if self.lamp_on else 0.0)
        cool = SUIT_COOL_KGPH * exert
        scrub = SUIT_CO2_KGPH * exert
        clocks = {
            "O2": (self.o2_frac, self.o2_s),
            "PWR": (self.batt_wh / SUIT_BATT_WH,
                    self.batt_wh / draw_w * 3_600.0 if draw_w > 0 else 1e9),
            "H2O": (self.feedwater_kg / SUIT_FEEDWATER_KG,
                    self.feedwater_kg / cool * 3_600.0 if cool > 0 else 1e9),
            "CO2": (1.0 - self.co2_load_kg / SUIT_CO2_CAP_KG,
                    (SUIT_CO2_CAP_KG - self.co2_load_kg) / scrub * 3_600.0
                    if scrub > 0 else 1e9),
        }
        limit_key = min(clocks, key=lambda k: clocks[k][1])
        return {"clocks": clocks, "limit_key": limit_key,
                "limit_s": clocks[limit_key][1]}

    def jump_apex_m(self) -> float:
        """How high this world lets you leap (HUD flavor + tests)."""
        return JUMP_MS ** 2 / (2.0 * self.g)

    # -- interactions -------------------------------------------------------
    def near(self, x_m: float, rng: float = INTERACT_RANGE_M) -> bool:
        return abs(self.x - x_m) <= rng

    # -- digging (tile worlds) ----------------------------------------------
    def dig_target(self, down: bool) -> tuple[float, float] | None:
        """World point the held tool attacks: the lowest blocking tile
        ahead of the facing edge (X), or the tile underfoot (C). None when
        airborne, tile-less, or facing open ground."""
        if self.tiles is None or self.airborne:
            return None
        if down:
            return self.x, self.y - 0.25
        lead = self.x + self.facing * 0.8
        for h in (BODY_LO_M, 0.8, BODY_HI_M):
            if self.tiles.solid(lead, self.y + h):
                return lead, self.y + h
        return None

    def depth_m(self) -> float:
        """Metres below the open-sky surface (0 above ground)."""
        if self.tiles is None:
            return 0.0
        return max(0.0, self.tiles.surface_y(self.x) - self.y)


def module_positions(built: list[str]) -> dict[int, float]:
    """Module exteriors line up right of the pad, matching the colony
    scene's ordering: index -> x metres."""
    return {i: 28.0 + 16.0 * i for i in range(len(built))}


ANOMALY_X_M = -95.0            # the marked site west of the pad
FLAG_X_MIN_M = 12.0            # plant clear of the lander
