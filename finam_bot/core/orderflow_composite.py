from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, List

from finam_bot.core.orderflow_signal import OrderFlowSignal, AbsorptionSignal


@dataclass
class CompositeOrderFlowSignal:
    side: str                 # "BUY" | "SELL"
    confidence: float         # 0.0 .. 1.0
    reasons: List[str]


def build_composite_signal(
    imbalance: Optional[OrderFlowSignal],
    absorption: Optional[AbsorptionSignal],
) -> Optional[CompositeOrderFlowSignal]:
    # 1) нет imbalance -> нет сигнала
    if imbalance is None:
        return None

    # 2) absorption против направления -> блок
    if absorption is not None and absorption.side is not None:
        if absorption.side != imbalance.side:
            return None

    reasons = [imbalance.reason]
    confidence = float(imbalance.strength)

    # 3) absorption усиливает ТОЛЬКО если side совпадает (не None)
    if absorption is not None and absorption.side == imbalance.side:
        reasons.append("absorption")
        confidence = 1.0

    confidence = min(confidence, 1.0)

    return CompositeOrderFlowSignal(
        side=imbalance.side,
        confidence=confidence,
        reasons=reasons,
    )
