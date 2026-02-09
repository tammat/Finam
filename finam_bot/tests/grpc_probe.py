#!/usr/bin/env python3
"""
Мини‑probe для Finam Trade API по gRPC:
- берет FINAM_TOKEN из окружения
- дергает AuthService.TokenDetails (проверка токена)
- печатает короткий JSON: ok/ошибка + пару полей

Требования:
  pip install grpcio grpcio-tools protobuf
  Сгенерированные *_pb2.py и *_pb2_grpc.py из proto Trade API должны быть в PYTHONPATH.

Как сгенерировать proto (пример):
  git clone https://github.com/Ruvad39/go-finam-grpc
  cd go-finam-grpc
  python -m pip install -U grpcio grpcio-tools protobuf
  python -m grpc_tools.protoc \
    -I proto \
    --python_out . \
    --grpc_python_out . \
    proto/grpc/tradeapi/v1/*.proto

После этого:
  export PYTHONPATH="$PWD:$PYTHONPATH"
  export FINAM_TOKEN="..."
  python grpc_probe.py
"""
from __future__ import annotations

import json
import os
import sys
import time
from typing import Dict, Any

import grpc

# ожидаем, что эти модули будут после генерации из proto
try:
    from proto.grpc.tradeapi.v1 import auth_pb2, auth_pb2_grpc  # type: ignore
except Exception as e:  # pragma: no cover
    print(json.dumps({
        "ok": False,
        "error": "PROTO_NOT_FOUND",
        "details": "Не найдены сгенерированные модули proto.grpc.tradeapi.v1.auth_pb2(_grpc). "
                   "Сгенерируй их командой из докстринга.",
        "exc": str(e),
    }, ensure_ascii=False))
    sys.exit(2)


HOST = os.getenv("FINAM_GRPC_HOST", "trade-api.finam.ru:443")


def main() -> int:
    token = os.getenv("FINAM_TOKEN", "").strip()
    if not token:
        print(json.dumps({"ok": False, "error": "FINAM_TOKEN_EMPTY"}, ensure_ascii=False))
        return 2

    # gRPC TLS канал
    creds = grpc.ssl_channel_credentials()
    t0 = time.time()
    try:
        with grpc.secure_channel(HOST, creds) as ch:
            stub = auth_pb2_grpc.AuthServiceStub(ch)

            # В Finam Trade API токен передается как Bearer
            md = (("authorization", f"Bearer {token}"),)

            # TokenDetailsRequest чаще всего пустой
            req = auth_pb2.TokenDetailsRequest()
            res = stub.TokenDetails(req, metadata=md, timeout=10.0)

        dt_ms = int((time.time() - t0) * 1000)
        out: Dict[str, Any] = {
            "ok": True,
            "host": HOST,
            "latency_ms": dt_ms,
        }

        # Поля зависят от proto. Выводим несколько самых полезных, если есть.
        for k in ("type", "scope", "exp", "key_id", "created", "renew_exp", "jti", "provider"):
            if hasattr(res, k):
                out[k] = getattr(res, k)

        print(json.dumps(out, ensure_ascii=False))
        return 0

    except grpc.RpcError as e:
        dt_ms = int((time.time() - t0) * 1000)
        print(json.dumps({
            "ok": False,
            "host": HOST,
            "latency_ms": dt_ms,
            "error": "GRPC",
            "code": getattr(e, "code")().name if hasattr(e, "code") else None,
            "details": getattr(e, "details")() if hasattr(e, "details") else str(e),
        }, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
