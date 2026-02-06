# finam_bot/backtest/report.py
from __future__ import annotations

import csv
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any, Iterable, Optional, Sequence


def _to_dict(obj: Any) -> dict:
    if obj is None:
        return {}
    if isinstance(obj, dict):
        return obj
    if is_dataclass(obj):
        return asdict(obj)
    # fallback: берем публичные атрибуты
    d = {}
    for k in dir(obj):
        if k.startswith("_"):
            continue
        try:
            v = getattr(obj, k)
        except Exception:
            continue
        if callable(v):
            continue
        d[k] = v
    return d


def save_equity_curve_csv(equity_curve: Sequence[float], path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["i", "equity"])
        for i, eq in enumerate(equity_curve):
            w.writerow([i, float(eq)])


def save_trades_csv(trades: Iterable[Any], path: str | Path) -> None:
    """
    Пишет trades в CSV максимально устойчиво:
    - dataclass -> asdict
    - dict -> dict
    - object -> attrs
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    rows = []
    keys = set()
    for t in trades:
        d = _to_dict(t)
        rows.append(d)
        keys |= set(d.keys())

    # стабильный порядок колонок
    preferred = ["symbol", "side", "entry_price", "exit_price", "qty", "pnl", "reason", "entry_ts", "exit_ts"]
    rest = [k for k in sorted(keys) if k not in preferred]
    fieldnames = [k for k in preferred if k in keys] + rest

    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for d in rows:
            w.writerow(d)


def top_trades(trades: Sequence[Any], n: int = 10, key: str = "pnl", reverse: bool = True) -> list[Any]:
    """
    Возвращает топ сделок по pnl (или другому полю).
    """
    def get_key(t: Any) -> float:
        d = _to_dict(t)
        v = d.get(key, 0.0)
        try:
            return float(v)
        except Exception:
            return 0.0

    return sorted(list(trades), key=get_key, reverse=reverse)[: max(0, int(n))]
