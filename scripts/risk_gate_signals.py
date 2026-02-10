from decimal import Decimal
from finam_bot.storage_sqlite import StorageSQLite
from finam_bot.risk_engine import RiskEngine

CAPITAL = Decimal("1000000")   # позже вынесем в env/таблицу
DEFAULT_RISK_AMOUNT = Decimal("3000")  # временно: фикс. риск на сигнал


def main():
    storage = StorageSQLite()
    risk = RiskEngine(storage, CAPITAL)

    # берём последние сигналы (если таблица signals есть)
    signals = storage.conn.execute(
        "SELECT * FROM signals ORDER BY ts DESC, id DESC LIMIT 50"
    ).fetchall()

    if not signals:
        print("No signals")
        return

    for s in reversed(signals):
        allowed, reason = risk.allow_trade(DEFAULT_RISK_AMOUNT)

        msg = f"{s['instrument']} {s['direction']} {s['signal_type']} -> {allowed} ({reason})"
        print(msg)

        # пишем решение в risk_state как журнал (минимально)
        storage.set_risk_flag(f"LAST_RISK_DECISION_{s['instrument']}", f"{allowed}:{reason}")

    print("ok risk gate processed")


if __name__ == "__main__":
    main()