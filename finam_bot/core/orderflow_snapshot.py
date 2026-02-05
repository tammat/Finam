# finam_bot/core/orderflow_snapshot.py

from dataclasses import dataclass


@dataclass(frozen=True)
class OrderFlowSnapshot:
    bid_volume: float
    ask_volume: float

    @property
    def total_volume(self) -> float:
        return self.bid_volume + self.ask_volume

    @property
    def delta(self) -> float:
        return self.bid_volume - self.ask_volume

    @property
    def imbalance(self) -> float:
        """
        Нормализованный дисбаланс [-1 .. +1]
        """
        total = self.total_volume
        if total == 0:
            return 0.0
        return self.delta / total

    @property
    def dominant_side(self) -> str | None:
        if self.bid_volume > self.ask_volume:
            return "BUY"
        if self.ask_volume > self.bid_volume:
            return "SELL"
        return None

    def is_aggressive(self, threshold: float = 0.6) -> bool:
        """
        Сильный перекос потока
        """
        return abs(self.imbalance) >= threshold
