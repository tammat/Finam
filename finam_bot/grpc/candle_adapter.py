# finam_bot/grpc/candle_adapter.py

def decimal_to_float(decimal) -> float:
    """
    Finam Decimal(num, scale) -> float
    """
    return decimal.num / (10 ** decimal.scale)


def candle_close_price(candle) -> float:
    """
    Из gRPC candle берём цену закрытия
    """
    return decimal_to_float(candle.close)
