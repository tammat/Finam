#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

rm -rf finam_bot/gen
mkdir -p finam_bot/gen

python -m grpc_tools.protoc \
  -I proto_src \
  -I vendor/googleapis \
  --python_out=finam_bot/gen \
  --grpc_python_out=finam_bot/gen \
  $(find proto_src/tradeapi -name '*.proto')

# __init__.py в каждую папку (чтобы импорты работали)
find finam_bot/gen -type d -exec sh -c 'test -f "$1/__init__.py" || : > "$1/__init__.py"' _ {} \;