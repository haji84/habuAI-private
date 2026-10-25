# G0 score-summary to Stage1 transport v1 — design only

Status: **DESIGN_ONLY / IMPLEMENTATION_NOT_AUTHORIZED**. This document alone
is owned by Lane F. Base is actual main
`f4222f7dc2167dba7c99b50b128e6789c9264976`; the separate summary prerequisite
examined is exact `eb20045228189c1b3b10ea01862d088d26eb6359` (entry 30,174 bytes,
SHA256 `4259b7f743d2747d3d5b0bfc440fa16234b0d3555efd3888b8ce7d977976e7df`).
It is not present in this design branch and is not assumed merged or accepted.
Its independent final gate, coordinator integration/new freeze/exact and fresh
CI, the concurrent data prerequisites, independent review of this design and an
explicit root runtime dispatch must precede implementation. No runtime, test,
state, source freeze, policy, Raw or ORIGINAL change is made here.

This revision resolves the blocking identity clarification against initial
`68cab9917580cd57154d462b99021b0842539f43`. The immutable independent design
receipt `.worktrees/g0-score-summary-stage1-transport-design-review-20261026.md`
is15,895 bytes / SHA256
`c325c582b9a47661289eb52648ad25f8acd0a4ac6fca5c36d38777e199185f9a`, disposition
NEEDS_CLARIFICATION. Re-review of this revision is pending; no design PASS or
runtime authorization is inferred.

## Gap established from current code

| Examined implementation at this base | Existing contract and resulting gap |
| --- | --- |
| `evaluation/stage1_source_adapter._prepared_limits`, `_prepared_owned` (lines145–340) | Requires full G0 rows and all three complete native prediction arrays, at most120,000 units. It verifies native identities, groups each candidate's spatial scores by area and applies `statistics.mean`. A summary has the same area statistic but lacks those native arrays and their hashes. |
| `_scope_projection` (lines343–366) | Binds original manifest horizon to all observed forecast windows and checks that the prior bbox contains the **whole100m square** of every row's cell. Distinct original domain cells and a validated rectangular horizon suffice; no unit-array expansion is mathematically necessary. |
| `_evaluate` (lines419–670) | Admits predictions before evaluation reads; loads prior scope before outcomes; reuses actual CSV parsers, source DAG, complete coverage/individual ledger, evaluation and final source rescan. Only its admission/identity/geometry seam needs a new mode. |
| `evaluation/full_ledger_stage1._scores`, `_configured_scores`, `_measure` (lines224,540,491) | The public configured evaluator is **a function in this module**, not a `full_ledger_stage1_v2.py` file. Both score admission and returned `candidate_lineage` explicitly require `prediction_sha256`. A framed stream SHA cannot truthfully occupy that field. |
| `research_pdca_adapter` requestv4 and `_v4_stage1_admission` (lines100,295 onward) | Selects TRAIN, collects full future rows, fits/prepares and admits native configured predictions before Stage1. This path still blocks above collector capacity; no summary parent request exists. |
| Separate summary `_ScoreReducer` | Computes every canonical G0 unit, exact per-area mean/count, lexical Top10 and a framed score-stream digest, then returns only after closure/rescan/seal. Supports exactly uniform/A0/A1; missing seven predictors/model/lineage gives whole-set NMD. It does not authenticate TRAIN or produce a native prediction. |

The source-adapter mean and summary mean are mathematically the same binary64
statistic; identical owned units/code declarations on the same runtime must
produce exactly equal floats, not approximate equality or shard-mean averages.
This transport is lossless **for the existing Stage1 area-score statistic and
identity evidence**. It cannot reconstruct native per-unit arrays, native
prediction SHA, HB-B1 global/conditional ranks or point/time evaluation artifacts.

Read-only native anchors at mainf4222:

| File | Bytes | SHA256 |
| --- | ---: | --- |
| `src/evaluation/stage1_source_adapter.py` |41569|`092f851495c34b8cb3b00e68a386d520ea7cee38239049c65e683a6739b03cf0`|
| `src/evaluation/full_ledger_stage1.py` |31246|`9eaab362a065f7e2fb0a7405c2cd8c17468308301316f432b7b45429c2269cb7`|
| `src/research_pdca_adapter.py` |31947|`1892440621057125b40adfef09a583395a744e505a3cc5fff657fa0f2db2fcc9`|
| `src/g0_forecast_contract.py` |55032|`4b31cca1120925f25f8687bab98366cbde93e38685cf04eb5dcd5622b6cc0e21`|

