# scripts/run_signals.py

from datetime import datetime, timezone
import uuid

from finam_bot.storage_sqlite import StorageSQLite
from finam_bot.signals.registry import STRATEGIES
from finam_bot.instruments import get_asset_class
from finam_bot.qty import QtyCalculator
from finam_bot.risk_engine_v2_2 import RiskEngineV22
from finam_bot.risk_config import MAX_RISK_PER_TRADE
from finam_bot.env import load_env

def main():
    # === 0. Infra ===
    load_env()
    storage = StorageSQLite()
    equity = 100_000.0  # временно, далее из account snapshot
    risk_engine = RiskEngineV22(storage=storage, equity=equity)

    print(f"EQUITY: {equity}")
    print(f"MAX_RISK_PER_TRADE: {MAX_RISK_PER_TRADE}")

    # === 1. Market data (временно mock) ===
    symbol = "NG-2.26"
    last_price = 3.11

    # === 2. Signal detection ===
    signal = None
    for strategy in STRATEGIES:
        signal = strategy.detect(symbol=symbol, price=last_price)
        if signal:
            break

    if not signal:
        print("NO SIGNAL")
        return

    print(f"SIGNAL: {signal}")

    # === 3. Asset class ===
    asset_class = get_asset_class(signal.symbol)
    print(f"ASSET_CLASS: {asset_class}")

    # === 4. Qty calculation ===
    qty = QtyCalculator(
        max_risk_per_trade=MAX_RISK_PER_TRADE
    ).calc(
        entry_price=signal.entry,
        stop_price=signal.stop,
        asset_class=asset_class,
    )

    print(f"QTY: {qty}")

    if qty <= 0:
        print("QTY BLOCKED")
        return

    # === 5. Risk v2.2 ===
    verdict = risk_engine.check(
        asset_class=asset_class,
        qty=qty,
        entry=signal.entry,
        stop=signal.stop,
    )

    allowed = verdict.allowed
    reason = verdict.reason

    if not allowed:
        print(f"⛔ BLOCKED: {reason}")
        return

    print(f"✅ ALLOWED [{asset_class}] qty={qty}")

    # === 6. Decision snapshot ===
    decision = {
        "decision_id": str(uuid.uuid4()),
        "ts": datetime.now(timezone.utc).isoformat(),
        "symbol": signal.symbol,
        "asset_class": asset_class,
        "side": signal.side,
        "entry": signal.entry,
        "stop": signal.stop,
        "qty": qty,
        "risk_allowed": allowed,
        "risk_reason": reason,
        "strategy": signal.reason,
        "confidence": signal.confidence,
    }

    storage.insert_decision(decision)
    print("🧠 DECISION STORED")


if __name__ == "__main__":
    main()