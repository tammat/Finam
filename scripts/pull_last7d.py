#!/usr/bin/env python3
import os
import json
from datetime import datetime, timezone, timedelta

import grpc

from finam_bot.finam_client import FinamClient
from finam_bot.storage_sqlite import connect, upsert_meta, insert_trade, insert_tx


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _parse_dt(s: str) -> datetime | None:
    s = (s or "").strip()
    if not s:
        return None
    # "2026-02-10T11:22:00.523Z" -> "+00:00"
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None


def _meta_get(con, key: str) -> str | None:
    """
    Поддержим чуть разные схемы meta на всякий случай:
    - meta(key TEXT PRIMARY KEY, value TEXT, updated_at TEXT ...)
    - meta(name TEXT PRIMARY KEY, value TEXT ...)
    """
    for sql in (
        "SELECT value FROM meta WHERE key=? LIMIT 1",
        "SELECT value FROM meta WHERE name=? LIMIT 1",
    ):
        try:
            cur = con.execute(sql, (key,))
            row = cur.fetchone()
            if row and row[0] is not None:
                return str(row[0])
        except Exception:
            continue
    return None


def _msg_to_dict(m):
    try:
        from google.protobuf.json_format import MessageToDict
        return MessageToDict(m, preserving_proto_field_name=True)
    except Exception:
        try:
            return json.loads(m.__class__.to_json(m))  # type: ignore[attr-defined]
        except Exception:
            return {"_repr": repr(m)}


def _maybe_set_account_id(msg, account_id: str) -> None:
    try:
        if hasattr(msg, "account_id"):
            cur = getattr(msg, "account_id")
            if not cur:
                setattr(msg, "account_id", account_id)
    except Exception:
        pass


def _call_insert_trade(con, account_id: str, tr) -> None:
    _maybe_set_account_id(tr, account_id)

    # 1) insert_trade(con, tr)
    try:
        insert_trade(con, tr)
        return
    except TypeError:
        pass

    # 2) insert_trade(con, account_id, tr)
    try:
        insert_trade(con, account_id, tr)
        return
    except TypeError:
        pass

    # 3) insert_trade(con, tr, account_id=...)
    try:
        insert_trade(con, tr, account_id=account_id)
        return
    except TypeError:
        pass

    # 4) старый вариант: insert_trade(con, trade_id, account_id, ts, raw_json)
    d = _msg_to_dict(tr)
    trade_id = d.get("id") or d.get("trade_id") or d.get("request_id") or ""
    ts = d.get("timestamp") or d.get("ts") or d.get("time") or d.get("datetime") or d.get("created_at") or ""
    insert_trade(con, str(trade_id), account_id, str(ts), json.dumps(d, ensure_ascii=False))


def _table_cols(con, table: str) -> set[str]:
    cur = con.execute(f"PRAGMA table_info({table})")
    return {r[1] for r in cur.fetchall()}  # name

def _insert_tx_fallback(con, account_id: str, tx) -> None:
    d = _msg_to_dict(tx)

    tx_id = str(d.get("id") or d.get("transaction_id") or "")
    ts = str(d.get("timestamp") or d.get("ts") or "")

    cols = _table_cols(con, "transactions")

    row = {
        "id": tx_id,
        "account_id": account_id,
        "ts": ts,
        "raw_json": json.dumps(d, ensure_ascii=False),
    }

    # optional columns
    if "kind" in cols:
        row["kind"] = str(d.get("category") or d.get("transaction_category") or d.get("kind") or "")
    if "currency" in cols:
        ch = d.get("change") or {}
        row["currency"] = str(ch.get("currency_code") or d.get("currency") or "")
    if "amount" in cols:
        # amount в protobuf money = units + nanos; запишем строкой "units.nanos" либо units
        ch = d.get("change") or {}
        units = ch.get("units")
        nanos = ch.get("nanos")
        if units is not None and nanos is not None:
            # nanos может быть отрицательным — оставим как есть
            row["amount"] = f"{units}.{abs(int(nanos)):09d}"
        elif units is not None:
            row["amount"] = str(units)

    # собираем SQL только по реально существующим колонкам
    use_keys = [k for k in ("id", "account_id", "ts", "kind", "amount", "currency", "raw_json") if k in cols and k in row]
    placeholders = ",".join(["?"] * len(use_keys))
    sql = f"INSERT OR REPLACE INTO transactions ({','.join(use_keys)}) VALUES ({placeholders})"
    con.execute(sql, [row[k] for k in use_keys])

def _call_insert_tx(con, account_id: str, tx) -> None:
    """
    Сначала пробуем существующий insert_tx в нескольких сигнатурах.
    Если он падает/пытается биндингить protobuf-объект — делаем fallback-вставку сами.
    """
    _maybe_set_account_id(tx, account_id)

    try:
        # 1) insert_tx(con, account_id, tx)
        try:
            insert_tx(con, account_id, tx)
            return
        except TypeError:
            pass

        # 2) insert_tx(con, tx, account_id=...)
        try:
            insert_tx(con, tx, account_id=account_id)
            return
        except TypeError:
            pass

        # 3) insert_tx(con, tx)
        insert_tx(con, tx)
        return

    except Exception as e:
        # ключевая ошибка: sqlite не умеет параметром protobuf объект
        if "type 'Transaction' is not supported" in str(e) or "Error binding parameter" in str(e):
            _insert_tx_fallback(con, account_id, tx)
            return
        raise

