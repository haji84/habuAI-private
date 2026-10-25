# Full-universe G0 score-summary foundation v1 — design proposal

Status: **DESIGN_ONLY / IMPLEMENTATION_NOT_APPROVED**. This commit changes this
specification only. Base is `483800bfd1ba9e5603d22794c659542ca325b0a2`.
Root and independent review must approve this contract, and the reviewed compact
OSM change must pass its main integration gate, before runtime work begins.

This design-only clarification addresses the two findings against immutable
`d52d16c129207f53c68f1757309766cf5bb57651` in the private independent receipt
`.worktrees/g0-full-universe-score-summary-design-review-20261026.md`, 7,627 bytes,
SHA-256 `c53966869f5510078c061a394fba8971997ca18f7b73cb347811ef78da3a43ed`.
That receipt's disposition was NEEDS_CLARIFICATION; this revision awaits exact
re-review and does not imply runtime approval or implementation PASS.

## Purpose and current gap

Add one standalone, unconnected diagnostic operation that scores **every** unit
in a declared G0 universe, retaining bounded exact per-area statistics instead
of the complete row/prediction arrays. It validates the complete same forecast
closure and exposes nothing until validation, model checks, final rescans and
sealing finish. It does not fit a model, issue a forecast, dispatch the research
parent, evaluate outcomes, select candidates or create a promotion slot.

The source-grounded prerequisite is the independent read-only audit
`.worktrees/full-night-model-next-slice-audit-20261026.md`, 9,934 bytes,
SHA-256 `98c50cac2c63bc1b5a6240b6b28a84350f63e5f3256655f5f8b17b07db2f1ff2`.
At this base, `g0_forecast_contract._validate(collect=False)` already validates
all shards, hashes all owned `_model_row` results and rescans the closure.
`collect=True`, the research preparation APIs and Stage1 source adapters require
complete arrays capped at 120,000 rows and 16 MiB. A new summary cannot impersonate
those arrays or their existing prediction/prepared hashes.

The independently reviewed compact OSM source `3e35f703bd0629c21620663593230c5d101e7296`
has a separate actual-source software rehearsal: 16,990 cells × 72 windows =
1,223,280 units, 81.219 seconds, 1,412,221,558 cumulative read bytes. This proves
that particular input-validation run only. It did not score models, collect
model rows, fit TRAIN, evaluate Stage1 or run the parent. Its native whole-worker
PeakWorkingSet was 183,341,056 bytes, not a total-RSS ≤128 MiB result. Extra
model/code reads, scalar work, exact reductions, final seals, memory and the
complete new operation's 300-second feasibility remain **UNMEASURED**.

## Alternatives and chosen boundary

| Approach | Consequence |
| --- | --- |
| Raise collector limits, concatenate chunk predictions or expose a public row iterator | Rejected. Changes existing capacity/whole-universe guarantees; partial arrays and B1 ranks are not native full-universe artifacts. |
| Private fixed reducer in the existing complete G0 validator | Chosen proposal. One physical/source validator and canonical joined hash; bounded state; additive diagnostic output only. |
| Lossless full-native prediction/rank transport with external/global ordering | Separate later design. Necessary for existing HB-B1 global/conditional ranks and possibly native Stage1/parent transport; not implemented by an area summary. |

There is no public arbitrary row callback, generator, plugin reducer, configurable
scoring expression, cache exemption, second parser/physical validator, new learner
package or per-shard refit. A deadline/cancellation `check()` receives no row or
state and is not a data consumer. Default G0 APIs keep their exact output fields,
hash definitions, read order, capacities and counters.

## Proposed entry point and transport

```python
score_g0_forecast_summary(
    root, summary_manifest_ref, operational_night, as_of, *,
    expected_feature_definition_sha256, expected_candidate_config_sha256,
    budget_seconds=30, _read_context=None, check=None)
```

Proposed location: `src/g0_full_universe_score_summary.py`, outside `models/`.
`summary_manifest_ref` is an owned primitive `{path, sha256, size_bytes}` reference
to a new, immutable development JSON profile. Physical SHA hashes file bytes;
every separately named canonical/content SHA hashes the specified parsed body.
Neither is an issuer signature or proof that a fitted model used authentic data.
There is no caller-supplied model object or callback-owned row container.

The profile's exact fields are:

