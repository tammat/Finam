# finam_bot/storage_sqlite.py

import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Optional


class StorageSQLite:
    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            db_path = Path(__file__).parent / "data" / "finam.db"
        self.db_path = str(db_path)

        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row

        self._init_db()

    # ------------------------------------------------------------------
    # INIT
    # ------------------------------------------------------------------

    def _init_db(self):
        # TRADES
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS trades (
                id TEXT PRIMARY KEY,
                account_id TEXT NOT NULL,
                ts TEXT NOT NULL,
                symbol TEXT NOT NULL,
                side TEXT NOT NULL,
                qty REAL NOT NULL,
                price REAL NOT NULL,
                commission REAL,
                currency TEXT,
                raw_json TEXT
            )
            """
        )

        self.conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_trades_symbol_ts ON trades(symbol, ts)"
        )

        # POSITIONS
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS positions (
                instrument TEXT NOT NULL,
                side TEXT NOT NULL,
                qty REAL NOT NULL,
                avg_price REAL NOT NULL,
                realized_pnl REAL NOT NULL DEFAULT 0,
                updated_ts TEXT NOT NULL,
                asset_class TEXT
            )
            """
        )

        # DECISIONS (Risk v2.2)
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS decisions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts TEXT NOT NULL,
                symbol TEXT NOT NULL,
                asset_class TEXT NOT NULL,
                side TEXT,
                qty REAL,
                entry REAL,
                stop REAL,
                allowed INTEGER NOT NULL,
                reason TEXT NOT NULL,
                confidence REAL
            )
            """
        )

        self.conn.commit()

    # ------------------------------------------------------------------
    # HELPERS
    # ------------------------------------------------------------------

    @staticmethod
    def _now_iso() -> str:
        return datetime.utcnow().isoformat()

    # ------------------------------------------------------------------
    # TRADES
    # ------------------------------------------------------------------

    def insert_trades(self, trades, account_id: str):
        rows = []
        for t in trades:
            rows.append(
                (
                    t.id,
                    account_id,
                    str(t.timestamp),
                    t.symbol,
                    t.side,
                    float(t.qty),
                    float(t.price),
                    float(t.commission) if t.commission is not None else None,
                    getattr(t, "currency", None),
                    str(t),
                )
            )

        self.conn.executemany(
            """
            INSERT OR IGNORE INTO trades (
                id, account_id, ts, symbol, side,
                qty, price, commission, currency, raw_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )
        self.conn.commit()

    # ------------------------------------------------------------------
    # POSITIONS (used by Risk)
    # ------------------------------------------------------------------

    def count_open_positions(self, asset_class: str) -> int:
        row = self.conn.execute(
            """
            SELECT COUNT(*) AS cnt
            FROM positions
            WHERE qty != 0 AND asset_class = ?
            """,
            (asset_class,),
        ).fetchone()
        return int(row["cnt"] or 0)

    def sum_exposure(self, asset_class: str) -> float:
        row = self.conn.execute(
            """
            SELECT SUM(ABS(qty * avg_price)) AS exposure
            FROM positions
            WHERE qty != 0 AND asset_class = ?
            """,
            (asset_class,),
        ).fetchone()
        return float(row["exposure"] or 0.0)

    def sum_open_risk(self, asset_class: str) -> float:
        """
        Risk = |qty| * |avg_price|
        (упрощённая модель, корректная для v2.2)
        """
        row = self.conn.execute(
            """
            SELECT SUM(ABS(qty * avg_price)) AS risk
            FROM positions
            WHERE qty != 0 AND asset_class = ?
            """,
            (asset_class,),
        ).fetchone()
        return float(row["risk"] or 0.0)

    # ------------------------------------------------------------------
    # DECISIONS (Risk v2.2)
    # ------------------------------------------------------------------
    def insert_decision(self, decision: dict):

        """
        decision dict:
            ts
            symbol
            asset_class
            side
            qty
            entry
            stop
            allowed (bool)
            reason
            confidence
        """
        self.conn.execute(
            """
            INSERT INTO decisions (
                ts,
                symbol,
                asset_class,
                side,
                qty,
                entry,
                stop,
                allowed,
                reason,
                confidence
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                decision["ts"],
                decision["symbol"],
                decision["asset_class"],
                decision.get("side"),
                decision.get("qty"),
                decision.get("entry"),
                decision.get("stop"),
                1 if decision["allowed"] else 0,
                decision["reason"],
                decision.get("confidence"),
            ),
        )
        self.conn.commit()

    # ------------------------------------------------------------------
    # CLOSE
    # ------------------------------------------------------------------

    def close(self):
        self.conn.close()