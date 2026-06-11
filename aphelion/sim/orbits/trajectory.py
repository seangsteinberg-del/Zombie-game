"""Patched-conic trajectory prediction across SOI transitions (01 §3.7:
the node planner draws the resulting trajectory across up to 5 SOI
transitions ahead; 13 §3.8 owns the crossing machinery).

A trajectory is a list of legs; each leg is one conic in one frame. The
chain re-expresses state at each crossing exactly as the live sim will
(subtract/add body state at the crossing instant, refit elements) — the
planner and reality share the same math by construction.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from aphelion.sim.orbits.frames import FrameTree
from aphelion.sim.orbits.kepler import (
    Elements,
    elements_to_state,
    state_to_elements,
)
from aphelion.sim.orbits.soi import predict_entry, predict_exit

MAX_TRANSITIONS = 5     # binding (01 §3.7)


@dataclass(frozen=True, slots=True)
class TrajectoryLeg:
    frame_id: str
    elements: Elements
    t_start: float
    t_end: float            # crossing time, or t_start + horizon
    end_reason: str         # "soi_exit" | "soi_entry:<body>" | "horizon"


def predict_trajectory(tree: FrameTree, frame_id: str, elements: Elements,
                       t0: float, horizon: float,
                       max_transitions: int = MAX_TRANSITIONS,
                       ) -> list[TrajectoryLeg]:
    """Chain conics from (frame, elements, t0) until the horizon or the
    transition budget is exhausted."""
    legs: list[TrajectoryLeg] = []
    t = t0
    t_end_total = t0 + horizon
    cur_frame = frame_id
    cur_el = elements

    for _ in range(max_transitions + 1):
        remaining = t_end_total - t
        if remaining <= 0.0:
            break
        frame_body = tree.body(cur_frame)

        # earliest exit from the current frame's SOI
        exit_cross = predict_exit(cur_el, frame_body.soi_radius, cur_frame,
                                  t, remaining)
        # earliest entry into any child SOI
        entry_cross = None
        for child_id in tree.children(cur_frame):
            child = tree.body(child_id)
            if not child.has_soi or child.elements is None:
                continue
            c = predict_entry(cur_el, child.elements, child.soi_radius,
                              child_id, t, remaining)
            if c is not None and (entry_cross is None
                                  or c.t_cross < entry_cross.t_cross):
                entry_cross = c

        crossing = None
        if exit_cross is not None and entry_cross is not None:
            crossing = exit_cross if exit_cross.t_cross < entry_cross.t_cross else entry_cross
        else:
            crossing = exit_cross or entry_cross

        if crossing is None:
            legs.append(TrajectoryLeg(cur_frame, cur_el, t, t_end_total, "horizon"))
            return legs

        t_cross = crossing.t_cross
        state = elements_to_state(cur_el, t_cross)
        if crossing.entering:
            child_id = crossing.body_id
            new_state = tree.to_child_frame(state, child_id, t_cross)
            new_frame = child_id
            reason = f"soi_entry:{child_id}"
        else:
            parent = frame_body.parent
            if parent is None:
                legs.append(TrajectoryLeg(cur_frame, cur_el, t, t_end_total, "horizon"))
                return legs
            new_state = tree.to_parent_frame(state, cur_frame, t_cross)
            new_frame = parent
            reason = "soi_exit"

        legs.append(TrajectoryLeg(cur_frame, cur_el, t, t_cross, reason))
        cur_el = state_to_elements(*new_state, t_cross, tree.body(new_frame).mu)
        cur_frame = new_frame
        t = t_cross

    return legs
