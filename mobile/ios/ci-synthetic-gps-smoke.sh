#!/usr/bin/env bash
# Isolated CI acceptance: synthetic Simulator coordinates, never owner GPX.
# This does NOT prove locked-screen behavior on a physical iPhone.
set -Eeuo pipefail
fail() { echo "SYNTHETIC_GPS_FAIL: $*" >&2; exit 1; }
[[ "$(uname -s)" == "Darwin" ]] || fail "Mac runner required"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$HERE"
command -v xcodegen >/dev/null || fail "XcodeGen missing"
xcodegen generate --spec project.yml >/dev/null

DEVICE_ID="$(xcrun simctl list -j devices available | python3 -c '
import json,sys
raw=json.load(sys.stdin)
xs=[]
for runtime,devices in raw.get("devices",{}).items():
  if "iOS" not in runtime: continue
  for d in devices:
    if d.get("isAvailable",True) and d.get("name","").startswith("iPhone") and d.get("udid"):
      xs.append((0 if d.get("state")=="Booted" else 1,d["udid"]))
if xs: print(sorted(xs)[0][1])
')"
[[ -n "$DEVICE_ID" ]] || fail "No available iPhone Simulator runtime"
echo "Selected available iPhone Simulator (device ID withheld)"
xcrun simctl boot "$DEVICE_ID" >/dev/null 2>&1 || true
xcrun simctl bootstatus "$DEVICE_ID" -b >/dev/null
# OS can show a consent prompt instead; UI test handles it.
xcrun simctl privacy "$DEVICE_ID" grant location org.habuai.fieldrecorder >/dev/null 2>&1 || true

# Keep generating a changing fake location, even while xcodebuild is compiling.
# The values below are fixtures only; no original user location enters this job.
(
  while :; do
    xcrun simctl location "$DEVICE_ID" set 35.681236,139.767125 >/dev/null 2>&1 || exit 1
    sleep 6
    xcrun simctl location "$DEVICE_ID" set 35.681750,139.767800 >/dev/null 2>&1 || exit 1
    sleep 6
  done
) &
LOCATION_LOOP_PID=$!
cleanup() {
  kill "$LOCATION_LOOP_PID" >/dev/null 2>&1 || true
  wait "$LOCATION_LOOP_PID" >/dev/null 2>&1 || true
  xcrun simctl location "$DEVICE_ID" clear >/dev/null 2>&1 || true
}
trap cleanup EXIT

# No test report artifact: results exist only in the ephemeral runner.
xcodebuild test \
  -project HabuFieldRecorder.xcodeproj \
  -scheme HabuFieldRecorder \
  -configuration Debug \
  -destination "platform=iOS Simulator,id=$DEVICE_ID" \
  -parallel-testing-enabled NO \
  -maximum-concurrent-test-simulator-destinations 1 \
  -only-testing:HabuFieldRecorderTests \
  -only-testing:HabuFieldRecorderUITests \
  CODE_SIGNING_ALLOWED=NO \
  -quiet

APP_DATA="$(xcrun simctl get_app_container "$DEVICE_ID" org.habuai.fieldrecorder data)" ||
  fail "Cannot read isolated Simulator app container"

python3 - "$APP_DATA" <<'PY'
import json,sys
from pathlib import Path
from xml.etree import ElementTree as ET

base = Path(sys.argv[1])
logs = base / "Library/Application Support/observations"
if not logs.is_dir():
    raise SystemExit("SYNTHETIC_GPS_FAIL: sandbox log directory missing")

verified = False
for source in logs.glob("*.jsonl"):
    try:
        entries = [json.loads(s) for s in source.read_text(encoding="utf-8").splitlines() if s.strip()]
    except (ValueError, OSError):
        continue
    kinds = [e.get("kind") for e in entries]
    fixes = [e for e in entries if e.get("kind") == "fix"]
    events = [e for e in entries if e.get("kind") == "event"]
    if not (fixes and events and kinds[0] == "start" and kinds[-1] == "stop"):
        continue
    gpx_path = base / "tmp" / ("habu-" + source.stem + ".gpx")
    if not gpx_path.exists():
        raise SystemExit("SYNTHETIC_GPS_FAIL: GPX export missing")
    root = ET.parse(gpx_path).getroot()
    points = root.findall(".//{http://www.topografix.com/GPX/1/1}trkpt")
    if len(points) != len(fixes):
        raise SystemExit("SYNTHETIC_GPS_FAIL: exported track count mismatch")
    if not all(isinstance(x.get("accuracy"), (int,float)) for x in fixes):
        raise SystemExit("SYNTHETIC_GPS_FAIL: fix accuracy missing")
    print("SYNTHETIC_GPS_PASS: saved fixes=%s, observations=%s, GPX points=%s; no location data published" %
          (len(fixes), len(events), len(points)))
    verified = True
    break
if not verified:
    raise SystemExit("SYNTHETIC_GPS_FAIL: no completed session with fixes and observation")
PY
