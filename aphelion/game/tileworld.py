"""Terraria-style site worlds (director directive + bible S-7c): every
landing sector instantiates ONE persistent side-view tile world — strata
under the heightline, ore and ice veins visible in cross-section, caves
and lava tubes to find, and digging at canonical excavation rates. The
planet stays real-scale on the map; this is the local window you walk.

Tiles are 0.5 m. Worlds are deterministic per sector; player edits
(dug tiles) persist in the campaign's explore state.
"""

from __future__ import annotations

import hashlib

import numpy as np

from aphelion.game.eva import terrain_line, _TERRAIN_SPAN_M

TILE_M = 0.5
W_TILES = 4_096                 # 2,048 m of world, wraps at the edges
D_TILES = 320                   # 160 m of diggable depth below datum
SKY_ROWS = 64                   # rows above datum for hills/jumping
H_TILES = SKY_ROWS + D_TILES

# tile types
AIR = 0
REGOLITH = 1
ROCK = 2
ICE = 3
ORE = 4
BEDROCK = 5

# what a dug tile yields, kg (0.5 x 0.5 x 1 m at honest densities)
TILE_KG = {REGOLITH: 375.0, ROCK: 650.0, ICE: 230.0, ORE: 900.0}
# seconds for ONE astronaut with a hand scoop (e_dig made tactile);
# machines dig through the ledger, people dig to prospect and shelter
DIG_S = {REGOLITH: 1.2, ICE: 2.4, ORE: 4.5, ROCK: 6.0}

_ICY_KINDS = {"psr_ice", "mars_ice", "ice_burrow"}


def _seed(s: str) -> int:
    return int.from_bytes(hashlib.blake2b(s.encode(), digest_size=8).digest(),
                          "little")


def generate(sector_id: str, slope_sigma: float,
             site_kind: str) -> np.ndarray:
    """The world grid, shape (W_TILES, H_TILES); row 0 = top of sky.
    Deterministic per sector."""
    rng = np.random.default_rng(_seed("tiles:" + sector_id))
    grid = np.zeros((W_TILES, H_TILES), dtype=np.uint8)

    # surface from the SAME heightline the walk scene used (continuity)
    line = terrain_line(sector_id, slope_sigma)
    xs = (np.arange(W_TILES) / W_TILES * len(line)).astype(int)
    surf_m = line[np.minimum(xs, len(line) - 1)]
    surf_row = (SKY_ROWS - surf_m / TILE_M).astype(int)
    surf_row = np.clip(surf_row, 4, SKY_ROWS + 40)

    rows = np.arange(H_TILES)[None, :]
    depth_m = (rows - surf_row[:, None]) * TILE_M    # >0 below ground

    # strata: regolith blanket (3-8 m, varies along x) over rock
    blanket = 3.0 + 5.0 * (0.5 + 0.5 * np.sin(
        np.arange(W_TILES) * 0.011 + rng.uniform(0, 6.28)))
    grid[(depth_m > 0)] = ROCK
    grid[(depth_m > 0) & (depth_m <= blanket[:, None])] = REGOLITH
    grid[depth_m > (D_TILES - 8) * TILE_M] = BEDROCK
    grid[:, H_TILES - 6:] = BEDROCK              # absolute floor seal

    # ice lenses on icy worlds: shallow ellipses you can SEE in a cliff
    n_lens = 18 if site_kind in _ICY_KINDS else 3
    for _ in range(n_lens):
        cx = int(rng.uniform(0, W_TILES))
        cd = rng.uniform(2.0, 60.0)                  # lens depth, m
        ax = rng.uniform(5.0, 26.0) / TILE_M         # semi-axes in tiles
        ay = rng.uniform(1.5, 7.0) / TILE_M
        cy = int(surf_row[cx] + cd / TILE_M)
        x0, x1 = int(cx - ax), int(cx + ax + 1)
        for gx in range(x0, x1):
            wx = gx % W_TILES
            dx = (gx - cx) / ax
            span = ay * np.sqrt(max(0.0, 1.0 - dx * dx))
            y0, y1 = int(cy - span), int(cy + span + 1)
            sel = grid[wx, max(0, y0):y1]
            sel[(sel == ROCK) | (sel == REGOLITH)] = ICE
            grid[wx, max(0, y0):y1] = sel

    # ore veins: drunken walks through the rock
    n_vein = 10 if site_kind not in _ICY_KINDS else 4
    for _ in range(n_vein):
        vx = rng.uniform(0, W_TILES)
        vy = surf_row[int(vx) % W_TILES] + rng.uniform(6.0, 80.0) / TILE_M
        ang = rng.uniform(0, 6.28)
        for _step in range(int(rng.uniform(60, 220))):
            ang += rng.uniform(-0.5, 0.5)
            vx += np.cos(ang) * 1.6
            vy += abs(np.sin(ang)) * 0.5 + rng.uniform(-0.4, 0.6)
            ix, iy = int(vx) % W_TILES, int(vy)
            if iy <= 4 or iy >= H_TILES - 9:
                break
            for ox in (-1, 0, 1):
                for oy in (0, 1):
                    gx, gy = (ix + ox) % W_TILES, min(iy + oy, H_TILES - 1)
                    if grid[gx, gy] == ROCK:
                        grid[gx, gy] = ORE

    # caves and lava tubes: worm carves, mostly sealed underground
    for _ in range(6):
        wx = rng.uniform(0, W_TILES)
        wy = surf_row[int(wx) % W_TILES] + rng.uniform(8.0, 90.0) / TILE_M
        ang = rng.uniform(0, 6.28)
        r = rng.uniform(1.8, 4.0)
        for _step in range(int(rng.uniform(120, 400))):
            ang += rng.uniform(-0.35, 0.35)
            wx += np.cos(ang) * 1.5
            wy += np.sin(ang) * 0.7
            ix, iy = int(wx) % W_TILES, int(wy)
            if iy <= SKY_ROWS - 2 or iy >= H_TILES - 10:
                break
            rr = int(r)
            for ox in range(-rr, rr + 1):
                for oy in range(-rr, rr + 1):
                    if ox * ox + oy * oy <= rr * rr:
                        gx = (ix + ox) % W_TILES
                        gy = iy + oy
                        if 0 <= gy < H_TILES - 8 \
                                and grid[gx, gy] != BEDROCK:
                            grid[gx, gy] = AIR
    return grid


