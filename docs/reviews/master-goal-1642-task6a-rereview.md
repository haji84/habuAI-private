# Task6a scoped re-review — 9e5f3b7

Reviewed frozen commit `9e5f3b7d6b6b55b2ede5f489d6a5dfad209e025e`, supplied `3dcc2f8..9e5f3b7` diff, AGENTS.md, bounded Task6a plan, original seven-finding review and repair handoff. No repository edits, subagents or full-suite rerun. Parent owns the full-suite verification.

**Spec compliance: changes required. Code quality: changes required.** Six findings addressed; Important 1 retains a reproduced scope gap. No additional independent Critical/Important regression found in the bounded diff.

| Original finding | Verdict | Review evidence |
|---|---|---|
| 1. Unresolved capture becomes negative | **NOT_ADDRESSED** | Original unqualified CSV case is repaired: matching units are masked, rejected/conflicting CSV or individual evidence masks conservatively, and qualified positives are retained. Raw JSON failures still disappear from the masking/completeness inputs; detailed probe below. |
| 2. Malformed empty log accepted | **ADDRESSED** | Required event/time/location/count header groups and duplicate-header checks run before row iteration. Parsed-source membership is required by both sessions and full-domain coverage. Header-only valid schema remains admissible; no-ID rows remain diagnostic rather than canonical. |
| 3. Recognized noncapture poisons completeness | **ADDRESSED** | Recognized sighting/roadkill/reaction rows are retained separately with source hash and original record. Other/blank kinds remain rejected. These noncapture rows neither become captures nor enter the unresolved-capture guard. |
| 4. GPX/link failures not propagated | **ADDRESSED** | Strict point parsing errors emit aggregate `gpx_schema` FAIL checks; affected segments remain ineligible. Individual errors emit `individual_links` FAIL checks, block negatives and coverage, while independent event diagnostics remain available. Ordinary gap/ordering QC retains its separate conservative treatment. |
| 5. Existing learning bypasses failed audit | **ADDRESSED** | Builder checks upstream FAIL before existing-input return. Master checks actual current audit FAIL before operational/model execution and emits failed child stages without invoking evaluation. |
| 6. Builder outside shared budget | **ADDRESSED** | Parent supplies `remaining`; builder checks it around source reads/hashes, feature/row work, validation and publication. `_validate` receives the live check. Read/count/row limits were added. Runtime failure produces typed RUNTIME_BLOCKED; staged publication is removed if the shared deadline expires immediately after rename. No fresh independent budget supersedes the parent's callback. |
| 7. Derived ledger retains stale digest | **ADDRESSED** | Parent digest is verified, copied into `parent_ledger_sha256`, and the extended ledger receives a new content digest including the outside-universe projection. Original audit ledger remains unmodified. |

## Remaining Important 1 — Failed raw capture evidence still permits an explicit zero and complete denominator

Relevant code: `src/evidence_audit.py:228–248`, new masking at `349–367`, coverage checks at `422–429`.

`_raw_logs` extends `raw_log_candidates` only after every event and summary passes. A capture with unknown quantity, or a valid capture followed by a contradictory summary, raises first. The exception emits a failed check but records no unresolved candidate or source for `_units` and `_outcome_coverage`. Their new masks inspect CSV rejections/conflicts/link errors and successfully emitted raw candidates, so this failed raw evidence remains invisible to eligibility.

Two direct temporary-fixture probes against the frozen commit:

1. Start with `fixture(root, True, empty=True)` and `complete_coverage(root, cap)`.
2. Write `data/raw/habu_logs/known.json` and a valid matching receipt via fixture helpers. Operational date is `2026-09-28`; event is type `capture` at `2026-09-28T21:00:00+09:00`.
3. Variant A sets `individual_count` to null. Variant B sets count to 1 but summary to `{individuals: 2, capture_events: 1}`.
4. Run `audit_evidence(root, NIGHT, verified_at=VERIFIED)`.

Both produce **status FAIL, observation labels `[0]`, empty raw candidates, and `ESTABLISHED_FOR_DECLARED_DOMAIN`**. Variant A reports `RAW_LOG_EXACT_COUNT_REQUIRED`; variant B reports `RAW_LOG_SUMMARY_CONFLICT`. Receipt hashes/sizes are valid. These are known unresolved capture records in the declared operational night; their absence from the candidate list cannot establish noncapture or domain completeness.

The new upstream FAIL guard correctly stops the builder/master from consuming this result, reducing impact. It does not fix the audit's published eligibility/denominator contract. This is the unresolved-quantity/conflict scope of original finding 1, not a demand for later scientific features.

Required repair: preserve raw-log failure evidence and its safely known scope even when count/summary reconciliation fails. Feed it to both negative-unit masking and full-domain coverage. Conservatively block the affected night or broader scope when localization is unavailable; retain independently qualified positive diagnostics. Regression assertions should require UNKNOWN and NOT_ESTABLISHED in both variants, plus the existing aggregate FAIL and builder refusal.

## Limits

The rest of the verdicts derive from direct implementation and test-diff inspection; only the two residual probes were executed here to avoid repeating the parent's frozen-commit suite. No raw/ORIGINAL files were altered. The changes retain the 07:00 Asia/Tokyo boundary, source hashes, UNKNOWN semantics and shared cooperative runtime policy. Historical source completeness, ex-ante availability and authenticated scientific authority remain legitimately NOT_VALIDATED; no Task6b/8 implementation or production approval is implied.
