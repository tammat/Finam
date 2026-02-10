import math
from finam_bot.qty.rules import QtyRules


class QtyCalculator:
    def __init__(self, max_risk_per_trade: float):
        self.max_risk = max_risk_per_trade

    def calc(
        self,
        entry_price: float,
        stop_price: float,
        rules: QtyRules = QtyRules(),
    ) -> float:
        """
        Возвращает допустимое количество (>= 0).
        0 означает: вход запрещён.
        """
        if entry_price <= 0 or stop_price <= 0:
            return 0.0

        risk_per_unit = abs(entry_price - stop_price)
        if risk_per_unit <= 0:
            return 0.0

        raw_qty = self.max_risk / risk_per_unit

        # округление вниз по шагу
        stepped_qty = math.floor(raw_qty / rules.step) * rules.step

        if stepped_qty < rules.min_qty:
            return 0.0

        return stepped_qty