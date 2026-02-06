# /Users/alex/Finam/finam_bot/core/risk_manager.py
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
    Risk manager with equity-based sizing.

    - risk_pct is applied to current equity (preferred) or capital as fallback.
    - stop distance is ATR * sl_atr_mult with floor min_stop.
    - take distance is ATR * tp_atr_mult.
    """

    def __init__(
        self,
        equity: float = 100_000.0,
        *,
        capital: Optional[float] = None,   # compatibility alias
        risk_pct: float = 0.01,            # 1% risk per trade by default
        sl_atr_mult: float = 1.0,
        tp_atr_mult: float = 1.0,
        min_stop: float = 0.01,
    ):
        # keep BOTH names for compatibility
        self.equity = float(equity if capital is None else capital)
        self.capital = float(self.equity)

        self.risk_pct = float(risk_pct)
        self.sl_atr_mult = float(sl_atr_mult)
        self.tp_atr_mult = float(tp_atr_mult)
        self.min_stop = float(min_stop)

    # ---- compatibility helper (used in tests / external code) ----
    def position_size(self, stop_dist: float, *, equity: Optional[float] = None, capital: Optional[float] = None) -> float:
        base = equity
        if base is None:
            base = capital
        if base is None:
            base = self.equity

        stop = max(float(stop_dist), float(self.min_stop))
        risk_amount = float(base) * float(self.risk_pct)

        if stop <= 0 or risk_amount <= 0:
            return 0.0
        return risk_amount / stop

    # ---- main API (engine uses it) ----
    def calculate(
        self,
        *,
        price: float,
        atr: float,
        direction: Direction | str | None = None,
        side: Direction | str | None = None,
        signal: Direction | str | None = None,
        equity: Optional[float] = None,
        capital: Optional[float] = None,
        **_: Any,
    ) -> TradePlan:
        # normalize direction
        d = direction or side or signal or "LONG"
        d = str(d).upper()
        if d in ("BUY", "LONG"):
            d = "LONG"
        elif d in ("SELL", "SHORT"):
            d = "SHORT"
        else:
            d = "LONG"

        price = float(price)
        atr = max(float(atr), 0.0)

        stop_dist = max(atr * self.sl_atr_mult, self.min_stop)
        take_dist = max(atr * self.tp_atr_mult, self.min_stop)

        qty = self.position_size(stop_dist, equity=equity, capital=capital)

        if d == "LONG":
            stop_loss = price - stop_dist
            take_profit = price + take_dist
        else:
            stop_loss = price + stop_dist
            take_profit = price - take_dist

        return TradePlan(qty=float(qty), stop_loss=float(stop_loss), take_profit=float(take_profit))