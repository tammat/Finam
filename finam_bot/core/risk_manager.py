# finam_bot/core/risk_manager.py

from dataclasses import dataclass


@dataclass
class RiskParams:
    qty: float
    stop_loss: float
    take_profit: float
    risk_amount: float


class RiskManager:
    """
    S4 Risk Manager
    - Fixed % risk per trade
    - SL / TP based on ATR
    - No real trading logic (TEST SAFE)
    """

    def __init__(
        self,
        equity: float,
        risk_pct: float = 0.01,     # 1% от капитала
        sl_atr: float = 1.5,        # SL = 1.5 ATR
        tp_atr: float = 3.0,        # TP = 3.0 ATR
        min_qty: float = 1.0,       # минимальный размер контракта
        max_qty: float = 100.0,     # защита от безумных объёмов
    ):
        self.equity = equity
        self.risk_pct = risk_pct
        self.sl_atr = sl_atr
        self.tp_atr = tp_atr
        self.min_qty = min_qty
        self.max_qty = max_qty

    def calculate(
        self,
        entry_price: float,
        atr: float,
        direction: str,
    ) -> RiskParams | None:
        """
        Возвращает параметры сделки или None, если вход запрещён
        """

        # 🛑 Базовые проверки
        if atr <= 0:
            return None

        risk_amount = self.equity * self.risk_pct
        stop_distance = atr * self.sl_atr

        if stop_distance <= 0:
            return None

        qty = risk_amount / stop_distance

        # 🔒 Ограничения
        if qty < self.min_qty:
            return None

        qty = min(qty, self.max_qty)

        # 🎯 SL / TP
        if direction == "LONG":
            stop_loss = entry_price - stop_distance
            take_profit = entry_price + atr * self.tp_atr
        elif direction == "SHORT":
            stop_loss = entry_price + stop_distance
            take_profit = entry_price - atr * self.tp_atr
        else:
            return None

        return RiskParams(
            qty=round(qty, 2),
            stop_loss=round(stop_loss, 4),
            take_profit=round(take_profit, 4),
            risk_amount=round(risk_amount, 2),
        )
