#!/usr/bin/env python3
"""Consistent SQLite backup/verified offline restore for broker state."""
from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
from pathlib import Path


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        while block := f.read(1024 * 1024): h.update(block)
    return h.hexdigest()


def integrity(path: Path) -> None:
    with sqlite3.connect(path) as db:
        if db.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
            raise ValueError('SQLite integrity check failed')


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument('operation', choices=['backup', 'restore'])
    p.add_argument('--source', type=Path, required=True)
    p.add_argument('--destination', type=Path, required=True)
    p.add_argument('--dry-run', action='store_true')
    args = p.parse_args()
    if not args.source.is_file() or args.destination.exists():
        raise SystemExit('source missing or destination exists')
    print(f'{args.operation}: {args.source.resolve()} -> {args.destination.resolve()}')
    if args.dry_run: return 0
    if args.operation == 'backup':
        with sqlite3.connect(args.source) as src, sqlite3.connect(args.destination) as dst:
            src.backup(dst)
    else:
        integrity(args.source)
        expected = args.source.with_suffix(args.source.suffix + '.sha256')
        if not expected.is_file() or expected.read_text().strip() != digest(args.source):
            raise SystemExit('backup checksum mismatch')
        with sqlite3.connect(args.source) as src, sqlite3.connect(args.destination) as dst:
            src.backup(dst)
    integrity(args.destination)
    checksum = digest(args.destination)
    args.destination.with_suffix(args.destination.suffix + '.sha256').write_text(checksum + '\n')
    print('verified: ' + checksum)
    return 0

if __name__ == '__main__': raise SystemExit(main())
