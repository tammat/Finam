# finam_bot/portfolio/snapshot.py

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Protocol


class ClientLike(Protocol):
    def get_portfolios(self) -> List[Dict[str, Any]]: ...
    def get_positions(self) -> List[Dict[str, Any]]: ...
    def get_trades(self, limit: int = 100) -> List[Dict[str, Any]]: ...
    def get_transactions(self, days: int = 7, limit: int = 100) -> List[Dict[str, Any]]: ...


@dataclass(frozen=True)
class PortfolioSnapshot:
    portfolios: List[Dict[str, Any]]
    positions: List[Dict[str, Any]]
    trades: List[Dict[str, Any]]
    transactions: List[Dict[str, Any]]


def build_snapshot(
    client: ClientLike,
    trades_limit: int = 100,
    tx_days: int = 7,
    tx_limit: int = 100,
) -> PortfolioSnapshot:
    return PortfolioSnapshot(
        portfolios=client.get_portfolios(),
        positions=client.get_positions(),
        trades=client.get_trades(limit=trades_limit),
        transactions=client.get_transactions(days=tx_days, limit=tx_limit),
    )