| Field | Required content |
| --- | --- |
| `schema_version` | `habu-g0-full-universe-score-source-v1` |
| `kind` | `UNCONNECTED_DEVELOPMENT_SCORE_SUMMARY` |
| `operational_night`, `fit_cutoff`, `forecast_cutoff` | Aware timestamps/night bound to config, models and G0 manifest; fit strictly precedes night start and forecast cutoff. |
| `feature_definition_sha256` | The complete registered strict definition digest, not the names digest. |
| `forecast_manifest` | Existing exact G0 byte reference; no subset/domain override. |
| `candidate_config_manifest` | Existing source-profile reference accepted by `load_research_candidate_config`; expected canonical config SHA is also supplied to this API. |
| `fit_lineage` | Null for explicitly missing evidence, otherwise exact `{ref, lineage_sha256, readiness, usable_at}`. |
| `models` | Exact ordered three entries `{candidate_id, artifact}`; `artifact` is null or exact `{ref, model_sha256, readiness, usable_at}`. |
| `readiness`, `usable_at` | All four own stages; effective maximum includes all supplied prerequisites. |

This is a new source/summary transport because old prepared/native prediction
schemas require full arrays. It is not a new request version for the parent or
a replacement for the existing research config. No `trusted`, eligibility,
authority or arbitrary extra fields are accepted.

Reuse the existing candidate-config **v2**, exact three slots, uniform first and
two unique optional IDs. This foundation supports only `uniform/HB-A0/HB-A1`;
the order of A0/A1 remains the exact configured order. No new one/two-model config
surface, fourth candidate or fallback is introduced. A config containing HB-B1
raises an explicit `IMPLEMENTATION_BLOCKED` capability error after config and
known supplied envelope/ref checks; it produces no summary. Its absent global,
conditional and native rank artifacts are not relabeled as probabilities.
HB-A2's standalone backend/admission is also outside this contract.

### Label-free TRAIN identity

The new fit-lineage declaration has exactly `schema_version`
(`habu-g0-fitted-lineage-declaration-v1`), `kind`
(`LABEL_FREE_TRAIN_IDENTITY_DECLARATION`), `heldout_night`, `fit_cutoff`,
`selection_sha256`, `corpus_sha256`, `source_sha256`, `source_received_at`,
`training_nights`, `training_window_start_max`, `counts`, `feature_names`,
`training_rows_sha256`, `training_row_ids_sha256`, `raw_feature_rows_sha256` and
`model_sha256_by_id`. The map has the exact configured three keys, each equal to
its supplied artifact's canonical SHA or null when that artifact is missing.
Counts use the existing exact shape and bounded binary-count consistency;
insufficient declared support with a missing model is a data gap. A supplied
fitted model must meet its existing model-specific support floor. Nights are
sorted/unique/valid and prior to the held-out night;
the actual maximum declared training window is aligned, belongs to the last
training night and strictly precedes fit. Source-map received times strictly
precede fit. No label rows, event ledger, calibration outcomes or confirmation
references are embedded or followed.

Model selection/fit cutoff/counts and every overlapping retained field must
match this one identity, using the explicit feature-order projections below
rather than requiring different native ordered vectors to equal each other.
A0's `selection_sha256` and A1/uniform's
`training_selection_sha256` bind the same selection. A0/A1 corpus, source map,
received times, nights and latest window must match. A1's three row/feature
snapshot hashes must match; uniform's smaller original envelope is preserved,
so absent fields are declared by this sidecar, not invented in that model.
Every model SHA matches the declaration and its own canonical model body.

`fit_lineage.feature_names` is a unique, lexically sorted canonical list, exactly
the order retained by the selected TRAIN envelope. For the complete supported
three-model set it equals `sorted(prospective_candidate_model.FEATURES)`:

```text
humidity_pct, precipitation_mm, road_length_m, slope_deg,
temperature_c, tpi_m, wind_cross_road_proxy
```

The model-specific comparisons are exact projections, not a shared vector order:

| Retained field | Exact comparison with the sidecar |
| --- | --- |
| TRAIN selection `feature_names` (asserted identity, not reopened here) | The same sorted canonical list. |
| HB-A0 `selection_feature_names` | The same sorted canonical list, byte-for-byte list equality. |
| HB-A1 `feature_names` with the required full-seven mask | The same names in existing native `FEATURES` order: `temperature_c, humidity_pct, precipitation_mm, slope_deg, tpi_m, road_length_m, wind_cross_road_proxy`. First require exact canonical membership; then compare the retained model list to this native ordered projection. |
| uniform model | No feature-name field exists; do not add one. Its existing selection hash and the sidecar bind the assertion. |

