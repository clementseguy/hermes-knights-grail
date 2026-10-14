"""Durable plan registry.  It has no operation that accepts shell text or paths at apply time."""
from __future__ import annotations

import json
import os
import secrets
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterator, Optional

from .contracts import PLAN_ADJECTIVES, PLAN_NOUNS, canonical_manifest, canonical_plan_id, fingerprint, manifest_digest, parse_manifest

DEFAULT_SHA256_MAX_BYTES = 1024 * 1024 * 1024


class PlanStore:
    def __init__(self, database: Path, *, sha256_max_bytes: int = DEFAULT_SHA256_MAX_BYTES) -> None:
        if sha256_max_bytes < 1:
            raise ValueError("sha256_max_bytes must be positive")
        database.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        self.database, self.sha256_max_bytes = database, sha256_max_bytes
        with self._connect() as connection:
            version = connection.execute('PRAGMA user_version').fetchone()[0]
            if version not in (0, 1, 2):
                raise RuntimeError(f'unsupported broker schema version {version}')
            connection.execute("""CREATE TABLE IF NOT EXISTS plans (
              id TEXT PRIMARY KEY, owner TEXT NOT NULL, created_at TEXT NOT NULL,
              expires_at TEXT NOT NULL, state TEXT NOT NULL, manifest_json TEXT NOT NULL,
              manifest_sha256 TEXT NOT NULL, details_json TEXT NOT NULL, result_json TEXT
            )""")
            connection.execute("""CREATE TABLE IF NOT EXISTS a_trier_tracking (
              id INTEGER PRIMARY KEY, source_path TEXT NOT NULL, source_extension TEXT NOT NULL,
              source_size INTEGER NOT NULL, source_mtime_ns INTEGER NOT NULL, source_sha256 TEXT NOT NULL,
              a_trier_path TEXT NOT NULL UNIQUE, device INTEGER NOT NULL, inode INTEGER NOT NULL,
              created_at TEXT NOT NULL
            )""")
            connection.execute("""CREATE TABLE IF NOT EXISTS learning_examples (
              id INTEGER PRIMARY KEY, source_name TEXT NOT NULL, extension TEXT NOT NULL, size INTEGER NOT NULL,
              destination_directory TEXT NOT NULL, learned_at TEXT NOT NULL, expires_at TEXT NOT NULL
            )""")
            connection.execute("""CREATE TABLE IF NOT EXISTS learning_events (
              id INTEGER PRIMARY KEY, event_type TEXT NOT NULL, source_path TEXT NOT NULL,
              destination TEXT, created_at TEXT NOT NULL, expires_at TEXT NOT NULL
            )""")
            if version == 0:
                connection.execute('PRAGMA user_version = 1')
        os.chmod(database, 0o600)

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.database)
        connection.row_factory = sqlite3.Row
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    @staticmethod
    def _now() -> datetime:
        return datetime.now(timezone.utc)

    def create(self, *, owner: str, manifest: Any, details: dict[str, Any], ttl_minutes: int = 30) -> dict[str, Any]:
        if not owner or ttl_minutes != 30:
            raise ValueError("owner is required and plan validity must be 30 minutes")
        actions = parse_manifest(manifest)
        if any(action.expected.size > self.sha256_max_bytes for action in actions):
            raise ValueError("a file exceeds the approved SHA-256 size ceiling")
        normal = canonical_manifest(manifest)
        now = self._now()
        for _ in range(10):
            identifier = f"{secrets.choice(PLAN_ADJECTIVES)}-{secrets.choice(PLAN_NOUNS)}"
            record = {"id": identifier, "owner": owner, "created_at": now.isoformat(),
                      "expires_at": (now + timedelta(minutes=ttl_minutes)).isoformat(), "state": "proposed",
                      "manifest": normal, "manifest_sha256": manifest_digest(normal), "details": details}
            try:
                with self._connect() as connection:
                    connection.execute("UPDATE plans SET state = 'invalidated' WHERE state = 'proposed'")
                    connection.execute("INSERT INTO plans VALUES (?, ?, ?, ?, ?, ?, ?, ?, NULL)",
                                       (record["id"], owner, record["created_at"], record["expires_at"], record["state"],
                                        json.dumps(normal, ensure_ascii=False, sort_keys=True), record["manifest_sha256"],
                                        json.dumps(details, ensure_ascii=False, sort_keys=True)))
                return record
            except sqlite3.IntegrityError:
                continue
        raise RuntimeError("unable to allocate a unique plan identifier")

    def get(self, identifier: str) -> Optional[dict[str, Any]]:
        try:
            identifier = canonical_plan_id(identifier)
        except ValueError:
            return None
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM plans WHERE id = ?", (identifier,)).fetchone()
        return self._row(row) if row else None

    def claim(self, identifier: str, owner: str) -> dict[str, Any]:
        """Atomically consume a proposed plan before invoking the executor."""
        try:
            identifier = canonical_plan_id(identifier)
        except ValueError as exc:
            raise ValueError("unknown plan") from exc
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM plans WHERE id = ?", (identifier,)).fetchone()
            if row is None:
                raise ValueError("unknown plan")
            record = self._row(row)
            if record["owner"] != owner:
                raise PermissionError("plan owner mismatch")
            if record["state"] != "proposed":
                raise ValueError("plan is no longer applicable")
            if datetime.fromisoformat(record["expires_at"]) <= self._now():
                connection.execute("UPDATE plans SET state = 'expired' WHERE id = ?", (identifier,))
                raise ValueError("plan has expired")
            changed = connection.execute("UPDATE plans SET state = 'applying' WHERE id = ? AND state = 'proposed'", (identifier,)).rowcount
            if changed != 1:
                raise ValueError("plan was claimed concurrently")
            record["state"] = "applying"
            return record

    def finish(self, identifier: str, result: dict[str, Any]) -> None:
        state = {"APPLIED": "applied", "ROLLED_BACK": "rolled_back", "BLOCKED_RECOVERY": "blocked_recovery"}.get(result.get("state"), "rejected")
        with self._connect() as connection:
            connection.execute("UPDATE plans SET state = ?, result_json = ? WHERE id = ? AND state = 'applying'",
                               (state, json.dumps(result, ensure_ascii=False, sort_keys=True), identifier))
            # F-013/F-014 are deferred. Legacy learning tables are retained intact.

    # F-013/F-014 are deferred. Keep legacy tables and rows, but expose no
    # collection, inference, consultation, correction or deletion operation.
    @staticmethod
    def _learning_deferred() -> None:
        raise RuntimeError('PB-LEARNING-DEFERRED')

    def reconcile_a_trier(self, *args: Any, **kwargs: Any) -> None:
        self._learning_deferred()

    def learning_hints(self, *args: Any, **kwargs: Any) -> None:
        self._learning_deferred()

    def learning_status(self, *args: Any, **kwargs: Any) -> None:
        self._learning_deferred()

    def list_learning_examples(self, *args: Any, **kwargs: Any) -> None:
        self._learning_deferred()

    def delete_learning_example(self, *args: Any, **kwargs: Any) -> None:
        self._learning_deferred()

    def correct_learning_example(self, *args: Any, **kwargs: Any) -> None:
        self._learning_deferred()

    def purge_plan_records(self, retention_days: int = 30) -> int:
        """Remove only broker metadata; this never examines or removes quarantine files."""
        if retention_days < 1:
            raise ValueError("retention_days must be positive")
        cutoff = self._now() - timedelta(days=retention_days)
        with self._connect() as connection:
            return connection.execute("DELETE FROM plans WHERE created_at < ? AND state IN ('applied','rolled_back','rejected','expired','invalidated')",
                                      (cutoff.isoformat(),)).rowcount

    @staticmethod
    def _row(row: sqlite3.Row) -> dict[str, Any]:
        return {"id": row["id"], "owner": row["owner"], "created_at": row["created_at"],
                "expires_at": row["expires_at"], "state": row["state"], "manifest": json.loads(row["manifest_json"]),
                "manifest_sha256": row["manifest_sha256"], "details": json.loads(row["details_json"]),
                "result": json.loads(row["result_json"]) if row["result_json"] else None}
