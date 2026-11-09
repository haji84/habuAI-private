# Private dashboard intake implementation plan

Goal: one shared private intake path for owner Chat attachments and the existing dashboard log/GPX input. User requested implementation on 2026-11-08; do not create a duplicate PR or scheduled task.

Architecture: reuse the current log parser, owner-batch validator and dashboard builder. Add a private durable transactional store and authenticated same-origin WSGI API. Keep all new originals, receipts and aggregate updates outside the public checkout. The existing dashboard is served through the private adapter; its capture_summary route returns the committed private snapshot. Static hosting alone cannot accept private writes.

Approaches: putting raw inputs in public git is rejected. Browser-only IndexedDB is not cross-device synchronization. A private API with persistent storage is the selected implementation approach, consistent with the user's request; deployment identity, private volume and existing protected-host routing remain independently verified deployment requirements, not assumed capabilities.

Constraints: preserve raw bytes and SHA; 07:00 Asia/Tokyo night boundary; owner confirmations do not authorize scientific labels or fitting; no main merge, provider provisioning, paid service, visibility changes or production deployment in this change. Preserve latest main privacy gates rather than restoring old PR92 public-artifact/deployment assumptions. Old PR92 history remains an ancestor.

Tasks:
- [ ] RED: prove shared server intake is missing; capture code-only dependencies for reproducible local tests.
- [ ] Implement private durable intake, SHA deduplication, date/GPX checks, atomic aggregate update and revision conflicts using the existing builder/validator.
- [ ] Add authenticated API and Chat-side CLI transport; no credentials in browser assets, git or URLs.
- [ ] Connect the existing intake page to GPX+log submission, confirmations, status/readback and refreshed summary. Show unavailable connection explicitly.
- [ ] Test duplicate uploads, conflict/partial input, 07:00 rollover, zero capture, invalid GPX, hostile paths, unauthorized requests, storage failures and actual HTTP roundtrip.
- [ ] Verify changed code and CI at exact head. Report implementation and live deployment separately.

Review focus: retries after lost response; stale-tab apply; multi-night mixed logs; partial GPX must not prove full-night coverage; authenticated UI must not cache private API results. All tests use synthetic sources, never owner coordinates or logs.