An incomplete but otherwise valid sidecar schema remains a concrete whole-set
data gap. A supplied A1 model must still pass its own exact full-seven native
schema/recipe guard; a retained model/sidecar identity contradiction still rejects
before that gap. Never sort its `feature_names`, means, scales, coefficients
or input numeric vector, weaken equality to set equality, or rewrite the model
and reseal it merely to make cross-field comparison pass.

This sidecar is a **caller assertion**, even after byte and digest verification.
The inference operation does not read/refit the original labelled TRAIN corpus
or validate its raw qualification, actual row counts, training execution,
issuer, source receipt authentication or pre-reveal admission. Model guards
validate the retained serialized claims only. Actual fit/source linkage remains
`CALLER_DEPENDENCY_REQUIRED`; never describe this as source-certified training.
Opening target files merely to hash them at prediction time is also prohibited.

## Shared source, time, ownership and failure rules

Use the existing `ProspectiveReadContext` and `G0ArtifactReader`, the fixed G0
policy and the existing candidate-config source loader/rechecker. One absolute
deadline (default 30 seconds, maximum 300) and cumulative actual-read ledger
(maximum 2 GiB) cover metadata, policy, current code bytes, models, G0 initial
reads, decoding, all existing internal reads and all final rescans. Previously
charged bytes remain charged. No nested fresh allowance, phase-wide `restrict`
that accidentally lowers the whole job, unaccounted `Path.read_bytes` or CLI
validator call is allowed. Accounting receipts distinguish snapshots taken at
different times; only the final summary ledger equals the final context.

Config/code/policy reuse their existing strict boundary
`B=min(fit_cutoff, forecast_cutoff, heldout-night 07:00)` and existing exact
current `code_paths` membership/raw-byte checks. No membership-only scan is
called code-byte authentication. The A1 full recipe's two implementation SHAs
must match those actual code-byte references. Model and label-free lineage
bindings have all four readiness stages strictly before forecast cutoff;
effective `usable_at` is their own maximum plus all consumed prerequisites.
Profile usability includes config, forecast and all supplied model/lineage
usability. No timestamp is reconstructed/backdated from Git commit dates.
These declarations do not authenticate historical availability, issuer,
installed Python/native dependencies or loaded bytecode.

Before payload opens, snapshot input ref/hash/time primitives, reject all known
unsafe/reserved paths and aliases, and preflight reparse/ancestor containment.
Profiles/lineage use `protocols/development/` or `config/`; model artifacts use
`models/candidates/`; forecast paths retain the existing G0 namespace rules.
Metadata cannot redirect to raw/outcome/ORIGINAL/incoming/reports/sealed/
confirmation sources. Role-conflicting same-path or same-byte aliases cannot
launder label evidence into models/features. TRAIN source hashes inside the
label-free declaration are identity strings, not permission to open those paths.
Use the existing portable component and guarded-local-path rules, not a new
filesystem authorization system.

Known schema/hash/model/recipe/time/feature/physical contradictions raise
`ValueError` before an insufficiency decision. Null missing model/lineage
bindings and a valid non-seven-feature forecast schema accumulate concrete
`NEED_MORE_DATA` blockers; missing required keys/readiness are malformed, not
healthy missing evidence. Supplied model artifacts must be valid fitted models;
an invalid support-count claim is not converted to missing data. Missing files
are explicit missing-source blocks, with no broad `ValueError` swallowing.
If a required source cannot be validated, no complete diagnostic summary is
returned. Existing `InputCapacityError` and `TimeoutError` preserve capacity and
deadline identity. A new `ScoreSummarySourceBlocked(ValueError)` identifies an
absent required metadata file or a structurally valid new metadata availability
claim at/after its boundary; it does not catch/reclassify arbitrary G0 errors or
callback exceptions. Unsupported B1 uses `ForecastCapabilityError` with
`IMPLEMENTATION_BLOCKED`. No new exception changes a legacy entry point.

Even with known insufficiency, validate every supplied known model/config and
all complete forecast shards, all supplied known A1 raw-field physical bounds,
reachability, source consumption and final rescans. An invalid last shard must
not disappear behind a missing model or missing temperature column. On valid
insufficiency, return the new receipt with `model_summaries=[]`; never partial
uniform/A0 results. Any already computed private state is discarded.

