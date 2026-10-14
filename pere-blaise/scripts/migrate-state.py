#!/usr/bin/env python3
"""Offline, reversible broker schema marker migration; never touches learning rows."""
from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


def integrity(connection: sqlite3.Connection) -> None:
    if connection.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
        raise RuntimeError('SQLite integrity_check failed')


def no_active_work(connection: sqlite3.Connection, state: Path) -> None:
    try:
        active = connection.execute("SELECT count(*) FROM plans WHERE state='applying'").fetchone()[0]
    except sqlite3.OperationalError:
        active = 0
    if active:
        raise RuntimeError('applying plan blocks schema change')
    for path in state.glob('*.journal.json'):
        if json.loads(path.read_text()).get('state') in ('PREPARING', 'BACKUPS_VERIFIED', 'APPLYING', 'BLOCKED_RECOVERY'):
            raise RuntimeError('unfinished journal blocks schema change')


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('upgrade', 'rollback'))
    parser.add_argument('--database', required=True, type=Path)
    parser.add_argument('--state', required=True, type=Path)
    parser.add_argument('--backup', required=True, type=Path)
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    db_path = args.database.resolve(strict=True)
    state = args.state.resolve(strict=True)
    backup = args.backup.resolve(strict=False)
    if (db_path.parent != state or backup.exists() or backup.with_name(backup.name + '.sha256').exists()
            or backup.parent == state or state in backup.parents or args.backup.is_symlink()):
        raise SystemExit('database/state/backup scope invalid or backup exists')
    with sqlite3.connect(f'file:{db_path}?mode=ro', uri=True) as source:
        integrity(source)
        no_active_work(source, state)
        version = source.execute('PRAGMA user_version').fetchone()[0]
        expected = 1 if args.action == 'upgrade' else 2
        if version != expected:
            raise SystemExit(f'expected schema {expected}, found {version}')
        print(f'{args.action}: {db_path} schema {version} -> {2 if expected == 1 else 1}; backup {backup}')
        if args.dry_run:
            return
        with sqlite3.connect(backup) as target:
            source.backup(target)
            integrity(target)
    backup.chmod(0o600)
    checksum = hashlib.sha256(backup.read_bytes()).hexdigest()
    backup.with_name(backup.name + '.sha256').write_text(checksum + '\n')
    backup.with_name(backup.name + '.sha256').chmod(0o600)
    with sqlite3.connect(db_path) as connection:
        integrity(connection)
        no_active_work(connection, state)
        if connection.execute('PRAGMA user_version').fetchone()[0] != expected:
            raise RuntimeError('schema changed during migration')
        if args.action == 'upgrade':
            connection.execute('CREATE TABLE schema_history (version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL)')
            connection.execute('INSERT INTO schema_history VALUES (?, ?)', (2, datetime.now(timezone.utc).isoformat()))
            connection.execute('PRAGMA user_version = 2')
        else:
            row = connection.execute('SELECT count(*) FROM schema_history WHERE version=2').fetchone()[0]
            if row != 1:
                raise RuntimeError('schema history is incompatible')
            connection.execute('DROP TABLE schema_history')
            connection.execute('PRAGMA user_version = 1')
        integrity(connection)
    print('schema change complete; backup SHA-256 written')


if __name__ == '__main__':
    main()
