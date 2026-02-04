# finam_bot/grpc/finam_grpc_client.py

import grpc
import asyncio
from finam_bot.grpc.candle_adapter import candle_close_price
from typing import Optional

from finam_bot import config

# gRPC stubs
from finam_bot.grpc.generated.proto.tradeapi.v1 import (
    candles_pb2,
    candles_pb2_grpc,
    common_pb2,
)


class FinamGrpcClient:
    """
    gRPC client for Finam Trade API.
    All gRPC logic is isolated here.
    """

    def __init__(self) -> None:
        self._channel: Optional[grpc.Channel] = None
        self._candles_stub: Optional[candles_pb2_grpc.CandlesServiceStub] = None

        if config.MODE.value == "REAL":
            self._connect()
        else:
            # TEST mode — no real connections
            print("🧪 Finam gRPC client initialized in TEST mode")

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _connect(self) -> None:
        if not config.FINAM_API_KEY:
            raise RuntimeError("FINAM_API_KEY не задан")

        # gRPC endpoint Финама (пример, можно вынести в config)
        target = "trade-api.finam.ru:443"

        credentials = grpc.ssl_channel_credentials()

        self._channel = grpc.secure_channel(
            target,
            credentials,
        )

        self._candles_stub = candles_pb2_grpc.CandlesServiceStub(self._channel)

        print("✅ Finam gRPC channel connected")

    def _metadata(self):
        return (
            ("authorization", f"Bearer {config.FINAM_API_KEY}"),
        )

    # ------------------------------------------------------------------
    # Market Data
    # ------------------------------------------------------------------

    def get_candles(
        self,
        symbol: str,
        timeframe: str,
        limit: int = 100,
    ):
        """
        Получение свечей.
        В TEST режиме возвращает пустой список.
        """

        if config.MODE.value != "REAL":
            print(f"🧪 TEST get_candles({symbol}, {timeframe})")
            return []

        if not self._candles_stub:
            raise RuntimeError("CandlesServiceStub не инициализирован")

        request = candles_pb2.GetCandlesRequest(
            security_code=symbol,
            timeframe=timeframe,
            count=limit,
        )

        response = self._candles_stub.GetCandles(
            request,
            metadata=self._metadata(),
        )

        return response.candles

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def close(self) -> None:
        if self._channel:
            self._channel.close()
            print("🔌 Finam gRPC channel closed")
    async def stream_candles(
        self,
        symbol: str,
        timeframe: str = "M5",
        delay: int = 10,
    ):
        """
        Асинхронный генератор свечей (TEST-safe).
        get_candles() синхронный → выносим в thread.
        """
        while True:
            candles = await asyncio.to_thread(
                self.get_candles,
                symbol,
                timeframe,
            )

            for candle in candles:
                price = candle_close_price(candle)
                yield price

            await asyncio.sleep(delay)
