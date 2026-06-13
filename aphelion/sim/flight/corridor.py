"""Aerocapture / entry corridor advisor (01 §1.6 EDL/aerocapture corridor
rules; 01 §3.11 entry physics).

Finds the flight-path-angle corridor by bisection over `fly_entry` outcomes
(the integrator already adjudicated by test_phase5_environments: Mars at
5.6 km/s / beta 300 — 7 deg skips, 9 captures, 11 lands), reports it both as
gamma limits (degrees) and as the §1.6 periapsis-altitude window
(h_p* ± Δh, Δh ≈ 0.5–1.0 × H_local), advises a planned entry against it,
sizes TPS need from the Sutton–Graves + f_rad heating law at the
Allen–Eggers peak-heating point, and estimates ballistic downrange for
landing-site prediction.

The game is 2D coplanar: entries are planar ballistic arcs (no inclination,
no out-of-plane lift), so the classical corridor is exactly a 1D band in
flight-path angle gamma — corridor edges are single bisections, not a
2D target box.

TPS classes map to the ratings the game already ships (aphelion/main.py
lines 70–71): _CAPSULE_HEAT_W_M2 = 2.5e6 (ablative-protected stack) and
_BARE_HEAT_W_M2 = 0.9e6 (bare tankage); main.py compares them against the
f_rad-augmented fly_entry peak heating, and so does this module.

Pure functions, deterministic, no pygame.
"""

from __future__ import annotations

import math
from bisect import bisect_right
from dataclasses import dataclass

from aphelion.sim.environment.atmosphere import (
    BREAKPOINTS,
    density,
    interface_altitude,
)
from aphelion.sim.flight.entry import (
    EntryResult,
    fly_entry,
    stagnation_heating_w_m2,
)

# Shipped TPS ratings — keep in sync with aphelion/main.py:70-71
# (_CAPSULE_HEAT_W_M2 / _BARE_HEAT_W_M2); main.py burns a vessel up when
# fly_entry's peak_heating_w_m2 exceeds its rating.
CAPSULE_HEAT_W_M2 = 2.5e6     # ablative-protected stack survives this
BARE_HEAT_W_M2 = 0.9e6        # bare tankage does not

# Allen-Eggers ballistic entry (01 §1.6 sanity model): along an exponential
# atmosphere v(rho) = v_E exp(-rho H / (2 beta sin g)); q = k sqrt(rho) v^3
# peaks where rho* = beta sin(gamma)/(3 H) and v* = v_E e^(-1/6).
_VSTAR_FRACTION = math.exp(-1.0 / 6.0)

_RANK = {"escaped": 0, "captured": 1, "landed": 2}


# ---------------------------------------------------------------------------
# helpers

def local_scale_height(body_id: str, altitude_m: float) -> float:
    """Local exponential scale height H_i (m) of the piecewise-exponential
    atmosphere segment containing altitude_m (01 §1.4b breakpoint tables);
    clamped to the first/last segment outside the table."""
    bp = BREAKPOINTS.get(body_id)
    if not bp:
        raise ValueError(f"{body_id} has no atmosphere (no corridor)")
    i = max(0, min(bisect_right([h for h, _ in bp], altitude_m) - 1,
                   len(bp) - 2))
    (h_i, rho_i), (h_j, rho_j) = bp[i], bp[i + 1]
    return (h_j - h_i) / math.log(rho_i / rho_j)


def vacuum_periapsis_alt_m(mu: float, radius: float, r0: float,
                           v: float, gamma_rad: float) -> float:
    """Periapsis altitude (m) of the drag-free conic through the entry state
    (r0, v, gamma). This is the §1.6 corridor coordinate: the corridor is a
    periapsis-altitude window h_p* ± Δh as much as a gamma band. Planar 2D:
    r_p = p/(1+e) works for every conic."""
    eps = 0.5 * v * v - mu / r0
    h_mom = r0 * v * math.cos(gamma_rad)
    e = math.sqrt(max(1.0 + 2.0 * eps * h_mom * h_mom / (mu * mu), 0.0))
    r_p = h_mom * h_mom / mu / (1.0 + e)
    return r_p - radius


# ---------------------------------------------------------------------------
# corridor search

@dataclass(frozen=True, slots=True)
class CorridorReport:
    """Entry corridor for one (body, v_entry, beta), angles in DEGREES
    (positive = below the local horizon, the fly_entry convention)."""

    body_id: str
    v_entry: float                # m/s at the atmosphere interface
    beta: float                   # kg/m2 ballistic coefficient
    gamma_skip_limit: float       # shallower than this escapes; NaN = no
                                  # skip-out possible (bound arrival)
    gamma_capture_lo: float       # capture band, shallow edge (NaN = none)
    gamma_capture_hi: float       # capture band, steep edge
    gamma_land_limit: float       # steeper than this lands; NaN = nothing
                                  # lands inside the search envelope
    gamma_center: float           # capture-band midpoint (NaN = no band)
    peak_g: float                 # fly_entry peak g at the corridor center
    peak_heating_w_m2: float      # fly_entry peak heating at the center
    exit_apoapsis_m: float        # post-pass apoapsis at the center
    hp_window_lo_m: float         # §1.6 periapsis-altitude window, deep edge
    hp_window_hi_m: float         # ... shallow edge (vacuum-conic h_p)

    @property
    def width_deg(self) -> float:
        return self.gamma_capture_hi - self.gamma_capture_lo

    @property
    def has_capture_band(self) -> bool:
        return (math.isfinite(self.gamma_capture_lo)
                and math.isfinite(self.gamma_capture_hi))


