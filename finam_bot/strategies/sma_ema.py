# finam_bot/strategies/sma_ema.py

from collections import deque
from statistics import mean

from finam_bot.core.signals import Signal
from finam_bot.strategies.base import Strategy


class SMAStrategy(Strategy):
    def __init__(self, window: int = 5):
        self.prices = deque(maxlen=window)

    def on_price(self, price: float) -> Signal:
        self.prices.append(price)

        if len(self.prices) < self.prices.maxlen:
            return Signal.HOLD

        avg = mean(self.prices)

        if price > avg:
            return Signal.BUY
        elif price < avg:
            return Signal.SELL
        return Signal.HOLD
