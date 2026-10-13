#!/usr/bin/env bash
set -euo pipefail

root_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
compose_file="$root_dir/compose.yaml"
config_file="$root_dir/config/config.yaml"
skill_file="$root_dir/skills/leodagan/SKILL.md"
todo_file="$root_dir/TODO.md"

require() {
  local pattern=$1
  local file=$2
  grep -Fq -- "$pattern" "$file" || {
    echo "Missing '$pattern' in $file" >&2
    exit 1
  }
}

forbid() {
  local pattern=$1
  local file=$2
  if grep -Fq -- "$pattern" "$file"; then
    echo "Forbidden '$pattern' in $file" >&2
    exit 1
  fi
}

require 'name: hermes-leodagan' "$compose_file"
require 'container_name: hermes-leodagan' "$compose_file"
require 'cap_drop:' "$compose_file"
require '      - CHOWN' "$compose_file"
require '      - DAC_OVERRIDE' "$compose_file"
require '      - SETGID' "$compose_file"
require '      - SETUID' "$compose_file"
require 'no-new-privileges:true' "$compose_file"
require 'pids_limit: 64' "$compose_file"
require 'mem_limit: 768m' "$compose_file"
require 'cpus: 1.0' "$compose_file"
require 'healthcheck:' "$compose_file"
require 'HERMES_WRITE_SAFE_ROOT: /opt/data:/review-inbox' "$compose_file"
forbid 'network_mode: host' "$compose_file"
require 'provider: openai-codex' "$config_file"
require 'default: gpt-6-luna' "$config_file"
forbid '    - browser' "$config_file"
require 'strictement unique pour cette exécution' "$skill_file"
require '[CRON_FAILURE]' "$skill_file"
require 'Registre de décision' "$root_dir/README.md"
require 'Conditions de reprise' "$todo_file"
require 'Notifications Telegram' "$root_dir/docs/telegram-notifications.md"
require "Matrice d'accès de Léodagan" "$root_dir/docs/access-matrix.md"

echo 'Configuration Léodagan : contrôles statiques réussis.'
