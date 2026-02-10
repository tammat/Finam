from decimal import Decimal
from collections import defaultdict
from finam_bot.storage_sqlite import StorageSQLite


def calc_positions(trades):
    """
    FIFO-позиции по каждому инструменту.
    Возвращает открытые позиции и реализованный PnL.
    """
    positions = defaultdict(list)   # symbol -> lots
    realized_pnl = defaultdict(Decimal)

    for t in trades:
        symbol = t["symbol"]
        side = t["side"]
        qty = Decimal(str(t["qty"]))
        price = Decimal(str(t["price"]))

        direction = Decimal("1") if side in ("BUY", "SIDE_BUY") else Decimal("-1")
        remaining = qty

        # закрываем противоположные позиции
        while remaining > 0 and positions[symbol] and positions[symbol][0]["dir"] != direction:
            lot = positions[symbol][0]
            close_qty = min(remaining, lot["qty"])

            pnl = close_qty * (price - lot["price"]) * lot["dir"]
            realized_pnl[symbol] += pnl

            lot["qty"] -= close_qty
            remaining -= close_qty

            if lot["qty"] == 0:
                positions[symbol].pop(0)

        # открываем новую позицию
        if remaining > 0:
            positions[symbol].append({
                "qty": remaining,
                "price": price,
                "dir": direction,
            })

    return positions, realized_pnl


def main():
    storage = StorageSQLite()

    trades = storage.conn.execute(
        """
        SELECT *
        FROM trades
        ORDER BY ts, id
        """
    ).fetchall()

    if not trades:
        print("No trades")
        return

    positions, realized = calc_positions(trades)

    print("\n=== OPEN POSITIONS ===")
    for symbol, lots in positions.items():
        if not lots:
            continue

        total_qty = sum(l["qty"] * l["dir"] for l in lots)
        avg_price = (
            sum(l["qty"] * l["price"] for l in lots) /
            sum(l["qty"] for l in lots)
        )

        side = "LONG" if total_qty > 0 else "SHORT"

        print(
            f"{symbol:12} | "
            f"{side:5} | "
            f"Qty: {abs(total_qty):>8.2f} | "
            f"AvgPx: {avg_price:>10.4f} | "
            f"RealizedPnL: {realized[symbol]:>10.2f}"
        )

    print("\n=== REALIZED PnL (CLOSED) ===")
    for symbol, pnl in realized.items():
        if pnl != 0:
            print(f"{symbol:12} | {pnl:>10.2f}")


if __name__ == "__main__":
    main()