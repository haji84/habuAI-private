# Full-ledger Stage1 diagnostic evaluator

Approved bounded V slice, based on main `4a3605249dae6f22954aa3051541642ae47e3a53`.
Owned files are this specification, `src/evaluation/full_ledger_stage1.py` and
`tests/test_full_ledger_stage1.py`. Existing restricted-universe metrics, model
fits, labels, policy, state, Raw and ORIGINAL are unchanged.

## Purpose and authority

`evaluate_full_ledger_stage1(forecast_universe, candidate_scores, ledger,
budget_seconds=30)` is a pure independent diagnostic calculation. It accepts
already supplied JSON values; it does not open files, read sealed outcomes,
authenticate declarations, fit models, choose a winner or publish REPLAY.

The chosen approach is a small explicit area-score/individual-ledger projection.
Replacing the historical evaluator would change reviewed v1 behavior; directly
accepting arbitrary model artifacts would couple independent metrics to three
different model formats. The parent is responsible for constructing this
projection from the same complete, source-validated prepared forecast set.

Even a declared-complete ledger and recall >=0.90 never grant official status.
Every return keeps scientific_status=NOT_VALIDATED, source_authenticated=false,
confirmation_source_authenticated=false, official_stage1_recall_computed=false,
official_threshold_pass=false, fit_authorized=false, production_authorized=false.
The shared G0 policy digest, Top10 and five-night process floor are retained.
Five nights do not prove adequacy, independence or trustworthy confirmation.

## Exact input projections

All dictionaries have exactly the documented fields. SHA-256 fields are lower
case 64-hex strings. Input digests use canonical JSON, not source-file bytes.

Forecast universe (`habu-stage1-universe-v1`):

- `schema_version`, `nights`.
- Each night: `operational_night`, `scope`, `scope_sha256`, `cutoff_time`,
  `horizon_start`, `horizon_end`, `area_ids`.
- Scope: `crs="EPSG:32652"`, `bbox_utm=[xmin,ymin,xmax,ymax]` in meters.
  Scope digest binds that exact declared projection. It does not prove the
  actual scope's independent geographic completeness or authentic source.
- Canonical areas are `utm52n_1km_<floor(x/1000)>_<floor(y/1000)>`.
  Areas are unique, sorted and intersect the declared half-open bounding box.
  This binds every supplied candidate area, never only observed/captured areas.
- `cutoff_time < horizon_start < horizon_end`; the whole half-open horizon
  lies in the operational night [07:00 JST,next 07:00 JST). End may equal 07:00.

Scores (`habu-stage1-scores-v1`):

- `schema_version`, `universe_sha256`, `candidates`.
- Each candidate: `candidate_id`, `score_semantics`, `model_sha256`,
  `prediction_sha256`, `scores` (night -> every area -> finite nonboolean number).
- Uniform is first and mandatory; at most HB-A0 and HB-B1 may follow, without
  duplicates. Candidate hashes/semantics are declared lineage, not authenticated
  model receipts. Native hierarchy rank scores are never turned into probabilities.
- Uniform scores must be spatially constant within each night. Their common
  level may differ between nights; the evaluator does not estimate it.
- Every candidate uses exactly the same nights and complete area universe.
  Rank by descending score, then canonical area ID lexical order. Select at most
  ten unique areas. No score, cell or outcome-driven universe filtering occurs.

Ledger (`habu-stage1-ledger-v1`):

- `schema_version`, `source_refs`, `complete_scopes`, `events`, `ledger_sha256`.
  Ledger digest excludes only `ledger_sha256`.
- Source refs: `{path,sha256,bytes}`; bounded canonical relative POSIX paths.
  Paths remain references: no path is opened or hashed by this evaluator.
- Each scope: `operational_night`, `scope_sha256`, `horizon_start`, `horizon_end`,
  `declaration` (DECLARED_COMPLETE, INCOMPLETE or UNKNOWN), `coverage_ref`,
  `source_paths`. Complete scopes require a registered matching coverage ref and
  nonempty registered capture-source paths. Scope/horizon must match the universe.
