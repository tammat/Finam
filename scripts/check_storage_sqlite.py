from finam_bot.storage_sqlite import StorageSQLite
from datetime import datetime, timezone

ACCOUNT_ID = "TEST_ACCOUNT"

storage = StorageSQLite()

print("=== SCHEMA CHECK ===")

tables = storage.conn.execute("""
SELECT name FROM sqlite_master WHERE type='table'
""").fetchall()

print("tables:", [t["name"] for t in tables])

print("\n=== INSERT + DEDUP CHECK ===")

ts_now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

trade = {
    "id": "TRADE_1",
    "account_id": ACCOUNT_ID,
    "ts": ts_now,
    "symbol": "TEST",
    "side": "BUY",
    "qty": 1.0,
    "price": 100.0,
    "commission": 1.0,
    "currency": "RUB",
    "raw_json": "{}",
}

# вставляем ДВА раза
storage.insert_trades([trade])
storage.insert_trades([trade])

rows = storage.conn.execute(
    "SELECT COUNT(*) AS cnt FROM trades WHERE id='TRADE_1'"
).fetchone()["cnt"]

print("trades with id=TRADE_1:", rows)

assert rows == 1, "DEDUP FAILED (trade duplicated)"

print("\n=== TRANSACTION DEDUP CHECK ===")

tx = {
    "id": "TX_1",
    "account_id": ACCOUNT_ID,
    "ts": ts_now,
    "kind": "COMMISSION",
    "amount": -10.0,
    "currency": "RUB",
    "raw_json": "{}",
}

storage.insert_transactions([tx])
storage.insert_transactions([tx])

rows = storage.conn.execute(
    "SELECT COUNT(*) AS cnt FROM transactions WHERE id='TX_1'"
).fetchone()["cnt"]

print("transactions with id=TX_1:", rows)

assert rows == 1, "DEDUP FAILED (transaction duplicated)"

print("\n=== SINCE CHECK ===")

since_trades = storage.get_since_trades(ACCOUNT_ID)
since_tx = storage.get_since_transactions(ACCOUNT_ID)

print("since trades:", since_trades)
print("since transactions:", since_tx)

assert since_trades < ts_now, "since(trades) >= max(ts)"
assert since_tx < ts_now, "since(transactions) >= max(ts)"

print("\n=== READ CHECK ===")

trades = storage.get_trades(ACCOUNT_ID)
txs = storage.get_transactions(ACCOUNT_ID)

print("read trades:", len(trades))
print("read transactions:", len(txs))

assert len(trades) == 1
assert len(txs) == 1

print("\n✅ STORAGE_SQLITE CHECK PASSED")