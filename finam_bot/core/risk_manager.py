# finam_bot/core/risk_manager.py

from datetime import date


class RiskManager:
    """
    Professional risk management layer
    """

    def __init__(
        self,
        capital: float,
        risk_per_trade: float = 0.01,
        max_trades_per_day: int = 5,
        max_daily_loss: float = 0.03,
        max_consecutive_losses: int = 3,
    ):
        self.capital = capital
        self.risk_per_trade = risk_per_trade
        self.max_trades_per_day = max_trades_per_day
        self.max_daily_loss = max_daily_loss
        self.max_consecutive_losses = max_consecutive_losses

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

    # ===== POSITION SIZE =====

    def position_size(self, stop_distance: float) -> int:
        """
        Calculates position size based on fixed risk
        """
        if stop_distance <= 0:
            return 0

        risk_amount = self.capital * self.risk_per_trade
        size = risk_amount / stop_distance

        return max(int(size), 0)

    # ===== UPDATE AFTER TRADE =====

    def on_trade_closed(self, pnl: float):
        self._check_new_day()

        self.trades_today += 1
        self.daily_pnl += pnl

        if pnl < 0:
            self.consecutive_losses += 1
        else:
            self.consecutive_losses = 0
