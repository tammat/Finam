#!/usr/bin/env bash
set -e

echo "=== CLEAN OLD GENERATED ==="
rm -rf finam_bot/grpc_api

echo "=== CLONE TEMP REPOS ==="
rm -rf .grpc_tmp
mkdir .grpc_tmp
cd .grpc_tmp

git clone --depth 1 https://github.com/FinamWeb/finam-trade-api.git
git clone --depth 1 https://github.com/googleapis/googleapis.git

cd ..

echo "=== GENERATE PROTO ==="
mkdir -p finam_bot/grpc_api

python -m grpc_tools.protoc \
  -I=.grpc_tmp/finam-trade-api/proto \
  -I=.grpc_tmp/googleapis \
  --python_out=finam_bot/grpc_api \
  --grpc_python_out=finam_bot/grpc_api \
  $(find .grpc_tmp/finam-trade-api/proto/grpc/tradeapi/v1 -name "*.proto" \
    | grep -v "/metrics/")

echo "=== FIX PACKAGE INIT FILES ==="
find finam_bot/grpc_api -type d -exec touch {}/__init__.py \;

echo "=== FIX IMPORTS (avoid grpc namespace conflict) ==="

find finam_bot/grpc_api -type f -name "*_pb2*.py" -exec sed -i '' \
  's/from grpc.tradeapi/from finam_bot.grpc_api.grpc.tradeapi/g' {} \;

echo "=== CLEAN TMP ==="
rm -rf .grpc_tmp

echo "=== DONE ==="