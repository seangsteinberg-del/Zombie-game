"""Chunk H (depth update): onboarding that survives — multi-rail tutorial
with real completion predicates, save/restore of the rail position, and
the rail hand-off chain (first flight → nodes → docking → bases)."""

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from aphelion.ui.tutorial import (RAIL_BUILDERS, first_flight_tutorial,
                                  next_rail, restore_rail)

BASE_STATE = dict(builder_open=False, stack_launchable=False, in_orbit=False,
                  warp_idx=0, apo_m=0.0, moon_leg=False, frame="",
                  moon_paid=False)


def test_step_one_needs_a_launchable_stack_not_an_open_builder():
    tut = first_flight_tutorial()
    s = dict(BASE_STATE)
    s["builder_open"] = True               # the OLD bug: this completed it
    assert not tut.update(s)
    assert tut.index == 0
    s["stack_launchable"] = True
    assert tut.update(s)
    assert tut.index == 1


def test_final_step_completes_when_the_moon_pays():
    tut = first_flight_tutorial()
    tut.index = len(tut.steps) - 1
    s = dict(BASE_STATE)
    assert not tut.update(s)               # the OLD bug: lambda s: False
    s["moon_paid"] = True
    assert tut.update(s)
    assert tut.completed


def test_rail_chain_orders_first_node_dock_base():
    done = set()
    seen = []
    while True:
        tut = next_rail(done)
        if tut is None:
            break
        seen.append(tut.rail)
        done.add(tut.rail)
    assert seen == ["first", "node", "dock", "base"]


def test_restore_rail_roundtrip():
    tut = next_rail({"first"})             # the node rail, step 1
    tut.index = 1
    tut.visible = False
    state = {"rail": tut.rail, "index": tut.index,
             "visible": tut.visible, "done": sorted(tut.done_rails)}
    back = restore_rail(state)
    assert back.rail == "node"
    assert back.index == 1
    assert back.visible is False
    assert back.done_rails == {"first"}
    # legacy save (no state) starts rail 1 at the top
    legacy = restore_rail(None)
    assert legacy.rail == "first" and legacy.index == 0


def test_every_rail_step_has_a_satisfiable_predicate():
    """No step may be a lambda s: False — every objective must be
    completable from a state dict."""
    keys = dict(BASE_STATE, node_placed=True, node_armed=True,
                node_executed=True, fleet_two=True, prox_open=True,
                docked=True, landed_surface=True, base_founded=True,
                base_producing=True, stack_launchable=True, in_orbit=True,
                warp_idx=3, apo_m=2e6, moon_leg=True, frame="core:moon",
                moon_paid=True)
    for name, build in RAIL_BUILDERS.items():
        tut = build()
        for step in tut.steps:
            assert step.done(keys), (name, step.text)