def corridor(body_id: str, mu: float, radius: float, v_entry: float,
             beta_kg_m2: float, *, nose_radius_m: float = 2.0,
             gamma_floor_deg: float = 0.5, gamma_ceil_deg: float = 30.0,
             tol_deg: float = 0.02, dt: float = 0.05) -> CorridorReport:
    """Bisect fly_entry outcomes over gamma (degrees, planar) to find the
    skip/capture/land corridor at the atmosphere interface.

    Outcome rank (escaped=0 < captured=1 < landed=2) is monotone
    non-decreasing in gamma for a ballistic single pass — steeper digs
    deeper, sheds more energy — so each corridor edge is one bisection.
    """
    h_int = interface_altitude(body_id)
    if not math.isfinite(h_int):
        raise ValueError(f"{body_id} has no atmosphere (no corridor)")
    r0 = radius + h_int

    def run(gamma_deg: float) -> EntryResult:
        return fly_entry(body_id, mu, radius, r0=r0, v0=v_entry,
                         gamma0_rad=math.radians(gamma_deg),
                         beta_kg_m2=beta_kg_m2,
                         nose_radius_m=nose_radius_m, dt=dt)

    def rank(gamma_deg: float) -> int:
        return _RANK[run(gamma_deg).outcome]

    def edge(lo: float, hi: float, target: int) -> float:
        # precondition rank(lo) < target <= rank(hi)
        while hi - lo > tol_deg:
            mid = 0.5 * (lo + hi)
            if rank(mid) >= target:
                hi = mid
            else:
                lo = mid
        return 0.5 * (lo + hi)

    r_floor = rank(gamma_floor_deg)
    r_ceil = rank(gamma_ceil_deg)

    skip = cap_lo = cap_hi = land = math.nan
    if r_floor == 0 and r_ceil >= 1:
        skip = edge(gamma_floor_deg, gamma_ceil_deg, 1)
        cap_lo = skip
    elif r_floor == 1:
        cap_lo = gamma_floor_deg      # bound arrival: aerobrakes from floor
    if r_ceil == 2:
        if r_floor == 2:
            land = gamma_floor_deg    # everything in the envelope lands
        else:
            land = edge(gamma_floor_deg, gamma_ceil_deg, 2)
            if math.isfinite(cap_lo):
                cap_hi = land
    elif r_ceil == 1 and math.isfinite(cap_lo):
        cap_hi = gamma_ceil_deg       # captures all the way to the ceiling

    if math.isfinite(cap_lo) and math.isfinite(cap_hi):
        center = 0.5 * (cap_lo + cap_hi)
        res = run(center)
        hp_lo = vacuum_periapsis_alt_m(mu, radius, r0, v_entry,
                                       math.radians(cap_hi))
        hp_hi = vacuum_periapsis_alt_m(mu, radius, r0, v_entry,
                                       math.radians(cap_lo))
        return CorridorReport(body_id, v_entry, beta_kg_m2, skip, cap_lo,
                              cap_hi, land, center, res.peak_g,
                              res.peak_heating_w_m2, res.exit_apoapsis_m,
                              hp_lo, hp_hi)
    return CorridorReport(body_id, v_entry, beta_kg_m2, skip, cap_lo,
                          cap_hi, land, math.nan, math.nan, math.nan,
                          math.nan, math.nan, math.nan)


def advise(report: CorridorReport,
           gamma_planned_deg: float) -> tuple[str, float]:
    """One-liner verdict + margin (deg) for the entry HUD gauge (§1.6
    corridor advisor). Margin is signed: positive = inside the corridor
    (distance to the nearest edge), negative = outside by that much."""
    g = gamma_planned_deg
    if report.has_capture_band:
        lo, hi = report.gamma_capture_lo, report.gamma_capture_hi
        band = f"CAPTURE corridor {lo:.1f}-{hi:.1f} deg"
        if g < lo:
            m = lo - g
            return (f"{band}, you are {m:.1f} deg shallow", -m)
        if g > hi:
            m = g - hi
            return (f"{band}, you are {m:.1f} deg steep", -m)
        m = min(g - lo, hi - g)
        return (f"{band}, you are GO ({m:.1f} deg margin)", m)
    if math.isfinite(report.gamma_land_limit):
        land = report.gamma_land_limit
        band = f"LAND corridor {land:.1f}+ deg"
        if g < land:
            m = land - g
            return (f"{band}, you are {m:.1f} deg shallow", -m)
        m = g - land
        return (f"{band}, you are GO ({m:.1f} deg margin)", m)
    return ("NO CORRIDOR — this entry can neither capture nor land",
            math.nan)