All parsed payloads and scalar work use owned data. The caller's check can mutate
its original ref objects without changing copied bindings or receipt contents.
Check through bounded scans, copies, numeric steps, integer adds, hashing,
sorting, rescans, sealed encoding and immediately before return. Catch numeric
conversion/overflow errors only around the local operation: callback exceptions
including `ValueError`, `OverflowError`, `TimeoutError` and `KeyboardInterrupt`
must escape as the same object. There are no files or partial output publications.

## Single validation seam and unchanged scalar numerics

`g0_forecast_contract._validate` gains only a default-disabled private mode that
constructs the fixed reducer. The public validate/load paths cannot accept a
reducer. The reducer receives each owned `_model_row` after existing physical,
feature/source/readiness/valid-time checks; the same core updates the original
complete joined hash. It sees the exact existing order: sorted
`(cell_partition,time_partition)` shards, then existing in-shard cell/time order.
This is not a new global row-ID sort. Reordered shard declarations do not change
it; a different physical partitioning may change this existing ordered hash.

No list of all units, output row IDs, row-ID set, per-shard prediction arrays or
unbounded lineage cache is retained. G0 already proves canonical full coverage.
Pending metadata refs are included in the final guarded common rescan/closure
barrier; code membership is checked before/after/final. If reuse of an existing
loader performs another read/rescan, charge it rather than trusting a fabricated
receipt or hiding duplicate I/O. Default-disabled calls retain old read ledgers.

Reuse these exact existing computations and admission guards:

| Model | Reuse requirement |
| --- | --- |
| uniform | Extract the exact scalar from `research_model_adapter._uniform`. Add its missing private shared serialized-envelope/count/prior guard in that same pure module, using the existing Stage1 guard as an independent admission oracle. The old builder calls the scalar with identical output numerics/fields/hash. No copied Beta formula in the new reducer. |
| HB-A0 | Reuse `occupancy_shrinkage._validate_model`; extract/reuse its exact fitted-area lookup/global fallback from `predict_shrinkage`. Existing `_area_probability` remains the guard's support/prior check. No refit or formula rewrite. |
| HB-A1 | Reuse `hba1_feature_candidate._model`, full-seven recipe and the scalar body currently in `_predict`, including finite intermediate checks, legacy `learner._score` and round-to-8. Extract a private owned-row scalar and have the old loop call it. No optimizer, float32 substitution or new calibration. |

Optional private `check` seams in existing guard/copy loops must preserve old
defaults and every old artifact/hash **for identical owned inputs and identical
code-binding declarations in the same runtime**. The whole-row public predictors
keep their
120k/16 MiB limits; they are not called on chunks. The new reducer checks all
supplied known raw A1 fields even when schema is incomplete, reusing current
physical-range semantics. Exact seven raw features, not the three static OSM
features, are required for A1. Unknown/null/NaN/nonfinite values are never zeroed;
numeric overflow/nonfinite score is a local `ValueError`.
Uniform currently has no standalone native model validator; this small guard
addition must be reviewed explicitly, not described as an already present API.
The existing Stage1 adapter and evaluator remain unchanged and unconnected.

### Numeric compatibility versus current code-byte identity

The compatibility oracle archives the pre-extraction source and immutable full
historical golden artifacts before edits. It invokes old and extracted public
paths with the same owned selection, model, forecast inputs, recipe/config/code
declarations, code-payload fixture context and runtime. The old path must execute
the genuinely archived pre-extraction implementation, with provenance for the
source/dependencies it uses; it cannot alias/import the new scalar as its old
reference. Compare complete native objects, canonical bytes and
all hash fields, including recipe/model/prediction/receipt identities. Do not
drop hash fields, apply a numeric tolerance, accept a platform-hash whitelist or
overwrite old goldens to make this comparison pass. Default G0 receipt/read-order
and ledger comparisons have the same fixed-input/code-binding prerequisite.

This is a different assertion from a current source-bound execution. Extracting
the A1 scalar changes `src/models/hba1_feature_candidate.py`, one of the exact
files pinned by `recipe.implementation_sha256`. Its actual raw-file SHA changes;
a newly bound recipe SHA, model SHA, config/source receipt and any dependent
strict feature-definition/code-closure digest consequently change wherever
their contents change. Preserve historical recipes/models/receipts unchanged;
create new correctly bound declarations instead of pinning the new file to its
old SHA. No existing optimizer, numeric-recipe tag, native feature order or
canonical hash definition changes.

