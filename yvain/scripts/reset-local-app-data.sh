#!/usr/bin/env bash
set -euo pipefail

root_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
set -a
source "$root_dir/config/runner.env"
set +a
export ANDROID_SDK_ROOT="$YVAIN_ANDROID_SDK"
export PATH="$ANDROID_SDK_ROOT/platform-tools:$PATH"

# Remise à zéro complète, indépendante de l'interface : Hive, préférences,
# cache et éventuels jetons de l'APK sont supprimés par Android.
adb -s "$YVAIN_DEVICE" shell pm clear com.example.tir_sportif >/dev/null
adb -s "$YVAIN_DEVICE" shell monkey -p com.example.tir_sportif 1 >/dev/null
echo "Données locales NexTarget réinitialisées sur $YVAIN_DEVICE."
