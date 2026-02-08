# /Users/alex/finam/finam_bot/backtest/data_source.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Sequence, Tuple, Protocol, List
import datetime as dt

from finam_bot.backtest.models import Candle


class CandleSource(Protocol):
    name: str

    def load(
        self,
        *,
        symbols: Sequence[str],
        tf: str,
        dt_from: Optional[dt.datetime] = None,
        dt_to: Optional[dt.datetime] = None,
        limit: Optional[int] = None,
    ) -> dict[str, List[Candle]]:
        """
        Returns dict symbol -> candles (sorted by ts)
        """


@dataclass
class SyntheticSource:
    name: str = "synthetic"

    def load(
        self,
        *,
        symbols: Sequence[str],
        tf: str,
        dt_from: Optional[dt.datetime] = None,
        dt_to: Optional[dt.datetime] = None,
        limit: Optional[int] = None,
    ) -> dict[str, List[Candle]]:
        from finam_bot.backtest.synthetic import generate_synthetic_candles

        n = int(limit or 200)
        out: dict[str, List[Candle]] = {}
        for s in symbols:
            out[s] = generate_synthetic_candles(n=n, start_price=100.0)
        return out


@dataclass
class CsvSource:
    csv_path: str
    name: str = "csv"

    def load(
        self,
        *,
        symbols: Sequence[str],
        tf: str,
        dt_from: Optional[dt.datetime] = None,
        dt_to: Optional[dt.datetime] = None,
        limit: Optional[int] = None,
    ) -> dict[str, List[Candle]]:
        # текущий CSV-лоадер у тебя уже есть в cli.py (или рядом).
        # Чтобы не ломать ничего сейчас — импортируем оттуда функцию.
        from finam_bot.backtest.cli import load_candles_from_csv  # noqa

        candles = load_candles_from_csv(self.csv_path, limit=limit)
        # CSV у нас пока "один инструмент" → мапим на первый symbol
        sym = symbols[0] if symbols else "CSV"
        return {sym: candles}