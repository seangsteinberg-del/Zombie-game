"""Ephemeris: build the live FrameTree from the validated content pack
(13 §3.6: planets and moons are permanently on rails from their 03 epoch
elements; per-frame positions are memoized in FrameTree).
"""

from __future__ import annotations

import math

from aphelion.content.loader import ContentDB, default_data_dir, load_packs
from aphelion.content.validate import validate
from aphelion.sim.orbits.frames import Body, FrameTree
from aphelion.sim.orbits.kepler import Elements


def _depth(bodies: dict[str, dict], item_id: str) -> int:
    d = 0
    cur = bodies[item_id]
    while cur["parent"] is not None:
        d += 1
        cur = bodies[cur["parent"]]
    return d


def build_frame_tree(db: ContentDB) -> FrameTree:
    bodies = db.bodies
    tree = FrameTree()
    for item_id in sorted(bodies, key=lambda i: (_depth(bodies, i), i)):
        raw = bodies[item_id]
        el_raw = raw.get("elements")
        elements = None
        if el_raw is not None:
            # Two-body reduction: the orbit's mu is parent + body. For planets
            # the correction is ppm-level; for binary-class pairs it is the
            # difference between right and 6% wrong (Pluto-Charon's real
            # 6.387 d period needs mu_total, not mu_Pluto alone).
            mu_parent = bodies[raw["parent"]]["mu_m3s2"] + raw["mu_m3s2"]
            elements = Elements(
                mu=mu_parent,
                alpha=1.0 / el_raw["a_m"],
                e=el_raw["e"],
                varpi=el_raw["lon_peri_rad"],
                tau=el_raw["t_peri_s"],
                s=float(el_raw["sense"]),
            )
        soi = raw["soi_m"]
        tree.add(Body(
            body_id=item_id,
            mu=raw["mu_m3s2"],
            radius=raw["radius_m"],
            parent=raw["parent"],
            elements=elements,
            soi_radius=math.inf if soi is None else float(soi),
        ))
    return tree


def load_solar_system() -> tuple[ContentDB, FrameTree]:
    """Load + validate the data packs and build the frame tree."""
    db = load_packs(default_data_dir())
    validate(db)
    return db, build_frame_tree(db)
