# finam_bot/finam_client.py

import os
from pathlib import Path
import grpc
from dotenv import load_dotenv

# --- Надёжная загрузка .env ---
def _load_env_once():
    env_path = Path.cwd() / ".env"
    if env_path.exists():
        load_dotenv(env_path, override=True)

_load_env_once()


# --- gRPC stubs ---
from finam_bot.grpc_api.grpc.tradeapi.v1.accounts import (
    accounts_service_pb2_grpc,
    accounts_service_pb2,
)
from finam_bot.grpc_api.grpc.tradeapi.v1.orders import (
    orders_service_pb2_grpc,
    orders_service_pb2,
)
from finam_bot.grpc_api.grpc.tradeapi.v1.marketdata import (
    marketdata_service_pb2_grpc,
)
from finam_bot.grpc_api.grpc.tradeapi.v1.auth import (
    auth_service_pb2_grpc,
    auth_service_pb2,
)


class FinamClient:
    def __init__(self):

        self.mode = os.getenv("MODE", "REAL").upper()
        self.api_token = os.getenv("FINAM_TOKEN")
        self.account_id = os.getenv("FINAM_ACCOUNT_ID")

        if not self.api_token:
            raise RuntimeError("FINAM_TOKEN not set")

        if not self.account_id:
            raise RuntimeError("FINAM_ACCOUNT_ID not set")

        # --- host ---
        if self.mode == "TEST":
            self.host = "sandbox-api.finam.ru:443"
        else:
            self.host = "api.finam.ru:443"

        creds = grpc.ssl_channel_credentials()
        self.channel = grpc.secure_channel(self.host, creds)

        # --- AuthService ---
        self._auth_stub = auth_service_pb2_grpc.AuthServiceStub(self.channel)

        # обмен API token → JWT
        self.jwt_token = self._exchange_token()

        # --- Service stubs ---
        self.accounts = accounts_service_pb2_grpc.AccountsServiceStub(self.channel)
        self.orders = orders_service_pb2_grpc.OrdersServiceStub(self.channel)
        self.marketdata = marketdata_service_pb2_grpc.MarketDataServiceStub(self.channel)

        print("✅ FinamClient initialized")
        print("Host:", self.host)
        print("Account ID:", self.account_id)
        print("JWT length:", len(self.jwt_token))

    # -------------------------------------------------

    def _exchange_token(self) -> str:
        """
        Обменивает API токен на session JWT через AuthService
        """
        req = auth_service_pb2.AuthRequest(secret=self.api_token)
        resp = self._auth_stub.Auth(req)
        return resp.token

    # -------------------------------------------------

    def _meta(self):
        return (("authorization", f"Bearer {self.jwt_token}"),)

    # -------------------------------------------------
    # PUBLIC METHODS
    # -------------------------------------------------

    def get_account(self):
        req = accounts_service_pb2.GetAccountRequest(
            account_id=self.account_id
        )
        return self.accounts.GetAccount(req, metadata=self._meta())

    def get_orders(self):
        req = orders_service_pb2.OrdersRequest(
            account_id=self.account_id
        )
        return self.orders.GetOrders(req, metadata=self._meta())