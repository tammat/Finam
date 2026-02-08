# /Users/alex/finam/finam_bot/backtest/cli.py
from __future__ import annotations

import argparse
import dataclasses
import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from typing import List, Optional, Sequence, Tuple, Any, Dict

from finam_bot.backtest.engine import BacktestEngine
from finam_bot.backtest.models import Candle

logger = logging.getLogger("backtest.run")

EXIT_OK = 0
EXIT_DATA_ERROR = 2
EXIT_METRICS_ERROR = 4
EXIT_RUNTIME_ERROR = 5

FINAM_BASE_DEFAULT = "https://api.finam.ru"


# ---------------------------
# helpers
# ---------------------------
def _iso_to_epoch_seconds(s: str) -> int:
    """
    Parse ISO8601 like '2026-02-01T10:00:00' or '2026-02-01T10:00:00Z' to epoch seconds (UTC).
    If no timezone info is provided, treat as local time.
    """
    if not s:
        raise ValueError("empty datetime")
    # accept trailing Z
    if s.endswith("Z"):
        dt = datetime.fromisoformat(s[:-1]).replace(tzinfo=timezone.utc)
    else:
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            # local -> epoch
            return int(dt.timestamp())
    return int(dt.astimezone(timezone.utc).timestamp())


def _parse_symbols(raw: str) -> List[str]:
    # accepts "A,B,C" or "A B C"
    if not raw:
        return []
    parts = []
    for chunk in raw.replace(",", " ").split():
        chunk = chunk.strip()
        if chunk:
            parts.append(chunk)
    return parts


def _tf_to_finam(tf: str) -> str:
    """
    Finam REST expects enum-like strings for timeFrame.
    We'll accept:
      M1, M5, M15, M30, H1, D1, W1
    and pass TIME_FRAME_<X>.
    If user already passes TIME_FRAME_..., we keep it.
    """
    tf = (tf or "").strip().upper()
    if tf.startswith("TIME_FRAME_"):
        return tf
    mapping = {
        "M1": "TIME_FRAME_M1",
        "M5": "TIME_FRAME_M5",
        "M10": "TIME_FRAME_M10",
        "M15": "TIME_FRAME_M15",
        "M30": "TIME_FRAME_M30",
        "H1": "TIME_FRAME_H1",
        "D1": "TIME_FRAME_D1",
        "W1": "TIME_FRAME_W1",
    }
    if tf not in mapping:
        raise ValueError(f"Unsupported tf={tf}. Use one of: {', '.join(mapping)}")
    return mapping[tf]


def _http_json(method: str, url: str, *, headers: Dict[str, str], body: Optional[dict] = None, timeout: int = 30) -> Any:
    """
    Minimal JSON HTTP client (no external deps).
    Raises ValueError with helpful message if response isn't JSON.
    """
    import urllib.request
    import urllib.error

    data = None
    if body is not None:
        raw = json.dumps(body).encode("utf-8")
        data = raw
        headers = dict(headers)
        headers.setdefault("Content-Type", "application/json; charset=utf-8")

    req = urllib.request.Request(url=url, method=method.upper(), headers=headers, data=data)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            status = getattr(resp, "status", 200)
            raw = resp.read()
            ctype = resp.headers.get("Content-Type", "")
    except urllib.error.HTTPError as e:
        raw = e.read()
        ctype = e.headers.get("Content-Type", "")
        msg = raw[:500].decode("utf-8", errors="replace")
        raise ValueError(f"HTTP {e.code} for {url}. content-type={ctype}. body[0:500]={msg}") from e
    except Exception as e:
        raise ValueError(f"HTTP request failed for {url}: {e}") from e

    txt = raw.decode("utf-8", errors="replace").strip()
    if not txt:
        raise ValueError(f"Empty response for {url} (status={status}, content-type={ctype})")
    try:
        return json.loads(txt)
    except json.JSONDecodeError as e:
        # show snippet to debug HTML/proxy/etc.
        snippet = txt[:500].replace("\n", "\\n")
        raise ValueError(f"Non-JSON response for {url} (status={status}, content-type={ctype}). body[0:500]={snippet}") from e


