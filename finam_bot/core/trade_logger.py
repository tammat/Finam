# finam_bot/core/trade_logger.py

from dataclasses import dataclass
from datetime import datetime
from typing import List


@dataclass
class TradeRecord:
    time: datetime
    symbol: str
    side: str
    entry: float
    exit: float
    qty: float
    pnl: float
    reason: str


class TradeLogger:
    def __init__(self):
        self.trades: List[TradeRecord] = []

    def log(
        self,
        symbol: str,
        side: str,
        entry: float,
        exit: float,
        qty: float,
        pnl: float,
        reason: str,
    ):
        record = TradeRecord(
            time=datetime.utcnow(),
            symbol=symbol,
            side=side,
            entry=entry,
            exit=exit,
            qty=qty,
            pnl=pnl,
            reason=reason,
        )
        self.trades.append(record)