## Alternatives and proposed smallest useful boundary

1. **Reuse scores-v2 by writing `score_stream_sha256` into
   `prediction_sha256`, or manufacture prepared/forecast rows. Rejected.** This
   changes identity meaning, bypasses native admission and misrepresents a
   complete bounded collection. A fake native digest or empty/dummy rows cannot
   carry a full-universe proof.
2. **New explicit summary score/source/result versions, one existing numeric
   evaluator core, standalone source entry. Recommended.** Admit/recompute the
   complete summary before outcomes, project its complete area means and reuse
   the existing ledger/matching/Top10/bootstrap calculation. Only identity and
   compact geometry admission differ. Old defaults remain untouched in behavior.
3. **Produce native full prediction arrays through external lossless transport.
   Deferred.** This would serve a broader consumer and perhaps B1, but requires
   separate storage/order/rank/whole-artifact design. It is not needed for this
   statistic and is not permission to raise collector limits.

The recommendation is a development diagnostic projection, unconnected to the
research parent. It does not create another learner, evaluator algorithm,
campaign, command pipeline, fourth candidate, A2 registration or official route.

## Proposed source API and exact identities

```python
evaluate_stage1_summary_sources(
    root, summary_manifest_ref, stage1_manifest_ref,
    operational_night, forecast_as_of, *,
    expected_feature_definition_sha256, expected_candidate_config_sha256,
    context)
```

`context` is the mandatory existing `ProspectiveReadContext`. The refs are exact
owned `{path,sha256,size_bytes}` physical-byte references. The entry accepts
neither a caller-supplied summary object nor a trusted/authenticated boolean.
It invokes the existing `score_g0_forecast_summary` **once**, under this context,
and requires `COMPLETE_DECLARED_SCORE_SUMMARY`. All summary source/config/model/
TRAIN-assertion/definition/scalar checks, every physical G0 unit and full closure
rescan complete before any Stage1 manifest or outcome payload read. No fitting,
TRAIN targets or confirmation are read by this operation. The inherited label-
free TRAIN/model assertions remain caller dependencies, not newly attested facts.

The config is the existing exact candidate-configv2: uniform first plus A0/A1
in either declared order. Its complete three-slot identity, recipe and strict
feature-definition digest are bound throughout. Any config containing B1 is
explicit `IMPLEMENTATION_BLOCKED` before evaluation-manifest reads, with no
partial uniform/A0 evaluation, fallback, reorder or new registry. A valid missing
summary input yields whole-set `NEED_MORE_DATA`, empty metrics and no outcome
reads after all known forecast/model contradictions and full forecast rescans
have been checked by the summary entry. Source absence, capacity and malformed
evidence retain their distinct existing classifications; no synthetic summary.

### Stable projection and actual execution receipt are different identities

The existing summary's `summary_sha256` correctly hashes its **whole** body
excluding only its own field. That body includes actual cumulative counters and
nested config/forecast receipts. An incoming context with genuine prior charges
therefore changes that whole execution receipt SHA, even for identical physical
inputs, models, streams and means. Do not change eb200/the old summary schema,
strip fields from its old hash, reset/fake counters, or assume that whole SHA is
phase-invariant. Its actual full bytes/hash are retained as execution evidence.

Define a NEW explicit canonical JSON object, the **score-summary projection**.
`H(x)` is SHA256 of the entire exact object in UTF-8, sorted keys, compact
separators, Unicode retained and nonfinite numbers rejected. The projection has
no self-hash field. `score_summary_projection_sha256=H(projection)` is a new
identity with its own schema, not an alternate interpretation of the old hash.
This exact20-field projection is constructed only after complete actual summary
validation and exact-ref domain/config rereads, before outcome access:

```text
schema_version, purpose, summary_manifest_ref, summary_manifest_canonical_sha256,
operational_night, fit_cutoff, forecast_cutoff, forecast_manifest_ref,
canonical_joined_rows_sha256, domain_ref, horizon, candidate_ids,
candidate_config_source, candidate_config_sha256, feature_definition_sha256,
fit_lineage, training_selection_sha256, model_bindings, full_counts, model_summaries
```

