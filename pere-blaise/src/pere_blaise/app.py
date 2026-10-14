"""Combined broker and channel relays for the isolated application container."""
from __future__ import annotations

import json
import os
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

from .scheduler import WeeklyScheduler, run_once
from .slack_gateway import Slack, SlackGateway, run as run_slack
from .telegram_gateway import Gateway, Telegram


def main() -> int:
    os.umask(0o077)
    config = json.loads(Path(os.environ['PB_CONFIG']).read_text())
    token = Path(os.environ['PB_TELEGRAM_TOKEN_FILE']).read_text().strip()
    bot = Telegram(token)
    planner_env = Path(os.environ['PB_PLANNER_ENV'])
    project = Path('/app')
    gateway = Gateway(config, bot, project, planner_env)
    state = Path(config['runtime_dir'])
    scheduler = WeeklyScheduler(Path(config['database']), config.get('weekly_enabled', False))
    slack_token = Path(os.environ['PB_SLACK_BOT_TOKEN_FILE']).read_text().strip()
    app_token = Path(os.environ['PB_SLACK_APP_TOKEN_FILE']).read_text().strip()
    slack = Slack(slack_token, app_token)
    slack_gateway = SlackGateway(config, slack, project, planner_env,
                                 config['slack_allowed_channel_id'], set(map(str, config['slack_allowed_user_ids'])))
    import websocket
    threading.Thread(target=run_slack, args=(slack_gateway, websocket.create_connection), daemon=True).start()
    def weekly_loop():
        while True:
            try:
                if scheduler.claim(datetime.now(timezone.utc)):
                    failures = run_once(gateway, bot, slack, str(config['weekly_telegram_chat']),
                                        config['slack_allowed_channel_id'], config['weekly_owner'])
                    if failures:
                        print(json.dumps({'code': 'PB-CHANNEL-FAILED', 'failures': failures}), file=sys.stderr, flush=True)
                (state / 'heartbeat').touch()
            except Exception as exc:
                print(json.dumps({'code': 'PB-CHANNEL-FAILED', 'error_type': type(exc).__name__}), file=sys.stderr, flush=True)
            time.sleep(30)
    threading.Thread(target=weekly_loop, daemon=True).start()
    offset_file = state / 'telegram-offset'
    offset = int(offset_file.read_text()) if offset_file.exists() else 0
    while True:
        try:
            updates = bot.call('getUpdates', {'offset': offset, 'timeout': 30, 'allowed_updates': '["message"]'})
            for update in updates if isinstance(updates, list) else []:
                if isinstance(update.get('update_id'), int):
                    offset = max(offset, update['update_id'] + 1)
                    offset_file.write_text(str(offset))
                    offset_file.chmod(0o600)
                if isinstance(update.get('message'), dict):
                    gateway.handle(update['message'])
        except KeyboardInterrupt:
            return 0
        except Exception:
            time.sleep(5)

if __name__ == '__main__':
    raise SystemExit(main())
