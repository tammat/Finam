# finam_bot/core/orderflow_signal.py

from dataclasses import dataclass
from typing import Literal

Side = Literal["BUY", "SELL"]


@dataclass(frozen=True)
class OrderFlowSignal:
    side: Side
    strength: float          # 0.0 .. 1.0
    imbalance: float         # -1 .. +1
    reason: str              # human-readable (logs/debug)

    @property
    def is_strong(self) -> bool:
        return True
# finam_bot/core/orderflow_signal.py

from dataclasses import dataclass


@dataclass
class OrderFlowSignal:
    side: str            # "BUY" | "SELL"
    strength: float      # 0..1
    imbalance: float
    reason: str

    @property
    def is_strong(self) -> bool:
        return self.strength >= 0.6


@dataclass
class AbsorptionSignal(OrderFlowSignal):
    """
    Сигнал абсорбции:
    большой объём + отсутствие продолжения цены
    """
    absorbed_volume: float = 0.0
