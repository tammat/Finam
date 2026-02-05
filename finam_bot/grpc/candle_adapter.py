# finam_bot/grpc/candle_adapter.py

from dataclasses import dataclass
from typing import Optional


@dataclass
class Candle:
    open: float
    high: float
    low: float
    close: float
    volume: Optional[float] = None
    timestamp: Optional[int] = None


def candle_from_proto(proto) -> Candle:
    """
    Adapter: Finam gRPC Candle → internal Candle
    """

    return Candle(
        open=proto.open,
        high=proto.high,
        low=proto.low,
        close=proto.close,
        volume=getattr(proto, "volume", None),
        timestamp=getattr(proto, "timestamp", None),
    )
