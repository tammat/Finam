def asset_class_by_symbol(symbol: str) -> str:
    s = symbol.upper()
    if s.startswith("NG") or s.endswith(".F") or "-" in s:
        return "futures"
    if s.endswith(".B"):
        return "bonds"
    return "stocks"
# finam_bot/instruments.py

INSTRUMENTS = {
    "NG-2.26": {
        "asset_class": "FUTURES",
    },
    "BR-3.26": {
        "asset_class": "FUTURES",
    },
    # добавляй по мере необходимости
}


def get_asset_class(symbol: str) -> str:
    """
    Return asset_class for symbol.
    Raises KeyError if symbol is unknown (это правильно).
    """
    try:
        return INSTRUMENTS[symbol]["asset_class"]
    except KeyError:
        raise KeyError(f"Unknown instrument: {symbol}")