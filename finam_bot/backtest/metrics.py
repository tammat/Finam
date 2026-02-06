# finam_bot/backtest/metrics.py
from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import Any, Iterable, Mapping, Sequence


def _get(obj: Any, name: str, default: Any = None) -> Any:
    """Безопасно достать поле из dataclass/объекта/словаря."""
    if obj is None:
        return default
    if isinstance(obj, Mapping):
        return obj.get(name, default)
    if hasattr(obj, name):
        return getattr(obj, name)
    return default


def compute_drawdown(equity_curve: Sequence[float]) -> dict[str, float]:
    """
    Максимальная просадка по equity_curve.
    Возвращает:
      - max_drawdown_pct: float (0..1)
      - max_drawdown_amount: float (>=0)
    """
    eq = list(equity_curve or [])
    if not eq:
        return {"max_drawdown_pct": 0.0, "max_drawdown_amount": 0.0}

    peak = eq[0]
    max_dd_amt = 0.0
    max_dd_pct = 0.0

    for x in eq:
        if x > peak:
            peak = x
        dd_amt = peak - x
        if dd_amt > max_dd_amt:
            max_dd_amt = dd_amt
            if peak > 0:
                max_dd_pct = dd_amt / peak
            else:
                max_dd_pct = 0.0

    return {"max_drawdown_pct": float(max_dd_pct), "max_drawdown_amount": float(max_dd_amt)}


def expectancy(trades: Sequence[Any]) -> dict[str, float]:
    """
    Expectancy (матожидание) на одну сделку.
    Используем net_pnl = pnl - fees (если fees есть).
    Возвращает:
      - expectancy_per_trade
      - avg_win
      - avg_loss (модуль, >=0)
      - winrate (0..1)
      - profit_factor
      - total_pnl
    """
    ts = list(trades or [])
    if not ts:
        return {
            "expectancy_per_trade": 0.0,
            "avg_win": 0.0,
            "avg_loss": 0.0,
            "winrate": 0.0,
            "profit_factor": 0.0,
            "total_pnl": 0.0,
        }

    net_pnls: list[float] = []
    wins: list[float] = []
    losses: list[float] = []

    for t in ts:
        pnl = float(_get(t, "pnl", 0.0) or 0.0)
        fees = float(_get(t, "fees", 0.0) or 0.0)
        net = pnl - fees
        net_pnls.append(net)
        if net > 0:
            wins.append(net)
        elif net < 0:
            losses.append(net)

    total = float(sum(net_pnls))
    n = len(net_pnls)
    winrate = (len(wins) / n) if n else 0.0
    avg_win = float(sum(wins) / len(wins)) if wins else 0.0
    avg_loss = float(abs(sum(losses) / len(losses))) if losses else 0.0

    gross_profit = float(sum(wins))
    gross_loss = float(abs(sum(losses)))
    profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else (float("inf") if gross_profit > 0 else 0.0)

    exp_per_trade = float(total / n) if n else 0.0

    return {
        "expectancy_per_trade": exp_per_trade,
        "avg_win": avg_win,
        "avg_loss": avg_loss,
        "winrate": float(winrate),
        "profit_factor": float(profit_factor) if profit_factor != float("inf") else float("inf"),
        "total_pnl": total,
    }


def summarize_trades(trades: Sequence[Any]) -> dict[str, float]:
    """Короткая сводка по сделкам (без equity)."""
    ts = list(trades or [])
    exp = expectancy(ts)

    count = len(ts)
    wins = 0
    losses = 0
    for t in ts:
        pnl = float(_get(t, "pnl", 0.0) or 0.0) - float(_get(t, "fees", 0.0) or 0.0)
        if pnl > 0:
            wins += 1
        elif pnl < 0:
            losses += 1

    winrate = (wins / count) if count else 0.0

    return {
        "trades": float(count),
        "wins": float(wins),
        "losses": float(losses),
        "winrate": float(winrate),
        "profit_factor": float(exp["profit_factor"]),
        "expectancy": float(exp["expectancy_per_trade"]),
        "total_pnl": float(exp["total_pnl"]),
    }


def compute_backtest_metrics(
    *,
    trades: Sequence[Any],
    equity_curve: Sequence[float] | None = None,
) -> dict[str, float]:
    """
    Универсальный набор метрик:
      - trades/winrate/profit_factor/expectancy/total_pnl
      - max_drawdown_pct/max_drawdown_amount (если equity_curve задана)
    """
    out = summarize_trades(trades)

    if equity_curve is not None:
        dd = compute_drawdown(equity_curve)
        out.update(dd)
    else:
        out.update({"max_drawdown_pct": 0.0, "max_drawdown_amount": 0.0})

    return out
