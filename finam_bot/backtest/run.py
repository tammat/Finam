# finam_bot/backtest/run.py
from __future__ import annotations

import argparse
import csv
import logging
from pathlib import Path
from typing import Optional, Sequence

from finam_bot.backtest.engine import BacktestEngine
from finam_bot.backtest.models import Candle
from finam_bot.backtest.synthetic import (
    generate_synthetic_candles,
    generate_synthetic_orderflow,
)
from finam_bot.backtest.metrics import compute_backtest_metrics

from finam_bot.strategies.order_flow_pullback import OrderFlowPullbackStrategy


def _parse_log_level(val: str) -> int:
    v = val.strip().upper()
    mapping = {
        "CRITICAL": logging.CRITICAL,
        "ERROR": logging.ERROR,
        "WARNING": logging.WARNING,
        "WARN": logging.WARNING,
        "INFO": logging.INFO,
        "DEBUG": logging.DEBUG,
    }
    if v.isdigit():
        return int(v)
    return mapping.get(v, logging.WARNING)


def _load_csv_candles(path: str, limit: Optional[int] = None) -> list[Candle]:
    """
    Очень простой CSV loader без pandas.
    Ожидаемые колонки: ts, open, high, low, close, volume (volume опционально).
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"CSV not found: {path}")

    candles: list[Candle] = []
    with p.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # допускаем разные имена колонок (минимальная гибкость)
            def g(*names: str, default: str = "") -> str:
                for n in names:
                    if n in row and row[n] not in (None, ""):
                        return row[n]
                return default

            ts_s = g("ts", "time", "timestamp", default="")
            ts = int(float(ts_s)) if ts_s else None

            o = float(g("open", "o"))
            h = float(g("high", "h"))
            l = float(g("low", "l"))
            c = float(g("close", "c"))
            v_s = g("volume", "vol", default="0")
            v = float(v_s) if v_s else 0.0

            candles.append(Candle(ts=ts, open=o, high=h, low=l, close=c, volume=v))
            if limit is not None and len(candles) >= limit:
                break

    return candles


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(prog="finam_bot.backtest.run")

    # data source
    ap.add_argument("--csv", type=str, default=None, help="Path to CSV candles")
    ap.add_argument("--limit", type=int, default=None, help="Limit CSV rows")

    # synthetic
    ap.add_argument("--n", type=int, default=500, help="Number of synthetic candles")
    ap.add_argument("--start", type=float, default=100.0, help="Start price for synthetic")
    ap.add_argument("--mode", type=str, default="mixed", help="up|down|flat|mixed (synthetic)")
    ap.add_argument("--seed", type=int, default=42, help="Random seed (synthetic)")
    ap.add_argument("--with-orderflow", action="store_true", help="Attach synthetic orderflow to snapshots")

    # engine params
    ap.add_argument("--symbol", type=str, default="TEST")
    ap.add_argument("--equity", type=float, default=100_000.0)
    ap.add_argument("--commission", type=float, default=0.0004, help="Commission rate, e.g. 0.0004 = 0.04%")
    ap.add_argument("--leverage", type=float, default=1.0)
    ap.add_argument("--atr-period", type=int, default=14)
    ap.add_argument("--atr-floor", type=float, default=0.0, help="Minimum ATR floor to avoid huge sizing")
    ap.add_argument("--fill", type=str, default="worst", help="worst|best (intrabar SL/TP priority)")
    ap.add_argument("--fill-policy", dest="fill", type=str, help="Alias for --fill")
    # logging
    ap.add_argument("--log", type=str, default="WARNING", help="DEBUG|INFO|WARNING|ERROR or numeric level")

    args = ap.parse_args(argv)

    log_level = _parse_log_level(args.log)
    logging.basicConfig(level=log_level, format="%(levelname)s:%(name)s:%(message)s")

    strategy = OrderFlowPullbackStrategy(verbose=False, log_level=log_level)
    engine = BacktestEngine(
        symbol=args.symbol,
        strategy=strategy,
        start_equity=args.equity,
        commission_rate=args.commission,
        max_leverage=args.leverage,
        atr_period=args.atr_period,
        fill_policy=args.fill,
    )

    # candles
    if args.csv:
        candles = _load_csv_candles(args.csv, limit=args.limit)
        broker = engine.run(candles, atr_floor=args.atr_floor)
    else:
        candles = generate_synthetic_candles(
            n=args.n,
            start_price=args.start,
            mode=args.mode,
            seed=args.seed,
        )
        if args.with_orderflow:
            of_list = generate_synthetic_orderflow(
                n=len(candles),
                seed=args.seed,
            )
            broker = engine.run(candles, orderflow=of_list, atr_floor=args.atr_floor)
        else:
            broker = engine.run(candles, atr_floor=args.atr_floor)

    # metrics
    metrics = compute_backtest_metrics(
        trades=broker.trades,
        equity_curve=getattr(engine, "equity_curve", None),
    )

    print(f"equity={broker.equity} cash={broker.cash} trades={len(broker.trades)}")
    print(
        f"wins={int(metrics['wins'])} losses={int(metrics['losses'])} "
        f"winrate={metrics['winrate']*100:.2f}% profit_factor={metrics['profit_factor']:.2f}"
    )
    print(
        f"expectancy={metrics['expectancy']:.4f} "
        f"maxDD={metrics['max_drawdown_pct']*100:.2f}% "
        f"total_pnl={metrics['total_pnl']:.2f}"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
