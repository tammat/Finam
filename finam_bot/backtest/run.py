# finam_bot/backtest/run.py
from __future__ import annotations

import argparse

from finam_bot.backtest.engine import BacktestEngine
from finam_bot.strategies.order_flow_pullback import OrderFlowPullbackStrategy

try:
    # если есть готовые метрики — используем
    from finam_bot.backtest.metrics import summarize_broker  # type: ignore
except Exception:
    summarize_broker = None  # fallback ниже


def _fallback_summary(broker) -> str:
    trades = getattr(broker, "trades", []) or []
    equity = getattr(broker, "equity", None)
    cash = getattr(broker, "cash", None)

    lines = []
    lines.append(f"equity={equity} cash={cash} trades={len(trades)}")

    if trades:
        pnl_list = []
        wins = 0
        losses = 0
        gross_profit = 0.0
        gross_loss = 0.0

        for t in trades:
            pnl = getattr(t, "pnl", None)
            if pnl is None:
                # если pnl нет — пробуем вычислить грубо
                entry = getattr(t, "entry_price", None)
                exitp = getattr(t, "exit_price", None)
                qty = getattr(t, "qty", 0.0)
                if entry is not None and exitp is not None:
                    side = getattr(t, "side", "LONG")
                    sign = 1.0 if side == "LONG" else -1.0
                    pnl = (exitp - entry) * qty * sign
                else:
                    pnl = 0.0

            pnl_list.append(float(pnl))
            if pnl > 0:
                wins += 1
                gross_profit += pnl
            elif pnl < 0:
                losses += 1
                gross_loss += abs(pnl)

        winrate = wins / len(trades) if trades else 0.0
        pf = (gross_profit / gross_loss) if gross_loss > 0 else float("inf")

        lines.append(f"wins={wins} losses={losses} winrate={winrate:.2%} profit_factor={pf:.2f}")

        total_pnl = sum(pnl_list)
        lines.append(f"total_pnl={total_pnl:.2f}")

    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser("finam_bot backtest runner (synthetic)")
    ap.add_argument("--symbol", default="TEST")
    ap.add_argument("--n", type=int, default=500)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--start-equity", type=float, default=100_000.0)
    ap.add_argument("--commission", type=float, default=0.0004)
    ap.add_argument("--max-leverage", type=float, default=2.0)
    ap.add_argument("--fill-policy", default="worst", choices=["worst", "best"])
    ap.add_argument("--with-orderflow", action="store_true", help="add synthetic orderflow for OrderFlow strategy")
    ap.add_argument("--atr-floor", type=float, default=0.01)

    args = ap.parse_args()

    strategy = OrderFlowPullbackStrategy()

    engine = BacktestEngine(
        symbol=args.symbol,
        strategy=strategy,
        start_equity=args.start_equity,
        commission_rate=args.commission,
        max_leverage=args.max_leverage,
        fill_policy=args.fill_policy,
        atr_period=14,
    )

    broker = engine.run_synthetic(
        n=args.n,
        seed=args.seed,
        with_orderflow=args.with_orderflow,
        atr_floor=args.atr_floor,
    )

    if summarize_broker is not None:
        print(summarize_broker(broker))
    else:
        print(_fallback_summary(broker))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
