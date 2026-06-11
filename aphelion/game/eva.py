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
SUIT_O2_S = 6.0 * 3_600.0     # surface EVA suit endurance (08 ls03)
INTERACT_RANGE_M = 4.0
SCOOPS_PER_EVA = 3

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
                 member: str) -> None:
        self.sector_id = sector_id
        self.g = max(0.03, g)          # dock-mode worlds still settle
        self.member = member
        self.terrain = terrain_line(sector_id, slope_sigma)
        rng = np.random.default_rng(_seed("rocks:" + sector_id))
        self.rocks = [(float(rng.uniform(-900.0, 900.0)),
                       float(rng.uniform(0.2, 1.1)))
                      for _ in range(70)]
        self.x = 6.0                   # metres; lander pad at origin
        self.y = self.ground_at(6.0)
        self.vy = 0.0
        self.facing = 1
        self.airborne = False
        self.o2_s = SUIT_O2_S
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

    @property
    def o2_frac(self) -> float:
        return self.o2_s / SUIT_O2_S

    def jump_apex_m(self) -> float:
        """How high this world lets you leap (HUD flavor + tests)."""
        return JUMP_MS ** 2 / (2.0 * self.g)

    # -- interactions -------------------------------------------------------
    def near(self, x_m: float, rng: float = INTERACT_RANGE_M) -> bool:
        return abs(self.x - x_m) <= rng


def module_positions(built: list[str]) -> dict[int, float]:
    """Module exteriors line up right of the pad, matching the colony
    scene's ordering: index -> x metres."""
    return {i: 28.0 + 16.0 * i for i in range(len(built))}


ANOMALY_X_M = -95.0            # the marked site west of the pad
FLAG_X_MIN_M = 12.0            # plant clear of the lander
