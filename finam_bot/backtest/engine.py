from __future__ import annotations

import inspect
from dataclasses import dataclass
from typing import Optional, Literal, Sequence

from finam_bot.backtest.models import Candle
from finam_bot.backtest.broker import BrokerSim, PercentCommission
from finam_bot.core.market_snapshot import MarketSnapshot
from finam_bot.core.signals import Signal
from finam_bot.core.risk_manager import RiskManager

# В проекте ATR реализован как finam_bot.core.atr.ATR
from finam_bot.core.atr import ATR as ATRCalc

try:
    from finam_bot.backtest.synthetic import generate_synthetic_candles, generate_synthetic_orderflow
except Exception:  # pragma: no cover
    generate_synthetic_candles = None
    generate_synthetic_orderflow = None

Side = Literal["LONG", "SHORT"]
FillPolicy = Literal["worst", "best"]


@dataclass
class PendingEntry:
    side: Side
    qty: float
    stop_loss: float
    take_profit: float


class BacktestEngine:
    """
    Минимальный backtest engine (OHLC intrabar SL/TP, комиссия, плечо).

    - Сигнал генерируем на CLOSE свечи i
    - Вход исполняем на OPEN свечи i+1
    - Выход (SL/TP) проверяем внутри каждой свечи по OHLC

    fill_policy:
      - "worst": если в одной свече задеты и SL и TP — выбираем худший исход
      - "best":  если в одной свече задеты и SL и TP — выбираем лучший исход
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
        fill_policy: FillPolicy = "worst",
    ):
        self.symbol = symbol
        self.equity_curve: list[float] = []
        self.strategy = strategy
        self.risk = risk or RiskManager(equity=start_equity)
        self.atr = ATRCalc(period=atr_period)
        self.fill_policy: FillPolicy = fill_policy

        self.broker = BrokerSim(
            start_equity=start_equity,
            commission=PercentCommission(rate=commission_rate),
            max_leverage=max_leverage,
        )
        self._pending: Optional[PendingEntry] = None

    # ------------------------- helpers -------------------------

    def _cap_qty_to_margin(self, qty: float, price: float) -> float:
        """
        BrokerSim margin rule: margin = abs(qty*price)/max_leverage <= cash
        """
        if qty <= 0 or price <= 0:
            return 0.0
        max_qty = (self.broker.cash * self.broker.max_leverage) / price
        return max(0.0, min(float(qty), float(max_qty)))

    def _fallback_trade(self, side: Side, price: float, atr: float):
        """
        Если RiskManager.calculate(...) несовместим — считаем сами:
        - риск 1% капитала
        - SL = 2*ATR, TP = 2*ATR
        - qty = risk_money / stop_dist
        """
        equity = float(getattr(self.broker, "equity", self.broker.cash))
        atr = max(float(atr), 1e-9)

        risk_pct = 0.01
        stop_dist = 2.0 * atr
        risk_money = equity * risk_pct
        qty = risk_money / stop_dist

        if side == "LONG":
            stop_loss = price - stop_dist
            take_profit = price + stop_dist
        else:
            stop_loss = price + stop_dist
            take_profit = price - stop_dist

        class _Trade:
            pass

        t = _Trade()
        t.qty = float(qty)
        t.stop_loss = float(stop_loss)
        t.take_profit = float(take_profit)
        return t

    def _risk_calculate(self, side: Side, price: float, atr: float):
        """
        Универсальный вызов risk.calculate(...) с авто-подбором аргументов.
        Если не получилось — fallback.
        """
        if not hasattr(self.risk, "calculate"):
            return self._fallback_trade(side=side, price=price, atr=atr)

        fn = self.risk.calculate
        try:
            params = set(inspect.signature(fn).parameters.keys())
        except Exception:
            return self._fallback_trade(side=side, price=price, atr=atr)

        kwargs = {}

        if "side" in params:
            kwargs["side"] = side
        elif "signal" in params:
            kwargs["signal"] = side

        if "price" in params:
            kwargs["price"] = price
        elif "entry_price" in params:
            kwargs["entry_price"] = price

        if "atr" in params:
            kwargs["atr"] = atr

        if "equity" in params:
            kwargs["equity"] = float(getattr(self.broker, "equity", self.broker.cash))
        if "capital" in params:
            kwargs["capital"] = float(getattr(self.broker, "equity", self.broker.cash))

        try:
            return fn(**kwargs)
        except TypeError:
            return self._fallback_trade(side=side, price=price, atr=atr)

    def _check_intrabar_exit(self, c: Candle) -> Optional[tuple[str, float]]:
        """
        Возвращает (reason, exit_price) или None.
        Если в одной свече задеты и SL и TP — решаем по fill_policy.
        """
        pos = self.broker.position
        if pos is None:
            return None

        if pos.is_long():
            hit_stop = c.low <= pos.stop_loss
            hit_take = c.high >= pos.take_profit

            if hit_stop and hit_take:
                if self.fill_policy == "best":
                    return ("TAKE", pos.take_profit)
                return ("STOP", pos.stop_loss)

            if hit_stop:
                return ("STOP", pos.stop_loss)
            if hit_take:
                return ("TAKE", pos.take_profit)

        else:  # SHORT
            hit_stop = c.high >= pos.stop_loss
            hit_take = c.low <= pos.take_profit

            if hit_stop and hit_take:
                if self.fill_policy == "best":
                    return ("TAKE", pos.take_profit)
                return ("STOP", pos.stop_loss)

            if hit_stop:
                return ("STOP", pos.stop_loss)
            if hit_take:
                return ("TAKE", pos.take_profit)

        return None

    # ------------------------- main API -------------------------

    def run(
        self,
        candles: Sequence[Candle],
        *,
        orderflow: Optional[Sequence[object]] = None,
        atr_floor: float = 0.0,
    ) -> BrokerSim:
        """
        orderflow: список такого же размера, как candles (опционально).
        atr_floor: минимальный ATR, чтобы не улетал размер позиции на первых барах.
        """
        candles = list(candles)
        self.equity_curve = [self.broker.equity]
        for i, c in enumerate(candles):
            # 1) исполняем отложенный вход по OPEN текущего бара
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

            # 2) SL/TP внутри бара
            exit_hit = self._check_intrabar_exit(c)
            if exit_hit:
                reason, px = exit_hit
                self.broker.close_position(price=px, ts=c.ts, reason=reason)

            # 3) ATR (на текущей свече)
            atr_raw = self.atr.update(c)
            atr_val = max(float(atr_raw or 0.0), float(atr_floor))

            # 4) snapshot (CLOSE)
            snap_kwargs = dict(
                symbol=self.symbol,
                price=c.close,
                bid_volume=None,
                ask_volume=None,
                atr=atr_val,
            )

            if orderflow is not None and i < len(orderflow):
                of = orderflow[i]
                snap_kwargs["bid_volume"] = getattr(of, "bid_volume", None) or (of.get("bid_volume") if isinstance(of, dict) else None)
                snap_kwargs["ask_volume"] = getattr(of, "ask_volume", None) or (of.get("ask_volume") if isinstance(of, dict) else None)
                snap_kwargs["prices"] = getattr(of, "prices", None) or (of.get("prices") if isinstance(of, dict) else None)
                snap_kwargs["volumes"] = getattr(of, "volumes", None) or (of.get("volumes") if isinstance(of, dict) else None)

            snapshot = MarketSnapshot(**snap_kwargs)
            # 4a) стратегия: on_snapshot | on_candle (return) | on_candle+generate_signal | callable
            sig_raw = None

            if hasattr(self.strategy, "on_snapshot"):
                sig_raw = self.strategy.on_snapshot(snapshot)

            elif hasattr(self.strategy, "on_candle"):
                # пробуем передать snapshot (как в твоём тесте)
                try:
                    sig_raw = self.strategy.on_candle(c, snapshot=snapshot)
                except TypeError:
                    try:
                        sig_raw = self.strategy.on_candle(c, snapshot)
                    except TypeError:
                        sig_raw = self.strategy.on_candle(c)

                # если у стратегии есть генератор — он главнее
                if hasattr(self.strategy, "generate_signal"):
                    sig_raw = self.strategy.generate_signal()

            elif callable(self.strategy):
                sig_raw = self.strategy(snapshot)

            sig: Signal = self._normalize_signal(sig_raw)

            # 5) pending entry (если FLAT и не последний бар)
            if self.broker.position is None and self._pending is None and i < len(candles) - 1:
                if sig == Signal.BUY:
                    side: Optional[Side] = "LONG"
                elif sig == Signal.SELL:
                    side = "SHORT"
                else:
                    side = None

                if side:
                    trade = self._risk_calculate(side=side, price=c.close, atr=max(atr_val, 1e-9))
                    qty = float(getattr(trade, "qty", 0.0))
                    qty = self._cap_qty_to_margin(qty, price=candles[i + 1].open)

                    if qty > 0:
                        self._pending = PendingEntry(
                            side=side,
                            qty=qty,
                            stop_loss=float(trade.stop_loss),
                            take_profit=float(trade.take_profit),
                        )
                
            self.equity_curve.append(self.broker.equity)

        # EOD close
        if self.broker.position is not None and candles:
            self.broker.close_position(price=candles[-1].close, ts=candles[-1].ts, reason="EOD")

        # equity curve: always include final equity
        self.equity_curve.append(self.broker.equity)

        return self.broker

    def _normalize_signal(self, sig):
        # уже enum
        if isinstance(sig, Signal):
            return sig

        # строка "BUY"/"SELL"/"HOLD"
        if isinstance(sig, str):
            s = sig.strip().upper()
            if s == "BUY":
                return Signal.BUY
            if s == "SELL":
                return Signal.SELL
            return Signal.HOLD

        # на всякий: Enum с .value
        if hasattr(sig, "value") and isinstance(sig.value, str):
            return self._normalize_signal(sig.value)

        return Signal.HOLD

    def run_synthetic(
        self,
        n: int = 300,
        start_price: float = 100.0,
        mode: str = "mixed",
        drift: float = 0.02,
        volatility: float = 0.10,
        wick: float = 0.15,
        with_orderflow: bool = False,
        volume_base: float = 1000.0,
        volume_noise: float = 0.2,
        seed: int = 42,
        start_ts: Optional[int] = 1,
        ts_step: int = 1,
        atr_floor: float = 0.01,
    ) -> BrokerSim:
        """
        One-liner backtest without CSV:
            BacktestEngine(...).run_synthetic(n=500, with_orderflow=True)
        """
        if generate_synthetic_candles is None:
            raise RuntimeError("synthetic generator is not available")

        candles = generate_synthetic_candles(
            n=n,
            start_price=start_price,
            mode=mode,
            drift=drift,
            volatility=volatility,
            wick=wick,
            start_ts=start_ts,
            ts_step=ts_step,
            seed=seed,
            volume_base=volume_base,
            volume_noise=volume_noise,
        )

        of_list = None
        if with_orderflow:
            if generate_synthetic_orderflow is None:
                raise RuntimeError("generate_synthetic_orderflow is missing in finam_bot.backtest.synthetic")
            of_list = generate_synthetic_orderflow(
                n=len(candles),
                volume_base=volume_base,
                volume_noise=volume_noise,
                seed=seed,
            )

        return self.run(candles, orderflow=of_list, atr_floor=atr_floor)
