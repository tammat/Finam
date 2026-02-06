from finam_bot.core.risk_manager import RiskManager

def test_position_size_uses_equity_when_provided():
    rm = RiskManager(capital=10_000, risk_pct=0.01, sl_atr_mult=1.0, tp_atr_mult=1.0, min_stop=1.0)

    # stop_dist = 10 → риск 1% от equity
    qty_eq_10k = rm.position_size(10, equity=10_000)
    qty_eq_20k = rm.position_size(10, equity=20_000)

    assert qty_eq_20k == qty_eq_10k * 2
