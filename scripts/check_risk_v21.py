from finam_bot.storage_sqlite import StorageSQLite
from finam_bot.risk_v2.engine_v21 import RiskEngineV21
from finam_bot.risk_v2.config import RiskConfig


def main():
    storage = StorageSQLite()
    engine = RiskEngineV21(storage, RiskConfig())

    verdict = engine.check_entry(
        instrument="NG-2.26",
        side="BUY",
        entry_price=3.20,
        stop_price=3.05,
    )

    print("ALLOWED:", verdict.allowed)
    print("REASON :", verdict.reason)


if __name__ == "__main__":
    main()