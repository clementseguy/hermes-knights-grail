#!/usr/bin/env bash
set -euo pipefail

# Installe un runtime Android dédié à Yvain sans modifier Homebrew ni /Applications.
# Les archives et composants sont publiés par Android Developers et Adoptium.
task_home="${YVAIN_HOME:-$HOME/.yvain}"
sdk_root="${YVAIN_ANDROID_SDK:-$HOME/Library/Android/sdk}"
jdk_dir="$task_home/jdk/temurin-21"
tools_dir="$sdk_root/cmdline-tools/latest"
mkdir -p "$task_home/jdk" "$sdk_root/cmdline-tools"

work_dir=$(mktemp -d)
trap 'rm -rf "$work_dir"' EXIT

if [[ ! -x "$jdk_dir/Contents/Home/bin/java" ]]; then
  jdk_archive="$work_dir/temurin.tar.gz"
  curl --fail --location --retry 3 \
    'https://api.adoptium.net/v3/binary/latest/21/ga/mac/x64/jdk/hotspot/normal/eclipse?project=jdk' \
    --output "$jdk_archive"
  archive_root=$(tar -tzf "$jdk_archive" | head -1 | cut -d/ -f1)
  tar -xzf "$jdk_archive" -C "$work_dir"
  mv "$work_dir/$archive_root" "$jdk_dir"
fi
export JAVA_HOME="$jdk_dir/Contents/Home"
export ANDROID_SDK_ROOT="$sdk_root"
export PATH="$JAVA_HOME/bin:$ANDROID_SDK_ROOT/cmdline-tools/latest/bin:$ANDROID_SDK_ROOT/platform-tools:$ANDROID_SDK_ROOT/emulator:$PATH"

if [[ ! -x "$tools_dir/bin/sdkmanager" ]]; then
  tools_archive="$work_dir/commandlinetools.zip"
  curl --fail --location --retry 3 \
    'https://dl.google.com/android/repository/commandlinetools-mac_x86_64-15859902_latest.zip' \
    --output "$tools_archive"
  unzip -q "$tools_archive" -d "$work_dir"
  mkdir -p "$tools_dir"
  mv "$work_dir/cmdline-tools"/* "$tools_dir/"
fi

# `sdkmanager` ferme son entrée dès la dernière licence ; `yes` reçoit alors
# SIGPIPE, ce qui n'est pas un échec avec `set -o pipefail`.
set +o pipefail
yes | sdkmanager --licenses >/dev/null
set -o pipefail
sdkmanager --install \
  'platform-tools' \
  'emulator' \
  'platforms;android-34' \
  'system-images;android-34;google_apis;x86_64'

avd_name="${YVAIN_AVD:-Yvain_Pixel_8_API_34}"
if ! emulator -list-avds | grep -Fxq "$avd_name"; then
  printf 'no\n' | avdmanager create avd \
    --name "$avd_name" \
    --package 'system-images;android-34;google_apis;x86_64' \
    --device 'pixel_8'
fi

echo "Runtime Android Yvain prêt : $avd_name"
