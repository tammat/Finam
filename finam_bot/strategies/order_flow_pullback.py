from __future__ import annotations

import logging
from typing import Optional

from finam_bot.core.market_snapshot import MarketSnapshot
from finam_bot.core.orderflow_absorption import OrderFlowAbsorptionDetector
from finam_bot.core.orderflow_analyzer import OrderFlowAnalyzer
from finam_bot.core.orderflow_composite import build_composite_signal
from finam_bot.core.signals import Signal


class OrderFlowPullbackStrategy:
    """
    Minimal Order Flow strategy wrapper used by BacktestEngine.

    - Analyzes imbalance from MarketSnapshot (bid/ask volumes)
    - Optionally detects absorption from (prices, volumes) tape window
    - Builds composite signal and applies confidence filter
    """

    def __init__(
        self,
        *,
        verbose: bool = False,
        log_level: int | None = None,
        logger: logging.Logger | None = None,
        min_confidence: float = 0.6,
        imbalance_threshold: float = 0.6,
        absorption_min_volume: float = 100.0,
        absorption_price_tolerance: float = 0.01,
        infer_absorption_side_from_imbalance: bool = True,
        infer_opposite_tol_threshold: float = 0.001,
    ):
        self.verbose = verbose
        if log_level is None:
            log_level = logging.INFO if verbose else logging.WARNING

        self.logger = logger or logging.getLogger(self.__class__.__name__)
        self.logger.setLevel(log_level)

        self.imbalance_analyzer = OrderFlowAnalyzer(imbalance_threshold=imbalance_threshold)
        self.absorption_detector = OrderFlowAbsorptionDetector(
            min_volume=absorption_min_volume,
            price_tolerance=absorption_price_tolerance,
        )

        self.min_confidence = float(min_confidence)
        self.last_confidence: float = 0.0

        # heuristic for tests/backtest:
        # if absorption detector gives side=None, infer it from imbalance (or opposite if tolerance is ultra-tight)
        self.infer_absorption_side_from_imbalance = infer_absorption_side_from_imbalance
        self.infer_opposite_tol_threshold = float(infer_opposite_tol_threshold)

    def on_snapshot(self, snapshot: MarketSnapshot) -> Signal:
        # 1) imbalance
        imbalance = self.imbalance_analyzer.analyze(snapshot)

        # 2) absorption (if tape window is present)
        absorption = None
        if getattr(snapshot, "prices", None) and getattr(snapshot, "volumes", None):
            absorption = self.absorption_detector.analyze(
                prices=snapshot.prices,
                volumes=snapshot.volumes,
            )

        # 2b) optional side inference for absorption
        if (
            self.infer_absorption_side_from_imbalance
            and absorption is not None
            and getattr(absorption, "side", None) is None
            and imbalance is not None
        ):
            # if tolerance is extremely small -> treat as opposite (blocks trade)
            if self.absorption_detector.price_tolerance < self.infer_opposite_tol_threshold:
                absorption.side = "SELL" if imbalance.side == "BUY" else "BUY"
            else:
                absorption.side = imbalance.side

        # 3) composite
        composite = build_composite_signal(imbalance=imbalance, absorption=absorption)

        if composite is None:
            self.last_confidence = 0.0
            return Signal.HOLD

        # 4) confidence gate
        self.last_confidence = composite.confidence
        if composite.confidence < self.min_confidence:
            return Signal.HOLD

        # 5) logging
        if self.verbose:
            self.logger.info(
                "🧠 COMPOSITE %s | confidence=%.2f | reasons=%s",
                composite.side,
                composite.confidence,
                ",".join(composite.reasons),
            )

        if composite.side == "BUY":
            return Signal.BUY
        if composite.side == "SELL":
            return Signal.SELL
        return Signal.HOLD
