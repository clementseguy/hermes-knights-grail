#!/usr/bin/env python3
"""Offline operator-only learning review/correction; stop the broker first."""
from __future__ import annotations
import argparse
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from pere_blaise.store import PlanStore

p = argparse.ArgumentParser()
p.add_argument('--database', type=Path, required=True)
p.add_argument('--documents', type=Path, required=True)
p.add_argument('action', choices=['list', 'delete', 'correct'])
p.add_argument('--id', type=int)
p.add_argument('--directory')
a = p.parse_args()
store = PlanStore(a.database)
if a.action == 'list':
    for item in store.list_learning_examples(): print(item)
elif a.action == 'delete' and a.id is not None:
    print('deleted' if store.delete_learning_example(a.id) else 'not found')
elif a.action == 'correct' and a.id is not None and a.directory:
    print('corrected' if store.correct_learning_example(a.id, a.directory, a.documents) else 'not found')
else:
    p.error('--id and (for correct) --directory required')
