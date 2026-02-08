# /Users/alex/finam/finam_bot/backtest/metrics.py
from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional, Sequence
import math


def _to_float(x: Any, default: float = 0.0) -> float:
    try:
        if x is None:
            return default
        return float(x)
    except Exception:
        return default


def _get(obj: Any, name: str, default: Any = None) -> Any:
    """Safe getattr/dict-get."""
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


def _extract_pnls(trades: Sequence[Any]) -> List[float]:
    pnls: List[float] = []
    for t in trades or []:
        pnl = _get(t, "pnl", None)
        if pnl is None:
            pnl = _get(t, "realized_pnl", None)
        pnls.append(_to_float(pnl, 0.0))
    return pnls


def _extract_fees(trades: Sequence[Any]) -> float:
    total = 0.0
    for t in trades or []:
        fee = _get(t, "fees", None)
        if fee is None:
            fee = _get(t, "fee", None)
        total += _to_float(fee, 0.0)
    return total


def compute_winrate(pnls: Sequence[float]) -> float:
    pnls = list(pnls or [])
    if not pnls:
        return 0.0
    wins = sum(1 for x in pnls if x > 0)
    return wins / len(pnls)


def compute_profit_factor(pnls: Sequence[float]) -> float:
    pnls = list(pnls or [])
    if not pnls:
        return 0.0
    gross_profit = sum(x for x in pnls if x > 0)
    gross_loss = -sum(x for x in pnls if x < 0)  # positive number
    if gross_loss <= 0:
        return float("inf") if gross_profit > 0 else 0.0
    return gross_profit / gross_loss


def compute_expectancy(pnls: Sequence[float]) -> float:
    pnls = list(pnls or [])
    if not pnls:
        return 0.0
    return sum(pnls) / len(pnls)


def compute_drawdown(equity_curve: Sequence[float]) -> Dict[str, float]:
    """
    Drawdown stats:
      max_drawdown: absolute (money)
      max_drawdown_pct: fraction (0.123 = 12.3%)
      peak_equity / trough_equity: values at max DD
    """
    eq = [float(x) for x in (equity_curve or []) if x is not None]
    if not eq:
        return {
            "max_drawdown": 0.0,
            "max_drawdown_pct": 0.0,
            "peak_equity": 0.0,
            "trough_equity": 0.0,
        }

    peak = eq[0]
    max_dd = 0.0
    max_dd_pct = 0.0
    peak_at_max = peak
    trough_at_max = peak

    for x in eq:
        if x > peak:
            peak = x
        dd = peak - x
        dd_pct = (dd / peak) if peak > 0 else 0.0
        if dd > max_dd:
            max_dd = dd
            max_dd_pct = dd_pct
            peak_at_max = peak
            trough_at_max = x

    return {
        "max_drawdown": float(max_dd),
        "max_drawdown_pct": float(max_dd_pct),
        "peak_equity": float(peak_at_max),
        "trough_equity": float(trough_at_max),
    }


def _returns_from_equity(equity_curve: Sequence[float]) -> List[float]:
    eq = [float(x) for x in (equity_curve or []) if x is not None]
    if len(eq) < 2:
        return []
    rets: List[float] = []
    prev = eq[0]
    for x in eq[1:]:
        if prev != 0:
            rets.append((x - prev) / prev)
        else:
            rets.append(0.0)
        prev = x
    return rets


def compute_sharpe_sortino(
    equity_curve: Sequence[float],
    *,
    rf: float = 0.0,
    annualization: float = 1.0,
) -> Dict[str, float]:
    """
    Sharpe/Sortino on *returns* of equity curve.
    annualization: sqrt(N) multiplier. Если таймфрейм неизвестен — оставь 1.0.
    """
    rets = _returns_from_equity(equity_curve)
    if not rets:
        return {"sharpe": 0.0, "sortino": 0.0}

    # excess returns
    ex = [r - rf for r in rets]

    mean = sum(ex) / len(ex)

    # std
    var = sum((r - mean) ** 2 for r in ex) / max(1, (len(ex) - 1))
    std = math.sqrt(var) if var > 0 else 0.0
    sharpe = (mean / std) * math.sqrt(annualization) if std > 0 else 0.0

    # downside std
    downs = [r for r in ex if r < 0]
    if not downs:
        sortino = float("inf") if mean > 0 else 0.0
    else:
        d_mean = sum(downs) / len(downs)
        d_var = sum((r - d_mean) ** 2 for r in downs) / max(1, (len(downs) - 1))
        d_std = math.sqrt(d_var) if d_var > 0 else 0.0
        sortino = (mean / d_std) * math.sqrt(annualization) if d_std > 0 else 0.0

    # не печатаем inf в консоль как есть — чтобы “не пугать”
    if sortino == float("inf"):
        sortino = 0.0

    return {"sharpe": float(sharpe), "sortino": float(sortino)}


