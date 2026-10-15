#!/usr/bin/env bash
# Conservatively manage the dedicated Père Blaise Docker project.
set -euo pipefail

slug=pere-blaise
project_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
deploy_root="$HOME/Library/Application Support/HermesAgents/deployments"
private_root="$HOME/Library/Application Support/HermesAgents/runtime/$slug"
backup_root="$HOME/Library/Application Support/HermesAgents/backups/$slug"

fail() { printf '%s\n' "PB-LIFECYCLE: $*" >&2; exit 2; }
physical() { python3 -c 'from pathlib import Path; import sys; print(Path(sys.argv[1]).resolve(strict=False))' "$1"; }
size() { [[ -e "$1" ]] && du -sk "$1" | awk '{print $1 " KiB"}' || printf 'absent'; }
volume_size() {
  if ! docker volume inspect "$1" >/dev/null 2>&1; then printf 'absent'; return; fi
  docker run --rm --mount "type=volume,source=$1,target=/data,readonly" \
    python:3.12-slim@sha256:a6e34c598f2467ed0e9a8d349809fcd8b5c603269512df273a0bb1784edc11b1 \
    du -sk /data | awk '{print $1 " KiB"}'
}
check_path() {
  local path expected_parent
  path="$(physical "$1")"; expected_parent="$(physical "$2")"
  [[ "$path" == "$expected_parent/$slug" && "$path" != / && "$path" != "$HOME" ]] || fail "unsafe path: $path"
  [[ ! -L "$path" ]] || fail "symlink refused: $path"
  printf '%s\n' "$path"
}
[[ $# -ge 1 ]] || fail 'command required'
command=$1; shift
case "$command" in
  install|update)
    [[ $# -gt 0 ]] || fail 'pass deploy-stage-safe.sh phase and budget explicitly'
    if [[ "$1" == --dry-run ]]; then shift; set -- "$@" --preview; fi
    exec "$project_dir/scripts/deploy-stage-safe.sh" --deploy-root "$deploy_root" "$@"
    ;;
  backup|restore)
    exec "$project_dir/scripts/volume-backup.sh" "$command" "$@"
    ;;
  configure)
    [[ $# -eq 3 ]] || fail 'configure requires physical Downloads Documents Backups paths'
    for raw in "$@"; do [[ ! -L "$raw" ]] || fail "symlink root refused: $raw"; done
    downloads="$(physical "$1")"; documents="$(physical "$2")"; backups="$(physical "$3")"
    for p in "$downloads" "$documents" "$backups"; do [[ -d "$p" && ! -L "$p" ]] || fail "root missing/symlink: $p"; done
    python3 - "$downloads" "$documents" "$backups" <<'PY'
from pathlib import Path
import sys
roots=list(map(Path,sys.argv[1:]))
for root in roots:
    if root in (Path('/'),Path.home(),Path('/Users'),Path('/System'),Path('/Library'),Path('/Applications'),Path('/Volumes')):
        raise SystemExit('unsafe business root')
for i, first in enumerate(roots):
    for second in roots[i+1:]:
        if first==second or first in second.parents or second in first.parents:
            raise SystemExit('business roots overlap')
PY
    [[ "$(physical "$private_root")" == "$(physical "$HOME/Library/Application Support/HermesAgents/runtime")/$slug" ]] || fail 'private root mismatch'
    printf 'Private configuration: %s\nDownloads: %s\nDocuments: %s\nBackups: %s\n' "$private_root" "$downloads" "$documents" "$backups"
    umask 077
    mkdir -p -- "$private_root"
    [[ ! -e "$private_root/broker.json" ]] && cp -- "$project_dir/config/broker.example.json" "$private_root/broker.json" || true
    [[ ! -e "$private_root/planner.config.yaml" ]] && cp -- "$project_dir/config/planner.config.yaml" "$private_root/planner.config.yaml" || true
    for f in telegram.token slack-bot.token slack-app.token planner.env planner-api.env; do
      [[ -e "$private_root/$f" ]] || : > "$private_root/$f"
      chmod 600 "$private_root/$f"
    done
    python3 - "$private_root" "$downloads" "$documents" "$backups" <<'PY'
import json,sys
from pathlib import Path
private,downloads,documents,backups=map(Path,sys.argv[1:])
paths={'PB_PLANNER_ENV_FILE':str(private/'planner-api.env'),'PB_HERMES_CONFIG':str(private/'planner.config.yaml'),
       'PB_DOWNLOADS':str(downloads),'PB_DOCUMENTS':str(documents),'PB_BACKUPS':str(backups),'PB_PRIVATE_DIR':str(private)}
target=private/'paths.env'
new=''.join(k+'='+json.dumps(v)+'\n' for k,v in paths.items())
if target.exists():
    old={}
    for line in target.read_text().splitlines():
        key,value=line.split('=',1)
        old[key]=json.loads(value) if value.startswith('"') else value
    if old != paths:
        raise SystemExit('paths.env already selects different roots; change it only during a controlled service stop')
else:
    target.write_text(new)
    target.chmod(0o600)
print('Created private placeholders; fill IDs, allowlists, key and tokens out of Git.')
PY
    ;;
  start|restart|stop|status|logs)
    [[ $# -eq 0 ]] || fail 'unexpected arguments'
    env_file="$private_root/paths.env"
    [[ -f "$env_file" ]] || fail "missing private paths file: $env_file"
    compose=(docker compose --project-directory "$project_dir" --env-file "$env_file" -f "$project_dir/compose.yaml")
    if [[ "$command" == start || "$command" == restart ]]; then
      python3 - "$env_file" <<'PY'
import json, sys
from pathlib import Path
values={}
for line in Path(sys.argv[1]).read_text().splitlines():
    if '=' not in line or line.lstrip().startswith('#'):
        continue
    key,value=line.split('=',1)
    values[key]=json.loads(value) if value.startswith('"') else value
for key in ('PB_DOWNLOADS','PB_DOCUMENTS','PB_BACKUPS'):
    raw=values.get(key)
    if not raw:
        raise SystemExit(f'missing {key} in paths.env')
    path=Path(raw).resolve(strict=False)
    if path == Path('/private/tmp') or Path('/private/tmp') in path.parents or path == Path('/tmp') or Path('/tmp') in path.parents:
        raise SystemExit(f'{key} points to a temporary test root; production start refused')
    if not path.is_dir() or Path(raw).is_symlink() or path == Path.home() or path in Path.home().parents:
        raise SystemExit(f'unsafe {key} root')
PY
      for f in broker.json telegram.token slack-bot.token slack-app.token planner.env planner-api.env; do
        [[ -s "$private_root/$f" && ! -L "$private_root/$f" ]] || fail "missing/empty private file: $f"
      done
      python3 "$project_dir/scripts/validate-private.py" "$private_root"
      docker info >/dev/null
      "${compose[@]}" config --quiet
    fi
    case "$command" in
      start) "${compose[@]}" up -d --build --wait ;;
      restart) "${compose[@]}" stop; "${compose[@]}" up -d --build --wait ;;
      stop) "${compose[@]}" stop ;;
      status) "${compose[@]}" ps ;;
      logs) "${compose[@]}" logs --no-color --tail=100 ;;
    esac
    ;;
  uninstall)
    [[ $# -ge 1 && "$1" == --dry-run || $# -eq 2 && "$1" == --confirm-archive ]] || fail 'uninstall --dry-run or --confirm-archive EXACT_ARCHIVE_PATH'
    deployed="$(check_path "$deploy_root/$slug" "$deploy_root")"
    printf 'Code deployment: %s (%s)\nPrivate data preserved: %s (%s)\nBackups preserved: %s (%s)\nVolumes preserved: %s, %s\n' "$deployed" "$(size "$deployed")" "$private_root" "$(size "$private_root")" "$backup_root" "$(size "$backup_root")" hermes-pere-blaise-data hermes-pere-blaise-broker-data
    if [[ "$1" == --dry-run ]]; then exit 0; fi
    archive="$(physical "$2")"; expected_archive="$(physical "$deploy_root/.archive")"
    [[ "$archive" == "$expected_archive"/pere-blaise-* && ! -e "$archive" ]] || fail 'archive path invalid/existing'
    "$project_dir/scripts/lifecycle.sh" stop
    mkdir -p -- "$private_root/logs"
    chmod 700 "$private_root/logs"
    docker compose --project-directory "$project_dir" --env-file "$private_root/paths.env" -f "$project_dir/compose.yaml" logs --no-color > "$private_root/logs/uninstall-$(date -u +%Y%m%dT%H%M%SZ).log"
    docker compose --project-directory "$project_dir" --env-file "$private_root/paths.env" -f "$project_dir/compose.yaml" down
    mkdir -p -- "$expected_archive"
    mv -- "$deployed" "$archive"
    printf 'Archived code: %s\n' "$archive"
    ;;
  purge)
    [[ $# -ge 1 && "$1" == --dry-run || $# -eq 3 && "$1" == --confirm && "$2" == 'PURGE pere-blaise' && "$3" == --reviewed ]] || fail 'purge --dry-run or purge --confirm "PURGE pere-blaise" --reviewed'
    deployed="$(check_path "$deploy_root/$slug" "$deploy_root")"
    private="$(check_path "$private_root" "$HOME/Library/Application Support/HermesAgents/runtime")"
    backups="$(check_path "$backup_root" "$HOME/Library/Application Support/HermesAgents/backups")"
    printf 'PURGE PREVIEW\nCode: %s (%s)\nSecrets/state/logs: %s (%s)\nBackups: %s (%s)\nVolume hermes-pere-blaise-data: %s\nVolume hermes-pere-blaise-broker-data: %s\nDownloads/Documents: EXCLUDED\n' "$deployed" "$(size "$deployed")" "$private" "$(size "$private")" "$backups" "$(size "$backups")" "$(volume_size hermes-pere-blaise-data)" "$(volume_size hermes-pere-blaise-broker-data)"
    if [[ -d "$deploy_root/.archive" ]]; then
      find "$deploy_root/.archive" -maxdepth 1 -type d -name 'pere-blaise-*' -print
    fi
    if [[ "$1" == --dry-run ]]; then exit 0; fi
    if [[ -d "$deploy_root/.archive" ]] && find "$deploy_root/.archive" -maxdepth 1 -type d -name 'pere-blaise-*' -print -quit | grep -q .; then
      fail 'archived deployments exist; review them separately before full purge'
    fi
    if [[ -f "$private/paths.env" ]]; then
      python3 - "$private/paths.env" "$backups" <<'PY'
import json,sys
from pathlib import Path
items={}
for line in Path(sys.argv[1]).read_text().splitlines():
    if '=' in line:
        key,value=line.split('=',1)
        items[key]=json.loads(value) if value.startswith('"') else value
if Path(items.get('PB_BACKUPS','')).resolve()!=Path(sys.argv[2]):
    raise SystemExit('configured backup root differs from purge scope; stop')
PY
    fi
    [[ -t 0 ]] || fail 'interactive terminal required for purge'
    read -r -p 'Type the exact paths above, separated by a space: ' answer
    [[ "$answer" == "$deployed $private $backups" ]] || fail 'confirmation mismatch'
    if [[ -e "$private/paths.env" ]]; then
      "$project_dir/scripts/lifecycle.sh" stop
      docker compose --project-directory "$project_dir" --env-file "$private/paths.env" -f "$project_dir/compose.yaml" down
    fi
    [[ ! -e "$deployed" ]] || rm -rf -- "$deployed"
    [[ ! -e "$private" ]] || rm -rf -- "$private"
    [[ ! -e "$backups" ]] || rm -rf -- "$backups"
    for volume in hermes-pere-blaise-data hermes-pere-blaise-broker-data; do
      if docker volume inspect "$volume" >/dev/null 2>&1; then docker volume rm "$volume"; fi
    done
    ;;
  *) fail "unknown command: $command" ;;
esac
