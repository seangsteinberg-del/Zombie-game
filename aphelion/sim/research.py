"""Research system (11): two currencies — Science (exploration) and
Engineering Data (operations) — spent on tech-tree nodes from the content
pack. The loader never hides locked items (13 §6: tiers gate DATA, not
engine features).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from aphelion.content.loader import ContentDB


@dataclass(slots=True)
class ResearchState:
    science: float = 0.0
    eng_data: float = 0.0
    unlocked: set[str] = field(default_factory=set)
    history: list[tuple[float, str]] = field(default_factory=list)

    def earn_science(self, points: float) -> None:
        self.science += points

    def earn_eng_data(self, points: float) -> None:
        self.eng_data += points

    def can_unlock(self, db: ContentDB, node_id: str) -> bool:
        node = db.tech.get(node_id)
        if node is None or node_id in self.unlocked:
            return False
        if not all(p in self.unlocked for p in node["prereqs"]):
            return False
        return self.science >= node.get("cost_sci", 0.0) and \
            self.eng_data >= node.get("cost_ed", 0.0)

    def unlock(self, db: ContentDB, node_id: str, t: float = 0.0) -> bool:
        if not self.can_unlock(db, node_id):
            return False
        node = db.tech[node_id]
        self.science -= node.get("cost_sci", 0.0)
        self.eng_data -= node.get("cost_ed", 0.0)
        self.unlocked.add(node_id)
        self.history.append((t, node_id))
        return True

    def part_available(self, db: ContentDB, part_id: str) -> bool:
        """A part is available iff some unlocked node lists it, or no node
        gates it at all (T0 base set)."""
        gated = False
        for node_id, node in db.tech.items():
            if part_id in node.get("unlocks", []):
                gated = True
                if node_id in self.unlocked:
                    return True
        return not gated
