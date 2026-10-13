#!/usr/bin/env bash
set -euo pipefail

root_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
runtime_dir="$root_dir/runtime"
mkdir -p "$runtime_dir/skills/yvain" "$root_dir/reports"
cp "$root_dir/config/config.yaml" "$runtime_dir/config.yaml"
cp "$root_dir/prompts/system.md" "$runtime_dir/yvain-policy.md"
cp "$root_dir/skills/yvain/SKILL.md" "$runtime_dir/skills/yvain/SKILL.md"
echo "Runtime Yvain initialisé dans $runtime_dir"
