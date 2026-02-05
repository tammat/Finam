import math

from finam_bot.core.orderflow_accumulator import (
    OrderFlowAccumulator,
    OrderFlowSnapshot,
)


def assert_snapshot(
    snap: OrderFlowSnapshot,
    *,
    bid: float,
    ask: float,
    total: float,
    delta: float,
    trades: int,
    vwap: float | None,
):
    assert snap.bid_volume == bid
    assert snap.ask_volume == ask
    assert snap.total_volume == total
    assert snap.delta == delta
    assert snap.trades == trades

    if vwap is None:
        assert snap.vwap is None
    else:
        assert math.isclose(snap.vwap, vwap, rel_tol=1e-6)


def test_empty_flush():
    acc = OrderFlowAccumulator()

    snap = acc.flush()

    assert_snapshot(
        snap,
        bid=0.0,
        ask=0.0,
        total=0.0,
        delta=0.0,
        trades=0,
        vwap=None,
    )


def test_single_buy_trade():
    acc = OrderFlowAccumulator()

    acc.update(price=100.0, qty=10, side="BUY")
    snap = acc.flush()

    assert_snapshot(
        snap,
        bid=0.0,
        ask=10.0,
        total=10.0,
        delta=-10.0,
        trades=1,
        vwap=100.0,
    )


def test_single_sell_trade():
    acc = OrderFlowAccumulator()

    acc.update(price=100.0, qty=7, side="SELL")
    snap = acc.flush()

    assert_snapshot(
        snap,
        bid=7.0,
        ask=0.0,
        total=7.0,
        delta=7.0,
        trades=1,
        vwap=100.0,
    )


def test_mixed_trades():
    acc = OrderFlowAccumulator()

    acc.update(price=100.0, qty=10, side="BUY")
    acc.update(price=99.5, qty=5, side="SELL")
    acc.update(price=100.5, qty=15, side="BUY")

    snap = acc.flush()

    expected_vwap = (
        100.0 * 10 +
        99.5 * 5 +
        100.5 * 15
    ) / 30

    assert_snapshot(
        snap,
        bid=5.0,
        ask=25.0,
        total=30.0,
        delta=-20.0,
        trades=3,
        vwap=expected_vwap,
    )


def test_flush_resets_state():
    acc = OrderFlowAccumulator()

    acc.update(price=100.0, qty=10, side="BUY")
    snap1 = acc.flush()

    snap2 = acc.flush()

    assert snap1.total_volume == 10.0
    assert snap2.total_volume == 0.0
    assert snap2.trades == 0


def test_ignores_zero_and_negative_qty():
    acc = OrderFlowAccumulator()

    acc.update(price=100.0, qty=0, side="BUY")
    acc.update(price=100.0, qty=-5, side="SELL")

    snap = acc.flush()

    assert_snapshot(
        snap,
        bid=0.0,
        ask=0.0,
        total=0.0,
        delta=0.0,
        trades=0,
        vwap=None,
    )


def test_ignores_unknown_side():
    acc = OrderFlowAccumulator()

    acc.update(price=100.0, qty=10, side="UNKNOWN")

    snap = acc.flush()

    assert snap.total_volume == 0.0
    assert snap.trades == 0
