#!/usr/bin/env bash
set -euo pipefail

root_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
temp_dir="$(mktemp -d "${TMPDIR:-/tmp}/yvain-staging-test.XXXXXX")"
trap 'rm -rf "$temp_dir"' EXIT
mkdir -p "$temp_dir/bin" "$temp_dir/app"
touch "$temp_dir/app/pubspec.yaml"

cat > "$temp_dir/bin/adb" <<'SH'
#!/usr/bin/env bash
if [[ "$1" == "devices" ]]; then
  printf 'List of devices attached\nemulator-5554\tdevice\n'
elif [[ "$1" == "-s" && ( "$3" == "get-state" || "$3" == "reverse" ) ]]; then
  exit 0
else
  exit 1
fi
SH
cat > "$temp_dir/bin/curl" <<'SH'
#!/usr/bin/env bash
printf '%s\n' "$FAKE_HEALTH"
SH
cat > "$temp_dir/bin/flutter" <<'SH'
#!/usr/bin/env bash
printf '%s\n' "$*" > "$QA_CAPTURE"
SH
chmod +x "$temp_dir/bin/adb" "$temp_dir/bin/curl" "$temp_dir/bin/flutter"

revision="$(printf 'a%.0s' {1..40})"
export NEXTARGET_APP_DIR="$temp_dir/app"
export NEXTARGET_QA_DEVICE=emulator-5554
export QA_CAPTURE="$temp_dir/flutter-args"
export PATH="$temp_dir/bin:$PATH"
export FAKE_HEALTH="{\"status\":\"ok\",\"environment\":\"staging\",\"revision\":\"$revision\"}"

bash "$root_dir/scripts/run-android-staging.sh" "$revision" --apk
rg -q -- 'build apk --debug' "$QA_CAPTURE"
rg -q -- "NEXTARGET_QA_SERVER_SHA=$revision" "$QA_CAPTURE"
rg -q -- 'NEXTARGET_SERVER_URL=http://127.0.0.1:18000' "$QA_CAPTURE"

rm "$QA_CAPTURE"
export FAKE_HEALTH='{"status":"ok","environment":"production","revision":"wrong"}'
if bash "$root_dir/scripts/run-android-staging.sh" "$revision" --apk >/dev/null 2>&1; then
  printf 'A non-staging server was accepted.\n' >&2
  exit 1
fi
[[ ! -e "$QA_CAPTURE" ]]
