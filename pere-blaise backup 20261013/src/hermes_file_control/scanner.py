"""Read-only metadata inventory for Documents and Downloads.

This module never opens document content.  SHA-256 is calculated only for eligible
Downloads files, because an approved organization action needs a stable precondition.
"""
from __future__ import annotations

import os
import stat
from pathlib import Path
from typing import Any, Iterator

from .contracts import fingerprint, safe_relative


def _files(root: Path) -> Iterator[Path]:
    for directory, dirnames, filenames in os.walk(root, followlinks=False):
        base = Path(directory)
        dirnames[:] = [name for name in dirnames if not name.startswith(".") and not (base / name).is_symlink()]
        for name in filenames:
            if name.startswith("."):
                continue
            candidate = base / name
            try:
                info = candidate.lstat()
            except OSError:
                continue
            if stat.S_ISREG(info.st_mode) and not candidate.is_symlink():
                yield candidate


def scan(root: Path, *, hash_files: bool, sha256_max_bytes: int) -> dict[str, Any]:
    """Return data only; unreadable, symlinked, and oversize files are explicitly excluded."""
    records = []
    excluded = []
    for path in _files(root):
        relative = str(path.relative_to(root))
        try:
            # A name containing control/format code points is never presented to the
            # model nor accepted into a manifest.  Keeping it out of `excluded`
            # avoids echoing a hostile filename back through Telegram as well.
            safe_relative(relative, "scanned path")
            info = path.lstat()
            record = {"path": relative, "size": info.st_size, "mtime_ns": info.st_mtime_ns,
                      "extension": path.suffix.lower(), "device": info.st_dev, "inode": info.st_ino}
            if hash_files:
                if info.st_size > sha256_max_bytes:
                    excluded.append({"path": relative, "reason": "sha256_size_ceiling"})
                    continue
                record["expected"] = fingerprint(path).as_dict()
            records.append(record)
        except ValueError:
            excluded.append({"reason": "unsafe_filename"})
        except OSError:
            excluded.append({"path": relative, "reason": "unreadable_or_changed"})
    return {"root": str(root), "files": records, "excluded": excluded}


def _directories(root: Path) -> list[str]:
    """Return safe visible directory paths, including empty directories."""
    result: list[str] = []
    for directory, dirnames, _filenames in os.walk(root, followlinks=False):
        base = Path(directory)
        dirnames[:] = [name for name in dirnames if not name.startswith(".") and not (base / name).is_symlink()]
        if base == root:
            continue
        relative = str(base.relative_to(root))
        try:
            safe_relative(relative, "scanned directory")
        except ValueError:
            continue
        result.append(relative)
    return sorted(result)


def scan_library(home: Path, sha256_max_bytes: int) -> dict[str, Any]:
    """The roots are fixed to the local user's library; callers cannot provide arbitrary paths."""
    documents_root = home / "Documents"
    documents = scan(documents_root, hash_files=False, sha256_max_bytes=sha256_max_bytes)
    documents["directories"] = _directories(documents_root)
    return {"downloads": scan(home / "Downloads", hash_files=True, sha256_max_bytes=sha256_max_bytes),
            "documents": documents}
