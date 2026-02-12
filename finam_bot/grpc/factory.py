# finam_bot/grpc/factory.py

import os

MODE = os.getenv("MODE", "TEST").upper()

def create_client():
    if MODE == "REAL":
        from finam_bot.finam_client import FinamClient
        return FinamClient()

    else:
        from finam_bot.grpc.finam_grpc_client import FinamGrpcClient
        return FinamGrpcClient()