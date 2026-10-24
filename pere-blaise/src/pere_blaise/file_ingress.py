"""Bounded, owner-only attachment import into the existing Downloads mount.

The channel adapters authenticate the sender before calling this module. File
names and bytes remain untrusted; Hermes never sees either attachment bytes.
"""
from __future__ import annotations

import os
import re
import stat
import unicodedata
import uuid
import zipfile
from pathlib import Path
from typing import BinaryIO
from urllib.parse import urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener


ALLOWED = {'.pdf', '.png', '.jpg', '.jpeg', '.txt', '.csv', '.docx', '.xlsx', '.pptx'}
DANGEROUS = {'.app', '.bat', '.bin', '.cmd', '.com', '.dmg', '.exe', '.html', '.htm',
             '.jar', '.js', '.jse', '.lnk', '.msi', '.php', '.pl', '.ps1', '.py',
             '.rb', '.scpt', '.sh', '.svg', '.vbs', '.webloc', '.workflow', '.zsh'}
MAX_NAME = 160


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, message, headers, newurl):
        raise ValueError('PB-RECEIVE-FAILED')


def open_download(url: str, host: str, headers: dict[str, str] | None = None):
    parsed = urlparse(url)
    if (parsed.scheme != 'https' or parsed.hostname != host or parsed.port not in (None, 443) or
            parsed.username or parsed.password or parsed.fragment):
        raise ValueError('PB-RECEIVE-FAILED')
    return build_opener(_NoRedirect()).open(Request(url, headers=headers or {}), timeout=90)


def safe_filename(raw: object) -> str:
    if not isinstance(raw, str):
        raise ValueError('PB-RECEIVE-TYPE')
    name = unicodedata.normalize('NFC', raw)
    if (not name or len(name) > MAX_NAME or name in ('.', '..') or
            name.startswith('.') or name.endswith((' ', '.')) or '/' in name or '\\' in name or
            any(unicodedata.category(c).startswith('C') for c in name)):
        raise ValueError('PB-RECEIVE-TYPE')
    suffixes = {s.casefold() for s in Path(name).suffixes}
    if Path(name).suffix.casefold() not in ALLOWED or suffixes & DANGEROUS:
        raise ValueError('PB-RECEIVE-TYPE')
    return name


def _check_zip(path: Path, extension: str, limit: int) -> None:
    root = {'.docx': 'word/', '.xlsx': 'xl/', '.pptx': 'ppt/'}[extension]
    try:
        with zipfile.ZipFile(path) as archive:
            entries = archive.infolist()
            if not entries or len(entries) > 2000 or not any(e.filename.startswith(root) for e in entries):
                raise ValueError('PB-RECEIVE-TYPE')
            if '[Content_Types].xml' not in archive.namelist():
                raise ValueError('PB-RECEIVE-TYPE')
            if archive.getinfo('[Content_Types].xml').file_size > min(limit * 8, 2 * 1024 * 1024):
                raise ValueError('PB-RECEIVE-TYPE')
            if b'macroenabled' in archive.read('[Content_Types].xml').lower():
                raise ValueError('PB-RECEIVE-TYPE')
            expanded = 0
            for entry in entries:
                name = entry.filename.casefold()
                expanded += entry.file_size
                if (expanded > limit * 8 or entry.flag_bits & 1 or name.startswith('/') or
                        '..' in Path(name).parts or '\\' in name or
                        any(part in name for part in ('vba', 'macro', 'activex', 'embedding', 'oleobject')) or
                        Path(name).suffix in DANGEROUS):
                    raise ValueError('PB-RECEIVE-TYPE')
                if name.endswith('.rels') and re.search(rb'TargetMode\s*=\s*[\x22\x27]External[\x22\x27]',
                                                       archive.read(entry), re.IGNORECASE):
                    raise ValueError('PB-RECEIVE-TYPE')
    except (zipfile.BadZipFile, RuntimeError, OSError) as exc:
        raise ValueError('PB-RECEIVE-TYPE') from exc


def _check_content(path: Path, name: str, limit: int) -> None:
    extension = Path(name).suffix.casefold()
    if extension in ('.docx', '.xlsx', '.pptx'):
        _check_zip(path, extension, limit)
        return
    data = path.read_bytes()
    if extension == '.pdf':
        if (not data.startswith(b'%PDF-') or b'%%EOF' not in data[-2048:] or
                any(marker in data for marker in (b'/JavaScript', b'/JS ', b'/Launch',
                                                  b'/EmbeddedFile', b'/OpenAction', b'/AA '))):
            raise ValueError('PB-RECEIVE-TYPE')
    elif extension == '.png':
        if not data.startswith(b'\x89PNG\r\n\x1a\n') or not data.endswith(b'IEND\xaeB`\x82'):
            raise ValueError('PB-RECEIVE-TYPE')
    elif extension in ('.jpg', '.jpeg'):
        if not data.startswith(b'\xff\xd8\xff') or not data.endswith(b'\xff\xd9'):
            raise ValueError('PB-RECEIVE-TYPE')
    else:
        try:
            content = data.decode('utf-8-sig')
        except UnicodeDecodeError as exc:
            raise ValueError('PB-RECEIVE-TYPE') from exc
        stripped = content.lstrip().casefold()
        if (b'\x00' in data or any(unicodedata.category(c).startswith('C') and c not in '\r\n\t' for c in content) or
                stripped.startswith(('#!', '<!doctype', '<html', '<script', '<?', '<svg')) or
                re.search(r'<script\b', stripped)):
            raise ValueError('PB-RECEIVE-TYPE')


def save_attachment(downloads: Path, raw_name: object, declared_size: object,
                    stream: BinaryIO, limit: int) -> str:
    """Stream into a hidden temporary file; publish only after all checks pass."""
    name = safe_filename(raw_name)
    if (not isinstance(limit, int) or limit < 1 or not isinstance(declared_size, int) or
            isinstance(declared_size, bool) or declared_size < 0 or declared_size > limit):
        raise ValueError('PB-RECEIVE-LIMIT')
    root_fd = os.open(downloads, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    temporary = '.pb-ingress-' + uuid.uuid4().hex
    created = False
    try:
        if not stat.S_ISDIR(os.fstat(root_fd).st_mode):
            raise ValueError('PB-RECEIVE-FAILED')
        fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=root_fd)
        created = True
        try:
            total = 0
            while True:
                block = stream.read(min(65536, limit + 1 - total))
                if not block:
                    break
                if not isinstance(block, bytes):
                    raise ValueError('PB-RECEIVE-FAILED')
                total += len(block)
                if total > limit:
                    raise ValueError('PB-RECEIVE-LIMIT')
                view = memoryview(block)
                while view:
                    view = view[os.write(fd, view):]
            if total != declared_size:
                raise ValueError('PB-RECEIVE-FAILED')
            os.fsync(fd)
        finally:
            os.close(fd)
        staged = downloads / temporary
        _check_content(staged, name, limit)
        folded = unicodedata.normalize('NFD', name).casefold()
        if any(unicodedata.normalize('NFD', item).casefold() == folded for item in os.listdir(root_fd)):
            raise ValueError('PB-RECEIVE-COLLISION')
        os.link(temporary, name, src_dir_fd=root_fd, dst_dir_fd=root_fd, follow_symlinks=False)
        os.unlink(temporary, dir_fd=root_fd)
        created = False
        os.fsync(root_fd)
        return name
    finally:
        if created:
            os.unlink(temporary, dir_fd=root_fd)
        os.close(root_fd)
