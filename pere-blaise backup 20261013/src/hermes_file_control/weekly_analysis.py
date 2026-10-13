"""One-shot, non-destructive weekly analysis for launchd."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .telegram_gateway import Gateway, Telegram, _env_value, _user_error


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--broker-config", type=Path, required=True)
    parser.add_argument("--telegram-env", type=Path, required=True)
    parser.add_argument("--planner-env", type=Path, required=True)
    args = parser.parse_args()
    config = json.loads(args.broker_config.read_text(encoding="utf-8"))
    owners = list(map(str, config["telegram_allowed_user_ids"]))
    if len(owners) != 1:
        raise ValueError("weekly analysis requires exactly one authorized Telegram owner")
    telegram = Telegram(_env_value(args.telegram_env, "TELEGRAM_BOT_TOKEN"))
    gateway = Gateway(config, telegram, Path(__file__).resolve().parents[2], args.planner_env)
    try:
        telegram.message(owners[0], "Analyse hebdomadaire\n" + gateway._analyse(owners[0]))
    except Exception as exc:
        telegram.message(owners[0], "Analyse hebdomadaire : " + _user_error(exc))
        raise
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