# ---------------------------
# FINAM REST loader
# ---------------------------
def finam_create_session(*, secret: str, base_url: str = FINAM_BASE_DEFAULT) -> str:
    """
    POST /v1/sessions  { "secret": "<token>" } -> { "token": "<jwt>" }
    """
    url = f"{base_url.rstrip('/')}/v1/sessions"
    data = _http_json("POST", url, headers={"Accept": "application/json"}, body={"secret": secret})
    token = data.get("token") if isinstance(data, dict) else None
    if not token:
        raise ValueError(f"Unexpected sessions response: {data}")
    return str(token)


def load_finam_candles(
    *,
    symbols: Sequence[str],
    tf: str,
    dt_from: str,
    dt_to: str,
    secret: str,
    base_url: str = FINAM_BASE_DEFAULT,
    limit: int = 50000,
) -> List[Candle]:
    """
    Load candles from Finam Trade API (REST).
    Important: symbol format in Finam docs is usually like 'YDEX@MISX' (ticker@mic/board).
    """
    jwt = finam_create_session(secret=secret, base_url=base_url)
    time_frame = _tf_to_finam(tf)
    # REST expects RFC3339 timestamps, keep as ISO; if user gives no TZ, it's treated local by API (usually).
    # We'll validate parseable.
    _ = _iso_to_epoch_seconds(dt_from)
    _ = _iso_to_epoch_seconds(dt_to)

    all_candles: List[Candle] = []
    for sym in symbols:
        # Bars endpoint (market data)
        # Docs: /v1/marketdata/bars?symbol=YDEX@MISX&timeFrame=TIME_FRAME_M1&from=...&to=...
        url = (
            f"{base_url.rstrip('/')}/v1/marketdata/bars"
            f"?symbol={sym}"
            f"&timeFrame={time_frame}"
            f"&from={dt_from}"
            f"&to={dt_to}"
            f"&limit={int(limit)}"
        )
        data = _http_json("GET", url, headers={"Accept": "application/json", "Authorization": f"Bearer {jwt}"})
        items = None
        if isinstance(data, dict):
            # docs typically: {"bars":[...]} or {"candles":[...]} or {"data":[...]}
            for k in ("bars", "candles", "data", "items"):
                if k in data and isinstance(data[k], list):
                    items = data[k]
                    break
        if items is None:
            raise ValueError(f"Unexpected bars response for {sym}: {data}")

        for it in items:
            # common keys in docs: time/open/high/low/close/volume
            ts_raw = it.get("time") or it.get("ts") or it.get("timestamp")
            if not ts_raw:
                continue
            ts = _iso_to_epoch_seconds(str(ts_raw))
            c = Candle(
                ts=ts,
                open=float(it.get("open", 0.0)),
                high=float(it.get("high", 0.0)),
                low=float(it.get("low", 0.0)),
                close=float(it.get("close", 0.0)),
                volume=float(it.get("volume", 0.0) or 0.0),
            )
            all_candles.append(c)

    all_candles.sort(key=lambda x: (x.ts or 0))
    return all_candles


# ---------------------------
# synthetic / csv loader stubs (keep your existing ones)
# ---------------------------
def generate_synthetic_candles(n: int = 200, seed: int = 1, start_price: float = 100.0) -> List[Candle]:
    import random
    r = random.Random(seed)
    price = float(start_price)
    ts0 = int(time.time()) - n * 60
    out: List[Candle] = []
    for i in range(n):
        # random walk
        o = price
        change = r.uniform(-1.0, 1.0)
        c = max(0.01, o + change)
        h = max(o, c) + r.uniform(0.0, 0.3)
        l = min(o, c) - r.uniform(0.0, 0.3)
        v = r.uniform(10, 100)
        out.append(Candle(ts=ts0 + i * 60, open=o, high=h, low=l, close=c, volume=v))
        price = c
    return out


