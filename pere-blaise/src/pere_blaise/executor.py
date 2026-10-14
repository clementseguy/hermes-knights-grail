"""Recoverable, all-or-rollback file transaction. Only the broker calls this module."""
from __future__ import annotations

import fcntl
import hashlib
import json
import os
import shutil
import stat
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from .contracts import Action, parse_manifest


class TransactionError(Exception):
    pass


def _digest(path: Path) -> str:
    h = hashlib.sha256()
    fd = os.open(path, os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_NONBLOCK', 0))
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise TransactionError('not a regular file')
        while block := os.read(fd, 1024 * 1024):
            h.update(block)
    finally:
        os.close(fd)
    return h.hexdigest()


def _directory(root: Path, relative: Path | None = None) -> Path:
    current = root
    if not stat.S_ISDIR(current.lstat().st_mode) or current.is_symlink():
        raise TransactionError('unsafe root')
    for part in relative.parts if relative else ():
        current = current / part
        if not stat.S_ISDIR(current.lstat().st_mode) or current.is_symlink():
            raise TransactionError('unsafe parent')
    return current


def _fsync_dir(path: Path) -> None:
    fd = os.open(path, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _copy_new(source: Path, target: Path) -> None:
    source_fd = os.open(source, os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_NONBLOCK', 0))
    try:
        target_fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, 'O_NOFOLLOW', 0), 0o600)
        try:
            while block := os.read(source_fd, 1024 * 1024):
                os.write(target_fd, block)
            os.fsync(target_fd)
        finally:
            os.close(target_fd)
    finally:
        os.close(source_fd)
    _fsync_dir(target.parent)


@contextmanager
def _parent_fd(root: Path, relative: Path):
    fd = os.open(root, os.O_RDONLY | getattr(os, 'O_DIRECTORY', 0) | getattr(os, 'O_NOFOLLOW', 0))
    try:
        for part in relative.parts[:-1]:
            child = os.open(part, os.O_RDONLY | getattr(os, 'O_DIRECTORY', 0) | getattr(os, 'O_NOFOLLOW', 0), dir_fd=fd)
            os.close(fd)
            fd = child
        yield fd
    finally:
        os.close(fd)


def _stat_at(root: Path, relative: Path) -> os.stat_result:
    with _parent_fd(root, relative) as parent:
        return os.stat(relative.name, dir_fd=parent, follow_symlinks=False)


def _digest_at(root: Path, relative: Path) -> str:
    with _parent_fd(root, relative) as parent:
        fd = os.open(relative.name, os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_NONBLOCK', 0), dir_fd=parent)
        try:
            if not stat.S_ISREG(os.fstat(fd).st_mode):
                raise TransactionError('not a regular file')
            digest = hashlib.sha256()
            while block := os.read(fd, 1024 * 1024):
                digest.update(block)
            return digest.hexdigest()
        finally:
            os.close(fd)


def _copy_at(src_root: Path, src_rel: Path, dst_root: Path, dst_rel: Path) -> os.stat_result:
    with _parent_fd(src_root, src_rel) as source_parent, _parent_fd(dst_root, dst_rel) as target_parent:
        source = os.open(src_rel.name, os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_NONBLOCK', 0), dir_fd=source_parent)
        try:
            if not stat.S_ISREG(os.fstat(source).st_mode):
                raise TransactionError('not a regular file')
            target = os.open(dst_rel.name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, 'O_NOFOLLOW', 0),
                             0o600, dir_fd=target_parent)
            try:
                while block := os.read(source, 1024 * 1024):
                    view = memoryview(block)
                    while view:
                        view = view[os.write(target, view):]
                os.fsync(target)
                target_info = os.fstat(target)
            finally:
                os.close(target)
        finally:
            os.close(source)
        os.fsync(target_parent)
        return target_info


def _unlink_at(root: Path, relative: Path) -> None:
    with _parent_fd(root, relative) as parent:
        os.unlink(relative.name, dir_fd=parent)
        os.fsync(parent)


class Executor:
    def __init__(self, downloads: Path, documents: Path, backups: Path, state: Path):
        self.downloads, self.documents, self.backups, self.state = downloads, documents, backups, state
        for root in (downloads, documents, backups, state):
            _directory(root)
        self.lock = state / 'transaction.lock'

    @contextmanager
    def _locked(self):
        with self.lock.open('a+b') as handle:
            fcntl.flock(handle, fcntl.LOCK_EX)
            yield

    def _journal_path(self, plan_id: str) -> Path:
        if not plan_id or '/' in plan_id or '.' in plan_id:
            raise TransactionError('invalid plan id')
        return self.state / f'{plan_id}.journal.json'

    def _write(self, path: Path, payload: dict[str, Any]) -> None:
        temp = path.with_name(path.name + '.' + uuid.uuid4().hex + '.tmp')
        with temp.open('x', encoding='utf-8') as handle:
            os.fchmod(handle.fileno(), 0o600)
            json.dump(payload, handle, ensure_ascii=False, sort_keys=True)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp, path)
        _fsync_dir(path.parent)

    def _paths(self, action: Action) -> tuple[Path, Path]:
        _directory(self.downloads, action.source.parent if action.source.parent != Path('.') else None)
        parent = action.destination.parent
        if parent == Path('a_trier') and not (self.documents / parent).exists():
            pass
        else:
            _directory(self.documents, parent if parent != Path('.') else None)
        return self.downloads / action.source, self.documents / action.destination

    def _preflight(self, actions: list[Action], plan_id: str) -> None:
        total = 0
        if not os.access(self.backups, os.W_OK) or not os.access(self.state, os.W_OK):
            raise TransactionError('backup or journal permission denied')
        for action in actions:
            source, destination = self._paths(action)
            if not os.access(source.parent, os.W_OK) or not os.access(destination.parent if destination.parent.exists() else self.documents, os.W_OK):
                raise TransactionError('source or destination permission denied')
            if destination.exists() or destination.is_symlink():
                raise TransactionError('destination exists')
            info = _stat_at(self.downloads, action.source)
            expected = action.expected
            if not stat.S_ISREG(info.st_mode) or source.is_symlink() or (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns) != (expected.device, expected.inode, expected.size, expected.mtime_ns):
                raise TransactionError('source changed')
            if _digest_at(self.downloads, action.source) != expected.sha256:
                raise TransactionError('source content changed')
            total += expected.size
        backup_root = self.backups / plan_id
        if backup_root.exists():
            raise TransactionError('backup already exists')
        if shutil.disk_usage(self.backups).free < total * 2 + 1024 * 1024:
            raise TransactionError('backup space insufficient')
        if shutil.disk_usage(self.documents).free < total + 1024 * 1024:
            raise TransactionError('destination space insufficient')

    def apply(self, plan_id: str, manifest: dict[str, Any], *, fault_after: int | None = None,
              crash_after: int | None = None) -> dict[str, Any]:
        actions = parse_manifest(manifest)
        with self._locked():
            journal_path = self._journal_path(plan_id)
            if journal_path.exists():
                return json.loads(journal_path.read_text())
            self._preflight(actions, plan_id)
            journal: dict[str, Any] = {'plan_id': plan_id, 'state': 'PREPARING', 'manifest': manifest,
                                       'moved': [], 'created': {}, 'ignore_existing': [], 'incident': uuid.uuid4().hex[:12]}
            self._write(journal_path, journal)
            backup_root = self.backups / plan_id
            current_destination = None
            try:
                backup_root.mkdir(mode=0o700)
                _fsync_dir(self.backups)
                for action in actions:
                    source, _ = self._paths(action)
                    backup = backup_root / action.source
                    backup.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
                    _copy_at(self.downloads, action.source, backup_root, action.source)
                    if _digest_at(backup_root, action.source) != action.expected.sha256:
                        raise TransactionError('backup verification failed')
                self._write(backup_root / 'manifest.json', {'manifest': manifest, 'verified': True})
                journal['state'] = 'BACKUPS_VERIFIED'
                self._write(journal_path, journal)
                if any(a.destination.parent == Path('a_trier') for a in actions):
                    (self.documents / 'a_trier').mkdir(exist_ok=True)
                    _fsync_dir(self.documents)
                journal['state'] = 'APPLYING'
                self._write(journal_path, journal)
                results = []
                for index, action in enumerate(actions):
                    source, destination = self._paths(action)
                    current_destination = str(action.destination)
                    created_info = _copy_at(self.downloads, action.source, self.documents, action.destination)
                    if _digest_at(self.documents, action.destination) != action.expected.sha256:
                        raise TransactionError('destination verification failed')
                    visible_info = _stat_at(self.documents, action.destination)
                    if (visible_info.st_dev, visible_info.st_ino) != (created_info.st_dev, created_info.st_ino):
                        raise TransactionError('destination changed before journaling')
                    journal['created'][current_destination] = {'device': created_info.st_dev, 'inode': created_info.st_ino}
                    self._write(journal_path, journal)
                    current = _stat_at(self.downloads, action.source)
                    expected = action.expected
                    if (current.st_dev, current.st_ino, current.st_size, current.st_mtime_ns) != (expected.device, expected.inode, expected.size, expected.mtime_ns) or _digest_at(self.downloads, action.source) != expected.sha256:
                        raise TransactionError('source changed before removal')
                    # Recovery recognizes a copied destination even if power fails here.
                    _unlink_at(self.downloads, action.source)
                    journal['moved'].append(str(action.destination))
                    self._write(journal_path, journal)
                    info = _stat_at(self.documents, action.destination)
                    results.append({'source': str(action.source), 'destination': str(action.destination), 'status': 'applied', 'destination_identity': {'device': info.st_dev, 'inode': info.st_ino, 'mtime_ns': info.st_mtime_ns}})
                    if fault_after is not None and index + 1 == fault_after:
                        raise TransactionError('injected failure')
                    if crash_after is not None and index + 1 == crash_after:
                        os._exit(77)  # test-only hard stop; no broker input can set this
                journal['state'] = 'APPLIED'
                journal['actions'] = results
                self._write(journal_path, journal)
                return journal
            except FileExistsError:
                if journal['state'] == 'APPLYING' and current_destination is not None:
                    journal['ignore_existing'].append(current_destination)
                    self._write(journal_path, journal)
                return self._rollback(journal_path, journal)
            except Exception:
                return self._rollback(journal_path, journal)

    def _rollback(self, path: Path, journal: dict[str, Any]) -> dict[str, Any]:
        blocked = False
        for action in reversed(parse_manifest(journal['manifest'])):
            try:
                source, destination = self._paths(action)
                backup = self.backups / journal['plan_id'] / action.source
                if destination.exists():
                    if str(action.destination) in journal.get('ignore_existing', []):
                        continue
                    proof = journal.get('created', {}).get(str(action.destination))
                    if not proof:
                        blocked = True
                        continue
                    info = _stat_at(self.documents, action.destination)
                    if (info.st_dev, info.st_ino) != (proof['device'], proof['inode']):
                        blocked = True
                        continue
                    if destination.is_symlink() or _digest_at(self.documents, action.destination) != action.expected.sha256:
                        blocked = True
                        continue
                if not source.exists() and backup.exists():
                    if _digest_at(self.backups, Path(journal['plan_id']) / action.source) != action.expected.sha256:
                        blocked = True
                        continue
                    _copy_at(self.backups, Path(journal['plan_id']) / action.source, self.downloads, action.source)
                    if _digest_at(self.downloads, action.source) != action.expected.sha256:
                        blocked = True
                        continue
                elif source.exists() and _digest_at(self.downloads, action.source) != action.expected.sha256:
                    blocked = True
                    continue
                elif not source.exists():
                    blocked = True
                    continue
                if destination.exists():
                    _unlink_at(self.documents, action.destination)
            except (OSError, TransactionError, ValueError):
                blocked = True
        journal['state'] = 'BLOCKED_RECOVERY' if blocked else 'ROLLED_BACK'
        self._write(path, journal)
        return journal

    def recover(self) -> list[dict[str, Any]]:
        with self._locked():
            results = []
            for path in sorted(self.state.glob('*.journal.json')):
                journal = json.loads(path.read_text())
                if journal['state'] == 'BLOCKED_RECOVERY':
                    results.append(journal)
                if journal['state'] not in ('APPLIED', 'ROLLED_BACK', 'BLOCKED_RECOVERY'):
                    results.append(self._rollback(path, journal))
            return results
