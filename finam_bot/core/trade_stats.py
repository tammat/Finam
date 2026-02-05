from dataclasses import dataclass, field
from typing import List


@dataclass
class TradeStats:
    trades: int = 0
    wins: int = 0
    losses: int = 0
    pnl_history: List[float] = field(default_factory=list)
    equity_curve: List[float] = field(default_factory=list)

    def on_trade_exit(self, pnl: float, equity: float):
        self.trades += 1
        self.pnl_history.append(pnl)
        self.equity_curve.append(equity)

        if pnl > 0:
            self.wins += 1
        else:
            self.losses += 1

    @property
    def winrate(self) -> float:
        if self.trades == 0:
            return 0.0
        return self.wins / self.trades

    @property
    def expectancy(self) -> float:
        if not self.pnl_history:
            return 0.0
        return sum(self.pnl_history) / len(self.pnl_history)

    @property
    def max_drawdown(self) -> float:
        peak = self.equity_curve[0] if self.equity_curve else 0
        max_dd = 0.0

        for equity in self.equity_curve:
            if equity > peak:
                peak = equity
            dd = peak - equity
            if dd > max_dd:
                max_dd = dd

        return max_dd
