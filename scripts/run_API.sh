export PYTHONPATH="$PWD/finam_bot/gen:$PWD"
export FINAM_GRPC_HOST="api.finam.ru:443"
export FINAM_ACCOUNT_ID="1943312"
source ~/.config/finam/env   # там FINAM_TOKEN
# JWT можно не ставить — скрипт сам обновит через REST при пустом JWT

python scripts/pull_last7d.py
python scripts/export_csv.py