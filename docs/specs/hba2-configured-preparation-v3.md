# Pure fixed HB-A1/HB-A2 candidate preparation v3

DESIGN ONLY. Base: verified main `76b2c109e801dd9da2856532664b96be870fa853`. No implementation, registry admission, source/summary/Stage1/parent dispatch, fitting, scientific selection or authority is authorized by committing this document.

The base still contains A2 module21,362 B / `3a30d1650f90cce8bd7d5258e3deac1b188d4c3a888ec2af75993ff809c47692`. The separate caller-origin repair `1bb46c6e6bf0cf8c0c0072251e38e33689d1e651` has fixed module21,767 B / `43706bf221fcb2e9dfbb16b3dc8db5cb68e31e14e06a4dcd8fe8b4a115d2dd36` and independent scoped code acceptance; its own exact/fresh CI and actual-main integration are still prerequisites to a later implementation dispatch. ROOT must provide the subsequent verified base and explicitly dispatch after independent design review. Pending canonical Aug24 data gates are separate; source registration cannot certify seven features, scientific TRAIN or permission to fit real data.

## Bounded choice and ownership

The next substantive connection is one new pure entry returning exactly `uniform, HB-A1, HB-A2` in that order. Both existing native learners/predictors and the generic complete-row binding are reused. No fourth candidate, permutation, A0/B1 fallback, new learner, scalar extraction, feature search, model choice or old M0–M3 redefinition is included.

Future implementation AllowedPaths are exactly:

- NEW `src/research_candidate_preparation_v3.py`
- NEW `tests/test_research_candidate_preparation_v3.py`
- NEW `docs/reviews/hba2_configured_preparation_v3_20261026.md`
- This spec, only for evidence-driven clarification recorded in that review.

Do not edit existing model/base/selection/kernel, `research_model_adapter.py`, source/config/summary/evaluation/parent modules, requirements, policy, Raw/ORIGINAL, existing tests/goldens, STATE, cycles, workflows or permissions. All existing v1/v2 function bodies, constants, default dispatch, receipts and native modules remain byte-for-byte unchanged. ROOT owns any later source-closure freeze and integration metadata.

## Exact pure API and six-field config

```python
prepare_research_candidates_v3(selection, forecast_rows, *, candidate_config,
    expected_config_sha256, cutoff_time, joined_universe_sha256,
    feature_definition_sha256, budget_seconds=30, check=None)
```

All inputs are explicit JSON-compatible values; no path reader, discovery, backend installer, outcome/confirmation payload, writer or persistent ledger is accepted. Reuse existing `validate_selection`, `validate_future_rows`, native model admission, and the complete candidate binding in `research_model_adapter._candidate`; do not call the whole v1/v2 preparer or change its registry.

Config has exactly these six fields:

| Field | Exact meaning |
| --- | --- |
| `schema_version` | `habu-research-candidate-config-v3` |
| `mode` | `DEVELOPMENT_ONLY` |
| `candidate_ids` | exactly the list `["uniform","HB-A1","HB-A2"]` |
| `hba1_recipe` | nonnull existing five-field A1 recipe, fixed numeric recipe, exact seven `True` booleans; no ablation |
| `hba2_recipe` | nonnull existing eight-field `habu-hba2-gbc-recipe-v1` recipe |
| `feature_definition_sha256` | exact lowerhex SHA equal to the explicit expected definition argument |

Reject extra/missing fields, aliases, duplicates, a fourth ID, reversed order, null recipes and wrong schema/mode even for empty/insufficient data. `expected_config_sha256` is the canonical SHA of the whole copied config. Native recipe digests bind their complete content. A1 retains its fixed L2/320-step recipe and two implementation-map keys; A2 retains its exact32-tree depth2 zero-init log-loss parameters, native feature order, scikit-learn1.5.2/NumPy2.2.6/SciPy1.15.3, five implementation keys and two requirement keys. No parameter, dtype, transform, tree inference or serialization change is allowed.

Those maps are pure caller declarations. Their syntax/digest/content consistency is checked; this entry cannot attest actual files, imported code/packages, historical readiness, issuer or prereveal provenance. A later guarded source adapter must verify physical bytes/readiness separately.

## Complete common inputs and contradiction-first disposition

First validate finite positive nonboolean `budget_seconds <=300`, the optional callable check, scalar hashes and the combined bounded JSON snapshot. All data/schema/recipe checks and known contradictions below finish before any native fitter/backend probe or successful missing-data disposition.

