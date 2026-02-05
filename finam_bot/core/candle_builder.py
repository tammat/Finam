# finam_bot/core/candle_builder.py

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class Candle:
    open: float
    high: float
    low: float
    close: float


class CandleBuilder:
    """
    Собирает свечи фиксированной длины из потока цен
    """

    def __init__(self, barsize: int = 5):
        self.barsize = barsize
        self.buffer: List[float] = []

    def push(self, price: float) -> Optional[Candle]:
        self.buffer.append(price)

        if len(self.buffer) < self.barsize:
            return None

        candle = Candle(
            open=self.buffer[0],
            high=max(self.buffer),
            low=min(self.buffer),
            close=self.buffer[-1],
        )

        self.buffer.clear()
        return candle
