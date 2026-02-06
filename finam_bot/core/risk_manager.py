from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


Direction = Literal["LONG", "SHORT"]


@dataclass(frozen=True)
class TradePlan:
    qty: float
    stop_loss: float
    take_profit: float


class RiskManager:
    """
    Простой риск-менеджер для бэктеста.

    - risk_pct: доля капитала, которую мы готовы потерять на сделку (по SL)
    - sl_atr_mult/tp_atr_mult: SL/TP в единицах ATR
    """

    def __init__(
        self,
        capital: float | None = None,
        equity: float | None = None,
        risk_pct: float = 0.01,
        sl_atr_mult: float = 1.0,
        tp_atr_mult: float = 1.0,
        min_stop: float = 0.01,
    ):
        # совместимость: раньше могли передавать equity=...
        if capital is None and equity is None:
            raise ValueError("RiskManager requires capital or equity")
        self.capital = float(capital if capital is not None else equity)
        self.risk_pct = float(risk_pct)
        self.sl_atr_mult = float(sl_atr_mult)
        self.tp_atr_mult = float(tp_atr_mult)
        self.min_stop = float(min_stop)

    def position_size(self, stop_distance: float) -> float:
        """
        Кол-во контрактов/акций так, чтобы риск по SL был <= capital*risk_pct.
        """
        stop_distance = max(float(stop_distance), self.min_stop)
        risk_amount = self.capital * self.risk_pct
        return risk_amount / stop_distance

    def calculate(
        self,
        entry_price: float,
        atr: float,
        direction: Direction,
    ) -> TradePlan:
        """
        Возвращает план сделки: qty/SL/TP.
        """
        entry_price = float(entry_price)
        atr = float(atr)

        sl_dist = max(atr * self.sl_atr_mult, self.min_stop)
        tp_dist = max(atr * self.tp_atr_mult, self.min_stop)

        qty = float(self.position_size(sl_dist))

        if direction == "LONG":
            stop_loss = entry_price - sl_dist
            take_profit = entry_price + tp_dist
        else:
            stop_loss = entry_price + sl_dist
            take_profit = entry_price - tp_dist

        return TradePlan(qty=qty, stop_loss=stop_loss, take_profit=take_profit)
