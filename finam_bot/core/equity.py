# finam_bot/core/equity.py

class EquityCurve:
    def __init__(self, start_equity: float):
        self.start_equity = start_equity
        self.equity = start_equity
        self.history = [start_equity]

    def apply_pnl(self, pnl: float):
        self.equity += pnl
        self.history.append(self.equity)
