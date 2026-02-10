from finam_bot.signals.registry import STRATEGIES


def main():
    symbol = "NG-2.26"
    last_price = 3.11

    for strat in STRATEGIES:
        sig = strat.detect(symbol, last_price)
        if sig:
            print("SIGNAL:", sig)
            return

    print("No signals")


if __name__ == "__main__":
    main()