def _grpc_err(e: Exception) -> dict:
    if isinstance(e, grpc.RpcError):
        try:
            return {"code": e.code().name, "details": e.details()}
        except Exception:
            return {"details": str(e)}
    return {"details": str(e)}


def main() -> int:
    host = os.getenv("FINAM_GRPC_HOST", "api.finam.ru:443")
    secret = os.getenv("FINAM_TOKEN", "")
    jwt = os.getenv("JWT", "")
    account_id = os.getenv("FINAM_ACCOUNT_ID", "")

    print(json.dumps({
        "ok": True,
        "stage": "start",
        "host": host,
        "has_secret": bool(secret),
        "jwt_len": len(jwt),
        "jwt_dots": jwt.count("."),
        "account_id": account_id,
    }, ensure_ascii=False))

    if not account_id:
        print(json.dumps({"ok": False, "stage": "env", "error": "FINAM_ACCOUNT_ID is empty"}, ensure_ascii=False))
        return 2

    con = connect()

    started_at = _now_utc().isoformat()
    upsert_meta(con, "last_run_started_at", started_at)
    upsert_meta(con, "last_run_status", "running")
    upsert_meta(con, "last_error", "")
    con.commit()

    # since: из meta.last_success_ts либо последние N дней
    since_days = int(os.getenv("FINAM_SINCE_DAYS", "7"))
    overlap_min = int(os.getenv("FINAM_OVERLAP_MINUTES", "5"))

    last_success = _parse_dt(_meta_get(con, "last_success_ts") or "")
    if last_success:
        since = last_success - timedelta(minutes=overlap_min)
        since_source = "meta.last_success_ts"
    else:
        since = _now_utc() - timedelta(days=since_days)
        since_source = f"default_{since_days}d"

    upsert_meta(con, "last_since", since.isoformat())
    upsert_meta(con, "last_since_source", since_source)
    con.commit()

    c = FinamClient.from_env()

    # token_details (клиент сам попробует refresh через Auth при необходимости)
    try:
        td = c.token_details()
        md_count = None
        try:
            md_count = len(getattr(td, "md_permissions", []))
        except Exception:
            md_count = None

        print(json.dumps({
            "ok": True,
            "stage": "token_details",
            "created_at": str(getattr(td, "created_at", None)),
            "expires_at": str(getattr(td, "expires_at", None)),
            "md_permissions_count": md_count,
            "account_ids": list(getattr(td, "account_ids", [])) if hasattr(td, "account_ids") else None,
        }, ensure_ascii=False))
    except Exception as e:
        info = _grpc_err(e)
        print(json.dumps({"ok": False, "stage": "token_details", **info}, ensure_ascii=False))
        upsert_meta(con, "last_run_status", "error")
        upsert_meta(con, "last_error", f"token_details: {info.get('details','')}")
        upsert_meta(con, "last_run_finished_at", _now_utc().isoformat())
        con.commit()
        return 1

    # get_account
    try:
        acc = c.get_account(account_id)
        d = _msg_to_dict(acc)
        print(json.dumps({
            "ok": True,
            "stage": "get_account",
            "account_id": account_id,
            "status": d.get("status"),
            "type": d.get("type"),
        }, ensure_ascii=False))
    except Exception as e:
        info = _grpc_err(e)
        print(json.dumps({"ok": False, "stage": "get_account", **info}, ensure_ascii=False))
        upsert_meta(con, "last_run_status", "error")
        upsert_meta(con, "last_error", f"get_account: {info.get('details','')}")
        upsert_meta(con, "last_run_finished_at", _now_utc().isoformat())
        con.commit()
        return 1

    # fetch + store
    trades_n = 0
    tx_n = 0
    try:
        for tr in c.fetch_trades(account_id, since=since, limit=500):
            trades_n += 1
            _call_insert_trade(con, account_id, tr)
        con.commit()
        print(json.dumps({"ok": True, "stage": "trades", "count": trades_n, "since": since.isoformat()}, ensure_ascii=False))

        for tx in c.fetch_transactions(account_id, since=since, limit=500):
            tx_n += 1
            _call_insert_tx(con, account_id, tx)
        con.commit()
        print(json.dumps({"ok": True, "stage": "transactions", "count": tx_n, "since": since.isoformat()}, ensure_ascii=False))

    except Exception as e:
        con.rollback()
        info = _grpc_err(e)
        print(json.dumps({"ok": False, "stage": "fetch", **info}, ensure_ascii=False))
        upsert_meta(con, "last_run_status", "error")
        upsert_meta(con, "last_error", f"fetch: {info.get('details','')}")
        upsert_meta(con, "last_run_finished_at", _now_utc().isoformat())
        con.commit()
        return 1
    finally:
        try:
            con.close()
        except Exception:
            pass

    # success
    con = connect()
    finished_at = _now_utc()
    upsert_meta(con, "last_run_status", "ok")
    upsert_meta(con, "last_run_finished_at", finished_at.isoformat())
    upsert_meta(con, "last_success_ts", finished_at.isoformat())
    upsert_meta(con, "last_trades_n", str(trades_n))
    upsert_meta(con, "last_transactions_n", str(tx_n))
    con.commit()
    con.close()

    print(json.dumps({"ok": True, "stage": "done", "account_id": account_id, "trades": trades_n, "transactions": tx_n}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())