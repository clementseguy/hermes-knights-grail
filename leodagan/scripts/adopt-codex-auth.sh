#!/usr/bin/env bash
set -euo pipefail

# Copy the already logged-in Codex subscription into Léodagan's own Hermes
# home. The copy is necessary because Hermes refreshes OAuth credentials; two
# containers must never share a writable auth.json.
root_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
source_auth='/Users/clement/Library/Application Support/HermesFileControl/planner-auth.json'
target_auth="$root_dir/runtime/auth.json"

if [[ ! -f "$source_auth" ]]; then
  echo "Authentification source absente : $source_auth" >&2
  exit 1
fi

mkdir -p "$root_dir/runtime"
cp "$source_auth" "$target_auth"
chmod 600 "$target_auth"
echo "Authentification Codex copiée dans le runtime privé de Léodagan."
