from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Literal

from finam_bot.backtest.models import Position, Trade

Side = Literal["LONG", "SHORT"]


@dataclass
class PercentCommission:
    """
    Комиссия как % от оборота (notional = price * qty).
    rate=0.0004 => 0.04%
    """
    rate: float = 0.0004
    min_fee: float = 0.0

    def calc(self, notional: float) -> float:
        fee = abs(notional) * self.rate
        if fee < self.min_fee:
            fee = self.min_fee
        return fee


class BrokerSim:
    """
    Мини-брокер:
    - одна позиция одновременно (для MVP)
    - плечо: max_leverage (маржинальное требование = notional / max_leverage)
    - комиссия на вход и выход
    """
    def __init__(
        self,
        start_equity: float,
        commission: Optional[PercentCommission] = None,
        max_leverage: float = 1.0,
    ):
        if max_leverage <= 0:
            raise ValueError("max_leverage must be > 0")

        self.start_equity = float(start_equity)
        self.cash = float(start_equity)
        self.equity = float(start_equity)
        self.max_leverage = float(max_leverage)
        self.commission = commission or PercentCommission()

        self.position: Optional[Position] = None
        self.used_margin: float = 0.0

        self.trades: list[Trade] = []

    def _margin_required(self, price: float, qty: float) -> float:
        notional = abs(price * qty)
        return notional / self.max_leverage

    def _apply_fee(self, fee: float) -> None:
        self.cash -= fee
        self.equity -= fee

    def open_position(
        self,
        symbol: str,
        side: Side,
        price: float,
        qty: float,
        stop_loss: float,
        take_profit: float,
        ts: Optional[int] = None,
    ) -> None:
        if self.position is not None:
            raise RuntimeError("Position already open")

        if qty <= 0:
            raise ValueError("qty must be > 0")

        margin = self._margin_required(price, qty)
        if self.cash < margin:
            raise RuntimeError(f"Not enough cash for margin: need={margin:.2f} have={self.cash:.2f}")

        # комиссия на вход
        fee_entry = self.commission.calc(price * qty)
        self._apply_fee(fee_entry)

        self.used_margin = margin
        self.position = Position(
            symbol=symbol,
            side=side,
            qty=qty,
            entry_price=price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            entry_ts=ts,
        )

        # сохраняем fee_entry на позиции (даже если поля нет в dataclass)
        setattr(self.position, "entry_fee", float(fee_entry))

    def close_position(
        self,
        price: float,
        ts: Optional[int] = None,
        reason: str = "EXIT",
    ) -> Trade:
        if self.position is None:
            raise RuntimeError("No open position")

        pos = self.position

        # комиссия на выход
        fee_exit = self.commission.calc(price * pos.qty)
        self._apply_fee(fee_exit)

        # PnL
        pnl = pos.unrealized_pnl(price)
        self.cash += pnl
        self.equity += pnl

        # освободили маржу/позицию
        self.used_margin = 0.0
        self.position = None

        fee_entry = float(getattr(pos, "entry_fee", 0.0))
        total_fees = fee_entry + float(fee_exit)

        trade = Trade(
            symbol=pos.symbol,
            side=pos.side,
            qty=pos.qty,
            entry_price=pos.entry_price,
            exit_price=price,
            entry_ts=pos.entry_ts,
            exit_ts=ts,
            pnl=float(pnl),
            fees=float(total_fees),
            reason=reason,
        )

        self.trades.append(trade)
        return trade