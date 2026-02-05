# finam_bot/core/orderflow_composite.py

from typing import Optional
from finam_bot.core.orderflow_signal import OrderFlowSignal, AbsorptionSignal


class CompositeOrderFlowSignal:
    def __init__(
        self,
        side: str,
        confidence: float,
        reasons: list[str],
    ):
        self.side = side
        self.confidence = confidence
        self.reasons = reasons


def build_composite_signal(
    imbalance: Optional[OrderFlowSignal],
    absorption: Optional[AbsorptionSignal],
) -> Optional[CompositeOrderFlowSignal]:

    # 1️⃣ нет imbalance → нет сигнала
    if imbalance is None:
        return None

    # 2️⃣ absorption ПРОТИВ → блок
    if absorption is not None and absorption.side != imbalance.side:
        return None

    confidence = imbalance.strength
    reasons = [imbalance.reason]

    # 3️⃣ absorption усиливает
    if absorption is not None:
        confidence = 1.0
        reasons.append("absorption")

    confidence = min(confidence, 1.0)

    return CompositeOrderFlowSignal(
        side=imbalance.side,
        confidence=confidence,
        reasons=reasons,
    )
