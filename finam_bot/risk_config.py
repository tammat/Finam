from decimal import Decimal

# Лимиты (стартовые, потом вынесем в .env)
MAX_DAILY_LOSS = Decimal("0.02")      # 2% от капитала
MAX_TRADE_RISK = Decimal("0.005")     # 0.5% на сделку
MAX_TRADES_PER_DAY = 5

# Флаги
KILL_SWITCH_KEY = "KILL_SWITCH"       # ON / OFF

from dataclasses import dataclass


@dataclass
class RiskConfigV21:
    max_positions: int = 10
    max_total_risk: float = 50_000
    max_risk_per_trade: float = 10_000
#from dataclasses import dataclass

@dataclass
class RiskConfigV22:
    max_positions_by_class: dict = None
    max_total_risk_by_class: dict = None
    max_risk_per_trade: float = 10_000

    def __post_init__(self):
        self.max_positions_by_class = self.max_positions_by_class or {
            "futures": 1,
            "stocks": 10,
            "bonds": 20,
        }
        self.max_total_risk_by_class = self.max_total_risk_by_class or {
            "futures": 30_000,
            "stocks": 50_000,
            "bonds": 20_000,
        }