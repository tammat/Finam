# finam_bot/qty/rules.py

from dataclasses import dataclass


@dataclass(frozen=True)
class QtyRule:
    step: float
    min_qty: float


# ЕДИНЫЙ РЕЕСТР ПРАВИЛ
QTY_RULES = {
    "FUTURES": QtyRule(
        step=1.0,
        min_qty=1.0,
    ),
    "STOCKS": QtyRule(
        step=1.0,
        min_qty=1.0,
    ),
    "BONDS": QtyRule(
        step=1.0,
        min_qty=1.0,
    ),
    "FX": QtyRule(
        step=1000.0,
        min_qty=1000.0,
    ),
}