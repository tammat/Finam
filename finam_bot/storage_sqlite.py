import sqlite3
from pathlib import Path
from datetime import datetime, timezone, timedelta
from decimal import Decimal
import json


class StorageSQLite:
    def __init__(self):
        base_dir = Path(__file__).resolve().parent
        self.db_path = base_dir / "data" / "finam.db"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self.init_schema()

    # ---------------- schema ----------------
    def init_schema(self):
        cur = self.conn.cursor()

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS trades (
                trade_id TEXT NOT NULL,
                account_id TEXT NOT NULL,
                ts TEXT NOT NULL,
                symbol TEXT NOT NULL,
                side TEXT NOT NULL,
                qty REAL NOT NULL,
                price REAL NOT NULL,
                commission REAL,
                currency TEXT,
                raw_json TEXT,
                PRIMARY KEY (account_id, trade_id)
            );
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS transactions
            (
                id
                TEXT
                NOT
                NULL,
                account_id
                TEXT
                NOT
                NULL,
                ts
                TEXT
                NOT
                NULL,
                kind
                TEXT
                NOT
                NULL,
                amount
                REAL
                NOT
                NULL,
                currency
                TEXT,
                raw_json
                TEXT,
                PRIMARY
                KEY
            (
                account_id,
                id
            )
                );
            """
        )


        cur.execute("CREATE INDEX IF NOT EXISTS idx_trades_ts ON trades(ts);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_trades_symbol_ts ON trades(symbol, ts);")

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS positions (
                instrument TEXT PRIMARY KEY,
                qty REAL NOT NULL,
                side TEXT NOT NULL,
                avg_price REAL,
                realized_pnl REAL NOT NULL,
                updated_ts TEXT NOT NULL
            );
            """
        )

        self.conn.commit()

    # ---------------- helpers ----------------
    def _now(self):
        return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    def _num(self, v, default=0.0):
        if v is None:
            return None if default is None else float(default)
        if isinstance(v, Decimal):
            return float(v)
        if hasattr(v, "value"):
            return float(v.value)
        return float(v)

    def _ts(self, v):
        if v is None:
            return None
        if hasattr(v, "seconds"):
            dt = datetime.fromtimestamp(v.seconds + v.nanos / 1e9, tz=timezone.utc)
            return dt.isoformat().replace("+00:00", "Z")
        if isinstance(v, datetime):
            if v.tzinfo is None:
                v = v.replace(tzinfo=timezone.utc)
            return v.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
        return str(v)

    def _json(self, obj):
        try:
            return json.dumps(obj, default=str, ensure_ascii=False)
        except Exception:
            return None

    # ---------------- since ----------------
    def _get_max_ts(self, table, account_id):
        try:
            row = self.conn.execute(
                f"SELECT MAX(ts) AS ts FROM {table} WHERE account_id = ?",
                (account_id,),
            ).fetchone()
        except sqlite3.OperationalError:
            return None
        return row["ts"] if row and row["ts"] else None

    def _calc_since(self, max_ts, overlap_minutes=5):
        if not max_ts:
            return "1970-01-01T00:00:00Z"
        dt = datetime.fromisoformat(max_ts.replace("Z", "+00:00"))
        dt -= timedelta(minutes=overlap_minutes)
        return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")

    def get_since_trades(self, account_id, overlap_minutes=5):
        return self._calc_since(self._get_max_ts("trades", account_id), overlap_minutes)

    def get_since_transactions(self, account_id, overlap_minutes=5):
        return self._calc_since(
            self._get_max_ts("transactions", account_id),
            overlap_minutes
        )
    # ---------------- trades ----------------
    def insert_trades(self, trades, account_id):
        sql = """
            INSERT OR IGNORE INTO trades (
                trade_id, account_id, ts, symbol, side,
                qty, price, commission, currency, raw_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """

        rows = []

        for t in trades:
            raw_ts = getattr(t, "timestamp", None) or getattr(t, "ts", None)
            ts = self._ts(raw_ts) or self._now()

            trade_id = getattr(t, "trade_id", None) or getattr(t, "id", None)
            if not trade_id:
                continue

            rows.append(
                (
                    str(trade_id),
                    str(account_id),
                    ts,
                    getattr(t, "symbol", None),
                    getattr(t, "side", None),
                    self._num(getattr(t, "qty", None) or getattr(t, "size", None)),
                    self._num(getattr(t, "price", None)),
                    self._num(getattr(t, "commission", None), None),
                    getattr(t, "currency", None),
                    self._json(t),
                )
            )

        if rows:
            self.conn.executemany(sql, rows)
            self.conn.commit()

    def insert_transactions(self, transactions, account_id=None):
        sql = """
              INSERT \
              OR IGNORE INTO transactions (
                id, account_id, ts, kind, amount, currency, raw_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?) \
              """

        rows = []

        for t in transactions:
            tx_id = getattr(t, "id", None)
            if not tx_id:
                continue

            raw_ts = getattr(t, "timestamp", None) or getattr(t, "ts", None)
            ts = self._ts(raw_ts) or self._now()

            acc_id = (
                    account_id
                    or getattr(t, "account_id", None)
            )

            rows.append(
                (
                    str(tx_id),
                    str(acc_id),
                    ts,
                    getattr(t, "category", None) or getattr(t, "kind", None),
                    self._num(getattr(t, "amount", None)),
                    getattr(t, "currency", None),
                    self._json(t),
                )
            )

        if rows:
            self.conn.executemany(sql, rows)
            self.conn.commit()

    def count_open_positions(self) -> int:
        """
        Считает количество открытых позиций (qty != 0)
        """
        row = self.conn.execute(
            """
            SELECT COUNT(*)
            FROM positions
            WHERE qty != 0
            """
        ).fetchone()
        return int(row[0] or 0)

    def get_total_risk(self) -> float:
        """
        Совокупный риск по всем открытым позициям
        risk = abs(entry_price - stop_price) * qty
        """
        rows = self.conn.execute(
            """
            SELECT entry_price, stop_price, qty
            FROM positions
            WHERE qty != 0
            """
        ).fetchall()

        total = 0.0
        for entry, stop, qty in rows:
            if entry is None or stop is None:
                continue
            total += abs(entry - stop) * abs(qty)

        return float(total)


    def count_open_positions_by_class(self, asset_class: str) -> int:
        row = self.conn.execute(
            """
            SELECT COUNT(*)
            FROM positions
            WHERE qty != 0 AND asset_class = ?
            """,
            (asset_class,),
        ).fetchone()
        return int(row[0] or 0)


    def get_total_risk_by_class(self, asset_class: str) -> float:
        rows = self.conn.execute(
            """
            SELECT entry_price, stop_price, qty
            FROM positions
            WHERE qty != 0 AND asset_class = ?
            """,
            (asset_class,),
        ).fetchall()

        total = 0.0
        for entry, stop, qty in rows:
            if entry is None or stop is None:
                continue
            total += abs(entry - stop) * abs(qty)
        return float(total)