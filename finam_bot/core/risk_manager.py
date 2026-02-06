# finam_bot/core/risk_manager.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Literal, Any


Direction = Literal["LONG", "SHORT"]


@dataclass
class TradePlan:
    qty: float
    stop_loss: float
    take_profit: float


class RiskManager:
    """
    Универсальный RiskManager для бэктеста/лайва.

    Совместимость:
    - __init__ принимает: capital=..., equity=..., start_equity=...
    - хранит sl_atr_mult/tp_atr_mult (как ждёт backtest.run)
    - calculate принимает direction/side/signal и equity/capital override
    """

    def __init__(
        self,
        equity: Optional[float] = None,
        *,
        capital: Optional[float] = None,
        start_equity: Optional[float] = None,
        risk_pct: float = 0.01,
        sl_atr_mult: float = 1.0,
        tp_atr_mult: float = 1.0,
        min_stop: float = 0.01,
        **_: Any,  # чтобы не падать от лишних kwargs в старом коде
    ):
        base = (
            capital
            if capital is not None
            else equity
            if equity is not None
            else start_equity
            if start_equity is not None
            else 100_000.0
        )

        self.equity = float(base)
        self.capital = float(base)  # alias
        self.risk_pct = float(risk_pct)

        # поля, которые ожидает runner/backtest
        self.sl_atr_mult = float(sl_atr_mult)
        self.tp_atr_mult = float(tp_atr_mult)
        self.min_stop = float(min_stop)

    def calculate(
        self,
        *,
        direction: Optional[Direction | str] = None,
        side: Optional[Direction | str] = None,
        signal: Optional[Direction | str] = None,
        price: float,
        atr: float,
        equity: Optional[float] = None,
        capital: Optional[float] = None,
        **_: Any,
    ) -> TradePlan:
        """
        Возвращает план сделки: qty, stop_loss, take_profit.

        Приоритет выбора направления: direction > side > signal
        Приоритет базы для sizing: equity override > capital override > self.equity
        """

        dir_raw = direction or side or signal or "LONG"
        d = str(dir_raw).upper()
        is_long = d in ("LONG", "BUY")

        base_equity = (
            float(equity) if equity is not None
            else float(capital) if capital is not None
            else float(self.equity)
        )

        atr_val = max(float(atr), 0.0)
        stop_dist = max(self.min_stop, atr_val * self.sl_atr_mult)

        # risk in money per trade
        risk_money = max(0.0, base_equity * self.risk_pct)

        qty = 0.0
        if stop_dist > 0:
            qty = risk_money / stop_dist

        if is_long:
            stop_loss = float(price) - stop_dist
            take_profit = float(price) + max(self.min_stop, atr_val * self.tp_atr_mult)
        else:
            stop_loss = float(price) + stop_dist
            take_profit = float(price) - max(self.min_stop, atr_val * self.tp_atr_mult)

        return TradePlan(qty=qty, stop_loss=stop_loss, take_profit=take_profit)



    def position_size(
        self,
        stop_dist: float,
        *,
        equity: Optional[float] = None,
        capital: Optional[float] = None,
    ) -> float:
        """
        Backward-compatible helper used by tests.
        qty = (risk_pct * equity) / stop_dist
        """
        base_equity = (
            float(equity) if equity is not None
            else float(capital) if capital is not None
            else float(self.equity)
        )

        sd = float(stop_dist)
        if sd <= 0:
            return 0.0

        risk_money = max(0.0, base_equity * float(self.risk_pct))
        return risk_money / sd
