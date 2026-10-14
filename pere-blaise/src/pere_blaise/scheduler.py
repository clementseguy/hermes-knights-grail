"""Disabled-by-default Sunday scheduler with local timezone and week idempotence."""
from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta
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
        if now.tzinfo is None:
            raise ValueError('timezone-aware clock required')
        local = now.astimezone(ZoneInfo('Europe/Paris'))
        sunday = (local - timedelta(days=(local.weekday() + 1) % 7)).date()
        deadline = datetime(sunday.year, sunday.month, sunday.day, 17, tzinfo=ZoneInfo('Europe/Paris'))
        return deadline <= local < deadline + timedelta(hours=24)

    def claim(self, now: datetime) -> bool:
        if not self.due(now):
            return False
        local = now.astimezone(ZoneInfo('Europe/Paris'))
        sunday = (local - timedelta(days=(local.weekday() + 1) % 7)).date()
        week = sunday.isoformat()
        with sqlite3.connect(self.database) as db:
            return db.execute('INSERT OR IGNORE INTO weekly_runs VALUES (?, ?)', (week, local.isoformat())).rowcount == 1


def run_once(gateway, telegram, slack, telegram_chat: str, slack_channel: str, owner: str) -> dict[str, str]:
    failures: dict[str, str] = {}
    for name, send in [('telegram', lambda text: telegram.message(telegram_chat, text)),
                       ('slack', lambda text: slack.call('chat.postMessage', {'channel': slack_channel, 'text': text}))]:
        try:
            send('Analyse hebdomadaire démarrée.')
        except Exception as exc:
            from .errors import incident
            incident('PB-CHANNEL-FAILED', stage='weekly-' + name + '-start', exc=exc)
            failures[name + '_start'] = 'PB-CHANNEL-FAILED'
    try:
        result = gateway._analyse(owner)
    except Exception as exc:
        from .errors import user_message
        result = user_message('PB-MODEL-UNAVAILABLE', stage='analyse', exc=exc)
    for name, send in [('telegram', lambda text: telegram.message(telegram_chat, text)),
                       ('slack', lambda text: slack.call('chat.postMessage', {'channel': slack_channel, 'text': text}))]:
        try:
            send(result)
        except Exception as exc:
            from .errors import incident
            incident('PB-CHANNEL-FAILED', stage='weekly-' + name + '-result', exc=exc)
            failures[name + '_result'] = 'PB-CHANNEL-FAILED'
    return failures
