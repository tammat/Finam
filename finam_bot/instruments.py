def asset_class_by_symbol(symbol: str) -> str:
    s = symbol.upper()
    if s.startswith("NG") or s.endswith(".F") or "-" in s:
        return "futures"
    if s.endswith(".B"):
        return "bonds"
    return "stocks"