# ---------------------------------------------------------------------------
# TPS sizing

@dataclass(frozen=True, slots=True)
class TpsReport:
    peak_heating_w_m2: float      # f_rad-augmented stagnation peak estimate
    tps_class: str                # "bare" | "ablator" | "beyond"
    rating_w_m2: float            # shipped rating that covers it (inf=none)


def tps_required(body_id: str, v_entry: float, beta_kg_m2: float,
                 gamma_deg: float = 10.0,
                 nose_radius_m: float = 2.0) -> TpsReport:
    """Closed-form peak-heating estimate -> shipped TPS class.

    Peak q̇ on an Allen–Eggers ballistic path occurs at rho* =
    beta·sin(gamma)/(3·H_local), v* = v_E·e^(-1/6) (from §1.6's
    q̇ = k·sqrt(rho/r_n)·v³ and the A-E velocity law); rho* is solved
    self-consistently against the piecewise H_local of the §1.4b breakpoint
    tables, clamped at surface density if the path bottoms out first. The
    default gamma (10 deg, land-limit side) sizes the steep case —
    conservative, since q̇ grows with sqrt(sin gamma).

    Classes map to the game's shipped ratings (aphelion/main.py:70-71):
    bare ≤ 0.9 MW/m² (_BARE_HEAT_W_M2) < ablator ≤ 2.5 MW/m²
    (_CAPSULE_HEAT_W_M2) < beyond (Table 1.5 PICA/HEEET territory, not yet
    a shipped part — main.py would burn the stack up).
    """
    if gamma_deg <= 0.0:
        raise ValueError("entry flight-path angle must be positive")
    h_int = interface_altitude(body_id)
    if not math.isfinite(h_int):
        raise ValueError(f"{body_id} has no atmosphere (no entry heating)")
    target = beta_kg_m2 * math.sin(math.radians(gamma_deg)) / 3.0

    def excess(h: float) -> float:
        return density(body_id, h) - target / local_scale_height(body_id, h)

    if excess(0.0) <= 0.0:
        rho_star = density(body_id, 0.0)      # bottoms out before A-E peak
    else:
        lo, hi = 0.0, h_int                   # excess: + at surface, - at top
        for _ in range(60):
            mid = 0.5 * (lo + hi)
            if excess(mid) > 0.0:
                lo = mid
            else:
                hi = mid
        rho_star = density(body_id, 0.5 * (lo + hi))

    v_star = v_entry * _VSTAR_FRACTION
    q_peak = stagnation_heating_w_m2(body_id, rho_star, v_star,
                                     nose_radius_m)
    if q_peak <= BARE_HEAT_W_M2:
        return TpsReport(q_peak, "bare", BARE_HEAT_W_M2)
    if q_peak <= CAPSULE_HEAT_W_M2:
        return TpsReport(q_peak, "ablator", CAPSULE_HEAT_W_M2)
    return TpsReport(q_peak, "beyond", math.inf)


# ---------------------------------------------------------------------------
# downrange

def ballistic_range(body_id: str, mu: float, radius: float,
                    r0: float, v0: float, gamma0_rad: float,
                    beta_kg_m2: float, dt: float = 0.05) -> float:
    """Ground-track distance (m) from the entry state to touchdown, for
    landing-site prediction. Returns inf if the pass exits the atmosphere
    (aerocapture/skip) or never lands inside the integration horizon.

    fly_entry does not expose its trajectory, so this mirrors its
    integration scheme step for step (drag + inverse-square gravity, same
    dt, same termination rules) and accumulates the swept polar angle;
    downrange = radius * |Δtheta| (planar 2D ground track). Keep in
    lockstep with entry.fly_entry so verdicts agree.
    """
    h_int = interface_altitude(body_id)
    x, y = r0, 0.0
    vx = v0 * math.sin(gamma0_rad)
    vy = v0 * math.cos(gamma0_rad)
    if gamma0_rad > 0.0:
        vx = -abs(vx)                      # entries descend
    t = 0.0
    in_atmo = False
    theta = 0.0

    while t < 3_600.0:
        r = math.hypot(x, y)
        h = r - radius
        v = math.hypot(vx, vy)
        rho = density(body_id, h)
        if rho > 0.0:
            in_atmo = True
            decel = 0.5 * rho * v * v / beta_kg_m2
            if v > 0.0:
                vx -= decel * vx / v * dt
                vy -= decel * vy / v * dt
        elif in_atmo and h > h_int:
            return math.inf                # exited: aerocapture, not landing

        g = mu / (r * r)
        vx -= g * x / r * dt
        vy -= g * y / r * dt
        theta += (x * vy - y * vx) / (r * r) * dt
        x += vx * dt
        y += vy * dt
        t += dt

        if (h < 5_000.0 and v < 300.0) or h <= 0.0:
            return radius * abs(theta)     # fly_entry's "landed" rules

    return math.inf
