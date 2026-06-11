"""Program economy (12 §3/§4): Act 1-2 funding — cash, launch costs,
contracts with deadlines and payouts. Mid-game the material ledger takes
over and money fades to a triumph indicator (DECISIONS F33); this module
deliberately stays small.
"""

from __future__ import annotations

from dataclasses import dataclass, field


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
