"""Program economy (12 §3/§4): Act 1-2 funding — cash, launch costs,
contracts with deadlines and payouts. Mid-game the material ledger takes
over and money fades to a triumph indicator (DECISIONS F33); this module
deliberately stays small.
"""

from __future__ import annotations

from dataclasses import dataclass, field


# -- hardware pricing (depth update: replaces the flat $/ton placeholder) -----
# Tier reflects manufacturing maturity: a T3 vacuum engine is NOT priced
# like T0 sheet metal. Propellant is cheap; hardware is not.

_TIER_MULT = {"T0": 1.0, "T1": 1.6, "T2": 2.6, "T3": 4.0, "T4": 6.5}
_PROP_USD_PER_T = 120_000.0          # bulk cryo/storable, padded for ops


def part_cost_usd(part: dict) -> float:
    """2049 USD unit cost of one DRY part, from its real data."""
    tier = _TIER_MULT.get(part.get("tier", "T0"), 1.0)
    kind = part.get("type", "structure")
    mass_t = float(part.get("mass_t", 1.0))
    if kind == "engine":
        eng = part["engine"]
        # thrust buys size, Isp buys precision engineering
        base = 3.0e6 + 4_500.0 * float(eng["thrust_kN"]) ** 0.85
        base *= 1.0 + max(0.0, float(eng["isp_s"]) - 300.0) / 250.0
    elif kind == "tank":
        base = 0.4e6 + 0.25e6 * float(part["tank"]["capacity_t"]) ** 0.8
    elif kind == "crew":
        cap = float(part.get("crew", {}).get("capacity", 2))
        base = 9.0e6 + 4.0e6 * cap
    else:                              # structure / payload / probe
        base = 1.2e6 + 1.4e6 * mass_t
    return base * tier


def vessel_cost_usd(vessel) -> float:
    """Full launch price: sum of unit part costs + propellant load."""
    hardware = sum(part_cost_usd(vessel.part(r)) for r in vessel.rows)
    prop_t = (vessel.total_mass_kg() - vessel.dry_mass_kg()) / 1_000.0
    return hardware + prop_t * _PROP_USD_PER_T


@dataclass(slots=True)
class Contract:
    contract_id: str
    description: str
    payout: float
    deadline_s: float
    completed_t: float | None = None
    failed: bool = False


@dataclass(slots=True)
class Program:
    """The player's program ledger (2049 USD)."""
    funds: float
    contracts: list[Contract] = field(default_factory=list)
    history: list[tuple[float, str, float]] = field(default_factory=list)

    def spend(self, t: float, amount: float, what: str) -> bool:
        if amount > self.funds:
            return False
        self.funds -= amount
        self.history.append((t, what, -amount))
        return True

    def earn(self, t: float, amount: float, what: str) -> None:
        self.funds += amount
        self.history.append((t, what, amount))

    def offer(self, c: Contract) -> None:
        self.contracts.append(c)

    def complete(self, t: float, contract_id: str) -> bool:
        for c in self.contracts:
            if c.contract_id == contract_id and c.completed_t is None and not c.failed:
                if t > c.deadline_s:
                    c.failed = True
                    return False
                c.completed_t = t
                self.earn(t, c.payout, f"contract:{contract_id}")
                return True
        return False

    def expire_overdue(self, t: float) -> list[str]:
        failed = []
        for c in self.contracts:
            if c.completed_t is None and not c.failed and t > c.deadline_s:
                c.failed = True
                failed.append(c.contract_id)
        return failed

    @property
    def runway_report(self) -> str:
        return f"funds ${self.funds:,.0f}; {len([c for c in self.contracts if c.completed_t])} contracts done"
