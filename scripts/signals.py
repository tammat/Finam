from datetime import datetime, timezone
from finam_bot.storage_sqlite import StorageSQLite


LOOKBACK = 20        # количество последних сделок для оценки
BREAKOUT_K = 1.002   # 0.2% над максимумом
MOMENTUM_K = 1.001   # импульс


def now_iso():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def gen_signals_for_symbol(storage: StorageSQLite, symbol: str):
    rows = storage.conn.execute(
        """
        SELECT ts, price, side
        FROM trades
        WHERE symbol = ?
        ORDER BY ts DESC
        LIMIT ?
        """,
        (symbol, LOOKBACK),
    ).fetchall()

    if len(rows) < LOOKBACK:
        return

    prices = [float(r["price"]) for r in rows]
    last_price = prices[0]
    max_price = max(prices)
    min_price = min(prices)

    ts = now_iso()

    # BREAKOUT LONG
    if last_price >= max_price * BREAKOUT_K:
        storage.insert_signal(
            ts=ts,
            instrument=symbol,
            direction="LONG",
            signal_type="breakout",
            level=max_price,
            confidence=0.70,
            reason=f"Breakout above {max_price:.4f}",
        )

    # BREAKOUT SHORT
    if last_price <= min_price / BREAKOUT_K:
        storage.insert_signal(
            ts=ts,
            instrument=symbol,
            direction="SHORT",
            signal_type="breakout",
            level=min_price,
            confidence=0.70,
            reason=f"Breakdown below {min_price:.4f}",
        )

    # MOMENTUM
    if prices[0] >= prices[1] * MOMENTUM_K and prices[1] >= prices[2]:
        storage.insert_signal(
            ts=ts,
            instrument=symbol,
            direction="LONG",
            signal_type="momentum",
            level=None,
            confidence=0.55,
            reason="Short-term momentum up",
        )


def main():
    storage = StorageSQLite()

    symbols = storage.conn.execute(
        "SELECT DISTINCT symbol FROM trades"
    ).fetchall()

    for r in symbols:
        gen_signals_for_symbol(storage, r["symbol"])

    print("ok signals generated")


if __name__ == "__main__":
    main()