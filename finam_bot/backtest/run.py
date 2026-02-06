# finam_bot/backtest/run.py
from __future__ import annotations

import argparse
import csv
import logging
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Optional, Sequence, Tuple, List, Any

from finam_bot.backtest.engine import BacktestEngine
from finam_bot.backtest.models import Candle
from finam_bot.backtest.synthetic import generate_synthetic_candles, generate_synthetic_orderflow
from finam_bot.strategies.order_flow_pullback import OrderFlowPullbackStrategy

logger = logging.getLogger("backtest.run")


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
    # 1) если есть csv и файл существует → грузим csv
    if args.csv:
        try:
            candles = load_csv_candles(args.csv, limit=int(args.limit or 0))
            if candles:
                return "csv", candles
        except Exception as e:
            logger.warning("CSV load failed (%s). Fallback to synthetic.", e)

    # 2) иначе synthetic
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


def _print_summary(broker, equity_curve: Optional[Sequence[float]] = None) -> None:
    print(
        f"equity={broker.equity} cash={getattr(broker, 'cash', broker.equity)} trades={len(broker.trades)}"
    )

    # Метрики — безопасно, без падений
    pnls = _extract_pnls(getattr(broker, "trades", []))

    # 1) trade stats
    try:
        from finam_bot.backtest.metrics import basic_trade_stats  # ожидаем что есть

        s = basic_trade_stats(pnls)
        if is_dataclass(s):
            s = asdict(s)

        wins = s.get("wins", 0)
        losses = s.get("losses", 0)
        winrate = s.get("winrate", 0.0)
        pf = s.get("profit_factor", 0.0)
        expectancy = s.get("expectancy", 0.0)
        total = s.get("total_pnl", 0.0)
        print(f"wins={wins} losses={losses} winrate={winrate*100:.2f}% profit_factor={pf:.2f}")
        print(f"expectancy={expectancy:.4f} total_pnl={total:.2f}")

    except Exception as e:
        logger.debug("metrics.basic_trade_stats unavailable: %s", e)

    # 2) drawdown
    try:
        from finam_bot.backtest.metrics import compute_drawdown

        if equity_curve:
            dd = compute_drawdown(list(equity_curve))
            if isinstance(dd, dict):
                print(f"maxDD={dd.get('max_drawdown_pct', 0.0) * 100:.2f}%")
            else:
                # если вдруг вернули float
                print(f"maxDD={float(dd) * 100:.2f}%")
    except Exception as e:
        logger.debug("metrics.compute_drawdown unavailable: %s", e)


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

    args = p.parse_args(argv)

    level = getattr(logging, str(args.log).upper(), logging.WARNING)
    logging.basicConfig(level=level)
    logger.setLevel(level)

    try:
        source, candles = load_candles_auto(args)
        logger.warning("Loaded candles source=%s bars=%d", source, len(candles))

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

        of_list = None
        if args.with_orderflow:
            of_list = generate_synthetic_orderflow(
                n=len(candles),
                seed=int(args.seed),
            )

        broker = engine.run(
            candles,
            orderflow=of_list,
            atr_floor=float(args.atr_floor),
        )

        eq_curve = getattr(engine, "equity_curve", None)
        _print_summary(broker, eq_curve)

        return 0

    except Exception as e:
        logger.exception("Backtest runner crashed unexpectedly: %s", e)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
