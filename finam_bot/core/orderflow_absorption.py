from finam_bot.core.orderflow_signal import AbsorptionSignal
from finam_bot.core.market_snapshot import MarketSnapshot


class OrderFlowAbsorptionDetector:
    def __init__(
        self,
        min_volume: float,
        price_tolerance: float,
        eps: float = 1e-9,
    ):
        self.min_volume = min_volume
        self.price_tolerance = price_tolerance
        self.eps = eps

    def analyze(
        self,
        prices: list[float],
        volumes: list[float],
    ):
        if not prices or not volumes:
            return None

        total_volume = sum(volumes)
        if total_volume < self.min_volume:
            return None

        mean_price = sum(prices) / len(prices)
        max_deviation = max(abs(p - mean_price) for p in prices)

        if max_deviation > self.price_tolerance + self.eps:
            return None

        # ✅ ВАЖНО: правильный конструктор
        return AbsorptionSignal(
            side=None,          # 🔥 КЛЮЧЕВО
            strength=total_volume,
            imbalance=0.0,
            reason="absorption",
        )


    def analyze_snapshot(self, snapshot: MarketSnapshot):
        """
        Absorption + определение стороны по агрессору (bid/ask).
        """
        base = self.analyze(prices=snapshot.prices, volumes=snapshot.volumes)
        if base is None:
            return None

        bid = snapshot.bid_volume or 0.0
        ask = snapshot.ask_volume or 0.0
        total = bid + ask

        side = None
        if total > 0:
            ratio = bid / total
            if ratio >= 0.6:
                side = "BUY"
            elif ratio <= 0.4:
                side = "SELL"

        # ВАЖНО: не мутируем base (на случай frozen dataclass)
        return AbsorptionSignal(
            side=side,
            strength=base.strength,
            imbalance=getattr(base, "imbalance", 0.0),
            reason=base.reason,
        )
