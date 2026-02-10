from __future__ import annotations

import os
import json
import time
from typing import Any, Iterable, List, Optional, Tuple

import grpc
import requests
from google.protobuf.timestamp_pb2 import Timestamp

from tradeapi.v1.auth import auth_service_pb2, auth_service_pb2_grpc
from tradeapi.v1.accounts import accounts_service_pb2, accounts_service_pb2_grpc


def _ts_from_unix(sec: int) -> Timestamp:
    ts = Timestamp()
    ts.seconds = int(sec)
    ts.nanos = 0
    return ts


def _set_if_has(msg: Any, field: str, value: Any) -> bool:
    if not hasattr(msg, field):
        return False
    try:
        setattr(msg, field, value)
        return True
    except Exception:
        return False


def _set_ts(msg: Any, field: str, ts: Timestamp) -> bool:
    if not hasattr(msg, field):
        return False
    try:
        sub = getattr(msg, field)
        if hasattr(sub, "CopyFrom"):
            sub.CopyFrom(ts)
            return True
        setattr(msg, field, int(ts.seconds))
        return True
    except Exception:
        return False


class FinamClient:
    def __init__(
        self,
        host: Optional[str] = None,
        secret: Optional[str] = None,
        jwt: Optional[str] = None,
        account_id: Optional[str] = None,
        timeout: float = 10.0,
    ):
        self.host = host or os.getenv("FINAM_GRPC_HOST", "api.finam.ru:443")
        self.secret = secret if secret is not None else os.getenv("FINAM_TOKEN", "")
        self.jwt = jwt if jwt is not None else os.getenv("JWT", "")
        self.account_id = account_id if account_id is not None else os.getenv("FINAM_ACCOUNT_ID", "")
        self.timeout = float(timeout)

        self._channel = grpc.secure_channel(self.host, grpc.ssl_channel_credentials())
        self.auth_stub = auth_service_pb2_grpc.AuthServiceStub(self._channel)
        self.accounts_stub = accounts_service_pb2_grpc.AccountsServiceStub(self._channel)

    @classmethod
    def from_env(cls) -> "FinamClient":
        return cls()

    @staticmethod
    def _looks_like_jwt(tok: str) -> bool:
        return bool(tok) and tok.count(".") == 2 and len(tok) > 50

    def _md(self) -> List[Tuple[str, str]]:
        if self._looks_like_jwt(self.jwt):
            return [("authorization", f"Bearer {self.jwt}")]
        return []

    def refresh_jwt_via_rest(self) -> str:
        if not self.secret:
            raise RuntimeError("FINAM_TOKEN is empty (can't refresh JWT)")

        url = "https://api.finam.ru/v1/sessions"
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json; charset=utf-8",
        }
        payload = {"secret": self.secret}

        r = requests.post(url, headers=headers, data=json.dumps(payload), allow_redirects=True, timeout=15)
        ct = (r.headers.get("content-type") or "").lower()

        if r.status_code >= 400:
            raise RuntimeError(f"REST /v1/sessions failed http={r.status_code} ct={ct} body_head={r.text[:160]!r}")
        if "application/json" not in ct:
            raise RuntimeError(f"REST /v1/sessions non-json ct={ct} body_head={r.text[:160]!r}")

        tok = (r.json() or {}).get("token") or ""
        if tok.count(".") != 2:
            raise RuntimeError(f"Bad JWT format (dots={tok.count('.')})")

        self.jwt = tok
        return tok

    def ensure_jwt(self) -> str:
        if self._looks_like_jwt(self.jwt):
            return self.jwt
        # JWT нет/битый → пробуем получить по секрету
        return self.refresh_jwt_via_rest()

    def _is_auth_error(self, e: Exception) -> bool:
        if not isinstance(e, grpc.RpcError):
            return False
        details = (e.details() or "") if hasattr(e, "details") else str(e)
        d = details.lower()
        return (
            "unauthenticated" in d
            or "missing auth token" in d
            or "token is expired" in d
            or "expected to have 3 parts" in d
            or "jwt token check failed" in d
        )

    def _call_with_one_refresh(self, fn, *args, require_jwt: bool = False, **kwargs):
        try:
            return fn(*args, **kwargs)
        except Exception as e:
            if require_jwt and self.secret:
                # если JWT обязателен — обновим и повторим
                self.ensure_jwt()
                return fn(*args, **kwargs)
            if self._is_auth_error(e) and self.secret:
                self.ensure_jwt()
                return fn(*args, **kwargs)
            raise

    # ---------- RPC ----------
    def token_details(self) -> auth_service_pb2.TokenDetailsResponse:
        # Тут JWT ФАКТИЧЕСКИ нужен, потому что сервер валидирует request.token
        jwt = self.ensure_jwt()

        req = auth_service_pb2.TokenDetailsRequest()
        # У финама это обычно поле token (иногда jwt) — заполним то, что есть
        if not (_set_if_has(req, "token", jwt) or _set_if_has(req, "jwt", jwt)):
            # если внезапно нет полей — всё равно попробуем только metadata
            pass

        return self._call_with_one_refresh(
            self.auth_stub.TokenDetails,
            req,
            metadata=self._md(),
            timeout=self.timeout,
            require_jwt=True,
        )

    def get_account(self, account_id: Optional[str] = None) -> accounts_service_pb2.GetAccountResponse:
        self.ensure_jwt()
        aid = str(account_id or self.account_id or "")
        if not aid:
            raise RuntimeError("FINAM_ACCOUNT_ID is empty")

        req = accounts_service_pb2.GetAccountRequest()
        _set_if_has(req, "account_id", aid)

        return self._call_with_one_refresh(
            self.accounts_stub.GetAccount,
            req,
            metadata=self._md(),
            timeout=self.timeout,
            require_jwt=True,
        )

    def _build_interval(self, req: Any, since_unix: int, limit: int) -> None:
        _set_if_has(req, "limit", int(limit))
        if not hasattr(req, "interval"):
            return
        interval = getattr(req, "interval")
        ts_from = _ts_from_unix(since_unix)
        ts_to = _ts_from_unix(int(time.time()))
        for name in ("from", "from_time", "start", "start_time", "date_from", "time_from"):
            _set_ts(interval, name, ts_from)
        for name in ("to", "to_time", "end", "end_time", "date_to", "time_to"):
            _set_ts(interval, name, ts_to)

    def fetch_trades(self, account_id: str, since, limit: int = 1000) -> Iterable[Any]:
        self.ensure_jwt()
        req = accounts_service_pb2.TradesRequest()
        _set_if_has(req, "account_id", str(account_id))
        self._build_interval(req, int(since.timestamp()), limit)

        resp = self._call_with_one_refresh(
            self.accounts_stub.Trades,
            req,
            metadata=self._md(),
            timeout=self.timeout,
            require_jwt=True,
        )
        return list(resp.trades) if hasattr(resp, "trades") else []

    def fetch_transactions(self, account_id: str, since, limit: int = 1000) -> Iterable[Any]:
        self.ensure_jwt()
        req = accounts_service_pb2.TransactionsRequest()
        _set_if_has(req, "account_id", str(account_id))
        self._build_interval(req, int(since.timestamp()), limit)

        resp = self._call_with_one_refresh(
            self.accounts_stub.Transactions,
            req,
            metadata=self._md(),
            timeout=self.timeout,
            require_jwt=True,
        )
        return list(resp.transactions) if hasattr(resp, "transactions") else []
