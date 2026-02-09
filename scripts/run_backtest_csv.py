# scripts/run_backtest_csv.py
from __future__ import annotations
import csv
import sys

from finam_bot.backtest.engine import BacktestEngine
from finam_bot.backtest.metrics import summarize
from finam_bot.data.csv_loader import load_candles_csv


# Пример: стратегия (потом подставишь свою реальную)
from finam_bot.strategies.order_flow_pullback import OrderFlowPullbackStrategy


def export_trades(trades, path="trades_out.csv"):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["symbol", "side", "entry_ts", "entry_px", "exit_ts", "exit_px", "qty", "pnl", "reason"])
        for t in trades:
            w.writerow([t.symbol, t.side, t.entry_ts, t.entry_price, t.exit_ts, t.exit_price, t.qty, t.pnl, t.reason])


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/run_backtest_csv.py path/to/data.csv")
        raise SystemExit(1)

    path = sys.argv[1]
    candles = load_candles_csv(
        path,
        col_ts="ts",      # поменяешь под свой CSV
        col_open="open",
        col_high="high",
        col_low="low",
        col_close="close",
        col_volume="volume",
        delimiter=",",
    )

    engine = BacktestEngine(
        symbol="TEST",
        strategy=OrderFlowPullbackStrategy(),
        start_equity=100_000.0,
        commission_rate=0.0004,
        max_leverage=2.0,
        atr_period=14,
        fill_policy="worst",  # worst/best
    )

    broker = engine.run(candles)

    report = summarize(broker.trades, broker.equity_curve)

    print("=== BACKTEST REPORT ===")
    print(f"Trades: {report.trades}")
    print(f"Wins/Losses: {report.wins}/{report.losses} (winrate={report.winrate:.2%})")
    print(f"Gross PnL: {report.gross_pnl:.2f}")
    print(f"Avg PnL: {report.avg_pnl:.2f}")
    print(f"Expectancy: {report.expectancy:.2f}")
    print(f"Max DD: {report.max_drawdown:.2f}")
    print(f"Final equity: {broker.equity:.2f}")

    export_trades(broker.trades, "trades_out.csv")
    print("Saved trades_out.csv")


if __name__ == "__main__":
    main()
