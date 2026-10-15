"""Strict local inventory. Only the separate broker sees content hashes."""
from __future__ import annotations

import os
import stat
from pathlib import Path
from typing import Any

from .contracts import fingerprint, safe_relative


def scan(root: Path, *, hash_files: bool, sha256_max_bytes: int, max_files: int = 1000,
         enforce_file_limits: bool = True) -> dict[str, Any]:
    if not root.is_dir() or root.is_symlink():
        raise PermissionError('inventory root unavailable')
    files: list[dict[str, Any]] = []
    directories: list[str] = []
    excluded = 0
    def failed(error: OSError) -> None:
        raise error
    for directory, dirnames, filenames in os.walk(root, followlinks=False, onerror=failed):
        base = Path(directory)
        if base != root:
            directories.append(str(base.relative_to(root)))
        kept = []
        for name in dirnames:
            child = base / name
            if name.startswith('.') or child.is_symlink():
                excluded += 1
            else:
                safe_relative(str(child.relative_to(root)), 'directory')
                kept.append(name)
        dirnames[:] = kept
        for name in filenames:
            path = base / name
            if name.startswith('.'):
                excluded += 1
                continue
            relative = str(path.relative_to(root))
            safe_relative(relative, 'scanned path')
            info = path.lstat()
            if not stat.S_ISREG(info.st_mode) or path.is_symlink():
                excluded += 1
                continue
            if enforce_file_limits and (len(files) >= max_files or info.st_size > sha256_max_bytes):
                raise ValueError('inventory limit exceeded')
            item = {'path': relative, 'size': info.st_size, 'mtime_ns': info.st_mtime_ns,
                    'extension': path.suffix.lower(), 'device': info.st_dev, 'inode': info.st_ino}
            if hash_files:
                item['expected'] = fingerprint(path).as_dict()
            files.append(item)
    return {'root': str(root), 'files': sorted(files, key=lambda item: item['path']),
            'directories': sorted(directories), 'excluded_count': excluded}


def scan_library(home: Path, sha256_max_bytes: int, max_files: int = 1000) -> dict[str, Any]:
    return {'downloads': scan(home / 'Downloads', hash_files=True, sha256_max_bytes=sha256_max_bytes, max_files=max_files),
            'documents': scan(home / 'Documents', hash_files=False, sha256_max_bytes=sha256_max_bytes,
                              max_files=max_files, enforce_file_limits=False)}
