from finam_bot.finam_client import FinamClient
from finam_bot.grpc_api.grpc.tradeapi.v1.accounts import accounts_service_pb2

c = FinamClient()

print("Using account_id:", c.account_id)

req = accounts_service_pb2.GetAccountRequest(
    account_id=c.account_id
)

resp = c.accounts.GetAccount(req, metadata=c._meta())
print(resp)