Validate the entire selection under the existing contract, including accepted/rejected counts and summaries, known nonboolean binary labels, row/unit/event uniqueness, night/window/cutoff/source identity and content hash. Rejected summaries do not acquire predictors or labels. Preserve the existing nonempty future-list requirement: an empty list is invalid input. Every supplied future row is validated in full against the same selected feature-name schema, heldout night and cutoff, unique row/physical identity, availability and canonical joined-rows digest. That digest means supplied joined rows, not authentication of a source universe file. No observed-only subset, dropped hard row, window mask or candidate-specific cohort is allowed.

The required raw feature set/order is the unchanged A1/A2 native tuple: temperature_c, humidity_pct, precipitation_mm, slope_deg, tpi_m, road_length_m, wind_cross_road_proxy. Selection names retain their canonical **sorted** projection; both recipes/models retain their exact native order. Do not sort native model columns or infer missing predictors.

A generic-valid **proper subset of those seven names** is a missing-feature condition. Extra/unknown names, missing keys relative to the declared row schema, leaked/future/outcome fields, stale hashes or contradictory counts are invalid input. Before classifying a proper subset or insufficient support, inspect every known supplied raw value in every accepted TRAIN and future row: finite nonboolean number; humidity[0,100], precipitation[0,300], slope[0,90), road_length>0, wind proxy[0,1], temperature/tpi finite. Convert every supplied required raw value with the existing A2 finite binary32 conversion and require finiteness after cast, including temperature/tpi overflow. Missing another feature, empty TRAIN, low support or absent backend cannot hide a last-row contradiction. No clipping/imputation or invented feature value is permitted.

After all known checks, return whole-set `NEED_MORE_DATA`, `candidates=[]`, and nonempty deterministic blockers if selected status is insufficient, fewer than20 accepted rows/five distinct prior nights/two positives/two negatives, or a valid proper feature subset. All valid existing selection blockers remain available. These are engineering feasibility floors, not scientific adequacy. No fit/backend probe occurs on this path.

For ready inputs all three candidates use the identical selected TRAIN snapshot/row IDs/raw-feature digest, source/cohort/count claims, fit cutoff/heldout night and entire future set. Freeze execution as: A2 native fit first (so missing capability does not waste an A1 fit), A1 native fit next, then native prediction/uniform construction and binding; assemble output only in the fixed public candidate order. Pass each nested API the same remaining deadline/check. A2 valid `CAPABILITY_BLOCKED` fit (missing/mismatched/import-broken pinned backend) returns whole-set `CAPABILITY_BLOCKED`, `candidates=[]`, with its intact native blocked fit receipt; never NEED_MORE_DATA, a two-model success or fallback. All supplied input contradictions were already checked.

Validate native fit receipt seals, exact schemas/status/recipe/count/selection identities and models. Successful A1/A2 fits must be `DEVELOPMENT_FIT_ONLY`, with complete admitted models and all expected TRAIN row/raw/ID/source/cutoff/recipe bindings. A blocked A2 receipt must have model=null, exact runtime/assessment/requirements binding and nonempty matching issues; a rehashed contradictory receipt is invalid. Unexpected native insufficiency after this entry's ready preflight is a contradiction, not permission to publish earlier candidates. Validate native predictions/seals/recipe/selection flags and complete one-to-one unit coverage before generic binding. Never mutate/reseal a returned native child to fix a discrepancy.

## Strict result and whole-set status

Result version is `habu-research-candidates-prepared-v3`. Exactly the following top-level fields are returned:

```text
schema_version, purpose, status, candidate_ids, candidate_config_sha256,
feature_definition_sha256, recipe_sha256_by_id, training_selection_sha256,
training_rows_sha256, training_row_ids_sha256, raw_feature_rows_sha256,
heldout_night, fit_cutoff, cutoff_time, joined_universe_sha256, forecast_units,
joined_digest_semantics, candidates, blockers, capability_receipt,
validation_status, replay_status, preregistration, campaign_limits,
implementation_blockers, limitations,
source_authentication, source_authenticity, scientific_status,
fit_authorized, selection_authorized, promotion_authorized,
scientific_execution_authorized, official_issuance_authorized,
production_activation_authorized, receipt_sha256
```

`purpose=DEVELOPMENT_ONLY`; IDs remain the fixed list even when empty candidates are returned. `recipe_sha256_by_id` has exactly uniform:null plus the two canonical recipe hashes. Hashes/counts/cutoffs describe the validated common owned inputs. `joined_digest_semantics=CANONICAL_SUPPLIED_JOINED_ROWS_NOT_SOURCE_UNIVERSE_FILE`, validation/scientific status NOT_VALIDATED, replay PREPARED_NOT_PUBLISHED_OR_TRUSTED_SEALED, preregistration CALLER_DEPENDENCY_REQUIRED. The nine inline flag/authentication fields retain exactly `hba1._flags()` values: caller dependency, NOT_ATTESTED/NOT_VALIDATED and all six authority booleans false.

