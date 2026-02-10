# finam_bot/storage_sqlite.py
from __future__ import annotations

import hashlib
import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

try:
    from google.protobuf.json_format import MessageToDict  # type: ignore
except Exception:  # pragma: no cover
    MessageToDict = None  # type: ignore


DEFAULT_DB_PATH = "finam_bot/data/finam.sqlite3"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ensure_dir_for(path: str) -> None:
    p = Path(path)
    if p.parent:
        p.parent.mkdir(parents=True, exist_ok=True)


def _columns(con: sqlite3.Connection, table: str) -> list[str]:
    cur = con.execute(f"PRAGMA table_info({table})")
    return [row[1] for row in cur.fetchall()]  # row[1] = name


def _table_exists(con: sqlite3.Connection, table: str) -> bool:
    cur = con.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (table,),
    )
    return cur.fetchone() is not None


def _pick_existing(cols: list[str], candidates: Tuple[str, ...]) -> Optional[str]:
    s = set(cols)
    for c in candidates:
        if c in s:
            return c
    return None


def _migrate_meta_to_v2(con: sqlite3.Connection) -> None:
    """
    Ensures meta table has columns: key, value, updated_at.
    If old meta exists with different column names, migrate data.
    """
    if not _table_exists(con, "meta"):
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS meta (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        return

    cols = _columns(con, "meta")
    if "key" in cols and "value" in cols and "updated_at" in cols:
        return

    # try to infer old column names
    key_col = _pick_existing(cols, ("key", "k", "name", "meta_key", "metaKey"))
    val_col = _pick_existing(cols, ("value", "v", "val", "data", "meta_value", "metaValue"))
    upd_col = _pick_existing(cols, ("updated_at", "updated", "updatedAt", "ts", "timestamp"))

    # If we can't infer, do a "best effort": take first two text-ish columns
    if key_col is None or val_col is None:
        # fallback: use first two columns
        if len(cols) >= 2:
            key_col = key_col or cols[0]
            val_col = val_col or cols[1]
        else:
            # broken table, recreate empty
            con.execute("DROP TABLE IF EXISTS meta")
            con.execute(
                """
                CREATE TABLE meta (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            return

    # create new table
    con.execute("DROP TABLE IF EXISTS meta_new")
    con.execute(
        """
        CREATE TABLE meta_new (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )

    now = _utc_now_iso()
    if upd_col:
        con.execute(
            f"""
            INSERT OR REPLACE INTO meta_new(key, value, updated_at)
            SELECT CAST({key_col} AS TEXT),
                   CAST({val_col} AS TEXT),
                   COALESCE(CAST({upd_col} AS TEXT), ?)
            FROM meta
            """,
            (now,),
        )
    else:
        con.execute(
            f"""
            INSERT OR REPLACE INTO meta_new(key, value, updated_at)
            SELECT CAST({key_col} AS TEXT),
                   CAST({val_col} AS TEXT),
                   ?
            FROM meta
            """,
            (now,),
        )

    con.execute("DROP TABLE meta")
    con.execute("ALTER TABLE meta_new RENAME TO meta")


def _init_schema(con: sqlite3.Connection) -> None:
    con.execute("PRAGMA journal_mode=WAL;")
    con.execute("PRAGMA synchronous=NORMAL;")
    con.execute("PRAGMA foreign_keys=ON;")

    _migrate_meta_to_v2(con)

    con.execute(
        """
        CREATE TABLE IF NOT EXISTS trades (
            id TEXT PRIMARY KEY,
            account_id TEXT,
            ts TEXT,
            raw_json TEXT NOT NULL
        )
        """
    )
    con.execute("CREATE INDEX IF NOT EXISTS idx_trades_ts ON trades(ts)")
    con.execute("CREATE INDEX IF NOT EXISTS idx_trades_account_ts ON trades(account_id, ts)")

    con.execute(
        """
        CREATE TABLE IF NOT EXISTS transactions (
            id TEXT PRIMARY KEY,
            account_id TEXT,
            ts TEXT,
            raw_json TEXT NOT NULL
        )
        """
    )
    con.execute("CREATE INDEX IF NOT EXISTS idx_transactions_ts ON transactions(ts)")
    con.execute("CREATE INDEX IF NOT EXISTS idx_transactions_account_ts ON transactions(account_id, ts)")

    con.commit()


def connect(db_path: Optional[str] = None) -> sqlite3.Connection:
    path = (db_path or os.getenv("FINAM_DB_PATH") or DEFAULT_DB_PATH).strip()
    if not path:
        path = DEFAULT_DB_PATH
    _ensure_dir_for(path)
    con = sqlite3.connect(path)
    con.row_factory = sqlite3.Row
    _init_schema(con)
    return con


def upsert_meta(con: sqlite3.Connection, key: str, value: str) -> None:
    con.execute(
        """
        INSERT INTO meta(key, value, updated_at)
        VALUES(?, ?, ?)
        ON CONFLICT(key) DO UPDATE SET
            value=excluded.value,
            updated_at=excluded.updated_at
        """,
        (key, value, _utc_now_iso()),
    )


def _as_dict(obj: Any) -> Dict[str, Any]:
    if MessageToDict is not None:
        try:
            return MessageToDict(obj, preserving_proto_field_name=True)  # type: ignore
        except Exception:
            pass
    if isinstance(obj, dict):
        return obj
    try:
        return dict(obj)  # type: ignore
    except Exception:
        return {"repr": repr(obj)}


def _json_dump(d: Dict[str, Any]) -> str:
    return json.dumps(d, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def _stable_id(raw_json: str) -> str:
    return hashlib.sha256(raw_json.encode("utf-8")).hexdigest()[:32]


def _pick_first(d: Dict[str, Any], keys: Tuple[str, ...]) -> Optional[str]:
    for k in keys:
        v = d.get(k)
        if v is None:
            continue
        if isinstance(v, (int, float)):
            return str(v)
        if isinstance(v, str) and v.strip():
            return v.strip()
    return None


def insert_trade(con: sqlite3.Connection, trade: Any, account_id: Optional[str] = None) -> None:
    d = _as_dict(trade)
    raw = _json_dump(d)

    tid = _pick_first(d, ("id", "trade_id", "tradeId", "order_id", "orderId")) or _stable_id(raw)
    ts = _pick_first(d, ("ts", "time", "timestamp", "created_at", "createdAt", "date"))
    acc = account_id or _pick_first(d, ("account_id", "accountId"))

    con.execute(
        """
        INSERT INTO trades(id, account_id, ts, raw_json)
        VALUES(?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            account_id=COALESCE(excluded.account_id, trades.account_id),
            ts=COALESCE(excluded.ts, trades.ts),
            raw_json=excluded.raw_json
        """,
        (tid, acc, ts, raw),
    )


def insert_tx(con: sqlite3.Connection, tx: Any, account_id: Optional[str] = None) -> None:
    d = _as_dict(tx)
    raw = _json_dump(d)

    xid = _pick_first(d, ("id", "transaction_id", "transactionId", "tx_id", "txId")) or _stable_id(raw)
    ts = _pick_first(d, ("ts", "time", "timestamp", "created_at", "createdAt", "date"))
    acc = account_id or _pick_first(d, ("account_id", "accountId"))

    con.execute(
        """
        INSERT INTO transactions(id, account_id, ts, raw_json)
        VALUES(?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            account_id=COALESCE(excluded.account_id, transactions.account_id),
            ts=COALESCE(excluded.ts, transactions.ts),
            raw_json=excluded.raw_json
        """,
        (xid, acc, ts, raw),
    )