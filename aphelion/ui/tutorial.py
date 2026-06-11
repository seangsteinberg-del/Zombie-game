"""Onboarding (12 §5.8 — the first minutes, scripted-ish): a sequenced
objective rail whose steps complete from REAL game state, not timers.
F1 dismisses/restores.
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
    return Tutorial(steps=[
        Step("Press . (period) to engage time warp",
             lambda s: s["warp_idx"] > 0),
        Step("Press X to burn prograde — raise your apoapsis past 1,000 km",
             lambda s: s["apo_m"] > 1.0e6),
        Step("Keep raising apoapsis until a MOON leg appears in your "
             "predicted trajectory (shift+X = 100 m/s)",
             lambda s: s["moon_leg"]),
        Step("Warp ahead and ride the handoff into the Moon's SOI",
             lambda s: s["frame"] == "core:moon"),
        Step("Contract paid! Burn retrograde at periapsis if you want to "
             "stay; TAB tours the system. Fly safe, Director.",
             lambda s: False),
    ])
