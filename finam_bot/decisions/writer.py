from datetime import datetime, timezone
import uuid


class DecisionWriter:
    def __init__(self, storage):
        self.storage = storage

    def write(self, signal, qty, verdict: bool, reason: str) -> dict:
        decision = {
            "decision_id": str(uuid.uuid4()),
            "ts": datetime.now(timezone.utc).isoformat(),
            "symbol": signal.symbol,
            "asset_class": signal.asset_class,
            "side": signal.side,
            "entry": signal.entry,
            "stop": signal.stop,
            "qty": qty,
            "risk_allowed": verdict,
            "risk_reason": reason,
            "strategy": getattr(signal, "reason", None),
            "confidence": getattr(signal, "confidence", None),
        }

        self.storage.insert_decision(decision)
        return decision