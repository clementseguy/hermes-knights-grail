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
path=''; key=''; mode=''; disposable=0; requested_private=''; requested_hermes=''; requested_broker=''
while (($#)); do
  case "$1" in
    --path) path="${2:-}"; shift 2 ;;
    --disposable) disposable=1; shift ;;
    --private-root) requested_private="${2:-}"; shift 2 ;;
    --hermes-volume) requested_hermes="${2:-}"; shift 2 ;;
    --broker-volume) requested_broker="${2:-}"; shift 2 ;;
    --recipient|--identity) key="${2:-}"; shift 2 ;;
    --dry-run) mode=dry-run; shift ;;
    --confirm) mode=confirm; shift ;;
    *) fail "unexpected argument: $1" ;;
  esac
done
[[ -n "$path" && -n "$mode" ]] || fail 'explicit --path and --dry-run/--confirm required'
[[ ! -L "$path" && ( -z "$requested_private" || ! -L "$requested_private" ) ]] || fail 'symlink target refused'
if [[ "$disposable" == 1 ]]; then
  [[ -n "$requested_private" && -n "$requested_hermes" && -n "$requested_broker" ]] || fail 'disposable targets must be explicit'
  private_root="$(physical "$requested_private")"
  hermes_volume="$requested_hermes"; broker_volume="$requested_broker"
  [[ "$private_root" == /private/tmp/pb-test-* || "$private_root" == /tmp/pb-test-* ]] || fail 'disposable private root must be under /tmp/pb-test-*'
  [[ "$hermes_volume" =~ ^pb-test-[a-z0-9-]+$ && "$broker_volume" =~ ^pb-test-[a-z0-9-]+$ && "$hermes_volume" != "$broker_volume" ]] || fail 'unsafe disposable volume names'
else
  [[ -z "$requested_private" && -z "$requested_hermes" && -z "$requested_broker" ]] || fail 'custom targets require --disposable'
  [[ "$(physical "$private_root")" == "$(physical "$HOME/Library/Application Support/HermesAgents/runtime")/$slug" ]] || fail 'private root outside scope'
fi
path="$(physical "$path")"; snapshot_root="$(physical "$snapshot_root")"
if [[ "$disposable" == 1 ]]; then
  [[ "$path" == /private/tmp/pb-test-* || "$path" == /tmp/pb-test-* ]] || fail 'disposable snapshot must be under /tmp/pb-test-*'
