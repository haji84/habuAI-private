# Task 1 scoped re-review — fix round 1

Scope: `317c8341c508503a866c803c65b2a0344dcfeb81`, reviewed using `task-1-fix1-review.diff` against docs-only parent `81fad6a`, and the updated implementation report. This re-review covers the prior two Important findings and new breakage introduced by this fix only.

## Spec compliance verdict: approved for this scoped fix

**Prior finding 1 — ADDRESSED.** `scripts/freeze_prediction.py` now preserves a supplied information cutoff at or before actual issuance and rejects a future cutoff. The actual issuer clock continues to establish freeze time; prospective targets must still occur strictly after actual issuance and belong to the issued operational night. A previous-day cutoff does not authorize completed-night issuance or retroactive targets. The existing explicit provenance limitations remain intact. This resolves the normative distinction between information cutoff and issuance without introducing a permissive issuance-backdating window.

The test removing the one-second-earlier-cutoff rejection is a correction to an invalid expectation, not a weakened governance constraint. Its replacement positively checks cutoff preservation, actual issuance metadata, correct hash, and continuing official ineligibility, while a separate regression rejects elapsed targets with an earlier cutoff.

No new Critical or Important spec-compliance findings identified in the fix.

## Code quality verdict: approved for this scoped fix

**Prior finding 2 — ADDRESSED.** `src/pdca_pipeline.py` uses loader-owned `_directory_version` for the load-stage label. Unvalidated payload version fields no longer reach the string join. The contract validator explicitly rejects missing, non-string, and noncanonical versions before evidence/scoring; failure is returned and persisted through the established integrity path. The added regression checks missing, integer, list, and `P00` cases, including a valid hash and unchanged prediction bytes.

The implementation is small, directly resolves the reported failure path, and preserves the loader's refusal to synthesize hashed payload content. No new Critical or Important robustness findings identified in the fix.

## Verification and limits

Independently ran only these three targeted regressions, all passing:

- `test_missing_or_nonstring_version_returns_structured_integrity_failure`
- `test_freeze_preserves_earlier_information_cutoff_without_lag_window`
- `test_earlier_cutoff_cannot_make_already_elapsed_target_prospective`

Command: `PYTHONPATH=tests python -m unittest test_master_scoring.ScoringIntegrityTests.test_missing_or_nonstring_version_returns_structured_integrity_failure test_master_scoring.FreezeIntegrityTests.test_freeze_preserves_earlier_information_cutoff_without_lag_window test_master_scoring.FreezeIntegrityTests.test_earlier_cutoff_cannot_make_already_elapsed_target_prospective`.

The report states all 77 tests pass; the full suite was not repeated here. No source/data edits were made. Unchanged dependencies, the complete canonical remote tree, remote Actions, and live bridge behavior remain **not independently verified by this re-review**. The updated report explicitly supersedes its original exact-cutoff-equality limitation. The original review's later-slice/provenance limitations remain, and this scoped approval is not full Master Goal acceptance or a claim of production/scientific eligibility.
