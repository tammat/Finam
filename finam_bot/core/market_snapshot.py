from dataclasses import dataclass
from typing import Optional
from datetime import datetime   # ← ВОТ ЭТО


@dataclass
class MarketSnapshot:
    symbol: str                 # ← ДОБАВИТЬ 
    price: float
# 🔽 ДОБАВИТЬ
    bid_volume: Optional[float] = None
    ask_volume: Optional[float] = None
    delta: Optional[float] = None

    atr: Optional[float] = None
    timestamp: Optional[datetime] = None
    atr: Optional[float] = None
    atr_fast: Optional[float] = None
    timestamp: Optional[int] = None
    
    @classmethod
    def from_candle(
        cls,
        *,
        symbol: str,
        candle,
        atr: float | None = None,
        timestamp: int | None = None,
    ) -> "MarketSnapshot":
        """
        Универсальный адаптер:
        - candle может быть float (TEST)
        - candle может быть объектом с .close (REAL)
        """

        # TEST MODE: candle = float
        if isinstance(candle, (int, float)):
            price = float(candle)
            ts = timestamp

        # REAL MODE: candle object
        else:
            price = candle.close
            ts = getattr(candle, "timestamp", timestamp)

        return cls(
            symbol=symbol,
            price=price,
            atr=atr,
            timestamp=ts,
        )