else
  [[ "$path" == "$snapshot_root"/* && "$(dirname "$path")" == "$snapshot_root" ]] || fail 'snapshot path outside approved slug root'
fi
[[ ! -L "$path" && ! -L "$private_root" ]] || fail 'symlink root refused'
printf 'Operation: %s\nSnapshot: %s\nPrivate: %s\nVolumes: %s, %s\n' "$operation" "$path" "$private_root" "$hermes_volume" "$broker_volume"
[[ "$mode" == dry-run ]] && exit 0
if ! command -v age >/dev/null; then
  private_bin="$HOME/Library/Application Support/HermesAgents/bin"
  [[ -x "$private_bin/age" ]] && PATH="$private_bin:$PATH"
fi
command -v age >/dev/null || fail 'age CLI is required'
[[ -n "$key" ]] || fail 'recipient or identity required'
if [[ "$operation" == backup ]]; then
  [[ "$key" == age1* ]] || fail 'public age recipient required'
  [[ ! -e "$path" && -d "$private_root" && -f "$private_root/paths.env" ]] || fail 'snapshot exists or private configuration absent'
fi
if [[ "$operation" == backup && "$disposable" != 1 ]]; then
  "$project_dir/scripts/lifecycle.sh" stop
fi
for volume in "$hermes_volume" "$broker_volume"; do
  [[ -z "$(docker ps -q --filter "volume=$volume")" ]] || fail "volume is attached to a running container: $volume"
done
for volume in "$hermes_volume" "$broker_volume"; do docker volume inspect "$volume" >/dev/null 2>&1 || [[ "$operation" == restore ]] || fail "volume absent: $volume"; done
if [[ "$operation" == backup ]]; then
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
  python3 - "$private_root" <<'PY' | age -r "$key" -o "$path/private.tar.age"
import os,sys,tarfile
from pathlib import Path
root=Path(sys.argv[1])
with tarfile.open(fileobj=sys.stdout.buffer,mode='w|') as archive:
    for base, dirs, files in os.walk(root,followlinks=False):
        for name in dirs+files:
            item=Path(base)/name
            if item.is_symlink(): raise SystemExit('symlink in private snapshot refused')
            archive.add(item,arcname=str(item.relative_to(root)),recursive=False)
PY
  python3 - "$path" "$project_dir/compose.yaml" "$hermes_volume" "$broker_volume" <<'PY'
import hashlib,json,sys
from pathlib import Path
folder=Path(sys.argv[1]); compose=Path(sys.argv[2])
files={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(folder.glob('*.age'))}
(folder/'manifest.json').write_text(json.dumps({'version':2,'compose_sha256':hashlib.sha256(compose.read_bytes()).hexdigest(),
 'volume_archives':{'hermes':sys.argv[3]+'.tar.age','broker':sys.argv[4]+'.tar.age'},'files':files},sort_keys=True,indent=2)+'\n')
(folder/'manifest.json').chmod(0o600)
PY
  printf 'Encrypted snapshot complete: %s\n' "$path"
else
  [[ -f "$key" && ! -L "$key" && -d "$path" && -f "$path/manifest.json" ]] || fail 'identity or snapshot absent'
  python3 - "$key" <<'PY'
import os,stat,sys
if stat.S_IMODE(os.stat(sys.argv[1]).st_mode) & 0o077:
    raise SystemExit('identity permissions too broad')
PY
  [[ ! -e "$private_root" ]] || fail 'private runtime exists; restore requires an empty target'
  for volume in "$hermes_volume" "$broker_volume"; do
    ! docker volume inspect "$volume" >/dev/null 2>&1 || fail "volume exists; restore requires an empty target: $volume"
  done
  python3 - "$path" <<'PY'
import hashlib,json,sys
from pathlib import Path
folder=Path(sys.argv[1]); manifest=json.loads((folder/'manifest.json').read_text())
archives=manifest['volume_archives']
expected={'broker-sqlite.age','private.tar.age',archives['hermes'],archives['broker']}
assert manifest['version']==2 and set(manifest['files'])==expected
for name,digest in manifest['files'].items():
    assert Path(name).name==name and name.endswith('.age'), name
    assert hashlib.sha256((folder/name).read_bytes()).hexdigest()==digest, name
PY
  hermes_archive="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["volume_archives"]["hermes"])' "$path/manifest.json")"
  broker_archive="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["volume_archives"]["broker"])' "$path/manifest.json")"
  mkdir -p -- "$private_root"
  chmod 700 "$private_root"
  age -d -i "$key" "$path/private.tar.age" | python3 "$project_dir/scripts/safe-tar-extract.py" "$private_root"
  chmod 700 "$private_root"
  for role in hermes broker; do
    if [[ "$role" == hermes ]]; then volume="$hermes_volume"; archive="$hermes_archive"; else volume="$broker_volume"; archive="$broker_archive"; fi
    docker volume create "$volume" >/dev/null
    age -d -i "$key" "$path/$archive" | docker run --rm -i --mount "type=volume,source=$volume,target=/data" \
      python:3.12-slim@sha256:a6e34c598f2467ed0e9a8d349809fcd8b5c603269512df273a0bb1784edc11b1 \
      python -c 'import sys,tarfile,pathlib,os
with tarfile.open(fileobj=sys.stdin.buffer,mode="r|") as t:
 for m in t:
  p=pathlib.Path(m.name)
  if p.is_absolute() or ".." in p.parts or not (m.isfile() or m.isdir()) or m.uid not in (0,10000) or m.gid not in (0,10000) or m.uid!=m.gid or m.mode & 0o7000: raise ValueError("unsafe volume archive")
  t.extract(m,"/data",filter="data")
  target=pathlib.Path("/data")/p
  os.chown(target,m.uid,m.gid,follow_symlinks=False)
  os.chmod(target,m.mode & 0o777,follow_symlinks=False)'
  done
  docker run --rm --mount "type=volume,source=$broker_volume,target=/state,readonly" \
    python:3.12-slim@sha256:a6e34c598f2467ed0e9a8d349809fcd8b5c603269512df273a0bb1784edc11b1 \
    python -c 'import sqlite3; d=sqlite3.connect("file:/state/plans.sqlite3?mode=ro",uri=True); assert d.execute("PRAGMA integrity_check").fetchone()[0]=="ok"; print("broker SQLite verified")'
  printf 'Restored cold volumes and private runtime. Run smoke tests before start.\n'
fi