Exact values and scopes:

- `schema_version=habu-g0-score-summary-projection-v1` and
  `purpose=DEVELOPMENT_EVALUATION_ONLY` are constants.
- `summary_manifest_ref` and `summary_manifest_canonical_sha256` copy the actual
  summary's `source_manifest_ref` and `source_manifest_canonical_sha256`.
- Night/fit/forecast fields, ordered candidate IDs, strict definition and config
  SHA, `fit_lineage`, `training_selection_sha256`, `model_bindings`, `full_counts`
  and `model_summaries` copy the corresponding actual summary fields unchanged.
  They cannot be sourced from caller flags or an outcome manifest.
- `forecast_manifest_ref` and `canonical_joined_rows_sha256` copy the actual
  nested forecast receipt. `domain_ref` is the exact original manifest's resolved
  domain ref already present in actual consumed refs. `horizon` is the exact
  original `{start,end}` object, hash/read-bound to that same manifest. No time
  rewriting, fake domain or new Cartesian rows.
- `candidate_config_source` is an exact10-field object copied from the actual
  nested config receipt: `manifest_ref,manifest_canonical_sha256,config_ref,
  config_sha256,cycle_ref,cycle_canonical_sha256,code_sha256_by_path,
  code_map_sha256,policy_ref,policy_canonical_sha256`. All are the already
  validated raw-file/canonical/current-code identities, with original ref sizes.
  No caller-supplied substitute registry or installed-runtime authentication.
- `fit_lineage` is the nonnull exact existing binding
  `{ref,lineage_sha256,readiness,usable_at}`. Ordered `model_bindings` are exact
  `{candidate_id,artifact}` entries, with each nonnull artifact
  `{ref,model_sha256,readiness,usable_at}`. Preserve the actual physical/canonical
  distinctions and readiness declarations; do not strip them into an auth claim.
- `full_counts` has exactly `cell_count,window_count,shard_count,unit_count,
  area_count`. Each ordered model summary has exactly `candidate_id,model_sha256,
  recipe_sha256,score_semantics,score_stream_sha256,unit_count,area_summaries,
  top10_area_ids`; each sorted area has exactly
  `area_id,unit_count,mean_native_score`. Preserve all areas and exact floats.

This new schema deliberately contains **no** elapsed budget, deadline, incoming/
current read counter, nested execution receipt or old `summary_sha256`. That is
the explicit definition of a new projection, not silent field exclusion from
any old artifact. It preserves actual source/model/code/TRAIN/score content.
Content/source/code changes legitimately change this projection, even if area
rank happens to stay equal. It proves no source issuer, history or trusted freeze.

Separately name `summary_execution_receipt_sha256`: this is the actual unchanged
summary object's existing `summary_sha256`. Verify it against that whole actual
body before projection. The actual summary body is retained unmodified in the
new source result. Do not prerequire an execution SHA made with a different
incoming context. Different actual whole receipts are expected across phases;
the new stable projection and streams/means can remain exactly equal.

New source manifest schema `habu-stage1-summary-source-contract-v1` has exactly
the existing source-v2 fields plus `score_summary_projection_sha256` (16 fields
total); this **replaces the ambiguous pin in initial68**, not an old runtime field:

```text
schema_version, purpose, operational_night, evaluation_as_of,
forecast_manifest_sha256, joined_universe_sha256,
candidate_config_sha256, feature_definition_sha256, score_summary_projection_sha256,
scope_id, captures_id, individuals_id, coverage_id,
source_nodes, readiness, usable_at
```

`purpose` remains `DEVELOPMENT_EVALUATION_ONLY`. Schema is never silently
downgraded to sourcev1/v2. Its stable pin must equal `H(actual new projection)`
before any outcome payload read. The other four identity SHAs keep their actual
forecast/config/definition meanings. `joined_universe_sha256` remains the
existing complete canonical joined-row SHA. This manifest contains no expected
whole execution receipt SHA. Supplying the old whole SHA in the stable field,
an initial68 field name, or an otherwise stale/cross-source projection rejects.
No phase requirement may be solved by clearing/refilling the context.

New pure API, in the existing `full_ledger_stage1.py` module:

