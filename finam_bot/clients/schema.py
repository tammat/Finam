# finam_bot/clients/schema.py

PORTFOLIO_FIELDS = {
    "account_id": str,
    "balance": float,
}

TRADE_FIELDS = {
    "trade_id": str,
    "account_id": str,
    "ts": str,          # ISO-8601
    "symbol": str,
    "mic": str,
    "side": str,        # BUY / SELL
    "qty": float,
    "price": float,
    "order_id": str,
}

TRANSACTION_FIELDS = {
    "id": str,
    "ts": str,          # ISO-8601
    "symbol": str,
    "category": str,
    "amount": float,
    "currency": str,
    "description": str,
}
POSITION_FIELDS = {
    "account_id": str,
    "symbol": str,
    "mic": str,
    "qty": float,
    "avg_price": float,
    "current_price": float,
    "unrealized_pnl": float,
}
def validate_row(row: dict, schema: dict, entity: str):
    """
    Runtime contract validation.
    Raises ValueError if schema mismatch.
    """
    for field, field_type in schema.items():
        if field not in row:
            raise ValueError(f"{entity}: missing field '{field}'")

        if row[field] is not None and not isinstance(row[field], field_type):
            raise TypeError(
                f"{entity}: field '{field}' expected {field_type}, "
                f"got {type(row[field])}"
            )

    return True