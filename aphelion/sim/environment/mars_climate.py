"""Mars dust seasons & climate (03 S-9/S-9a, DECISIONS C24): areocentric
solar longitude Ls from the real eccentric orbit, the pre-rolled dust-storm
timeline (regional + the once-per-Mars-year global roll), panel-soiling
optical depth, seasonal site pressure, and the ±50%-clamped atmospheric
density multiplier f_climate that 01's corridor planning consumes.

Deterministic: storm rolls hash off one campaign seed per Mars year.
"""

from __future__ import annotations

import math

SOL_S = 88_775.0
MARS_YEAR_SOLS = 668.6
MARS_YEAR_S = MARS_YEAR_SOLS * SOL_S
E_MARS = 0.0934
# perihelion occurs at Ls = 251°; choose t_peri so Ls(0) lands in northern
# spring (Ls ≈ 0 near epoch is fine at game fidelity)
T_PERI_S = -0.30 * MARS_YEAR_S


def mean_anomaly(t: float) -> float:
    return 2 * math.pi * ((t - T_PERI_S) / MARS_YEAR_S % 1.0)


def true_anomaly(t: float) -> float:
    m = mean_anomaly(t)
    # equation of center to O(e²) — plenty at e = 0.0934
    return m + 2 * E_MARS * math.sin(m) + 1.25 * E_MARS ** 2 * math.sin(2 * m)


def ls_deg(t: float) -> float:
    """Areocentric solar longitude: Ls = (ν + 251°) mod 360 (S-9)."""
    return (math.degrees(true_anomaly(t)) + 251.0) % 360.0


def tau_base(ls: float) -> float:
    return 0.3 if ls < 180.0 else 0.5


class MarsWeather:
    """Pre-rolled storm timeline. Global storms: one roll per Mars year at
    Ls = 200°±30°, p = 0.33, all sectors τ → U(4,9), duration U(60,100)
    sols, e-fold decay 25 sols. Regional storms [SIMPLIFIED here to a
    per-year count over the 18 Mars sectors] during Ls 180-330."""

    def __init__(self, seed: int) -> None:
        self._base_seed = int(seed) & 0x7FFFFFFF
        self._years: dict[int, dict] = {}

    def _year(self, my: int) -> dict:
        got = self._years.get(my)
        if got is not None:
            return got
        import numpy as np
        seed = ((my * 40_503_481) ^ self._base_seed) & 0xFFFFFFFF
        rng = np.random.default_rng(seed)
        year: dict = {"global": None, "regional": []}
        # global roll at Ls ≈ 200° of this Mars year
        if rng.random() < 0.33:
            ls_onset = 200.0 + rng.uniform(-30.0, 30.0)
            t_on = (my + ls_onset / 360.0) * MARS_YEAR_S   # uniform-Ls approx
            year["global"] = {
                "t_on": t_on,
                "tau_peak": float(rng.uniform(4.0, 9.0)),
                "dur_s": float(rng.uniform(60.0, 100.0)) * SOL_S,
                "decay_s": 25.0 * SOL_S,
            }
        # regional storms: expected ~0.004/sol/sector over the dusty half
        n_regional = rng.poisson(0.004 * MARS_YEAR_SOLS / 2.0 * 18)
        for _ in range(int(n_regional)):
            ls_onset = float(rng.uniform(180.0, 330.0))
            year["regional"].append({
                "sector_idx": int(rng.integers(1, 19)),
                "t_on": (my + ls_onset / 360.0) * MARS_YEAR_S,
                "tau_peak": float(rng.uniform(2.0, 4.0)),
                "dur_s": float(rng.uniform(5.0, 40.0)) * SOL_S,
            })
        self._years[my] = year
        return year

    def tau(self, t: float, sector_idx: int = 0) -> float:
        """Optical depth at t for a sector (0 = body-wide max)."""
        tau = tau_base(ls_deg(t))
        for my in (int(t / MARS_YEAR_S) - 1, int(t / MARS_YEAR_S)):
            if my < 0:
                continue
            yr = self._year(my)
            g = yr["global"]
            if g is not None:
                if g["t_on"] <= t <= g["t_on"] + g["dur_s"]:
                    ramp = min(1.0, (t - g["t_on"]) / (10.0 * SOL_S))
                    tau = max(tau, g["tau_peak"] * ramp)
                elif t > g["t_on"] + g["dur_s"]:
                    dec = math.exp(-(t - g["t_on"] - g["dur_s"])
                                   / g["decay_s"])
                    tau = max(tau, g["tau_peak"] * dec)
            for st in yr["regional"]:
                if sector_idx in (0, st["sector_idx"]) \
                        and st["t_on"] <= t <= st["t_on"] + st["dur_s"]:
                    ramp = min(1.0, (t - st["t_on"]) / (2.0 * SOL_S))
                    tau = max(tau, st["tau_peak"] * ramp)
        return tau

    def global_storm_active(self, t: float) -> bool:
        for my in (int(t / MARS_YEAR_S) - 1, int(t / MARS_YEAR_S)):
            if my < 0:
                continue
            g = self._year(my)["global"]
            if g is not None and g["t_on"] <= t <= g["t_on"] + g["dur_s"]:
                return True
        return False


def f_dust(tau: float, olympus: bool = False) -> float:
    """Solar transmission through dust: max(0.04, exp(−0.45·τ));
    Olympus Mons summit sits above the dust (exponent ×0.5, AN-14)."""
    k = 0.225 if olympus else 0.45
    return max(0.04, math.exp(-k * tau))


def p_site_factor(t: float) -> float:
    """Seasonal surface-pressure swing (S-9): ±15% around datum."""
    return 1.0 + 0.15 * math.sin(2 * math.pi * (ls_deg(t) - 250.0) / 360.0)


def f_climate(h_m: float, t: float, c_sun: float = 1.0,
              tau: float | None = None) -> float:
    """C24 contract: density multiplier for ρ_Mars(h), clamped [0.50, 1.50].
    Consumed at plan time AND execution by EDL/aerobraking."""
    ls = ls_deg(t)
    tau_now = tau if tau is not None else tau_base(ls)
    h_km = h_m / 1_000.0
    f_season = 1.0 + 0.15 * math.sin(2 * math.pi * (ls - 250.0) / 360.0)
    f_dustheat = 1.0 + 0.05 * tau_now * (0.5 + h_km / 100.0)
    f_diurnal = 1.0 - 0.20 * (1.0 - c_sun) * min(1.0, h_km / 100.0)
    return max(0.50, min(1.50, f_season * f_dustheat * f_diurnal))


def soiling_rate_per_sol(storm: bool) -> float:
    """Panel soiling: −0.2%/sol clear, −2%/sol storm (S-9)."""
    return 0.02 if storm else 0.002
