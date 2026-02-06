from __future__ import annotations

import pytest

from finam_bot.backtest.models import Candle
from finam_bot.backtest.engine import BacktestEngine
from finam_bot.core.signals import Signal


class BuyOnceStrategy:
    def __init__(self):
        self._did = False

    def on_snapshot(self, snapshot):
        if not self._did:
            self._did = True
            return Signal.BUY
        return Signal.HOLD


def test_backtest_take_profit_with_commission():
    candles = [
        Candle(ts=1, open=100.0, high=100.5, low=99.5, close=100.0),
        Candle(ts=2, open=100.0, high=101.0, low=99.0, close=100.5),
    ]

    engine = BacktestEngine(
        symbol="TEST",
        strategy=BuyOnceStrategy(),
        start_equity=10_000.0,
        commission_rate=0.0004,  # 0.04%
        max_leverage=2.0,
        atr_period=1,
    )

    # ✅ делаем тест независимым от RiskManager
    class FakeTrade:
        qty = 10.0
        stop_loss = 98.0
        take_profit = 101.0

    engine.risk.calculate = lambda **kwargs: FakeTrade()

    broker = engine.run(candles)

    assert len(broker.trades) == 1
    t = broker.trades[0]
    assert t.reason == "TAKE"

    # Entry: 100.0 (open свечи 2), Exit: 101.0 => pnl = (101-100)*10 = 10
    # Fee entry = 100*10*0.0004 = 0.4
    # Fee exit  = 101*10*0.0004 = 0.404
    # Equity = 10000 - 0.4 - 0.404 + 10 = 10009.196
    assert broker.equity == pytest.approx(10009.196, rel=1e-9, abs=1e-9)
