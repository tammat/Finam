# finam_bot/backtest/run.py
from __future__ import annotations
from finam_bot.backtest.metrics import basic_trade_stats, compute_drawdown  # compute_drawdown можно и не использовать напрямую

import argparse
import csv
import logging
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Optional, Sequence, Tuple, List, Any
from finam_bot.backtest.metrics import compute_summary
from finam_bot.backtest.engine import BacktestEngine
from finam_bot.backtest.models import Candle
from finam_bot.backtest.synthetic import generate_synthetic_candles, generate_synthetic_orderflow
from finam_bot.strategies.order_flow_pullback import OrderFlowPullbackStrategy

logger = logging.getLogger("backtest.run")


# Exit codes (удобно для CI)
EXIT_OK = 0
EXIT_DATA_ERROR = 2
EXIT_ENGINE_ERROR = 3
EXIT_METRICS_ERROR = 4

try:
    from finam_bot.backtest.metrics import basic_trade_stats
except Exception:
    basic_trade_stats = None

def _print_summary(broker, equity_curve=None):
    if basic_trade_stats is None:
        print(f"equity={broker.equity:.2f} cash={broker.cash:.2f} trades={len(getattr(broker, 'trades', []))}")
        print("metrics: unavailable (basic_trade_stats import failed)")
        return 0
def _parse_float(x: Any, default: float = 0.0) -> float:
    try:
        return float(x)
    except Exception:
        return default


