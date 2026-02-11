# finam_bot/qty/calculator.py

import math
from dataclasses import dataclass
from finam_bot.qty.rules import QTY_RULES


class QtyCalculator:
    def __init__(self, max_risk_per_trade: float):
        self.max_risk = float(max_risk_per_trade)

    def calc(
        self,
        entry_price: float,
        stop_price: float,
        asset_class: str,
    ) -> float:
        """
        Расчёт количества позиции по risk-based логике.

        entry_price : цена входа
        stop_price  : цена стопа
        asset_class : FUTURES / STOCKS / BONDS / etc
        """

        # 1️⃣ правила для класса актива
        rules = QTY_RULES.get(asset_class)
        if rules is None:
            raise ValueError(f"Unknown asset_class: {asset_class}")

        # 2️⃣ риск на 1 контракт / акцию
        risk_per_unit = abs(entry_price - stop_price)
        if risk_per_unit <= 0:
            return 0.0

        # 3️⃣ сырой объём
        raw_qty = self.max_risk / risk_per_unit

        # 4️⃣ округление по шагу
        stepped_qty = math.floor(raw_qty / rules.step) * rules.step

        # 5️⃣ минимальный объём
        if stepped_qty < rules.min_qty:
            return 0.0

        return float(stepped_qty)