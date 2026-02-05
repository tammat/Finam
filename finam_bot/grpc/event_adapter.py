from finam_bot.core.market_snapshot import MarketSnapshot


def extract_price_from_event(event) -> float | None:
    """
    Минимальный адаптер: извлечь последнюю цену из gRPC event
    Используется FinamGrpcClient
    """
    return getattr(event, "last_price", None)


def event_to_snapshot(event, symbol: str) -> MarketSnapshot | None:
    """
    Преобразует gRPC event → MarketSnapshot
    """
    # пример — зависит от структуры event
    if not hasattr(event, "last_price"):
        return None

    return MarketSnapshot(
        symbol=symbol,
        price=event.last_price,
        bid_volume=getattr(event, "bid_volume", None),
        ask_volume=getattr(event, "ask_volume", None),
        atr=None,          # ATR позже
        timestamp=None,
    )
