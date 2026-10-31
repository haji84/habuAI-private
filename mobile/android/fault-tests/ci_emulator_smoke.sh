#!/usr/bin/env bash
# Synthetic Android emulator smoke test. Never use, print, or upload owner GPS.
set -euo pipefail

PKG=org.habuai.field
APK=mobile/android/app/build/outputs/apk/debug/app-debug.apk
test -f "$APK"
adb install -r "$APK" >/dev/null
adb shell cmd location set-location-enabled true
adb shell pm grant "$PKG" android.permission.ACCESS_COARSE_LOCATION
adb shell pm grant "$PKG" android.permission.ACCESS_FINE_LOCATION
adb shell pm grant "$PKG" android.permission.POST_NOTIFICATIONS

click_button() {
  local prefix="$1"
  adb shell uiautomator dump /sdcard/window.xml >/dev/null
  local point
  point="$(adb exec-out cat /sdcard/window.xml | python3 -c '
import re, sys, xml.etree.ElementTree as ET
root = ET.fromstring(sys.stdin.read())
matches = [n.attrib["bounds"] for n in root.iter()
           if n.attrib.get("text", "").startswith(sys.argv[1])
           and "bounds" in n.attrib]
if not matches:
    sys.exit("Requested button not found")
x1, y1, x2, y2 = map(int, re.findall(r"\d+", matches[0]))
print((x1 + x2) // 2, (y1 + y2) // 2)
' "$prefix")"
  adb shell input tap $point
}

track_name() {
  adb shell run-as "$PKG" ls files/private-tracks | tr -d '\r' |
    grep -E '^[0-9a-f-]{36}\.ndjson$' | head -n 1
}

fix_count() {
  local track
  track="$(track_name)"
  test -n "$track"
  # Inspect synthetic records inside CI only; output point COUNT, not coordinates.
  adb exec-out run-as "$PKG" cat "files/private-tracks/$track" |
    python3 -c 'import json,sys; print(sum(1 for line in sys.stdin if line.strip() and json.loads(line).get("kind") == "fix"))'
}

require_increase() {
  local baseline="$1" label="$2" count
  for i in $(seq 1 10); do
    count="$(fix_count)"
    if (( count > baseline )); then
      printf 'PASS: %s (synthetic fixes: %s)\n' "$label" "$count"
      CURRENT_COUNT="$count"
      return
    fi
    sleep 4
  done
  echo "::error::$label: synthetic GPS fix count did not increase" >&2
  exit 1
}

adb shell am start -n "$PKG/.MainActivity" >/dev/null
sleep 3
click_button "探索開始"
sleep 2
test -n "$(track_name)"
CURRENT_COUNT=0

# Emulator-only synthetic locations, unrelated to any real exploration route.
adb emu geo fix -73.9857 40.7484 >/dev/null
require_increase "$CURRENT_COUNT" "GPS while screen on"

adb shell input keyevent KEYCODE_SLEEP
sleep 2
adb emu geo fix -73.9849 40.7492 >/dev/null
require_increase "$CURRENT_COUNT" "GPS while screen locked"

# Disable network transports. This does not assert physical GPS reliability.
adb shell svc wifi disable
adb shell svc data disable
sleep 2
adb emu geo fix -73.9838 40.7503 >/dev/null
require_increase "$CURRENT_COUNT" "GPS with emulator network disabled"

adb shell input keyevent KEYCODE_WAKEUP
adb shell wm dismiss-keyguard || true
adb shell am start -n "$PKG/.MainActivity" >/dev/null
sleep 3
click_button "探索終了"
sleep 3
stop_count="$(fix_count)"
adb emu geo fix -73.9827 40.7514 >/dev/null
sleep 8
test "$(fix_count)" -eq "$stop_count" || {
  echo "::error::GPS fixes increased after explicit Stop" >&2
  exit 1
}
echo "PASS: no new fixes after explicit Stop. No artifacts or coordinates uploaded."
echo "LIMIT: emulator smoke is not a 30-minute physical-device screen-lock test."
