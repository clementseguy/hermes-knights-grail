"""Non-destructive analysis workflow."""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Callable

from .broker import Broker
from .planning import manifest_from_proposal, planner_context
from .scanner import scan

Planner = Callable[[dict[str, Any]], dict[str, Any]]


def _opaque_name(name: str) -> bool:
    stem = Path(name).stem
    compact = re.sub(r'[^a-zA-Z0-9]', '', stem)
    if len(compact) >= 12 and sum(char.isdigit() for char in compact) * 2 >= len(compact):
        return True
    return len(compact) >= 18 and not re.search(r'[aeiouyAEIOUY]{2}', compact)


def inventory_signature(inventory: dict[str, Any]) -> str:
    payload = {'downloads': [(f['path'], f['expected']) for f in inventory['downloads']['files']],
               'directories': inventory['documents']['directories']}
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def analyse(owner: str, home: Path, broker: Broker, planner: Planner, sha256_max_bytes: int) -> dict[str, Any]:
    with broker.operation_lock():
        return _analyse_locked(owner, home, broker, planner, sha256_max_bytes)


def _analyse_locked(owner: str, home: Path, broker: Broker, planner: Planner, sha256_max_bytes: int) -> dict[str, Any]:
    downloads = broker.downloads or home / 'Downloads'
    documents = broker.documents or home / 'Documents'
    inventory = {'downloads': scan(downloads, hash_files=True, sha256_max_bytes=sha256_max_bytes, max_files=broker.max_files),
                 'documents': scan(documents, hash_files=False, sha256_max_bytes=sha256_max_bytes, max_files=broker.max_files)}
    broker.store.reconcile_a_trier(inventory['documents'], documents, sha256_max_bytes)
    if not inventory['downloads']['files']:
        raise ValueError('PB-DL-EMPTY')
    context = planner_context(inventory, learning_hints=broker.store.learning_hints(inventory['downloads']['files']),
                              max_directories=broker.max_directories)
    last_error = None
    for _ in range(2):
        try:
            manifest, action_details = manifest_from_proposal(planner(context), inventory)
            break
        except ValueError as exc:
            last_error = exc
    else:
        raise last_error or ValueError('invalid proposal')
    count = len(action_details)
    a_trier = sum(Path(item['destination']).parent == Path('a_trier') for item in action_details)
    opaque = any(item['certainty'] == 'opaque' or _opaque_name(item['source']) for item in action_details)
    confidence = 'Low' if opaque or a_trier * 5 >= count else 'Medium' if a_trier else 'High'
    details = {'actions': action_details, 'confidence': confidence, 'a_trier_count': a_trier,
               'a_trier_percent': 100 * a_trier / count, 'excluded_count': inventory['downloads']['excluded_count'],
               'snapshot': inventory_signature(inventory)}
    return broker.create_plan(owner, manifest, details)
