import os

MODE = os.getenv("MODE", "TEST").upper()

if MODE == "REAL":
    from finam_bot.finam_client import FinamClient as FinamGrpcClient
else:
    from finam_bot.grpc.finam_grpc_client import FinamGrpcClient