"""Onboarding (12 §5.8 — guided, not scripted): sequenced objective rails
whose steps complete from REAL game state, not timers. The depth update
makes the rail SURVIVE (its index persists in saves), COMPLETE (every
step has a real predicate), and CONTINUE (after the first flight, new
rails teach nodes, docking, and bases as the campaign demands them).
H dismisses/restores.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable


@dataclass(slots=True)
class Step:
    text: str
    done: Callable[[dict], bool]


@dataclass(slots=True)
class Tutorial:
    steps: list[Step]
    index: int = 0
    visible: bool = True
    completed: bool = False
    rail: str = "first"
    done_rails: set = field(default_factory=set)

    def update(self, state: dict) -> bool:
        """Advance on completion; returns True the frame a step completes."""
        if self.completed or self.index >= len(self.steps):
            self.completed = True
            return False
        if self.steps[self.index].done(state):
            self.index += 1
            if self.index >= len(self.steps):
                self.completed = True
            return True
        return False

    @property
    def current_text(self) -> str:
        if self.completed:
            return ""
        return f"OBJECTIVE {self.index + 1}/{len(self.steps)}: " \
               f"{self.steps[self.index].text}"


def first_flight_tutorial() -> Tutorial:
    """Rail 1: pad to the Moon. Step 1 stays visible while you BUILD (it
    completes on a launchable stack, not on opening the builder), and the
    farewell step completes when the Moon contract pays."""
    return Tutorial(steps=[
        Step("Press B and assemble a rocket — 2 boosters + XL tank, new "
             "stage (S), vacuum engine + M tank + capsule. Then L to launch",
             lambda s: s.get("stack_launchable", False)),
        Step("Fly it to orbit: SPACE ignites, the autopilot flies the "
             "program — stage when called, C to circularize",
             lambda s: s["in_orbit"]),
        Step("Press . (period) to engage time warp",
             lambda s: s["in_orbit"] and s["warp_idx"] > 0),
        Step("Press X to burn prograde — raise your apoapsis past 1,000 km",
             lambda s: s["apo_m"] > 1.0e6),
        Step("Keep raising apoapsis until a MOON leg appears in your "
             "predicted trajectory (shift+X = 100 m/s)",
             lambda s: s["moon_leg"]),
        Step("Warp ahead and ride the handoff into the Moon's SOI",
             lambda s: s["frame"] == "core:moon"),
        Step("MOON REACHED — contract pays on the sweep. G lands when "
             "you're in LOW orbit; H hides this rail. Fly safe, Director.",
             lambda s: s.get("moon_paid", False)),
    ])


def node_tutorial() -> Tutorial:
    """Rail 2: the maneuver-node planner, taught after the Moon pays."""
    return Tutorial(steps=[
        Step("Time to plan like a program: press N to place a maneuver "
             "node on your orbit",
             lambda s: s.get("node_placed", False)),
        Step("Shape it: arrows set dv (CTRL = 1 m/s), [/] move it in time, "
             "P snaps to periapsis — then ENTER arms it",
             lambda s: s.get("node_armed", False)),
        Step("Press W to warp to the burn; it executes on time. P also "
             "opens the TRANSFER PLANNER for interplanetary windows.",
             lambda s: s.get("node_executed", False)),
    ])


def dock_tutorial() -> Tutorial:
    """Rail 3: rendezvous + the flown prox-ops approach."""
    return Tutorial(steps=[
        Step("Launch a SECOND vessel (B). The NAV panel shows range and "
             "closing rate to your nearest fleet-mate",
             lambda s: s.get("fleet_two", False)),
        Step("Burn until range < 100 km, then press E — you pay the "
             "velocity match and FLY the final approach",
             lambda s: s.get("prox_open", False)),
        Step("Arrow keys pulse RCS. Enter the circle under 2 m/s for soft "
             "capture, then ENTER hard-docks (A = pilot autopilot)",
             lambda s: s.get("docked", False)),
    ])


def base_tutorial() -> Tutorial:
    """Rail 4: land, found, industrialize."""
    return Tutorial(steps=[
        Step("Get your periapsis under 300 km at the Moon, press G, and "
             "FLY the powered descent (watch the BURN ladder)",
             lambda s: s.get("landed_surface", False)),
        Step("Press G again: FOUND A BASE — your tanks and crew become "
             "the colony",
             lambda s: s.get("base_founded", False)),
        Step("Press F2: build a drill + electrolyzer + solar wings, and "
             "watch the LOX bank fill. Banked propellant REFUELS landers.",
             lambda s: s.get("base_producing", False)),
    ])


RAIL_BUILDERS: dict[str, Callable[[], Tutorial]] = {
    "first": first_flight_tutorial,
    "node": node_tutorial,
    "dock": dock_tutorial,
    "base": base_tutorial,
}


def next_rail(done_rails: set[str]) -> Tutorial | None:
    """The campaign's next teachable moment, or None when schooled out."""
    for name, build in RAIL_BUILDERS.items():
        if name not in done_rails:
            tut = build()
            tut.rail = name
            tut.done_rails = set(done_rails)
            return tut
    return None


def restore_rail(state: dict | None) -> Tutorial:
    """Rebuild the saved rail at its saved step (rails survive loads)."""
    if not state:
        return first_flight_tutorial()
    done = set(state.get("done", []))
    tut = next_rail(done - {state.get("rail")})
    if tut is None or tut.rail != state.get("rail"):
        tut = next_rail(done) or first_flight_tutorial()
    tut.index = min(int(state.get("index", 0)), len(tut.steps))
    tut.completed = tut.index >= len(tut.steps)
    tut.visible = bool(state.get("visible", True))
    tut.done_rails = done
    return tut
