from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Literal

from finam_bot.backtest.models import Candle
from finam_bot.backtest.broker import BrokerSim, PercentCommission
from finam_bot.core.market_snapshot import MarketSnapshot
from finam_bot.core.signals import Signal
from finam_bot.core.risk_manager import RiskManager

Side = Literal["LONG", "SHORT"]


class ATRCalc:
    """
    Очень простой ATR по OHLC (без гэпов точных), для MVP.
    """
    def __init__(self, period: int = 14):
        self.period = period
        self.trs: list[float] = []
        self.prev_close: Optional[float] = None

    def update(self, c: Candle) -> Optional[float]:
        if self.prev_close is None:
            self.prev_close = c.close
            return None

        tr = max(
            c.high - c.low,
            abs(c.high - self.prev_close),
            abs(c.low - self.prev_close),
        )
        self.trs.append(tr)
        if len(self.trs) > self.period:
            self.trs.pop(0)

        self.prev_close = c.close
        if len(self.trs) < self.period:
            return None
        return sum(self.trs) / len(self.trs)


@dataclass
class PendingEntry:
    side: Side
    qty: float
    stop_loss: float
    take_profit: float
    reason: str = "SIGNAL"


class BacktestEngine:
    """
    Исполнение:
    - сигнал формируем по CLOSE свечи
    - вход исполняем по OPEN следующей свечи
    - SL/TP проверяем по OHLC текущей свечи (приоритет: STOP -> TAKE)
        """
    def __init__(
        self,
        symbol: str,
        strategy,
        start_equity: float = 100_000.0,
        commission_rate: float = 0.0004,
        max_leverage: float = 1.0,
        risk: Optional[RiskManager] = None,
        atr_period: int = 14,
        fill_policy: str = "worst",  # "worst" | "best" | "open" | "close"
    ):
        self.symbol = symbol
        self.strategy = strategy
        self.risk = risk or RiskManager(equity=start_equity)
        self.atr = ATRCalc(period=atr_period)
        self.fill_policy = fill_policy  # ✅ тут правильно

        self.broker = BrokerSim(
            start_equity=start_equity,
            commission=PercentCommission(rate=commission_rate),
            max_leverage=max_leverage,
        )

        self._pending: Optional[PendingEntry] = None

    def _check_intrabar_exit(self, c: Candle) -> Optional[tuple[str, float]]:
        """
        Возвращает (reason, exit_price) или None.

        Если в одной свече задеты и SL и TP:
          - fill_policy="worst": STOP
          - fill_policy="best":  TAKE
          - fill_policy="open":  кто ближе к c.open
          - fill_policy="close": кто ближе к c.close
        """
        pos = self.broker.position
        if pos is None:
            return None

        if pos.is_long():
            hit_stop = c.low <= pos.stop_loss
            hit_take = c.high >= pos.take_profit
            stop_price = pos.stop_loss
            take_price = pos.take_profit
        else:  # SHORT
            hit_stop = c.high >= pos.stop_loss
            hit_take = c.low <= pos.take_profit
            stop_price = pos.stop_loss
            take_price = pos.take_profit

        if hit_stop and hit_take:
            if self.fill_policy == "best":
                return ("TAKE", take_price)

            if self.fill_policy == "open":
                dist_stop = abs(c.open - stop_price)
                dist_take = abs(c.open - take_price)
                return ("TAKE", take_price) if dist_take < dist_stop else ("STOP", stop_price)

            if self.fill_policy == "close":
                dist_stop = abs(c.close - stop_price)
                dist_take = abs(c.close - take_price)
                return ("TAKE", take_price) if dist_take < dist_stop else ("STOP", stop_price)

            return ("STOP", stop_price)  # worst/default

        if hit_stop:
            return ("STOP", stop_price)
        if hit_take:
            return ("TAKE", take_price)

        return None

    def _get_signal(self, candle: Candle, snapshot: MarketSnapshot) -> Signal:
        """
        Универсальный вызов стратегии:
        1) on_snapshot(snapshot)
        2) on_candle(candle)
        3) __call__(snapshot) или __call__(candle)
        """
        s = self.strategy

        if hasattr(s, "on_snapshot"):
            sig = s.on_snapshot(snapshot)
        elif hasattr(s, "on_candle"):
            sig = s.on_candle(candle)
        elif callable(s):
            try:
                sig = s(snapshot)
            except TypeError:
                sig = s(candle)
        else:
            sig = Signal.HOLD

        # нормализация
        if sig is None:
            return Signal.HOLD

        # если вдруг вернули строку "BUY"/"SELL"/"HOLD"
        if isinstance(sig, str):
            try:
                return Signal(sig)
            except ValueError:
                return Signal.HOLD

        return sig

    def run(self, candles: list[Candle]) -> BrokerSim:
        for i, c in enumerate(candles):
            # 1) если был сигнал на прошлом баре — исполняем вход по OPEN текущего бара
            if self._pending is not None and self.broker.position is None:
                p = self._pending
                self.broker.open_position(
                    symbol=self.symbol,
                    side=p.side,
                    price=c.open,
                    qty=p.qty,
                    stop_loss=p.stop_loss,
                    take_profit=p.take_profit,
                    ts=c.ts,
                )
                self._pending = None

            # 2) проверка SL/TP внутри бара (OHLC)
            exit_hit = self._check_intrabar_exit(c)
            if exit_hit:
                reason, px = exit_hit
                self.broker.close_position(price=px, ts=c.ts, reason=reason)

            # 3) считаем ATR (на текущей свече)
            atr_val = self.atr.update(c) or 0.01

            # 4) стратегия принимает решение по CLOSE
            snapshot = MarketSnapshot(
                symbol=self.symbol,
                price=c.close,
                bid_volume=None,
                ask_volume=None,
                atr=atr_val,
            )
            sig = self._get_signal(c, snapshot)

            if sig == Signal.HOLD:
                continue

            # 5) если позиции нет и нет pending — создаём pending на следующий бар
            if self.broker.position is None and self._pending is None and i + 1 < len(candles):
                direction = "LONG" if sig == Signal.BUY else "SHORT"
                trade = self.risk.calculate(
                    entry_price=c.close,      # расчёт от close (сигнал)
                    atr=atr_val,
                    direction=direction,
                )
                side: Side = "LONG" if sig == Signal.BUY else "SHORT"
                self._pending = PendingEntry(
                    side=side,
                    qty=trade.qty,
                    stop_loss=trade.stop_loss,
                    take_profit=trade.take_profit,
                    reason="SIGNAL",
                )

        # если осталась позиция — можно закрыть по last close (MVP решение)
        if self.broker.position is not None and candles:
            last = candles[-1]
            self.broker.close_position(price=last.close, ts=last.ts, reason="EOD")

        return self.broker
