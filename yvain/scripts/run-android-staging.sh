#!/usr/bin/env bash
# Launch the DEBUG app only after checking the local staging server revision.
set -euo pipefail

usage() {
  printf 'Usage: scripts/run-android-staging.sh <server-commit-sha> [--apk]\n' >&2
  exit 2
}

fail() {
  printf 'Error: %s\n' "$*" >&2
  exit 1
}

[[ $# -eq 1 || ( $# -eq 2 && "$2" == "--apk" ) ]] || usage
expected_revision="$1"
mode="${2:-run}"
[[ "$expected_revision" =~ ^[0-9a-f]{40}$ ]] || fail "Expected a full Git commit SHA."

runner_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
if [[ -z "${NEXTARGET_APP_DIR:-}" ]]; then
  [[ -f "$runner_root/config/runner.env" ]] \
    || fail "Missing runner.env with NEXTARGET_APP_DIR."
  set -a
  source "$runner_root/config/runner.env"
  set +a
fi
[[ -f "$NEXTARGET_APP_DIR/pubspec.yaml" ]] \
  || fail "NEXTARGET_APP_DIR does not point to NexTarget-app."
if [[ -z "${JAVA_HOME:-}" && -n "${YVAIN_HOME:-}" ]]; then
  export JAVA_HOME="$YVAIN_HOME/jdk/temurin-21/Contents/Home"
fi
if command -v adb >/dev/null 2>&1; then
  adb_bin="$(command -v adb)"
elif [[ -x "${ANDROID_HOME:-}/platform-tools/adb" ]]; then
  adb_bin="${ANDROID_HOME}/platform-tools/adb"
elif [[ -x "$HOME/Library/Android/sdk/platform-tools/adb" ]]; then
  adb_bin="$HOME/Library/Android/sdk/platform-tools/adb"
else
  fail "adb is required to connect the Android emulator."
fi

device="${NEXTARGET_QA_DEVICE:-}"
if [[ -z "$device" ]]; then
  devices="$("$adb_bin" devices | awk '$1 ~ /^emulator-/ && $2 == "device" {print $1}')"
  [[ $(printf '%s\n' "$devices" | sed '/^$/d' | wc -l | tr -d ' ') -eq 1 ]] \
    || fail "Start exactly one emulator or set NEXTARGET_QA_DEVICE."
  device="$devices"
fi

"$adb_bin" -s "$device" get-state >/dev/null \
  || fail "Android device $device is unavailable."
"$adb_bin" -s "$device" reverse tcp:18000 tcp:18000 \
  || fail "Unable to connect the emulator to local staging port 18000."

health="$(curl --fail --silent --show-error --max-time 5 http://127.0.0.1:18000/health)" \
  || fail "Local staging is unavailable on port 18000."
actual_revision="$(jq -r 'if .status == "ok" and .environment == "staging" then .revision // empty else empty end' <<<"$health")" \
  || fail "Local staging returned invalid health data."
[[ "$actual_revision" == "$expected_revision" ]] \
  || fail "Local staging revision does not match $expected_revision."

printf 'Launching DEBUG app against local staging at %s.\n' "$actual_revision"
cd "$NEXTARGET_APP_DIR"
if [[ "$mode" == "--apk" ]]; then
  exec flutter build apk --debug \
    --dart-define=NEXTARGET_SERVER_URL=http://127.0.0.1:18000 \
    --dart-define="NEXTARGET_QA_SERVER_SHA=$expected_revision"
fi
exec flutter run --debug -d "$device" \
  --dart-define=NEXTARGET_SERVER_URL=http://127.0.0.1:18000 \
  --dart-define="NEXTARGET_QA_SERVER_SHA=$expected_revision"
