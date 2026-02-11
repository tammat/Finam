# scripts/fix_grpc_imports.py
from __future__ import annotations

from pathlib import Path

ROOT = Path("finam_bot/grpc_api")
if not ROOT.exists():
    raise SystemExit("finam_bot/grpc_api not found")

REPLACEMENTS = [
    ("from grpc.tradeapi", "from finam_bot.grpc_api.grpc.tradeapi"),
    ("import grpc.tradeapi", "import finam_bot.grpc_api.grpc.tradeapi"),
]

changed = 0
for p in ROOT.rglob("*.py"):
    txt = p.read_text(encoding="utf-8")
    new = txt
    for a, b in REPLACEMENTS:
        new = new.replace(a, b)
    if new != txt:
        p.write_text(new, encoding="utf-8")
        changed += 1

print(f"Imports fixed. files_changed={changed}")