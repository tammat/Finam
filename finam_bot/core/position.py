# finam_bot/core/position.py

from dataclasses import dataclass
from typing import Optional


@dataclass
class Position:
    symbol: str
    side: str          # LONG / SHORT
    qty: int
    entry_price: float
    exit_price: Optional[float] = None

    def close(self, price: float) -> float:
        self.exit_price = price
        return self.pnl()

    def pnl(self) -> float:
        if self.exit_price is None:
            return 0.0

        if self.side == "LONG":
            return (self.exit_price - self.entry_price) * self.qty
        else:
            return (self.entry_price - self.exit_price) * self.qty
