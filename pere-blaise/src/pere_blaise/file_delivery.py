"""Deterministic, read-only Documents lookup for Telegram delivery."""
from __future__ import annotations

import os
import re
import stat
import unicodedata
from pathlib import Path

STOP_WORDS = frozenset({
    "a", "au", "aux", "ce", "cet", "cette", "d", "de", "des", "du", "en", "et",
    "l", "la", "le", "les", "moi", "mon", "ma", "mes", "pour", "sur", "un", "une",
})


def _normalise(value: str) -> str:
    decomposed = unicodedata.normalize("NFD", value).casefold()
    return "".join(char for char in decomposed if unicodedata.category(char) != "Mn")


def _terms(query: str) -> list[str]:
    return [item for item in re.split(r"[^\w.-]+", _normalise(query)) if item and item not in STOP_WORDS]


def search_documents(documents: Path, query: str, *, limit: int = 5) -> list[Path]:
    """Match filename/path words only; never read file content or follow symlinks."""
    terms = _terms(query)
    if not terms:
        return []
    matches: list[Path] = []
    for directory, dirnames, filenames in os.walk(documents, followlinks=False):
        base = Path(directory)
        dirnames[:] = [name for name in dirnames if not (base / name).is_symlink()]
        for name in filenames:
            candidate = base / name
            try:
                info = candidate.lstat()
            except OSError:
                continue
            if candidate.is_symlink() or not stat.S_ISREG(info.st_mode):
                continue
            relative = str(candidate.relative_to(documents))
            haystack = _normalise(relative)
            if all(term in haystack for term in terms):
                matches.append(candidate)
                if len(matches) >= limit:
                    return matches
    return matches
