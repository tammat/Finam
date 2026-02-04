# finam_bot/core/trade_engine.py

from typing import Optional
from finam_bot.core.position import Position
from finam_bot.core.signals import Signal


class TradeEngine:
    """
    TEST trade engine — no real orders.
    """

    def __init__(self, symbol: str, qty: int = 1):
        self.symbol = symbol
        self.qty = qty
        self.position: Optional[Position] = None
        self.total_pnl: float = 0.0

    def on_signal(self, signal: Signal, price: float):
        if signal == Signal.BUY:
            self._open("LONG", price)
        elif signal == Signal.SELL:
            self._open("SHORT", price)

    def _open(self, side: str, price: float):
        if self.position:
            pnl = self.position.close(price)
            self.total_pnl += pnl
            print(f"🔁 Закрыта позиция PnL={pnl:.2f}")

        self.position = Position(
            symbol=self.symbol,
            side=side,
            qty=self.qty,
            entry_price=price,
        )

        print(f"📈 Открыта {side} @ {price}")

    def status(self):
        return {
            "position": self.position,
            "total_pnl": self.total_pnl,
        }
