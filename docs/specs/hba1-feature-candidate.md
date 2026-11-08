# Standalone HB-A1 and retrained development ablation v1

This is a pure software capability on caller-supplied declarations, tested only
with synthetic fixtures. It does not authenticate training evidence, execute
confirmation, register another candidate, choose a winner or activate production.
The existing dispatch remains exactly `uniform`, `HB-A0`, `HB-B1`. Integrating
HB-A1 requires a separately reviewed explicit replacement within the three-slot
protocol; appending a fourth candidate is prohibited.

## Numerical reuse and legacy compatibility

`prospective_candidate_model._fit_numeric(matrix, labels, *, feature_mask=None,
check=None)` is the single optimizer. Input rows always have all seven fixed
features in the original `FEATURES` order. A nonempty seven-boolean mask projects
columns and each call recomputes means/scales and initializes all coefficients
to zero. All-false, wrong-size and nonboolean masks are invalid. It retains
320 epochs, step 0.15, L2 0.04 with unpenalized intercept, scale floor 1e-9,
sigmoid clipping at +/-35, arithmetic and row order. There is no new optimizer.

Legacy `train_candidate` calls that core with all seven features. Its default
v1/v2 serialization, internal development split, dimensions, model hash and
`rank_future` formatting/ranking are unchanged. Its optional `check` callback
creates no fresh clock. The core owns bounded scalar matrix/labels/mask before
its first callback; its short snapshot boundary is not preemptible by callback.
Projection, scaling, epochs, rows, updates and final return check the same callback.
The trainer also checks after model hashing, immediately before return.

The legacy fixture model SHA remains
`f90609a3ad2ca43aaab2db27363d2db810b38c061b17fb3b813f5dc4085212b2`.
All 127 nonempty masks have zero-initialized first epochs on identical input rows.
Parent independently verified 12 synthetic shifted/shuffled variants against
pre-extraction complete model dictionaries, hashes and rank dictionaries.

## Public standalone APIs

```python
fit_hba1(training_selection, *, recipe, expected_recipe_sha256,
         budget_seconds=30, check=None)
predict_hba1(model, forecast_rows, *, cutoff_time, joined_universe_sha256,
             budget_seconds=30, check=None)
describe_retrained_ablations(protocol, folds, *, expected_protocol_sha256,
                            budget_seconds=30, check=None)
```

Recipe fields are exactly:

| Field | Fixed meaning |
| --- | --- |
| `schema_version` | `habu-hba1-fixed-logistic-recipe-v1` |
| `target` | `OWNER_CAPTURE_BINARY_GIVEN_QUALIFIED_OBSERVED_100M_10MIN_UNIT` |
| `numeric_recipe` | `LEGACY_L2_320_LR_0_15_L2_0_04_UNPENALIZED_INTERCEPT` |
| `feature_mask` | Seven booleans, at least one true |
| `implementation_sha256` | Exact keys `src/prospective_candidate_model.py` and `src/models/hba1_feature_candidate.py`, each SHA-256 |

Code hashes and expected recipe/protocol/model hashes bind declared content.
They are **asserted only**: the pure API reads no code/source file and creates no
source authentication or prior-freeze evidence. Parent must verify the actual
implementation/source closure and trustworthy selection before any real use.

Fit owns/checks the existing `validate_selection` envelope, all seven raw feature
values including removed columns, and existing physical range checks. It uses
every accepted TRAIN row in deterministic selector order, with at least five
prior TRAIN nights and 20 rows plus the selector's binary class conditions.
It does not use the legacy trainer's last-two-night internal split: the caller
supplies a separate outer held-out night. Unknown observations cannot fit.
Valid insufficient data return `NEED_MORE_DATA`, `model=None`, concrete blockers;
known conflicts raise `ValueError`, including alongside insufficient data.
These engineering floors do not establish scientific adequacy.

The fit receipt has `schema_version=habu-hba1-standalone-fit-v1`, status,
model/blockers, training selection SHA, counts, recipe SHA,
`registration_status=STANDALONE_NOT_REGISTERED`, authority fields below and
`receipt_sha256`. A successful model has exact fields:

