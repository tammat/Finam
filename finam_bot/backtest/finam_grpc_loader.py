# /Users/alex/finam/finam_bot/backtest/finam_grpc_loader.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Sequence, List
import datetime as dt

from finam_bot.backtest.models import Candle


@dataclass
class FinamGrpcSource:
    """
    Реальный источник данных Finam Trade API (gRPC).

    Сейчас это "безопасная заглушка":
    - не требует grpc/proto пакетов
    - при вызове говорит что нужно добавить SDK/прото
    """
    token: str
    host: str = "trade-api.finam.ru:443"  # позже уточним
    name: str = "finam"

    def load(
        self,
        *,
        symbols: Sequence[str],
        tf: str,
        dt_from: Optional[dt.datetime] = None,
        dt_to: Optional[dt.datetime] = None,
        limit: Optional[int] = None,
    ) -> dict[str, List[Candle]]:
        raise RuntimeError(
            "Finam gRPC loader is not wired yet. "
            "Need Finam proto/SDK or endpoint methods to fetch candles/trades."
        )