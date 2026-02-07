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
    entry_fee: float = 0.0
    def is_long(self) -> bool:
        return self.side == "LONG"

    def unrealized_pnl(self, price: float) -> float:
        if self.is_long():
            return (price - self.entry_price) * self.qty
        return (self.entry_price - price) * self.qty


from dataclasses import dataclass
from typing import Optional, Literal

AssetClass = Literal["equity", "future", "bond"]

@dataclass
class Instrument:
    symbol: str
    asset_class: AssetClass = "equity"

    # bonds only
    face_value: float = 1000.0          # номинал (обычно 1000)
    price_is_percent: bool = False      # для облигаций True (цена в % от номинала)

@dataclass
class CashflowEvent:
    ts: Optional[int]
    symbol: str
    kind: str              # "COUPON"
    amount: float          # +cash
    comment: str = ""