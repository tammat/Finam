# finam_bot/core/orderflow_analyzer.py

from typing import Optional
from finam_bot.core.orderflow_snapshot import OrderFlowSnapshot
from finam_bot.core.orderflow_signal import OrderFlowSignal


class OrderFlowAnalyzer:
    """
    Интерпретирует OrderFlowSnapshot → OrderFlowSignal
    """

    def __init__(
        self,
        imbalance_threshold: float = 0.6,
        min_volume: float = 50.0,
    ):
        self.imbalance_threshold = imbalance_threshold
        self.min_volume = min_volume

    def analyze(self, snapshot: OrderFlowSnapshot) -> Optional[OrderFlowSignal]:
        # 1️⃣ фильтр пустоты / шума
        if snapshot.total_volume < self.min_volume:
            return None

        imbalance = snapshot.imbalance

        # 2️⃣ BUY pressure
        if imbalance >= self.imbalance_threshold:
            strength = min(1.0, abs(imbalance))
            return OrderFlowSignal(
                side="BUY",
                strength=strength,
                imbalance=imbalance,
                reason="aggressive_buy_imbalance",
            )

        # 3️⃣ SELL pressure
        if imbalance <= -self.imbalance_threshold:
            strength = min(1.0, abs(imbalance))
            return OrderFlowSignal(
                side="SELL",
                strength=strength,
                imbalance=imbalance,
                reason="aggressive_sell_imbalance",
            )

        # 4️⃣ нет сигнала
        return None
