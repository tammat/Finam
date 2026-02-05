# finam_bot/tests/test_orderflow_composite_neutral.py

from finam_bot.core.orderflow_composite import build_composite_signal
from finam_bot.core.orderflow_signal import OrderFlowSignal, AbsorptionSignal


def test_absorption_opposite_side_blocks():
    imbalance = OrderFlowSignal(
        side="BUY",
        strength=0.7,
        imbalance=0.7,
        reason="imbalance",
    )
    absorption = AbsorptionSignal(
        side="SELL",          # ⛔ против BUY
        strength=150,
        imbalance=0.0,
        reason="absorption",
    )

    composite = build_composite_signal(imbalance=imbalance, absorption=absorption)
    assert composite is None


def test_absorption_neutral_does_not_boost_confidence():
    imbalance = OrderFlowSignal(
        side="BUY",
        strength=0.7,
        imbalance=0.7,
        reason="imbalance",
    )
    absorption_neutral = AbsorptionSignal(
        side=None,            # ✅ neutral
        strength=200,
        imbalance=0.0,
        reason="absorption",
    )

    composite = build_composite_signal(imbalance=imbalance, absorption=absorption_neutral)

    assert composite is not None
    assert composite.side == "BUY"
    # ✅ НЕ усиливает до 1.0
    assert composite.confidence == imbalance.strength
    # ✅ НЕ добавляет "absorption" как усиление
    assert "absorption" not in composite.reasons
