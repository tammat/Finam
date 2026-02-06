# finam_bot/backtest/metrics.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence, Optional, Dict, Any, List


def compute_drawdown(equity_curve: Sequence[float]) -> Dict[str, float]:
    """Return drawdown stats for an equity curve.

    Returns:
      {
        "max_drawdown": float,         # absolute money drawdown (>=0)
        "max_drawdown_pct": float,     # fraction, e.g. 0.123 = 12.3%
        "peak_equity": float,
        "trough_equity": float,
      }
    """
    if not equity_curve:
        return {
            "max_drawdown": 0.0,
            "max_drawdown_pct": 0.0,
            "peak_equity": 0.0,
            "trough_equity": 0.0,
        }

    peak = float(equity_curve[0])
    trough = float(equity_curve[0])
    max_dd = 0.0
    max_dd_pct = 0.0
    peak_at_max = peak
    trough_at_max = trough

    for x in equity_curve:
        eq = float(x)
        if eq > peak:
            peak = eq
            trough = eq
        if eq < trough:
            trough = eq

        dd = peak - eq
        dd_pct = (dd / peak) if peak > 0 else 0.0

        if dd > max_dd:
            max_dd = dd
            max_dd_pct = dd_pct
            peak_at_max = peak
            trough_at_max = eq

    return {
        "max_drawdown": float(max_dd),
        "max_drawdown_pct": float(max_dd_pct),
        "peak_equity": float(peak_at_max),
        "trough_equity": float(trough_at_max),
    }


def expectancy(
    pnls: Sequence[float],
    *,
    winrate: Optional[float] = None,
) -> float:
    """Classic expectancy per trade.

    If winrate is not provided, it is computed from pnls (pnl>0 => win).
    """
    if not pnls:
        return 0.0

    wins = [float(p) for p in pnls if float(p) > 0]
    losses = [float(p) for p in pnls if float(p) < 0]

    if winrate is None:
        winrate = len(wins) / len(pnls)

    avg_win = (sum(wins) / len(wins)) if wins else 0.0
    avg_loss = (sum(losses) / len(losses)) if losses else 0.0  # negative

    # E = P(win)*AvgWin + P(loss)*AvgLoss
    return float(winrate) * avg_win + (1.0 - float(winrate)) * avg_loss


def profit_factor(pnls: Sequence[float]) -> float:
    """Gross profit / gross loss (absolute)."""
    wins = sum(float(p) for p in pnls if float(p) > 0)
    losses = -sum(float(p) for p in pnls if float(p) < 0)
    if losses <= 0:
        return float("inf") if wins > 0 else 0.0
    return wins / losses


def basic_trade_stats(pnls: Sequence[float]) -> Dict[str, float]:
    """Convenience stats from PnLs list."""
    n = len(pnls)
    if n == 0:
        return {
            "trades": 0.0,
            "wins": 0.0,
            "losses": 0.0,
            "winrate": 0.0,
            "total_pnl": 0.0,
            "profit_factor": 0.0,
            "expectancy": 0.0,
        }
    wins = sum(1 for p in pnls if float(p) > 0)
    losses = sum(1 for p in pnls if float(p) < 0)
    winrate = wins / n
    total = sum(float(p) for p in pnls)
    pf = profit_factor(pnls)
    exp = expectancy(pnls, winrate=winrate)
    return {
        "trades": float(n),
        "wins": float(wins),
        "losses": float(losses),
        "winrate": float(winrate),
        "total_pnl": float(total),
        "profit_factor": float(pf),
        "expectancy": float(exp),
    }
