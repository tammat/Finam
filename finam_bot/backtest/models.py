from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Literal


Side = Literal["LONG", "SHORT"]


@dataclass(frozen=True)
class Candle:
    ts: Optional[int]  # можно epoch seconds, пока None/инт
    open: float
    high: float
    low: float
    close: float
    volume: float = 0.0


@dataclass
class Trade:
    symbol: str
    side: Side
    qty: float
    entry_price: float
    exit_price: float
    entry_ts: Optional[int] = None
    exit_ts: Optional[int] = None
    pnl: float = 0.0
    fees: float = 0.0
    reason: str = "EXIT"  # TAKE/STOP/EXIT


@dataclass
class Position:
    symbol: str
    side: Side
    qty: float
    entry_price: float
    stop_loss: float
    take_profit: float
    entry_ts: Optional[int] = None

    def is_long(self) -> bool:
        return self.side == "LONG"

    def unrealized_pnl(self, price: float) -> float:
        if self.is_long():
            return (price - self.entry_price) * self.qty
        return (self.entry_price - price) * self.qty
