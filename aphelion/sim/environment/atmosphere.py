"""Piecewise-exponential atmospheres (01 §3.11 / §4.4b, binding; 03
republishes these breakpoints verbatim).

rho(h) = rho_i * exp(-(h - h_i)/H_i), H_i = (h_i+1 - h_i)/ln(rho_i/rho_i+1)
between anchors; rho = 0 strictly above the last (interface) anchor. The
interface altitude is also the rails-warp lockout boundary.
"""

from __future__ import annotations

import math
from bisect import bisect_right

# body id -> list of (altitude_m, density_kg_m3); last anchor = interface
BREAKPOINTS: dict[str, list[tuple[float, float]]] = {
    "core:earth": [(0.0, 1.225), (25e3, 4.0e-2), (50e3, 1.03e-3),
                   (75e3, 4.0e-5), (100e3, 5.6e-7), (120e3, 2.2e-8),
                   (140e3, 3.9e-9)],
    "core:mars": [(0.0, 1.5e-2), (25e3, 2.5e-3), (50e3, 2.8e-4),
                  (75e3, 1.6e-5), (100e3, 1.0e-7), (125e3, 6e-9)],
    "core:venus": [(0.0, 65.0), (50e3, 1.6), (70e3, 9.2e-2),
                   (100e3, 5e-5), (130e3, 1e-7), (180e3, 2e-9)],
    "core:titan": [(0.0, 5.28), (75e3, 1.5e-1), (300e3, 1.7e-3),
                   (600e3, 4e-6), (850e3, 7e-8)],
    # gas giants: altitude relative to the 1-bar datum
    "core:jupiter": [(-100e3, 0.6), (0.0, 0.16), (200e3, 9e-5),
                     (500e3, 1.3e-9), (1000e3, 1e-13)],
    "core:saturn": [(-150e3, 0.5), (0.0, 0.19), (300e3, 1.2e-3),
                    (800e3, 2e-8), (1500e3, 1e-13)],
}


def interface_altitude(body_id: str) -> float:
    """Atmosphere interface (m); -inf for airless bodies (no lockout)."""
    bp = BREAKPOINTS.get(body_id)
    return bp[-1][0] if bp else -math.inf


def density(body_id: str, altitude_m: float) -> float:
    bp = BREAKPOINTS.get(body_id)
    if bp is None:
        return 0.0
    if altitude_m >= bp[-1][0]:
        return bp[-1][1] if altitude_m == bp[-1][0] else 0.0
    if altitude_m <= bp[0][0]:
        return bp[0][1]
    i = bisect_right([h for h, _ in bp], altitude_m) - 1
    h_i, rho_i = bp[i]
    h_j, rho_j = bp[i + 1]
    scale = (h_j - h_i) / math.log(rho_i / rho_j)
    return rho_i * math.exp(-(altitude_m - h_i) / scale)
