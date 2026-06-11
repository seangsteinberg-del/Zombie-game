"""Comms light-lag and teleoperation effectiveness (92-16 / 05 §3.4).

RTT is geometry over c. Teleop effectiveness follows the canon table
(Lunokhod-anchored): eta = 1/(1 + RTT/26 s) reproduces the 05 rows —
Earth->Moon 2.6 s -> 0.91 (workable), Earth->Mars best 6.2 min -> 0.063
(useless; the physics itself forces local autonomy at Mars and beyond).
"""

from __future__ import annotations

import math

from aphelion.core.units import C_LIGHT

TELEOP_TAU_S = 26.0


def rtt_seconds(distance_m: float) -> float:
    return 2.0 * distance_m / C_LIGHT


def teleop_effectiveness(rtt_s: float) -> float:
    """eta in [0,1]: fraction of hands-on work rate a remote operator
    achieves at this round-trip time (05 §3.4 canon fit)."""
    return 1.0 / (1.0 + rtt_s / TELEOP_TAU_S)


def distance_between(tree, body_a: str, body_b: str, t: float) -> float:
    ax, ay, _, _ = tree.state_in_root(body_a, t)
    bx, by, _, _ = tree.state_in_root(body_b, t)
    return math.hypot(ax - bx, ay - by)


def teleop_eta_between(tree, operator_body: str, site_body: str,
                       t: float) -> float:
    return teleop_effectiveness(
        rtt_seconds(distance_between(tree, operator_body, site_body, t)))
