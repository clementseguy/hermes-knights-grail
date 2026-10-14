#!/usr/bin/env bash
# Encrypted, cold volume snapshot. Requires age and a reviewed recipient/identity.
set -euo pipefail
slug=pere-blaise
project_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
private_root="$HOME/Library/Application Support/HermesAgents/runtime/$slug"
snapshot_root="$HOME/Library/Application Support/HermesAgents/snapshots/$slug"
hermes_volume=hermes-pere-blaise-data
broker_volume=hermes-pere-blaise-broker-data
fail() { printf 'PB-BACKUP: %s\n' "$*" >&2; exit 2; }
physical() { python3 -c 'from pathlib import Path; import sys; print(Path(sys.argv[1]).resolve(strict=False))' "$1"; }
[[ $# -ge 1 ]] || fail 'backup or restore required'
operation=$1; shift
[[ "$operation" == backup || "$operation" == restore ]] || fail 'backup or restore required'
path=''; key=''; mode=''
while (($#)); do
  case "$1" in
    --path) path="${2:-}"; shift 2 ;;
    --recipient|--identity) key="${2:-}"; shift 2 ;;
    --dry-run) mode=dry-run; shift ;;
    --confirm) mode=confirm; shift ;;
    *) fail "unexpected argument: $1" ;;
  esac
done
[[ -n "$path" && -n "$mode" ]] || fail 'explicit --path and --dry-run/--confirm required'
path="$(physical "$path")"; snapshot_root="$(physical "$snapshot_root")"
[[ "$path" == "$snapshot_root"/* && "$(dirname "$path")" == "$snapshot_root" && ! -L "$path" ]] || fail 'snapshot path outside approved slug root'
[[ "$(physical "$private_root")" == "$(physical "$HOME/Library/Application Support/HermesAgents/runtime")/$slug" ]] || fail 'private root outside scope'
printf 'Operation: %s\nSnapshot: %s\nPrivate: %s\nVolumes: %s, %s\n' "$operation" "$path" "$private_root" "$hermes_volume" "$broker_volume"
[[ "$mode" == dry-run ]] && exit 0
command -v age >/dev/null || fail 'age CLI is required'
[[ -n "$key" ]] || fail 'recipient or identity required'
for volume in "$hermes_volume" "$broker_volume"; do docker volume inspect "$volume" >/dev/null 2>&1 || [[ "$operation" == restore ]] || fail "volume absent: $volume"; done
if [[ "$operation" == backup ]]; then
  [[ "$key" == age1* ]] || fail 'public age recipient required'
  [[ ! -e "$path" && -d "$private_root" && -f "$private_root/paths.env" ]] || fail 'snapshot exists or private configuration absent'
  "$project_dir/scripts/lifecycle.sh" stop
  umask 077
  mkdir -p -- "$snapshot_root" "$path"
  # SQLite backup API: broker volume is stopped but remains on native Docker storage.
  docker run --rm --mount "type=volume,source=$broker_volume,target=/state,readonly" --tmpfs /tmp \
    python:3.12-slim@sha256:a6e34c598f2467ed0e9a8d349809fcd8b5c603269512df273a0bb1784edc11b1 \
    python -c 'import sqlite3,sys; s=sqlite3.connect("file:/state/plans.sqlite3?mode=ro",uri=True); d=sqlite3.connect("/tmp/export.db"); s.backup(d); d.close(); s.close(); d=sqlite3.connect("/tmp/export.db"); assert d.execute("PRAGMA integrity_check").fetchone()[0]=="ok"; d.close(); sys.stdout.buffer.write(open("/tmp/export.db","rb").read())' \
    | age -r "$key" -o "$path/broker-sqlite.age"
  for item in "$hermes_volume" "$broker_volume"; do
    docker run --rm --mount "type=volume,source=$item,target=/data,readonly" \
      python:3.12-slim@sha256:a6e34c598f2467ed0e9a8d349809fcd8b5c603269512df273a0bb1784edc11b1 \
      python -c 'import sys,tarfile; t=tarfile.open(fileobj=sys.stdout.buffer,mode="w|"); t.add("/data",arcname=".",recursive=True); t.close()' \
      | age -r "$key" -o "$path/$item.tar.age"
  done
  tar -C "$private_root" -cf - . | age -r "$key" -o "$path/private.tar.age"
  python3 - "$path" "$project_dir/compose.yaml" <<'PY'
import hashlib,json,sys
from pathlib import Path
folder=Path(sys.argv[1]); compose=Path(sys.argv[2])
files={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(folder.glob('*.age'))}
(folder/'manifest.json').write_text(json.dumps({'version':1,'compose_sha256':hashlib.sha256(compose.read_bytes()).hexdigest(),'files':files},sort_keys=True,indent=2)+'\n')
(folder/'manifest.json').chmod(0o600)
PY
  printf 'Encrypted snapshot complete: %s\n' "$path"
else
  [[ -f "$key" && -d "$path" && -f "$path/manifest.json" ]] || fail 'identity or snapshot absent'
  [[ ! -e "$private_root" ]] || fail 'private runtime exists; restore requires an empty target'
  for volume in "$hermes_volume" "$broker_volume"; do
    ! docker volume inspect "$volume" >/dev/null 2>&1 || fail "volume exists; restore requires an empty target: $volume"
  done
  python3 - "$path" <<'PY'
import hashlib,json,sys
from pathlib import Path
folder=Path(sys.argv[1]); manifest=json.loads((folder/'manifest.json').read_text())
expected={'broker-sqlite.age','private.tar.age','hermes-pere-blaise-data.tar.age','hermes-pere-blaise-broker-data.tar.age'}
assert manifest['version']==1 and set(manifest['files'])==expected
for name,digest in manifest['files'].items():
    assert hashlib.sha256((folder/name).read_bytes()).hexdigest()==digest, name
PY
  mkdir -p -- "$private_root"
  chmod 700 "$private_root"
  age -d -i "$key" "$path/private.tar.age" | tar -C "$private_root" -xf -
  chmod 700 "$private_root"
  for volume in "$hermes_volume" "$broker_volume"; do
    docker volume create "$volume" >/dev/null
    age -d -i "$key" "$path/$volume.tar.age" | docker run --rm -i --mount "type=volume,source=$volume,target=/data" \
      python:3.12-slim@sha256:a6e34c598f2467ed0e9a8d349809fcd8b5c603269512df273a0bb1784edc11b1 \
      python -c 'import sys,tarfile; t=tarfile.open(fileobj=sys.stdin.buffer,mode="r|"); t.extractall("/data",filter="data"); t.close()'
  done
  docker run --rm --mount "type=volume,source=$broker_volume,target=/state,readonly" \
    python:3.12-slim@sha256:a6e34c598f2467ed0e9a8d349809fcd8b5c603269512df273a0bb1784edc11b1 \
    python -c 'import sqlite3; d=sqlite3.connect("file:/state/plans.sqlite3?mode=ro",uri=True); assert d.execute("PRAGMA integrity_check").fetchone()[0]=="ok"; print("broker SQLite verified")'
  printf 'Restored cold volumes and private runtime. Run smoke tests before start.\n'
fi
