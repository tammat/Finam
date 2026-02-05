# finam_bot/strategies/br_intraday.py

from finam_bot.core.signals import Signal
from finam_bot.core.market_context import Bias, MarketContext
from finam_bot.core.market_snapshot import MarketSnapshot


class BRIntradayStrategy:
    """
    Brent intraday trend-pullback strategy
    (expert-style)
    """

    def on_market(
        self,
        snapshot: MarketSnapshot,
        context: MarketContext,
    ) -> Signal:

        # --- 1. Global permission ---
        if not context.trading_allowed:
            return Signal.HOLD

        price = snapshot.price
        ind = snapshot.indicators

        vwap = ind.get("vwap")
        rsi = ind.get("rsi")

        if vwap is None or rsi is None:
            return Signal.HOLD

        # --- 2. LONG ---
        if context.bias == Bias.LONG:
            if price >= vwap and 45 <= rsi <= 60:
                return Signal.BUY

        # --- 3. SHORT ---
        if context.bias == Bias.SHORT:
            if price <= vwap and 40 <= rsi <= 55:
                return Signal.SELL

        return Signal.HOLD