Keep two separate decisive checks: (a) full old/current output equality under
identical immutable declarations to prove the numerical extraction; and (b)
the current snapshot's actual raw-byte code map, exact membership, recipe's two
implementation refs and source-profile checks to prove declared current-byte
consistency. The pure oracle's fixed declared code SHA is not current-file
authentication. A stale historical recipe against changed current bytes must
fail the source-bound check; it must not be accepted merely because numerical
predictions match. Conversely, naturally changed current-bound digest fields
are not a numerical regression or a reason to remove them from the oracle.

## Exact statistics, full areas and framed stream identity

All three native outputs here are finite conditional observed-unit probability
scores in `[0,1]`, with probability validity/calibration **NOT_VALIDATED**.
An area mean is descriptive `MEAN_NATIVE_UNIT_SPATIAL_SCORE`, not organism
occupancy, encounter probability, count, diagnostic hierarchy rank or official
Top10 performance. Geometry remains `CELL_ORIGIN_PROXY_NOT_POINT_GEOMETRY`.

For each model/physical 1km area, retain an integer unit count and exact sum of
the native float values, not a running float or mean of shard means. Each finite
binary64 value has an exact integer multiple of `2**-1074`; accumulate that
integer, then convert `Fraction(integer_sum, count * 2**1074)` to float once.
This must equal `statistics.mean(native_values)` in the same runtime. Zero is
canonicalized exactly as that oracle, not chosen for a preferred result.
For ≤4,000,000 nonnegative scores ≤1, sum width is bounded by 1,097 bits.
Check count/cap/deadline before each add/shift and reject over-width state.
No per-row `Fraction` list or bulk unconstrained set/union is needed.

Every area represented by the full declared domain remains in the result,
including zero-score areas and areas absent from TRAIN (A0 retains its existing
global fallback). Missing/unknown scores block the whole result; an area is
never dropped or imputed. Each model's area counts sum exactly to G0 row_count,
each area count agrees across models, and all area IDs agree with the domain.
Sort Top10 by `(-exact_oracle_float_mean, lexical_area_id)`; return exactly
`min(10, area_count)` unique IDs. The rounded native float mean, not an alternate
unrounded rational ranking, defines ties. All area summaries are returned in
lexical area-ID order. No recall, denominator or held-out outcomes are computed.

Each model has a **new** `score_stream_sha256` with this exact framing:

1. Prefix ASCII `HABU-G0-SCORE-STREAM-V1` followed by NUL.
2. A header frame: byte `H`, unsigned 64-bit big-endian payload length, canonical
   UTF-8 JSON `{candidate_id, model_sha256, recipe_sha256, candidate_config_sha256,
   feature_definition_sha256, training_selection_sha256, fit_lineage_sha256,
   operational_night, fit_cutoff, forecast_cutoff, score_semantics}`. Non-A1
   recipe SHA is null. Canonical JSON uses the existing repository encoding.
3. For every canonical G0 unit, byte `R`, the same length framing, canonical
   `{ordinal, row_id, native_score}`. Ordinal is zero-based and consecutive.
4. A trailer frame `T` containing canonical
   `{row_count, canonical_joined_rows_sha256}` from the same finished G0 core.

The header is not modified after streaming; the trailer binds the completed
joined hash without a second forecast replay. This is not any old native
`prediction_sha256`, prepared hash, Stage1 score SHA or issuance artifact.

## Explicit bounded state and result

Existing G0 bounds remain unchanged: ≤100k cells, ≤144 windows, ≤4M whole units,
≤256 shards, ≤32 features, ≤400k numeric joins/shard, ≤128 MiB/source and
≤384 MiB/shard, plus the same shared ≤300 seconds/2 GiB actual read budget.
Legacy whole-row collection remains ≤120k rows/16 MiB.