```python
evaluate_full_ledger_stage1_summary_v1(
    universe, summary_scores, ledger, *, candidate_config,
    expected_config_sha256, feature_definition_sha256,
    budget_seconds=30, check=None)
```

Universe and ledger keep their existing exact v1 schemas. The new pure score
input has exactly eight fields:

```text
schema_version = habu-stage1-summary-scores-v1,
universe_sha256, candidate_config_sha256, feature_definition_sha256,
score_summary_projection, score_summary_projection_sha256,
summary_execution_receipt_sha256, candidates
```

Each of the exact three ordered candidates has exactly:

```text
candidate_id, score_semantics, model_sha256, recipe_sha256,
score_stream_sha256, scores
```

`score_summary_projection` is the exact new20-field body above, and its SHA
matches `H(body)`. Every overlapping config/definition/night/model/recipe/stream
and complete area mean/count agrees with the actual candidates and universe;
no arbitrary declaration is treated as authentication. The pure function can
check the supplied execution SHA grammar, not authenticate an absent whole
execution receipt. The source entry binds it to the actual body before calling
pure code. `scores` is the complete `{night:{area_id:mean_native_score}}` map. Semantics is
exact `MEAN_NATIVE_UNIT_SPATIAL_SCORE`. Recipe SHA equals the actual full A1
recipe canonical digest for A1 and is null for uniform/A0. Native model SHA,
framed stream SHA, NEW projection SHA, actual whole execution receipt SHA,
original raw file SHA and joined-row SHA
retain distinct names and scopes. None is an issuer signature. There is **no**
`prediction_sha256`, `prepared_receipt_sha256` or fake replacement native field
in the new identity contract.
This first source operation and its new pure projection cover exactly one
operational night, as does one original score summary. Do not claim a multi-night
summary by attaching one night's SHA to several score maps. The pure wrapper
validates every supplied config/score/universe/ledger projection before an NMD
return, following v2's known-contradiction-first rule even if another is null.

The new pure result version is
`habu-full-ledger-stage1-summary-diagnostic-v1`. It keeps the existing numerical
result fields/status/denominator/uncertainty semantics, binds both
`score_summary_projection_sha256` and `summary_execution_receipt_sha256`, and
has `score_identity_kind=G0_SCORE_SUMMARY_PROJECTION_V1`. Its candidate lineage
contains exactly `score_semantics,model_sha256,recipe_sha256,score_stream_sha256`;
config/definition/both summary identities live at the result/header level.
Input digests hash the actual new score input, existing universe/ledger and
config. Since the score input includes the actual execution SHA, its whole
digest and new pure result receipt may legitimately differ across contexts;
only the defined stable projection and numeric content are phase-invariant.
With a genuinely absent score input, pure summary identities are null; known
supplied other projections still validate before NMD.

To keep original whole receipts intact, the source entry returns a NEW explicit
wrapper `habu-stage1-summary-source-result-v1`, rather than editing a nested
summary or silently adding source facts to a sealed pure result. It has exactly
24 fields, including its own self-hash:

```text
schema_version, purpose, status, operational_night, candidate_ids,
candidate_config_sha256, feature_definition_sha256,
score_summary_projection, score_summary_projection_sha256,
summary_execution_receipt, summary_execution_receipt_sha256,
stage1_result, source_receipt, source_summary,
source_authentication, source_consistency, fit_lineage_authentication,
scientific_status, authorities, limitations,
entry_initial_read_bytes, actual_read_bytes, transport_read_bytes, receipt_sha256
```

`purpose` remains DEVELOPMENT_EVALUATION_ONLY; authentication NOT_ATTESTED,
consistency DECLARED_CONSISTENCY_ONLY, fit-lineage authentication
CALLER_DEPENDENCY_REQUIRED and scientific status NOT_VALIDATED. Config/night/IDs
match the actual source. `summary_execution_receipt` retains the actual owned
original whole summary unchanged, including all old counters, nested receipts,
limitations, flags, field order and its unchanged self-hash. An additional copy
must preserve those fields/order and cannot normalize away counters. `stage1_result`
is the unmodified sealed new pure result; neither nested receipt is resealed.
The wrapper's `receipt_sha256` hashes its entire body except only that own field.

