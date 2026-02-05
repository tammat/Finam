import asyncio
from typing import AsyncIterator, List

print("🧪 Finam gRPC client initialized in TEST mode")


class FinamGrpcClient:
    """
    READ-ONLY gRPC client (S7)
    TEST MODE
    """

    def __init__(self):
        self.test_mode = True

    async def get_candles(
        self,
        symbol: str,
        timeframe: str = "1m"
    ) -> List[float]:
        """
        TEST candles — fake prices
        """
        print(f"🧪 TEST get_candles({symbol}, {timeframe})")
        return [
            100.0,
            100.2,
            100.1,
            100.4,
            100.3,
        ]

    async def stream_candles(
        self,
        symbol: str,
        timeframe: str = "1m",
    ) -> AsyncIterator[float]:
        """
        TEST candle stream
        """
        while True:
            candles = await self.get_candles(symbol, timeframe)
            for price in candles:
                yield price
            await asyncio.sleep(1)

    async def stream_orderflow(
        self,
        symbol: str,
    ) -> AsyncIterator[dict]:
        """
        S7.D — orderflow stream (STUB)
        """
        while True:
            yield {
                "price": 100.0,
                "bid_volume": 1200,
                "ask_volume": 800,
            }
            await asyncio.sleep(0.5)
