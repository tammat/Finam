from collections import deque
from typing import Optional
import math


class ATRCalculator:
    def __init__(self, period: int, ema_period: Optional[int] = None):
        self.period = period
        self.ema_period = ema_period

        self.tr_values = deque(maxlen=period)
        self.prev_close: Optional[float] = None

        self.ema_atr: Optional[float] = None
        if ema_period:
            self.alpha = 2 / (ema_period + 1)

    def update(self, high: float, low: float, close: float):
        if self.prev_close is None:
            tr = high - low
        else:
            tr = max(
                high - low,
                abs(high - self.prev_close),
                abs(low - self.prev_close),
            )

        self.tr_values.append(tr)

        # EMA ATR
        if self.ema_period:
            if self.ema_atr is None:
                self.ema_atr = tr
            else:
                self.ema_atr = self.alpha * tr + (1 - self.alpha) * self.ema_atr

        self.prev_close = close

    def atr(self) -> Optional[float]:
        if len(self.tr_values) < self.period:
            return None
        return sum(self.tr_values) / len(self.tr_values)

    def atr_ema(self) -> Optional[float]:
        return self.ema_atr
