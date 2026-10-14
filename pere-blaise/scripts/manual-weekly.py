#!/usr/bin/env python3
"""One operator-invoked weekly analysis; never enables the scheduler or calls range."""
from __future__ import annotations

import json
import os
from pathlib import Path

from pere_blaise.scheduler import run_once
from pere_blaise.slack_gateway import Slack
from pere_blaise.telegram_gateway import Gateway, Telegram


def main() -> int:
    config = json.loads(Path(os.environ['PB_CONFIG']).read_text())
    if config.get('weekly_enabled'):
        raise SystemExit('disable weekly scheduling before the manual test')
    if str(config['weekly_telegram_chat']) not in set(map(str, config['telegram_allowed_user_ids'])):
        raise SystemExit('weekly Telegram recipient is not allowlisted')
    if not config.get('slack_allowed_channel_id') or not config.get('weekly_owner'):
        raise SystemExit('weekly owner/channel missing')
    telegram = Telegram(Path(os.environ['PB_TELEGRAM_TOKEN_FILE']).read_text().strip())
    slack = Slack(Path(os.environ['PB_SLACK_BOT_TOKEN_FILE']).read_text().strip(),
                  Path(os.environ['PB_SLACK_APP_TOKEN_FILE']).read_text().strip())
    gateway = Gateway(config, telegram, Path('/app'), Path(os.environ['PB_PLANNER_ENV']))
    failures = run_once(gateway, telegram, slack, str(config['weekly_telegram_chat']),
                        config['slack_allowed_channel_id'], config['weekly_owner'])
    print(json.dumps({'manual_weekly': 'completed', 'channel_failures': sorted(failures)}, sort_keys=True))
    return 1 if failures else 0


if __name__ == '__main__':
    raise SystemExit(main())
