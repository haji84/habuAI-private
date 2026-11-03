#!/usr/bin/env bash
# HABU FIELD: launch the existing iOS prototype in a Mac iPhone Simulator.
# No Apple ID, device cable, distribution signing, or GPS upload required.
set -Eeuo pipefail

fail() { printf 'STOP: %s\n' "$*" >&2; exit 1; }

[[ "$(uname -s)" == 'Darwin' ]] || fail 'MacBook上で実行してください。'
for cmd in xcodebuild xcodegen xcrun xcode-select python3 open; do
  command -v "$cmd" >/dev/null 2>&1 || fail "$cmd が見つかりません。"
done
xcodebuild -version >/dev/null || fail 'Xcodeの初期設定が未完了です。'

IOS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
[[ -f "$IOS_DIR/project.yml" ]] || fail 'mobile/ios/project.yml が見つかりません。'

# Prefer a booted iPhone, then any available iPhone, then an available iPad.
# The Simulator runtime is separate from the Xcode app installation.
DEVICE_ID="$(xcrun simctl list -j devices available | python3 -c '
import json, sys
raw = json.load(sys.stdin)
choices = []
for runtime, devices in raw.get("devices", {}).items():
    if "iOS" not in runtime:
        continue
    for device in devices:
        if device.get("isAvailable", True) is False:
            continue
        udid = device.get("udid")
        if udid:
            name = device.get("name", "")
            choices.append((0 if name.startswith("iPhone") else 1,
                            0 if device.get("state") == "Booted" else 1,
                            name, udid))
if choices:
    print(sorted(choices)[0][-1])
')" || fail 'Simulator一覧を取得できません。'
if [[ -z "$DEVICE_ID" ]]; then
  fail 'iOS Simulatorが未導入です。XcodeのSettings > ComponentsでiOS Simulatorを入れるか、ターミナルで xcodebuild -downloadPlatform iOS を実行してください。容量の大きいダウンロードなので自動では開始しません。'
fi

printf '使用するSimulator: %s\n' "$DEVICE_ID"
cd "$IOS_DIR"
xcodegen generate --spec project.yml

DERIVED_DIR="$HOME/Library/Developer/Xcode/DerivedData/HabuFieldRecorder-LocalSmoke"
printf 'アプリをビルドしています（iPhone実機ではありません）...\n'
xcodebuild -project HabuFieldRecorder.xcodeproj \
  -scheme HabuFieldRecorder -configuration Debug \
  -destination "platform=iOS Simulator,id=$DEVICE_ID" \
  -derivedDataPath "$DERIVED_DIR" CODE_SIGNING_ALLOWED=NO -quiet build

APP="$DERIVED_DIR/Build/Products/Debug-iphonesimulator/HabuFieldRecorder.app"
[[ -d "$APP" ]] || fail "ビルド済みアプリが見つかりません: $APP"

# Already-booted devices make simctl boot exit non-zero; bootstatus verifies readiness.
if ! xcrun simctl boot "$DEVICE_ID" >/dev/null 2>&1; then
  printf 'Simulatorは起動済みの可能性があります。状態を確認します。\n'
fi
xcrun simctl bootstatus "$DEVICE_ID" -b

# Install and launch via simctl first: the Simulator graphical application
# may be absent or not registered with macOS LaunchServices.
# Never prevent installation just because the viewer cannot be opened.
xcrun simctl install "$DEVICE_ID" "$APP"
xcrun simctl launch "$DEVICE_ID" org.habuai.fieldrecorder

XCODE_DEVELOPER_DIR="$(xcode-select -p)"
XCODE_CONTENTS_DIR="$(dirname "$XCODE_DEVELOPER_DIR")"
DEVICE_HUB_UI="${XCODE_CONTENTS_DIR}/Applications/DeviceHub.app"
SIMULATOR_UI="${XCODE_DEVELOPER_DIR}/Applications/Simulator.app"

# Xcode 27 moved the simulator GUI into Device Hub at Contents/Applications.
# Simulator.app is a legacy Xcode <=26 path. Do not reinstall Xcode or
# erase simulators just because the legacy standalone app does not exist.
if [[ -d "$DEVICE_HUB_UI" ]]; then
  printf 'Xcode 27 Device Hubを検出: %s\n' "$DEVICE_HUB_UI"
  if open -a "$DEVICE_HUB_UI"; then
    printf 'DEVICE_HUB_OPENED: Device Hubの起動要求に成功しました。\n'
    # Ask Device Hub to show the exact simulated device, if the URL handler
    # is supported. Failure must not invalidate the successful app launch.
    if open "devices://manage/select?id=${DEVICE_ID}" >/dev/null 2>&1; then
      printf 'DEVICE_HUB_SELECT_REQUESTED: %s\n' "$DEVICE_ID"
    else
      printf 'WARNING: Device Hubの端末選択リンクを開けません。Device Hubで該当iPhoneを選んでください。\n' >&2
    fi
  else
    printf 'WARNING: Device Hubの画面起動に失敗しました。GPSアプリ自体は起動済みです。\n' >&2
  fi
elif [[ -d "$SIMULATOR_UI" ]]; then
  if open -a "$SIMULATOR_UI" --args -CurrentDeviceUDID "$DEVICE_ID"; then
    printf 'SIMULATOR_UI_OPENED: 従来のSimulator画面起動要求に成功しました。\n'
  else
    printf 'WARNING: Simulator.appの画面起動に失敗しました。GPSアプリ自体は起動済みです。\n' >&2
  fi
elif open -b com.apple.iphonesimulator --args -CurrentDeviceUDID "$DEVICE_ID" >/dev/null 2>&1; then
  printf 'SIMULATOR_UI_OPENED: 従来のSimulator画面起動要求に成功しました。\n'
else
  printf 'WARNING: Simulator画面アプリを発見できません。XcodeのOpen Developer Tool > Device Hubを確認してください。\n' >&2
  printf '検査先: %s と %s\n' "$DEVICE_HUB_UI" "$SIMULATOR_UI" >&2
fi

printf '\nSIMULATOR_APP_LAUNCHED: HABU FIELDをsimctlで起動しました。\n'
printf '注意: Simulator画面の表示と実機GPS追跡の検証は別です。\n'
