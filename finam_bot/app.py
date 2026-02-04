# finam_bot/app.py

import asyncio
import random
from finam_bot.telegram.controller import TelegramController


async def price_feeder(controller: TelegramController):
    """
    TEST-генератор цен (имитация рынка)
    """
    price = 100.0

    while True:
        # небольшое случайное движение
        price += random.uniform(-1.5, 1.5)
        price = round(price, 2)

        await controller.on_price(price)
        await asyncio.sleep(1)


async def main():
    controller = TelegramController()

    await controller.run()

    # запускаем генератор цен в фоне
    asyncio.create_task(price_feeder(controller))

    try:
        # держим процесс живым
        while True:
            await asyncio.sleep(3600)

    except (KeyboardInterrupt, asyncio.CancelledError):
        print("⛔ Остановка бота")

    finally:
        if controller.app:
            await controller.app.stop()
            await controller.app.shutdown()
            print("🧹 Telegram бот корректно остановлен")


if __name__ == "__main__":
    asyncio.run(main())
