from finam_bot.grpc import FinamGrpcClient
from finam_bot.services.market_data import MarketDataService

def main():
    client = FinamGrpcClient()
    service = MarketDataService(client)

    portfolios = service.get_portfolios()
    print("PORTFOLIOS:", portfolios)

if __name__ == "__main__":
    main()