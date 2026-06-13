"""Ship's stores & habitability, rolled up from a flying stack's parts
(08 §1/§3). A pure summary of what a craft actually carries for its crew:
provisioned crew-days of consumables, pressurized volume and berths,
on-board greenhouse closure, and cargo capacity. Feeds the interior LIFE
SUPPORT / STORES panel and the builder's habitability readout.

The single source of truth is the part data itself: crew tables carry an
[crew].endurance_days (the consumables stocked per seat), [hab] tables carry
pressurized volume / sleeps / grow area, and cargo bays carry cargo_t /
cells. Nothing here is invented — it sums the catalog.
"""

from __future__ import annotations

from aphelion.sim.habitat.food import AREA_FULL_DIET_M2
from aphelion.sim.habitat.lsc import FOOD_KG_DAY, O2_KG_DAY, WATER_KG_DAY


def manifest(parts: list[dict], crew_n: int) -> dict:
    """Roll a list of part-spec dicts into the stores summary for `crew_n`
    souls aboard. crew_days = Σ(seat capacity × endurance_days)."""
    crew_days = 0.0
    seats = berths = labs = cargo_cells = 0
    volume = grow_m2 = cargo_t = 0.0
    for p in parts:
        hab = p.get("hab") or {}
        crew = p.get("crew") or {}
        cap = int(crew.get("capacity", 0) or 0)
        seats += cap
        crew_days += cap * float(crew.get("endurance_days", 0.0) or 0.0)
        berths += int(hab.get("sleeps", 0) or 0)
        volume += float(hab.get("v_press_m3", 0.0) or 0.0)
        grow_m2 += float(hab.get("grow_m2", 0.0) or 0.0)
        if hab.get("lab"):
            labs += 1
        cargo_t += float(p.get("cargo_t", 0.0) or 0.0)
        cargo_cells += int(p.get("cargo_cells", 0) or 0)

    n = max(1, crew_n)
    # an on-board greenhouse grows a fraction of the diet (08 §3.5 anchor of
    # 40 m²/crew for a full closed diet); that share stops drawing the
    # stocked food, so the carried food lasts proportionally longer
    food_closure = (min(0.95, grow_m2 / (AREA_FULL_DIET_M2 * n))
                    if grow_m2 > 0.0 else 0.0)
    daily_kg = {
        "O2": O2_KG_DAY * crew_n,
        "Water": WATER_KG_DAY * crew_n,
        "Food": FOOD_KG_DAY * crew_n * (1.0 - food_closure),
    }
    # endurance: consumables run for crew_days/crew (O2 & water govern); the
    # farm extends the FOOD line specifically, reported separately
    days = crew_days / n
    food_days = days / max(0.05, 1.0 - food_closure)
    return {
        "crew_n": crew_n, "seats": seats, "crew_days": crew_days,
        "days": days, "food_days": food_days,
        "berths": berths, "volume_m3": volume, "vol_per_crew": volume / n,
        "grow_m2": grow_m2, "food_closure": food_closure, "labs": labs,
        "cargo_t": cargo_t, "cargo_cells": cargo_cells,
        "daily_kg": daily_kg,
    }


def from_vessel(vessel, crew_n: int) -> dict:
    """Convenience: pull the part specs off a Vessel (rows + .part)."""
    parts = []
    for r in getattr(vessel, "rows", []):
        try:
            parts.append(vessel.part(r))
        except Exception:
            continue
    return manifest(parts, crew_n)
