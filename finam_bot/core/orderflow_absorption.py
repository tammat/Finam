from finam_bot.core.orderflow_signal import AbsorptionSignal


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
            side="BUY",                 # или SELL — см. ниже
            imbalance=0.0,              # absorption = нет направленного перекоса
            strength=total_volume,
            reason="absorption",
        )
