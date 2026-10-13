#!/usr/bin/env python3
"""The only file-moving executor for Hermes organization plans.

It accepts only a strict v2 manifest, never shell commands or free paths.
It copies verified content into Documents and atomically quarantines the original.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import stat
import sys
import uuid
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from pere_blaise.contracts import Action, ExpectedFile, parse_manifest  # noqa: E402


def _within(path: Path, root: Path, label: str) -> None:
    try:
        path.resolve().relative_to(root.resolve())
    except ValueError as exc:
        raise ValueError(f"{label} escapes its permitted root") from exc


def _same(info: os.stat_result, expected: ExpectedFile) -> bool:
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns) == (
        expected.device, expected.inode, expected.size, expected.mtime_ns)


def _hash_fd(fd: int) -> str:
    digest = hashlib.sha256()
    os.lseek(fd, 0, os.SEEK_SET)
    while chunk := os.read(fd, 1024 * 1024):
        digest.update(chunk)
    os.lseek(fd, 0, os.SEEK_SET)
    return digest.hexdigest()


def _hash_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb", buffering=0) as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _copy_fd(fd: int, temporary: Path) -> None:
    os.lseek(fd, 0, os.SEEK_SET)
    with temporary.open("xb", buffering=0) as output:
        while chunk := os.read(fd, 1024 * 1024):
            output.write(chunk)
        output.flush()
        os.fsync(output.fileno())


def _apply_one(action: Action, downloads: Path, documents: Path, quarantine: Path) -> dict[str, str]:
    source = downloads / action.source
    destination = documents / action.destination
    temporary = destination.with_name(f".{destination.name}.hermes-copy-{uuid.uuid4().hex}")
    fd = -1
    try:
        _within(source.parent, downloads, "source")
        _within(destination.parent, documents, "destination")
        if destination.exists() or destination.is_symlink():
            raise ValueError("destination exists")
        flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
        fd = os.open(source, flags)
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or not _same(info, action.expected):
            raise ValueError("source identity changed since analysis")
        if _hash_fd(fd) != action.expected.sha256:
            raise ValueError("source content changed since analysis")
        destination.parent.mkdir(parents=True, exist_ok=True)
        _copy_fd(fd, temporary)
        if _hash_path(temporary) != action.expected.sha256:
            raise ValueError("copied content does not match approved digest")
        # Re-check the directory entry, not only the still-open descriptor, before move.
        current = source.lstat()
        if not stat.S_ISREG(current.st_mode) or not _same(current, action.expected):
            raise ValueError("source changed while applying plan")
        target = quarantine / action.source
        if target.exists() or target.is_symlink():
            raise ValueError("quarantine target exists")
        target.parent.mkdir(parents=True, exist_ok=True)
        if current.st_dev != target.parent.stat().st_dev:
            raise ValueError("quarantine must share Downloads filesystem")
        os.replace(temporary, destination)
        os.replace(source, target)
        destination_info = destination.lstat()
        return {"source": str(action.source), "destination": str(action.destination), "quarantine": str(target),
                "destination_identity": {"device": destination_info.st_dev, "inode": destination_info.st_ino,
                                         "mtime_ns": destination_info.st_mtime_ns}, "status": "applied"}
    except Exception as exc:
        temporary.unlink(missing_ok=True)
        return {"source": str(action.source), "destination": str(action.destination), "status": f"failed: {exc}"}
    finally:
        if fd >= 0:
            os.close(fd)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--apply", action="store_true", required=True)
    parser.add_argument("--non-interactive", action="store_true", required=True)
    args = parser.parse_args()
    try:
        actions = parse_manifest(json.loads(args.manifest.read_text(encoding="utf-8")))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"actions": [], "refused": str(exc)}))
        return 2
    home = Path.home()
    run_id = datetime.now().astimezone().strftime("%Y-%m-%d_%H-%M-%S") + "-" + uuid.uuid4().hex[:8]
    quarantine = home / "Hermes-Quarantine" / run_id / "Downloads"
    results = [_apply_one(action, home / "Downloads", home / "Documents", quarantine) for action in actions]
    payload = {"actions": results}
    # Only create a run directory when something was actually moved.
    if any(result["status"] == "applied" for result in results):
        quarantine.parent.mkdir(parents=True, exist_ok=True)
        (quarantine.parent / "result.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return 0 if all(result["status"] == "applied" for result in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
