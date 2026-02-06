# finam_bot/core/risk_manager.py
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Optional, Literal


Side = Literal["LONG", "SHORT"]


@dataclass(frozen=True)
class TradePlan:
    qty: float
    stop_loss: float
    take_profit: float


class RiskManager:
    """
    Fixed fractional risk (% of equity) + daily limits.

    - risk_per_trade: доля капитала на риск (например 0.01 = 1%)
    - SL от ATR: stop_atr * ATR
    - TP через RR: take_rr * stop_distance
    """

    def __init__(
        self,
        capital: Optional[float] = None,
        *,
        equity: Optional[float] = None,  # алиас под BacktestEngine
        risk_per_trade: float = 0.01,
        max_trades_per_day: int = 5,
        max_daily_loss: float = 0.03,
        max_consecutive_losses: int = 3,
        # параметры модели SL/TP
        stop_atr: float = 1.5,
        take_rr: float = 2.0,
        # округление/минималки (под акции/фьючи можно менять)
        min_qty: float = 1.0,
        qty_step: float = 1.0,
    ):
        base = equity if equity is not None else (capital if capital is not None else 0.0)
        self.capital = float(base)

        self.risk_per_trade = float(risk_per_trade)
        self.max_trades_per_day = int(max_trades_per_day)
        self.max_daily_loss = float(max_daily_loss)
        self.max_consecutive_losses = int(max_consecutive_losses)

        self.stop_atr = float(stop_atr)
        self.take_rr = float(take_rr)

        self.min_qty = float(min_qty)
        self.qty_step = float(qty_step)

        self._reset_day()

    # ===== DAY CONTROL =====

    def _reset_day(self):
        self.current_day = date.today()
        self.trades_today = 0
        self.daily_pnl = 0.0
        self.consecutive_losses = 0

    def _check_new_day(self):
        if date.today() != self.current_day:
            self._reset_day()

    # ===== PERMISSION =====

    def allow_trade(self) -> bool:
        self._check_new_day()

        if self.trades_today >= self.max_trades_per_day:
            return False

        if self.daily_pnl <= -self.capital * self.max_daily_loss:
            return False

        if self.consecutive_losses >= self.max_consecutive_losses:
            return False

        return True

    # ===== HELPERS =====

    def update_capital(self, equity: float):
        """Зови этим после каждого бара/сделки, если хочешь чтобы лимиты/риск шли от актуального equity."""
        self.capital = float(equity)

    def _round_qty(self, qty: float) -> float:
        if qty <= 0:
            return 0.0
        step = self.qty_step if self.qty_step > 0 else 1.0
        rounded = (qty // step) * step
        if rounded < self.min_qty:
            return 0.0
        return float(rounded)

    # ===== MAIN API FOR ENGINE =====

    def calculate(
        self,
        *,
        side: Optional[Side] = None,
        signal: Optional[Side] = None,   # алиас
        price: float,
        atr: float,
        equity: Optional[float] = None,
        capital: Optional[float] = None,
    ) -> TradePlan:
        """
        Возвращает план сделки qty/SL/TP.

        Engine может передавать разные наборы аргументов — мы поддерживаем:
        - side или signal
        - equity или capital (если оба None — берём self.capital)
        """
        chosen_side = side or signal or "LONG"

        base_equity = (
            float(equity) if equity is not None
            else float(capital) if capital is not None
            else float(self.capital)
        )
        # обновляем капитал, чтобы дневные лимиты жили от актуального equity
        self.capital = base_equity

        # если торговля запрещена — вернём нулевой план
        if not self.allow_trade():
            return TradePlan(qty=0.0, stop_loss=price, take_profit=price)

        atr = float(atr)
        price = float(price)
        if atr <= 0 or price <= 0:
            return TradePlan(qty=0.0, stop_loss=price, take_profit=price)

        stop_dist = max(atr * self.stop_atr, 1e-9)
        risk_amount = base_equity * self.risk_per_trade

        raw_qty = risk_amount / stop_dist
        qty = self._round_qty(raw_qty)

        if qty <= 0:
            return TradePlan(qty=0.0, stop_loss=price, take_profit=price)

        if chosen_side == "LONG":
            sl = price - stop_dist
            tp = price + stop_dist * self.take_rr
        else:
            sl = price + stop_dist
            tp = price - stop_dist * self.take_rr

        return TradePlan(qty=qty, stop_loss=float(sl), take_profit=float(tp))

    # ===== UPDATE AFTER TRADE =====

    def on_trade_closed(self, pnl: float):
        self._check_new_day()

        self.trades_today += 1
        self.daily_pnl += float(pnl)

        if pnl < 0:
            self.consecutive_losses += 1
        else:
            self.consecutive_losses = 0
