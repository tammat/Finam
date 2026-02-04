# finam_bot/app.py

import asyncio
from finam_bot.telegram.controller import TelegramController
from finam_bot.grpc.finam_grpc_client import FinamGrpcClient


async def main():
    controller = TelegramController()
    await controller.run()

    grpc = FinamGrpcClient()

    try:
        async for price in grpc.stream_candles(
            symbol="GAZP",
            timeframe="M5",
            delay=10,
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
