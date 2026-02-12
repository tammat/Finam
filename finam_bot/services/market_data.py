# finam_bot/services/market_data.py

from finam_bot.grpc import FinamGrpcClient



class MarketDataService:
    def __init__(self, client):
        self.client = client

    def get_portfolios(self):
        return self.client.get_portfolios()

    def get_trades(self, limit=100):
        return self.client.get_trades(limit=limit)

    def get_transactions(self, days=7, limit=100):
        return self.client.get_transactions(days=days, limit=limit)

    def get_positions(self):
        return self.client.get_positions()