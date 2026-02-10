from dataclasses import dataclass

@dataclass(frozen=True)
class QtyRules:
    min_qty: float = 1.0
    step: float = 1.0   # шаг количества (1 акция, 1 контракт)