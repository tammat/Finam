from finam_bot.signals.registry import STRATEGIES
from finam_bot.qty.calculator import QtyCalculator
from finam_bot.storage_sqlite import StorageSQLite
from finam_bot.risk_engine_v2_1 import RiskEngineV21
from finam_bot.risk_config import RiskConfigV21


def detect_signal(symbol: str, price: float):
    for strat in STRATEGIES:
        sig = strat.detect(symbol, price)
        if sig:
            return sig
    return None


def main():
    symbol = "NG-2.26"
    last_price = 3.11  # пока вручную

    # 1) detect
    signal = detect_signal(symbol, last_price)
    if not signal:
        print("NO SIGNAL")
        return
    print("SIGNAL:", signal)

    # 2) qty
    qty_calc = QtyCalculator(max_risk_per_trade=RiskConfigV21().max_risk_per_trade)
    qty = qty_calc.calc(entry_price=signal.entry, stop_price=signal.stop)
    print("QTY:", qty)
    if qty <= 0:
        print("BLOCKED: QTY_ZERO")
        return

    # 3) risk v2.1
    storage = StorageSQLite()
    risk = RiskEngineV21(storage, RiskConfigV21())
    allowed, reason = risk.check(qty=qty, signal=signal)
    print("RISK:", allowed, reason)

    if not allowed:
        print("⛔ BLOCKED")
        return

    # 4) notify stub
    print("✅ ALLOWED — SEND NOTIFICATION", {"symbol": signal.symbol, "side": signal.side, "qty": qty})


if __name__ == "__main__":
    main()