For summary NMD before source reads, wrapper status is NEED_MORE_DATA; stable
projection/body, `stage1_result`, `source_receipt` and `source_summary` are null.
The actual NMD summary and its real whole execution SHA remain present; there
are no partial candidates or Stage1 metrics. When summary completes but outcomes
are incomplete, stable/actual identities remain present, nested Stage1 result
is its genuine NMD/empty metrics and source facts remain known. For full declared
evaluation, status is DIAGNOSTIC_ONLY, never scientific/official PASS.

For completed source processing, `source_receipt` has exactly22 fields:

```text
summary_manifest_ref, score_summary_projection_sha256,
summary_execution_receipt_sha256, forecast_manifest_ref, domain_ref,
candidate_config_manifest_ref, candidate_config_sha256, feature_definition_sha256,
training_selection_sha256, model_sha256_by_id, forecast_counts,
summary_actual_read_bytes, stage1_manifest_ref, evaluation_as_of,
readiness, usable_at, projection_sha256, consumed_refs, consumed_sha256,
actual_read_bytes, transport_read_bytes, missing_inputs
```

Refs retain original physical sizes. `forecast_counts` copies exact full counts;
model map is exact configured IDs -> native model SHA. `projection_sha256` is
the existing-shaped universe/scores/ledger body-hash map (null only for absent
projections), distinct from the NEW stable identity field. `source_summary`
contains the existing actual parsed capture_events/individuals counts, with
missing roles/files explicit in sorted unique `missing_inputs`; no claim of a
complete zero ledger follows absence. `summary_actual_read_bytes` copies the
earlier summary snapshot. Final source receipt bytes equal wrapper cumulative
`actual_read_bytes`; `transport_read_bytes=actual_read_bytes-entry_initial_read_bytes`,
including genuine prior charges only in the cumulative figure. There is no
counter assignment/reset, phase-specific hidden allowance or final-read waiver.

All nine summary authority keys remain false in a new pure result `authorities`
object and in the source wrapper, in addition to inherited official/fit/production/source flags. The nine
exact keys are `fit_authorized`, `selection_authorized`, `promotion_authorized`,
`scientific_execution_authorized`, `official_issuance_authorized`,
`production_activation_authorized`, `confirmation_authorized`,
`trusted_campaign_authorized`, `trusted_pre_reveal_authorized`. Source/model/
fit/campaign/pre-reveal/loaded-runtime qualification remains NOT_ATTESTED/
CALLER_DEPENDENCY_REQUIRED; scientific status NOT_VALIDATED.

## Reuse seams; no second full validation or evaluator

Do not feed the new scores to public v1/v2 with forged native fields. Extract
only shared structural score-map checks from `_scores` as necessary, preserving
the old wrapper's exact validation order and output. Add new exact summary-
identity admission. Reuse `_universe`, `_ledger`, `_measure`, `_uncertainty` and
their existing constants/formulas. `_measure` currently constructs native
candidate lineage using three hard-coded field names; use a **fixed private
native/summary identity mode**, default native, to select the truthful lineage
fields. Public v1/v2 signatures and their allowed IDs remain unchanged. No
caller-provided field list, ranking function or arbitrary evaluation callback.

In the source adapter, keep `_prepared*` as the old default admission. A new
private summary admission supplies owned areas/scores and source identities
instead of pretending to return full `forecast/prepared` objects. Factor only
the common source DAG/scope/CSV/coverage/ledger/evaluation/rescan body needed by
both admissions. The fixed new branch chooses its exact manifest/result schema
and identity fields. It reuses existing parsers and observational causality;
there is no second source graph or arbitrary payload/row sink.

## Compact full-scope geometry proof

After the complete summary succeeds, read its **original** forecast manifest,
resolved `domain_id` node's physical ref and config body through the same guarded
reader, using the sizes/hashes already present in summary `consumed_refs`.
Require those exact bindings; do not discover sizes by unchecked stat or accept
a substitute domain from an outcome ledger. Confirm the same original night,
cutoff, horizon and strict-definition identity. Reuse G0's existing horizon and
cell-list checks by a narrow pure extraction if needed, with unchanged G0 callers.
The initial complete G0 pass already established parents, typed OSM CSV equality,
class, coverage and all cell/time shards. Matching these reread bytes to that
pass carries the proof; do not call `_domain` with an empty invented OSM mapping,
skip initial OSM verification, or start a second full G0/ZIP/shard pass.

