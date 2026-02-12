# finam_bot/grpc/finam_grpc_client.py

import asyncio
from typing import AsyncIterator


print("🧪 Finam gRPC client initialized in TEST mode")


# -------------------------------------------------
# Fake REAL-compatible structures
# -------------------------------------------------

class _Portfolio:
    def __init__(self):
        self.account_id = "1943312"
        self.status = "ACCOUNT_ACTIVE"
        self.balance = 389451.37


class _FakePortfolioResponse:
    def __init__(self):
        self.portfolios = [_Portfolio()]


class _Event:
    def __init__(self):
        self.type = "TEST_EVENT"
        self.message = "Simulated event"


class _FakeEventsResponse:
    def __init__(self):
        self.events = [_Event()]


# -------------------------------------------------
# TEST gRPC Client
# -------------------------------------------------

class FinamGrpcClient:
    """
    TEST MODE client
    Fully interface-compatible with REAL client
    """

    def __init__(self):
        self.test_mode = True

    # -------------------------------------------------
    # Portfolio
    # -------------------------------------------------

    def get_portfolios_raw(self):
        print("🧪 TEST get_portfolios_raw()")
        return _FakePortfolioResponse()

    # -------------------------------------------------
    # Events
    # -------------------------------------------------

    def get_events_raw(self):
        print("🧪 TEST get_events_raw()")
        return _FakeEventsResponse()

    # -------------------------------------------------
    # Candles
    # -------------------------------------------------

    async def get_candles(self, symbol: str, timeframe: str = "1m"):
        print(f"🧪 TEST get_candles({symbol}, {timeframe})")
        return [100.0, 100.2, 100.1, 100.4, 100.3]

    async def stream_candles(
        self,
        symbol: str,
        timeframe: str = "1m",
    ) -> AsyncIterator[float]:
        while True:
            candles = await self.get_candles(symbol, timeframe)
            for price in candles:
                yield price
            await asyncio.sleep(1)

    # -------------------------------------------------
    # Orderflow
    # -------------------------------------------------

    async def stream_orderflow(self, symbol: str):
        while True:
            yield {
                "price": 100.0,
                "bid_volume": 1200,
                "ask_volume": 800,
            }
            await asyncio.sleep(0.5)
    # ------------------------------------------
    # Compatibility layer (for services)
    # ------------------------------------------

    def get_portfolios_raw(self):
        print("🧪 TEST get_portfolios_raw()")

        class _Portfolio:
            def __init__(self):
                self.account_id = "1943312"
                self.balance = 389451.37

        class _Response:
            portfolios = [_Portfolio()]

        return _Response()
    def get_events_raw(self):
        print("🧪 TEST get_events_raw()")

        class _Response:
            events = []

        return _Response()
    # -------------------------------------------------
    # Accounts
    # -------------------------------------------------

    def get_account(self):
        print("🧪 TEST get_account()")
        return {
            "account_id": "1943312",
            "status": "ACCOUNT_ACTIVE",
            "equity": 389451.37,
        }

    def get_trades(self, limit: int = 50):
        print("🧪 TEST get_trades()")
        return [
            {
                "trade_id": "T1",
                "symbol": "BRH6@RTSX",
                "side": 2,
                "qty": 1.0,
                "price": 70.39,
            }
        ]

    def get_transactions(self, days: int = 7, limit: int = 100):
        print("🧪 TEST get_transactions()")
        return [
            {
                "id": "TX1",
                "symbol": "",
                "category": 13,
                "amount": -1070.0,
                "currency": "RUB",
                "description": "TEST margin write-off",
            }
        ]

    # -------------------------------------------------
    # Orders
    # -------------------------------------------------

    def get_orders(self):
        print("🧪 TEST get_orders()")
        return []

    def get_order(self, order_id: str):
        print("🧪 TEST get_order()")
        return {"order_id": order_id, "status": "FILLED"}

    def cancel_order(self, order_id: str):
        print("🧪 TEST cancel_order()")
        return {"order_id": order_id, "status": "CANCELLED"}

    def health_check(self) -> bool:
        """
        Проверка доступности Finam API
        """
        try:
            self.get_account()
            return True
        except Exception as e:
            print("⚠ Health check failed:", e)
            return False