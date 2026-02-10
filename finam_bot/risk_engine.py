from datetime import date
from decimal import Decimal
from finam_bot.storage_sqlite import StorageSQLite
from finam_bot.risk_config import (
    MAX_DAILY_LOSS,
    MAX_TRADE_RISK,
    MAX_TRADES_PER_DAY,
    KILL_SWITCH_KEY,
)


class RiskEngine:
    def __init__(self, storage: StorageSQLite, capital: Decimal):
        self.storage = storage
        self.capital = capital

    def is_killed(self) -> bool:
        return self.storage.get_risk_flag(KILL_SWITCH_KEY, default="OFF") == "ON"

    def trades_today(self) -> int:
        today = date.today().isoformat()
        row = self.storage.conn.execute(
            "SELECT COUNT(*) AS cnt FROM trades WHERE substr(ts,1,10) = ?",
            (today,),
        ).fetchone()
        return int(row["cnt"])

    def daily_pnl(self) -> Decimal:
        """
        Пока считаем простой cashflow-based индикатор:
        BUY -> минус, SELL -> плюс.
        Для лимитов потерь этого достаточно на старте.
        """
        today = date.today().isoformat()
        row = self.storage.conn.execute(
            """
            SELECT SUM(
                qty * price *
                CASE WHEN side IN ('SELL','SIDE_SELL') THEN 1 ELSE -1 END
            ) AS pnl
            FROM trades
            WHERE substr(ts,1,10) = ?
            """,
            (today,),
        ).fetchone()
        return Decimal(str(row["pnl"] or 0))

    def allow_trade(self, risk_amount: Decimal) -> tuple[bool, str]:
        if self.is_killed():
            return False, "KILL_SWITCH_ACTIVE"

        if self.trades_today() >= MAX_TRADES_PER_DAY:
            return False, "MAX_TRADES_EXCEEDED"

        daily_loss = self.daily_pnl()
        if daily_loss < -self.capital * MAX_DAILY_LOSS:
            self.storage.set_risk_flag(KILL_SWITCH_KEY, "ON")
            return False, "MAX_DAILY_LOSS"

        if risk_amount > self.capital * MAX_TRADE_RISK:
            return False, "TRADE_RISK_TOO_HIGH"

        return True, "OK"