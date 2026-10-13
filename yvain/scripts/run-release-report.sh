#!/usr/bin/env bash
set -euo pipefail

# Rapport non bloquant de la release candidate dev vers main.
root_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
exec bash "$root_dir/scripts/run-recipe.sh" origin/main dev false
