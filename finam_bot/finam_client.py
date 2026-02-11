# finam_bot/finam_client.py

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import os
import grpc
from dotenv import load_dotenv

from google.type import interval_pb2
from google.protobuf.timestamp_pb2 import Timestamp

# --- gRPC stubs ---
from finam_bot.grpc_api.grpc.tradeapi.v1.accounts import (
    accounts_service_pb2,
    accounts_service_pb2_grpc,
)
from finam_bot.grpc_api.grpc.tradeapi.v1.orders import (
    orders_service_pb2,
    orders_service_pb2_grpc,
)
from finam_bot.grpc_api.grpc.tradeapi.v1.marketdata import (
    marketdata_service_pb2_grpc,
)
from finam_bot.grpc_api.grpc.tradeapi.v1.auth import (
    auth_service_pb2,
    auth_service_pb2_grpc,
)


# -------------------------------------------------
# ENV
# -------------------------------------------------

def _load_env_once() -> None:
    env_path = Path.cwd() / ".env"
    if env_path.exists():
        load_dotenv(env_path, override=True)


_load_env_once()


# -------------------------------------------------
# CLIENT
# -------------------------------------------------

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

        # --- Auth ---
        self._auth_stub = auth_service_pb2_grpc.AuthServiceStub(self.channel)
        self.jwt_token = self._exchange_token()

        self.metadata = [("authorization", f"Bearer {self.jwt_token}")]

        # --- Services ---
        self.accounts = accounts_service_pb2_grpc.AccountsServiceStub(self.channel)
        self.orders = orders_service_pb2_grpc.OrdersServiceStub(self.channel)
        self.marketdata = marketdata_service_pb2_grpc.MarketDataServiceStub(self.channel)

        print("✅ FinamClient initialized")
        print("Host:", self.host)
        print("Account ID:", self.account_id)
        print("JWT length:", len(self.jwt_token))

    # -------------------------------------------------

    def _exchange_token(self) -> str:
        req = auth_service_pb2.AuthRequest(secret=self.api_token)
        resp = self._auth_stub.Auth(req)
        return resp.token

    # -------------------------------------------------

    def _rpc_call(self, fn: Callable, request: Any):
        return fn(request, metadata=self.metadata)

    # -------------------------------------------------
    # ACCOUNT
    # -------------------------------------------------

    def get_account(self):
        req = accounts_service_pb2.GetAccountRequest(
            account_id=str(self.account_id)
        )
        return self._rpc_call(self.accounts.GetAccount, req)

    # -------------------------------------------------
    # TRADES
    # -------------------------------------------------

    def get_trades(self, days: int = 7, limit: int = 100) -> List[Dict]:

        now = datetime.now(timezone.utc)
        start = now - timedelta(days=days)

        start_ts = Timestamp()
        start_ts.FromDatetime(start)

        end_ts = Timestamp()
        end_ts.FromDatetime(now)

        interval = interval_pb2.Interval(
            start_time=start_ts,
            end_time=end_ts,
        )

        req = accounts_service_pb2.TradesRequest(
            account_id=str(self.account_id),
            limit=int(limit),
            interval=interval,
        )

        resp = self._rpc_call(self.accounts.Trades, req)

        out: List[Dict] = []

        for t in resp.trades:
            out.append({
                "trade_id": t.trade_id,
                "account_id": t.account_id,
                "ts": t.timestamp.seconds if t.timestamp else None,
                "symbol": t.symbol,
                "side": t.side,
                "qty": float(t.size.value) if t.size.value else None,
                "price": float(t.price.value) if t.price.value else None,
                "order_id": t.order_id,
            })

        return out

    # -------------------------------------------------
    # TRANSACTIONS
    # -------------------------------------------------

    def get_transactions(self, days: int = 7, limit: int = 100) -> List[Dict]:

        now = datetime.now(timezone.utc)
        start = now - timedelta(days=days)

        start_ts = Timestamp()
        start_ts.FromDatetime(start)

        end_ts = Timestamp()
        end_ts.FromDatetime(now)

        interval = interval_pb2.Interval(
            start_time=start_ts,
            end_time=end_ts,
        )

        req = accounts_service_pb2.TransactionsRequest(
            account_id=str(self.account_id),
            limit=int(limit),
            interval=interval,
        )

        resp = self._rpc_call(self.accounts.Transactions, req)

        out: List[Dict] = []

        for t in resp.transactions:

            amount = 0.0
            currency = None

            if t.change:
                currency = t.change.currency_code
                amount = float(t.change.units) + float(t.change.nanos) / 1_000_000_000

            out.append({
                "id": t.id,
                "ts": t.timestamp.seconds if t.timestamp else None,
                "symbol": t.symbol,
                "category": t.transaction_category,
                "amount": amount,
                "currency": currency,
                "description": t.transaction_name,
            })

        return out

    # -------------------------------------------------
    # ORDERS
    # -------------------------------------------------

    def get_orders(self):
        req = orders_service_pb2.OrdersRequest(
            account_id=str(self.account_id)
        )
        return self._rpc_call(self.orders.GetOrders, req)

    def get_order(self, order_id: str):
        req = orders_service_pb2.GetOrderRequest(
            account_id=str(self.account_id),
            order_id=str(order_id),
        )
        return self._rpc_call(self.orders.GetOrder, req)

    def cancel_order(self, order_id: str):
        req = orders_service_pb2.CancelOrderRequest(
            account_id=str(self.account_id),
            order_id=str(order_id),
        )
        return self._rpc_call(self.orders.CancelOrder, req)