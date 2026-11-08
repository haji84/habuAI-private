# HUB NATURAL cross-platform integration contract

Status: design proposal, not implemented or approved for production.

## Common record envelope
Every local capture or GPS session must have a random `user_id`, `session_id`, `event_id`, schema version, timestamp with timezone, revision, and explicit source type. A capture belongs to one operational night with a 07:00 JST boundary. Record raw measured GPS fixes only; represent interruptions as gaps, never interpolated coordinates. Imported records retain source hashes and duplicate detection. An amendment updates a record revision, never adds the old count again.

## Data separation
Keep GPS fixes, route geometry and original notes in the user's local private store. The statistics layer receives only reviewed owner-capture counts and night status. Do not transfer sensitive GPS into the public GitHub repository, Actions artifacts, build logs or public dashboard payloads. Separate scientific labels from owner-confirmed capture totals.

## Offline and backup
Capture and GPS writes must complete locally before the UI confirms success. Use a crash-safe store and encrypted, authenticated backups with restore verification. Track export is not a substitute for backup. Verify interrupted writes, corrupt backups, revoked permissions, restarts, and offline operation on both iOS and Android.

## Capability enforcement
FREE: capture records, basic statistics, GPS recording and local retention; no route map history or in-app GPX/CSV export. TRACK: route history and export. AI: standard forecasts. PREMIUM: validated higher-tier forecasts and route optimization. Owner-development access is distinct from commercial entitlements. Enforce capability checks at the actual action handler, not only by hiding buttons. No paid plans activated in v1.

## Release gates
Complete the #92/#136 deduplication and #138 native integration in existing PRs. Require exact-head tests, independent review, iPhone/Android real-device locked-screen and airplane-mode trials, restore roundtrips, and explicit approval before main merge or public deployment. Cloudflare is not required for first-stage local operation.
