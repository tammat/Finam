# finam_bot/core/market_snapshot.py

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Optional


@dataclass
class OrderBookSnapshot:
    best_bid: Optional[float] = None
    best_ask: Optional[float] = None
    bid_volume: Optional[float] = None
    ask_volume: Optional[float] = None

    @property
    def spread(self) -> Optional[float]:
        if self.best_bid is None or self.best_ask is None:
            return None
        return self.best_ask - self.best_bid

    @property
    def imbalance(self) -> Optional[float]:
        if self.bid_volume is None or self.ask_volume is None:
            return None
        total = self.bid_volume + self.ask_volume
        if total == 0:
            return None
        return self.bid_volume / total


@dataclass
class MarketSnapshot:
    instrument: str
    price: float
    timestamp: datetime

    # --- indicators ---
    indicators: Dict[str, float]

    # --- order book (optional) ---
    orderbook: Optional[OrderBookSnapshot] = None

    # --- correlations ---
    correlations: Optional[Dict[str, str]] = None
