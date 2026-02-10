from finam_bot.risk_v2.verdict import RiskVerdict
from finam_bot.risk_v2.config import RiskConfig


class RiskEngineV2:
    def __init__(self, storage, config: RiskConfig):
        self.storage = storage
        self.cfg = config

    def _load_positions(self):
        rows = self.storage.conn.execute(
            """
            SELECT instrument, qty, side, avg_price
            FROM positions
            """
        ).fetchall()

        return [
            {
                "instrument": r["instrument"],
                "qty": r["qty"],
                "side": r["side"],
                "avg_price": r["avg_price"],
            }
            for r in rows
        ]

    def check_entry(
        self,
        instrument: str,
        side: str,
        entry_price: float,
        stop_price: float,
    ) -> RiskVerdict:

        positions = self._load_positions()

        # 1. лимит количества позиций
        if len(positions) >= self.cfg.max_positions:
            return RiskVerdict(False, "MAX_POSITIONS_REACHED")

        # 2. проверка существующей позиции
        for p in positions:
            if p["instrument"] == instrument:
                if p["side"] == side:
                    return RiskVerdict(False, "POSITION_ALREADY_OPEN")
                if self.cfg.forbid_averaging:
                    return RiskVerdict(False, "AVERAGING_FORBIDDEN")

        # 3. риск по сделке
        risk_per_unit = abs(entry_price - stop_price)
        if risk_per_unit <= 0:
            return RiskVerdict(False, "INVALID_STOP")

        qty_allowed = self.cfg.max_risk_per_trade / risk_per_unit
        if qty_allowed <= 0:
            return RiskVerdict(False, "RISK_LIMIT_ZERO_QTY")

        # 4. общий риск портфеля
        total_risk = 0.0
        for p in positions:
            total_risk += abs(p["avg_price"] * p["qty"]) * 0.02  # консервативная оценка

        if total_risk + self.cfg.max_risk_per_trade > self.cfg.max_total_risk:
            return RiskVerdict(False, "TOTAL_RISK_LIMIT")

        return RiskVerdict(True, "OK")