"""
CLI-проверка Risk v2.2 (asset_class)

Запуск:
python -m scripts.check_risk_v22
python -m scripts.check_risk_v22 --asset FUTURES
"""

import argparse

from finam_bot.storage_sqlite import StorageSQLite
from finam_bot.risk_engine_v2_2 import RiskEngineV22


def main():
    parser = argparse.ArgumentParser(description="Check Risk v2.2 by asset_class")
    parser.add_argument(
        "--asset",
        type=str,
        default="FUTURES",
        help="Asset class to test (FUTURES, EQUITY, BOND, ETF, CURRENCY)",
    )
    parser.add_argument(
        "--equity",
        type=float,
        default=1_000_000,
        help="Account equity",
    )
    parser.add_argument(
        "--qty",
        type=float,
        default=1,
        help="Test quantity",
    )
    parser.add_argument(
        "--entry",
        type=float,
        default=100.0,
        help="Entry price",
    )
    parser.add_argument(
        "--stop",
        type=float,
        default=99.0,
        help="Stop price",
    )

    args = parser.parse_args()

    storage = StorageSQLite()
    risk = RiskEngineV22(storage, equity=args.equity)

    verdict = risk.check(
        qty=args.qty,
        entry=args.entry,
        stop=args.stop,
        asset_class=args.asset,
    )

    print("=== RISK v2.2 CHECK ===")
    print(f"ASSET_CLASS : {args.asset}")
    print(f"QTY         : {args.qty}")
    print(f"ENTRY/STOP  : {args.entry} / {args.stop}")
    print("----------------------")
    print(f"ALLOWED     : {verdict.allowed}")
    print(f"REASON      : {verdict.reason}")

    if verdict.metric is not None and verdict.limit is not None:
        print(f"DETAIL      : {verdict.metric:.6f} > {verdict.limit:.6f}")

    print("======================")

    # Ненулевой код возврата при блокировке — удобно для CI
    if not verdict.allowed:
        raise SystemExit(2)


if __name__ == "__main__":
    main()