import csv
from pathlib import Path
from finam_bot.storage_sqlite import StorageSQLite


EXPORT_DIR = Path("finam_bot/data/export")
EXPORT_DIR.mkdir(parents=True, exist_ok=True)


def export_trades(storage: StorageSQLite, account_id: str):
    rows = storage.get_trades(account_id)

    path = EXPORT_DIR / "trades.csv"
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)

        # фиксированная схема
        writer.writerow([
            "id",
            "account_id",
            "ts",
            "symbol",
            "side",
            "qty",
            "price",
            "commission",
            "currency",
        ])

        for r in rows:
            writer.writerow([
                r["id"],
                r["account_id"],
                r["ts"],
                r["symbol"],
                r["side"],
                r["qty"],
                r["price"],
                r["commission"],
                r["currency"],
            ])

    print(f"ok exported trades -> {path}")


def export_transactions(storage: StorageSQLite, account_id: str):
    rows = storage.get_transactions(account_id)

    path = EXPORT_DIR / "transactions.csv"
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)

        # фиксированная схема
        writer.writerow([
            "id",
            "account_id",
            "ts",
            "kind",
            "amount",
            "currency",
        ])

        for r in rows:
            writer.writerow([
                r["id"],
                r["account_id"],
                r["ts"],
                r["kind"],
                r["amount"],
                r["currency"],
            ])

    print(f"ok exported transactions -> {path}")


def main():
    storage = StorageSQLite()

    # account_id берём из данных (один аккаунт = одна БД)
    cur = storage.conn.execute(
        "SELECT DISTINCT account_id FROM trades LIMIT 1"
    )
    row = cur.fetchone()
    if not row:
        raise RuntimeError("No trades in database")

    account_id = row["account_id"]

    export_trades(storage, account_id)
    export_transactions(storage, account_id)


if __name__ == "__main__":
    main()