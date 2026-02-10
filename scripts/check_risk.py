from decimal import Decimal
from finam_bot.storage_sqlite import StorageSQLite
from finam_bot.risk_engine import RiskEngine

CAPITAL = Decimal("1000000")  # 1 млн

storage = StorageSQLite()
risk = RiskEngine(storage, CAPITAL)

allowed, reason = risk.allow_trade(Decimal("3000"))

print("ALLOWED:", allowed)
print("REASON :", reason)