from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
)

from finam_bot.config import TELEGRAM_TOKEN


class TelegramController:
    def __init__(self):
        if not TELEGRAM_TOKEN:
            raise RuntimeError("TELEGRAM_TOKEN не задан")

        self.app = (
            ApplicationBuilder()
            .token(TELEGRAM_TOKEN)
            .build()
        )

        self.app.add_handler(CommandHandler("start", self.start))
        self.app.add_handler(CommandHandler("status", self.status))

    # === Handlers ===

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            "🤖 Finam bot запущен\n"
            "Команды:\n"
            "/status — состояние"
        )

    async def status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("🟢 Bot работает (READ-ONLY)")

    # === Lifecycle ===

    def start_polling(self):
        print("🤖 Telegram бот запущен")
        self.app.run_polling(stop_signals=None)
