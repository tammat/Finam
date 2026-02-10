from dataclasses import dataclass

@dataclass(frozen=True)
class RiskConfig:
    max_positions: int = 30
    max_risk_per_trade: float = 5_000.0      # ₽
    max_total_risk: float = 15_000.0          # ₽
    forbid_averaging: bool = True