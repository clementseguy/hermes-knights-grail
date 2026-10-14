"""Private plan broker; movement accepts only a registered, owner-bound plan ID."""
from __future__ import annotations

from pathlib import Path
from contextlib import contextmanager
import fcntl
import os
from typing import Any

from .executor import Executor, TransactionError
from .store import PlanStore
from .scanner import scan


class Broker:
    def __init__(self, store: PlanStore, executor: Path | None = None, runtime_dir: Path | None = None, *,
                 downloads: Path | None = None, documents: Path | None = None, backups: Path | None = None,
                 plan_ttl_minutes: int = 30, max_files: int = 1000, max_directories: int = 500) -> None:
        if plan_ttl_minutes != 30:
            raise ValueError('plan validity must be 30 minutes')
        self.store = store
        self.downloads, self.documents, self.backups = downloads, documents, backups
        self.runtime_dir = runtime_dir
        self.max_files, self.max_directories = max_files, max_directories
        self.executor = Executor(downloads, documents, backups, runtime_dir) if all((downloads, documents, backups, runtime_dir)) else None
        if self.executor:
            recovered = self.executor.recover()
            for item in recovered:
                self.store.finish(item['plan_id'], item)
            import json
            for path in runtime_dir.glob('*.journal.json'):
                item = json.loads(path.read_text())
                record = self.store.get(item['plan_id'])
                if record and record['state'] == 'applying' and item['state'] in ('APPLIED', 'ROLLED_BACK', 'BLOCKED_RECOVERY'):
                    self.store.finish(item['plan_id'], item)
            if any(item['state'] == 'BLOCKED_RECOVERY' for item in recovered):
                raise RuntimeError('PB-ROLLBACK-BLOCKED')

    def create_plan(self, owner: str, manifest: dict[str, Any], details: dict[str, Any]) -> dict[str, Any]:
        self._ensure_unblocked()
        self.store.purge_plan_records(30)
        return self.store.create(owner=owner, manifest=manifest, details=details, ttl_minutes=30)

    @contextmanager
    def operation_lock(self):
        if self.runtime_dir is None:
            yield
            return
        fd = os.open(self.runtime_dir / 'control.lock', os.O_CREAT | os.O_RDWR, 0o600)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX)
            yield
        finally:
            fcntl.flock(fd, fcntl.LOCK_UN)
            os.close(fd)

    def _ensure_unblocked(self) -> None:
        if self.runtime_dir is None:
            return
        import json
        for path in self.runtime_dir.glob('*.journal.json'):
            if json.loads(path.read_text()).get('state') == 'BLOCKED_RECOVERY':
                raise RuntimeError('PB-ROLLBACK-BLOCKED')

    def detail(self, owner: str, plan_id: str) -> dict[str, Any]:
        plan = self.store.get(plan_id)
        if plan is None:
            raise ValueError('unknown plan')
        if plan['owner'] != owner:
            raise PermissionError('plan owner mismatch')
        if plan['state'] != 'proposed':
            raise ValueError('plan is no longer applicable')
        from datetime import datetime, timezone
        if datetime.fromisoformat(plan['expires_at']) <= datetime.now(timezone.utc):
            raise ValueError('plan has expired')
        return plan

    def apply(self, owner: str, plan_id: str) -> dict[str, Any]:
        with self.operation_lock():
            return self._apply_locked(owner, plan_id)

    def _apply_locked(self, owner: str, plan_id: str) -> dict[str, Any]:
        self._ensure_unblocked()
        if self.executor is None:
            raise RuntimeError('executor is not configured')
        self.detail(owner, plan_id)
        plan = self.store.get(plan_id)
        assert plan is not None
        snapshot = plan['details'].get('snapshot')
        if snapshot is not None:
            current = {'downloads': scan(self.downloads, hash_files=True, sha256_max_bytes=self.store.sha256_max_bytes, max_files=self.max_files),
                       'documents': scan(self.documents, hash_files=False, sha256_max_bytes=self.store.sha256_max_bytes, max_files=self.max_files)}
            from .workflow import inventory_signature
            if inventory_signature(current) != snapshot:
                raise ValueError('plan inventory changed')
        claimed = self.store.claim(plan_id, owner)
        try:
            result = self.executor.apply(plan_id, claimed['manifest'])
        except Exception as exc:
            from .errors import classify, incident
            code = classify(exc, stage='apply')
            journal = self.runtime_dir / f'{plan_id}.journal.json'
            uncertain = journal.exists()
            code = 'PB-ROLLBACK-BLOCKED' if uncertain else code
            result = {'state': 'BLOCKED_RECOVERY' if uncertain else 'REJECTED',
                      'code': code, 'incident': incident(code, stage='apply', exc=exc), 'actions': []}
        self.store.finish(plan_id, result)
        return result