def load_csv_candles(path: str, limit: int = 0) -> List[Candle]:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(path)

    out: List[Candle] = []
    with p.open("r", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for i, row in enumerate(r):
            if limit and i >= limit:
                break

            # максимально терпимо к разным заголовкам
            ts = row.get("ts") or row.get("time") or row.get("timestamp") or row.get("date")
            try:
                ts_int = int(float(ts)) if ts is not None else None
            except Exception:
                ts_int = None

            o = row.get("open") or row.get("o")
            h = row.get("high") or row.get("h")
            l = row.get("low") or row.get("l")
            c = row.get("close") or row.get("c")
            v = row.get("volume") or row.get("v") or 0.0

            out.append(
                Candle(
                    ts=ts_int,
                    open=_parse_float(o),
                    high=_parse_float(h),
                    low=_parse_float(l),
                    close=_parse_float(c),
                    volume=_parse_float(v),
                )
            )
    return out


def load_candles_auto(args) -> Tuple[str, List[Candle]]:
    # STRICT: требуем CSV и успешную загрузку
    if getattr(args, "strict", False):
        logger.info("STRICT mode enabled")
        if not args.csv:
            raise ValueError("--strict requires --csv")
        candles = load_csv_candles(args.csv, limit=int(args.limit or 0))
        if not candles:
            raise ValueError(f"CSV loaded but empty: {args.csv}")
        return "csv", candles

    # NON-STRICT: csv -> fallback -> synthetic
    if args.csv:
        try:
            candles = load_csv_candles(args.csv, limit=int(args.limit or 0))
            if candles:
                return "csv", candles
            logger.warning("CSV loaded but empty (%s). Fallback to synthetic.", args.csv)
        except Exception as e:
            logger.warning("CSV load failed (%s). Fallback to synthetic.", e)

    candles = generate_synthetic_candles(
        n=int(args.n),
        start_price=float(args.start),
        mode=str(args.mode),
        seed=int(args.seed),
    )
    return "synthetic", candles


def _extract_pnls(trades: Sequence[Any]) -> List[float]:
    pnls: List[float] = []
    for t in trades:
        if isinstance(t, dict):
            pnls.append(_parse_float(t.get("pnl", 0.0)))
        else:
            pnls.append(_parse_float(getattr(t, "pnl", 0.0)))
    return pnls

def _print_summary(broker, equity_curve: Optional[Sequence[float]] = None) -> int:
    """
    Печатает статистику.
    Возвращает:
      0 — всё ок (даже если метрики недоступны, мы не падаем)
      4 — метрики упали/недоступны (но вывод equity/trades всё равно печатаем)
    """
    trades = getattr(broker, "trades", []) or []
    eq = float(getattr(broker, "equity", 0.0) or 0.0)
    cash = float(getattr(broker, "cash", eq) or eq)

    # Базовый вывод — всегда
    print(f"equity={eq:.2f} cash={cash:.2f} trades={len(trades)}")

    # Дефолтные ключи — чтобы никогда не падать по KeyError
    s: dict[str, float] = {
        "trades": float(len(trades)),
        "wins": 0.0,
        "losses": 0.0,
        "winrate": 0.0,
        "profit_factor": 0.0,
        "expectancy": 0.0,
        "total_pnl": 0.0,
        "fees": 0.0,
        "avg_win": 0.0,
        "avg_loss": 0.0,
        "payoff": 0.0,
        "max_drawdown_pct": 0.0,
        "sharpe": 0.0,
        "sortino": 0.0,
        "max_win_streak": 0.0,
        "max_loss_streak": 0.0,
    }

    metrics_failed = False

    # ---- trade stats ----
    try:
        from dataclasses import asdict, is_dataclass
        from finam_bot.backtest.metrics import basic_trade_stats

        res = basic_trade_stats(trades, equity_curve=equity_curve)

        if is_dataclass(res):
            res = asdict(res)

        if isinstance(res, dict):
            for k, v in res.items():
                try:
                    s[k] = float(v)
                except Exception:
                    pass
        else:
            metrics_failed = True
    except Exception:
        metrics_failed = True

    # ---- equity stats: DD / Sharpe / Sortino ----
    try:
        if equity_curve:
            from finam_bot.backtest.metrics import compute_drawdown, compute_sharpe_sortino

            dd = compute_drawdown(list(equity_curve))
            sr = compute_sharpe_sortino(list(equity_curve))

            if isinstance(dd, dict):
                s["max_drawdown_pct"] = float(dd.get("max_drawdown_pct", 0.0) or 0.0)
            else:
                s["max_drawdown_pct"] = float(dd or 0.0)

            if isinstance(sr, dict):
                s["sharpe"] = float(sr.get("sharpe", 0.0) or 0.0)
                s["sortino"] = float(sr.get("sortino", 0.0) or 0.0)
    except Exception:
        metrics_failed = True

    # ---- печать метрик (всё безопасно через get) ----
    wins = int(s.get("wins", 0.0))
    losses = int(s.get("losses", 0.0))
    winrate = float(s.get("winrate", 0.0))
    pf = float(s.get("profit_factor", 0.0))

    expectancy = float(s.get("expectancy", 0.0))
    total_pnl = float(s.get("total_pnl", 0.0))
    fees = float(s.get("fees", 0.0))

    avg_win = float(s.get("avg_win", 0.0))
    avg_loss = float(s.get("avg_loss", 0.0))
    payoff = float(s.get("payoff", 0.0))

    max_dd_pct = float(s.get("max_drawdown_pct", 0.0))
    sharpe = float(s.get("sharpe", 0.0))
    sortino = float(s.get("sortino", 0.0))

    max_win_streak = int(s.get("max_win_streak", 0.0))
    max_loss_streak = int(s.get("max_loss_streak", 0.0))

    print(f"wins={wins} losses={losses} winrate={winrate*100:.2f}% profit_factor={pf:.2f}")
    print(f"expectancy={expectancy:.4f} total_pnl={total_pnl:.2f} fees={fees:.2f}")
    print(f"avg_win={avg_win:.2f} avg_loss={avg_loss:.2f} payoff={payoff:.2f}")
    print(f"maxDD={max_dd_pct*100:.2f}% sharpe={sharpe:.2f} sortino={sortino:.2f}")
    print(f"streaks: win={max_win_streak} loss={max_loss_streak}")

    return 4 if metrics_failed else 0


def main(argv: Optional[list[str]] = None) -> int:
    p = argparse.ArgumentParser("finam_bot.backtest.run")

    # data source
    p.add_argument("--csv", type=str, default=None, help="Path to CSV with OHLCV (fallback to synthetic)")
    p.add_argument("--limit", type=int, default=0, help="Limit CSV rows (0 = no limit)")
    p.add_argument("--tf", type=str, default="1m", help="Timeframe label (for logs only)")

    # synthetic params
    p.add_argument("--n", type=int, default=500, help="Synthetic candles count")
    p.add_argument("--start", type=float, default=100.0, help="Synthetic start price")
    p.add_argument("--mode", type=str, default="mixed", help='Synthetic mode: "up"|"down"|"flat"|"mixed"')
    p.add_argument("--seed", type=int, default=42, help="Synthetic seed")
    p.add_argument("--with-orderflow", action="store_true", help="Use synthetic orderflow")

    # engine params
    p.add_argument("--symbol", type=str, default="TEST")
    p.add_argument("--equity", type=float, default=100_000.0)
    p.add_argument("--commission", type=float, default=0.0004)
    p.add_argument("--leverage", type=float, default=2.0)
    p.add_argument("--atr-period", type=int, default=14)
    p.add_argument("--atr-floor", type=float, default=0.01)
    p.add_argument("--fill", type=str, default="worst", help='fill_policy: "worst"|"best"')

    # logging
    p.add_argument("--log", type=str, default="WARNING", help="DEBUG|INFO|WARNING|ERROR")
    p.add_argument(
        "--strict",
        action="store_true",
        help="Disable fallbacks: require valid --csv, fail on any load error/empty data",
    )
    args = p.parse_args(argv)

    level = getattr(logging, str(args.log).upper(), logging.WARNING)
    logging.basicConfig(level=level)
    logger.setLevel(level)

    try:
        # ---- DATA LOAD ----
        try:
            source, candles = load_candles_auto(args)
            logger.warning("Loaded candles source=%s bars=%d", source, len(candles))
        except Exception as e:
            logger.error("Data loading failed: %s", e)
            return EXIT_DATA_ERROR

        # ---- ENGINE ----
        strategy = OrderFlowPullbackStrategy(verbose=False)

        engine = BacktestEngine(
            symbol=str(args.symbol),
            strategy=strategy,
            start_equity=float(args.equity),
            commission_rate=float(args.commission),
            max_leverage=float(args.leverage),
            atr_period=int(args.atr_period),
            fill_policy=str(args.fill),
        )

        # ---- ORDERFLOW ----
        of_list = None
        if args.with_orderflow:
            try:
                of_list = generate_synthetic_orderflow(
                    n=len(candles),
                    seed=int(args.seed),
                )
            except Exception as e:
                logger.error("Orderflow generation failed: %s", e)
                return EXIT_ENGINE_ERROR

        # ---- RUN BACKTEST ----
        try:
            broker = engine.run(
                candles,
                orderflow=of_list,
                atr_floor=float(args.atr_floor),
            )
        except Exception as e:
            logger.error("Engine run failed: %s", e)
            return EXIT_ENGINE_ERROR

        # ---- SUMMARY ----
        eq_curve = getattr(engine, "equity_curve", None)
        return _print_summary(broker, eq_curve)

    except Exception as e:
        logger.exception("Backtest runner crashed unexpectedly: %s", e)
        return EXIT_ENGINE_ERROR


if __name__ == "__main__":
    raise SystemExit(main())