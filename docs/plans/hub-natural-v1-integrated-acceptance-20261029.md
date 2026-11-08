# HUB NATURAL v1.0 integrated acceptance and dependency ledger

Updated: 2026-10-29. Planning artifact only; no merge, deployment, or permission change authorized.

## Goal
Finish an owner-only, offline-first iPhone and Android application using existing work in PR #136 (dashboard and intake), PR #138 (native location recorder), and PR #92 (source-gated dashboard refresh). Cloudflare is optional for v1.0, not a launch dependency.

## Verified repository state at ledger creation
- PR #136 compared with main: diverged, 67 commits ahead, 144 behind.
- PR #138 compared with main: diverged, 24 commits ahead, 144 behind.
- Existing code paths include dashboard/field-app.js, dashboard/intake-core.js, scripts/build_capture_dashboard.py, mobile/ios/HabuFieldRecorder, mobile/android, and tests/test_native_background_gps_contract.py.
- These comparisons show file presence, not completed functionality or passing current CI.

## Work packages and dependencies
| ID | Work | Dependencies | Acceptance evidence |
|---|---|---|---|
| A | Pin current HEADs and inventory source/PR overlaps | none | SHA and per-file decision table |
| B | Independent design review for offline storage, native GPS, privacy, plan gates | A | independent review with resolved findings |
| C | Reconcile PR #92 and #136 without duplicate capture count | A,B | owner 249/97/86/11 and correction/replay tests |
| D | Integrate native iOS/Android recorder with local capture data | B,C | build artifacts and no location upload |
| E | Durable encrypted local backup/restore and integrity checking | B,D | roundtrip + corruption + restart tests |
| F | Offline and locked-screen device tests | D,E | iOS and Android 30-minute locked/airplane-mode sessions, permission denial, process stop, reboot |
| G | Full CI and independent code review on exact HEAD | C,D,E | no failures; review findings resolved |
| H | Owner approval for protected main integration | F,G | explicit authorization, exact SHA |
| I | Future subscription readiness only (no billing in v1) | B | capability gates, user/event/revision schema, cross-user isolation design |

## Product capabilities
FREE: capture records, basic statistics, GPS recording and local retention; no in-app route export or past-route map view.
TRACK: past routes and GPX/CSV export.
AI: standard forecast.
PREMIUM: independently validated higher-tier forecast and route optimization.
The owner-development mode is separate from commercial subscription entitlements. No subscription billing is activated in v1.

## Non-negotiable security gates
- The GitHub repository is public. Do not add sensitive GPS, raw tracks, capture points, or credentials to GitHub, Actions artifacts, browser payloads, or logs.
- Audit historical exposure separately. Moving files now does not undo historical public access.
- Do not mutate raw originals, historical scientific freezes, or provenance hashes without separate approval.
- Local capture statistics are not scientific Positive/Negative training labels.
- Cloudflare Access does not protect GitHub history; first-stage offline operation must not require Cloudflare.
- Any paid service, deployment, external exposure, permission change, destructive migration, or main merge requires explicit owner approval.

## Immediate next engineering action
Perform exact-HEAD CI inspection and independent architecture review, then resolve #92/#136 overlap within existing PRs. Do not mark v1.0 complete until real iPhone and Android devices pass the acceptance tests.
