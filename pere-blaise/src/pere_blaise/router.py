"""Strict parsing for the future Telegram ingress.

This is deliberately independent of Telegram and Hermes.  It turns only the
small supported language into data; everything else is ordinary planner text.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

from .contracts import canonical_plan_id

SEND_PREFIX = "envoie "
DETAIL = re.compile(r"d[ée]tail(?:le)?\s+(\S+)", re.IGNORECASE)
RANGE = re.compile(r"range\s+(\S+)", re.IGNORECASE)


@dataclass(frozen=True)
class Command:
    name: str
    argument: str = ""


def parse_message(text: str) -> Optional[Command]:
    """Recognize exact privileged commands; never interpret shell-like suffixes."""
    if not isinstance(text, str):
        return None
    normalized = " ".join(text.strip().split())
    if normalized.casefold() == "analyse":
        return Command("analyse")
    if normalized.casefold() == "apprentissages":
        return Command("learning")
    for name, expression in (("detail", DETAIL), ("range", RANGE)):
        matched = expression.fullmatch(normalized)
        if matched:
            try:
                return Command(name, canonical_plan_id(matched.group(1)))
            except ValueError:
                continue
    if normalized.casefold().startswith(SEND_PREFIX):
        query = normalized[len(SEND_PREFIX):].strip()
        if 1 <= len(query) <= 160 and "\x00" not in query:
            return Command("send", query)
    return None
