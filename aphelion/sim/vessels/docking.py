"""Docking, undocking, and propellant transfer (06 §3 / 13 §3.3: a docked
assembly is ONE entity whose parts are rows; docking is row-merge, undock
is row-split — save-format-trivial by construction).
"""

from __future__ import annotations

from aphelion.sim.vessels.vessel import PartRow, Vessel


def dock(a: Vessel, b: Vessel) -> Vessel:
    """Merge b's rows into a (a is the station/primary). Stage plans
    concatenate (a's stages first); fills carry over untouched."""
    offset = len(a.rows)
    a.rows.extend(b.rows)
    a.stage_plan.extend([[i + offset for i in s] for s in b.stage_plan])
    return a


def undock(a: Vessel, row_indices: list[int]) -> Vessel:
    """Split the given rows out of a into a new vessel. Stage plans are
    partitioned; indices are remapped on both sides."""
    going = set(row_indices)
    new_rows = [r for i, r in enumerate(a.rows) if i in going]
    keep_rows = [r for i, r in enumerate(a.rows) if i not in going]

    remap_keep = {}
    remap_go = {}
    ki = gi = 0
    for i in range(len(a.rows)):
        if i in going:
            remap_go[i] = gi
            gi += 1
        else:
            remap_keep[i] = ki
            ki += 1

    new_plan = []
    keep_plan = []
    for stage in a.stage_plan:
        gs = [remap_go[i] for i in stage if i in going]
        ks = [remap_keep[i] for i in stage if i not in going]
        if gs:
            new_plan.append(gs)
        if ks:
            keep_plan.append(ks)

    a.rows = keep_rows
    a.stage_plan = keep_plan
    return Vessel(a._db, new_rows, new_plan if new_plan else [list(range(len(new_rows)))],
                  cd_a_m2=a.cd_a_m2)


def tank_capacity_kg(vessel: Vessel, row: PartRow) -> float:
    tank = vessel.part(row).get("tank")
    return tank["capacity_t"] * 1_000.0 if tank else 0.0


def transfer_resource(src: Vessel, dst: Vessel, resource: str,
                      kg: float) -> float:
    """Move up to kg of a resource between vessels' tanks (depot refueling,
    05). Respects per-tank capacity and mixture membership. Returns kg
    actually moved."""
    available = 0.0
    for r in src.rows:
        available += r.fill.get(resource, 0.0)
    room = 0.0
    for r in dst.rows:
        tank = dst.part(r).get("tank")
        if not tank or resource not in tank["mixture"]:
            continue
        share = tank["mixture"][resource]
        cap = tank["capacity_t"] * 1_000.0 * share
        room += max(0.0, cap - r.fill.get(resource, 0.0))
    move = min(kg, available, room)
    if move <= 0.0:
        return 0.0

    left = move
    for r in src.rows:
        if left <= 0.0:
            break
        have = r.fill.get(resource, 0.0)
        take = min(have, left)
        if take > 0.0:
            r.fill[resource] = have - take
            left -= take
    left = move
    for r in dst.rows:
        if left <= 0.0:
            break
        tank = dst.part(r).get("tank")
        if not tank or resource not in tank["mixture"]:
            continue
        share = tank["mixture"][resource]
        cap = tank["capacity_t"] * 1_000.0 * share
        space = cap - r.fill.get(resource, 0.0)
        put = min(space, left)
        if put > 0.0:
            r.fill[resource] = r.fill.get(resource, 0.0) + put
            left -= put
    return move
