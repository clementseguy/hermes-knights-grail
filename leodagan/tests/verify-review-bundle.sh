#!/usr/bin/env bash
set -euo pipefail

bundle_dir=${1:?Usage: verify-review-bundle.sh /absolute/path/to/review-bundle}
bundle_name=$(basename "$bundle_dir")

fail() {
  echo "Review bundle validation failed: $*" >&2
  exit 1
}

[[ -d "$bundle_dir" ]] || fail "directory does not exist: $bundle_dir"
[[ "$bundle_name" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{6}Z-[a-z0-9-]+-[a-z0-9]{6}$ ]] || \
  fail "directory name is not a unique run identifier: $bundle_name"

for file in README.md veille.md sources.md; do
  [[ -s "$bundle_dir/$file" ]] || fail "missing or empty $file"
done

if grep -Fq 'PRET_A_RELIRE' "$bundle_dir/README.md"; then
  [[ -s "$bundle_dir/post.md" ]] || fail "PRET_A_RELIRE requires post.md"
  [[ -s "$bundle_dir/image-prompt.md" ]] || fail "PRET_A_RELIRE requires image-prompt.md"
elif grep -Fq 'NON_PUBLIABLE' "$bundle_dir/README.md"; then
  [[ ! -e "$bundle_dir/post.md" ]] || fail "NON_PUBLIABLE must not contain post.md"
  [[ ! -e "$bundle_dir/image-prompt.md" ]] || fail "NON_PUBLIABLE must not contain image-prompt.md"
else
  fail "README.md has no recognised editorial state"
fi

echo "Review bundle validated: $bundle_dir"