- Each event: `event_id`, `operational_night`, `datetime`, `utm_x_m`, `utm_y_m`,
  `individual_ids`, `source_paths`. Event and individual IDs are explicit, unique
  across the entire supplied cohort and source-bound. Missing/duplicate IDs,
  invented implicit count=1, boolean/nonfinite coordinates, wrong-night times,
  points outside scope and events outside the fixed horizon are rejected.
- One event with two individual IDs contributes two to the denominator. An
  individual outside forecast candidate areas remains in the denominator and
  is a miss. No observed-only shrinking or random cell split is performed.
- Missing inputs or missing/noncomplete scope coverage return NEED_MORE_DATA
  without partial metric results. When all inputs are present, malformed
  contracts raise ValueError. If any projection is None, remaining projections
  receive JSON resource checks only; no projection validation, acceptance or
  input-digest receipt is claimed for that incomplete call.
  A complete declared empty ledger yields diagnostic zero counts and null recall.

## Results and uncertainty

Per night report unique forecast/actual area counts, source-bound event/individual
identity digests, outside-universe misses, and each candidate's Top10, numerator,
denominator and recall (null when denominator=0). Pooled recall is sum(numerator)
divided by sum(denominator), not a mean of nightly recalls.
The result also preserves each candidate's native score semantics and declared
model/prediction digests, plus unique forecast/actual area counts over all nights.

Uncertainty is paired NIGHT-block bootstrap: fixed local seed 0, 2,000 replicates,
the same resampled nights for all candidates. Recompute pooled recall differences
against uniform in each replicate, report nominal 2.5/97.5 percentiles, effective
replicates and zero-denominator draws. No individual/cell resampling is used.
Intervals are withheld with fewer than two informative nights. Small night counts,
unverified independence and the five-night floor are explicitly reported; these
are descriptive intervals and never a confirmation or accuracy certificate.
Quantiles use linear interpolation at `(replicate_count-1)*quantile`. Zero-denominator
draws are counted and omitted from interval calculation, never converted to zero
recall. Their count plus valid replicates always equals 2,000. Below two informative
nights, every interval is null even if some draws have nonzero denominators.

## Bounds and failure semantics

128 nights, 120,000 area-night entries, three candidates, 20,000 events,
100,000 individual IDs, 16 MiB combined JSON, bounded depth/nodes/strings.
JSON depth is at most 12, nodes 2,000,000, key length 512 and string length 4,096;
source refs at most 20,000 and source bindings at most 32 per event/scope. Reference
paths are canonical relative POSIX strings in data/evidence/features/policies/reports,
without traversal, drive/absolute paths or ASCII control characters. Declared
source size is an integer between zero and 2 GiB, never an authenticated byte count.
Capacity overrun raises Stage1CapacityBlocked(ValueError); deadline exhaustion
raises Stage1BudgetBlocked(ValueError). Default elapsed budget is 30 seconds,
finite positive and at most 300; parent passes its remaining allowance. A shared
monotonic deadline is checked during JSON encoding, validation, metrics,
bootstrap and after final receipt sealing. No partial results escape a failure.
Checks are cooperative and do not OS-preempt a single Python operation.

## Implementation plan and execution ledger

Use writing-plans, executing-plans, TDD and verification-before-completion in this
isolated worktree. Parent approved native execution and final independent review.
No additional plan artifact is created outside the three owned paths.

- [x] Tests first: outside-universe denominator, two individuals/event, pooled
  ratio, deterministic ties, exact source/hash/scope/ID rejection and no authority.
- [x] Observe RED, implement the smallest pure contract/count evaluator, verify GREEN.
- [x] Tests first: paired bootstrap, no-data/no-partial-result and deadline/capacity
  controls; observe RED before completing each corresponding behavior.
