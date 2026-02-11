import pathlib

ROOT = pathlib.Path("finam_bot/grpc_api")

for file in ROOT.rglob("*.py"):
    text = file.read_text()

    # Fix imports to our namespace
    text = text.replace(
        "from grpc.tradeapi",
        "from finam_bot.grpc_api.grpc.tradeapi"
    )

    text = text.replace(
        "import grpc.tradeapi",
        "import finam_bot.grpc_api.grpc.tradeapi"
    )

    file.write_text(text)

print("All grpc imports fixed.")