For every distinct physical domain cell, derive its existing 1km ID and count;
area IDs must exactly equal every model's summary IDs. Check:

- domain cell count, bounded horizon window count and their product equal all
  summary/G0 counts; each area unit count equals its cells times window count;
- full horizon exactly matches the prior scope, with existing UTC-normalized
  aligned600s half-open/07:00-night rules and strict cutoff;
- for scope bbox `[x0,y0,x1,y1]`, every cell satisfies
  `x0<=100*cx` and `100*cx+100<=x1`, likewise y. Checking the midpoint or only
  area intersection is insufficient. Loop cells once, not cells×windows.

No dummy joined rows, fabricated features or giant Cartesian array. Another
possible seam is a private bounded domain witness retained from the completed
G0 pass; this avoids rereads but expands the summary-private return boundary.
Prefer the exact-ref reread above for this slice; any witness alternative needs
independent design review. Never expand the public summary or expose row APIs
merely to avoid a small accounted read.

## Truth denominator, chronology and read order

Preflight all top-level refs before payloads with shared portable component,
protected namespace and ancestor/reparse/containment guards. Before outcome
payloads, finish summary/model/code admission, bind the complete original domain,
then read the Stage1 manifest and every scope ancestor first. Validate the whole
100m-cell scope/horizon even with adversarial source-node ordering. Apply the
new path's full reserved set (`original,incoming,reports,sealed,confirmation`),
C0/DEL and snapshot namespace rules to all refs before their reads. This adds
no permission to old default APIs or any evaluation confirmation namespace.
Final refs retain their purpose-specific existing grammar; pinned typed OSM
archive/part refs are not reclassified as general JSON snapshot refs merely to
reuse a path helper. No new path class or Raw-write permission is introduced.

Reuse current RAW/DERIVED reachability, readiness and four-stage observation
causality to all ancestors. Scope and all ancestors are strictly ex ante cutoff;
actual outcomes/coverage may finalize later but must exist before evaluation.
Use the original forecast-as-of claim for G0 validation, not evaluation-as-of
(a completed evaluation horizon cannot become a new future horizon). Neither
claim authenticates actual issuance time, history or issuer. Normalize pure
conversion overflow locally only; never catch caller cancellation broadly.

Read and validate **whole** supplied capture and individual CSVs. Preserve exact
event↔individual links and quantities: one event with two individuals contributes
two. Select events in the **entire prior declared scope and horizon**, including
places outside forecast cell/area U; never prefilter to predicted areas/Top10.
Coverage must bind exact complete scoped event/individual sets and actual byte
refs. Outside-U individuals remain denominator misses. Missing/UNKNOWN coverage
does not create zero outcomes or Negative labels; no active-search/count exposure
is inferred. A prior scope cannot be shrunk to the forecast bbox after reveal.

For complete source inputs the same `_measure` chooses lexical ties at Top10,
keeps all areas (including zero native scores/unseen TRAIN areas), computes the
full individual numerator/denominator and outside-U misses, pooled counts and
seed0/2,000-draw paired-night bootstrap. One-night diagnostics still lack the
five-night process floor; even meeting it does not establish adequacy or
independence. The actual score is used for ranking, never recalibrated into a
biological probability. Missing scope/coverage/individuals still produce NMD
with empty metrics while checking known supplied source contradictions.

After evaluation, recheck **all** summary/forecast/model/config/code/domain and
evaluation consumed refs with their original sizes under the same context;
check code membership as well. Source effects after prediction are not trusted
because an earlier per-gate rescan happened. Preserve nested summary bytes and
its earlier read-ledger snapshot; expose final cumulative bytes separately and
explain phase deltas. Build new result/source receipt, sealed-output cap and
final deadline check only after final scans. The stable projection is not
rebuilt from changed bytes after outcomes: any rescan/membership/hash drift
rejects; the original execution receipt stays its truthful earlier snapshot.
New pure/source whole hashes bind their actual execution identity/counters and
are not phase-invariant. On failure, public results zero.
No artifact publication is added; future callers need their own reviewed final
reread/publication boundary. Ordinary ownership/hash guards are not an atomic
filesystem snapshot or hostile same-user execution sandbox.

## Bounds and feasibility not yet measured

