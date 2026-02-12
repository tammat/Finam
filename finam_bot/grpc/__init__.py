import os

MODE = os.getenv("MODE", "TEST").upper()

if MODE == "REAL":
    try:
        from finam_bot.finam_client import FinamClient

        test_client = FinamClient()
        if not test_client.health_check():
            raise RuntimeError("Health check failed")

        FinamGrpcClient = FinamClient

    except Exception as e:
        print("⚠ REAL mode failed, switching to TEST mode")
        print("Reason:", e)
        from finam_bot.grpc.finam_grpc_client import FinamGrpcClient
else:
    from finam_bot.grpc.finam_grpc_client import FinamGrpcClient