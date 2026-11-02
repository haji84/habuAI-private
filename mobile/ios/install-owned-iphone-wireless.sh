#!/usr/bin/env bash
# HABU FIELD: owner-initiated, physical-iPhone-only local development install.
# No GitHub push, no cloud GPS sync, no App Store/TestFlight distribution.
# This script does not change the original checkout or the user's JARVIS app.
set -Eeuo pipefail

say() { printf '%s\n' "$*"; }
stop() { printf 'STOP: %s\n' "$*" >&2; exit 2; }

[[ "$(uname -s)" == "Darwin" ]] || stop "MacBookで実行してください。"
for tool in git xcrun xcodebuild xcodegen python3 security mktemp tar; do
  command -v "$tool" >/dev/null 2>&1 || stop "$tool が見つかりません。"
done
xcodebuild -version >/dev/null 2>&1 || stop "Xcodeの初期設定を完了してください。"

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(git -C "$HERE" rev-parse --show-toplevel)" || stop "Gitリポジトリ内で実行してください。"
[[ -f "$REPO/mobile/ios/project.yml" ]] || stop "ハブAIのiOSプロジェクトが見つかりません。"
HEAD="$(git -C "$REPO" rev-parse HEAD)"
[[ "$HEAD" =~ ^[0-9a-f]{40}$ ]] || stop "コミットを確定できません。"
say "対象コミット: ${HEAD:0:12} (作業中のInfo.plistは一切変更しません)"

# Never use a partial filename or a stale iPhone UUID from another project.
# Developer device identifiers and signing information are kept local.
temp="$(mktemp -d "${TMPDIR:-/tmp/}habu-owned-iphone.XXXXXX")"
cleanup() {
  # Only a unique, script-created temporary folder. Source repo untouched.
  if [[ "$temp" == *"/habu-owned-iphone."* && -d "$temp" ]]; then
    rm -rf -- "$temp"
  fi
}
trap cleanup EXIT

device_json="$temp/devices.json"
if ! xcrun devicectl list devices --json-output "$device_json" >/dev/null 2>&1; then
  stop "Device Hubから実機一覧を取得できません。iPhoneを解除しWi-Fiを確認してください。"
fi

# Require EXACTLY ONE paired and connected iPhone 13 Pro (hardware iPhone14,2).
# Refuse to install on a different iPhone or an ambiguous multi-device match.
device_id="$(python3 - "$device_json" <<'PY'
import json,sys
from pathlib import Path
try:
    devices=json.loads(Path(sys.argv[1]).read_text(encoding="utf-8")).get("result",{}).get("devices",[])
except (OSError,ValueError,TypeError):
    raise SystemExit(1)
matches=[]
for d in devices:
    hw=d.get("hardwareProperties") or {}
    con=d.get("connectionProperties") or {}
    if (hw.get("productType") == "iPhone14,2"
        and con.get("pairingState") == "paired"
        and con.get("tunnelState") == "connected"):
        identifier=d.get("identifier") or hw.get("udid")
        if isinstance(identifier,str) and identifier:
            matches.append(identifier)
if len(matches) != 1:
    raise SystemExit(1)
print(matches[0])
PY
)" || stop "iPhone 13 Proの接続済み候補が1台に特定できません。iPhoneを解除し同じWi-Fiを確認してください。"
say "接続済みiPhone 13 Proを1台確認（識別番号は表示しません）"

# A unique existing signing identity is required. Never print or upload Apple
# account names, email addresses, certificate hashes, or Team IDs.
team="${HABU_DEVELOPMENT_TEAM:-}"
if [[ -z "$team" ]]; then
  team="$(security find-identity -v -p codesigning 2>/dev/null | python3 -c '
import re,sys
teams=set()
for line in sys.stdin:
    if "Apple Development:" not in line and "iPhone Developer:" not in line:
        continue
    m=re.search(r"\(([A-Z0-9]{10})\)",line)
    if m: teams.add(m.group(1))
if len(teams)==1: print(next(iter(teams)))
')"
fi
if [[ ! "$team" =~ ^[A-Z0-9]{10}$ ]]; then
  stop "署名Teamを1つに特定できません。Xcode → Settings → AccountsでApple Accountを確認してください。既存Teamが複数ある場合はMac内で HABU_DEVELOPMENT_TEAM を設定します（ここにTeam IDを貼らない）。"
fi
say "既存の開発用署名Teamを確認（秘密情報は表示しません）"

# Make a clean detached snapshot from committed source. The local modified
# Info.plist and other unrelated working files remain untouched.
mkdir -p "$temp/source" "$temp/derived"
git -C "$REPO" archive "$HEAD" mobile/ios | tar -xf - -C "$temp/source"
cd "$temp/source/mobile/ios"
xcodegen generate --spec project.yml >/dev/null ||
  stop "XcodeGenでプロジェクトを生成できません。"
say "iPhone用の署名付きDebugビルドを開始"

# Provisioning updates may use the Apple Account already connected in Xcode.
# User invoked this script for installing only onto their own paired device.
# No paid Developer Program enrollment or distribution is attempted.
if ! xcodebuild \
    -project HabuFieldRecorder.xcodeproj -scheme HabuFieldRecorder \
    -configuration Debug -destination "platform=iOS,id=$device_id" \
    -derivedDataPath "$temp/derived" \
    -allowProvisioningUpdates \
    CODE_SIGN_STYLE=Automatic DEVELOPMENT_TEAM="$team" \
    -quiet build >"$temp/build.log" 2>&1; then
  if grep -Eiq 'No Accounts|No profiles|Signing|provision|certificate|development team' "$temp/build.log"; then
    stop "SIGNING_FAILED: 既存Apple Accountの署名/プロビジョニングが不足しています。Xcode → Settings → Accountsを確認してください。パスワードや証明書は送らないでください。"
  fi
  stop "BUILD_FAILED: iPhone用ビルドに失敗しました。詳細ログには署名情報が含まれ得るため自動共有しません。"
fi

app="$temp/derived/Build/Products/Debug-iphoneos/HabuFieldRecorder.app"
[[ -d "$app" ]] || stop "iPhone用の署名済み.appが生成されませんでした。"
say "実機ビルド成功。iPhoneへのローカルインストールを開始"

# A different bundle ID from JARVIS; does not uninstall or erase other apps.
if ! xcrun devicectl device install app --device "$device_id" "$app" >"$temp/install.log" 2>&1; then
  stop "DEVICE_INSTALL_FAILED: iPhoneのロック解除・Developer Mode・Wi-Fi接続を確認してください。"
fi
say "OWNED_IPHONE_INSTALL_PASS: HABU FIELD GPSをiPhone 13 Proにインストールしました。"

if xcrun devicectl device process launch --device "$device_id" org.habuai.fieldrecorder >"$temp/launch.log" 2>&1; then
  say "OWNED_IPHONE_LAUNCHED: 実機でアプリの起動要求に成功しました。"
else
  say "OWNED_IPHONE_LAUNCH_PENDING: インストール済み。iPhoneでHABU FIELD GPSを開いてください。"
fi
say "次の検証: 画面ロック30分、通信オフ10分、保存失敗復旧。実機試験は未合格です。"