Statuses are only `NEED_MORE_DATA`, `CAPABILITY_BLOCKED`, `DIAGNOSTIC_CANDIDATES_PREPARED`. The first two have no candidates/nonempty blockers; the first has capability_receipt=null, the second has the intact blocked A2 fit receipt. Complete success has exactly three candidates/empty blockers/capability_receipt=null. Invalid/capacity/deadline/caller failure raises and returns no result.

Each successful candidate has exactly the eight generic `_candidate` fields (candidate_id, model_sha256, prediction_sha256, joined_universe_sha256, forecast_row_ids, forecast_units, model, prediction), plus candidate_config_sha256, feature_definition_sha256, training_selection_sha256, training_rows_sha256, training_row_ids_sha256, raw_feature_rows_sha256, recipe_sha256, fit_receipt. Recipe/fit receipt are null for uniform; A1/A2 retain their complete unmodified native fit receipts. Complete embedded models/predictions and native digests are retained; no selected-field projection masquerades as a native artifact.

`campaign_limits` is exactly `{candidate_configurations:3, improvement_rounds:2, cross_invocation_enforcement:"CALLER_OR_TRUSTED_LEDGER_REQUIRED"}`. This entry enforces its fixed three slots, not a trusted command/campaign counter. Repeated calls/config hashes/output names cannot establish or reset the existing three-configuration/two-round/cumulative allowance. `implementation_blockers` is the fixed ordered list:

```text
A2_SOURCE_CONFIG_ADAPTER_NOT_IMPLEMENTED
A2_FULL_G0_SCORE_SUMMARY_NOT_IMPLEMENTED
A2_STAGE1_SOURCE_ADAPTER_NOT_IMPLEMENTED
A2_PARENT_DISPATCH_NOT_IMPLEMENTED
TRUSTED_CUMULATIVE_CAMPAIGN_LEDGER_NOT_IMPLEMENTED
TRUSTED_PRE_REVEAL_FREEZE_AND_CONSUMPTION_LEDGER_NOT_IMPLEMENTED
MODEL_COMPARISON_AND_WINNER_SELECTION_NOT_IMPLEMENTED
REAL_SOURCE_TRAIN_AND_SCIENTIFIC_ELIGIBILITY_NOT_ESTABLISHED
```

`limitations` is the fixed ordered list `DECLARED_HASHES_NOT_FILE_OR_ISSUER_AUTHENTICATION`, `NO_OUTCOMES_METRICS_WINNER_OR_CONFIRMATION_CONSUMED`, `CROSS_INVOCATION_LIMITS_REQUIRE_TRUSTED_CALLER`, `COOPERATIVE_DEADLINE_NOT_HARD_PREEMPTION`. Missing-data blockers preserve valid selector blockers then append absent-schema/support reasons in that order with stable first-occurrence deduplication; capability blockers exactly copy the validated native A2 blockers. No successful field authorizes selection, fitting real data, confirmation, activation or official P0.

## One deadline, ownership and nested exception origin

Preserve actual combined16MiB encoded input/output,2,000,000 nodes,depth12,20,000 accepted+rejected TRAIN rows and120,000 complete supplied future rows. Apply structural/string/key/number/row bounds before owned copying. Check both the complete prehash body and the complete fully sealed output against all output bounds before final return, including the outer receipt_sha256, every child receipt/hash, every field and JSON encoding overhead within16MiB. Hashing, both bound checks and the final guard remain under the same remaining deadline; never strip fields, truncate or increase a cap to pass the sealed-output check. Nested calls do not receive a new allowance: use the smaller positive remaining time and the same parent guard throughout preflight, backend/import/monitor, fits, predictions, bindings, hashing and final check. Keep the actual source 2GiB/300s and native collector caps outside this pure slice; never increase them to fit an oversized result. Upper row limits do not guarantee that every such result fits16MiB. On cap/expiry no truncation, sampling, partial candidate/model publication or successful partial receipt is permitted. Native imports/tree stages remain cooperative, not hard preemption.

