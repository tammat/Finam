# finam_bot/app.py

import asyncio

from finam_bot.grpc.finam_grpc_client import FinamGrpcClient
from finam_bot.core.trade_engine import TradeEngine
from finam_bot.core.market_snapshot import MarketSnapshot

SYMBOL = "NGG6"


async def main():
    print("🟢 START S5.A — REAL DATA / READ-ONLY")

    grpc = FinamGrpcClient()
    engine = TradeEngine(symbol=SYMBOL)

    async for price in grpc.stream_candles(symbol=SYMBOL, timeframe="1m"):
        snapshot = MarketSnapshot(
            symbol=SYMBOL,
            price=price,
        )

        engine.on_market_data(snapshot)


if __name__ == "__main__":
    asyncio.run(main())
