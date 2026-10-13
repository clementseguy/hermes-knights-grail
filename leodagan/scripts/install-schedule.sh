#!/usr/bin/env bash
set -euo pipefail

root_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$root_dir"
export HERMES_UID="$(id -u)"
export HERMES_GID="$(id -g)"

./scripts/bootstrap.sh

docker compose up -d leodagan

if docker compose exec -T leodagan hermes cron list | grep -Fq 'Name:      Léodagan LinkedIn'; then
  echo 'La planification Léodagan existe déjà ; aucune seconde planification n est créée.'
  exit 0
fi

# The job is created paused: a human explicitly resumes it after the first
# manual test. The scheduler itself runs inside the isolated Hermes gateway.
docker compose exec -T leodagan hermes cron create \
  '0 21 * * 1,4' \
  'Prépare l édition LinkedIn demandée en appliquant le skill leodagan. Travaille uniquement dans /review-inbox et ne publie jamais.' \
  --name 'Léodagan LinkedIn' \
  --skill leodagan \
  --workdir /review-inbox \
  --provider openai-codex \
  --model gpt-6-luna \
  --reasoning-effort low \
  --deliver local \
  --failure-deliver local \
  --paused

echo 'Planification créée en pause. Lancez ./scripts/test-edition.sh puis reprenez-la via :'
echo 'docker compose exec leodagan hermes cron list'
