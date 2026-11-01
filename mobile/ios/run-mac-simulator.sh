#!/usr/bin/env bash
# HABU FIELD: launch the existing iOS prototype in a Mac iPhone Simulator.
# No Apple ID, device cable, distribution signing, or GPS upload required.
set -Eeuo pipefail

fail() { printf 'STOP: %s\n' "$*" >&2; exit 1; }

[[ "$(uname -s)" == 'Darwin' ]] || fail 'MacBook上で実行してください。'
for cmd in xcodebuild xcodegen xcrun python3 open; do
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
open -a Simulator --args -CurrentDeviceUDID "$DEVICE_ID"
xcrun simctl install "$DEVICE_ID" "$APP"
xcrun simctl launch "$DEVICE_ID" org.habuai.fieldrecorder
printf '\nSIMULATOR_APP_LAUNCHED: HABU FIELDをMacBookのSimulatorで起動しました。\n'
printf '注意: 模擬位置情報は、画面ロック中の実GPS記録の証拠にはなりません。\n'
