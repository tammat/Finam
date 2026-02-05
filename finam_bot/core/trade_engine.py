# finam_bot/core/trade_engine.py

from typing import Optional
from finam_bot.core.trade_stats import TradeStats
from finam_bot.core.position import Position
from finam_bot.core.signals import Signal
from finam_bot.core.market_snapshot import MarketSnapshot
from finam_bot.core.risk_manager import RiskManager
from finam_bot.strategies.order_flow_pullback import OrderFlowPullbackStrategy
from finam_bot.core.equity_tracker import EquityTracker

print("🔥 LOADED trade_engine.py FROM:", __file__)

class TradeEngine:
    """
    S5.B — TradeEngine with cooldown & risk manager
    READ-ONLY (no real orders)
    """

    def __init__(self, symbol: str, equity: float = 100_000):
        from finam_bot.core.trade_logger import TradeLogger
        from finam_bot.core.equity import EquityCurve

        self.equity_curve = EquityCurve(start_equity=equity)
        self.logger = TradeLogger()
        self.symbol = symbol
        self.stats = TradeStats()
        # --- state ---
        self.position: Optional[Position] = None
        self.total_pnl: float = 0.0
        # S5.C
        self.cooldown_bars = 3
        self.cooldown_left = 0

        # --- strategy & risk ---
        self.strategy = OrderFlowPullbackStrategy()
        self.risk = RiskManager(equity=equity)
        self.equity = EquityTracker(start_equity=equity)

        # --- S5.B discipline ---
        self.bar_index: int = 0
        self.last_trade_bar: int = -999
        self.cooldown_bars: int = 3
        self.cooldown_bars = 2
        self.cooldown_left = 0
        # --- S5.B control ---
        self.bar_index = 0
        self.cooldown_bars = 2        # сколько баров ждать после закрытия
        self.cooldown_left = 0

        self.last_trade_bar = None    # чтобы не входить 2 раза в один бар

    def on_market_data(self, snapshot: MarketSnapshot):

        # 1️⃣ cooldown после сделки
        if self.cooldown_left > 0:
            self.cooldown_left -= 1
            return
        if self.position:
            exit_reason = self.position.check_exit(snapshot.price)

            if exit_reason:
                pnl = self.position.close(snapshot.price)
                self.total_pnl += pnl
                self.equity.on_trade_exit(
                    bar=self.bar_index,
                    pnl=pnl,
                    reason=exit_reason,
                )

                # 🔽 статистика
                self.stats.on_trade_exit(
                    pnl=pnl,
                    equity=self.equity.equity                )
                # 🔽 логер
                self.logger.log(
                    symbol=self.symbol,
                    side=self.position.side,
                    entry=self.position.entry_price,
                    exit=snapshot.price,
                    qty=self.position.qty,
                    pnl=pnl,
                    reason=exit_reason,
                )
                self.equity.on_trade_exit(
                    bar=self.bar_index,
                    pnl=pnl,
                    reason=exit_reason,
                )
                self.stats = TradeStats()
                print(f"🔁 EXIT {exit_reason} PnL={pnl:.2f}")

                self.position = None
                self.cooldown_left = self.cooldown_bars

            return
        # 3️⃣ если позиции нет — ищем сигнал
        signal = self.strategy.on_snapshot(snapshot)

        if signal == Signal.HOLD:
            return

        # 4️⃣ риск-менеджмент
        trade = self.risk.calculate(
            entry_price=snapshot.price,
            atr=snapshot.atr or 0.01,
            direction="LONG" if signal == Signal.BUY else "SHORT",
        )

        side = "LONG" if signal == Signal.BUY else "SHORT"

        print(
            f"📊 {snapshot.symbol} {side} @ {snapshot.price} | "
            f"qty={trade.qty} SL={trade.stop_loss} TP={trade.take_profit}"
        )

        # 5️⃣ открытие позиции
        self._open(
            side=side,
            price=snapshot.price,
        
            qty=trade.qty,
            stop_loss=trade.stop_loss,
            take_profit=trade.take_profit,
        )

    def _open(
        self,
        side: str,
        price: float,
        qty: float,
        stop_loss: float,
        take_profit: float,
    ):
        self.position = Position(
            symbol=self.symbol,
            side=side,
            qty=qty,
            entry_price=price,
            stop_loss=stop_loss,
            take_profit=take_profit,
        )

        print(f"📈 Открыта {side} @ {price} | qty={qty}")
        
    def status(self):
        return {
            "symbol": self.symbol,
            "equity": self.equity.current,
            "total_pnl": self.total_pnl,
            "trades": self.stats.trades,
            "wins": self.stats.wins,
            "losses": self.stats.losses,
            "winrate": round(self.stats.winrate, 2),
            "expectancy": round(self.stats.expectancy, 2),
            "max_drawdown": round(self.stats.max_drawdown, 2),
        }
