# Standalone HB-A2 bounded nonlinear candidate

Design blob `e0c37718d775a10824aa3afd8533a8300d451d40` independently passed
review and the coordinator authorized TDD. Initial base
`a1d2a99de1ec7b0324e822c85c4e14a7e77c80eb` normally fast-forwarded to verified
main/origin/main `5d4b84fcc0d9b54683f80b4fcace0818d7fb94bd` before source edits; branch
`codex/hba2-candidate-20261025`. This slice owns only a new model module,
test module, this spec and a new review. Existing A1/core/selection, registries,
parent dispatch, requirements, policies, Raw/ORIGINAL and STATE remain unchanged.

## Choice and claim

The feasibility-only alternative can validate qualified inputs and return honest
NEED_MORE_DATA, but leaves nonlinear fit/export mechanics unimplemented. The
selected alternative adds controlled synthetic fit/export/predict using the
already pinned library, without a new optimizer. The coordinator approved this
direction and the exact fields/runtime/export boundaries below. Pure guards and
JSON inference are implemented and tested locally. Genuine pinned numeric fit
acceptance remains mandatory in existing Ubuntu CI; it has not run on this native
runtime. A source/CI PASS is not scientific validation.

HB-A2 is a standalone DEVELOPMENT_ONLY binary owner-capture candidate conditional
on a qualified observed 100m x 10min unit. It uses A1's exact seven raw features
and physical limits, without imputation, scaling, feature search or new labels.
It does not estimate animal abundance, calibrated island-wide risk, count or
effort. Existing three-slot registries do not admit HB-A2 and are not modified.
Registration, trusted campaign accounting, pre-reveal freeze and parent integration
are separate tasks. Scientific training-ready real rows remain zero; stored
source-qualified captures do not by themselves provide a complete training set.
Only synthetic fit mechanics are executed in this slice.

## Proposed public API

```python
assess_hba2(training_selection, *, recipe, expected_recipe_sha256,
            budget_seconds=30, check=None)
fit_hba2(training_selection, *, recipe, expected_recipe_sha256,
         budget_seconds=30, check=None)
predict_hba2(model, forecast_rows, *, cutoff_time, joined_universe_sha256,
             budget_seconds=30, check=None)
```

Reuse `models.research_selection.validate_selection` and `validate_future_rows`;
reuse A1's bounded JSON/budget/hash utilities and seven-feature physical checks.
No source readers, filesystem discovery or sealed/outcome reader exists here.
The source-bound G0 TRAIN selector and strict forecast loader remain upstream
requirements. These pure APIs cannot reauthenticate their discarded receipts.

Validate all supplied rows, exact feature order/count, binary types, counts,
unique units/events, source identity, held-out night and chronology before
returning NEED_MORE_DATA. UNKNOWN/bool labels, stale/rehashed count claims,
physical violations and leaked/future fields are errors even when another input
is insufficient. All seven feature names are required. A valid zero-row or
single-class selection remains NEED_MORE_DATA. Require at least 20 accepted rows,
five prior nights and the existing minimum two positives/two negatives for the
controlled fit. This is an engineering floor, not scientific sample adequacy.

Every supplied accepted TRAIN row is checked in full before the sample/night
floor, NEED_MORE_DATA or backend/capability classification. Validate all seven
known raw values and physical limits, convert each value to IEEE binary32 using
standard-library `struct.pack`/`unpack`, then check finiteness AFTER conversion.
Packing overflow, cast-to-infinity and any nonfinite input are ValueError, even
for a validly declared insufficient/single-class TRAIN selection and even when
the backend is absent. No NumPy import is needed for this preflight. Rejected-row
summaries contain no predictors and must retain the existing exact summary schema.
Future rows receive the same preflight. Do not silently retain float64, clip or
impute a value that cannot be represented as a finite float32 input.

## Exact recipe proposal

Eight fields, no arbitrary estimator or callable:

| Field | Required content |
| --- | --- |
| schema_version | habu-hba2-gbc-recipe-v1 |
| target | OWNER_CAPTURE_BINARY_GIVEN_QUALIFIED_OBSERVED_100M_10MIN_UNIT |
| algorithm | SKLEARN_GBC_BINARY_LOG_LOSS_ZERO_INIT_V1 |
| feature_names | Exact original seven `prospective_candidate_model.FEATURES`, in order |
| params | Exact fixed public parameters below, with exact scalar types |
| runtime_versions | Exact scikit-learn 1.5.2, NumPy 2.2.6, SciPy 1.15.3 |
| requirements_sha256 | Exact keys requirements-analysis.txt and requirements-osm.txt; declared native-byte SHA-256 each |
| implementation_sha256 | Exact new module, reused A1 helper, legacy feature/core, research_selection and gpx_audit source paths; declared SHA-256 each |

