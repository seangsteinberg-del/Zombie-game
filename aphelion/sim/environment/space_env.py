"""Space environment fields (03 S-4/S-8/S-13/S-14): the solar cycle,
SPE storm schedule, planetary radiation-belt field functions, conjunction
blackout geometry and comet activity. All deterministic — storm timelines
are pre-rolled from a named rng substream, never sampled at run time.

Formula IDs cite design/extracts/03-solar-system-buildspec.md.
"""

from __future__ import annotations

import math

YEAR = 365.25 * 86_400.0
# solar maxima (S-8a): ~2057 and 2068; epoch t=0 is 2049-01-01
T_SOLAR_MAX = 8.0 * YEAR
SOLAR_CYCLE = 11.0 * YEAR

R_E_KM = 6_371.0
R_J_KM = 71_492.0
R_S_KM = 58_232.0


def f_cycle(t: float) -> float:
    """GCR solar-cycle modulation: 0.65 at solar max, 1.35 at min (S-8a)."""
    f = 1.0 - 0.35 * math.cos(2 * math.pi * (t - T_SOLAR_MAX) / SOLAR_CYCLE)
    return min(1.35, max(0.65, f))


def gcr_msv_day(t: float) -> float:
    return 1.8 * f_cycle(t)


def spe_rate_per_year(t: float) -> float:
    """SPE Poisson rate λ(t): 4.0 events/yr at solar max, 0.5 at min."""
    return 0.5 + 3.5 * max(0.0, math.cos(2 * math.pi * (t - T_SOLAR_MAX)
                                         / SOLAR_CYCLE))


class SpeSchedule:
    """Pre-rolled solar-particle-event timeline (S-8b). Events generated
    lazily per epoch-year from a seeded substream; identical across
    save/load by construction. Dose at 1 AU: lognormal median 100 mSv,
    σ_ln = 1.2, cap 2,000 mSv, delivered over 6-48 h; scales 1/d²."""

    WARN_S = 45.0 * 60.0          # 30-60 min warning; fixed midpoint

    def __init__(self, seed: int) -> None:
        # per-year streams hash off the campaign-derived seed, so lazy
        # generation order never changes outcomes and saves need no state
        self._base_seed = int(seed) & 0x7FFFFFFF
        self._years: dict[int, list[tuple[float, float, float]]] = {}

    def _events_for_year(self, year: int) -> list[tuple[float, float, float]]:
        got = self._years.get(year)
        if got is not None:
            return got
        import numpy as np
        seed = ((year * 2_654_435_761) ^ self._base_seed) & 0xFFFFFFFF
        rng = np.random.default_rng(seed)
        t_mid = (year + 0.5) * YEAR
        lam = spe_rate_per_year(t_mid)
        n = rng.poisson(lam)
        events = []
        for _ in range(int(n)):
            t0 = (year + float(rng.random())) * YEAR
            dur = (6.0 + 42.0 * float(rng.random())) * 3_600.0
            dose = min(2_000.0, float(rng.lognormal(math.log(100.0), 1.2)))
            events.append((t0, dur, dose))
        events.sort()
        self._years[year] = events
        return events

    def active(self, t: float) -> tuple[float, float, float] | None:
        """The event in progress at t, if any: (t0, duration_s, dose_1au)."""
        for yr in (int(t / YEAR) - 1, int(t / YEAR)):
            for ev in self._events_for_year(max(0, yr)):
                if ev[0] <= t <= ev[0] + ev[1]:
                    return ev
        return None

    def warning(self, t: float) -> tuple[float, float, float] | None:
        """An event whose 45-min warning window contains t (flare seen,
        protons inbound — get to shelter)."""
        yr = int(t / YEAR)
        for ev in self._events_for_year(yr):
            if ev[0] - self.WARN_S <= t < ev[0]:
                return ev
        return None


def spe_distance_factor(d_au: float) -> float:
    return 1.0 / max(0.05, d_au) ** 2


def earth_belt_msv_day(r_km: float) -> float:
    """S-8c [SIMPLIFIED AP8/AE8] piecewise effective dose behind 5 g/cm²,
    geocentric radius in Earth radii: 0 @1.1 → 150 @1.6 → 10 @2.5 →
    50 @4.5 → 0 @8."""
    r = r_km / R_E_KM
    pts = [(1.1, 0.0), (1.6, 150.0), (2.5, 10.0), (4.5, 50.0), (8.0, 0.0)]
    if r <= pts[0][0] or r >= pts[-1][0]:
        return 0.0
    for (r0, d0), (r1, d1) in zip(pts, pts[1:]):
        if r0 <= r <= r1:
            return d0 + (d1 - d0) * (r - r0) / (r1 - r0)
    return 0.0


def jupiter_belt_msv_day(r_km: float) -> float:
    """DECISIONS A4: piecewise-exact log-linear through mission anchors.
    Io 36,000 · Europa 5,400 · Ganymede 160 · ~0 past 30 R_J."""
    r = r_km / R_J_KM
    if r <= 5.9:
        return 36_000.0
    if r <= 9.4:
        return 36_000.0 * math.exp(-(r - 5.9) / 1.845)
    if r <= 15.0:
        return 5_400.0 * math.exp(-(r - 9.4) / 1.591)
    if r <= 30.0:
        return 160.0 * math.exp(-(r - 15.0) / 1.605)
    return 0.0


def saturn_belt_msv_day(r_km: float) -> float:
    return 1.0 if r_km / R_S_KM < 8.0 else 0.0


def conjunction_blackout(obs_xy, sun_xy, tgt_xy, limit_deg: float = 1.0) -> bool:
    """S-4: blackout iff Sun-target angular separation seen from the
    observer < 1° AND the target is FARTHER than the Sun (superior
    conjunction only)."""
    sx, sy = sun_xy[0] - obs_xy[0], sun_xy[1] - obs_xy[1]
    tx, ty = tgt_xy[0] - obs_xy[0], tgt_xy[1] - obs_xy[1]
    ds = math.hypot(sx, sy)
    dt = math.hypot(tx, ty)
    if dt <= ds or ds == 0.0 or dt == 0.0:
        return False
    cosang = max(-1.0, min(1.0, (sx * tx + sy * ty) / (ds * dt)))
    return math.degrees(math.acos(cosang)) < limit_deg


def comet_activity(d_au: float) -> float:
    """S-13: A(d) = clamp((3/d)² − 1, 0, 8)."""
    return max(0.0, min(8.0, (3.0 / max(0.05, d_au)) ** 2 - 1.0))
