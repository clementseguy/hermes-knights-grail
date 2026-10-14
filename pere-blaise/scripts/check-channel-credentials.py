#!/usr/bin/env python3
"""Audit existing channel credentials without printing tokens or response bodies."""
from __future__ import annotations

import argparse
import json
import re
import stat
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen


def secret(path: Path) -> str:
    if path.is_symlink() or not path.is_file() or stat.S_IMODE(path.stat().st_mode) & 0o077:
        raise ValueError('credential file absent or permissions too broad')
    value = path.read_text(encoding='utf-8').strip()
    if not value or '\n' in value or '\r' in value:
        raise ValueError('credential file empty or malformed')
    return value


def request_json(url: str, token: str | None = None) -> tuple[dict, set[str]]:
    headers = {'Authorization': 'Bearer ' + token} if token else {}
    request = Request(url, data=b'', headers=headers, method='POST')
    with urlopen(request, timeout=15) as response:  # nosec: fixed API origins below
        result = json.load(response)
        scopes = set(filter(None, response.headers.get('x-oauth-scopes', '').split(',')))
    if not isinstance(result, dict):
        raise ValueError('malformed API response')
    return result, scopes


def safe_error(result: dict) -> str:
    value = result.get('error')
    return value if isinstance(value, str) and re.fullmatch(r'[a-z_]{1,60}', value) else 'unavailable'


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('private_dir', type=Path)
    parser.add_argument('--telegram-username', default='hermes_eztkiqpkemtowx7b_bot')
    args = parser.parse_args()
    private = args.private_dir.resolve(strict=True)
    if stat.S_IMODE(private.stat().st_mode) & 0o077:
        raise SystemExit('private directory permissions too broad')
    try:
        telegram = secret(private / 'telegram.token')
        slack_bot = secret(private / 'slack-bot.token')
        slack_app = secret(private / 'slack-app.token')
        if not re.fullmatch(r'\d+:[A-Za-z0-9_-]+', telegram):
            raise ValueError('Telegram token shape invalid')
        if not slack_bot.startswith('xoxb-') or not slack_app.startswith('xapp-'):
            raise ValueError('Slack token shape invalid')
        me, _ = request_json('https://api.telegram.org/bot' + telegram + '/getMe')
        identity = me.get('result', {}) if me.get('ok') else {}
        print('telegram_identity:', identity.get('username') if isinstance(identity, dict) else 'unavailable')
        webhook, _ = request_json('https://api.telegram.org/bot' + telegram + '/getWebhookInfo')
        info = webhook.get('result', {}) if webhook.get('ok') else {}
        print('telegram_webhook_configured:', bool(info.get('url')) if isinstance(info, dict) else 'unavailable')
        print('telegram_pending_updates:', info.get('pending_update_count') if isinstance(info, dict) else 'unavailable')
        bot_auth, bot_scopes = request_json('https://slack.com/api/auth.test', slack_bot)
        print('slack_bot_auth:', bool(bot_auth.get('ok')))
        if not bot_auth.get('ok'):
            print('slack_bot_error:', safe_error(bot_auth))
        print('slack_bot_scopes:', ','.join(sorted(bot_scopes)) if bot_scopes else 'unavailable')
        missing_bot_scopes = {'app_mentions:read', 'chat:write', 'files:write'} - bot_scopes
        print('slack_bot_missing_scopes:', ','.join(sorted(missing_bot_scopes)) or 'none')
        connection, app_scopes = request_json('https://slack.com/api/apps.connections.open', slack_app)
        socket = urlparse(connection.get('url', '')) if connection.get('ok') else None
        host = socket.hostname if socket and socket.scheme == 'wss' else None
        print('slack_app_auth:', bool(connection.get('ok')))
        if not connection.get('ok'):
            print('slack_app_error:', safe_error(connection))
        print('slack_websocket_host:', host if host and host.endswith('.slack.com') else 'unavailable')
        print('slack_app_scopes:', ','.join(sorted(app_scopes)) if app_scopes else 'unavailable')
        return 0 if (identity.get('username') == args.telegram_username and webhook.get('ok')
                     and not info.get('url') and bot_auth.get('ok') and not missing_bot_scopes
                     and connection.get('ok') and host and host.endswith('.slack.com')
                     and 'connections:write' in app_scopes) else 1
    except Exception as exc:
        # HTTP errors can contain the Telegram token in their URL. Never print
        # their message, traceback, request or response body.
        print('credential_check_failed:', type(exc).__name__)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
