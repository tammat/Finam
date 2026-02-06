# finam_bot/backtest/metrics.py
from __future__ import annotations
from dataclasses import dataclass
from math import sqrt
from typing import Iterable

from finam_bot.backtest.models import Trade


@dataclass
class BacktestReport:
    trades: int
    wins: int
    losses: int
    winrate: float
    gross_pnl: float
    avg_pnl: float
    expectancy: float
    max_drawdown: float


def compute_drawdown(equity_curve: list[float]) -> float:
    peak = float("-inf")
    max_dd = 0.0
    for e in equity_curve:
        peak = max(peak, e)
        dd = peak - e
        max_dd = max(max_dd, dd)
    return max_dd


def summarize(trades: list[Trade], equity_curve: list[float]) -> BacktestReport:
    n = len(trades)
    if n == 0:
        return BacktestReport(
            trades=0, wins=0, losses=0, winrate=0.0,
            gross_pnl=0.0, avg_pnl=0.0, expectancy=0.0,
            max_drawdown=compute_drawdown(equity_curve) if equity_curve else 0.0,
        )

    pnls = [t.pnl for t in trades]
    wins = sum(1 for p in pnls if p > 0)
    losses = sum(1 for p in pnls if p <= 0)

    gross = sum(pnls)
    avg = gross / n

    # expectancy = P(win)*avg_win + P(loss)*avg_loss
    win_p = wins / n
    loss_p = 1.0 - win_p
    avg_win = sum(p for p in pnls if p > 0) / wins if wins else 0.0
    avg_loss = sum(p for p in pnls if p <= 0) / losses if losses else 0.0
    expectancy = win_p * avg_win + loss_p * avg_loss

    return BacktestReport(
        trades=n,
        wins=wins,
        losses=losses,
        winrate=win_p,
        gross_pnl=gross,
        avg_pnl=avg,
        expectancy=expectancy,
        max_drawdown=compute_drawdown(equity_curve),
    )
