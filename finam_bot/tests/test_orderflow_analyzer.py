from finam_bot.core.orderflow_snapshot import OrderFlowSnapshot
from finam_bot.core.orderflow_analyzer import OrderFlowAnalyzer


def test_no_signal_low_volume():
    snap = OrderFlowSnapshot(10, 5)
    analyzer = OrderFlowAnalyzer(min_volume=50)
    assert analyzer.analyze(snap) is None


def test_buy_signal():
    snap = OrderFlowSnapshot(120, 30)
    analyzer = OrderFlowAnalyzer(imbalance_threshold=0.6)
    signal = analyzer.analyze(snap)

    assert signal is not None
    assert signal.side == "BUY"
    assert signal.is_strong
    assert signal.imbalance > 0


def test_sell_signal():
    snap = OrderFlowSnapshot(20, 100)
    analyzer = OrderFlowAnalyzer(imbalance_threshold=0.6)
    signal = analyzer.analyze(snap)

    assert signal is not None
    assert signal.side == "SELL"
    assert signal.is_strong
    assert signal.imbalance < 0


def test_no_signal_neutral_flow():
    snap = OrderFlowSnapshot(60, 40)
    analyzer = OrderFlowAnalyzer(imbalance_threshold=0.6)
    assert analyzer.analyze(snap) is None
