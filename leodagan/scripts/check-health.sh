#!/usr/bin/env bash
set -euo pipefail

root_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$root_dir"
export HERMES_UID="$(id -u)"
export HERMES_GID="$(id -g)"

docker compose ps --status running --services | grep -Fxq leodagan || {
  echo 'ÉCHEC : le conteneur Léodagan ne fonctionne pas.' >&2
  exit 1
}

status=$(docker compose exec -T leodagan hermes cron status 2>&1)
printf '%s\n' "$status"
grep -Fq 'Gateway is running' <<<"$status" || {
  echo 'ÉCHEC : le scheduler Hermes ne confirme pas son état.' >&2
  exit 1
}

echo 'Santé Léodagan : OK.'
