import pytest

from finam_bot.backtest.engine import BacktestEngine
from finam_bot.backtest.models import Candle


class BuyOnceStrategy:
    """Сигнал BUY один раз на первой свече, потом HOLD."""
    def __init__(self):
        self._done = False

    def on_candle(self, candle, snapshot=None):
        if self._done:
            return "HOLD"
        self._done = True
        return "BUY"


def _make_engine(fill_policy: str) -> BacktestEngine:
    engine = BacktestEngine(
        symbol="TEST",
        strategy=BuyOnceStrategy(),
        start_equity=10_000.0,
        commission_rate=0.0,   # чтобы тест был чистый
        max_leverage=2.0,
        atr_period=1,
        fill_policy=fill_policy,
    )

    # Делаем тест независимым от RiskManager
    class FakeTrade:
        qty = 10.0
        stop_loss = 99.0
        take_profit = 101.0

    engine.risk.calculate = lambda **kwargs: FakeTrade()
    return engine


@pytest.mark.parametrize(
    "fill_policy, expected_reason",
    [
        ("worst", "STOP"),
        ("best", "TAKE"),
    ],
)
def test_fill_policy_when_stop_and_take_in_same_candle(fill_policy, expected_reason):
    # Бар0: стратегия выдаёт BUY -> вход на Бар1 open
    # Бар1: high >= TP и low <= SL одновременно -> выбор зависит от fill_policy
    candles = [
        Candle(ts=1, open=100.0, high=100.2, low=99.8, close=100.0),
        Candle(ts=2, open=100.0, high=101.5, low=98.5, close=100.0),
    ]

    engine = _make_engine(fill_policy)
    broker = engine.run(candles)

    assert len(broker.trades) == 1
    assert broker.trades[0].reason == expected_reason
