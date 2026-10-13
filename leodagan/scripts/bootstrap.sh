#!/usr/bin/env bash
set -euo pipefail

root_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
runtime_dir="$root_dir/runtime"

mkdir -p "$runtime_dir/skills" "$root_dir/review-inbox"
cp "$root_dir/config/config.yaml" "$runtime_dir/config.yaml"
cp "$root_dir/prompts/editorial-policy.md" "$runtime_dir/editorial-policy.md"
cp "$root_dir/prompts/image-style.md" "$runtime_dir/image-style.md"
mkdir -p "$runtime_dir/skills/leodagan"
cp "$root_dir/skills/leodagan/SKILL.md" "$runtime_dir/skills/leodagan/SKILL.md"

echo "Profil Léodagan initialisé dans $runtime_dir"
