import sqlite3
from collections import defaultdict
from pathlib import Path

DB_PATH = Path("finam_bot/data/finam.db")


def asset_class_by_symbol(symbol: str) -> str:
    """
    Классификация инструмента.
    Расширяется позже (Risk v2.3+).
    """
    s = symbol.upper()

    if s.startswith(("NG", "BR", "CL")):
        return "FUTURES"

    if s.endswith((".ME", ".RU")):
        return "STOCKS"

    return "UNKNOWN"


def main():
    if not DB_PATH.exists():
        print("DB not found:", DB_PATH)
        return

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    # --- читаем сделки ---
    trades = conn.execute(
        """
        SELECT symbol, side, qty, price
        FROM trades
        ORDER BY ts
        """
    ).fetchall()

    print(f"trades read: {len(trades)}")

    if not trades:
        print("No trades in DB")
        return

    # --- агрегируем позиции ---
    positions = defaultdict(lambda: {
        "instrument": None,
        "qty": 0.0,
        "value": 0.0,   # qty * price
    })

    for t in trades:
        instrument = t["symbol"]
        side = t["side"]
        qty = float(t["qty"])
        price = float(t["price"])

        p = positions[instrument]
        p["instrument"] = instrument

        if side.upper() in ("BUY", "LONG"):
            signed_qty = qty
        elif side.upper() in ("SELL", "SHORT"):
            signed_qty = -qty
        else:
            continue

        p["qty"] += signed_qty
        p["value"] += signed_qty * price

    # --- очищаем positions ---
    conn.execute("DELETE FROM positions")

    written = 0

    for p in positions.values():
        qty = p["qty"]

        if qty == 0:
            continue

        instrument = p["instrument"]
        avg_price = abs(p["value"] / qty)
        side = "LONG" if qty > 0 else "SHORT"
        asset_class = asset_class_by_symbol(instrument)

        conn.execute(
            """
            INSERT INTO positions (
                instrument,
                side,
                asset_class,
                qty,
                avg_price
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                instrument,
                side,
                asset_class,
                qty,
                avg_price,
            )
        )

        written += 1

    conn.commit()
    conn.close()

    print(f"positions written: {written}")


if __name__ == "__main__":
    main()