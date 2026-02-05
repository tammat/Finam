
# finam_bot/core/trade_engine.py

from typing import Optional

from finam_bot.core.position import Position
from finam_bot.core.signals import Signal

from finam_bot.strategies.order_flow_pullback import (
    OrderFlowPullbackStrategy,
    Candle,
    OrderBook,
)


class TradeEngine:
    """
    TEST trade engine — no real orders.
    Strategy-driven.
    """

    def __init__(self, symbol: str, qty: int = 1):
        self.symbol = symbol
        self.qty = qty

        # Стратегия (ШАГ 2)
        self.strategy = OrderFlowPullbackStrategy()

        self.position: Optional[Position] = None
        self.total_pnl: float = 0.0

    # ======================================================
    # MARKET DATA INPUT (ШАГ 3)
    # ======================================================

    def on_candle(self, open_: float, high: float, low: float, close: float):
        """
        Вызывается на каждой новой 1m свече
        """
        candle = Candle(
            open=open_,
            high=high,
            low=low,
            close=close,
        )

        # Передаём свечу в стратегию
        self.strategy.on_candle(candle)

        # После обновления свечи — оцениваем сигнал
        self._evaluate(close)

    def on_orderbook(self, bid_volume: float, ask_volume: float):
        """
        Вызывается при обновлении стакана
        """
        book = OrderBook(
            bid_volume=bid_volume,
            ask_volume=ask_volume,
        )

        # Передаём стакан в стратегию
        self.strategy.on_orderbook(book)

    # ======================================================
    # DECISION & EXECUTION (ШАГ 4 — базовый)
    # ======================================================

    def _evaluate(self, price: float):
        signal = self.strategy.generate_signal()

        if signal == Signal.BUY:
            self._open("LONG", price)

        elif signal == Signal.SELL:
            self._open("SHORT", price)

    def _open(self, side: str, price: float):
        # Если позиция уже есть — закрываем
        if self.position:
            pnl = self.position.close(price)
            self.total_pnl += pnl
            print(f"🔁 Закрыта позиция PnL={pnl:.2f}")

        # Открываем новую
        self.position = Position(
            symbol=self.symbol,
            side=side,
            qty=self.qty,
            entry_price=price,
        )

        print(f"📈 Открыта {side} @ {price}")

    # ======================================================
    # STATUS
    # ======================================================

    def status(self):
        return {
            "symbol": self.symbol,
            "position": self.position,
            "total_pnl": self.total_pnl,
        }
