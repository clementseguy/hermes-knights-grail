"""Durable plan registry.  It has no operation that accepts shell text or paths at apply time."""
from __future__ import annotations

import json
import os
import re
import secrets
import sqlite3
import unicodedata
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterator, Optional

from .contracts import PLAN_ADJECTIVES, PLAN_NOUNS, canonical_manifest, canonical_plan_id, fingerprint, manifest_digest, parse_manifest

DEFAULT_SHA256_MAX_BYTES = 1024 * 1024 * 1024
LEARNING_RETENTION_DAYS = 90


class PlanStore:
    def __init__(self, database: Path, *, sha256_max_bytes: int = DEFAULT_SHA256_MAX_BYTES) -> None:
        if sha256_max_bytes < 1:
            raise ValueError("sha256_max_bytes must be positive")
        database.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        self.database, self.sha256_max_bytes = database, sha256_max_bytes
        with self._connect() as connection:
            version = connection.execute('PRAGMA user_version').fetchone()[0]
            if version not in (0, 1):
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
            if state == "applied":
                row = connection.execute("SELECT manifest_json FROM plans WHERE id = ?", (identifier,)).fetchone()
                if row is not None:
                    self._record_a_trier_actions(connection, json.loads(row["manifest_json"]), result)

    @staticmethod
    def _is_a_trier(path: str) -> bool:
        first = Path(path).parts[0] if Path(path).parts else ""
        normalised = unicodedata.normalize("NFD", first).casefold()
        normalised = "".join(char for char in normalised if unicodedata.category(char) != "Mn")
        return normalised == "a_trier"

    def _record_a_trier_actions(self, connection: sqlite3.Connection, manifest: dict[str, Any], result: dict[str, Any]) -> None:
        expected_by_destination = {item["destination"]: item["expected"] for item in manifest["actions"]
                                   if self._is_a_trier(item["destination"])}
        now = self._now().isoformat()
        for action in result.get("actions", []):
            destination = action.get("destination")
            identity = action.get("destination_identity")
            expected = expected_by_destination.get(destination)
            if action.get("status") != "applied" or not expected or not isinstance(identity, dict):
                continue
            if not all(isinstance(identity.get(key), int) and identity[key] >= 0 for key in ("device", "inode", "mtime_ns")):
                continue
            connection.execute(
                """INSERT OR REPLACE INTO a_trier_tracking
                   (source_path, source_extension, source_size, source_mtime_ns, source_sha256, a_trier_path, device, inode, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (action["source"], Path(action["source"]).suffix.lower(), expected["size"], identity["mtime_ns"],
                 expected["sha256"], destination, identity["device"], identity["inode"], now),
            )

    def reconcile_a_trier(self, documents: dict[str, Any], documents_root: Path, sha256_max_bytes: int) -> dict[str, Any]:
        """Learn user moves out of a_trier, then forget files that left scope.

        All matching happens on the host.  A hash is read only to decide between
        indistinguishable local metadata candidates; it is never sent to the planner.
        """
        files = documents["files"]
        by_path = {item["path"]: item for item in files}
        with self._connect() as connection:
            now = self._now()
            connection.execute("DELETE FROM learning_examples WHERE expires_at <= ?", (now.isoformat(),))
            connection.execute("DELETE FROM learning_events WHERE expires_at <= ?", (now.isoformat(),))
            tracked = connection.execute("SELECT * FROM a_trier_tracking ORDER BY id").fetchall()
            learned, missing = 0, []
            for row in tracked:
                tracked_path = row["a_trier_path"]
                current = by_path.get(tracked_path)
                if current is not None:
                    continue
                candidates = [item for item in files if item["size"] == row["source_size"]]
                candidates = self._sha256_matches(candidates, documents_root, row["source_sha256"], sha256_max_bytes)
                if len(candidates) == 1:
                    found = candidates[0]
                    if self._is_a_trier(found["path"]):
                        connection.execute("UPDATE a_trier_tracking SET a_trier_path = ?, device = ?, inode = ? WHERE id = ?",
                                           (found["path"], found["device"], found["inode"], row["id"]))
                        continue
                    destination = str(Path(found["path"]).parent)
                    connection.execute(
                        """INSERT INTO learning_examples
                           (source_name, extension, size, destination_directory, learned_at, expires_at)
                           VALUES (?, ?, ?, ?, ?, ?)""",
                        (Path(row["source_path"]).name, row["source_extension"], row["source_size"], destination,
                         now.isoformat(), (now + timedelta(days=LEARNING_RETENTION_DAYS)).isoformat()),
                    )
                    connection.execute("INSERT INTO learning_events (event_type, source_path, destination, created_at, expires_at) "
                                       "VALUES (?, ?, ?, ?, ?)",
                                       ("learned", row["source_path"], destination, now.isoformat(),
                                        (now + timedelta(days=LEARNING_RETENTION_DAYS)).isoformat()))
                    learned += 1
                else:
                    missing.append(tracked_path)
                    connection.execute("INSERT INTO learning_events (event_type, source_path, destination, created_at, expires_at) "
                                       "VALUES (?, ?, NULL, ?, ?)",
                                       ("forgotten", row["source_path"], now.isoformat(),
                                        (now + timedelta(days=LEARNING_RETENTION_DAYS)).isoformat()))
                if len(candidates) == 1:
                    connection.execute("DELETE FROM a_trier_tracking WHERE id = ?", (row["id"],))
        return {"learned": learned, "missing": missing}

    @staticmethod
    def _sha256_matches(candidates: list[dict[str, Any]], documents_root: Path, expected: str,
                        sha256_max_bytes: int) -> list[dict[str, Any]]:
        from .file_delivery import hash_document
        matches = []
        for candidate in candidates:
            if candidate["size"] > sha256_max_bytes:
                continue
            try:
                if hash_document(documents_root, documents_root / candidate["path"], sha256_max_bytes) == expected:
                    matches.append(candidate)
            except (OSError, ValueError):
                continue
        return matches

    def learning_hints(self, downloads: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Produce privacy-preserving routing hints from local manual corrections."""
        with self._connect() as connection:
            examples = connection.execute("SELECT source_name, extension, destination_directory FROM learning_examples "
                                          "WHERE expires_at > ?", (self._now().isoformat(),)).fetchall()
        hints = []
        for download in downloads:
            stem = self._tokens(Path(download["path"]).stem)
            scores: dict[str, int] = {}
            counts: dict[str, int] = {}
            for example in examples:
                if example["extension"] != download["extension"]:
                    continue
                example_stem = self._tokens(Path(example["source_name"]).stem)
                overlap = stem & example_stem
                exact = stem == example_stem and bool(stem)
                if not exact and len(overlap) < 2:
                    continue
                weight = 100 if exact else len(overlap)
                directory = example["destination_directory"]
                scores[directory] = scores.get(directory, 0) + weight
                counts[directory] = counts.get(directory, 0) + 1
            if scores:
                destination = max(scores, key=scores.get)
                hints.append({"source": download["path"], "suggested_directory": destination,
                              "evidence_count": counts[destination]})
        return hints

    def learning_status(self, limit: int = 20) -> dict[str, Any]:
        """Return local learning activity for the owner's explicit Telegram request."""
        if limit < 1 or limit > 50:
            raise ValueError("learning event limit must be between 1 and 50")
        with self._connect() as connection:
            now = self._now().isoformat()
            connection.execute("DELETE FROM learning_examples WHERE expires_at <= ?", (now,))
            connection.execute("DELETE FROM learning_events WHERE expires_at <= ?", (now,))
            pending = connection.execute("SELECT count(*) FROM a_trier_tracking").fetchone()[0]
            examples = connection.execute("SELECT count(*) FROM learning_examples").fetchone()[0]
            example_rows = connection.execute("SELECT id, source_name, destination_directory, learned_at FROM learning_examples ORDER BY id").fetchall()
            pending_rows = connection.execute("SELECT source_path, a_trier_path FROM a_trier_tracking ORDER BY id").fetchall()
            events = connection.execute("SELECT event_type, source_path, destination, created_at FROM learning_events "
                                        "ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return {"pending": pending, "examples": examples, "example_rows": [dict(row) for row in example_rows],
                "pending_rows": [dict(row) for row in pending_rows],
                "events": [{"type": row["event_type"], "source": row["source_path"],
                            "destination": row["destination"], "created_at": row["created_at"]} for row in events]}

    def list_learning_examples(self) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute("SELECT id, source_name, destination_directory, learned_at FROM learning_examples ORDER BY id").fetchall()
        return [dict(row) for row in rows]

    def delete_learning_example(self, example_id: int) -> bool:
        with self._connect() as connection:
            return connection.execute("DELETE FROM learning_examples WHERE id = ?", (example_id,)).rowcount == 1

    def correct_learning_example(self, example_id: int, directory: str, documents_root: Path) -> bool:
        from .contracts import safe_relative
        relative = safe_relative(directory, 'directory')
        target = documents_root / relative
        if not target.is_dir() or target.is_symlink():
            raise ValueError('directory is absent or unsafe')
        with self._connect() as connection:
            return connection.execute("UPDATE learning_examples SET destination_directory = ? WHERE id = ?",
                                      (str(relative), example_id)).rowcount == 1

    @staticmethod
    def _tokens(value: str) -> set[str]:
        folded = unicodedata.normalize("NFD", value).casefold()
        folded = "".join(char for char in folded if unicodedata.category(char) != "Mn")
        return {part for part in re.findall(r"[a-z0-9]+", folded) if len(part) > 1}

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
