# Task 1 independent review

Reviewed local Task 1 diff `c875a7c..4c36075`, the task brief/report, current affected source/tests, repository rules, and normative master specification. Recommendation: **changes requested** for the two Important findings below. No Critical findings identified.

## Spec compliance

### Important — information cutoff is incorrectly forced to equal issuance

File: `scripts/freeze_prediction.py`, lines 52–56 (also timestamp preservation at lines 69–72).

The loop treats `cutoff_time` and `created_at` as issuance-clock fields and rejects any supplied value that differs from the current clock, even by one microsecond. The normative specification explicitly separates the forecast information cutoff from trusted `issued_at`/`frozen_at`, and the existing freeze-versioning specification calls cutoff the hard information boundary. A legitimate predictor may stop consuming inputs at 20:00, compute, and freeze at 20:00:01. This implementation rejects that record. With the real CLI's internally sampled clock, practically every pre-populated cutoff is rejected. Omitting cutoff to make issuance work instead changes the recorded information boundary to completion time.

Targeted reproduction: cutoff `2026-09-30T20:00:00+09:00`, actual injected issuance `2026-09-30T20:00:01+09:00`, and a valid target at 21:00 on that night produces `ValueError: cutoff_time must equal actual issuance time`.

Action: preserve cutoff as a separately validated information boundary while sourcing issuance/freeze time from the issuer clock. Reject future cutoffs, completed-night issuance, retroactive targets, and class relabeling; do not use an earlier caller cutoff to establish historical issuance or Champion selection. Continue marking external generic records as provenance-unvalidated. Add a regression accepting a legitimately earlier cutoff with future targets and retaining the actual freeze timestamp, alongside the existing rejection cases. Align the test at `tests/test_master_scoring.py` lines 194–208, which currently requires even a one-second-earlier cutoff to fail, with the normative distinction.

Other reviewed Task 1 compliance is substantially improved: FAIL cannot be downgraded by missing hashes; missing hashes cannot become official; class/night/path comparison is present; fixed spatial/time thresholds replace payload overrides; targets at or before cutoff are excluded; maximum-cardinality matching is implemented; unmatched uncovered targets remain UNKNOWN; cell positivity uses common floor-grid/time units; capture filtering rejects the tested bad types/counts/coordinates/nights; historical scores remain validated-hash diagnostics; candidate/model validation no longer reports PASS. Official eligibility is consistently false pending independent provenance. The existing E2E assertion changes add truthful status assertions rather than weakening scientific gates.

## Code quality and robustness

### Important — missing prediction version crashes before contract validation

Files: `src/pdca_pipeline.py`, lines 53–55 and 467, with the intended validator at lines 59–71 / 469–475.

Removing the loader's synthesized `prediction_version` is correct for hash integrity, but the success-stage message still indexes `p["prediction_version"]` before validation runs. An ORIGINAL payload missing this field now raises `KeyError` instead of returning the structured integrity FAIL that the new path/version contract is designed to provide. This is an introduced interaction, not the separately disclosed pre-existing malformed-JSON limitation. A wrong-type version can similarly fail the string join before it is classified.

Targeted reproduction: write a well-formed JSON payload with valid `prediction_class`, `operational_night`, `cutoff_time`, and a correct canonical hash under `predictions/original/2026-09-30/P0/prediction.json`, omitting only `prediction_version`; `run_pipeline(root, "2026-09-30")` raises `KeyError: 'prediction_version'` before loading evidence or emitting its integrity result.

Action: avoid dereferencing unvalidated payload metadata when building the load-stage message; validate first or use the storage directory as the diagnostic label. Explicitly validate version presence/type/canonical format and return FAIL through the established integrity-result path. Add missing-version and wrong-type-version pipeline regressions proving there is no uncaught exception and no scoring occurs.

The matching implementation is understandable and its augmenting paths provide the requested cardinality behavior for current bounded inputs. Shared unit-key construction avoids the old sample-order label dependence. The private `_targets` import introduces modest coupling but is not a blocker for this bounded slice. Recursive matching depth, full schema hardening, stale output/concurrency, observation-quality audit, and Champion provenance remain acknowledged later work; this review does not demand those future modules as Task 1 fixes.

## Verification and limits

- Parent independently reported all 74 tests passing; I did not repeat that suite.
- Independently executed only the two concrete probes above in disposable temporary directories; both findings reproduced.
- Inspected the relevant test changes and normative contracts. No source or historical data was changed during review.
- Did not independently reproduce the report's 45-file historical byte-equality audit or verify the complete canonical remote tree, runtime dependencies, remote Actions, or live bridge behavior. Unchanged dependencies and remote evidence are therefore **not independently verified by this review**.
- No approval of future scientific validity, production eligibility, or full Master Goal completion is implied.