```text
schema_version=habu-hba1-research-model-v1
status=DEVELOPMENT_RESEARCH_FIT_ONLY, candidate_id=HB-A1, target_semantics
recipe, recipe_sha256, feature_names, means, scales, coefficients
training_selection_sha256, corpus_sha256, source_sha256, source_received_at
fit_cutoff, heldout_night, training_nights, training_window_start_max, counts
training_row_ids_sha256, training_rows_sha256, raw_feature_rows_sha256
authority fields, model_sha256
```

`training_rows_sha256` covers full accepted rows including labels, physical
units and canonical event identities; the raw feature digest covers ordered
`{row_id,features}` objects, always all seven features. The actual maximum
training window is computed from accepted timestamps, bound into the model,
and rechecked on reload: aware, aligned to 600 seconds, before fit strictly and
in the final declared 07:00 JST operational night. Counts, source maps, dimensions,
mask/feature order, cutoff/night ordering and all flags are revalidated on reload.

Per-row feature/source readiness, authentic label completeness and partial-night
qualification discarded by the selector cannot be recovered here. In particular,
later historical materialization never proves historical ex-ante availability.
Authentic training and forecast loader gates remain caller dependencies.

Prediction uses existing `validate_future_rows` with all seven features and the
full supplied joined-row digest. Model held-out night must match the forecast
night; fit cutoff must precede forecast cutoff strictly. Every future unit is
retained and scored after mask projection, using the shared legacy score and
eight-decimal probability formatting. Intermediate normalized values, terms and
linear score must be finite **before** sigmoid clipping; overflow/nonfinite fit
state or prediction raises `ValueError`, never a plausible clipped result.

Prediction has `schema_version=habu-hba1-unit-prediction-v1`, candidate/model/recipe/
training SHA, joined `universe_sha256`, cutoff/night/target, authority fields,
`unit_predictions` and `prediction_sha256`. Each unit has row ID, operational
night, window, cell x/y, 1km area ID, probability, identical spatial score and
`probability_status=NOT_VALIDATED`. There is no area ranking or changed aggregation.

## Actual retrained ablation contract

Protocol exact fields are `schema_version=habu-hba1-retrained-ablation-protocol-v1`,
`phase=DEVELOPMENT`, target as above, `base_recipe` with all seven mask entries
true, `groups`, and `folds`. Each group is exactly `{id,drop_features}`: 1–4
preregistered nonempty proper subsets in fixed feature order, unique masks and
case-insensitively unique nonreserved IDs. Full/baseline/HB-A1/uniform/selected/
Champion aliases are reserved. Inference-only zeroing is never used.

Each declared fold has exactly `night`, `training_selection_sha256`,
`joined_forecast_sha256`, `cutoff_time`, and `evaluation_selection_sha256`.
Each input fold has exactly `night`, `training_selection`, `forecast_rows`, and
`evaluation_selection`. There are 1–8 sorted unique outer nights. Every declared
fold must be supplied; no adverse fold or group is dropped for budget or coverage.

All folds preflight before any fit. Evaluation selections retain known labels
even if their selector readiness is `NEED_MORE_DATA`; they are observation
identities, not fit inputs. Each evaluation row must match the future row ID,
night, UTC-normalized window, physical cell **and all seven raw features**.
Evaluation may be a known observed subset of the full forecast universe; unknown
future units still receive predictions and never become negatives. The identical
observed mask (including labels/events) is hashed and used for every recipe.
TRAIN/evaluation row/event/physical-unit overlap is prohibited in each fold;
evaluation event and row reuse across folds is also prohibited. Earlier TRAIN
rows may recur across valid rolling folds. Across all TRAIN and evaluation roles,
each canonical event ID must always name the same night/cell/UTC window. A prior
development observation may train a later rolling fold at that same physical
identity; renaming it to a different observation is rejected. A global physical
unit-to-binary-label map also rejects known 1-to-0 or 0-to-1 contradictions across
roles/folds while allowing the same unit and label to recur in rolling TRAIN.
Feature values across different historical contexts are not globally equated;
each full/ablation comparison still uses its identical frozen fold snapshot.
Empty observations or insufficient
TRAIN support block the whole calculation with `NEED_MORE_DATA` and empty metric
lists; other contradictions are still checked and rejected.

