from finam_bot.services.market_data import MarketDataService
from finam_bot.grpc.factory import create_client

def main():
    client = create_client()
    service = MarketDataService(client)

    portfolios = service.get_portfolios()
    print("PORTFOLIOS:", portfolios)

if __name__ == "__main__":
    main()