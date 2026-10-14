"""Durable, at-most-once guard for channel events on the broker's private volume."""
from __future__ import annotations

import os
import sqlite3
from contextlib import closing
from datetime import datetime, timedelta, timezone
from pathlib import Path


class IngressLedger:
    def __init__(self, runtime_dir: Path, retention_days: int = 30) -> None:
        if retention_days < 1:
            raise ValueError('retention_days must be positive')
        runtime_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.database = runtime_dir / 'ingress.sqlite3'
        self.retention_days = retention_days
        with closing(self._connect()) as connection, connection:
            connection.execute('''CREATE TABLE IF NOT EXISTS events (
                channel TEXT NOT NULL, event_id TEXT NOT NULL, received_at TEXT NOT NULL,
                completed_at TEXT, PRIMARY KEY (channel, event_id))''')
        os.chmod(self.database, 0o600)

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database, timeout=10)
        connection.execute('PRAGMA synchronous = FULL')
        return connection

    def begin(self, channel: str, event_id: str) -> bool:
        if channel not in ('telegram', 'slack') or not event_id:
            raise ValueError('invalid ingress event')
        now = datetime.now(timezone.utc)
        cutoff = (now - timedelta(days=self.retention_days)).isoformat()
        with closing(self._connect()) as connection, connection:
            connection.execute('DELETE FROM events WHERE received_at < ? AND completed_at IS NOT NULL', (cutoff,))
            cursor = connection.execute(
                'INSERT OR IGNORE INTO events (channel, event_id, received_at) VALUES (?, ?, ?)',
                (channel, event_id, now.isoformat()))
            return cursor.rowcount == 1

    def complete(self, channel: str, event_id: str) -> None:
        with closing(self._connect()) as connection, connection:
            connection.execute('UPDATE events SET completed_at = ? WHERE channel = ? AND event_id = ?',
                               (datetime.now(timezone.utc).isoformat(), channel, event_id))
