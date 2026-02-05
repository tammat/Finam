import pytest

from finam_bot.core.orderflow_snapshot import OrderFlowSnapshot
from finam_bot.core.orderflow_analyzer import OrderFlowAnalyzer
from finam_bot.core.orderflow_signal import AbsorptionSignal, OrderFlowSignal
# finam_bot/tests/test_orderflow_absorption.py

from finam_bot.core.orderflow_absorption import OrderFlowAbsorptionDetector


def test_absorption_detected_on_high_volume_flat_price():
    detector = OrderFlowAbsorptionDetector(
        min_volume=100,
        price_tolerance=0.01,
    )

    prices = [100.0, 100.01, 99.99, 100.0]
    volumes = [30, 40, 50]

    signal = detector.analyze(prices=prices, volumes=volumes)

    assert signal is not None
    assert signal.reason == "absorption"