New local bounds: exactly three models; ≤10,000 distinct 1km areas and ≤30,000
`(model,area)` accumulators; counts ≤4M; exact sum ≤1,097 bits; metadata integers
≤64 bits checked with `bit_length` before abs/copy/encode; strings ≤4,096 UTF-8
bytes, refs ≤512 characters; metadata depth ≤12 and ≤2M JSON nodes. Profile and
lineage each ≤256 KiB physical bytes; each model ≤4 MiB. Combined owned
profile/config/lineage/model canonical input ≤16 MiB **before own copies**.
Current code closure retains its existing ≤256 refs, 4 MiB/file and candidate
source phase ≤16 MiB first-read-plus-rescan constraints. Final sealed result
including its hash is ≤16 MiB; each score frame ≤4 KiB. Check sizes/widths before
growing containers or creating integer/encoding copies. Exceeding a local cap
is `CAPACITY_BLOCKED`, never truncation, sampling or a smaller horizon.
These are logical allocation bounds, not a proven OS-RSS ceiling.

The result has exactly `schema_version`, `summary_kind`, `status`, `blockers`,
`source_manifest_ref`, `source_manifest_canonical_sha256`, `operational_night`,
`fit_cutoff`, `forecast_cutoff`, `candidate_ids`, `candidate_config_sha256`,
`candidate_config_source_receipt`, `feature_definition_sha256`, `fit_lineage`,
`training_selection_sha256`, `model_bindings`, `forecast_receipt`, `full_counts`,
`model_summaries`, `consumed_refs`, `consumed_sha256`, `actual_read_bytes`,
`summary_read_bytes`, `source_authenticity`, `source_authentication`,
`fit_lineage_authentication`, `scientific_status`, `authorities`, `limitations`
and `summary_sha256`. Version is `habu-g0-full-universe-score-summary-v1`, kind
is `UNCONNECTED_DIAGNOSTIC_ONLY`, and status is `COMPLETE_DECLARED_SCORE_SUMMARY`
or `NEED_MORE_DATA`. Refs/bindings preserve original byte sizes and separately
named canonical identities; `model_bindings` retains the exact input order and
nullable bindings. A missing lineage has null selection SHA. `full_counts` has
exactly `{cell_count,window_count,shard_count,unit_count,area_count}`.
`summary_read_bytes` is final bytes minus entry bytes; cumulative
`actual_read_bytes` includes earlier parent work. Each successful model summary
has exactly
`candidate_id`, `model_sha256`, `recipe_sha256`, `score_semantics`,
`score_stream_sha256`, `unit_count`, `area_summaries` (exact records
`{area_id,unit_count,mean_native_score}`) and `top10_area_ids`.

`summary_sha256` hashes the complete body excluding itself. After adding it,
encode/cap/check the entire sealed result and check the shared guard immediately
before return. There are no `prediction`, `unit_predictions`, `unit_scores`,
`forecast_row_ids`, `prepared` or `candidates` artifacts. A valid NMD result has
no model summaries/stream hashes/Top10; a complete G0 receipt still does not
turn a missing A1 input into an eligible set.

All results retain `source_authenticity=NOT_ATTESTED`,
`source_authentication=CALLER_DEPENDENCY_REQUIRED`,
`fit_lineage_authentication=CALLER_DEPENDENCY_REQUIRED`,
`scientific_status=NOT_VALIDATED`. Fit, selection, promotion, scientific execution,
official issuance, production activation, confirmation, trusted campaign and
pre-reveal authorities are false. The `authorities` object has exactly those nine
keys, named `fit_authorized`, `selection_authorized`, `promotion_authorized`,
`scientific_execution_authorized`, `official_issuance_authorized`,
`production_activation_authorized`, `confirmation_authorized`,
`trusted_campaign_authorized`, `trusted_pre_reveal_authorized`.
Real TRAIN/source-qualified fit count stays zero. Byte-verified models/TRAIN
metadata do not certify genuine labels, issuer,
training execution, untouched confirmation or model admission. No outcome/label
payload is opened while predicting. No artifact is published to disk by this API.

## Proposed future implementation paths and RED → GREEN plan

Only this specification is owned/changed now. Future runtime ownership must be
approved separately: new `src/g0_full_universe_score_summary.py`; narrow private
seams in `src/g0_forecast_contract.py`, `src/research_model_adapter.py`,
`src/models/occupancy_shrinkage.py`, `src/models/hba1_feature_candidate.py` and,
only if required for cooperative copy/guard reuse, `src/models/research_selection.py`.
New `tests/test_g0_full_universe_score_summary.py` plus affected existing numeric
tests and a new independent review record. No parent/Stage1/policy/STATE/cycle/
raw/requirements or existing numeric model-recipe changes belong in this slice.
New declarations must bind the actual changed code bytes; historical declared
recipes and source artifacts remain immutable.

