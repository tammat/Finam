# finam_bot/infra/grpc/client.py

import os
import grpc

from proto.tradeapi.v1 import portfolios_pb2
from proto.tradeapi.v1 import portfolios_pb2_grpc
from proto.tradeapi.v1 import events_pb2
from proto.tradeapi.v1 import events_pb2_grpc


class FinamGrpcClient:

    def __init__(self, jwt=None, host="api.finam.ru:443"):
        self.jwt = jwt or os.getenv("FINAM_JWT")
        if not self.jwt:
            raise RuntimeError("FINAM_JWT is not set")

        self.channel = grpc.secure_channel(
            host,
            grpc.ssl_channel_credentials(),
        )

        self.metadata = [("authorization", f"Bearer {self.jwt}")]

        self.portfolio_stub = portfolios_pb2_grpc.PortfoliosStub(self.channel)
        self.events_stub = events_pb2_grpc.EventsStub(self.channel)

    def get_portfolios_raw(self):
        request = portfolios_pb2.GetPortfoliosRequest()
        return self.portfolio_stub.GetPortfolios(
            request,
            metadata=self.metadata,
        )

    def get_events_raw(self):
        request = events_pb2.GetEventsRequest()
        return self.events_stub.GetEvents(
            request,
            metadata=self.metadata,
        )