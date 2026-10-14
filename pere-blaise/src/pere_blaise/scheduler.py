"""Disabled-by-default Sunday scheduler with local timezone and week idempotence."""
from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


class WeeklyScheduler:
    def __init__(self, database: Path, enabled: bool = False):
        self.database, self.enabled = database, enabled
        with sqlite3.connect(database) as db:
            db.execute('CREATE TABLE IF NOT EXISTS weekly_runs (week TEXT PRIMARY KEY, started_at TEXT NOT NULL)')

    def due(self, now: datetime) -> bool:
        if not self.enabled:
            return False
        local = now.astimezone(ZoneInfo('Europe/Paris'))
        return local.weekday() == 6 and local.hour == 17

    def claim(self, now: datetime) -> bool:
        if not self.due(now):
            return False
        local = now.astimezone(ZoneInfo('Europe/Paris'))
        week = f'{local.isocalendar().year}-{local.isocalendar().week:02d}'
        with sqlite3.connect(self.database) as db:
            return db.execute('INSERT OR IGNORE INTO weekly_runs VALUES (?, ?)', (week, local.isoformat())).rowcount == 1


def run_once(gateway, telegram, slack, telegram_chat: str, slack_channel: str, owner: str) -> dict[str, str]:
    failures: dict[str, str] = {}
    for name, send in [('telegram', lambda text: telegram.message(telegram_chat, text)),
                       ('slack', lambda text: slack.call('chat.postMessage', {'channel': slack_channel, 'text': text}))]:
        try:
            send('Analyse hebdomadaire démarrée.')
        except Exception:
            failures[name + '_start'] = 'PB-CHANNEL-FAILED'
    try:
        result = gateway._analyse(owner)
    except Exception:
        result = 'PB-MODEL-UNAVAILABLE — Analyse échouée.'
    for name, send in [('telegram', lambda text: telegram.message(telegram_chat, text)),
                       ('slack', lambda text: slack.call('chat.postMessage', {'channel': slack_channel, 'text': text}))]:
        try:
            send(result)
        except Exception:
            failures[name + '_result'] = 'PB-CHANNEL-FAILED'
    return failures
