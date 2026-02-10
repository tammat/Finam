from finam_bot.risk_v2.verdict import RiskVerdict
from finam_bot.risk_v2.config import RiskConfig


class RiskEngineV21:
    def __init__(self, storage, config: RiskConfig):
        self.storage = storage
        self.cfg = config

    # --- загрузка позиций ---
    def _load_positions(self):
        rows = self.storage.conn.execute(
            """
            SELECT instrument, qty, side, avg_price, realized_pnl
            FROM positions
            WHERE qty != 0
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

    # --- расчёт реального риска позиции ---
    def _position_risk(self, entry, stop, qty):
        return abs(entry - stop) * abs(qty)

    # --- основной метод ---
    def check_entry(
        self,
        instrument: str,
        side: str,
        entry_price: float,
        stop_price: float,
    ) -> RiskVerdict:

        if entry_price <= 0 or stop_price <= 0:
            return RiskVerdict(False, "INVALID_PRICE")

        if entry_price == stop_price:
            return RiskVerdict(False, "ZERO_STOP_DISTANCE")

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

        # 3. расчёт qty из риска на сделку
        risk_per_unit = abs(entry_price - stop_price)
        max_qty = self.cfg.max_risk_per_trade / risk_per_unit

        if max_qty <= 0:
            return RiskVerdict(False, "RISK_TOO_HIGH")

        # 4. текущий суммарный риск портфеля
        total_risk = 0.0
        for p in positions:
            # временно считаем стоп = avg_price ± 1R
            # (позже можно хранить реальные стопы)
            assumed_stop = p["avg_price"] * (0.98 if p["side"] == "BUY" else 1.02)
            total_risk += abs(p["avg_price"] - assumed_stop) * abs(p["qty"])

        # 5. риск новой сделки
        new_trade_risk = risk_per_unit * max_qty

        if total_risk + new_trade_risk > self.cfg.max_total_risk:
            return RiskVerdict(False, "TOTAL_RISK_LIMIT")

        return RiskVerdict(True, "OK")