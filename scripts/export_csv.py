#!/usr/bin/env python3
import csv
import json
import os
import sqlite3
from typing import Any, Dict
from datetime import datetime, timezone


def json_loads_safe(s: Any) -> Dict[str, Any]:
    if s is None:
        return {}
    if isinstance(s, dict):
        return s
    try:
        return json.loads(s)
    except Exception:
        return {}


# ---------- Нормализация времени ----------
def normalize_ts(value: Any) -> str:
    if not value:
        return ""

    try:
        if isinstance(value, (int, float)):
            if value > 1e12:
                value /= 1000
            dt = datetime.fromtimestamp(value, tz=timezone.utc)
            return dt.isoformat().replace("+00:00", "Z")

        s = str(value).strip()

        if s.endswith("Z"):
            s = s[:-1] + "+00:00"

        try:
            dt = datetime.fromisoformat(s)
        except Exception:
            dt = datetime.strptime(s, "%Y-%m-%d %H:%M:%S")

        if not dt.tzinfo:
            dt = dt.replace(tzinfo=timezone.utc)

        return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")

    except Exception:
        return str(value)


def connect_db() -> sqlite3.Connection:
    db = os.getenv("FINAM_DB", "finam_bot/data/finam.sqlite3")
    con = sqlite3.connect(db)
    con.row_factory = sqlite3.Row
    return con


def table_columns(con, table):
    cur = con.execute(f"PRAGMA table_info({table})")
    return {r["name"] for r in cur.fetchall()}


# ---------- EXPORT TRANSACTIONS ----------
def export_transactions_pretty(con, out_path):
    cols = table_columns(con, "transactions")

    id_col = "id" if "id" in cols else None
    acc_col = "account_id" if "account_id" in cols else None
    ts_col = "ts" if "ts" in cols else None
    raw_col = "raw_json" if "raw_json" in cols else None

    cur = con.execute("SELECT * FROM transactions ORDER BY ts DESC")

    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    with open(out_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["id", "account_id", "ts", "kind", "amount", "currency", "raw_json"])

        seen = set()

        for r in cur.fetchall():
            d = json_loads_safe(r[raw_col])

            tx_id = r[id_col] if id_col else None
            if not tx_id:
                tx_id = d.get("id") or d.get("transaction_id") or ""

            account_id = r[acc_col] or d.get("account_id") or ""

            # ---------- дедуп ----------
            if tx_id:
                key = (str(account_id), str(tx_id))
                if key in seen:
                    continue
                seen.add(key)

            ts = (
                r[ts_col] if ts_col else None
            ) or d.get("timestamp") or d.get("time") or d.get("ts")

            ts = normalize_ts(ts)

            kind = d.get("category") or d.get("transaction_category") or ""

            amount = ""
            currency = ""

            ch = d.get("change")
            if isinstance(ch, dict):
                currency = ch.get("currency_code") or ""

                units = ch.get("units")
                nanos = ch.get("nanos")

                if units is not None and nanos is not None:
                    amount = f"{units}.{str(abs(int(nanos))).rjust(9,'0')}"
                elif units is not None:
                    amount = str(units)

            w.writerow([
                str(tx_id),
                str(account_id),
                ts,
                str(kind),
                str(amount),
                str(currency),
                json.dumps(d, ensure_ascii=False),
            ])


def main():
    con = connect_db()
    out = "finam_bot/data/export/transactions.csv"
    export_transactions_pretty(con, out)
    print("ok exported transactions")


if __name__ == "__main__":
    main()