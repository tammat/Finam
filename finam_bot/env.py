# finam_bot/env.py
from __future__ import annotations

from dotenv import load_dotenv, find_dotenv


def load_env() -> None:
    """
    Грузим .env, но НЕ перезаписываем реальные переменные окружения.
    Приоритет:
      1) export FINAM_... в shell / CI / systemd
      2) .env (дефолты)
    """
    load_dotenv(find_dotenv(usecwd=True), override=False)