- [x] Run target and relevant existing protocol/model metadata regressions.
  Parent explicitly directed this worker to omit another known-failing native
  Windows full-suite run and use its exact-head Ubuntu integration CI instead.
  This is not a local full-suite PASS; existing Windows environment failures
  remain in coordinator state and previous worker reports.
- [x] Self-review, protected-path diff, source hashes, commit only owned files;
  return exact commit for parent independent review/CI/new source freeze.

Baseline: existing locked-protocol + G0 contract tests: 51 PASS (0.238 seconds).
Ruling: scope uses a bounded explicit UTM bounding-box projection so actual-point
scope contradictions can be checked; matching declared scope hashes remain
consistency evidence and never independent geographic authentication.

Verification on 2026-10-25 using the bundled native Python, `-B -X utf8`:

- First 14 controls: 14 expected assertion failures for the missing module,
  then 14 PASS after the contract/count implementation.
- Bootstrap/lineage controls: four expected missing-result-field errors,
  then 23 PASS including existing budget/stream-cap controls.
- Hostile self-probes: nonconstant uniform and three control-character paths
  produced four expected assertion failures; extreme night, event and integer
  budget produced three expected OverflowErrors. After bounded ValueError
  repairs, all 28 owned tests PASS (0.245 seconds).
- Final combined target: 144 PASS (7.779 seconds), no skips/errors/failures:
  `test_full_ledger_stage1.py`, `test_locked_protocol_manifest.py`,
  `test_codex_cycle_contract.py`, `test_codex_cycle_cursor.py`,
  `test_research_selection.py`, `test_occupancy_shrinkage.py`,
  `test_hierarchy_shrinkage.py`.
- Both owned Python files compiled in memory successfully. No Python bytecode,
  actual model fit, real capture ledger, sealed read, model winner or official
  prediction was produced. All fixture counts and coordinates are synthetic.

The parent must independently audit this exact source, refresh the conservative
code-closure manifest, and obtain exact-head CI before integration. This slice
does not wire parent PDCA, allocate future folds, prove source completeness,
validate pre-reveal freezes or finish real scientific confirmation.

Final source SHA-256 (Git index bytes equal working bytes):

- `src/evaluation/full_ledger_stage1.py`:
  `99fbc1ea210b22c35f52c2e31cf6d2d9e32e736833393ad8b8cccece9e2cd6d6`
- `tests/test_full_ledger_stage1.py`:
  `148d1545a12e848f1462887e695f9172decb45c0fec04be8512fcf84a173845e`

Self-review confirmed source/candidate identity checks, denominator inclusion,
same-night bootstrap pairing, bounded encoding, all-result deadline checks and
constant false authority. Only the three owned new files differ from the base;
protected data, existing policy/cycles, shared state and all fit code are unchanged.

## Integration branch preparation

The reviewed source `c0fcddfd4e87d21e49f93e7b0154d5fa35ea2a7e` was merged
non-destructively with main `fb06f7679efa74f6ca017bb04eee242b7900f63a`, which
contains exact PR32 head `9cf729a`. No source conflict or evaluator code change
was needed. Independent review reran the original 144 tests and a separate
three-night weighted-count/bootstrap oracle successfully. On the updated branch,
the original target group plus cycle prewalk and master inventory controls ran
**171 tests: 167 PASS, four Linux-only skips on native Windows**.

The branch uses dedicated cycle `20261025T1400-full-ledger-stage1`. The existing
coordinator freeze helper reads Git index bytes into a temporary native snapshot;
current-cycle CLI validation and a new immutable source closure are required.
Prior cycles and original sources are preserved. The helper's historical fixed
CI field is replaced in STATE with an actual verified main receipt; exact PR
CI receipts are recorded externally in Issue #86 to avoid recursive changes to
the tested commit. This PR prepares the pure diagnostic API only. Source and
confirmation authentication, official metrics and production remain false;
parent PDCA integration and main merge remain separate coordinator work.
