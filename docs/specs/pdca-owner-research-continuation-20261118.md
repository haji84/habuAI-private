# PDCA research continuation and owner-source intake v1
Date: 2026-11-18 JST. Parent goal: haji84/AI-#1642.

## Owner-approved order
1. Finish every independent descriptive/research stage even when ORIGINAL P0 and qualified Negative are missing.
2. From valid research outcomes, generate bounded candidates, compare old vs new using the same time-split/outcome universe, and save baselines, deltas, uncertainty and failure reasons. No improvement may be invented if the candidates do not run.
3. Require untouched future-night validation and all formal stage gates before Champion promotion; preserve rollback and immutable ORIGINAL.

## Acceptance of owner-supplied observations
- Owner-submitted capture logs, times, places, GPX and field conditions are **primary observation submissions**; do not require a third-party witness for each item just to carry out descriptive analysis or research fitting.
- Intake stores the original source bytes unchanged (in a nonpublic authorized source), receipt time, SHA-256, source type, duplicate link and transformation lineage. Owner-provided means an assertion of provenance, **not** that a hash independently proves historical accuracy.
- Promote the **valid fields** of each observation: capture totals can contribute to descriptive counts even if GPS is absent; time-only records can contribute to temporal diagnostics; spatial-only records cannot provide precise temporal labels.
- The absence of a record is not proof of noncapture, and GPX passage alone does not create a Negative. For a supervised 100m x 10min Negative, require a source-bound active-search interval and a separate source-bound statement/record that all owner capture outcomes for the same interval were recorded. One scoped owner confirmation of a complete session can cover many derived units if verified and indexed correctly; do not solicit repetitive approvals for each 100m cell.
- Duplicate events, contradictory counts, implausible positions, broken source bytes or future-data leakage are flagged automatically. Unknown remains Unknown, not zero. Never fabricate P0 from hindsight.
- No secret, exact owner capture/GPX coordinates, or private observation files may be committed to this public repository. Save public-safe aggregate research summaries only. Existing production security/approval gates remain.

## Implemented in this slice
- `run_pipeline` no longer returns immediately solely because P0 is missing. When the audited inputs contain captures and/or GPX exposure, it continues to independent descriptive analysis.
- Capture-only nights no longer require GPS points to report recorded capture counts/hours.
- Reports distinguish recording counts, distinct events, sampled units, qualified observed units and Unknown units. Precise positions/timestamps are excluded from the new research aggregate.
- No P0 score, no spatial-temporal ablation and no official model comparison is fabricated when predictions are unavailable.
- The master run manifest now publishes an aggregate summary of the **existing** matched Brier baseline-vs-candidate diagnostic (when actually computed), including mean, paired night count, difference and uncertainty interval. It never marks a research comparison as future-night validated or production-eligible.
- Concrete next data/issuance steps are produced by detected gaps; they are *research prompts*, not automatically trained models.
- All existing gate criteria and production Champion restrictions remain unchanged.

## Remaining mandatory work
- Wire a privacy-preserving **owner-source intake registry** for new records and explicit bounded search-session completeness, without weakening `AGENTS.md` Negative rules.
- Build owner-supported research feature joins and truly trained candidate models using eligible data, with time-blocked cross-validation and an identical baseline/holdout.
- Persist model comparison evidence and risk/uncertainty; the current `model_comparison.status=NOT_EVALUATED` is an honest placeholder until actual matched runs exist.
- Validate a fresh future night with frozen ORIGINAL P0/P1; demonstrate at least Stage1 1km Top10 Recall >=90%, then downstream 100m +/-10min gates. Implement trusted production activation only with verified evidence, rollback, and required approval.
- Regression tests must show research continuation in the absence of P0, no fabricated Negative, unchanged P0 score guards and valid master manifests.

## Acceptance example
For an audited night with two owner-recorded captures (one encounter) and one UNKNOWN GPS observation unit but no P0, output must show:
- `load_frozen_predictions=BLOCKED` while `research_capture_summary=PASS`;
- recorded individuals 2; distinct encounter 1; Unknown units 1; qualified observed units 0;
- `p0_score=null`, `model_comparison.status=NOT_EVALUATED`, and no automated production model change.

This slice does **not** satisfy the complete master goal; a Draft PR is appropriate pending CI and future-night acceptance.
