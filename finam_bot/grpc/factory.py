# finam_bot/grpc/factory.py
import os

def create_client():
    mode = os.getenv("MODE", "TEST").upper()
    print("FACTORY MODE:", mode)

    if mode == "REAL":
        from finam_bot.finam_client import FinamClient
        return FinamClient()

    from finam_bot.grpc.finam_grpc_client import FinamGrpcClient
    return FinamGrpcClient()


# если где-то уже используется make_client — оставь совместимость
def make_client():
    return create_client()