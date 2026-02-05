# finam_bot/grpc/finam_grpc_client.py

# finam_bot/grpc/finam_grpc_client.py

import asyncio
from typing import AsyncIterator, List

print("🧪 Finam gRPC client initialized in TEST mode")


class FinamGrpcClient:
    """
    READ-ONLY gRPC client.
    Пока работаем ТОЛЬКО в тестовом режиме.
    """

    def __init__(self):
        self.test_mode = True

    async def get_candles(self, symbol: str, timeframe: str = "1m") -> List[float]:
        """
        TEST candles — возвращаем фейковые цены
        """
        print(f"🧪 TEST get_candles({symbol}, {timeframe})")
        return [
            100.0,
            100.2,
            100.1,
            100.4,
            100.3,
        ]

    async def stream_candles(self, symbol: str, timeframe: str = "1m") -> AsyncIterator[float]:
        """
        Асинхронный стрим цен (TEST)
        """
        while True:
            candles = await self.get_candles(symbol, timeframe)
            for price in candles:
                yield price
            await asyncio.sleep(1)
