from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Signal:
    symbol: str
    side: str            # BUY / SELL
    entry: float
    stop: float
    reason: str
    confidence: float = 1.0