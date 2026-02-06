# finam_bot/backtest/metrics.py
from __future__ import annotations

from typing import Dict, Sequence


def compute_drawdown(equity_curve: Sequence[float]) -> Dict[str, float]:
    """
    Return drawdown stats for an equity curve.

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
    max_dd = 0.0
    max_dd_pct = 0.0
    peak_at_max = peak
    trough_at_max = peak

    for x in equity_curve:
        eq = float(x)
        if eq > peak:
            peak = eq

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


def compute_winrate(pnls: Sequence[float]) -> float:
    """
    Winrate по сделкам: wins / (wins + losses).
    Нулевые PnL игнорируем.
    Возвращает 0..1
    """
    wins = 0
    losses = 0
    for p in pnls or []:
        p = float(p)
        if p > 0:
            wins += 1
        elif p < 0:
            losses += 1
    total = wins + losses
    return (wins / total) if total > 0 else 0.0


def compute_profit_factor(pnls: Sequence[float]) -> float:
    """
    Profit Factor = sum(profits) / abs(sum(losses))
    """
    gross_profit = 0.0
    gross_loss = 0.0
    for p in pnls or []:
        p = float(p)
        if p > 0:
            gross_profit += p
        elif p < 0:
            gross_loss += p  # отрицательное
    if gross_loss == 0.0:
        return float("inf") if gross_profit > 0 else 0.0
    return gross_profit / abs(gross_loss)


def compute_expectancy(pnls: Sequence[float]) -> float:
    """
    Expectancy = средний PnL на сделку (mean PnL).
    """
    pnls = [float(p) for p in (pnls or [])]
    return (sum(pnls) / len(pnls)) if pnls else 0.0


def basic_trade_stats(pnls: Sequence[float]) -> Dict[str, float]:
    """
    Convenience stats from PnLs list.
    (Оставлено как один агрегатор, чтобы не размазывать логику по run.py)
    """
    n = len(pnls or [])
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
    winrate = compute_winrate(pnls)
    total = sum(float(p) for p in pnls)
    pf = compute_profit_factor(pnls)
    exp = compute_expectancy(pnls)

    return {
        "trades": float(n),
        "wins": float(wins),
        "losses": float(losses),
        "winrate": float(winrate),
        "total_pnl": float(total),
        "profit_factor": float(pf),
        "expectancy": float(exp),
    }


# -----------------------------
# Backward-compatible aliases
# -----------------------------
# Если где-то в коде раньше импортировали expectancy/profit_factor —
# это не сломается.
expectancy = compute_expectancy
profit_factor = compute_profit_factor
# --- Backward compatibility aliases ---
# -----------------------------
# Backward-compatible aliases
# -----------------------------
winrate = compute_winrate
