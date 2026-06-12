"""Docking topology rules (06 §3.3): androgynous ports mate within a
size class only (E8), capture limits with the bounce/damage ladder,
magnetic soft-capture doubling, and the across-the-joint burn load
check (Build B: 103 kN through a DK-L, would fail a DK-S).
"""

from __future__ import annotations

PORTS = {
    "S": {"passage_m": 0.8, "rating_kn": 60.0, "close_ms": 0.10},
    "B": {"passage_m": 1.27, "rating_kn": 150.0, "close_ms": 0.10,
          "needs_arm": True},
    "L": {"passage_m": 3.0, "rating_kn": 800.0, "close_ms": 0.05,
          "fluid": True},
}
LATERAL_MAX_M = 0.1
ANGLE_MAX_DEG = 5.0
DAMAGE_MS = 0.5


def can_mate(size_a: str, size_b: str) -> bool:
    """E8: sizes must match; androgynous within a class."""
    return size_a == size_b and size_a in PORTS


def capture(size: str, close_ms: float, lateral_m: float = 0.0,
            angle_deg: float = 0.0, magnetic: bool = False) -> str:
    """captured | bounce (at 0.5× closing speed) | damage (> 0.5 m/s)."""
    lim = PORTS[size]
    mult = 2.0 if magnetic else 1.0
    if close_ms > DAMAGE_MS:
        return "damage"
    if (close_ms <= lim["close_ms"] * mult
            and lateral_m <= LATERAL_MAX_M * mult
            and angle_deg <= ANGLE_MAX_DEG * mult):
        return "captured"
    return "bounce"


def burn_load_ok(size: str, payload_t: float, a_ms2: float,
                 derate: float = 1.0) -> tuple[bool, float]:
    """Burns while docked load the port joint: L = m·a (06 §2.8a across
    the docking joint). `derate` 0.5 under W6 wobble."""
    load_kn = payload_t * a_ms2
    return load_kn <= PORTS[size]["rating_kn"] * derate, load_kn
