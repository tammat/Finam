# finam_bot/backtest/synthetic.py
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional
import random

from finam_bot.backtest.models import Candle


@dataclass
class SyntheticOF:
    bid_volume: float
    ask_volume: float
    prices: list[float]
    volumes: list[float]


def generate_synthetic_orderflow(
    n: int,
    *,
    price_ref: float = 100.0,
    volume_base: float = 1000.0,
    volume_noise: float = 0.2,
    seed: Optional[int] = 42,
) -> list[SyntheticOF]:
    """
    Простой synthetic orderflow:
    - bid/ask объёмы
    - небольшой список "принтов" prices/volumes (для absorption detector)

    Это НЕ реалистичная лента, но достаточно, чтобы стратегия могла
    выдавать сигналы в synthetic backtest без CSV.
    """
    rng = random.Random(seed)
    out: list[SyntheticOF] = []

    for _ in range(max(0, n)):
        total = max(1.0, volume_base * (1.0 + rng.uniform(-volume_noise, volume_noise)))

        r = rng.uniform(0.3, 0.7)
        bid = total * r
        ask = total - bid

        k = rng.randint(3, 6)
        prices = [price_ref + rng.uniform(-0.02, 0.02) for _ in range(k)]
        vols_raw = [max(1.0, rng.random()) for _ in range(k)]
        s = sum(vols_raw)
        volumes = [total * (v / s) for v in vols_raw]

        out.append(SyntheticOF(bid_volume=bid, ask_volume=ask, prices=prices, volumes=volumes))

        price_ref += rng.gauss(0.0, 0.05)

    return out


def generate_synthetic_candles(
    n: int,
    start_price: float = 100.0,
    mode: str = "mixed",          # "up" | "down" | "flat" | "mixed"
    drift: float = 0.02,
    volatility: float = 0.10,
    wick: float = 0.15,
    start_ts: Optional[int] = 1,
    ts_step: int = 1,
    seed: Optional[int] = 42,
    volume_base: float = 1000.0,
    volume_noise: float = 0.2,
) -> List[Candle]:
    """
    Генератор OHLC свечей для бэктеста.
    Гарантирует: high >= max(open, close), low <= min(open, close).
    """
    if n <= 0:
        return []

    rng = random.Random(seed)
    price = float(start_price)

    def _drift_for_i(i: int) -> float:
        if mode == "up":
            return abs(drift)
        if mode == "down":
            return -abs(drift)
        if mode == "flat":
            return 0.0
        third = max(1, n // 3)
        if i < third:
            return abs(drift)
        if i < 2 * third:
            return 0.0
        return -abs(drift)

    candles: List[Candle] = []
    ts = start_ts

    for i in range(n):
        d = _drift_for_i(i)
        shock = rng.gauss(0.0, volatility)

        o = price
        c = price + d + shock

        base_hi = max(o, c)
        base_lo = min(o, c)

        hi = base_hi + abs(rng.gauss(0.0, wick))
        lo = base_lo - abs(rng.gauss(0.0, wick))

        vol = max(0.0, volume_base * (1.0 + rng.uniform(-volume_noise, volume_noise)))

        candles.append(
            Candle(
                ts=ts,
                open=float(o),
                high=float(hi),
                low=float(lo),
                close=float(c),
                volume=float(vol),
            )
        )

        price = c
        if ts is not None:
            ts += ts_step

    return candles
