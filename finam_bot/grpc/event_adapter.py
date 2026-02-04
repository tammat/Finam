# finam_bot/grpc/event_adapter.py

def decimal_to_float(decimal) -> float:
    return decimal.num / (10 ** decimal.scale)


def extract_price_from_event(event) -> float | None:
    """
    Из Event вытаскиваем цену сделки / котировки.
    Возвращает None, если событие не ценовое.
    """
    if event.HasField("trade"):
        return decimal_to_float(event.trade.price)

    if event.HasField("order_book"):
        return decimal_to_float(event.order_book.last_price)

    return None
