# finam_bot/backtest/data_loader.py
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable, Optional, Sequence

import csv
import math
import re

from finam_bot.backtest.models import Candle


# ----------------------------
# helpers
# ----------------------------

def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", (s or "").strip().lower())


def _to_float(x: object) -> Optional[float]:
    if x is None:
        return None
    if isinstance(x, (int, float)):
        v = float(x)
        return v if math.isfinite(v) else None
    s = str(x).strip()
    if not s:
        return None
    # support "1 234,56" and "1234.56"
    s = s.replace(" ", "").replace("\u00a0", "")
    if s.count(",") == 1 and s.count(".") == 0:
        s = s.replace(",", ".")
    try:
        v = float(s)
        return v if math.isfinite(v) else None
    except ValueError:
        return None


def _to_int(x: object) -> Optional[int]:
    if x is None:
        return None
    if isinstance(x, int):
        return x
    if isinstance(x, float):
        if math.isfinite(x):
            return int(x)
        return None
    s = str(x).strip()
    if not s:
        return None
    s = s.replace(" ", "").replace("\u00a0", "")
    # epoch might be "1700000000.0"
    try:
        f = float(s.replace(",", "."))
        if math.isfinite(f):
            return int(f)
    except ValueError:
        return None
    return None


def _parse_datetime_to_ts(
    s: object,
    *,
    tz: Optional[timezone] = None,
    dayfirst: bool = True,
) -> Optional[int]:
    """
    Tries to parse:
      - epoch seconds / ms
      - ISO datetime
      - common CSV datetime formats (Finam/TradingView-like)
    Returns epoch seconds (int).
    """
    if s is None:
        return None

    # epoch
    as_int = _to_int(s)
    if as_int is not None:
        # heuristics: ms vs sec
        if as_int > 10_000_000_000:  # ms
            return int(as_int / 1000)
        if as_int > 1_000_000_000:  # sec (2001+)
            return as_int

    raw = str(s).strip()
    if not raw:
        return None

    # Normalize separators
    raw2 = raw.replace("T", " ").replace("/", ".")
    raw2 = re.sub(r"\s+", " ", raw2)

    fmts = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y.%m.%d %H:%M:%S",
        "%Y.%m.%d %H:%M",
        "%d.%m.%Y %H:%M:%S",
        "%d.%m.%Y %H:%M",
        "%Y-%m-%d",
        "%d.%m.%Y",
        "%Y.%m.%d",
    ]

    # try ISO auto-ish
    try:
        dt = datetime.fromisoformat(raw2)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=tz)
        return int(dt.timestamp())
    except Exception:
        pass

    for f in fmts:
        try:
            dt = datetime.strptime(raw2, f)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=tz)
            return int(dt.timestamp())
        except Exception:
            continue

    # last chance: date + time split like "20240101" "120000"
    digits = re.sub(r"\D", "", raw)
    if len(digits) in (12, 14):  # YYYYMMDDHHMM[SS]
        try:
            if len(digits) == 12:
                dt = datetime.strptime(digits, "%Y%m%d%H%M")
            else:
                dt = datetime.strptime(digits, "%Y%m%d%H%M%S")
            dt = dt.replace(tzinfo=tz)
            return int(dt.timestamp())
        except Exception:
            pass

    return None


# ----------------------------
# main API
# ----------------------------

@dataclass(frozen=True)
class ColumnMap:
    ts: str
    open: str
    high: str
    low: str
    close: str
    volume: Optional[str] = None


DEFAULT_ALIASES = {
    "ts": {"ts", "time", "timestamp", "datetime", "date", "dttm"},
    "open": {"open", "o"},
    "high": {"high", "h"},
    "low": {"low", "l"},
    "close": {"close", "c", "last"},
    "volume": {"volume", "vol", "v", "qty", "quantity"},
}


def sniff_column_map(headers: Sequence[str]) -> ColumnMap:
    """
    Tries to map headers to Candle fields.
    Raises ValueError if cannot map required OHLC.
    """
    normed = {_norm(h): h for h in headers if h is not None}
    def pick(key: str, required: bool = True) -> Optional[str]:
        for alias in DEFAULT_ALIASES[key]:
            if alias in normed:
                return normed[alias]
        return None

    ts = pick("ts", required=False)
    o = pick("open")
    h = pick("high")
    l = pick("low")
    c = pick("close")
    v = pick("volume", required=False)

    if not (o and h and l and c):
        raise ValueError(f"Cannot map OHLC from headers={list(headers)}")

    # ts is optional; we will generate monotonic ts if missing
    return ColumnMap(ts=ts or "", open=o, high=h, low=l, close=c, volume=v)


def load_csv_candles(
    path: str,
    *,
    sep: Optional[str] = None,
    encoding: str = "utf-8",
    tz: Optional[timezone] = timezone.utc,
    dayfirst: bool = True,
    limit: Optional[int] = None,
    column_map: Optional[ColumnMap] = None,
    skip_bad_rows: bool = True,
    generate_ts_if_missing: bool = True,
    start_ts: int = 1,
    ts_step: int = 1,
) -> list[Candle]:
    """
    Universal CSV loader -> list[Candle].

    - Auto delimiter detection (if sep is None)
    - Auto header mapping (if column_map is None)
    - Timestamp optional: can parse or generate monotonic.
    - Skips bad rows by default.
    """
    with open(path, "r", encoding=encoding, newline="") as f:
        sample = f.read(4096)
        f.seek(0)

        if sep is None:
            try:
                dialect = csv.Sniffer().sniff(sample, delimiters=[",", ";", "\t", "|"])
                sep = dialect.delimiter
            except Exception:
                sep = ","  # fallback

        reader = csv.DictReader(f, delimiter=sep)
        if reader.fieldnames is None:
            raise ValueError("CSV has no header row (fieldnames missing)")

        if column_map is None:
            column_map = sniff_column_map(reader.fieldnames)

        out: list[Candle] = []
        ts_counter = start_ts

        for row in reader:
            if limit is not None and len(out) >= limit:
                break

            try:
                o = _to_float(row.get(column_map.open))
                h = _to_float(row.get(column_map.high))
                l = _to_float(row.get(column_map.low))
                c = _to_float(row.get(column_map.close))
                v = _to_float(row.get(column_map.volume)) if column_map.volume else 0.0

                if o is None or h is None or l is None or c is None:
                    raise ValueError("Missing OHLC")

                ts_val: Optional[int] = None
                if column_map.ts:
                    ts_val = _parse_datetime_to_ts(row.get(column_map.ts), tz=tz, dayfirst=dayfirst)

                if ts_val is None:
                    if not generate_ts_if_missing:
                        ts_val = None
                    else:
                        ts_val = ts_counter
                        ts_counter += ts_step

                # enforce candle constraints
                hi = max(h, o, c)
                lo = min(l, o, c)

                out.append(
                    Candle(
                        ts=ts_val,
                        open=float(o),
                        high=float(hi),
                        low=float(lo),
                        close=float(c),
                        volume=float(v or 0.0),
                    )
                )
            except Exception:
                if skip_bad_rows:
                    continue
                raise

        return out