def _max_streak(values: Sequence[float], predicate) -> int:
    best = 0
    cur = 0
    for v in values:
        if predicate(v):
            cur += 1
            best = max(best, cur)
        else:
            cur = 0
    return best


def basic_trade_stats(
    trades_or_pnls: Sequence[Any],
    *,
    equity_curve: Optional[Sequence[float]] = None,
) -> Dict[str, float]:
    """
    Универсальная статистика:
    - можно передать список трейдов (с .pnl/.fees)
    - или список pnl (floats)
    Возвращает dict с гарантированными ключами (под cli.py).
    """
    # detect trades vs pnls
    pnls: List[float]
    fees: float
    if trades_or_pnls and not isinstance(trades_or_pnls[0], (int, float)):
        trades = list(trades_or_pnls or [])
        pnls = _extract_pnls(trades)
        fees = _extract_fees(trades)
    else:
        pnls = [float(x) for x in (trades_or_pnls or [])]
        fees = 0.0

    n = len(pnls)
    wins = sum(1 for x in pnls if x > 0)
    losses = sum(1 for x in pnls if x < 0)

    gross_profit = sum(x for x in pnls if x > 0)
    gross_loss = -sum(x for x in pnls if x < 0)
    profit_factor = compute_profit_factor(pnls)
    winrate = compute_winrate(pnls)
    expectancy = compute_expectancy(pnls)
    total_pnl = sum(pnls)

    avg_win = (gross_profit / wins) if wins > 0 else 0.0

    # средний лосс в "модуле" (положительное число)
    avg_loss_mag = (gross_loss / losses) if losses > 0 else 0.0

    # для вывода хотим отрицательное число
    avg_loss_signed = -avg_loss_mag if avg_loss_mag > 0 else 0.0

    # payoff считаем по модулю среднего лосса
    payoff = (avg_win / avg_loss_mag) if avg_loss_mag > 0 else 0.0
    max_win_streak = _max_streak(pnls, lambda x: x > 0)
    max_loss_streak = _max_streak(pnls, lambda x: x < 0)

    dd = compute_drawdown(equity_curve or [])
    sr = compute_sharpe_sortino(equity_curve or [])

    # гарантируем все ключи для cli.py
    return {
        "trades": float(n),
        "wins": float(wins),
        "losses": float(losses),
        "winrate": float(winrate),
        "profit_factor": float(0.0 if profit_factor == float("inf") else profit_factor),
        "expectancy": float(expectancy),
        "total_pnl": float(total_pnl),
        "fees": float(fees),
        "avg_win": float(avg_win),
        "avg_loss": float(avg_loss_signed),  # отрицательное число
        "payoff": float(payoff),
        "max_drawdown_pct": float(dd.get("max_drawdown_pct", 0.0)),
        "sharpe": float(sr.get("sharpe", 0.0)),
        "sortino": float(sr.get("sortino", 0.0)),
        "max_win_streak": float(max_win_streak),
        "max_loss_streak": float(max_loss_streak),
    }
def compute_summary(
    trades_or_pnls: Sequence[Any],
    *,
    equity_curve: Optional[Sequence[float]] = None,
) -> Dict[str, float]:
    """
    Алиас для совместимости с cli.py и будущими версиями.
    Всегда возвращает dict с ключами, которые ожидает cli.py.
    """
    return basic_trade_stats(trades_or_pnls, equity_curve=equity_curve)