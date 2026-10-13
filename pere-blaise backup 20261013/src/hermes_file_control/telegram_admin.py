"""Restricted administrative actions for the single Telegram bot."""
from __future__ import annotations

import argparse
import unicodedata
from pathlib import Path

from .telegram_gateway import Telegram, _env_value


def _name(value: str) -> str:
    if not 1 <= len(value) <= 64 or any(unicodedata.category(char).startswith("C") for char in value):
        raise ValueError("name must contain 1 to 64 visible characters")
    return value


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--telegram-env", type=Path, required=True)
    parser.add_argument("action", nargs="?")
    parser.add_argument("--name")
    args = parser.parse_args()
    if args.action != "set-name" or args.name is None:
        parser.error("the only supported action is: set-name --name NAME")
    name = _name(args.name)
    telegram = Telegram(_env_value(args.telegram_env, "TELEGRAM_BOT_TOKEN"))
    telegram.call("setMyName", {"name": name})
    print("Telegram display name updated:", telegram.call("getMyName").get("name", ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