| Task / decisive initial RED | Required GREEN evidence |
| --- | --- |
| Extract scalar/admission seams; freeze existing synthetic full artifacts before edits. | Same-runtime pre-extraction independent reference with identical owned inputs/code declarations: full serialized models/native predictions/bytes/all hashes exactly unchanged, including A1 extreme/intermediate checks and old default G0 ledgers/read order. Independently verify the current actual raw-byte code map and correct new recipe/model/source bindings; stale old-code declarations reject. No excluded hash fields, platform-hash whitelist or modified historical goldens. |
| Valid three-model full-seven fixture with sorted selection/sidecar/A0 names and native-order A1 names. | Cross-field admission succeeds without mutating/reordering any native model/vector/hash. Reversed/noncanonical sidecar order, changed A0 order, or A1 sorted into lexical order rejects; native A1 order is not mistaken for a mismatch. |
| Small whole-U oracle using existing full public predictors, then project all native units with independent `statistics.mean` and lexical Top10. | New stream bytes/digest, every area/count/mean/Top10 exactly equal; unequal shard sizes, reordered shard declarations and several cp/tp layouts. Native prediction hashes remain separately named. |
| Rounding control `[1.0, 2**-53, 2**-53]`, subnormal/zero, ties and uneven per-area counts. | Mean `.3333333333333334`, unlike naive `+=`; no averaging shard means. Zero/unseen areas retained; lexical ties exact; one area and <10 areas handled. State bounds checked before each insertion/add/shift. |
| Valid OSM-like three-feature schema, null model/lineage, incomplete A1 schema plus an invalid known humidity in the last unit. | Valid gaps produce whole-set NMD/no partial; known contradictory field, last shard or supplied model rejects first after all relevant checks. No imputation, refit or fallback. |
| Wrong model/config/recipe/TRAIN/hash/cutoff/night/physical-unit claims; unsupported B1 config; stale code closure, raw-vs-canonical hash mixup, alias/reserved/reparse ref. | Explicit error class; no summary/labels/confirmation opened; genuine caller exceptions preserved by identity, including callbacks during numerical/hash/seal steps. |
| Last-shard corruption; mutation during final source/model/code rescan; callback mutation of caller refs; expiry after digest/full sealed encode. | Public result count zero on failure, immutable bindings, all prior read charges retained; no row iterator/callback leakage and no pending partial publication. |
| Local area/metadata/output/bit/frame cap, cumulative prior charges/remaining+1 read, final-seal cap at length−1/equality. | Capacity is explicit and all-or-none; no new allowance. Final context equals final result ledger, nested earlier receipt snapshot is identified separately. |

First run focused new synthetic tests and existing affected numerical/G0 tests;
record actual RED and GREEN, exact source/test hashes, independent hostile review
and whole-runtime oracle. Native path/cleanup tests and genuine Ubuntu CI remain
necessary; a Windows run cannot certify POSIX behavior. No actual source fit or
large rehearsal is authorized by this design. A later authorized fresh-code
resource run must measure elapsed/read-byte ledger/native peak RSS and footprint;
do not infer model-scoring performance from the earlier input-only 72-window run.

## Approval/risk boundary and remaining blockers

This is MEDIUM/local additive only while default APIs/numeric artifacts/limits,
source guards and permissions remain unchanged and the new summary stays
unconnected. Replacing canonical predictions/evaluation/ranking definitions,
relaxing old capacities, reducing the declared universe, extending canonical
parent/issuance authority or changing Master Goal architecture crosses the HIGH
boundary and needs a separate owner gate. A separately reviewed lossless native
transport is not automatically a canonical definition change, but is not approved
or delivered here.

Current real-data gaps remain: source-qualified TRAIN0; independent outcomes and
measured search qualification; source-bound seven raw predictors for HB-A1;
trusted model/source/runner admission, campaign exposure and pre-reveal locks.
Current pure capability gaps remain: native HB-B1 global/conditional rank arrays,
HB-A2 registration, summary-aware Stage1 transport/evaluation, research-parent
dispatch/REPLAY and official P0/route/production integration. An actual OSM
full-domain receipt or this new diagnostic summary must never be called
full-night model/Stage1/parent/scientific completion.
