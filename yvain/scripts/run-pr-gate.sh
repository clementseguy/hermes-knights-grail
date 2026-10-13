#!/usr/bin/env bash
set -euo pipefail

# Gate local d'une PR applicative vers dev. Le premier argument évite
# d'inverser la comparaison Git : base origin/dev, tête branche de la PR.
root_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
kind="${1:-}"
head="${2:-}"

if [[ "$kind" != "feature" && "$kind" != "fix" ]] || [[ -z "$head" ]]; then
  echo "Usage: bash scripts/run-pr-gate.sh <feature|fix> <branche-ou-ref>" >&2
  exit 2
fi

case "$kind" in
  feature) expected_prefix="feature/" ;;
  fix) expected_prefix="fix/" ;;
esac
if [[ "$head" != "$expected_prefix"* ]]; then
  echo "Branche invalide : une PR $kind doit commencer par $expected_prefix" >&2
  exit 2
fi

set -a
source "$root_dir/config/runner.env"
set +a
if ! git -C "$NEXTARGET_APP_DIR" rev-parse --verify --quiet "origin/dev^{commit}" >/dev/null; then
  echo "Référence origin/dev introuvable. Exécuter git fetch origin dev." >&2
  exit 2
fi
if ! git -C "$NEXTARGET_APP_DIR" rev-parse --verify --quiet "$head^{commit}" >/dev/null; then
  echo "Référence de tête introuvable : $head" >&2
  exit 2
fi

exec bash "$root_dir/scripts/run-recipe.sh" origin/dev "$head" true