For each fold the full recipe and each dropped-group recipe call the same
numeric core from fresh scaler/zero coefficient state on the exact same matrix
and labels. All recipes predict the entire same future universe before joining
the common observed mask. Each diagnostic evidence item includes used mask/
features, scaler/coefficients, recipe/model/prediction SHA, identical TRAIN row IDs/
row snapshot/raw features/selection SHA, forecast digest, observed-mask digest
and observed-unit Brier. Evidence is not a serialized usable model.

`ablated_minus_full_brier = ablated_brier - full_brier`: positive favors the full
model. Per-group summaries average paired per-night differences equally. A
hand calculation with labels `[1,1,1,0]`, full p=.75, ablated p=.25 verifies
full Brier=.1875, ablated=.4375, delta=+.25. No coefficient-based importance,
causal interpretation, calibration fit, Stage1 recall or full capture denominator
is inferred from these binary observed-mask scores.

The final schema is `habu-hba1-retrained-ablation-diagnostic-v1`, status
`DESCRIPTIVE_RETRAINED_ABLATION_ONLY` or `NEED_MORE_DATA`, with protocol SHA,
blockers, `fold_results`, `paired_summary`, explicit limitations and
`ablation_sha256`. It contains no `model`, `candidates`, selected winner or ranking
artifact. `registration_status=DIAGNOSTIC_NOT_A_CANDIDATE`, statistical adequacy
is `NOT_ASSESSED` and confirmation is `NOT_PERFORMED`.

## Authority, resource limits and failure semantics

Every receipt, model and prediction has `source_authentication=CALLER_DEPENDENCY_REQUIRED`,
`source_authenticity=NOT_ATTESTED`, `scientific_status=NOT_VALIDATED`, and false
`fit_authorized`, `selection_authorized`, `promotion_authorized`,
`scientific_execution_authorized`, `official_issuance_authorized`, and
`production_activation_authorized`. No trusted flag or confirmation mode is
accepted. Content hashes do not prove actual prior source readiness, prediction
generation or pre-reveal freezing; trusted parent controls and permanent
consumption history remain required. Diagnostic labels cannot authorize
reselection, another promotion candidate or production.

Each entry owns its combined inputs only after bounding canonical UTF-8 JSON to
16 MiB, 2,000,000 nodes, depth 12, 4096-character values, 512-character keys and
1024-bit integers. Across all folds: TRAIN<=20,000 rows, forecast<=120,000 rows,
observed<=20,000 rows and event memberships<=100,000; each event insertion checks
the cap and shared guard. The effective capacity is the minimum of every limit;
120,000 rows is a ceiling, not a promise that all such seven-feature payloads fit
16 MiB. There is no full-night/large-domain completion claim or silent sampling.

One monotonic deadline per public entry (default 30 seconds, max 300), plus the
parent's `check`, covers ownership, validation, all fits/scoring and hash/return.
Internal fits/predictions share that same guard without fresh deadlines. Existing
selector/future validators and bounded JSON parse/sort/aggregate operations have
checks before and after; this is cooperative cancellation, not process preemption.
Malformed/conflicting evidence or invalid numerical state raises `ValueError`;
capacity raises `HBA1CapacityBlocked` (`CAPACITY_BLOCKED`), expiry `TimeoutError`
(`RUNTIME_BLOCKED`). No partial fit/forecast/metric escapes. Final seals use
sorted-key compact non-NaN UTF-8 JSON, excluding their own hash field, and a final
guard runs after the digest and immediately before return.

The earlier development calibration v1 component remains unchanged and separate.
Its historical implementation-blocker fields describe its own capabilities; this
standalone companion implements fitting/retraining but does not wire HB-A1 into
parent dispatch or remove independent scientific, calibration, source or policy gates.
