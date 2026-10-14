"""Stable, content-free incident diagnostics shared by channel and broker paths."""
from __future__ import annotations

import json
import re
import sys
import uuid
from urllib.error import URLError

CATALOG = frozenset({
    'PB-DL-EMPTY', 'PB-FS-DENIED', 'PB-PLAN-EXPIRED', 'PB-PLAN-INVALID',
    'PB-PLAN-OWNER', 'PB-PLAN-COLLISION', 'PB-BACKUP-SPACE',
    'PB-BACKUP-VERIFY', 'PB-APPLY-FAILED', 'PB-ROLLBACK-BLOCKED',
    'PB-MODEL-UNAVAILABLE', 'PB-SEND-NOTFOUND', 'PB-SEND-AMBIGUOUS',
    'PB-SEND-LIMIT', 'PB-SEND-FAILED', 'PB-SEND-UNCERTAIN',
    'PB-CHANNEL-FAILED', 'PB-LEARNING-DEFERRED',
})


def classify(exc: Exception, *, stage: str = 'command') -> str:
    message = str(exc)
    direct = re.fullmatch(r'PB-[A-Z-]+', message)
    if direct and message in CATALOG:
        return message
    if isinstance(exc, PermissionError):
        return 'PB-PLAN-OWNER' if 'owner' in message else 'PB-FS-DENIED'
    if isinstance(exc, URLError):
        return 'PB-MODEL-UNAVAILABLE' if stage == 'analyse' else 'PB-CHANNEL-FAILED'
    if 'expired' in message:
        return 'PB-PLAN-EXPIRED'
    if 'space' in message:
        return 'PB-BACKUP-SPACE'
    if 'backup verification' in message:
        return 'PB-BACKUP-VERIFY'
    if 'destination exists' in message or 'collision' in message:
        return 'PB-PLAN-COLLISION'
    if 'too large' in message:
        return 'PB-SEND-LIMIT'
    if stage == 'analyse' and isinstance(exc, (TimeoutError, ConnectionError)):
        return 'PB-MODEL-UNAVAILABLE'
    if stage == 'send':
        return 'PB-SEND-FAILED'
    if stage == 'apply':
        return 'PB-APPLY-FAILED'
    return 'PB-PLAN-INVALID'


def incident(code: str, *, stage: str, exc: Exception | None = None, identifier: str | None = None) -> str:
    if code not in CATALOG:
        code = 'PB-PLAN-INVALID'
    identifier = identifier or uuid.uuid4().hex[:12]
    record = {'incident': identifier, 'code': code, 'stage': stage,
              'error_type': type(exc).__name__ if exc else None}
    print(json.dumps(record, sort_keys=True), file=sys.stderr, flush=True)
    return identifier


def user_message(code: str, *, stage: str, exc: Exception | None = None) -> str:
    identifier = incident(code, stage=stage, exc=exc)
    return f'{code} — Opération non aboutie ; consulter le journal local — incident {identifier}'
