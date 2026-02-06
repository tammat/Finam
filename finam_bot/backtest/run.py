# finam_bot/backtest/run.py
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import Optional, Sequence

from finam_bot.backtest.engine import BacktestEngine
from finam_bot.backtest.models import Candle
from finam_bot.backtest.synthetic import generate_synthetic_candles

from finam_bot.strategies.order_flow_pullback import OrderFlowPullbackStrategy


logger = logging.getLogger("backtest.run")


def _safe_float(x, default: float = 0.0) -> float:
    try:
        return float(x)
    except Exception:
        return default


def load_csv_candles_or_fallback(
    csv_path: str,
    *,
    limit: int = 0,
    fallback_n: int = 500,
    fallback_start: float = 100.0,
    fallback_mode: str = "mixed",
    fallback_seed: int = 42,
) -> list[Candle]:
    """
    Никогда не ломает запуск:
    - если CSV нет / не читается / колонки не совпали -> возвращаем synthetic.
    """
    path = Path(csv_path)

    if not path.exists():
        logger.warning("CSV not found: %s -> fallback to synthetic", path)
        return generate_synthetic_candles(
            n=fallback_n,
            start_price=fallback_start,
            mode=fallback_mode,
            seed=fallback_seed,
        )

    try:
        import csv

        candles: list[Candle] = []
        with path.open("r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            if not reader.fieldnames:
                raise ValueError("CSV has no header")

            # Популярные варианты имён колонок
            # open/high/low/close; ts|time|timestamp; volume|vol
            def pick(row: dict, *keys: str, default=None):
                for k in keys:
                    if k in row and row[k] not in (None, ""):
                        return row[k]
                return default

            for i, row in enumerate(reader):
                if limit and len(candles) >= limit:
                    break

                o = pick(row, "open", "Open", "OPEN")
                h = pick(row, "high", "High", "HIGH")
                l = pick(row, "low", "Low", "LOW")
                c = pick(row, "close", "Close", "CLOSE")
                v = pick(row, "volume", "Volume", "VOL", "vol", default=0.0)
                ts = pick(row, "ts", "time", "timestamp", "datetime", "Date", "DATE", default=i + 1)

                if o is None or h is None or l is None or c is None:
                    # если формат неизвестен — ломаться не будем, просто fallback
                    raise ValueError(
                        f"CSV columns mismatch. Need OHLC columns. Got fields={reader.fieldnames}"
                    )

                candles.append(
                    Candle(
                        ts=int(_safe_float(ts, i + 1)),
                        open=_safe_float(o),
                        high=_safe_float(h),
                        low=_safe_float(l),
                        close=_safe_float(c),
                        volume=_safe_float(v, 0.0),
                    )
                )

        if not candles:
            raise ValueError("CSV parsed but produced 0 candles")

        return candles

    except Exception as e:
        logger.warning("CSV load failed (%s) -> fallback to synthetic", e)
        return generate_synthetic_candles(
            n=fallback_n,
            start_price=fallback_start,
            mode=fallback_mode,
            seed=fallback_seed,
        )


def _print_summary(broker, equity_curve: Optional[Sequence[float]] = None) -> None:
    print(f"equity={broker.equity} cash={getattr(broker, 'cash', broker.equity)} trades={len(broker.trades)}")

    # Если есть metrics.py — попробуем красиво посчитать (но не требуем)
    try:
        from finam_bot.backtest.metrics import summarize_trades, compute_drawdown

        if broker.trades:
            s = summarize_trades(broker.trades)
            # summarize_trades может вернуть dict или dataclass — обработаем оба
            if isinstance(s, dict):
                wins = s.get("wins")
                losses = s.get("losses")
                winrate = s.get("winrate")
                pf = s.get("profit_factor")
                total = s.get("total_pnl")
            else:
                wins = getattr(s, "wins", None)
                losses = getattr(s, "losses", None)
                winrate = getattr(s, "winrate", None)
                pf = getattr(s, "profit_factor", None)
                total = getattr(s, "total_pnl", None)

            if wins is not None and losses is not None:
                print(f"wins={wins} losses={losses} winrate={winrate:.2f}% profit_factor={pf:.2f}")
            if total is not None:
                print(f"total_pnl={total:.2f}")

        if equity_curve:
            dd = compute_drawdown(list(equity_curve))
            # dd тоже может быть dict/float
            if isinstance(dd, dict):
                print(f"max_drawdown={dd.get('max_drawdown')}")
            else:
                print(f"max_drawdown={dd}")

    except Exception:
        # никаких падений из-за метрик
        pass


def main(argv: Optional[list[str]] = None) -> int:
    p = argparse.ArgumentParser("finam_bot.backtest.run")

    # data source
    p.add_argument("--csv", type=str, default=None, help="Path to CSV with OHLCV (auto-fallback to synthetic)")
    p.add_argument("--limit", type=int, default=0, help="Limit CSV rows (0 = no limit)")
    p.add_argument("--tf", type=str, default="1m", help="Timeframe label (for logs only)")

    # synthetic params
    p.add_argument("--n", type=int, default=500, help="Synthetic candles count")
    p.add_argument("--start", type=float, default=100.0, help="Synthetic start price")
    p.add_argument("--mode", type=str, default="mixed", help='Synthetic mode: "up"|"down"|"flat"|"mixed"')
    p.add_argument("--seed", type=int, default=42, help="Synthetic seed")
    p.add_argument("--with-orderflow", action="store_true", help="Use synthetic orderflow if engine supports it")

    # engine params
    p.add_argument("--symbol", type=str, default="TEST")
    p.add_argument("--equity", type=float, default=100_000.0)
    p.add_argument("--commission", type=float, default=0.0004)
    p.add_argument("--leverage", type=float, default=2.0)
    p.add_argument("--atr-period", type=int, default=14)
    p.add_argument("--atr-floor", type=float, default=0.01)
    p.add_argument("--fill", type=str, default="worst", help='fill_policy: "worst"|"best"')

    # logging
    p.add_argument("--log", type=str, default="WARNING", help="Logging level: DEBUG|INFO|WARNING|ERROR")

    args = p.parse_args(argv)

    level = getattr(logging, str(args.log).upper(), logging.WARNING)
    logging.basicConfig(level=level)
    logger.setLevel(level)

    try:
        strategy = OrderFlowPullbackStrategy(verbose=False)
    except TypeError:
        # если сигнатура у стратегии без verbose
        strategy = OrderFlowPullbackStrategy()

    engine = BacktestEngine(
        symbol=args.symbol,
        strategy=strategy,
        start_equity=args.equity,
        commission_rate=args.commission,
        max_leverage=args.leverage,
        atr_period=args.atr_period,
        fill_policy=args.fill,
    )

    # --- choose data source (NEVER FAIL) ---
    if args.csv:
        candles = load_csv_candles_or_fallback(
            args.csv,
            limit=args.limit,
            fallback_n=args.n,
            fallback_start=args.start,
            fallback_mode=args.mode,
            fallback_seed=args.seed,
        )
        broker = engine.run(candles, atr_floor=args.atr_floor)
        eq_curve = getattr(engine, "equity_curve", [broker.equity])
        _print_summary(broker, eq_curve)
        return 0

    # no csv -> synthetic
    # если у engine есть run_synthetic — используем его
    if hasattr(engine, "run_synthetic"):
        try:
            broker = engine.run_synthetic(
                n=args.n,
                start_price=args.start,
                mode=args.mode,
                seed=args.seed,
                with_orderflow=bool(args.with_orderflow),
                atr_floor=args.atr_floor,
            )
            eq_curve = getattr(engine, "equity_curve", [broker.equity])
            _print_summary(broker, eq_curve)
            return 0
        except Exception as e:
            logger.warning("run_synthetic failed (%s) -> fallback to engine.run(synthetic candles)", e)

    candles = generate_synthetic_candles(
        n=args.n,
        start_price=args.start,
        mode=args.mode,
        seed=args.seed,
    )
    broker = engine.run(candles, atr_floor=args.atr_floor)
    eq_curve = getattr(engine, "equity_curve", [broker.equity])
    _print_summary(broker, eq_curve)
    return 0


if __name__ == "__main__":
    # Никогда не падаем “наружу”
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception as e:
        logging.basicConfig(level=logging.WARNING)
        logger.exception("Backtest runner crashed unexpectedly: %s", e)
        raise SystemExit(0)
