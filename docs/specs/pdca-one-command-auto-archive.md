# PDCA one-command archive and continuation contract

Status: owner-requested target; implementation gaps are explicit.

## Owner request
When the owner says 「PDCAを回して」 or 「今日のPDCA全部回して」 in the PDCA chat, the workflow should continue through **input preservation -> freeze audit -> PDCA -> reports/evidence -> GitHub PR -> CI -> permitted main integration -> next improvement state**. Do not stop merely because a report file was generated locally.

## Preserve current canonical architecture
- Keep the existing GitHub Issue -> Actions -> `scripts/pdca_bridge.py` -> `scripts/run_pdca.py` and evidence/checkpoint/PR implementation. Avoid replacing it with another PDCA pipeline.
- Apply the 07:00 Asia/Tokyo operational-night boundary. Repeated historical log blocks must not double-count captures.
- All new original attachments first enter `incoming/`; audit SHA-256, byte length, format, timestamps, duplicates, provenance and GPS quality. Promote to `data/raw/` only when byte-exact and permitted. Never rewrite or delete existing Raw.
- Read and validate ORIGINAL P0/P1... immutably (version, cutoff, hash and before/after exposure). A missing official P0 is BLOCKED, not retrospectively fabricated. Keep `predictions/replay/` separate.
- Generate observed 100m × 10-minute exposure with Unknown != Negative, plus research and feature/model evaluation subject to forward-time gates.
- Persist human report, CSV, machine-readable run/evidence manifests, missing stages, model decision and reproducibility hashes. On unavailable data, persist PARTIAL/BLOCKED evidence instead of claiming completion.
- Every successful **write** uses a deterministic/idempotent branch, PR and CI. Main integration is only for a verified eligible scope; requirements, governance, permissions, destructive operations, confidential data risks, paid operations and model promotion require their existing stronger gates.
- A PR is not proof of completion. Independently validate source-versus-committed hashes, CI, security/privacy, report lineage and branch HEAD before any allowed integration. Never merge a failing PR to satisfy an automation metric.
- Champion promotions or rollbacks require separately passed scientific evidence gates; publication of a report alone cannot promote a model.

## Implemented in main at this audit (2026-10-21)
- `.github/workflows/pdca-command.yml` and `pdca-command-poller.yml` accept trusted owner command Issues.
- `src/pdca_bridge.py` persists immutable, bounded checkpoint and result branches, validates recovered receipts, and opens a report PR for a durable computation, including honest BLOCKED scientific results.
- `scripts/ingest_attachment.py` supports byte-preserving local-file intake, but **Chat attachments are not automatically delivered to GitHub Actions**.
- `.github/workflows/data-intake-tests.yml` runs the current unit-test suite for PRs.
- Current implementation does **not** automatically demonstrate that eligible CI-passing PRs reach main without owner clicks. A secure automatic merge path requires its own reviewed, fail-closed implementation and E2E test.

## Pending gaps (not silently completed)
1. End-to-end attachment transport for GPX/log files and local ZIP/CSV reports; a manifest containing hashes does not replace raw payloads.
2. Exact archival of 2026-10-20 GPX and entire generated validation ZIP; 2026-10-06..15 existing intake PR #39 is still open.
3. CI-gated eligible auto-main integration and independent reviewer policy for applicable risks.
4. Stable one-command invocation from PDCA chat across sessions with verified issue/branch receipts.
5. Source-complete weather/tide joins and independent walk-forward, baseline/ablation and Champion promotion evidence.

## Backfill policy
- Retrospective reports belong to `reports/pdca/<night>/retrospective/` and are tagged **PROVISIONAL** when no ORIGINAL Freeze exists.
- Each report and ZIP has a source hash/byte manifest; keep original ZIP locally/within Chat until full source content is safely transportable.
- Files created from indexed spreadsheet text are marked `sheet_view_` and must never be advertised as byte-exact CSV originals.
- Keep 2026-10-16 vs 2026-10-18 environmental comparison separate from the 2026-10-20 operational-night PDCA.
- Do not auto-merge this documentation-and-backfill PR without required CI and review.

## Acceptance tests
- Duplicate command does not create duplicate raw captures or overwrite a report.
- Source GPX/hash and raw log receipts match source bytes.
- Missing P0, incomplete GPX or missing historic weather has an explicit blocked stage.
- Report PR contains no unrelated source or ORIGINAL edits.
- CI and human/safety gates are independently verified before permitted main integration.
- Future prediction only consumes a separately approved Champion; no old ORIGINAL is revised.
