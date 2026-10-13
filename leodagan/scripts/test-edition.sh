#!/usr/bin/env bash
set -euo pipefail

root_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$root_dir"
export HERMES_UID="$(id -u)"
export HERMES_GID="$(id -g)"

./scripts/bootstrap.sh
docker compose up -d leodagan

echo 'Attente du scheduler Hermes (maximum 90 secondes)...'
scheduler_ready=false
for _ in {1..9}; do
  scheduler_status=$(docker compose exec -T leodagan hermes cron status 2>&1 || true)
  if grep -Fq 'Gateway is running' <<<"$scheduler_status"; then
    scheduler_ready=true
    break
  fi
  sleep 10
done
if [[ "$scheduler_ready" != true ]]; then
  printf '%s\n' "$scheduler_status" >&2
  echo 'Le scheduler Hermes n est pas prêt ; le test est abandonné.' >&2
  exit 1
fi

job_output=$(docker compose exec -T leodagan hermes cron create \
  '5m' \
  'Prépare une seule édition LinkedIn de test en appliquant le skill leodagan. Travaille uniquement dans /review-inbox, ne publie jamais et termine par un récapitulatif du dossier créé.' \
  --name 'Léodagan test ponctuel' \
  --skill leodagan \
  --workdir /review-inbox \
  --provider openai-codex \
  --model gpt-6-luna \
  --reasoning-effort low \
  --deliver local \
  --failure-deliver local \
  --repeat 1)

printf '%s\n' "$job_output"
job_id=$(printf '%s\n' "$job_output" | sed -n 's/^Created job: \([^ ]*\).*/\1/p')
if [[ -z "$job_id" ]]; then
  echo 'Impossible de retrouver l identifiant du job de test.' >&2
  exit 1
fi

cleanup() {
  docker compose exec -T leodagan hermes cron pause "$job_id" >/dev/null 2>&1 || true
}
trap cleanup EXIT

echo "Déclenchement immédiat du test $job_id..."
if ! docker compose exec -T leodagan hermes cron run "$job_id"; then
  echo 'Le job de test a échoué avant la validation du livrable.' >&2
  docker compose exec -T leodagan hermes cron runs --limit 1 >&2 || true
  exit 1
fi

echo 'Attente du livrable de test (maximum 10 minutes)...'
deadline=$((SECONDS + 600))
while (( SECONDS < deadline )); do
  newest_bundle=''
  newest_mtime=0
  while IFS= read -r -d '' candidate; do
    candidate_mtime=$(stat -f '%m' "$candidate")
    if (( candidate_mtime > newest_mtime )); then
      newest_bundle=$candidate
      newest_mtime=$candidate_mtime
    fi
  done < <(find "$root_dir/review-inbox" -mindepth 1 -maxdepth 1 -type d \
    -name '*T*Z-*-??????' -print0)
  if [[ -n "${newest_bundle:-}" ]] && [[ -f "$newest_bundle/README.md" ]]; then
    "$root_dir/tests/verify-review-bundle.sh" "$newest_bundle"
    exit 0
  fi
  sleep 10
done

echo 'Aucun livrable de test valide dans le délai imparti.' >&2
exit 1
