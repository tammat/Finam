# finam_bot/execution/executor.py

from typing import Optional
from finam_bot.grpc import FinamGrpcClient


class OrderExecutor:
    def __init__(self, grpc: FinamGrpcClient):
        self.grpc = grpc

    # -------------------------------------------------
    # MARKET ORDER
    # -------------------------------------------------
    def market_order(
        self,
        symbol: str,
        side: str,  # "BUY" / "SELL"
        qty: float,
    ):
        print(f"[EXEC] MARKET {side} {symbol} x{qty}")

        try:
            result = self.grpc.place_market_order(
                symbol=symbol,
                side=side,
                quantity=qty,
            )

            print("[EXEC] OK:", result)
            return result

        except Exception as e:
            print("[EXEC] ERROR:", e)
            return None

    # -------------------------------------------------
    # LIMIT ORDER
    # -------------------------------------------------
    def limit_order(
        self,
        symbol: str,
        side: str,
        qty: float,
        price: float,
    ):
        print(f"[EXEC] LIMIT {side} {symbol} x{qty} @ {price}")

        try:
            result = self.grpc.place_limit_order(
                symbol=symbol,
                side=side,
                quantity=qty,
                price=price,
            )

            print("[EXEC] OK:", result)
            return result

        except Exception as e:
            print("[EXEC] ERROR:", e)
            return None

    # -------------------------------------------------
    # CANCEL
    # -------------------------------------------------
    def cancel(self, order_id: str):
        print(f"[EXEC] CANCEL {order_id}")

        try:
            result = self.grpc.cancel_order(order_id)
            print("[EXEC] OK:", result)
            return result

        except Exception as e:
            print("[EXEC] ERROR:", e)
            return None