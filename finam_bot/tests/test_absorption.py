# finam_bot/tests/test_absorption.py

from finam_bot.core.orderflow_snapshot import OrderFlowSnapshot
from finam_bot.core.orderflow_analyzer import OrderFlowAnalyzer


def test_buy_absorption():
    snap = OrderFlowSnapshot(bid_volume=120, ask_volume=30)
    analyzer = OrderFlowAnalyzer(imbalance_threshold=0.6)

    signal = analyzer.analyze(snap)

    assert signal is not None
    assert signal.side == "BUY"
    assert signal.is_strong


def test_sell_absorption():
    snap = OrderFlowSnapshot(bid_volume=20, ask_volume=100)
    analyzer = OrderFlowAnalyzer(imbalance_threshold=0.6)

    signal = analyzer.analyze(snap)

    assert signal is not None
    assert signal.side == "SELL"
    assert signal.is_strong
