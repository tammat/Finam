from finam_bot.signals.base import SignalStrategy
from finam_bot.signals.models import Signal


class LevelBounceStrategy(SignalStrategy):

    def __init__(self, level: float, tolerance: float = 0.01):
        self.level = level
        self.tolerance = tolerance

    def detect(self, symbol: str, price: float):
        # BUY от уровня
        if abs(price - self.level) <= self.tolerance:
            return Signal(
                symbol=symbol,
                side="BUY",
                entry=price,
                stop=self.level - self.tolerance * 2,
                reason="LEVEL_BOUNCE",
                confidence=0.7,
            )

        return None