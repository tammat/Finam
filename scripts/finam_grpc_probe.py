#!/usr/bin/env python3
# scripts/finam_grpc_probe.py

"""
Пробник Finam gRPC:
- Auth(secret=FINAM_TOKEN) -> JWT
- TokenDetails(token=JWT)  -> проверка, срок действия, права
- GetAccount(account_id=FINAM_ACCOUNT_ID) -> базовая проверка аккаунта

ENV:
  FINAM_TOKEN        (обязательно) API token/secret
  FINAM_GRPC_HOST    (опц.) по умолчанию api.finam.ru:443
  FINAM_ACCOUNT_ID   (опц.) если задан — сделаем GetAccount
  JWT                (опц.) если задан — используем его, иначе сделаем Auth
"""

import json
import os
import sys
from pathlib import Path

import grpc


def jprint(obj):
    print(json.dumps(obj, ensure_ascii=False))


def _add_gen_to_syspath():
    # repo_root/scripts/finam_grpc_probe.py -> repo_root
    root = Path(__file__).resolve().parents[1]
    gen = root / "finam_bot" / "gen"
    sys.path.insert(0, str(gen))
    return gen


def _pick_field(msg_cls, preferred_names):
    names = {f.name for f in msg_cls.DESCRIPTOR.fields}
    for n in preferred_names:
        if n in names:
            return n
    return None


def _pick_token_from_auth_resp(resp):
    # 1) очевидные поля
    for n in ("jwt", "token", "access_token", "accessToken", "session", "session_token"):
        if hasattr(resp, n):
            v = getattr(resp, n)
            if isinstance(v, str) and v.count(".") == 2 and len(v) > 50:
                return v
    # 2) любое строковое поле с двумя точками
    for f in resp.DESCRIPTOR.fields:
        if f.type == f.TYPE_STRING:
            v = getattr(resp, f.name)
            if isinstance(v, str) and v.count(".") == 2 and len(v) > 50:
                return v
    return ""


def _grpc_err(e: grpc.RpcError):
    try:
        code = e.code().name
    except Exception:
        code = "UNKNOWN"
    try:
        details = e.details()
    except Exception:
        details = str(e)
    return code, details


