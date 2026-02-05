from dataclasses import dataclass
from collections import deque
from enum import Enum
from typing import Optional


# =========================
# СИГНАЛЫ
# =========================

class Signal(Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


# =========================
# ДАННЫЕ
# =========================

@dataclass
class Candle:
    open: float
    high: float
    low: float
    close: float


@dataclass
class OrderBook:
    bid_volume: float
    ask_volume: float


# =========================
# ФИЛЬТР ТРЕНДА (EMA 50 / 200)
# =========================

class TrendFilter:
    def __init__(self, ema_fast: int = 50, ema_slow: int = 200):
        self.ema_fast = ema_fast
        self.ema_slow = ema_slow
        self.prices = deque(maxlen=ema_slow)
        self._ema50 = None
        self._ema200 = None

    def update(self, price: float):
        self.prices.append(price)
        if len(self.prices) >= self.ema_slow:
            self._ema50 = self._ema(self.ema_fast)
            self._ema200 = self._ema(self.ema_slow)

    def _ema(self, period: int) -> float:
        k = 2 / (period + 1)
        ema = self.prices[0]
        for p in list(self.prices)[1:]:
            ema = p * k + ema * (1 - k)
        return ema

    def is_long(self) -> bool:
        return self._ema50 and self._ema200 and self._ema50 > self._ema200

    def is_short(self) -> bool:
        return self._ema50 and self._ema200 and self._ema50 < self._ema200

    def ema50(self) -> Optional[float]:
        return self._ema50


# =========================
# ВОЛАТИЛЬНОСТЬ (ATR)
# =========================

class VolatilityFilter:
    def __init__(self, period: int = 14):
        self.period = period
        self.tr_values = deque(maxlen=period)
        self.prev_close = None

    def update(self, candle: Candle):
        if self.prev_close is None:
            self.prev_close = candle.close
            return

        tr = max(
            candle.high - candle.low,
            abs(candle.high - self.prev_close),
            abs(candle.low - self.prev_close)
        )
        self.tr_values.append(tr)
        self.prev_close = candle.close

    def atr(self) -> Optional[float]:
        if len(self.tr_values) < self.period:
            return None
        return sum(self.tr_values) / len(self.tr_values)

    def is_active(self) -> bool:
        atr = self.atr()
        if atr is None:
            return False
        avg_atr = sum(self.tr_values) / len(self.tr_values)
        return atr > avg_atr * 1.2


# =========================
# АНАЛИЗ СТАКАНА
# =========================

class OrderBookAnalyzer:
    def __init__(self, threshold_long=0.65, threshold_short=0.35):
        self.threshold_long = threshold_long
        self.threshold_short = threshold_short

    def imbalance(self, book: OrderBook) -> float:
        total = book.bid_volume + book.ask_volume
        if total == 0:
            return 0.5
        return book.bid_volume / total

    def long_pressure(self, book: OrderBook) -> bool:
        return self.imbalance(book) >= self.threshold_long

    def short_pressure(self, book: OrderBook) -> bool:
        return self.imbalance(book) <= self.threshold_short


# =========================
# ОСНОВНАЯ СТРАТЕГИЯ
# =========================

class OrderFlowPullbackStrategy:
    """
    Order Flow Pullback
    1m вход
    EMA 50/200 (15m логически)
    ATR стопы
    """

    def __init__(self):
        self.trend = TrendFilter()
        self.volatility = VolatilityFilter()
        self.book = OrderBookAnalyzer()

        self.last_candle: Optional[Candle] = None
        self.last_price: Optional[float] = None
        self.last_orderbook: Optional[OrderBook] = None

    # -------- обновления --------

    def on_candle(self, candle: Candle):
        self.last_candle = candle
        self.last_price = candle.close
        self.trend.update(candle.close)
        self.volatility.update(candle)

    def on_orderbook(self, book: OrderBook):
        self.last_orderbook = book

    # -------- логика --------

    def generate_signal(self) -> Signal:
        if not all([
            self.last_price,
            self.last_orderbook,
            self.trend.ema50(),
            self.volatility.atr()
        ]):
            return Signal.HOLD

        atr = self.volatility.atr()
        ema50 = self.trend.ema50()
        price = self.last_price

        # допуск отката к EMA50
        near_ema = abs(price - ema50) <= 0.2 * atr

        if not near_ema or not self.volatility.is_active():
            return Signal.HOLD

        # LONG
        if self.trend.is_long() and self.book.long_pressure(self.last_orderbook):
            return Signal.BUY

        # SHORT
        if self.trend.is_short() and self.book.short_pressure(self.last_orderbook):
            return Signal.SELL

        return Signal.HOLD
