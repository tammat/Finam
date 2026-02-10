# finam_bot/risk_engine_v2_1.py

from finam_bot.storage_sqlite import StorageSQLite
from finam_bot.risk_config import RiskConfigV21


class RiskEngineV21:
    def __init__(self, storage: StorageSQLite, config: RiskConfigV21):
        self.storage = storage
        self.cfg = config

    def check(self, qty, signal):
        """
        qty      — рассчитанное количество
        signal   — объект сигнала (symbol, side, entry, stop)
        """

        # 1. Проверка макс. количества позиций
        open_positions = self.storage.count_open_positions()
        if open_positions >= self.cfg.max_positions:
            return False, "MAX_POSITIONS_REACHED"

        # 2. Проверка совокупного риска
        total_risk = self.storage.get_total_risk()
        trade_risk = abs(signal.entry - signal.stop) * qty

        if total_risk + trade_risk > self.cfg.max_total_risk:
            return False, "TOTAL_RISK_LIMIT"

        # 3. Проверка риска на сделку
        if trade_risk > self.cfg.max_risk_per_trade:
            return False, "TRADE_RISK_LIMIT"

        return True, "OK"