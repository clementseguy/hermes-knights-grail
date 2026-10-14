#!/usr/bin/env python3
"""Fail closed before Compose start; never display secret values."""
from __future__ import annotations
import json
import os
import stat
import sys
from pathlib import Path

private = Path(sys.argv[1]).resolve(strict=True)
if stat.S_IMODE(private.stat().st_mode) & 0o077:
    raise SystemExit('private directory permissions too broad')
for name in ('telegram.token', 'slack-bot.token', 'slack-app.token', 'planner.env', 'planner-api.env', 'broker.json'):
    path = private / name
    if path.is_symlink() or not path.is_file() or not path.stat().st_size or stat.S_IMODE(path.stat().st_mode) & 0o077:
        raise SystemExit('private file missing or permissions too broad: ' + name)
config = json.loads((private / 'broker.json').read_text())
if not config.get('telegram_allowed_user_ids') or not config.get('slack_allowed_user_ids') or not config.get('slack_allowed_channel_id'):
    raise SystemExit('channel allowlists incomplete')
principals = {'telegram:' + str(x) for x in config['telegram_allowed_user_ids']} | {'slack:' + str(x) for x in config['slack_allowed_user_ids']}
mapping = config.get('identity_map', {})
if not isinstance(mapping, dict) or not set(mapping).issubset(principals) or any(not isinstance(v, str) or not v for v in mapping.values()):
    raise SystemExit('invalid private identity map')
if config.get('weekly_enabled'):
    marker = private / 'weekly-approval.json'
    if not marker.is_file() or stat.S_IMODE(marker.stat().st_mode) & 0o077:
        raise SystemExit('weekly task requires private approval record after a manual test')
    approval = json.loads(marker.read_text())
    if approval.get('approved_by') != config.get('weekly_owner') or not approval.get('manual_test_at'):
        raise SystemExit('weekly approval owner/test evidence mismatch')
    if str(config.get('weekly_telegram_chat')) not in set(map(str, config['telegram_allowed_user_ids'])):
        raise SystemExit('weekly Telegram chat is not allowlisted')
    if config.get('weekly_owner') not in principals | set(mapping.values()):
        raise SystemExit('weekly owner is not authorized')
for key in ('downloads', 'documents', 'backups', 'database', 'runtime_dir'):
    if not isinstance(config.get(key), str) or not config[key].startswith('/'):
        raise SystemExit('invalid config path: ' + key)
if [config['downloads'], config['documents'], config['backups'], config['database'], config['runtime_dir']] != ['/downloads','/documents','/backups','/state/plans.sqlite3','/state']:
    raise SystemExit('container paths must match the isolated compose mounts')
for key, maximum in [('sha256_max_bytes', 10**10), ('send_max_bytes', 10**9), ('max_files', 10000),
                     ('max_directories', 10000), ('analysis_timeout_sec', 600)]:
    value = config.get(key)
    if not isinstance(value, int) or not 1 <= value <= maximum:
        raise SystemExit('invalid resource limit: ' + key)
if config.get('planner_endpoint', 'http://pere-blaise:8642') != 'http://pere-blaise:8642':
    raise SystemExit('planner endpoint must be the internal Compose service')
planner_key = None
for line in (private / 'planner.env').read_text().splitlines():
    if line.startswith('PERE_BLAISE_API_KEY='):
        planner_key = line.split('=', 1)[1]
api_key = None
for line in (private / 'planner-api.env').read_text().splitlines():
    if line.startswith('API_SERVER_KEY='):
        api_key = line.split('=', 1)[1]
if not planner_key or planner_key != api_key or len(api_key) < 32:
    raise SystemExit('internal API key absent, weak or mismatched')
print('Private configuration shape and permissions: OK')
