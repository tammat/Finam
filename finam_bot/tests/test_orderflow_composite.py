from typing import Optional

from finam_bot.core.orderflow_signal import OrderFlowSignal, AbsorptionSignal
from finam_bot.core.orderflow_composite import build_composite_signal


def test_buy_with_absorption_has_high_confidence():
    imbalance = OrderFlowSignal(
        side="BUY",
        strength=0.7,
        imbalance=0.7,
        reason="imbalance",
    )
    absorption = AbsorptionSignal(
        side="BUY",
        strength=120,
        imbalance=0.0,
        reason="absorption",
    )

    composite = build_composite_signal(
        imbalance=imbalance,
        absorption=absorption,
    )

    assert composite is not None
    assert composite.side == "BUY"
    assert composite.confidence == 1.0
    assert "absorption" in composite.reasons


def test_buy_without_absorption_is_medium_confidence():
    imbalance = OrderFlowSignal(
        side="BUY",
        strength=0.65,
        imbalance=0.65,
        reason="imbalance",
    )

    composite = build_composite_signal(
        imbalance=imbalance,
        absorption=None,
    )

    assert composite is not None
    assert composite.confidence == 0.65


def test_absorption_against_imbalance_blocks_signal():
    imbalance = OrderFlowSignal(
        side="BUY",
        strength=0.7,
        imbalance=0.7,
        reason="imbalance",
    )
    absorption = AbsorptionSignal(
        side="SELL",
        strength=150,
        imbalance=0.0,
        reason="absorption",
    )

    composite = build_composite_signal(
        imbalance=imbalance,
        absorption=absorption,
    )

    assert composite is None


def test_absorption_without_imbalance_gives_no_signal():
    absorption = AbsorptionSignal(
        side="BUY",
        strength=200,
        imbalance=0.0,
        reason="absorption",
    )

    composite = build_composite_signal(
        imbalance=None,
        absorption=absorption,
    )

    assert composite is None
