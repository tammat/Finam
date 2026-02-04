# finam_bot/strategies/base.py

from abc import ABC, abstractmethod
from finam_bot.core.signals import Signal


class Strategy(ABC):

    @abstractmethod
    def on_price(self, price: float) -> Signal:
        pass
