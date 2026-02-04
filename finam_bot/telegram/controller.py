# finam_bot/telegram/controller.py

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
)

from finam_bot.core.trade_engine import TradeEngine
from finam_bot.strategies.sma_ema import SMAStrategy
from finam_bot import config


class TelegramController:
    def __init__(self):
        self.trading_enabled = False
        self.engine = TradeEngine(symbol="GAZP", qty=1)
        self.strategy = SMAStrategy(window=3)
        self.app = None

    # ---------- COMMANDS ----------

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            "🤖 Робот Финам запущен\n\n"
            "Команды:\n"
            "/trade_on — включить торговлю (TEST)\n"
            "/trade_off — выключить торговлю\n"
            "/status — статус\n"
            "/position — текущая позиция\n"
            "/pnl — результат"
        )

    async def trade_on(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        self.trading_enabled = True
        await update.message.reply_text("▶️ Торговля ВКЛЮЧЕНА (TEST)")

    async def trade_off(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        self.trading_enabled = False
        await update.message.reply_text("⏸ Торговля ВЫКЛЮЧЕНА")

    async def status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            f"📊 Статус\n"
            f"Режим: 🧪 TEST\n"
            f"Торговля: {'ON' if self.trading_enabled else 'OFF'}"
        )

    async def position(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        pos = self.engine.position
        if not pos:
            await update.message.reply_text("📭 Позиция отсутствует")
            return

        await update.message.reply_text(
            f"📈 Позиция\n"
            f"{pos.side} {pos.symbol}\n"
            f"Цена входа: {pos.entry_price}"
        )

    async def pnl(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            f"💰 PnL (TEST): {self.engine.total_pnl:.2f}"
        )

    # ---------- PRICE FEED ----------

    async def on_price(self, price: float):
        if not self.trading_enabled:
            return

        signal = self.strategy.on_price(price)
        self.engine.on_signal(signal, price)

    # ---------- RUN ----------

    async def run(self):
        if not config.TELEGRAM_TOKEN:
            raise RuntimeError("TELEGRAM_TOKEN не задан")

        self.app = ApplicationBuilder().token(config.TELEGRAM_TOKEN).build()

        self.app.add_handler(CommandHandler("start", self.start))
        self.app.add_handler(CommandHandler("trade_on", self.trade_on))
        self.app.add_handler(CommandHandler("trade_off", self.trade_off))
        self.app.add_handler(CommandHandler("status", self.status))
        self.app.add_handler(CommandHandler("position", self.position))
        self.app.add_handler(CommandHandler("pnl", self.pnl))

        print("🤖 Telegram бот запущен и готов принимать команды")

        await self.app.initialize()
        await self.app.start()
        await self.app.updater.start_polling()
