"""
Central configuration for Finam Trading Bot.

Controls:
- Trading mode (TEST / REAL)
- Assets & strategies
- Timeframes & styles
- Risk management
- Telegram
- Database (PostgreSQL)
"""

from enum import Enum
from pathlib import Path
from typing import Dict
import os

from dotenv import load_dotenv


# ---------------------------------------------------------------------
# ENV
# ---------------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = BASE_DIR / ".env"

load_dotenv(ENV_PATH)

# === MODE ===
READ_ONLY = True   # ⬅️ ВАЖНО



# === Trading config ===

START_EQUITY = float(
    os.getenv("START_EQUITY", 100_000)
)
# ---------------------------------------------------------------------
# GLOBAL MODES
# ---------------------------------------------------------------------

class Mode(str, Enum):
    TEST = "TEST"
    REAL = "REAL"


MODE: Mode = Mode(os.getenv("MODE", "TEST"))


# ---------------------------------------------------------------------
# ASSET TYPES
# ---------------------------------------------------------------------

class AssetType(str, Enum):
    STOCK = "STOCK"
    FUTURE = "FUTURE"
    BOND = "BOND"


ASSET_TYPE: AssetType = AssetType(os.getenv("ASSET_TYPE", "STOCK"))


# ---------------------------------------------------------------------
# TRADING STYLES / TIMEFRAMES
# ---------------------------------------------------------------------

class TradeStyle(str, Enum):
    SCALPING = "SCALPING"      # seconds / 1m
    INTRADAY = "INTRADAY"      # 5m–15m
    SWING = "SWING"            # 1h–4h
    POSITION = "POSITION"     # days / weeks


TRADE_STYLE: TradeStyle = TradeStyle(os.getenv("TRADE_STYLE", "INTRADAY"))


TIMEFRAMES: Dict[TradeStyle, str] = {
    TradeStyle.SCALPING: "1m",
    TradeStyle.INTRADAY: "5m",
    TradeStyle.SWING: "1h",
    TradeStyle.POSITION: "1d",
}


# ---------------------------------------------------------------------
# STRATEGIES
# ---------------------------------------------------------------------

class Strategy(str, Enum):
    SMA_EMA = "SMA_EMA"
    BOLLINGER = "BOLLINGER"
    BOND_YIELD = "BOND_YIELD"


STRATEGY: Strategy = Strategy(os.getenv("STRATEGY", "SMA_EMA"))


STRATEGY_PARAMS = {
    Strategy.SMA_EMA: {
        "sma_fast": 10,
        "sma_slow": 50,
        "ema_filter": 100,
    },
    Strategy.BOLLINGER: {
        "period": 20,
        "std_dev": 2.0,
    },
    Strategy.BOND_YIELD: {
        "lookback_days": 30,
    },
}


# ---------------------------------------------------------------------
# RISK MANAGEMENT
# ---------------------------------------------------------------------

MAX_RISK_PER_TRADE = float(os.getenv("MAX_RISK_PER_TRADE", 0.01))   # 1%
MAX_OPEN_POSITIONS = int(os.getenv("MAX_OPEN_POSITIONS", 3))

STOP_LOSS_PCT = float(os.getenv("STOP_LOSS_PCT", 0.02))
TAKE_PROFIT_PCT = float(os.getenv("TAKE_PROFIT_PCT", 0.04))


# ---------------------------------------------------------------------
# FINAM API
# ---------------------------------------------------------------------

FINAM_API_KEY: str | None = os.getenv("FINAM_API_KEY")
FINAM_ACCOUNT_ID: str | None = os.getenv("FINAM_ACCOUNT_ID")

if MODE == Mode.REAL and not FINAM_API_KEY:
    raise RuntimeError("FINAM_API_KEY is required in REAL mode")


# ---------------------------------------------------------------------
# TELEGRAM
# ---------------------------------------------------------------------

TELEGRAM_TOKEN: str | None = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID: str | None = os.getenv("TELEGRAM_CHAT_ID")

TELEGRAM_ALLOWED_USERS = (
    {int(TELEGRAM_CHAT_ID)} if TELEGRAM_CHAT_ID else set()
)

ENABLE_TELEGRAM_COMMANDS = True


# ---------------------------------------------------------------------
# DATABASE (PostgreSQL)
# ---------------------------------------------------------------------

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", 5432))
DB_NAME = os.getenv("DB_NAME", "finam")
DB_USER = os.getenv("DB_USER", "finam")
DB_PASSWORD = os.getenv("DB_PASSWORD", "finam")

DB_ECHO = os.getenv("DB_ECHO", "false").lower() == "true"

DATABASE_URL = (
    f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}"
    f"@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)


# ---------------------------------------------------------------------
# SYMBOL / MARKET
# ---------------------------------------------------------------------

SYMBOL: str = os.getenv("SYMBOL", "GAZP")
CURRENCY: str = os.getenv("CURRENCY", "RUB")
EXCHANGE: str = os.getenv("EXCHANGE", "MOEX")


# ---------------------------------------------------------------------
# LOGGING
# ---------------------------------------------------------------------

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_TO_FILE = True
LOG_FILE = BASE_DIR / "finam_bot.log"

# ---------------------------------------------------------------------
# DATABASE (PostgreSQL)
# ---------------------------------------------------------------------

DB_ENABLED = os.getenv("DB_ENABLED", "false").lower() == "true"

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", 5432))
DB_NAME = os.getenv("DB_NAME", "finam")
DB_USER = os.getenv("DB_USER", "finam")
DB_PASSWORD = os.getenv("DB_PASSWORD", "finam")

DB_ECHO = os.getenv("DB_ECHO", "false").lower() == "true"

DATABASE_URL = None
if DB_ENABLED:
    DATABASE_URL = (
        f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}"
        f"@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    )
# ---------------------------------------------------------------------
# DEBUG OUTPUT
# ---------------------------------------------------------------------

def dump_config() -> None:
    """Print current configuration (safe for TEST mode)."""
    print("=== FINAM BOT CONFIG ===")
    print(f"MODE: {MODE}")
    print(f"ASSET_TYPE: {ASSET_TYPE}")
    print(f"TRADE_STYLE: {TRADE_STYLE}")
    print(f"TIMEFRAME: {TIMEFRAMES[TRADE_STYLE]}")
    print(f"STRATEGY: {STRATEGY}")
    print(f"SYMBOL: {SYMBOL}")
    print(f"EXCHANGE: {EXCHANGE}")
    print(f"DATABASE_URL: {DATABASE_URL}")
    print("========================")

# Источник рыночных данных
#MARKET_DATA_MODE = "events"  # "candles" | "events"
MARKET_DATA_MODE = "candles"
# Для candles
CANDLES_TIMEFRAME = "M5"
CANDLES_DELAY = 10
# === ATR CONFIG ===

ATR_MODE = "BOTH"        # CLASSIC | EMA | BOTH
ATR_PERIOD = 14
ATR_EMA_PERIOD = 7       # быстрый ATR для 1m

SYMBOL = "NGG6"

ATR_MODE = "BOTH"
ATR_PERIOD = 14
ATR_EMA_PERIOD = 7