The current recursive requirement files already pin the three numerical packages
and pandas/pyarrow/Pillow. Neither file changes. Recipe content hashes bind their
declared native-byte identities, not package/file authenticity. Fit stamps actual
numerical package/Python/platform versions and installed joblib/threadpoolctl
versions in its receipt. The latter transitive versions are recorded rather than
falsely described as newly pinned. No pickle/joblib load or persistence is used.

Fixed parameters: loss=log_loss; learning_rate=0.1; n_estimators=32;
subsample=1.0; criterion=friedman_mse; min_samples_split=10;
min_samples_leaf=5; min_weight_fraction_leaf=0.0; max_depth=2;
min_impurity_decrease=0.0; init=zero; random_state=0; max_features=null;
verbose=0; max_leaf_nodes=null; warm_start=false; validation_fraction=0.1;
n_iter_no_change=null; tol=0.0001; ccp_alpha=0.0. No sample weights, validation
subset, early stopping, search or alternate fit is permitted. Fixed randomness
does not imply cross-platform bitwise reproducibility.

The official [1.5.2 GradientBoostingClassifier API](https://scikit-learn.org/1.5/modules/generated/sklearn.ensemble.GradientBoostingClassifier.html)
documents zero initialization, binary sub-estimators, fixed seed, float32 inputs
and iteration monitoring. These support this proposal without a private optimizer.

## Canonical JSON model and inference closure

Proposed exact model fields: schema_version, status, candidate_id,
target_semantics, recipe, recipe_sha256, feature_names, input_dtype,
initial_raw_score, learning_rate, classes, trees, runtime,
training_selection_sha256, corpus_sha256, source_sha256, source_received_at,
fit_cutoff, heldout_night, training_nights, training_window_start_max, counts,
training_rows_sha256, training_row_ids_sha256, raw_feature_rows_sha256,
the existing nine A1 authority/authentication fields, and model_sha256.
Version is habu-hba2-research-model-v1, status DEVELOPMENT_RESEARCH_FIT_ONLY,
candidate HB-A2, input_dtype IEEE754_BINARY32, initial_raw_score=0.0,
learning_rate=0.1, classes=[0,1]. Authority/authentication flags retain A1's exact
false/NOT_VALIDATED/NOT_ATTESTED/caller-dependency values.

Export the documented `estimators_` regression trees through their documented
`tree_` structure attributes, never an opaque Python object. Exactly 32 trees,
each an exact {nodes} object with 1..7 nodes and depth <=2; 224 nodes total.
Each node has left, right, feature, threshold and value. A leaf has left=right=-1,
feature=threshold=null and a finite nonboolean value. A split has distinct valid
integer children, a feature index 0..6, finite threshold and value=null. Root is
index zero; no cycles, shared children, unreachable or out-of-range nodes are
accepted. All arrays/scalars are converted to ordinary JSON types. See the
official [tree structure example](https://scikit-learn.org/1.5/auto_examples/tree/plot_unveil_tree_structure.html).

Prediction imports no numerical library: round each validated raw feature to
IEEE float32 using standard-library pack/unpack, then require finiteness AFTER
that conversion. Preserve exported thresholds and finalized, unscaled post-fit
`tree_.value` leaf updates as binary64 JSON floats. Start `raw = 0.0`. In the
original 32-stage order, traverse using `X_float32 <= threshold`, then perform
exactly `raw += 0.1 * leaf_value` once per tree. Check both each product and each
partial sum for finiteness. No extra learning-rate factor, `fsum`, reordered
reduction, extra intercept, sigmoid clipping or alternative score is permitted.
Apply a stable binary logistic function after the last tree; check its result
before output rounding. Export admission compares unrounded raw decisions and
unrounded probabilities with public `decision_function`/`predict_proba` on every
supplied TRAIN row at absolute tolerance 1e-12. Mandatory controlled tests compare
those same two unrounded quantities on all TRAIN and complete future fixture rows
against the genuine pinned estimator, then check eight-decimal public output.
Threshold tests use actual adjacent binary32 feature inputs on opposite sides of
each selected split threshold; binary64 neighbors that collapse to one float32
are insufficient. Public unit probabilities/spatial scores use eight-decimal
rounding as A1.
No tree fitting or split selection is reimplemented by this interpreter.

Prediction receipt uses habu-hba2-unit-prediction-v1, candidate/model/recipe/TRAIN/
joined-universe hashes, cutoff/night/target, every exact future unit and the same
authority flags. Rows carry their original ID/night/window/cell/area and diagnostic
probability/spatial score. All native counts, actual tree structure, common
chronology, exact recipe and content hashes are admitted again before scoring;
rehashing invalid structure or privileged claims cannot grant validity.

## Exact receipts and runtime fieldsets

All objects are canonical JSON only, with no additional fields. Hashes are
lowercase 64-hex strings. Times are bounded timezone-aware ISO strings; nights
are canonical YYYY-MM-DD strings with the existing 07:00 boundary. Counts and
indices are exact nonboolean integers; numeric scores/errors are finite
nonboolean JSON floats. Blockers/issues are sorted unique lists of bounded
strings. No result can carry a privileged flag through rehashing.

The nine common flags are exactly source_authentication=
CALLER_DEPENDENCY_REQUIRED, source_authenticity=NOT_ATTESTED,
scientific_status=NOT_VALIDATED, and fit_authorized, selection_authorized,
promotion_authorized, scientific_execution_authorized,
official_issuance_authorized, production_activation_authorized all false.
Every public receipt additionally has purpose=DEVELOPMENT_ONLY and
registration_status=STANDALONE_NOT_REGISTERED.

`assess_hba2` has exact fields schema_version, status, purpose,
registration_status, candidate_id, target_semantics, recipe_sha256,
training_selection_sha256, corpus_sha256, source_sha256, source_received_at,
fit_cutoff, heldout_night, training_nights, training_window_start_max, counts,
training_rows_sha256, training_row_ids_sha256, raw_feature_rows_sha256,
backend_status, runtime, blockers, the nine flags, receipt_sha256.
Version is habu-hba2-feasibility-v1; candidate and target are fixed as above.
Status is NEED_MORE_DATA or SOFTWARE_INPUTS_READY, never a scientific readiness
claim. backend_status is exactly NOT_PROBED and runtime is null: assessment does
not import/probe numerical libraries. Blockers are nonempty only for NEED.
training_window_start_max is null only for zero accepted rows; otherwise it is
the exact latest accepted window. training_nights is the sorted unique actual
night list. counts has exactly accepted_rows, rejected_rows, nights, positives,
negatives, recomputed from actual rows. source_sha256 is a bounded path-to-hash
map and source_received_at has the same keys with declared aware times, subject
to the unchanged shared selector contract. The three TRAIN content hashes cover
the complete accepted row list, ordered row-ID list and ordered row_id/features
list respectively, including valid empty lists. receipt_sha256 seals all other
assessment fields.

`fit_hba2` has exact fields schema_version, status, purpose,
registration_status, candidate_id, target_semantics, recipe_sha256, assessment,
model, runtime, export_consistency, blockers, the nine flags, receipt_sha256.
Version is habu-hba2-standalone-fit-v1; assessment is the complete sealed object
above, never an unverified summary. The only combinations are:

- NEED_MORE_DATA: assessment NEED; model/runtime/export_consistency null;
  blockers equal assessment blockers; no backend import.
- CAPABILITY_BLOCKED: assessment SOFTWARE_INPUTS_READY; model and
  export_consistency null; runtime CAPABILITY_BLOCKED; blockers equal its issues.
- DEVELOPMENT_FIT_ONLY: assessment SOFTWARE_INPUTS_READY; exact validated model
  present; runtime PINNED_BACKEND_READY; export_consistency present; blockers empty.

`runtime` when present has exactly schema_version, status, expected_versions,
observed_versions, auxiliary_versions, python_version, python_implementation,
platform, input_dtype, requirements_sha256, issues. Version is
habu-hba2-runtime-v1. expected_versions and observed_versions have exactly the
distribution-name keys scikit-learn, numpy, scipy. Expected values are the recipe's
three fixed version strings; observed values are bounded actual version strings
or null when not installed. Successful admission requires imported versions and
distribution metadata to agree with those pins. auxiliary_versions has exactly
joblib and threadpoolctl, each a bounded installed-version string or null; these
are actual recorded transitive identities, not newly pinned versions. The three
Python/platform fields are nonempty bounded strings; input_dtype is exactly
IEEE754_BINARY32; requirements_sha256 equals the recipe's exact two-key map.
PINNED_BACKEND_READY has issues=[] and all three exact numerical pins. Missing,
mismatched or nonimportable numerical runtime is CAPABILITY_BLOCKED with explicit
issues; import failures are not mislabeled as missing scientific data. No package
or requirement-file authenticity is inferred from metadata/declarations.

`export_consistency` has exactly status, method, rows_checked, tolerance,
max_abs_raw_error, max_abs_probability_error. Status is NATIVE_JSON_AGREEMENT;
method is PUBLIC_DECISION_FUNCTION_AND_PREDICT_PROBA; rows_checked equals the
actual complete accepted TRAIN count; tolerance is the float 1e-12. Both maximum
errors are finite nonnegative floats <= tolerance. This checks serialization
mechanics, not prediction accuracy. Independent future parity belongs to the
controlled numeric tests; fitting does not consume held-out outcomes or invent
forecast rows for this receipt. The model's runtime equals the fit runtime.

`predict_hba2` has exactly schema_version, purpose, registration_status,
candidate_id, model_sha256, recipe_sha256, training_selection_sha256,
universe_sha256, cutoff_time, operational_night, target_semantics,
unit_predictions, the nine flags, prediction_sha256. Version is
habu-hba2-unit-prediction-v1; universe_sha256 equals the caller's explicit joined
universe digest. Every unit has exactly row_id, operational_night,
window_start_jst, cell_x, cell_y, area_id_1km, probability, spatial_score,
probability_status. Original strict identities are retained, cell indices are
exact ints, probability_status is NOT_VALIDATED, and probability/spatial_score
are equal eight-decimal finite floats in [0,1]. The complete future set is
validated before any scoring; no output rows are omitted or substituted.
prediction_sha256 seals every other field. No status/capability success claim
is inserted into a partial prediction: invalid/deadline/capacity input raises.

## Resource, missing-backend and publication boundaries

Combined recipe/selection, or model/complete future input, is owned before work
under existing 16 MiB/2,000,000-node/depth-12 bounds; row limits remain 20,000 TRAIN
and 120,000 future. Limit actual canonical encoded bytes before deepcopy/parsing;
declared size/count metadata does not replace actual counts. No cap increase,
sampling, partial universe, fallback or new process/global runtime installation.
One optional caller check plus one tightened local <=300s deadline spans validation,
hashes, import, array conversion, fit, export, consistency probes and final sealing.

Only enough valid TRAIN data reaches lazy backend admission. All three numerical
versions must match the existing pins. Missing or mismatched backend returns an
explicit CAPABILITY_BLOCKED fit receipt with model=null; insufficient valid data
returns NEED_MORE_DATA with model=null without importing a numerical backend.
`assess_hba2` reports input feasibility, not installed capability or fit success.
Malformed supplied data is never hidden by either missing-data/backend status.
Deadline/capacity errors release no partial model/prediction/metrics.

The public fit monitor checks the same absolute deadline after every stage and
never returns early-stop success. Import/array allocation and each native tree
stage are nonpreemptible; this cooperative API does not promise hard wall-clock
termination inside C code. Check immediately before/after those calls and before/
after the final result hash. Any late expiry discards all local fit state. Exactly
32 finished trees are required; no partial estimator is serialized. No artifact
writer or REPLAY publication exists in this standalone module.

## TDD and acceptance proposal

- Before code: freeze existing A1 28-test baseline and current registry identities.
- Valid zero/insufficient/single-class TRAIN: NEED_MORE_DATA and no backend import;
  malformed counts/types/duplicate IDs/UNKNOWN/bool/physical bounds still fail.
- Real pinned backend synthetic repeated 5-night/20+row fits; deterministic same
  environment; nonlinear interaction fixture; classifier-vs-JSON decisions and
  probabilities for all TRAIN/future rows and float32 threshold neighbors.
- Wrong versions/import absence -> explicit capability block. Numeric tests skip
  only explicitly unavailable pinned backend locally; installed contradiction is
  tested as a block. On GITHUB_ACTIONS=true no numeric test may skip because of a
  missing/wrong backend. An always-collected mandatory numeric gate must assert
  the three exact package versions and execute a genuine fit/export plus TRAIN
  and future unrounded raw/probability parity. It cannot use the local skip
  decorator or convert an import/version failure to skip. Thus missing/wrong
  fixed runtime or an otherwise all-skipped numeric group fails existing CI.
  The Ubuntu workflow already installs requirements-analysis; no workflow change.
- Stale/rehashed model/recipe hashes, altered counts/night/cutoff/authority,
  missing/reordered features, NaN/inf/bool, float32 overflow, cycles/shared children,
  wrong tree count/depth/indices/leaf sentinels and nonfinite raw sums are rejected.
- Combined actual JSON/row caps and shared expiry during import/native monitor/
  export/inference/final seal; no successful partial model/prediction.
- No real-source training run, registry/parent changes, sealed reads, numerical
  performance certification or model selection. Related A1/selection/candidate/
  source-parent regressions remain unchanged; native missing backend is recorded
  honestly and exact Ubuntu numeric CI is required before integration.

Preparation evidence: a1d2 main/origin/main matched and the initial tree was clean;
A1 28 tests PASS (1.614s). The source was implemented only after independent design
PASS and root authorization. Current bundled runtime has NumPy 2.3.5 and no
SciPy/scikit-learn. No library installation, real-source fit or local numerical
spike has been performed. The explicit local numeric skip is not a fit PASS;
the review records native receipts and the pending mandatory Ubuntu numeric gate.
