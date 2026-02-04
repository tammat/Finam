# finam_bot/app.py

import asyncio

from finam_bot import config
from finam_bot.telegram.controller import TelegramController
from finam_bot.grpc.finam_grpc_client import FinamGrpcClient


async def main():
    # --- Telegram ---
    controller = TelegramController()
    await controller.run()

    # --- Finam gRPC ---
    grpc = FinamGrpcClient()

    try:
        # ====== SWITCH MARKET DATA SOURCE ======
        if config.MARKET_DATA_MODE == "events":
            print("📡 MARKET DATA MODE: REALTIME EVENTS (C+)")

            async for price in grpc.stream_events(symbol="GAZP"):
                await controller.on_price(price)

        else:
            print("🕯 MARKET DATA MODE: CANDLES (C)")

            async for price in grpc.stream_candles(
                symbol="GAZP",
                timeframe=config.CANDLES_TIMEFRAME,
                delay=config.CANDLES_DELAY,
            ):
                await controller.on_price(price)

    except (KeyboardInterrupt, asyncio.CancelledError):
        print("⛔ Остановка бота")

    finally:
        if controller.app:
            try:
                await controller.app.updater.stop()
            except Exception:
                pass

            await controller.app.stop()
            await controller.app.shutdown()
            print("🧹 Telegram бот корректно остановлен")


if __name__ == "__main__":
    asyncio.run(main())
