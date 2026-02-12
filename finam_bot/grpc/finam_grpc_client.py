# finam_bot/grpc/finam_grpc_client.py

import asyncio
from typing import AsyncIterator, List
import os
print("🧪 Finam gRPC client initialized in TEST mode")


class FinamGrpcClient:
    """
    TEST MODE gRPC client
    Совместим с production adapters/services
    """

    def __init__(self):
        self.test_mode = True

    # -------------------------
    # Portfolios (RAW)
    # -------------------------

    class _Portfolio:
        def __init__(self, account_id: str, balance: float):
            self.account_id = account_id
            self.balance = balance

    class _PortfoliosResponse:
        def __init__(self, portfolios):
            self.portfolios = portfolios

    def get_portfolios_raw(self):
        print("🧪 TEST get_portfolios_raw()")

        account_id = os.getenv("FINAM_ACCOUNT_ID", "TEST_ACCOUNT")
        balance = float(os.getenv("TEST_BALANCE", "100000.0"))

        p = self._Portfolio(account_id=account_id, balance=balance)
        return self._PortfoliosResponse([p])

    # -------------------------
    # Events (RAW)
    # -------------------------

    class _EventsResponse:
        def __init__(self, events):
            self.events = events

    def get_events_raw(self):
        print("🧪 TEST get_events_raw()")
        return FinamGrpcClient._EventsResponse(events=[])

    # -------------------------
    # Market data stubs
    # -------------------------

    async def get_candles(self, symbol: str, timeframe: str = "1m") -> List[float]:
        print(f"🧪 TEST get_candles({symbol}, {timeframe})")
        return [100.0, 100.2, 100.1, 100.4, 100.3]

    async def stream_candles(self, symbol: str, timeframe: str = "1m") -> AsyncIterator[float]:
        while True:
            candles = await self.get_candles(symbol, timeframe)
            for price in candles:
                yield price
            await asyncio.sleep(1)

    async def stream_orderflow(self, symbol: str) -> AsyncIterator[dict]:
        while True:
            yield {"price": 100.0, "bid_volume": 1200, "ask_volume": 800}
            await asyncio.sleep(0.5)