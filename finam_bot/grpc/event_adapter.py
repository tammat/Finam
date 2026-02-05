from finam_bot.core.market_snapshot import MarketSnapshot


def extract_price_from_event(event) -> float | None:
    """
    Минимальный адаптер: извлечь последнюю цену из gRPC event
    Используется FinamGrpcClient
    """
    return getattr(event, "last_price", None)


def event_to_snapshot(event) -> MarketSnapshot | None:
    """
    Полный адаптер: gRPC event → MarketSnapshot
    Используется стратегией (READ-ONLY)
    """
    try:
        price = extract_price_from_event(event)
        if price is None:
            return None

        return MarketSnapshot(
            symbol=event.symbol,
            price=price,
            bid_volume=getattr(event, "bid_volume", None),
            ask_volume=getattr(event, "ask_volume", None),
            atr=None,              # ATR добавим на S5.A.1
            timestamp=event.time
        )

    except Exception as e:
        print(f"❌ event_to_snapshot error: {e}")
        return None
