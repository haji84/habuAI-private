#!/usr/bin/env bash
# Non-destructive check for previously-paired physical iPhones.
# Reports only pairing and connectivity status. Never prints device name,
# identifier, serial number, IP address, certificates, or owner GPS.
set -euo pipefail

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "STOP: このチェックはMacBook専用です。"
  exit 2
fi
for command in xcrun python3 mktemp; do
  command -v "$command" >/dev/null 2>&1 || {
    echo "STOP: $command が見つかりません。"
    exit 2
  }
done

json_file="$(mktemp "${TMPDIR:-/tmp/}habu-iphone-check.XXXXXX")"
trap 'rm -f "$json_file"' EXIT

echo "iPhoneのペアリングとWi-Fi接続状態を確認中（読み取り専用）"
if ! xcrun devicectl list devices --json-output "$json_file" >/dev/null 2>&1; then
  echo "DEVICE_CHECK_UNAVAILABLE: XcodeのDevice Hubが利用可能か確認してください。"
  echo "Xcode 27: Xcode → Open Developer Tool → Device Hub"
  exit 2
fi

python3 - "$json_file" <<'PY'
import json
import sys
from pathlib import Path

try:
    payload = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
except (OSError, ValueError):
    print("DEVICE_CHECK_ERROR: デバイス情報を解析できません。")
    raise SystemExit(2)
devices = payload.get("result", {}).get("devices", []) or []
phones = []
for device in devices:
    props = device.get("deviceProperties") or {}
    hw = device.get("hardwareProperties") or {}
    connection = device.get("connectionProperties") or {}
    model = str(hw.get("productType") or "")
    platform = str(hw.get("platform") or "")
    # Names may contain personally identifying text. Use them only to
    # classify, never print them.
    name = str(props.get("name") or "")
    if not (model.startswith("iPhone") or ("iphone" in platform.lower()) or ("iphone" in name.lower())):
        continue
    pairing = str(connection.get("pairingState") or "unknown")
    tunnel = str(connection.get("tunnelState") or "unknown")
    transport = str(connection.get("transportType") or "unknown")
    phones.append((model, pairing, tunnel, transport))

print(f"検出したiPhone: {len(phones)}台")
for index, (model, pairing, tunnel, transport) in enumerate(phones, 1):
    print(f"候補{index}: モデルコード={model or '不明'} / ペアリング={pairing} / 通信={tunnel} / 接続方式={transport}")
if not phones:
    print("CHECK_RESULT: NOT_DISCOVERED")
    print("同じWi-Fi・iPhoneのロック解除・開発者モードを確認してください。")
    print("iOS 27以降ならDevice Hubの『＋ → Pair Nearby Device』でケーブルなしの初回ペアリングも可能です。")
elif any(pair == "paired" and tunnel in {"connected", "available"} for _, pair, tunnel, _ in phones):
    print("CHECK_RESULT: PAIRED_AND_CONNECTED_CANDIDATE")
    print("次工程: 署名済み実機ビルドの可否確認。これだけでは実機インストール成功ではありません。")
elif any(pair == "paired" for _, pair, _, _ in phones):
    print("CHECK_RESULT: PAIRED_BUT_NOT_CONNECTED")
    print("同じWi-Fi上でiPhoneを起こし、Device Hubから利用可能になっているか確認してください。")
else:
    print("CHECK_RESULT: PAIRING_REQUIRED_OR_UNKNOWN")
    print("iOS 27以降はDevice Hubから近くの端末をワイヤレスペアリングできます。")
PY
