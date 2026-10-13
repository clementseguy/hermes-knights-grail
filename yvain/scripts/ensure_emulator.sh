#!/usr/bin/env bash
set -euo pipefail

device="${YVAIN_DEVICE:-emulator-5554}"
avd="${YVAIN_AVD:?YVAIN_AVD is required}"
if [[ -n "${YVAIN_HOME:-}" && -n "${YVAIN_ANDROID_SDK:-}" ]]; then
  export JAVA_HOME="$YVAIN_HOME/jdk/temurin-21/Contents/Home"
  export ANDROID_SDK_ROOT="$YVAIN_ANDROID_SDK"
  export PATH="$JAVA_HOME/bin:$ANDROID_SDK_ROOT/platform-tools:$ANDROID_SDK_ROOT/emulator:$PATH"
fi
if adb -s "$device" get-state 2>/dev/null | grep -qx device; then exit 0; fi
command -v emulator >/dev/null || { echo "Android Emulator requis." >&2; exit 2; }
emulator -avd "$avd" -no-audio -no-boot-anim -no-snapshot -gpu host >"${TMPDIR:-/tmp}/yvain-emulator.log" 2>&1 &
adb -s "$device" wait-for-device
deadline=$((SECONDS + 180))
until [[ "$(adb -s "$device" shell getprop sys.boot_completed | tr -d '\r')" == "1" ]]; do
  (( SECONDS < deadline )) || { echo "Démarrage AVD expiré." >&2; exit 1; }
  sleep 2
done
