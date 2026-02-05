from finam_bot.core.market_snapshot import MarketSnapshot
from finam_bot.core.orderflow_absorption import OrderFlowAbsorptionDetector


def make_snapshot(bid, ask, prices, volumes):
    return MarketSnapshot(
        symbol="TEST",
        price=prices[-1],
        bid_volume=bid,
        ask_volume=ask,
        prices=prices,
        volumes=volumes,
    )


def test_absorption_side_buy_when_bid_dominates():
    det = OrderFlowAbsorptionDetector(min_volume=100, price_tolerance=0.01)
    snap = make_snapshot(
        bid=200, ask=50,
        prices=[100.0, 100.01, 99.99, 100.0],
        volumes=[40, 40, 50],
    )
    sig = det.analyze_snapshot(snap)
    assert sig is not None
    assert sig.side == "BUY"


def test_absorption_side_sell_when_ask_dominates():
    det = OrderFlowAbsorptionDetector(min_volume=100, price_tolerance=0.01)
    snap = make_snapshot(
        bid=50, ask=200,
        prices=[100.0, 100.01, 99.99, 100.0],
        volumes=[40, 40, 50],
    )
    sig = det.analyze_snapshot(snap)
    assert sig is not None
    assert sig.side == "SELL"


def test_absorption_side_none_when_neutral():
    det = OrderFlowAbsorptionDetector(min_volume=100, price_tolerance=0.01)
    snap = make_snapshot(
        bid=100, ask=100,
        prices=[100.0, 100.01, 99.99, 100.0],
        volumes=[40, 40, 50],
    )
    sig = det.analyze_snapshot(snap)
    assert sig is not None
    assert sig.side is None
