from dataclasses import dataclass
from typing import Optional
from datetime import datetime   # ← ВОТ ЭТО
print("🔥 LOADED MarketSnapshot FROM:", __file__)

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

    @property
    def total_volume(self) -> float:
        if self.bid_volume is None or self.ask_volume is None:
            return 0.0
        return self.bid_volume + self.ask_volume
    @property
    def imbalance(self) -> float:
        if self.bid_volume is None or self.ask_volume is None:
            return 0.0

        total = self.bid_volume + self.ask_volume
        if total == 0:
            return 0.0

        return (self.bid_volume - self.ask_volume) / total
    
    @property
    def has_orderflow(self) -> bool:
        return (
            self.bid_volume is not None
            and self.ask_volume is not None
            and self.total_volume > 0
        )
    
    @property
    def has_absorption_data(self) -> bool:
        return bool(self.prices) and bool(self.volumes)
    @property
    def mid_price(self) -> float:
        return self.price

    @property
    def total_volume(self) -> float:
        if self.bid_volume is None or self.ask_volume is None:
            return 0.0
        return self.bid_volume + self.ask_volume

    @property
    def imbalance(self) -> float:
        tv = self.total_volume
        if tv == 0:
            return 0.5
        return self.bid_volume / tv
    
    def __init__(
        self,
        symbol: str,
        price: float,
        bid_volume: float | None = None,
        ask_volume: float | None = None,
        prices: list[float] | None = None,
        volumes: list[float] | None = None,
        delta: float | None = None,
        atr: float | None = None,
        atr_fast: float | None = None,
        timestamp=None,
    ):
        self.symbol = symbol
        self.price = price

        self.bid_volume = bid_volume
        self.ask_volume = ask_volume

        self.prices = prices or []
        self.volumes = volumes or []

        self.delta = delta
        self.atr = atr
        self.atr_fast = atr_fast
        self.timestamp = timestamp

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
