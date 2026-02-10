from finam_bot.instruments import asset_class_by_symbol
from finam_bot.risk_config import RiskConfigV22

class RiskEngineV22:
    def __init__(self, storage, config: RiskConfigV22):
        self.storage = storage
        self.cfg = config

    def check(self, qty, signal):
        asset_class = asset_class_by_symbol(signal.symbol)

        # 1) лимит позиций по классу
        open_cnt = self.storage.count_open_positions_by_class(asset_class)
        if open_cnt >= self.cfg.max_positions_by_class.get(asset_class, 0):
            return False, "MAX_POSITIONS_BY_CLASS"

        # 2) совокупный риск по классу
        total_risk = self.storage.get_total_risk_by_class(asset_class)
        trade_risk = abs(signal.entry - signal.stop) * qty
        if total_risk + trade_risk > self.cfg.max_total_risk_by_class.get(asset_class, 0):
            return False, "TOTAL_RISK_BY_CLASS"

        # 3) риск на сделку
        if trade_risk > self.cfg.max_risk_per_trade:
            return False, "TRADE_RISK_LIMIT"

        return True, "OK"