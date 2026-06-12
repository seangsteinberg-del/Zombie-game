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


# ---- stack-level port survey (the E8 pre-flight on REAL rows) -----------------
_PREF = ("L", "B", "S")        # mate through the biggest common passage


def stack_ports(vessel) -> set[str]:
    """Port sizes a stack actually carries (DK-* parts on its rows)."""
    return {vessel.part(r)["port"]["size"] for r in vessel.rows
            if "port" in vessel.part(r)}


def has_arm(vessel) -> bool:
    return any(vessel.part(r).get("robot_arm") for r in vessel.rows)


def mate_plan(chaser, target) -> tuple[str | None, bool, str]:
    """(size, soft_assist, refusal_note). E8: ports mate within a size
    class only. A stack with no DK part falls back to its integral S
    probe-and-drogue (early capsules keep docking). Berthing port B
    needs a robot arm on either side — and an arm present anywhere
    doubles capture tolerances on every size (it snags you)."""
    a = stack_ports(chaser) or {"S"}
    b = stack_ports(target) or {"S"}
    common = a & b
    arm = has_arm(chaser) or has_arm(target)
    if "B" in common and not arm:
        common.discard("B")
        if not common:
            return None, False, ("berthing port B needs a robot arm "
                                 "on either vessel")
    for s in _PREF:
        if s in common:
            return s, arm, ""
    return None, False, (f"E8: no matching port — chaser has "
                         f"{'/'.join(sorted(a))}, target has "
                         f"{'/'.join(sorted(b))}")
