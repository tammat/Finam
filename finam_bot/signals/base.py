from abc import ABC, abstractmethod
from typing import Optional
from finam_bot.signals.models import Signal


class SignalStrategy(ABC):

    @abstractmethod
    def detect(self, symbol: str, data) -> Optional[Signal]:
        pass