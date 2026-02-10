# finam_bot/storage_sqlite.py
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, Dict, Iterable, Optional


SCHEMA = """
PRAGMA journal_mode=WAL;

CREATE TABLE IF NOT EXISTS meta (
  k TEXT PRIMARY KEY,
  v TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS trades (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  account_id TEXT,
  ts INTEGER,
  symbol TEXT,
  side TEXT,
  qty TEXT,
  price TEXT,
  raw_json TEXT,
  UNIQUE(account_id, ts, symbol, side, qty, price, raw_json) ON CONFLICT IGNORE
);

CREATE TABLE IF NOT EXISTS transactions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  account_id TEXT,
  ts INTEGER,
  type TEXT,
  amount TEXT,
  currency TEXT,
  raw_json TEXT,
  UNIQUE(account_id, ts, type, amount, currency, raw_json) ON CONFLICT IGNORE
);
"""


def connect(db_path: str) -> sqlite3.Connection:
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(db_path)
    con.execute("PRAGMA foreign_keys=ON;")
    con.executescript(SCHEMA)
    return con


def upsert_meta(con: sqlite3.Connection, k: str, v: str) -> None:
    con.execute("INSERT INTO meta(k,v) VALUES(?,?) ON CONFLICT(k) DO UPDATE SET v=excluded.v", (k, v))


def insert_trade(con: sqlite3.Connection, row: Dict[str, Any]) -> None:
    con.execute(
        """
        INSERT INTO trades(account_id, ts, symbol, side, qty, price, raw_json)
        VALUES(?,?,?,?,?,?,?)
        """,
        (
            row.get("account_id"),
            row.get("ts"),
            row.get("symbol"),
            row.get("side"),
            row.get("qty"),
            row.get("price"),
            row.get("raw_json"),
        ),
    )


def insert_tx(con: sqlite3.Connection, row: Dict[str, Any]) -> None:
    con.execute(
        """
        INSERT INTO transactions(account_id, ts, type, amount, currency, raw_json)
        VALUES(?,?,?,?,?,?)
        """,
        (
            row.get("account_id"),
            row.get("ts"),
            row.get("type"),
            row.get("amount"),
            row.get("currency"),
            row.get("raw_json"),
        ),
    )