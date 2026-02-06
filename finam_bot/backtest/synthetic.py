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
    volume_base: float = 1000.0,
    volume_noise: float = 0.2,
    seed: Optional[int] = 42,
    absorption_prob: float = 0.25,
) -> list[SyntheticOF]:
    """
    Генерирует синтетические order-flow данные для каждой свечи.

    - bid_volume/ask_volume: создают imbalance (иногда сильный).
    - prices/volumes: иногда создают 'absorption' (высокий объём при почти плоской цене).
    """
    if n <= 0:
        return []

    rng = random.Random(seed)
    out: list[SyntheticOF] = []

    for _ in range(n):
        total = max(1.0, volume_base * (1.0 + rng.uniform(-volume_noise, volume_noise)))

        r = rng.random()
        if r < 0.35:
            ratio = 0.75  # buy pressure
        elif r < 0.70:
            ratio = 0.25  # sell pressure
        else:
            ratio = 0.50  # neutral

        bid = total * ratio
        ask = total - bid

        if rng.random() < absorption_prob:
            base = 100.0
            prices = [base, base + 0.01, base - 0.01, base]
            volumes = [40.0, 40.0, 50.0]  # sum=130 >= 100
        else:
            prices = []
            volumes = []

        out.append(SyntheticOF(bid_volume=bid, ask_volume=ask, prices=prices, volumes=volumes))

    return out


def generate_synthetic_candles(
    n: int,
    start_price: float = 100.0,
    mode: str = "mixed",          # "up" | "down" | "flat" | "mixed"
    drift: float = 0.02,          # средний шаг цены (в пунктах) на бар
    volatility: float = 0.10,     # шум (в пунктах) на бар
    wick: float = 0.15,           # размер теней (в пунктах)
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
        # mixed: 1/3 up, 1/3 flat, 1/3 down
        third = max(1, n // 3)
        if i < third:
            return abs(drift)
        if i < 2 * third:
            return 0.0
        return -abs(drift)

    candles: list[Candle] = []
    ts = start_ts

    for i in range(n):
        o = price
        step = _drift_for_i(i) + rng.gauss(0.0, volatility)
        c = max(0.01, o + step)

        # тени
        up_wick = abs(rng.gauss(0.0, wick))
        dn_wick = abs(rng.gauss(0.0, wick))

        h = max(o, c) + up_wick
        l = min(o, c) - dn_wick
        if l <= 0:
            l = 0.01

        vol = max(1.0, volume_base * (1.0 + rng.uniform(-volume_noise, volume_noise)))

        candles.append(Candle(ts=ts, open=o, high=h, low=l, close=c, volume=vol))

        price = c
        if ts is not None:
            ts += ts_step

    return candles
