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
        self.assertIn("START_NOT_STICKY", service)
        self.assertNotIn("return START_STICKY", service)
        self.assertIn("if (intent?.action != START)", service)
        self.assertIn('store.gap(it, "service-restart-rejected")', service)
        self.assertIn('store.gap(id!!, "no-location-provider")', service)
        self.assertIn("stopForeground(STOP_FOREGROUND_REMOVE)", service)
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

    def test_android_start_uses_fault_tested_coordinator(self):
        store=(ANDROID/"app/src/main/java/org/habuai/field/TrackingStore.kt").read_text(encoding="utf-8")
        coordinator=(ANDROID/"app/src/main/java/org/habuai/field/SessionStartCoordinator.kt").read_text(encoding="utf-8")
        self.assertIn("SessionStartCoordinator.begin(",store)
        self.assertIn("writeStart =",store)
        self.assertIn("persistActive =",store)
        self.assertLess(coordinator.index("writeStart()"),coordinator.index("persistActive()"))
        self.assertIn('throw IllegalStateException("Could not persist active session")',coordinator)
        self.assertNotIn(".delete()",coordinator)

    def test_android_orphan_inspection_is_explicit(self):
        activity=(ANDROID/"app/src/main/java/org/habuai/field/MainActivity.kt").read_text(encoding="utf-8")
        self.assertIn('button("未終了の保存記録を確認")',activity)
        self.assertIn('store.orphanedStarts()',activity)
        self.assertIn('GPSは自動再開しません',activity)
        self.assertIn('AlertDialog.Builder(this)',activity)
        self.assertIn('catch (_: Exception) { "読取不可・原本保持" }',activity)

    def test_user_initiated_restart_marks_gps_gap_without_invented_fixes(self):
        track = (ANDROID / "app/src/main/java/org/habuai/field/TrackingStore.kt").read_text(encoding="utf-8")
        activity = (ANDROID / "app/src/main/java/org/habuai/field/MainActivity.kt").read_text(encoding="utf-8")
        recorder = (IOS / "BackgroundTrackRecorder.swift").read_text(encoding="utf-8")
        self.assertIn('gap(it, "explicit-user-restart")', track)
        self.assertIn("未終了の探索:", activity)
        self.assertIn("resumingUnfinishedSession", recorder)
        self.assertIn('"explicit-user-restart"', recorder)
        self.assertIn('"location-permission-revoked"', recorder)

    def test_android_export_is_valid_ndjson_and_tracking_notification_is_opt_in(self):
        exporter=(ANDROID/"app/src/main/java/org/habuai/field/TrackExport.kt").read_text(encoding="utf-8")
        activity=(ANDROID/"app/src/main/java/org/habuai/field/MainActivity.kt").read_text(encoding="utf-8")
        self.assertIn('records.joinToString(separator = "\\n", postfix = "\\n") { it.toString() }', exporter)
        self.assertNotIn("HABU FIELD Android observed log", exporter)
        self.assertNotIn("observations, not automatically dashboard-confirmed", exporter)
        self.assertIn("notificationPermissionRequest", activity)
        self.assertIn("Build.VERSION_CODES.TIRAMISU", activity)
        self.assertIn("Manifest.permission.POST_NOTIFICATIONS", activity)
        self.assertIn("requestPermissions(arrayOf(Manifest.permission.POST_NOTIFICATIONS)", activity)
        self.assertIn("if (results.firstOrNull() == PackageManager.PERMISSION_GRANTED) startTracking()", activity)

    def test_android_rejects_cached_pre_start_location(self):
        service=(ANDROID/"app/src/main/java/org/habuai/field/LocationTrackingService.kt").read_text(encoding="utf-8")
        self.assertIn("@Volatile private var startedElapsedNanos: Long = Long.MAX_VALUE", service)
        self.assertNotIn("startFixToleranceNanos", service)
        self.assertIn("startedElapsedNanos = SystemClock.elapsedRealtimeNanos()", service)
        self.assertIn(
            "if (!GpsFixPolicy.isFresh(location.elapsedRealtimeNanos, startedElapsedNanos)) return",
            service
        )
        policy=(ANDROID/"app/src/main/java/org/habuai/field/GpsFixPolicy.kt").read_text(encoding="utf-8")
        self.assertIn("fixElapsedNanos >= startedElapsedNanos", policy)
        self.assertIn("fixElapsedNanos, startedElapsedNanos", service)
        jvm=(ANDROID/"app/src/test/java/org/habuai/field/GpsFixPolicyJvmTest.kt").read_text(encoding="utf-8")
        self.assertIn("startedAt - 3_000_000_000L", jvm)
        self.assertIn("assertFalse(GpsFixPolicy.isFresh(cachedFix, startedAt))", jvm)

    def test_android_recorder_stops_when_local_write_fails(self):
        service=(ANDROID/"app/src/main/java/org/habuai/field/LocationTrackingService.kt").read_text(encoding="utf-8")
        self.assertIn('store.gap(sessionId, "location-write-failed")', service)
        self.assertIn("manager.removeUpdates(this)", service)
        self.assertIn("stopForeground(STOP_FOREGROUND_REMOVE)", service)
        self.assertIn("stopSelf()", service)
        self.assertIn("if (!expectedShutdown && store.activeId() == it)", service)
        self.assertIn('try { store.gap(it, "service-stopped-unexpectedly") }', service)

    def test_android_export_retains_session_and_format_during_file_picker(self):
        activity=(ANDROID/"app/src/main/java/org/habuai/field/MainActivity.kt").read_text(encoding="utf-8")
        self.assertIn("override fun onSaveInstanceState(outState: Bundle)", activity)
        self.assertIn('outState.putString("pending_export_kind", exportKind)', activity)
        self.assertIn('outState.putString("pending_export_id", exportSessionId)', activity)
        self.assertIn('savedInstanceState?.getString("pending_export_kind")', activity)
        self.assertIn('savedInstanceState?.getString("pending_export_id")', activity)
        self.assertIn("exportSessionId = id", activity)
        self.assertIn('val id = exportSessionId ?: error(', activity)
        self.assertIn("finally { exportSessionId = null }", activity)

    def test_ios_recovered_session_can_close_and_cached_fixes_are_not_mislabeled(self):
        recorder=(IOS/"BackgroundTrackRecorder.swift").read_text(encoding="utf-8")
        view=(IOS/"ContentView.swift").read_text(encoding="utf-8")
        self.assertIn("var hasUnfinishedSession: Bool { store.activeId != nil }", recorder)
        self.assertIn("private var measurementStartedAt: Date?", recorder)
        self.assertIn("p.timestamp >= earliest && p.timestamp <= latest", recorder)
        self.assertIn("lastFixAt = p.timestamp", recorder)
        self.assertIn("manager.accuracyAuthorization == .reducedAccuracy", recorder)
        self.assertIn(".disabled(!recorder.hasUnfinishedSession)", view)
        self.assertIn("if let last = recorder.lastFixAt", view)

    def test_crash_recovery_preserves_raw_bytes_and_rejects_completed_reuse(self):
        store=(ANDROID/"app/src/main/java/org/habuai/field/TrackingStore.kt").read_text(encoding="utf-8")
        recovery=(ANDROID/"app/src/main/java/org/habuai/field/SessionRecovery.kt").read_text(encoding="utf-8")
        activity=(ANDROID/"app/src/main/java/org/habuai/field/MainActivity.kt").read_text(encoding="utf-8")
        ios=(IOS/"TrackStore.swift").read_text(encoding="utf-8")
        recorder=(IOS/"BackgroundTrackRecorder.swift").read_text(encoding="utf-8")
        view=(IOS/"ContentView.swift").read_text(encoding="utf-8")
        workflow=(ROOT/".github/workflows/habu-native-gps.yml").read_text(encoding="utf-8")
        self.assertIn("reconcileCompletedActiveSession()", store)
        self.assertIn("SessionRecovery.hasCompleted(", store)
        self.assertIn("SessionRecovery.canResume(", store)
        self.assertIn("fun rawBytes(id: String): ByteArray", store)
        self.assertIn('listOf("start", "unreadable-original")', store)
        self.assertIn('export("raw", ids[index])', activity)
        self.assertIn("store.rawBytes(id)", activity)
        self.assertIn("fun hasCompleted(kinds: List<String>): Boolean", recovery)
        self.assertIn("fun canResume(kinds: List<String>): Boolean", recovery)
        self.assertTrue((ANDROID/"app/src/test/java/org/habuai/field/SessionRecoveryJvmTest.kt").is_file())
        self.assertIn(":app:testDebugUnitTest :app:assembleDebug", workflow)
        self.assertIn('records.contains(where: { $0.kind == "stop" })', ios)
        self.assertIn("func recoveryCandidates() -> [String]", ios)
        self.assertIn("func exportedRecoveryFile(id: String) throws -> URL", ios)
        self.assertIn("Data(contentsOf: source).write(to: target, options: .atomic)", ios)
        self.assertIn("let resumingUnfinishedSession = priorSessionId == id", recorder)
        self.assertIn("exportRecovery(_ id: String)", recorder)
        self.assertIn("recorder.recoveryCandidates", view)

    def test_all_retained_sessions_remain_selectable_offline(self):
        android_store=(ANDROID/"app/src/main/java/org/habuai/field/TrackingStore.kt").read_text(encoding="utf-8")
        android_ui=(ANDROID/"app/src/main/java/org/habuai/field/MainActivity.kt").read_text(encoding="utf-8")
        ios_store=(IOS/"TrackStore.swift").read_text(encoding="utf-8")
        ios_recorder=(IOS/"BackgroundTrackRecorder.swift").read_text(encoding="utf-8")
        ios_ui=(IOS/"ContentView.swift").read_text(encoding="utf-8")
        self.assertIn("fun allSessionIds(): List<String>",android_store)
        self.assertIn("directory.listFiles().orEmpty()",android_store)
        self.assertIn('button("過去の探索記録を選んで書き出す")',android_ui)
        self.assertIn("val ids = store.allSessionIds()",android_ui)
        self.assertIn('export(type, id)',android_ui)
        self.assertIn("func allSessionIds() -> [String]",ios_store)
        self.assertIn("availableSessionIds = store.allSessionIds()",ios_recorder)
        self.assertIn("sessionId: String? = nil",ios_recorder)
        self.assertIn("Picker(\"書き出す探索記録\"",ios_ui)
        self.assertIn('recorder.export("gpx", sessionId: selectedSessionId)',ios_ui)
        self.assertIn('recorder.export("jsonl", sessionId: selectedSessionId)',ios_ui)
        self.assertIn('recorder.export("raw", sessionId: selectedSessionId)',ios_ui)
        self.assertIn('if ext == "raw" {',ios_store)
        self.assertIn("Data(contentsOf: source).write(to: target, options: .atomic)",ios_store)

    def test_android_gps_io_is_off_main_thread_and_session_records_are_serialized(self):
        service=(ANDROID/"app/src/main/java/org/habuai/field/LocationTrackingService.kt").read_text(encoding="utf-8")
        store=(ANDROID/"app/src/main/java/org/habuai/field/TrackingStore.kt").read_text(encoding="utf-8")
        self.assertIn('HandlerThread("habu-gps-log-writer").apply { start() }', service)
        self.assertIn("locationThread.looper", service)
        self.assertNotIn("Looper.getMainLooper()", service)
        self.assertIn("locationThread.quitSafely()", service)
        self.assertIn("@Volatile private var acceptingFixes: Boolean = false", service)
        self.assertIn("if (!acceptingFixes) return", service)
        self.assertIn("acceptingFixes = false", service)
        self.assertIn("private val fileWriteLock = Any()", store)
        self.assertGreaterEqual(store.count("synchronized(fileWriteLock)"), 3)
        self.assertIn("stream.fd.sync()", store)

    def test_android_precise_offline_location_and_resilient_stop(self):
        activity=(ANDROID/"app/src/main/java/org/habuai/field/MainActivity.kt").read_text(encoding="utf-8")
        service=(ANDROID/"app/src/main/java/org/habuai/field/LocationTrackingService.kt").read_text(encoding="utf-8")
        store=(ANDROID/"app/src/main/java/org/habuai/field/TrackingStore.kt").read_text(encoding="utf-8")
        self.assertIn('checkSelfPermission(Manifest.permission.ACCESS_COARSE_LOCATION) == PackageManager.PERMISSION_GRANTED',activity)
        self.assertIn('if (checkSelfPermission(Manifest.permission.ACCESS_FINE_LOCATION) == PackageManager.PERMISSION_GRANTED) startTracking()',activity)
        self.assertNotIn('if (results.any { it == PackageManager.PERMISSION_GRANTED }) startTracking()',activity)
        self.assertIn('val providers = listOf(LocationManager.GPS_PROVIDER)',service)
        self.assertIn('if (location.provider != LocationManager.GPS_PROVIDER) return', service)
        self.assertIn('if (!expectedShutdown && store.activeId() == it)', service)
        self.assertNotIn('else listOf(LocationManager.NETWORK_PROVIDER)',service)
        self.assertIn('if (provider != LocationManager.GPS_PROVIDER &&',service)
        self.assertIn('finally {\n            stopForeground(STOP_FOREGROUND_REMOVE)',service)
        self.assertIn('fun create(): String = synchronized(fileWriteLock)',store)
        self.assertIn('fun stop() {\n        // Atomic against GPS callbacks',store)
        self.assertGreaterEqual(store.count("synchronized(fileWriteLock)"),7)

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
