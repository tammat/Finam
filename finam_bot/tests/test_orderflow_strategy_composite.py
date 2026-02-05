from finam_bot.strategies.order_flow_pullback import OrderFlowPullbackStrategy
from finam_bot.core.market_snapshot import MarketSnapshot
from finam_bot.core.signals import Signal


def make_snapshot(
    price: float,
    bid_volume: float,
    ask_volume: float,
    prices=None,
    volumes=None,
):
    return MarketSnapshot(
        symbol="TEST",
        price=price,
        bid_volume=bid_volume,
        ask_volume=ask_volume,
        prices=prices or [],
        volumes=volumes or [],
    )


def test_buy_signal_with_absorption_has_high_confidence():
    strategy = OrderFlowPullbackStrategy()

    snapshot = make_snapshot(
        price=100.0,
        bid_volume=120,
        ask_volume=30,
        prices=[100.0, 100.01, 99.99],
        volumes=[40, 40, 50],
    )

    signal = strategy.on_snapshot(snapshot)
    assert signal.value == Signal.BUY.value
    assert strategy.last_confidence == 1.0


def test_buy_signal_without_absorption_is_medium_confidence():
    strategy = OrderFlowPullbackStrategy()

    snapshot = make_snapshot(
        price=100.0,
        bid_volume=130,
        ask_volume=50,
        prices=[],        # ❗ нет absorption
        volumes=[],
    )

    signal = strategy.on_snapshot(snapshot)

    assert signal.value == Signal.BUY.value
    assert 0.6 <= strategy.last_confidence < 1.0


def test_absorption_against_imbalance_blocks_trade():
    strategy = OrderFlowPullbackStrategy()

    snapshot = make_snapshot(
        price=100.0,
        bid_volume=140,
        ask_volume=40,     # BUY imbalance
        prices=[100.0, 100.0, 100.0],
        volumes=[200],    # absorption
    )

    # вручную симулируем "против" — через volumes/price неважно,
    # важно, что стратегия должна HOLD
    strategy.absorption_detector.price_tolerance = 0.00001

    signal = strategy.on_snapshot(snapshot)

    assert signal == Signal.HOLD
    assert strategy.last_confidence == 0.0


def test_no_signal_sets_confidence_to_zero():
    strategy = OrderFlowPullbackStrategy()

    snapshot = make_snapshot(
        price=100.0,
        bid_volume=50,
        ask_volume=50,
    )

    signal = strategy.on_snapshot(snapshot)

    assert signal == Signal.HOLD
    assert strategy.last_confidence == 0.0