**A2 fix alone is insufficient for origin propagation.** At this base A1 public fit's `_fit` catches OverflowError from `learner._fit_numeric`; a caller OverflowError at the first numeric checkpoint is wrapped in ValueError, before any scaler/coefficient is constructed. Legacy preparev2 also normalizes caller OverflowError/ResearchInputCapacity inside its config guard. A design-only actual control at main76b2 confirmed both; private receipt `.worktrees/hba2-preparation-v3-nested-origin-probe-20261026.json` (1933 B / `fd4367f7e92cb2ca8e58f3879f6881cfb21690deac42238dfcc7fe5325eab2f3`). It completed no fit/model/prediction or source/outcome read. A1 predict has no analogous public outer catch; its existing numeric-row caller checks are outside local arithmetic normalization. This is not an exhaustive same-object acceptance of every old helper.

The new v3 boundary must retain the **first original parent-check exception object** as a sticky abort, bare-raise it at origin, and restore that same object at its own outer boundary even when an unchanged nested helper wraps it. Checking only `exc is recorded_error` is insufficient for the measured A1 case. Check the sticky abort after each nested call, before every status return and before/after final sealing; it may never be suppressed into NEED/CAPABILITY/invalid input or followed by another successful result. Its existence is based on the wrapper's actual caller invocation, not exception text/class or arbitrary `__cause__` heuristics. Internal numerical/import/capacity failures that did not originate in that caller keep their existing classifications. None/noncallable validation order and legitimate caller BaseException objects remain intact.

This obligation is local to the new entry; no A1/legacy repair is authorized here. If implementation cannot restore measured nested caller origin without touching them, stop and request a separately scoped follow-up. Do not silently weaken the v3 guarantee or assume the separate A2 repair solved A1.

## Evidence and decisive acceptance before future release

Before edits on ROOT's then-verified base, seal genuine complete native old programs/dependencies and whole public outputs/order/ticks/hash/read-ledger/physical REPLAY baselines. All pure v1/v2 old/default outputs must remain exact on identical owned inputs and declarations. Preserve historical source-context artifacts unchanged; a newly added runtime module changes real closure membership/code identity. In a new context compare genuinely archived old legacy programs against current defaults under **the same complete code/data declarations**, and separately verify the actual new raw-code map. Do not regenerate expected artifacts from new code, omit hash fields, apply platform allowlists or call changed-context hashes identical.

TDD must cover:

- Fixed six fields/three IDs/order, full A1 mask/native feature order, distinct exact A2 recipe, stale/mismatched content hashes, null/extra/fourth/default/alias configurations; no old function/registry changes.
- Valid zero/positive-only/too few nights/proper feature subset: whole NEED and no backend; empty future rejects under the existing generic contract. Last-row physical/bool/NaN/infinity/finite64-to-infinite32 and row/schema/source/availability contradictions fail first even with another gap/backend absent. No model-specific dropped row or unobserved-outcome filter.
- Actual pinned20+row/five-night synthetic fits through the entry, complete same-cohort native predictions and full receipt/model/row-ID bindings. Public native-vs-JSON unrounded parity1e-12/rounded8-decimal predictions, float32 neighbours and deterministic same-runtime replay; genuine backend mandatory on CI with no skip/fake estimator. No real TRAIN/accuracy claim.
- Whole-set A2 capability block with intact bound runtime receipt; corrupted/rehashed native status/model/count/recipe/TRAIN/future/flag/cell/area/window/hash/coverage disagreement fails, including last row. No earlier candidate escapes on a later failure.
- Actual shared-cap/deadline interruption at ownership, nested A1 first numeric guard, A2 import return/monitor, predict and final seal. Same original parent object for affected standard/capacity subclasses and BaseException controls even through nested normalization; genuine internal classifications remain. Callback counts/order on normal old paths unchanged.
- Combined real encoded bytes/nodes/depth/rows/final output limits, owned input/child outputs, final hash/check expiry and caller mutation controls. No hidden fourth fit, budget refill, new persistent/campaign authority, source reader, target/evaluation payload, file publication or route/metric policy change.

Risk is LOW for mechanical reuse, MEDIUM for the new explicit protocol, whole-set capability disposition and nested origin/budget boundary. Independent design/code review plus actual exact/fresh Ubuntu are required. Software config admission is not scientific model selection: common-fold metrics, untouched confirmation, trusted prereveal/consumption, calibrated policy and owner-critical Champion/production gates remain unchanged. Current source-only counts/UNKNOWN are not scientific TRAIN; full seven deployment sources and real eligible outcomes remain missing. Source adapters, complete G0 summary, Stage1 and parent still reject/do not dispatch A2 until separately designed and approved. No accuracy, official forecast or Master completion follows from this design.
