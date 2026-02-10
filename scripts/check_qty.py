from finam_bot.qty.calculator import QtyCalculator
from finam_bot.qty.rules import QtyRules
from finam_bot.risk_v2.config import RiskConfig


def main():
    cfg = RiskConfig()
    calc = QtyCalculator(cfg.max_risk_per_trade)

    qty = calc.calc(
        entry_price=3.20,
        stop_price=3.05,
        rules=QtyRules(min_qty=1, step=1),
    )

    print("QTY:", qty)


if __name__ == "__main__":
    main()