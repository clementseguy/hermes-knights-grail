#!/usr/bin/env bash
set -euo pipefail

root_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
set -a
source "$root_dir/config/runner.env"
set +a
export JAVA_HOME="$YVAIN_HOME/jdk/temurin-21/Contents/Home"
export ANDROID_SDK_ROOT="$YVAIN_ANDROID_SDK"
export PATH="$JAVA_HOME/bin:$ANDROID_SDK_ROOT/cmdline-tools/latest/bin:$ANDROID_SDK_ROOT/platform-tools:$ANDROID_SDK_ROOT/emulator:$YVAIN_HOME/maestro/bin:$PATH"
export MAESTRO_CLI_NO_ANALYTICS=true
base="${1:?base SHA required}"
head="${2:?head SHA required}"
enforce="${3:-false}"
story="${4:-}"
run_id="$(date -u +%Y%m%dT%H%M%SZ)-${head:0:12}"
report_dir="$root_dir/reports/$run_id"
mkdir -p "$report_dir"

args=(--app-dir "$NEXTARGET_APP_DIR" --base "$base" --head "$head"
  --manifest "$root_dir/qa/manifest.json" --output "$report_dir/selection.json")
[[ "$enforce" == "true" ]] && args+=(--enforce)
[[ -n "$story" ]] && args+=(--story "$story")
python3 "$root_dir/scripts/select_cases.py" "${args[@]}"

docker compose -f "$NEXTARGET_SERVER_DIR/docker-compose.staging.yml" up -d --build --wait
# Chaque recette démarre avec les seules données déterministes prévues pour QA.
# La commande est protégée côté serveur : environnement staging + SQLite locale.
docker compose -f "$NEXTARGET_SERVER_DIR/docker-compose.staging.yml" exec -T \
  nextarget-staging python -m scripts.qa_data reset
python3 - "$report_dir/selection.json" <<'PY' > "$report_dir/cases.jsonl"
import json, sys
for case in json.load(open(sys.argv[1], encoding='utf-8'))['cases']:
    print(json.dumps(case))
PY
if [[ ! -s "$report_dir/cases.jsonl" ]]; then
  echo "Yvain: aucune recette prête; rapport: $report_dir"
  exit 0
fi
cd "$NEXTARGET_APP_DIR"
cases=()
while IFS= read -r selected_case; do
  cases+=("$selected_case")
done < "$report_dir/cases.jsonl"
for case in "${cases[@]}"; do
  kind=$(python3 -c 'import json,sys; print(json.loads(sys.argv[1])["kind"])' "$case")
  target=$(python3 -c 'import json,sys; print(json.loads(sys.argv[1])["target"])' "$case")
  name=$(python3 -c 'import json,sys; print(json.loads(sys.argv[1])["id"])' "$case")
  case "$kind" in
    flutter_test)
      flutter test "$target" </dev/null 2>&1 | tee "$report_dir/$name.log" || {
        printf '%s\n' "$name" >> "$report_dir/failed-cases.txt"
        exit 1
      }
      ;;
    maestro)
      command -v maestro >/dev/null || { echo "Maestro requis." >&2; exit 2; }
      bash "$root_dir/scripts/ensure_emulator.sh"
      flutter build apk --debug --dart-define=NEXTARGET_SERVER_URL=http://10.0.2.2:18000
      adb -s "$YVAIN_DEVICE" install -r build/app/outputs/flutter-apk/app-debug.apk >/dev/null
      bash "$root_dir/scripts/reset-local-app-data.sh"
      maestro_args=(
        --device "$YVAIN_DEVICE"
        --format JUNIT
        --output "$report_dir/$name.junit.xml"
        --test-output-dir "$report_dir/$name-artifacts"
        "$root_dir/$target"
      )
      if ! maestro test "${maestro_args[@]}" </dev/null 2>&1 | tee "$report_dir/$name.log"; then
        bash "$root_dir/scripts/reset-local-app-data.sh"
        if ! maestro test "${maestro_args[@]}" </dev/null 2>&1 | tee -a "$report_dir/$name.log"; then
          adb -s "$YVAIN_DEVICE" exec-out screencap -p > "$report_dir/$name.png" || true
          adb -s "$YVAIN_DEVICE" logcat -d -t 250 > "$report_dir/$name.log" || true
          printf '%s\n' "$name" >> "$report_dir/failed-cases.txt"
          exit 1
        fi
      fi
      ;;
    *) echo "Type de recette inconnu: $kind" >&2; exit 2 ;;
  esac
done
echo "Yvain: recette terminée; rapport: $report_dir"
