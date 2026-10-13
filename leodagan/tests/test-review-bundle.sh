#!/usr/bin/env bash
set -euo pipefail

root_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
fixture_root=$(mktemp -d)
trap 'rm -rf "$fixture_root"' EXIT

non_publishable="$fixture_root/2026-10-13T120000Z-veille-europe-abc123"
mkdir -p "$non_publishable"
printf '%s\n' '# Édition' 'État : NON_PUBLIABLE' > "$non_publishable/README.md"
printf '%s\n' '# Veille' > "$non_publishable/veille.md"
printf '%s\n' '# Sources' > "$non_publishable/sources.md"
"$root_dir/tests/verify-review-bundle.sh" "$non_publishable"

ready="$fixture_root/2026-10-13T120001Z-veille-europe-def456"
mkdir -p "$ready"
printf '%s\n' '# Édition' 'État : PRET_A_RELIRE' > "$ready/README.md"
printf '%s\n' '# Veille' > "$ready/veille.md"
printf '%s\n' '# Sources' > "$ready/sources.md"
printf '%s\n' '# Post' > "$ready/post.md"
printf '%s\n' '# Prompt visuel' > "$ready/image-prompt.md"
"$root_dir/tests/verify-review-bundle.sh" "$ready"

echo 'Review bundle fixtures: success.'
