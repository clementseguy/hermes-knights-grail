"""Minimal data boundary and strict validation of untrusted planner output."""
from __future__ import annotations

import unicodedata
from pathlib import Path
from typing import Any

from .contracts import safe_relative


def _key(value: str) -> str:
    return unicodedata.normalize('NFD', value).casefold()


def planner_context(inventory: dict[str, Any], *, max_directories: int = 500) -> dict[str, Any]:
    downloads = inventory['downloads']['files']
    directories = inventory['documents']['directories']
    if len(directories) > max_directories:
        raise ValueError('directory inventory limit exceeded')
    return {'untrusted_downloads': [{'source_relative': unicodedata.normalize('NFC', item['path']), 'size': item['size'], 'extension': item['extension']}
                                    for item in downloads], 'document_directories': [unicodedata.normalize('NFC', path) for path in directories],
            }


def manifest_from_proposal(proposal: Any, inventory: dict[str, Any], *,
                           collision_fallback: bool = False) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if not isinstance(proposal, dict) or not isinstance(proposal.get('actions'), list):
        raise ValueError('invalid proposal')
    available = {_key(item['path']): item for item in inventory['downloads']['files']}
    if len(available) != len(inventory['downloads']['files']):
        raise ValueError('ambiguous normalized download names')
    directories = {_key(path): path for path in inventory['documents']['directories']}
    if len(directories) != len(inventory['documents']['directories']):
        raise ValueError('ambiguous normalized directory names')
    directories.setdefault(_key('a_trier'), 'a_trier')
    directories[_key('.')] = '.'
    occupied = {_key(item['path']) for item in inventory['documents']['files']}
    actions = []
    details = []
    seen = set()
    sources = set()
    for raw in proposal['actions']:
        if not isinstance(raw, dict) or set(raw) != {'source_relative', 'destination_relative', 'reason', 'certainty'}:
            raise ValueError('invalid action shape')
        proposed_source = str(safe_relative(raw['source_relative'], 'source'))
        proposed_destination = str(safe_relative(raw['destination_relative'], 'destination'))
        selected = available.get(_key(proposed_source))
        if selected is None:
            raise ValueError('unknown source')
        source = selected['path']
        reason = raw['reason']
        certainty = raw['certainty']
        if not isinstance(reason, str) or not reason.strip() or len(reason) > 300 or any(ord(c) < 32 for c in reason):
            raise ValueError('invalid reason')
        if certainty not in ('clear', 'uncertain', 'opaque'):
            raise ValueError('invalid certainty')
        if source in sources or _key(Path(source).name) != _key(Path(proposed_destination).name):
            raise ValueError('unknown, repeated or renamed source')
        proposed_parent = str(Path(proposed_destination).parent)
        parent = directories.get(_key(proposed_parent))
        if parent is None or (parent == 'a_trier' and len(Path(proposed_destination).parts) != 2):
            raise ValueError('destination directory absent')
        destination = str(Path(parent) / Path(source).name)
        key = _key(destination)
        if key in occupied or key in seen:
            if not collision_fallback:
                raise ValueError('destination collision')
            # The planner never sees classified document names. The dedicated
            # duplicate folder must already exist; this code never creates it.
            duplicates = directories.get(_key('a_trier/doublons'))
            if duplicates is None:
                raise ValueError('duplicate review directory absent')
            destination = str(Path(duplicates) / Path(source).name)
            key = _key(destination)
            if key in occupied or key in seen:
                raise ValueError('destination collision')
            reason = 'Doublon repéré par le nom à la destination proposée ; classement à vérifier.'
            certainty = 'uncertain'
        sources.add(source)
        seen.add(key)
        actions.append({'source': source, 'destination': destination, 'expected': selected['expected']})
        details.append({'source': source, 'destination': destination, 'reason': reason.strip(), 'certainty': certainty})
    if sources != {item['path'] for item in inventory['downloads']['files']}:
        raise ValueError('proposal must cover every download')
    return {'version': 2, 'actions': actions}, details
