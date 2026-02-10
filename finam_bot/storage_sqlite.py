import sqlite3
from pathlib import Path
from typing import List, Any, Optional
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from google.protobuf.timestamp_pb2 import Timestamp

DEFAULT_DB_PATH = Path("finam_bot/data/finam.db")


def _get(obj: Any, name: str, default=None):
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)

def _num(v, default=0.0):
    """
    Normalize numeric values:
    int / float / str / Decimal -> float
    None -> default (or None if default is None)
    """
    if v is None:
        return None if default is None else float(default)
    if isinstance(v, Decimal):
        return float(v)
    try:
        return float(v)
    except Exception:
        return None if default is None else float(default)


def _iso(ts) -> Optional[str]:
    """
    Normalize timestamp to ISO-8601 UTC string.
    Supports:
    - str (ISO)
    - datetime
    - protobuf Timestamp (seconds/nanos)
    """
    if ts is None:
        return None

    # already ISO string
    if isinstance(ts, str):
        return ts

    # datetime
    if isinstance(ts, datetime):
        return ts.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")

    # protobuf Timestamp
    if hasattr(ts, "seconds"):
        dt = datetime.fromtimestamp(
            ts.seconds + ts.nanos / 1_000_000_000,
            tz=timezone.utc,
        )
        return dt.isoformat().replace("+00:00", "Z")

    # fallback (should not happen anymore)
    return str(ts)


class StorageSQLite:
    def __init__(self, db_path: Path = DEFAULT_DB_PATH):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self.init_schema()

    # ---------------------------
    # schema
    # ---------------------------
    def init_schema(self):
        self.conn.executescript(
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
            );

            CREATE TABLE IF NOT EXISTS transactions (
                id TEXT PRIMARY KEY,
                account_id TEXT NOT NULL,
                ts TEXT NOT NULL,
                kind TEXT NOT NULL,
                amount REAL NOT NULL,
                currency TEXT NOT NULL,
                raw_json TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_trades_ts ON trades(ts);
            CREATE INDEX IF NOT EXISTS idx_trades_symbol_ts ON trades(symbol, ts);
            CREATE INDEX IF NOT EXISTS idx_transactions_ts ON transactions(ts);
            """
        )
        self.conn.commit()

    # ---------------------------
    # insert (DEDUP SAFE)
    # ---------------------------
    def insert_trades(self, trades: List[Any]):
        sql = """
        INSERT OR IGNORE INTO trades
        (id, account_id, ts, symbol, side, qty, price, commission, currency, raw_json)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        rows = []
        for t in trades:
            rows.append(
                (
                    str(_get(t, "id")),
                    str(_get(t, "account_id")),
                    _iso(_get(t, "ts") or _get(t, "timestamp")),
                    str(_get(t, "symbol")),
                    str(_get(t, "side")),
                    _num(_get(t, "qty") or _get(t, "size")),
                    _num(_get(t, "price")),
                    _num(_get(t, "commission"), None),
                    _get(t, "currency"),
                    str(_get(t, "raw_json") or ""),
                )
            )
        self.conn.executemany(sql, rows)
        self.conn.commit()

    def insert_transactions(self, transactions: List[Any]):
        sql = """
        INSERT OR IGNORE INTO transactions
        (id, account_id, ts, kind, amount, currency, raw_json)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        rows = []
        for t in transactions:
            rows.append(
                (
                    str(_get(t, "id")),
                    str(_get(t, "account_id")),
                    _iso(_get(t, "ts") or _get(t, "timestamp")),
                    str(_get(t, "kind")),
                    _num(_get(t, "amount")),
                    str(_get(t, "currency")),
                    str(_get(t, "raw_json") or ""),
                )
            )
        self.conn.executemany(sql, rows)
        self.conn.commit()

    # ---------------------------
    # since helpers
    # ---------------------------
    def _get_max_ts(self, table: str, account_id: str) -> Optional[str]:
        cur = self.conn.execute(
            f"SELECT MAX(ts) AS max_ts FROM {table} WHERE account_id = ?",
            (account_id,),
        )
        row = cur.fetchone()
        return row["max_ts"] if row and row["max_ts"] else None

    def get_since_trades(self, account_id: str, overlap_minutes: int = 10) -> str:
        return self._calc_since(self._get_max_ts("trades", account_id), overlap_minutes)

    def get_since_transactions(self, account_id: str, overlap_minutes: int = 10) -> str:
        return self._calc_since(self._get_max_ts("transactions", account_id), overlap_minutes)

    @staticmethod
    def _calc_since(max_ts: Optional[str], overlap_minutes: int) -> str:
        if not max_ts:
            return "1970-01-01T00:00:00Z"
        dt = datetime.fromisoformat(max_ts.replace("Z", "+00:00"))
        dt -= timedelta(minutes=overlap_minutes)
        return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")