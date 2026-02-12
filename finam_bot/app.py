# finam_bot/app.py

import asyncio

from finam_bot import config
from finam_bot.grpc import FinamGrpcClient
from finam_bot.core.trade_engine import TradeEngine
from finam_bot.core.market_snapshot import MarketSnapshot
from finam_bot.telegram.controller import TelegramController


async def market_loop(engine: TradeEngine, grpc: FinamGrpcClient):
    """
    Market data → snapshots → TradeEngine
    """
    if config.MARKET_DATA_MODE == "events":
        print("📡 MARKET DATA MODE: REALTIME EVENTS")

        async for event in grpc.stream_events(symbol=config.SYMBOL):
            snapshot = MarketSnapshot.from_event(event)
            engine.on_market_data(snapshot)

    else:
        print("🕯 MARKET DATA MODE: CANDLES")

        async for candle in grpc.stream_candles(
            symbol=config.SYMBOL,
            timeframe=config.CANDLES_TIMEFRAME,
        ):
            snapshot = MarketSnapshot.from_candle(
                symbol=config.SYMBOL,
                candle=candle,
            )
            engine.on_market_data(snapshot)


async def main():
    print("🟢 START S7.C — STREAM → SNAPSHOT → ENGINE")

    from finam_bot.grpc.factory import create_client
    grpc = create_client()
    engine = TradeEngine(
        symbol=config.SYMBOL,
        equity=config.START_EQUITY,
    )

    #telegram = TelegramController(engine=engine)

    # --- параллельный запуск ---
    await asyncio.gather(
   #     telegram.run(),
        market_loop(engine, grpc),
    )


if __name__ == "__main__":
    asyncio.run(main())
