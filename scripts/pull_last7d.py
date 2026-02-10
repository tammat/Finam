import os
import json
from datetime import datetime, timezone
from finam_bot.finam_client import FinamClient
from finam_bot.storage_sqlite import StorageSQLite
import finam_bot.storage_sqlite
print("STORAGE MODULE FILE:", finam_bot.storage_sqlite.__file__)

def log(stage: str, **kwargs):
    payload = {"ok": True, "stage": stage}
    payload.update(kwargs)
    print(json.dumps(payload, ensure_ascii=False))


def safe_attr(obj, name: str):
    return getattr(obj, name, None)


def iso_to_dt(iso_ts: str) -> datetime:
    """
    '2026-02-10T12:44:02Z' -> datetime(timezone.utc)
    """
    return datetime.fromisoformat(
        iso_ts.replace("Z", "+00:00")
    ).astimezone(timezone.utc)


def main():
    # ---------------------------
    # config
    # ---------------------------
    account_id = os.getenv("FINAM_ACCOUNT_ID")
    if not account_id:
        raise RuntimeError("FINAM_ACCOUNT_ID is not set")

    client = FinamClient()
    storage = StorageSQLite()

    # ---------------------------
    # start log
    # ---------------------------
    host = safe_attr(client, "host") or safe_attr(client, "endpoint") or "api.finam.ru:443"
    has_secret = bool(
        os.getenv("FINAM_CLIENT_SECRET")
        or os.getenv("FINAM_SECRET")
        or safe_attr(client, "client_secret")
    )

    log(
        "start",
        host=host,
        has_secret=has_secret,
        account_id=account_id,
    )

    # ---------------------------
    # account check
    # ---------------------------
    if hasattr(client, "get_account"):
        acc = client.get_account(account_id)
        log(
            "get_account",
            account_id=account_id,
            status=safe_attr(acc, "status"),
            type=safe_attr(acc, "type"),
        )

    # ---------------------------
    # SINCE from SQLite (ISO -> datetime)
    # ---------------------------
    since_trades_iso = storage.get_since_trades(account_id)
    since_tx_iso = storage.get_since_transactions(account_id)

    since_trades = iso_to_dt(since_trades_iso)
    since_tx = iso_to_dt(since_tx_iso)

    log(
        "since",
        trades=since_trades_iso,
        transactions=since_tx_iso,
    )

    # ---------------------------
    # pull trades
    # ---------------------------
    trades = client.fetch_trades(
        account_id=account_id,
        since=since_trades,
    )
    storage.insert_trades(trades, account_id)
#    storage.insert_trades(trades)
    cnt = storage.conn.execute("SELECT COUNT(*) FROM trades").fetchone()[0]
    print("DB trades count AFTER INSERT:", cnt)
    log("trades", count=len(trades), since=since_trades_iso)

    # ---------------------------
    # pull transactions
    # ---------------------------
    transactions = client.fetch_transactions(
        account_id=account_id,
        since=since_tx,
    )

    storage.insert_transactions(transactions)

    log("transactions", count=len(transactions), since=since_tx_iso)

    # ---------------------------
    # done
    # ---------------------------
    log(
        "done",
        account_id=account_id,
        trades=len(trades),
        transactions=len(transactions),
        ts=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    )


if __name__ == "__main__":
    main()