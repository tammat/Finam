from abc import ABC, abstractmethod
from typing import List, Dict, Any


class BaseTradingClient(ABC):
    """
    Production-контракт торгового клиента.
    Любая реализация (Finam, Binance, IBKR и т.д.)
    обязана строго соответствовать этому интерфейсу.
    """

    # ---------- ACCOUNTS / PORTFOLIO ----------

    @abstractmethod
    def get_portfolios(self) -> List[Dict[str, Any]]:
        """
        Возвращает:
        [
            {
                "account_id": str,
                "balance": float
            }
        ]
        """
        pass

    # ---------- TRADES ----------

    @abstractmethod
    def get_trades(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Возвращает:
        [
            {
                "trade_id": str,
                "account_id": str,
                "ts": int,
                "symbol": str,
                "side": int,
                "qty": float,
                "price": float,
                "order_id": str
            }
        ]
        """
        pass

    # ---------- TRANSACTIONS ----------

    @abstractmethod
    def get_transactions(self, days: int = 7, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Возвращает:
        [
            {
                "id": str,
                "ts": int,
                "symbol": str,
                "category": str,
                "amount": float,
                "currency": str,
                "description": str
            }
        ]
        """
        pass

    # ---------- ORDERS ----------

    @abstractmethod
    def place_market_order(self, symbol: str, side: str, qty: float):
        """
        side: "BUY" | "SELL"
        """
        pass

    @abstractmethod
    def place_limit_order(self, symbol: str, side: str, qty: float, price: float):
        """
        side: "BUY" | "SELL"
        """
        pass

    @abstractmethod
    def cancel_order(self, order_id: str):
        pass

    # ---------- HEALTH ----------

    @abstractmethod
    def health_check(self) -> bool:
        """
        Проверка доступности брокера.
        """
        pass