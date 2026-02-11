# finam_bot/services/market_data.py

from finam_bot.grpc.finam_grpc_client import FinamGrpcClient
from finam_bot.infra.grpc.adapters import (
    portfolios_to_dict,
    events_to_dict,
)


class MarketDataService:

    def __init__(self, grpc_client: FinamGrpcClient):
        self.grpc = grpc_client

    def get_portfolios(self):
        raw = self.grpc.get_portfolios_raw()
        return portfolios_to_dict(raw)

    def get_events(self):
        raw = self.grpc.get_events_raw()
        return events_to_dict(raw)