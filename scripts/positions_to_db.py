from collections import defaultdict
from decimal import Decimal
from finam_bot.storage_sqlite import StorageSQLite
import finam_bot.storage_sqlite
print("STORAGE MODULE FILE:", finam_bot.storage_sqlite.__file__)

def calc_positions_fifo(trades):
    positions = defaultdict(list)
    realized = defaultdict(Decimal)

    for t in trades:
        symbol = t["symbol"]
        side = t["side"]
        qty = Decimal(str(t["qty"]))
        price = Decimal(str(t["price"]))

        direction = Decimal("1") if side in ("BUY", "SIDE_BUY") else Decimal("-1")
        remaining = qty

        while remaining > 0 and positions[symbol] and positions[symbol][0]["dir"] != direction:
            lot = positions[symbol][0]
            close_qty = min(remaining, lot["qty"])

            realized[symbol] += close_qty * (price - lot["price"]) * lot["dir"]

            lot["qty"] -= close_qty
            remaining -= close_qty
            if lot["qty"] == 0:
                positions[symbol].pop(0)

        if remaining > 0:
            positions[symbol].append({"qty": remaining, "price": price, "dir": direction})

    return positions, realized


def ensure_positions_table(storage: StorageSQLite):
    storage.conn.execute(
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
    storage.conn.commit()


def upsert(storage: StorageSQLite, instrument, qty, side, avg_price, realized_pnl):
    storage.conn.execute(
        """
        INSERT INTO positions (instrument, qty, side, avg_price, realized_pnl, updated_ts)
        VALUES (?, ?, ?, ?, ?, datetime('now'))
        ON CONFLICT(instrument) DO UPDATE SET
            qty = excluded.qty,
            side = excluded.side,
            avg_price = excluded.avg_price,
            realized_pnl = excluded.realized_pnl,
            updated_ts = excluded.updated_ts
        """,
        (instrument, qty, side, avg_price, realized_pnl),
    )


def main():

    storage = StorageSQLite()
    print("DB PATH:", storage.db_path)
    ensure_positions_table(storage)

    trades = storage.conn.execute(
        "SELECT * FROM trades ORDER BY ts, trade_id"
    ).fetchall()

    print("trades read:", len(trades))
    if not trades:
        print("No trades in DB")
        return

    lots_by_symbol, realized = calc_positions_fifo(trades)

    storage.conn.execute("DELETE FROM positions")
    storage.conn.commit()

    symbols = set(lots_by_symbol.keys()) | set(realized.keys())
    written = 0

    for symbol in sorted(symbols):
        lots = lots_by_symbol.get(symbol, [])
        rpn = float(realized.get(symbol, Decimal("0")))

        if not lots:
            upsert(storage, symbol, 0.0, "FLAT", None, rpn)
            written += 1
            continue

        net_qty = sum(l["qty"] * l["dir"] for l in lots)
        abs_qty = sum(l["qty"] for l in lots)
        avg_price = (sum(l["qty"] * l["price"] for l in lots) / abs_qty) if abs_qty != 0 else None

        side = "LONG" if net_qty > 0 else "SHORT"
        upsert(storage, symbol, float(abs(net_qty)), side, float(avg_price), rpn)
        written += 1

    storage.conn.commit()
    print("positions written:", written)


if __name__ == "__main__":
    main()