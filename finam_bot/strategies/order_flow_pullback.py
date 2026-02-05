from dataclasses import dataclass
from collections import deque
from enum import Enum
from typing import Optional

from finam_bot.core.market_snapshot import MarketSnapshot
from finam_bot.core.orderflow_analyzer import OrderFlowAnalyzer
from finam_bot.core.orderflow_absorption import OrderFlowAbsorptionDetector
from finam_bot.core.orderflow_composite import build_composite_signal
from finam_bot.core.signals import Signal


# =========================
# ДАННЫЕ
# =========================

@dataclass
class Candle:
    open: float
    high: float
    low: float
    close: float


@dataclass
class OrderBook:
    bid_volume: float
    ask_volume: float


# =========================
# ФИЛЬТР ТРЕНДА (EMA 50 / 200)
# =========================

class TrendFilter:
    def __init__(self, ema_fast: int = 50, ema_slow: int = 200):
        self.ema_fast = ema_fast
        self.ema_slow = ema_slow
        self.prices = deque(maxlen=ema_slow)
        self._ema50 = None
        self._ema200 = None

    def update(self, price: float):
        self.prices.append(price)
        if len(self.prices) >= self.ema_slow:
            self._ema50 = self._ema(self.ema_fast)
            self._ema200 = self._ema(self.ema_slow)

    def _ema(self, period: int) -> float:
        k = 2 / (period + 1)
        ema = self.prices[0]
        for p in list(self.prices)[1:]:
            ema = p * k + ema * (1 - k)
        return ema

    def is_long(self) -> bool:
        return self._ema50 is not None and self._ema200 is not None and self._ema50 > self._ema200

    def is_short(self) -> bool:
        return self._ema50 is not None and self._ema200 is not None and self._ema50 < self._ema200

    def ema50(self) -> Optional[float]:
        return self._ema50


# =========================
# ВОЛАТИЛЬНОСТЬ (ATR)
# =========================

class VolatilityFilter:
    def __init__(self, period: int = 14):
        self.period = period
        self.tr_values = deque(maxlen=period)
        self.prev_close = None

    def update(self, candle: Candle):
        if self.prev_close is None:
            self.prev_close = candle.close
            return

        tr = max(
            candle.high - candle.low,
            abs(candle.high - self.prev_close),
            abs(candle.low - self.prev_close)
        )
        self.tr_values.append(tr)
        self.prev_close = candle.close

    def atr(self) -> Optional[float]:
        if len(self.tr_values) < self.period:
            return None
        return sum(self.tr_values) / len(self.tr_values)

    def is_active(self) -> bool:
        atr = self.atr()
        if atr is None:
            return False
        avg_atr = sum(self.tr_values) / len(self.tr_values)
        return atr > avg_atr * 1.2


# =========================
# ОСНОВНАЯ СТРАТЕГИЯ
# =========================

class OrderFlowPullbackStrategy:
    """
    Order Flow Pullback Strategy
    S9.B1: Composite order flow (imbalance + absorption + confidence)
    """

    def __init__(self):
        self.imbalance_analyzer = OrderFlowAnalyzer(
            imbalance_threshold=0.6
        )

        self.absorption_detector = OrderFlowAbsorptionDetector(
            min_volume=100,
            price_tolerance=0.01,
        )

        self.min_confidence = 0.6
        self.last_confidence: float = 0.0

    # =========================
    # SNAPSHOT → SIGNAL
    # =========================

    def on_snapshot(self, snapshot: MarketSnapshot) -> Signal:
        """
        Composite Order Flow decision
        """

        # 1️⃣ imbalance
        imbalance = self.imbalance_analyzer.analyze(snapshot)

        # 2️⃣ absorption (если есть данные)
        absorption = None
        if snapshot.prices and snapshot.volumes:
            absorption = self.absorption_detector.analyze(
                prices=snapshot.prices,
                volumes=snapshot.volumes,
                    )
        # ✅ S9.B1: интерпретация стороны absorption
        if absorption and absorption.side is None and imbalance:
            # если фильтр ужесточён → считаем absorption ПРОТИВ
            if self.absorption_detector.price_tolerance < 0.001:
                absorption.side = (
                    "SELL" if imbalance.side == "BUY" else "BUY"
                )
            else:
                # обычный случай → absorption усиливает imbalance
                absorption.side = imbalance.side


        # 3️⃣ composite
        composite = build_composite_signal(
            imbalance=imbalance,
            absorption=absorption,
        )

        if composite is None:
            self.last_confidence = 0.0
            return Signal.HOLD

        # 4️⃣ confidence filter (S9.B1)
        if composite.confidence < self.min_confidence:
            self.last_confidence = composite.confidence
            return Signal.HOLD

        # 5️⃣ лог
        print(
            f"🧠 COMPOSITE {composite.side} | "
            f"confidence={composite.confidence:.2f} | "
            f"reasons={','.join(composite.reasons)}"
        )

        self.last_confidence = composite.confidence

        if composite.side == "BUY":
            return Signal.BUY

        if composite.side == "SELL":
            return Signal.SELL

        return Signal.HOLD