def load_candles_auto(args) -> Tuple[str, List[Candle]]:
    """
    source=auto:
      - if --csv given -> csv loader (not implemented here)
      - else -> synthetic
    source=finam:
      - use FINAM_TOKEN env or --token
    """
    src = (args.source or "auto").lower()
    if src == "synthetic" or (src == "auto" and not args.csv):
        return "synthetic", generate_synthetic_candles(n=args.n, seed=args.seed)

    if src == "csv" or (src == "auto" and args.csv):
        raise ValueError("CSV loader is not implemented yet in this file. Use your existing csv loader or add it.")

    if src == "finam":
        token = args.token or os.getenv("FINAM_TOKEN")
        if not token:
            raise ValueError("Finam token not provided. Use --token or FINAM_TOKEN env var.")
        if args.strict and not args.symbols:
            raise ValueError("--source finam requires --symbols")
        symbols = _parse_symbols(args.symbols or "")
        if not symbols:
            raise ValueError("--source finam requires --symbols (example: SBER@MISX)")
        if not args.dt_from or not args.dt_to:
            raise ValueError("--source finam requires --from and --to ISO timestamps")
        candles = load_finam_candles(
            symbols=symbols,
            tf=args.tf,
            dt_from=args.dt_from,
            dt_to=args.dt_to,
            secret=token,
            base_url=args.finam_base,
        )
        return "finam", candles

    raise ValueError(f"Unknown source: {args.source}")


# ---------------------------
# metrics printing (keep robust, call your metrics.py)
# ---------------------------
def _print_summary(broker, equity_curve: Optional[Sequence[float]] = None) -> int:
    trades = getattr(broker, "trades", []) or []
    eq = float(getattr(broker, "equity", 0.0) or 0.0)
    cash = float(getattr(broker, "cash", eq) or 0.0)

    print(f"equity={eq:.2f} cash={cash:.2f} trades={len(trades)}")

    try:
        from finam_bot.backtest.metrics import basic_trade_stats, compute_drawdown, compute_sharpe_sortino
    except Exception as e:
        logger.error("Trade metrics import failed: %s", e)
        return EXIT_METRICS_ERROR

    try:
        s = basic_trade_stats(trades, equity_curve=equity_curve)
        if dataclasses.is_dataclass(s):
            s = dataclasses.asdict(s)
    except Exception as e:
        logger.error("Trade metrics failed: %s", e)
        return EXIT_METRICS_ERROR

    # defensive defaults
    def g(key, default=0.0):
        v = s.get(key, default)
        try:
            return float(v)
        except Exception:
            return float(default)

    wins = int(g("wins", 0))
    losses = int(g("losses", 0))
    winrate = g("winrate", 0.0)
    pf = g("profit_factor", 0.0)
    expectancy = g("expectancy", 0.0)
    total_pnl = g("total_pnl", 0.0)
    fees = g("fees", g("total_fees", 0.0))
    avg_win = g("avg_win", 0.0)
    avg_loss = g("avg_loss", 0.0)
    payoff = g("payoff", 0.0)
    max_win_streak = int(g("max_win_streak", 0))
    max_loss_streak = int(g("max_loss_streak", 0))

    dd = compute_drawdown(list(equity_curve or []))
    sr = compute_sharpe_sortino(list(equity_curve or []))
    max_dd_pct = float(dd.get("max_drawdown_pct", 0.0) if isinstance(dd, dict) else (dd or 0.0))
    sharpe = float(sr.get("sharpe", 0.0) if isinstance(sr, dict) else 0.0)
    sortino = float(sr.get("sortino", 0.0) if isinstance(sr, dict) else 0.0)

    print(f"wins={wins} losses={losses} winrate={winrate*100:.2f}% profit_factor={pf:.2f}")
    print(f"expectancy={expectancy:.4f} total_pnl={total_pnl:.2f} fees={fees:.2f}")
    print(f"avg_win={avg_win:.2f} avg_loss={avg_loss:.2f} payoff={payoff:.2f}")
    print(f"maxDD={max_dd_pct*100:.2f}% sharpe={sharpe:.2f} sortino={sortino:.2f}")
    print(f"streaks: win={max_win_streak} loss={max_loss_streak}")
    return EXIT_OK


