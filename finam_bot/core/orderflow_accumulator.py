# finam_bot/core/orderflow_accumulator.py

from dataclasses import dataclass
from typing import Optional
from finam_bot.core.orderflow_snapshot import OrderFlowSnapshot

def flush_snapshot(self) -> OrderFlowSnapshot:
    snapshot = OrderFlowSnapshot(
        bid_volume=self.bid_volume,
        ask_volume=self.ask_volume,
    )
    self.flush()
    return snapshot

@dataclass
class OrderFlowSnapshot:
    bid_volume: float
    ask_volume: float
    total_volume: float
    delta: float
    trades: int
    vwap: Optional[float]


class OrderFlowAccumulator:
    """
    S8.A — Accumulates order flow (trade prints) inside a bar.

    READ-ONLY.
    No strategy logic.
    No timing logic.
    """

    def __init__(self):
        self.reset()

    def reset(self) -> None:
        self._bid_volume: float = 0.0
        self._ask_volume: float = 0.0
        self._total_volume: float = 0.0

        self._vwap_price_qty: float = 0.0
        self._trades: int = 0

    def update(self, *, price: float, qty: float, side: str) -> None:
        """
        Update accumulator with single trade.

        side:
            BUY  -> aggressive buyer -> ask volume
            SELL -> aggressive seller -> bid volume
        """

        if qty <= 0:
            return

        if side == "BUY":
            self._ask_volume += qty
        elif side == "SELL":
            self._bid_volume += qty
        else:
            # silently ignore unknown side
            return

        self._total_volume += qty
        self._vwap_price_qty += price * qty
        self._trades += 1

    def flush(self) -> OrderFlowSnapshot:
        """
        Finalize current bar and reset accumulator.
        """

        if self._total_volume > 0:
            vwap = self._vwap_price_qty / self._total_volume
        else:
            vwap = None

        snapshot = OrderFlowSnapshot(
            bid_volume=self._bid_volume,
            ask_volume=self._ask_volume,
            total_volume=self._total_volume,
            delta=self._bid_volume - self._ask_volume,
            trades=self._trades,
            vwap=vwap,
        )

        self.reset()
        return snapshot
