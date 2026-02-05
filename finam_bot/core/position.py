from dataclasses import dataclass
from typing import Optional


@dataclass
class Position:
    symbol: str
    side: str          # "LONG" | "SHORT"
    qty: float
    entry_price: float
    stop_loss: float
    take_profit: float

    exit_price: Optional[float] = None
    exit_reason: Optional[str] = None  # "STOP" | "TAKE"

    def is_long(self) -> bool:
        return self.side == "LONG"

    def check_exit(self, price: float) -> Optional[str]:
        """
        Возвращает:
        - "STOP"
        - "TAKE"
        - None
        """
        if self.is_long():
            if price <= self.stop_loss:
                return "STOP"
            if price >= self.take_profit:
                return "TAKE"
        else:  # SHORT
            if price >= self.stop_loss:
                return "STOP"
            if price <= self.take_profit:
                return "TAKE"

        return None

    def close(self, price: float, reason: Optional[str] = None) -> float:
        self.exit_price = price
        self.exit_reason = reason

        if self.is_long():
            pnl = (price - self.entry_price) * self.qty
        else:
            pnl = (self.entry_price - price) * self.qty

        return pnl
