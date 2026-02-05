from dataclasses import dataclass, field
from typing import List


@dataclass
class EquityPoint:
    bar: int
    equity: float
    pnl: float
    reason: str


@dataclass
class EquityTracker:
    start_equity: float
    equity: float = field(init=False)
    curve: List[EquityPoint] = field(default_factory=list)

    def __post_init__(self):
        self.equity = self.start_equity

    def on_trade_exit(self, bar: int, pnl: float, reason: str):
        self.equity += pnl
        self.curve.append(
            EquityPoint(
                bar=bar,
                equity=self.equity,
                pnl=pnl,
                reason=reason,
            )
        )

    def last(self) -> float:
        return self.equity
