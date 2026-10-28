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