One context, no refill: at most300s and2GiB cumulative actual bytes, including
all initial reads, code/model/proof reads, domain rereads and final scans. Pure
evaluation receives only remaining time plus this same check; it cannot grant
a fresh parent allowance. Existing per-source limits remain. Do not rerun the
whole summary as an allegedly cheap check or open payloads through unchecked
cycle CLI/hash helpers. Every new controlled loop/copy/hash/seal checks the
same callback; preserve exact caller exception identity.

Keep the stricter intersection of existing limits: domain100,000 cells,
144windows/4,000,000units; summary10,000areas/30,000model-area states and1,097-bit
exact accumulator; Stage1 area-night120,000,128nights,20,000events,
100,000individuals; existing DAG16,384nodes/32,768edges/depth32; combined snapshot
and final new output16MiB,2,000,000nodes/depth12 with bounded strings/keys and
explicit <=64-bit metadata integers. Preflight token/pending-child/encoded-byte
limits **before** extra copies/growth; no bulk Cartesian materialization. Hash
field syntax is included in final sealed-size checks. Counts are typed nonbool
integers; NaN/infinity and arithmetic overflow fail closed.
The combined16MiB/2M-node cap covers the actual summary execution receipt, new
stable projection/score map, config, universe and ledger before extra ownership
copies, and the final wrapper as a whole including both nested receipts and all
hash fields. These are not independent16MiB allowances. Duplicated declarations
do not justify extra capacity; a large valid summary can still capacity-block
when combined with its Stage1 transport.

The native collector remains120,000rows/16MiB and old callers still hit it.
The new bounded area statistic is a separate explicit capability, not a hidden
collector exemption. One diagnostic source call initially handles one night;
multi-night aggregation/protocol confirmation needs a later reviewed interface,
not sequential calls with reset campaign budgets.

The previous OSM-only72-window receipt (1,223,280units,1,412,221,558bytes) did not
score models or Stage1. It is not a resource proof for current code. Models,
final rereads, ledger/CSV work and seals may exhaust the unchanged limits;
return explicit capacity/deadline failure without partial metrics. No 72-window,
memory, scientific-fit or parent experiment is authorized by this document.

## Proposed later owned paths and verification plan

Only after explicit runtime dispatch, proposed exact paths are:

- `src/evaluation/stage1_source_adapter.py`: new fixed admission/source branch;
- `src/evaluation/full_ledger_stage1.py`: new explicit identity admission/result
  plus minimal shared structural checks/lineage mode; no numeric formula change;
- `src/g0_forecast_contract.py`: only if necessary, extract the existing pure
  cell-list checks for same-byte domain scope projection, preserving all defaults;
- new `tests/test_stage1_score_summary_transport.py`, additive affected
  `tests/test_full_ledger_stage1.py`, `tests/test_stage1_source_adapter.py`,
  `tests/test_stage1_configured_source_adapter.py`, `tests/test_stage1_projection_export.py`;
- this spec and new `docs/reviews/g0_score_summary_stage1_transport_20261026.md`.

No summary/model numerical code, learner, `research_pdca_adapter.py`, config
version, Stage1 parent registry, requirements, policy, STATE/cycle, Raw or
ORIGINAL change is proposed. If a shared seam requires another path, stop for
root scope review rather than silently widening it. The current parentv4 and
all old public APIs remain native-collection-only; no parent dispatch claim.

Before extraction, seal genuine native current source and small synthetic full
v1/v2/pure/export/requestv1–v4 artifacts, native/canonical bytes, all digests,
field order, literal REPLAY bytes and real read/open order/ledgers. Execute old
source and new source on the **same runtime, same owned inputs, identical real
incoming context/phase and code-binding declarations**, comparing complete outputs without excluded hash
fields/tolerances/platform allowlists. Historical goldens remain immutable.
Changed actual runtime bytes legitimately change current source-map bindings;
verify current actual raw bytes/closure separately, never pin them to old SHAs.

Required actual RED -> GREEN controls before independent review:

