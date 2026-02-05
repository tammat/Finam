from finam_bot.core.orderflow_snapshot import OrderFlowSnapshot


def test_empty_snapshot():
    snap = OrderFlowSnapshot(0, 0)
    assert snap.total_volume == 0
    assert snap.delta == 0
    assert snap.imbalance == 0
    assert snap.dominant_side is None


def test_buy_dominant():
    snap = OrderFlowSnapshot(bid_volume=120, ask_volume=30)
    assert snap.delta == 90
    assert snap.dominant_side == "BUY"
    assert snap.imbalance > 0


def test_sell_dominant():
    snap = OrderFlowSnapshot(bid_volume=40, ask_volume=100)
    assert snap.delta == -60
    assert snap.dominant_side == "SELL"
    assert snap.imbalance < 0


def test_aggressive_flow():
    snap = OrderFlowSnapshot(180, 20)
    assert snap.is_aggressive(threshold=0.6)


def test_non_aggressive_flow():
    snap = OrderFlowSnapshot(60, 40)
    assert not snap.is_aggressive(threshold=0.6)
