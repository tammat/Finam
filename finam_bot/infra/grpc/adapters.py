# finam_bot/infra/grpc/adapters.py

def portfolios_to_dict(response):
    return [
        {
            "account_id": p.account_id,
            "balance": p.balance,
        }
        for p in response.portfolios
    ]


def events_to_dict(response):
    result = []

    for e in response.events:
        result.append({
            "id": e.id,
            "symbol": e.symbol,
            "price": e.price.value if hasattr(e.price, "value") else None,
            "qty": e.size.value if hasattr(e.size, "value") else None,
            "timestamp": e.timestamp,
        })

    return result