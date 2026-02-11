# scripts/probe_accounts.py

from finam_bot.finam_client import FinamClient
from finam_bot.grpc_api.grpc.tradeapi.v1.accounts import accounts_service_pb2

c = FinamClient()

req = accounts_service_pb2.TradesRequest(
    account_id="940956RIZL5",
    limit=1
)

resp = c.accounts.Trades(req, metadata=c._meta())
print(resp)