# HABU FIELD native locked-screen GPS candidate

Status: Draft prototype, not an installed or verified production app. Built separately from dashboard PR #136 to avoid changing frozen historical evidence and unrelated model code. Do not merge or distribute without CI, independent review and owner approval.

## Why native mobile apps
An iPhone/Android browser PWA cannot guarantee GPS and local writes after screen lock, tab suspension or backgrounding. The native prototypes use Core Location for iOS and a visible location foreground service for Android.

Official platform docs:
https://developer.apple.com/documentation/corelocation/cllocationmanager/allowsbackgroundlocationupdates
https://developer.apple.com/documentation/corelocation/handling-location-updates-in-the-background
https://developer.android.com/develop/sensors-and-location/location/permissions
https://developer.android.com/develop/background-work/services/fgs/restrictions-bg-start

## iOS
- Mac and Xcode required. From mobile/ios run: xcodegen generate --spec project.yml
- Open generated project, set own bundle ID, Apple signing team and Background Modes / Location capability.
- Install to an owned iPhone. Grant requested location while in use, explicitly press Start while foregrounded; lock screen and test recording; stop from the app.
- Background updates may continue while running and locked. User force-quit, device shutdown, revoked permission, iOS termination and missing GNSS can still interrupt. No guarantee after force quit.
- Raw point files use file protection compatible with writing when screen locked and are exported as actual GPX and JSONL. A backup is necessary because device storage is not an archival guarantee.

## Android
- Open mobile/android with Android Studio, JDK 17 and SDK 35, or run gradle :app:assembleDebug with Gradle 8.9.
- Install to an owned Android device. Press Start while visible, grant coarse/fine location and verify notification, lock screen, then inspect actual GPS/GPX timestamps. Notification Stop or activity Stop ends recording.
- Uses Android location foreground service; no INTERNET permission; no ACCESS_BACKGROUND_LOCATION because foreground location service starts in visible Activity. It does not silently start tracking.
- Force stop, OS termination, disabled location, restricted battery mode or permission removal can interrupt recording. START_STICKY is not a guarantee.

## Records and privacy
- A UUID identifies each user-started session. Append-only JSON Lines records start, real GPS fixes, gaps, user-observed capture/sighting/roadkill and stop.
- GPX is derived ONLY from real fixes. Split tracks at explicit gaps and intervals of 300 seconds or longer. Never reconstruct lines across missing measurements.
- Local GPX/JSONL files contain private locations. DO NOT upload to public GitHub, Issues, CI artifacts, logs or PR comments.
- Owner-confirmed dashboard total remains 249 captures / 97 nights. Native events do not add to that count. Full synchronization needs owner authentication, dedup by session/event UUID and operational night (07:00 JST), offline queue with server replay and separate privacy-preserving aggregate exports.
- No Cloudflare paid product, bucket or database was activated by this PR.

## 2026-11-01 Android/iPhone reliability improvements

- Android 13+ now asks for notification permission **when the owner presses Start**. If denied, it does not start a location foreground service whose ongoing notification might be hidden. Older Android versions are unchanged.
- Android raw export is valid newline-delimited JSON (NDJSON), not a text report with a header/footer. GPX still contains only recorded fixes; both exports remain local and use a user-selected file location.
- iPhone indicates that the first *real* location fix is pending, displays the most recent stored fix time in the current app process, and warns when the OS grants approximate rather than precise location.
- The iPhone's Stop button can close an unfinished session found after relaunch, without silently turning GPS back on. Cached pre-start locations are excluded from the newly started measurement interval.
- Automated static contracts guard the above behavior. Simulator builds and Android emulator synthetic location tests are **not real-device proof**. Real owned-phone tests, independent review, owner approval and release remain pending.

## 2026-11-01 retained-record export and crash recovery hardening

- Both apps can enumerate **older completed sessions**, not only the most recent one, and let the owner choose which GPX/JSONL to export without a network request.
- Android offers exact original NDJSON export for a selected historical or orphaned file, including files whose final line is malformed; parsed GPX/NDJSON conversion may fail on damaged lines, but the original bytes are preserved.
- iPhone lists retained sessions for export and offers byte-exact owner-triggered backup of orphaned sources. Closing a session interrupted during persistence must not attach a new search to a previously closed recording.
- Android JVM crash-recovery regression tests run before every debug APK build. Static contract tests check the corresponding iOS and Android source paths.
- Only authorized, locally installed builds are eligible for real-device tests. Never upload historical GPS, original NDJSON, or export archives to Public GitHub or an untrusted share destination.
- This does not certify the system's end-to-end backup, automatic sync, independent code review, device tracking performance, or readiness for production.

## Acceptance gates
1. Exact-head Android CI build and iOS compile using Xcode, plus independent review.
2. Real iPhone and Android screen-lock test for 30 minutes, with airplane mode then normal network, GPS accuracy and gap checks.
3. Background switch, lock, force-stop, permission revoke, GPS disabled, restart and battery-mode tests with honest missing coverage.
4. On-device export restore and duplicate-import tests, PR #136/#92 reconciliation, protected sync, then main release only after explicit human approval.

Existing dashboard PR #136 still has frozen-cycle HASH_MISMATCH in overall CI. This independent native PR does not override or claim to fix the freeze. 
