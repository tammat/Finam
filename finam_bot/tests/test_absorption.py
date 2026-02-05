from finam_bot.core.orderflow_snapshot import OrderFlowSnapshot
from finam_bot.core.orderflow_analyzer import OrderFlowAnalyzer
from finam_bot.core.orderflow_signal import AbsorptionSignal

def test_buy_absorption():
    snap = OrderFlowSnapshot(buy_volume=120, sell_volume=30)
    analyzer = OrderFlowAnalyzer(imbalance_threshold=0.6)

    signal = analyzer.analyze(snap, price_delta=-0.01)

    assert isinstance(signal, AbsorptionSignal)
    assert signal.side == "BUY"
    assert signal.reason == "buy_absorption"

def test_sell_absorption():
    snap = OrderFlowSnapshot(buy_volume=20, sell_volume=100)
    analyzer = OrderFlowAnalyzer(imbalance_threshold=0.6)

    signal = analyzer.analyze(snap, price_delta=0.02)

    assert isinstance(signal, AbsorptionSignal)
    assert signal.side == "SELL"