def _setup_logging(level: str) -> None:
    lvl = getattr(logging, (level or "WARNING").upper(), logging.WARNING)
    logging.basicConfig(level=lvl, format="%(levelname)s:%(name)s:%(message)s")
    logger.setLevel(lvl)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="finam_bot.backtest.cli")
    p.add_argument("--source", choices=["auto", "synthetic", "csv", "finam"], default="auto",
                   help="Data source: auto|synthetic|csv|finam")
    p.add_argument("--csv", default=None, help="Path to CSV file (if source=csv/auto).")
    p.add_argument("--strict", action="store_true", help="Do not fallback to synthetic if data load fails.")
    p.add_argument("--n", type=int, default=200, help="Bars count for synthetic mode.")
    p.add_argument("--seed", type=int, default=1, help="RNG seed for synthetic mode.")
    p.add_argument("--symbols", default="", help="Symbols list. For Finam: use format like SBER@MISX (comma/space separated).")
    p.add_argument("--tf", default="M1", help="Timeframe for Finam, e.g. M1, M5, H1, D1.")
    p.add_argument("--from", dest="dt_from", default="", help="ISO from datetime, e.g. 2026-02-01T10:00:00")
    p.add_argument("--to", dest="dt_to", default="", help="ISO to datetime, e.g. 2026-02-01T18:45:00")
    p.add_argument("--token", default="", help="Finam secret token. Prefer env FINAM_TOKEN.")
    p.add_argument("--finam-base", default=FINAM_BASE_DEFAULT, help="Finam REST base URL (default: https://api.finam.ru).")

    # engine params
    p.add_argument("--symbol", default="TEST", help="Backtest symbol (internal).")
    p.add_argument("--equity", type=float, default=100_000.0)
    p.add_argument("--commission", type=float, default=0.001)
    p.add_argument("--leverage", type=float, default=1.0)
    p.add_argument("--atr-period", type=int, default=14)
    p.add_argument("--atr-floor", type=float, default=0.0)
    p.add_argument("--fill", choices=["worst", "best"], default="worst")
    p.add_argument("--with-orderflow", action="store_true")
    p.add_argument("--log", default="WARNING")
    return p


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(list(argv) if argv is not None else None)
    _setup_logging(args.log)

    try:
        source, candles = load_candles_auto(args)
        logger.warning("Loaded candles source=%s bars=%d", source, len(candles))
    except Exception as e:
        logger.error("Data loading failed: %s", e)
        if args.strict:
            return EXIT_DATA_ERROR
        # fallback synthetic
        source = "synthetic"
        candles = generate_synthetic_candles(n=args.n, seed=args.seed)
        logger.warning("Fallback to synthetic bars=%d", len(candles))

    # NOTE: you plug your strategy here
    from finam_bot.strategies.order_flow_pullback import OrderFlowPullbackStrategy

    engine = BacktestEngine(
        args.symbol,
        OrderFlowPullbackStrategy(verbose=False),
        start_equity=args.equity,
        commission_rate=args.commission,
        max_leverage=args.leverage,
        atr_period=args.atr_period,
        fill_policy=args.fill,
    )
    # --- IMPORTANT: wire --with-orderflow for synthetic data ---
    if args.with_orderflow and source == "synthetic":
        try:
            # run_synthetic сам создаёт candles+orderflow согласованно
            broker = engine.run_synthetic(n=len(candles), with_orderflow=True)
            eq_curve = getattr(engine, "equity_curve", None)
            return _print_summary(broker, eq_curve)
        except Exception as e:
            logger.warning("run_synthetic(with_orderflow=True) failed (%s) -> fallback to engine.run(candles)", e)
    # ----------------------------------------------------------
    # orderflow is synthetic in engine if you already have it; here keep None
    broker = engine.run(candles, orderflow=None, atr_floor=args.atr_floor)
    eq_curve = getattr(engine, "equity_curve", None)
    return _print_summary(broker, eq_curve)


if __name__ == "__main__":
    raise SystemExit(main())
