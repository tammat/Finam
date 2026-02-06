# finam_bot/tests/test_synthetic_candles.py
from finam_bot.backtest.synthetic import generate_synthetic_candles


def test_generate_length_and_ohlc_constraints():
    candles = generate_synthetic_candles(n=50, seed=1)
    assert len(candles) == 50

    for c in candles:
        assert c.high >= max(c.open, c.close)
        assert c.low <= min(c.open, c.close)
        assert c.high >= c.low


def test_ts_monotonic_when_enabled():
    candles = generate_synthetic_candles(n=10, start_ts=100, ts_step=5, seed=1)
    ts = [c.ts for c in candles]
    assert ts == list(range(100, 100 + 10 * 5, 5))


def test_trend_up_moves_up_on_average():
    candles = generate_synthetic_candles(
        n=60,
        mode="up",
        drift=0.05,
        volatility=0.02,
        seed=1,
    )
    assert candles[-1].close > candles[0].close


def test_trend_down_moves_down_on_average():
    candles = generate_synthetic_candles(
        n=60,
        mode="down",
        drift=0.05,
        volatility=0.02,
        seed=1,
    )
    assert candles[-1].close < candles[0].close