class TileWorld:
    """The walkable, diggable site world. x in metres maps to columns
    (wrapping); y in metres above datum maps to rows."""

    def __init__(self, sector_id: str, slope_sigma: float,
                 site_kind: str, dug: list | None = None) -> None:
        self.sector_id = sector_id
        self.grid = generate(sector_id, slope_sigma, site_kind)
        self.dug: set[tuple[int, int]] = set()
        for ix, iy in (dug or []):
            self.grid[int(ix) % W_TILES, int(iy)] = AIR
            self.dug.add((int(ix), int(iy)))

    # -- coordinate maps ----------------------------------------------------
    @staticmethod
    def col(x_m: float) -> int:
        u = (x_m / _TERRAIN_SPAN_M + 0.5) % 1.0
        return int(u * W_TILES) % W_TILES

    @staticmethod
    def row(y_m: float) -> int:
        return int(SKY_ROWS - y_m / TILE_M)

    @staticmethod
    def row_to_y(row: int) -> float:
        return (SKY_ROWS - row) * TILE_M

    def tile_at(self, x_m: float, y_m: float) -> int:
        r = self.row(y_m)
        if r < 0:
            return AIR
        if r >= H_TILES:
            return BEDROCK
        return int(self.grid[self.col(x_m), r])

    def solid(self, x_m: float, y_m: float) -> bool:
        return self.tile_at(x_m, y_m) != AIR

    def surface_y(self, x_m: float) -> float:
        """Metres-above-datum of the topmost solid tile at x (open sky)."""
        c = self.col(x_m)
        col = self.grid[c]
        solid_rows = np.nonzero(col != AIR)[0]
        if len(solid_rows) == 0:
            return 0.0
        return self.row_to_y(int(solid_rows[0]) - 1) - TILE_M

    def ground_below(self, x_m: float, y_m: float) -> float:
        """Metres of the first solid tile top at or below y (cave floors)."""
        c = self.col(x_m)
        r0 = max(0, self.row(y_m))
        col = self.grid[c]
        below = np.nonzero(col[r0:] != AIR)[0]
        if len(below) == 0:
            return self.row_to_y(H_TILES)
        return self.row_to_y(r0 + int(below[0]) - 1) - TILE_M

    # -- digging --------------------------------------------------------------
    def dig(self, x_m: float, y_m: float) -> tuple[int, float]:
        """Remove the tile at (x, y). Returns (tile_type, seconds it took);
        AIR/BEDROCK return (type, 0.0) and change nothing."""
        c, r = self.col(x_m), self.row(y_m)
        if not (0 <= r < H_TILES):
            return AIR, 0.0
        t = int(self.grid[c, r])
        if t in (AIR, BEDROCK):
            return t, 0.0
        self.grid[c, r] = AIR
        self.dug.add((c, r))
        return t, DIG_S[t]

    def dug_list(self) -> list[list[int]]:
        return sorted([list(p) for p in self.dug])
