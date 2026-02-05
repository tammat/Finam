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
    atr: Optional[float] = None
    timestamp: Optional[datetime] = None
    atr: Optional[float] = None
    atr_fast: Optional[float] = None
    timestamp: Optional[int] = None