| Control | Decisive expectation |
| --- | --- |
| Two synthetic calls on identical physical inputs/code: genuine fresh context0 versus a real guarded `G0ArtifactReader.read` of a bounded fixture ref before entry (incoming bytes I>0), with one source manifest pinning the stable identity | Independent reconstruction of all20 projection fields and H(body) equals in both; exact means/counts/streams and all Stage1 numeric metrics match. Original whole summary SHA and new execution-bound result hashes differ naturally. Each original whole hash independently verifies over every old field; entry counters are0/I, final counters/context and retained prior charges match; no manual counter mutation/reset, new ledger or second summary pass within either call. |
| Put a fresh-context whole execution SHA into the stable manifest pin, use the initial68 field name, or retain a stable pin after fully rebound valid source/model/code/stream content changes | Reject before ANY outcome payload opens, for both context0 and precharged contextI. Whole execution SHA is never an expected invariant; changed phase alone is accepted when stable content matches. Changed stream/model/source content is never accepted merely because ranks/means coincide. |
| Synthetic full-seven complete three models, both valid optional orders, unequal cp/tp shards/area counts, zero/unseen scores, lexical ties and <10 areas | Full native small oracle `statistics.mean` equals every summary mean/count; existing Stage1 numerical per-night/pooled/bootstrap/denominator fields exactly equal. New identity/result hashes are independently computed, not required to equal old native hashes. |
| One event/two individuals, complete zero scope, unknown scope, outside-U actual capture in the prior bbox | Exact denominator/link rules unchanged; outside-U remains FN; no fabricated zero/partial metric. |
| Framed SHA injected into native prediction field; stale/cross-config/recipe/model/TRAIN/summary/joined identities; reordered/missing areas; wrong per-area counts; finite-but-invalid physical values | New exact identity checks reject; old v1/v2 still reject the new schema; known contradiction cannot be hidden by another missing input. |
| Missing seven raw features/model/lineage; B1 config; last-shard or final model/code mutation | Whole-set block after required forecast validation; outcome-open observer zero; no uniform/A0-only result, fallback, fake rows or refit. |
| Midpoint inside bbox but cell edge outside; omitted domain cell; mismatched horizon/timezone spelling/alignment; 07:00/year-edge overflow | Whole-cell and exact normalized-time proof, local malformed ValueError; no global date gate or timestamp rewrite. |
| Missing/UNKNOWN roots alongside malformed supplied CSV, duplicate event/individual, wrong count/source link, pre-event RAW ancestor/coverage readiness | Reused full source checks still reject contradictions; valid incompleteness gives NMD/empty metrics, no denominator invented. |
| Parent callback raises same FileNotFoundError/ValueError/OverflowError/TimeoutError/KeyboardInterrupt during reader/proof/pure conversion/hash/final seal | Preserve exact object identity; distinguish static missing refs from caller exceptions. No broad wrapper catch around caller code. |
| Prior charges/remaining+1 read; domain/output/copy/bit/node caps; final seal cap at length-1/equality; last-source change/late expiry | Same absolute ledger/deadline, original ref sizes, no partial output, no fresh allowance; complete old defaults/read ledgers unchanged. |

Use synthetic fixtures only. Independent review must verify full oracles and
hostile source/identity/denominator probes on exact source, then coordinator
integration/new freeze/exact and fresh Ubuntu CI. Native Windows results cannot
certify POSIX behavior. Larger current-code latency/actual OS memory measurements
need a separate authorized rehearsal after review; no success estimate here.

## Risk and authority boundary

This is a proposed MEDIUM additive transport only if old schemas/algorithms/
limits/goldens and authority restrictions remain intact and it stays standalone.
Its new version honestly records a different score identity, with the same
Stage1 statistic. It does not satisfy existing **trusted native prediction**
admission: that contract requires unavailable whole arrays/native SHA and
issuer/pre-reveal evidence. An existing consumer demanding that contract must
return IMPLEMENTATION_BLOCKED; no hash substitution can make it compatible.

Replacing canonical issuance/native predictions/evaluation definitions, changing
the denominator/ranking/KPI, relaxing capacities, granting source/trusted issuer/
confirmation authority or integrating a new canonical parent architecture is
outside this slice and crosses the separate HIGH/owner gate. A later parent
request-version design is explicitly required even if this diagnostic transport
passes. B1 native rank transport, A2, source-qualified seven predictors/TRAIN,
independent denominator qualification, campaign/reveal locks and formal future-
blocked science remain incomplete. OSM full-universe validation, a score summary
or this proposed diagnostic must never be called full-night model/Stage1/parent
or scientific completion.
