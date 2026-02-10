from collections import defaultdict
from decimal import Decimal
from finam_bot.storage_sqlite import StorageSQLite


def calc_pnl(trades):
    """
    FIFO PnL по каждому инструменту.
    Поддерживает LONG/SHORT, комиссии учитываются.
    """
    positions = defaultdict(list)  # symbol -> list of open lots
    realized = defaultdict(Decimal)
    commissions = defaultdict(Decimal)

    for t in trades:
        symbol = t["symbol"]
        side = t["side"]
        qty = Decimal(str(t["qty"]))
        price = Decimal(str(t["price"]))
        commission = Decimal(str(t["commission"])) if t["commission"] is not None else Decimal("0")

        commissions[symbol] += commission

        # направление
        direction = 1 if side in ("BUY", "SIDE_BUY") else -1

        remaining = qty

        # закрываем противоположные позиции (FIFO)
        while remaining > 0 and positions[symbol] and positions[symbol][0]["dir"] != direction:
            lot = positions[symbol][0]
            close_qty = min(remaining, lot["qty"])

            pnl = close_qty * (price - lot["price"]) * lot["dir"]
            realized[symbol] += pnl

            lot["qty"] -= close_qty
            remaining -= close_qty

            if lot["qty"] == 0:
                positions[symbol].pop(0)

        # если что-то осталось — открываем новую позицию
        if remaining > 0:
            positions[symbol].append({
                "qty": remaining,
                "price": price,
                "dir": direction,
            })

    return realized, commissions


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

    realized, commissions = calc_pnl(trades)

    print("\n=== PnL SUMMARY ===")
    total_pnl = Decimal("0")
    total_comm = Decimal("0")

    for symbol in sorted(realized.keys()):
        pnl = realized[symbol]
        comm = commissions[symbol]
        net = pnl - comm

        total_pnl += pnl
        total_comm += comm

        print(
            f"{symbol:12} | "
            f"PnL: {pnl:>10.2f} | "
            f"Comm: {comm:>8.2f} | "
            f"Net: {net:>10.2f}"
        )

    print("-" * 60)
    print(
        f"{'TOTAL':12} | "
        f"PnL: {total_pnl:>10.2f} | "
        f"Comm: {total_comm:>8.2f} | "
        f"Net: {(total_pnl - total_comm):>10.2f}"
    )


if __name__ == "__main__":
    main()