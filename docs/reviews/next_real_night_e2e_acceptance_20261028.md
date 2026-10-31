# Next real-night P0 to PDCA E2E acceptance (2026-10-28)

**READ_ONLY / ENGINEERING-ONLY / NO PRODUCTION AUTHORITY.**

Usage:

    python scripts/audit_next_real_night_e2e.py --night YYYY-MM-DD --actual-start YYYY-MM-DDTHH:MM:SS+09:00 --phase before
    python scripts/audit_next_real_night_e2e.py --night YYYY-MM-DD --actual-start YYYY-MM-DDTHH:MM:SS+09:00 --phase after

The before phase reuses the existing scripts/check_p0_readiness.py. It remains BLOCKED while the real production issuer and source bundle have not been independently certified.

The after phase checks existing canonical ORIGINAL P0, immutable SHA-256 sidecar via pdca_pipeline.verify_predictions, issue/cutoff/freeze timestamps against an explicitly supplied actual start, the canonical parent nine-stage PDCA result and bound run-manifest pointer. It never issues or changes predictions, ingests data, trains models, runs a second PDCA, or writes files.

Checking file bytes and a user-provided actual start is not trusted source authentication. Even a synthetic report with completed=true, strict_official_score_eligible=true or a locally valid hash cannot prove the real time or issuer authority. This script intentionally always returns BLOCKED / official_e2e_complete=false until an independently reviewed trusted production acceptance authority is implemented.

True E2E remaining evidence:
1. Source-certified eligible training/confirmation and complete owner-outcome ledger with independently qualified active search; GPS passage alone remains UNKNOWN.
2. Ex-ante verified forecast universe, 1km through 100m x 10min model targets, weather/terrain/road and availability timestamps at the prediction cutoff; distinct A/B/C routes.
3. Task8 trusted issuer/Champion activation following exact-head CI, independent review and any required Human Gate.
4. Real next-night P0 published before actual departure with independently witnessed issuance time and SHA, never retroactive.
5. Actual post-return GPX/log exact bytes and source audit, then existing run_pdca parent scoring P0 and P1+ separately.
6. Genuine Stage1 Top10 Recall and formal 100m ±10min only on validated denominators; immutable ORIGINAL hash unchanged before/after.

This is a bounded acceptance-observer slice, NOT a completed Model/Science/Production E2E. It does not alter PR146/147 intake or merged PR149 parent code. Master Goal haji84/AI-#1642, owner issue haji84/habuAI-private#64, coordinator #86.

## Two-P2 repair from fixed 694714f (2026-10-28)

The observer now owns bounded captures instead of calling the uncapped ORIGINAL disk loader/verifier facade. The unchanged pure prediction contract/hash verifier and canonical serializer are reused. The local disk checks retain the existing exact sidecar and canonical-record bytes, status/reason precedence, ORIGINAL/night/version/path checks and verification reopen. Report/immutable-manifest equality uses actual bounded bytes and a bounded pointer recheck. No core verifier, common schema or prediction bytes changed.

Fixed limits: 16 MiB per JSON, 64 MiB actual cumulative reads (including every chunk and overflow byte), 128 artifact capture/reopen operations, 130-byte sidecar, 256 directory entries including unrelated entries, 64 P-prefix directories, JSON depth32 / 200,000 nodes per artifact / 500,000 cumulative nodes, and one cooperative30s deadline. String/escape-aware lexical depth/token checks run before JSON decoding; iterative node checks and deadline checks surround decoding and pure hashing. Overflow is a structured blocker, never truncated success. These are cooperative guards, not atomic hostile-filesystem confinement or hard OS preemption.

Every stage member is checked as a dict before `.get`; nine valid dicts plus `None` now returns `PDCA_REPORT_INVALID`. Existing missing/duplicate/nonPASS-stage diagnostics remain. Known missing `fcntl` is handled only by `ModuleNotFoundError.name == 'fcntl'`, returning `P0_PREFLIGHT_RUNTIME_BLOCKED` without fabricating an existing-preflight/production-authority result. Unrelated import errors are not converted to success. This small platform repair was separately authorized after observing the original error; it is not a core/Champion portability change.

Actual TDD and Windows results (Python `-B -X utf8 -m unittest`):

- Initial mixed-stage / physical16MiB-overflow / physical65MiB-cumulative tests: **3 FAIL / 0.415s**, then **3 PASS / 5.627s**. Native pre-edit pins and complete failing logs are retained privately.
- First full observer attempt: **31 = 29 PASS + 1 symlink skip + 1 missing-fcntl ERROR / 9.243s**; retained as history, not overwritten.
- New actual Windows missing-capability test: **1 FAIL / 0.009s** before that small repair. Final observer: **32 = 30 PASS + 2 skip / 9.487s**, no errors/failures. The two skips are genuine canonical POSIX preflight (paired with the actual Windows-capability test) and WinError1314 symlink creation; POSIX CI must execute the former preflight and symlink checks.
- The final observer includes12 complete native-verifier parity subcases, exact byte/depth/entry/P-directory boundaries, lexical duplicate-key/node accounting, shared node/read/deadline budgets, bounded record reopen, immutable manifest comparison, spoofed path and no-write checks. These12 parity subcases are not12 extra unittest methods.
- Unchanged `PredictionSidecarPathTests`: **13 = 11 PASS + 2 WinError1314 ERROR / 4.433s**, including actual Windows junction controls. Unchanged `test_p0_readiness` could not import due to missing `fcntl` (**1 loader ERROR**, not five executed tests). Unchanged recovered-scope contract: **1 PASS / 0.110s**. Neither old error is hidden or repaired outside the allowed paths.

Full suite, Ubuntu/POSIX execution, new source closure/CI, source qualification and PR integration are not claimed here. The author records and raw logs live under private `.worktrees/pr150-observer-repair-author-20261028/`. Only the observer/test/this review are changed. All tests use synthetic TemporaryDirectory fixtures; real-source ingestion, source/GPX audit, network/provider acquisition, fit, issuance, PR/STATE/cycle/workflow/dependency changes are outside this repair. Before/after remain read-only, always `BLOCKED` / `official_e2e_complete=false`; caller clocks/flags/hashes create no authority.