def main():
    gen = _add_gen_to_syspath()

    host = os.getenv("FINAM_GRPC_HOST", "api.finam.ru:443").strip()
    api_token = (os.getenv("FINAM_TOKEN") or os.getenv("FINAM_API_KEY") or os.getenv("FINAM_SECRET") or "").strip()
    if not api_token:
        jprint({"ok": False, "stage": "env", "error": "FINAM_TOKEN is empty"})
        return 2

    # --- imports (после sys.path) ---
    try:
        from tradeapi.v1.auth import auth_service_pb2_grpc, auth_service_pb2
        from tradeapi.v1.accounts import accounts_service_pb2_grpc, accounts_service_pb2
    except Exception as e:
        jprint({"ok": False, "stage": "import", "gen": str(gen), "error": str(e)})
        return 2

    creds = grpc.ssl_channel_credentials()
    channel = grpc.secure_channel(host, creds)

    auth_stub = auth_service_pb2_grpc.AuthServiceStub(channel)
    accounts_stub = accounts_service_pb2_grpc.AccountsServiceStub(channel)

    # --- JWT ---
    jwt_env = (os.getenv("JWT") or "").strip()
    jwt = jwt_env.replace("\n", "").strip()
    jwt_from_env = bool(jwt)

    def do_auth():
        req_cls = getattr(auth_service_pb2, "AuthRequest", None)
        if not req_cls:
            jprint({"ok": False, "stage": "introspect", "error": "AuthRequest not found in auth_service_pb2"})
            return ""

        secret_field = _pick_field(req_cls, ["secret", "api_token", "apiToken", "token"])
        if not secret_field:
            jprint({
                "ok": False,
                "stage": "introspect",
                "error": "AuthRequest has no secret-like field",
                "fields": [f.name for f in req_cls.DESCRIPTOR.fields],
            })
            return ""

        req = req_cls(**{secret_field: api_token})
        try:
            resp = auth_stub.Auth(req, timeout=10)
        except grpc.RpcError as e:
            code, details = _grpc_err(e)
            jprint({"ok": False, "stage": "auth", "host": host, "code": code, "details": details})
            return ""

        new_jwt = _pick_token_from_auth_resp(resp)
        jprint({
            "ok": bool(new_jwt),
            "stage": "auth",
            "host": host,
            "jwt_len": len(new_jwt),
            "jwt_dots": new_jwt.count("."),
            "jwt_head": new_jwt[:16],
            "jwt_tail": new_jwt[-16:],
        })
        if not new_jwt:
            jprint({
                "ok": False,
                "stage": "auth_parse",
                "hint": "Не смогли вытащить JWT из AuthResponse",
                "resp_fields": [f.name for f in resp.DESCRIPTOR.fields],
            })
        return new_jwt

    if not jwt:
        jwt = do_auth()
        if not jwt:
            return 2

    # --- TokenDetails(token=JWT) ---
    td_req_cls = getattr(auth_service_pb2, "TokenDetailsRequest", None)
    if not td_req_cls:
        jprint({"ok": False, "stage": "introspect", "error": "TokenDetailsRequest not found"})
        return 2

    token_field = _pick_field(td_req_cls, ["token", "jwt"])
    if not token_field:
        jprint({
            "ok": False,
            "stage": "introspect",
            "error": "TokenDetailsRequest has no token-like field",
            "fields": [f.name for f in td_req_cls.DESCRIPTOR.fields],
        })
        return 2

    def token_details(current_jwt: str):
        td = auth_stub.TokenDetails(td_req_cls(**{token_field: current_jwt}), timeout=10)
        created = getattr(td, "created_at", None)
        expires = getattr(td, "expires_at", None)
        mdp = getattr(td, "md_permissions", [])
        jprint({
            "ok": True,
            "stage": "token_details",
            "host": host,
            "jwt_len": len(current_jwt),
            "jwt_dots": current_jwt.count("."),
            "created_at": str(created).strip() if created is not None else None,
            "expires_at": str(expires).strip() if expires is not None else None,
            "md_permissions_count": len(mdp) if hasattr(mdp, "__len__") else None,
        })
        return td

    try:
        token_details(jwt)
    except grpc.RpcError as e:
        code, details = _grpc_err(e)

        # Если JWT был из ENV и протух — автоматически делаем Auth и повторяем
        if jwt_from_env and "expired" in (details or "").lower():
            jprint({"ok": False, "stage": "token_details", "host": host, "code": code, "details": details, "hint": "JWT истёк, делаю Auth() заново"})
            jwt = do_auth()
            if not jwt:
                return 2
            try:
                token_details(jwt)
            except grpc.RpcError as e2:
                code2, details2 = _grpc_err(e2)
                jprint({"ok": False, "stage": "token_details", "host": host, "code": code2, "details": details2})
                return 2
        else:
            jprint({"ok": False, "stage": "token_details", "host": host, "code": code, "details": details})
            return 2

    # --- GetAccount(account_id=...) ---
    account_id = (os.getenv("FINAM_ACCOUNT_ID") or "").strip()
    if not account_id:
        req_cls = getattr(accounts_service_pb2, "GetAccountRequest", None)
        fields = [f.name for f in req_cls.DESCRIPTOR.fields] if req_cls else []
        jprint({
            "ok": True,
            "stage": "need_account_id",
            "hint": "Задай FINAM_ACCOUNT_ID и повтори запуск",
            "get_account_request": {"name": "GetAccountRequest", "fields": fields},
        })
        return 0

    ga_req_cls = getattr(accounts_service_pb2, "GetAccountRequest", None)
    if not ga_req_cls:
        jprint({"ok": False, "stage": "introspect", "error": "GetAccountRequest not found"})
        return 2

    acc_field = _pick_field(ga_req_cls, ["account_id", "accountId", "account", "id"])
    if not acc_field:
        jprint({
            "ok": False,
            "stage": "introspect",
            "error": "GetAccountRequest has no account id field",
            "fields": [f.name for f in ga_req_cls.DESCRIPTOR.fields],
        })
        return 2

    greq = ga_req_cls(**{acc_field: account_id})

    # Важно: auth токен идёт в metadata
    md = [("authorization", f"Bearer {jwt}")]

    try:
        resp = accounts_stub.GetAccount(greq, metadata=md, timeout=10)
        out = {
            "ok": True,
            "stage": "get_account",
            "host": host,
            "md_used": "authorization",
            "account_id": account_id,
        }
        for k in ("status", "type", "currency", "market", "name"):
            if hasattr(resp, k):
                out[k] = str(getattr(resp, k))
        if len(out) == 5:
            out["resp_fields"] = [f.name for f in resp.DESCRIPTOR.fields][:12]
        jprint(out)
        return 0
    except grpc.RpcError as e:
        code, details = _grpc_err(e)
        jprint({
            "ok": False,
            "stage": "get_account",
            "host": host,
            "code": code,
            "details": details,
            "hint": "Проверь FINAM_ACCOUNT_ID и что JWT свежий; токен должен быть в metadata authorization",
        })
        return 2


if __name__ == "__main__":
    raise SystemExit(main())