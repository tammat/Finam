# finam_bot/core/atr.py

from typing import List
from finam_bot.core.candle_builder import Candle


class ATR:
    def __init__(self, period: int = 14):
        self.period = period
        self.tr_values: List[float] = []
        self.prev_close: float | None = None

    def update(self, candle: Candle) -> float | None:
        if self.prev_close is None:
            tr = candle.high - candle.low
        else:
            tr = max(
                candle.high - candle.low,
                abs(candle.high - self.prev_close),
                abs(candle.low - self.prev_close),
            )

        self.prev_close = candle.close
        self.tr_values.append(tr)

        if len(self.tr_values) < self.period:
            return None

        if len(self.tr_values) > self.period:
            self.tr_values.pop(0)

        return sum(self.tr_values) / self.period
