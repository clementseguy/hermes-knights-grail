"""Local filename search and descriptor-safe delivery selection."""
from __future__ import annotations

import os
import stat
import unicodedata
from pathlib import Path

from .contracts import safe_relative


def _fold(text: str) -> str:
    value = unicodedata.normalize('NFD', text).casefold()
    return ''.join(char for char in value if unicodedata.category(char) != 'Mn')


def search_documents(documents: Path, query: str) -> list[Path]:
    needle = _fold(query.strip())
    if not needle:
        return []
    results = []
    def failed(error: OSError) -> None:
        raise error
    for directory, dirs, files in os.walk(documents, followlinks=False, onerror=failed):
        base = Path(directory)
        dirs[:] = [item for item in dirs if not item.startswith('.') and not (base / item).is_symlink()]
        for name in files:
            if name.startswith('.'):
                continue
            path = base / name
            if _fold(name).find(needle) < 0:
                continue
            info = path.lstat()
            if path.is_symlink() or not stat.S_ISREG(info.st_mode):
                continue
            safe_relative(str(path.relative_to(documents)), 'selection')
            results.append(path)
    return sorted(results, key=lambda path: _fold(str(path.relative_to(documents))))


def validate_selection(documents: Path, path: Path, expected: tuple[int, int, int, int], max_bytes: int) -> Path:
    relative = safe_relative(str(path.relative_to(documents)), 'selection')
    current = documents
    if current.is_symlink():
        raise ValueError('unsafe root')
    for part in relative.parts[:-1]:
        current = current / part
        if current.is_symlink() or not current.is_dir():
            raise ValueError('unsafe parent')
    info = path.lstat()
    if path.is_symlink() or not stat.S_ISREG(info.st_mode):
        raise ValueError('file changed')
    if (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns) != expected:
        raise ValueError('file changed')
    if info.st_size > max_bytes:
        raise ValueError('file too large')
    return path


def identity(path: Path) -> tuple[int, int, int, int]:
    info = path.lstat()
    return info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns


def read_document_bytes(documents: Path, path: Path, max_bytes: int,
                        expected: tuple[int, int, int, int] | None = None) -> bytes:
    """Open every path component without following symlinks, then recheck identity."""
    relative = safe_relative(str(path.relative_to(documents)), 'selection')
    descriptor = os.open(documents, os.O_RDONLY | getattr(os, 'O_DIRECTORY', 0) | getattr(os, 'O_NOFOLLOW', 0))
    try:
        for part in relative.parts[:-1]:
            child = os.open(part, os.O_RDONLY | getattr(os, 'O_DIRECTORY', 0) | getattr(os, 'O_NOFOLLOW', 0), dir_fd=descriptor)
            os.close(descriptor)
            descriptor = child
        fd = os.open(relative.name, os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_NONBLOCK', 0), dir_fd=descriptor)
        try:
            before = os.fstat(fd)
            if not stat.S_ISREG(before.st_mode) or before.st_size > max_bytes:
                raise ValueError('file too large or not regular')
            if expected is not None and (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) != expected:
                raise ValueError('file changed before read')
            chunks = []
            remaining = before.st_size
            while remaining:
                chunk = os.read(fd, min(1024 * 1024, remaining))
                if not chunk:
                    raise ValueError('file changed during read')
                chunks.append(chunk)
                remaining -= len(chunk)
            after = os.fstat(fd)
            if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) != (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns):
                raise ValueError('file changed during read')
            return b''.join(chunks)
        finally:
            os.close(fd)
    finally:
        os.close(descriptor)


def hash_document(documents: Path, path: Path, max_bytes: int) -> str:
    import hashlib
    relative = safe_relative(str(path.relative_to(documents)), 'selection')
    directory = os.open(documents, os.O_RDONLY | getattr(os, 'O_DIRECTORY', 0) | getattr(os, 'O_NOFOLLOW', 0))
    try:
        for part in relative.parts[:-1]:
            child = os.open(part, os.O_RDONLY | getattr(os, 'O_DIRECTORY', 0) | getattr(os, 'O_NOFOLLOW', 0), dir_fd=directory)
            os.close(directory)
            directory = child
        fd = os.open(relative.name, os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_NONBLOCK', 0), dir_fd=directory)
        try:
            before = os.fstat(fd)
            if not stat.S_ISREG(before.st_mode) or before.st_size > max_bytes:
                raise ValueError('candidate too large or not regular')
            digest = hashlib.sha256()
            while block := os.read(fd, 1024 * 1024):
                digest.update(block)
            after = os.fstat(fd)
            if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) != (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns):
                raise ValueError('candidate changed during hash')
            return digest.hexdigest()
        finally:
            os.close(fd)
    finally:
        os.close(directory)
