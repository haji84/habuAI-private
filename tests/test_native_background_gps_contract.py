"""Static safety gates. Real screen-off tests require user devices and signing.

These checks do not imply OS permission, signed app, or GPS capture is proven.
"""
import re
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
ANDROID=ROOT/"mobile/android"
IOS=ROOT/"mobile/ios/HabuFieldRecorder"

class NativeGPSContractTests(unittest.TestCase):
    def test_android_location_service_opt_in_and_no_internet(self):
        manifest=(ANDROID/"app/src/main/AndroidManifest.xml").read_text(encoding="utf-8")
        service=(ANDROID/"app/src/main/java/org/habuai/field/LocationTrackingService.kt").read_text(encoding="utf-8")
        activity=(ANDROID/"app/src/main/java/org/habuai/field/MainActivity.kt").read_text(encoding="utf-8")
        self.assertIn('android:foregroundServiceType="location"',manifest)
        self.assertIn("android.permission.FOREGROUND_SERVICE_LOCATION",manifest)
        self.assertIn("android.permission.ACCESS_FINE_LOCATION",manifest)
        self.assertNotIn("android.permission.INTERNET",manifest)
        self.assertIn('android:stopWithTask="false"', manifest)
        self.assertIn("startForeground",service)
        self.assertIn("requestLocationUpdates",service)
        self.assertIn("START_STICKY",service)
        self.assertIn("stopForeground",service)
        self.assertIn("stopTracking()",activity)
        self.assertIn("startForegroundService",activity)

    def test_apple_background_mode_and_user_visible_start(self):
        plist=(IOS/"Info.plist").read_text(encoding="utf-8")
        src=(IOS/"BackgroundTrackRecorder.swift").read_text(encoding="utf-8")
        app=(IOS/"ContentView.swift").read_text(encoding="utf-8")
        self.assertRegex(plist,r"<key>UIBackgroundModes</key>\s*<array><string>location</string></array>")
        self.assertIn("NSLocationWhenInUseUsageDescription",plist)
        self.assertIn("allowsBackgroundLocationUpdates = true",src)
        self.assertIn("startUpdatingLocation()",src)
        self.assertIn("stopUpdatingLocation()",src)
        self.assertIn("requestWhenInUseAuthorization()",src)
        self.assertIn("requestStart()",app)
        self.assertIn("finish()",app)
        self.assertNotIn("URLSession",src)

    def test_both_teams_generate_gpx_from_real_fixes(self):
        kotlin=(ANDROID/"app/src/main/java/org/habuai/field/TrackExport.kt").read_text(encoding="utf-8")
        swift=(IOS/"TrackStore.swift").read_text(encoding="utf-8")
        store=(ANDROID/"app/src/main/java/org/habuai/field/TrackingStore.kt").read_text(encoding="utf-8")
        self.assertIn('item.optString("kind")',kotlin)
        self.assertIn('"fix"',kotlin)
        self.assertIn('"gap"',kotlin)
        self.assertIn("300_000",kotlin)
        self.assertIn('item.kind == "fix"', swift)
        self.assertIn('item.kind == "gap"', swift)
        self.assertIn("item.time - p >= 300",swift)
        self.assertIn("FileProtectionType.completeUntilFirstUserAuthentication",swift)
        self.assertIn("stream.fd.sync()",store)
        self.assertIn('"event"',store)

    def test_android_start_is_durable_before_active_marker(self):
        store=(ANDROID/"app/src/main/java/org/habuai/field/TrackingStore.kt").read_text(encoding="utf-8")
        start=store.split("fun create(): String {",1)[1].split("fun stop()",1)[0]
        self.assertLess(start.index('append(id, JSONObject().put("kind", "start")'),
                        start.index('putString("active_id", id)'))
        self.assertIn('if (!prefs.edit()', start)
        self.assertIn('.commit())', start)

    def test_failed_active_marker_preserves_start_for_recovery(self):
        store=(ANDROID/"app/src/main/java/org/habuai/field/TrackingStore.kt").read_text(encoding="utf-8")
        start=store.split("fun create(): String {",1)[1].split("fun stop()",1)[0]
        self.assertIn('if (!prefs.edit()',start)
        self.assertIn('error("Could not persist active session")',start)
        self.assertNotIn('.delete()',start)

    def test_android_orphan_inspection_is_explicit(self):
        activity=(ANDROID/"app/src/main/java/org/habuai/field/MainActivity.kt").read_text(encoding="utf-8")
        self.assertIn('button("未終了の保存記録を確認")',activity)
        self.assertIn('store.orphanedStarts()',activity)
        self.assertIn('GPSは自動再開しません',activity)
        self.assertIn('AlertDialog.Builder(this)',activity)

    def test_native_is_not_silently_auto_integrated_into_owner_capture_counts(self):
        src="\\n".join(p.read_text(encoding="utf-8") for p in (ANDROID/"app/src/main/java/org/habuai/field").glob("*.kt"))
        src+="\\n"+"\\n".join(p.read_text(encoding="utf-8") for p in IOS.glob("*.swift"))
        self.assertNotIn("api.github.com",src)
        self.assertNotIn("cloudflare",src.lower())
        self.assertNotIn("habuAI-private",src)
        self.assertNotIn("249",src)
        self.assertNotIn("97晩",src)

if __name__=="__main__":
    unittest.main()
