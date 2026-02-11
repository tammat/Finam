from dataclasses import dataclass
from typing import Tuple

# --- Конфигурация (ЗАФИКСИРОВАНА) ---

MAX_POSITIONS_BY_CLASS = {
    "FUTURES": 2,
    "EQUITY": 5,
    "BOND": 5,
    "ETF": 3,
    "CURRENCY": 2,
}

MAX_RISK_PCT_BY_CLASS = {
    "FUTURES": 0.02,     # 2%
    "EQUITY": 0.03,
    "BOND": 0.015,
    "ETF": 0.02,
    "CURRENCY": 0.01,
}

MAX_EXPOSURE_PCT_BY_CLASS = {
    "FUTURES": 0.30,
    "EQUITY": 0.50,
    "BOND": 0.60,
    "ETF": 0.30,
    "CURRENCY": 0.20,
}


# --- Verdict ---

@dataclass
class RiskVerdict:
    allowed: bool
    reason: str
    asset_class: str
    metric: float | None = None
    limit: float | None = None


# --- Engine ---

class RiskEngineV22:
    """
    Финальный риск-движок.
    asset_class — ОБЯЗАТЕЛЬНО.
    """

    def __init__(self, storage, equity: float):
        self.storage = storage
        self.equity = equity

    def check(self, *, qty: float, entry: float, stop: float, asset_class: str) -> RiskVerdict:
        if asset_class not in MAX_POSITIONS_BY_CLASS:
            return RiskVerdict(
                False,
                "UNKNOWN_ASSET_CLASS",
                asset_class
            )

        # 1. Количество позиций по классу
        open_positions = self.storage.count_open_positions(asset_class=asset_class)
        limit_positions = MAX_POSITIONS_BY_CLASS[asset_class]

        if open_positions >= limit_positions:
            return RiskVerdict(
                False,
                "MAX_POSITIONS_BY_CLASS",
                asset_class,
                open_positions,
                limit_positions
            )

        # 2. Риск сделки
        trade_risk = abs(entry - stop) * qty
        trade_risk_pct = trade_risk / self.equity

        max_risk_pct = MAX_RISK_PCT_BY_CLASS[asset_class]

        if trade_risk_pct > max_risk_pct:
            return RiskVerdict(
                False,
                "MAX_RISK_BY_CLASS",
                asset_class,
                trade_risk_pct,
                max_risk_pct
            )

        # 3. Совокупный риск по классу
        current_risk = self.storage.sum_open_risk(asset_class=asset_class)
        total_risk_pct = (current_risk + trade_risk) / self.equity

        if total_risk_pct > max_risk_pct:
            return RiskVerdict(
                False,
                "TOTAL_RISK_BY_CLASS",
                asset_class,
                total_risk_pct,
                max_risk_pct
            )

        # 4. Экспозиция по классу
        exposure = self.storage.sum_exposure(asset_class=asset_class)
        exposure_pct = (exposure + qty * entry) / self.equity

        max_exposure_pct = MAX_EXPOSURE_PCT_BY_CLASS[asset_class]

        if exposure_pct > max_exposure_pct:
            return RiskVerdict(
                False,
                "MAX_EXPOSURE_BY_CLASS",
                asset_class,
                exposure_pct,
                max_exposure_pct
            )

        return RiskVerdict(True, "OK", asset_class)