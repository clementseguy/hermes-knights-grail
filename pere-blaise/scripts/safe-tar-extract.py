#!/usr/bin/env python3
"""Extract a streamed tar to a new private directory without links or traversal."""
import sys
import tarfile
import os
import shutil
from pathlib import Path

root = Path(sys.argv[1])
with tarfile.open(fileobj=sys.stdin.buffer, mode='r|') as archive:
    for item in archive:
        relative = Path(item.name)
        if relative.is_absolute() or '..' in relative.parts or not (item.isfile() or item.isdir()):
            raise SystemExit('unsafe archive entry')
        target = root / relative
        if item.isdir():
            target.mkdir(mode=0o700, parents=True, exist_ok=True)
        else:
            target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, 'O_NOFOLLOW', 0), 0o600)
            with os.fdopen(fd, 'wb') as output:
                shutil.copyfileobj(archive.extractfile(item), output)
                output.flush()
                os.fsync(output.fileno())
