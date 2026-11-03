# Stage1 score-summary transport v2 contract

This is the standalone engineering contract approved in private R2 (23,841 bytes, SHA256 `0c6be31edc7887a5042d1960fb7031dda25a823ee5fbbc2b2b44c20bfee90bd8`) and independently reviewed before implementation. Root dispatched implementation after actual PR142 exact and fresh acceptance on main950. Historical R2 preparation and the pre-edit104/fixture107 captures retain their original times and scopes. The added module produces prospective native105 membership; Root owns its later freeze, exact/fresh CI and integration. This document confers no scientific, source-issuer, parent, registry or production authority. Risk MEDIUM.

## 1. Public seam and closed source route

NEW module `src/evaluation/stage1_score_summary_transport_v2.py` exports only:

```python
evaluate_stage1_summary_sources_v2(
    root, summary_manifest_ref, stage1_manifest_ref,
    operational_night, forecast_as_of, *,
    expected_feature_definition_sha256,
    expected_candidate_config_sha256, context)
```

Both refs are mandatory exact physical `{path,sha256,size_bytes}` objects, copied before the first caller check. Supplied-but-missing top-level files reject. No nullable manifest, cached execution, expected execution SHA, caller scores/callback/publication path or protocol-loader argument. `forecast_as_of` is aware caller input used unchanged by G0, never evaluation_as_of. Candidates are exactly ordered `['uniform','HB-A1','HB-A2']`; cfg tag is `habu-research-candidate-config-v3`. Reuse unchanged preparation-v3 ownership/digest/config admission for full-seven A1 and fixed A2 recipe. No fit/predict/preparer/backend call or native preparation array is permitted.

Existing adapter `_evaluate` gains only `_summary_v2=None` and an early fixed new route after existing context/export-type checks, before its original first callback/body. With None, the original body statements remain AST-identical apart from this additive route/signature. With the slot present require forecast/prepared/configured/_summary allNone, literal exportFalse, exact internally owned readonly class, complete root/context/construction binding, READY_STAGE1 phase and sealed child/P2 admission. Reject before reader construction or payload. Use static module/class dispatch, never an overridable instance method or caller-selected callable/type. Producer NMD never enters this route.

The new module owns its versioned source-DAG/scope orchestration, reusing existing `_captures`, `_individuals`/CSV helpers, G0 readiness/path primitives and unchanged pure `_universe`, `_ledger`, `_measure(...,_summary_identity=True)`, `_uncertainty`, ownership/hash/limit primitives. One selected route performs one graph/evaluation; never run old and new pipelines sequentially. Numerical matching/ranking/paired-night/bootstrap definitions are not rewritten. A private compact-score admission uses these helpers with the owned guard and no fresh public30s allowance. Old native/source/export/summary-v1 APIs, candidate globals, request-v4 parent and registry remain unchanged. No dynamic monkeypatch/exec or broad legacy refactor.

## 2. Exact versioned schemas

Canonical H(x) hashes the ENTIRE exact object as sorted-key compact UTF-8 JSON, Unicode retained and nonfinite rejected. P2 has no self-hash. Exact20 fields:

```text
schema_version,purpose,summary_manifest_ref,summary_manifest_canonical_sha256,
operational_night,fit_cutoff,forecast_cutoff,forecast_manifest_ref,
canonical_joined_rows_sha256,domain_ref,horizon,candidate_ids,
candidate_config_source,candidate_config_sha256,feature_definition_sha256,
fit_lineage,training_selection_sha256,model_bindings,full_counts,model_summaries
```

P2 tag `habu-g0-score-summary-projection-v2`, purpose DEVELOPMENT_EVALUATION_ONLY. Copy corresponding fields unchanged from the actual successful `habu-g0-full-universe-score-summary-v2` execution, whose source tag is `habu-g0-full-universe-score-source-v2`. Forecast ref/joined SHA come from its original forecast receipt. Domain ref and exact `{start,end}` horizon come from its already-consumed original forecast manifest/domain. Every ref retains physical size/hash/path. Nonnull lineage/model bindings retain readiness/usable_at and physical/canonical distinctions. Require actual unchanged v2 producer and its V2 H/R/T stream construction, not arbitrary supplied scores.

Stable config/source10 is copied from load2 receipt:

```text
manifest_ref,manifest_canonical_sha256,config_ref,config_sha256,cycle_ref,
cycle_canonical_sha256,code_sha256_by_path,code_map_sha256,
policy_ref,policy_canonical_sha256
```

Compare all10 typed fields with load1 exactly. Verify full code-map digest/membership and fixed G0 policy physical ref/canonical POLICY_DIGEST. Per-ID recipe map is uniform:null, HB-A1:H(config.hba1_recipe), HB-A2:H(config.hba2_recipe). Both expected config and feature SHA match EVERY overlapping model/source/summary/manifest/header. All3 ordered model summaries retain exact8 fields, area rows exact3. Validate identical complete sorted area sets and per-area counts across candidates, typed positive counts/windows/full totals, finite means in[0,1], uniform constant means, exact lexical Top10 and native model/recipe/stream identities. Equal aggregate totals do not excuse cross-candidate area-count reallocation.

NEW source tag `habu-stage1-summary-source-contract-v2`, exact16 fields:

```text
schema_version,purpose,operational_night,evaluation_as_of,
forecast_manifest_sha256,joined_universe_sha256,candidate_config_sha256,
feature_definition_sha256,score_summary_projection_sha256,
scope_id,captures_id,individuals_id,coverage_id,source_nodes,readiness,usable_at
```

Purpose DEVELOPMENT_EVALUATION_ONLY. Stable pin equals H(P2) before outcomes. Other hashes retain actual raw forecast/full joined/config/definition meanings. No expected whole execution SHA. Source-node/role/ref/readiness, RAW/DERIVED causality, scope and coverage remain current exact v1 shapes.

Compact scores tag `habu-stage1-summary-scores-v2`, exact8 fields:

```text
schema_version,universe_sha256,candidate_config_sha256,feature_definition_sha256,
score_summary_projection,score_summary_projection_sha256,
summary_execution_receipt_sha256,candidates
```

Each candidate has6: candidate_id,score_semantics,model_sha256,recipe_sha256,score_stream_sha256,scores. Semantics MEAN_NATIVE_UNIT_SPATIAL_SCORE; scores is exact `{night:{sorted_area:mean_native_score}}`. Universe/ledger keep v1 schemas. `summary_execution_receipt_sha256` is actual original whole summary's summary_sha256, verified over the complete body before P2. It is neither H(P2), native predictions_sha256, a signature nor context-invariant identity. No existing hashed field is removed/redefined. Whole result/input digests can legitimately differ with genuine nested/cumulative counters.

Private pure result tag `habu-full-ledger-stage1-summary-diagnostic-v2`, score_identity_kind G0_SCORE_SUMMARY_PROJECTION_V2. Keep current status-dependent pure summary/numeric fields exactly as unchanged _measure/current base produce them, changing only versioned identity/config/candidate header values. Retain P2 SHA/actual execution SHA and per-candidate semantics/model/recipe/stream lineage. Validate every supplied projection before NMD, including known night/horizon intersections with a supplied ledger when Universe is absent; never invent bbox/completeness.

NEW wrapper `habu-stage1-summary-source-result-v2`, exact27 fields (old24 plus final3):

```text
schema_version,purpose,status,operational_night,candidate_ids,
candidate_config_sha256,feature_definition_sha256,
score_summary_projection,score_summary_projection_sha256,
summary_execution_receipt,summary_execution_receipt_sha256,
stage1_result,source_receipt,source_summary,
source_authentication,source_consistency,fit_lineage_authentication,
scientific_status,authorities,limitations,
entry_initial_read_bytes,actual_read_bytes,transport_read_bytes,receipt_sha256,
source_admission_receipt,source_admission_receipt_sha256,phase_read_ledger
```

`source_admission_receipt` is the ENTIRE original sealed load1 Source2 receipt and its receipt_sha256. Execution retains ENTIRE original load2 receipt. Preserve native child order/body/hash/counters/limitations/false flags; no pop/update/reseal. Pure child is also sealed/unchanged. Purpose DEVELOPMENT_EVALUATION_ONLY, source NOT_ATTESTED, consistency DECLARED_CONSISTENCY_ONLY, fit-lineage CALLER_DEPENDENCY_REQUIRED, science NOT_VALIDATED, all9 authoritiesfalse. Outer receipt hashes every field except only its own hash. Bounded copies preserve child native bodies/key order/hash.

Completed source_receipt remains exact22:
summary_manifest_ref,score_summary_projection_sha256,summary_execution_receipt_sha256,
forecast_manifest_ref,domain_ref,candidate_config_manifest_ref,candidate_config_sha256,
feature_definition_sha256,training_selection_sha256,model_sha256_by_id,forecast_counts,
summary_actual_read_bytes,stage1_manifest_ref,evaluation_as_of,readiness,usable_at,
projection_sha256,consumed_refs,consumed_sha256,actual_read_bytes,transport_read_bytes,missing_inputs.
Source_summary is exact parsed capture_events/individuals counts. First-admission/phase facts exist only in their named outer fields, not rewritten child counters.

## 3. Exact physical stages

A. Own top refs/hash syntax/aware time, record B0 BEFORE the first actual context.check, then validate/check the actual context. No check or new I/O precedes B0. Existing context max_bytes exact int>0<=2GiB, bytes_read exact int>=0<max and original remaining>0<=300. Never replace context.check/clock/deadline/ledger, restrict/refill/reset or create another product context. Strong refs reject unsafe portable components, reserved ORIGINAL/incoming/reports/sealed/confirmation casefold segments, C0/DEL, alias/reparse/containment; typed OSM33-part namespace stays exact. All reads use genuine guarded G0 reader; no direct byte/hash shortcuts, fabricated stat sizes or memory overlays.

B. Before load1 physically read ONLY summary profile<=256KiB, Source2 profile<=256KiB and immutable cycle header<=4MiB. Parse/bound all known summary envelope/ref/type/time/definition/ordered-ID contradictions. Purely validate downstream ref syntax, but do not open/stat downstream forecast/model/TRAIN payloads. Retain forecast_as_of and current fit/night/cutoff rules. From Source2 metadata close exact profile/config/cycle/policy bindings, code_manifest/code_availability arrays and all known ref size/path/readiness declarations. Match complete<=256 code/availability paths, exact versions, fixed policy path, positive bounded sizes. Strong transport local_path preflight applies to these known SOURCE-closure refs before delegated reads. Config<=64KiB/code-cycle-policy<=4MiB bodies are NOT opened in this preliminary gate. Genuine Source2 owns actual config/code/policy/recipe/readiness admission. Record B1. Do not call old whole _summary_preflight, which opens forecast metadata too early.

C. Call actual load_research_candidate_config_v2 ONCE using owned source ref, same night/profile fit/profile cutoff/definition/context. Record B2 immediately on return; verify original complete receipt self-hash/schema/config SHA. Source2's valid-late CandidateConfigSourceBlocked propagates after its own full closure/rescan. At this barrier downstream forecast/model/TRAIN/evaluation payload opens0; unread poison is not claimed validated. Already-known unsafe metadata fails in B rather than being misclassified valid-late. Preliminary header bytes are extra global charges outside the loader's validation phase.

D. Only after load1 success, stronger-preflight known model/lineage/forecast refs, read original forecast metadata<=4MiB, and preflight every nested node/feature/provenance/code/policy ref BEFORE its payload. Retain exact OSM/archive/part/typed-road grammar. Validate already-read known metadata; unchanged producer owns complete G0/model semantics. Do not open model/TRAIN bodies here. Reject reserved/alias/junction targets before payloads; record B3.

E. Call unchanged score_g0_forecast_summary_v2 ONCE under SAME context. It performs real load2/native model checks/full G0 stream and rescans. No fitter/preparer/backend or second full G0. Record B4 on return; verify original whole summary and load2 receipt self-hashes/version/status. Stable10 and whole config identity must match load1; drift rejects before evaluation. Both whole child receipts survive even though counters/whole hashes differ. Do not prerequire equality of their execution SHA. Summary ledger drift at B4 rejects instead of changing its counter.

F. For complete summary reread only original already-consumed forecast/resolved domain/config with exact original sizes. Bind refs against producer consumed_refs, match config to load1, build/validate P2 and full cell/area counts; record B5. Loop distinct cells, not cell-times-window arrays. Each area count equals its physical cells times windows; all candidates/full rectangular totals agree. No invented typed OSM map, substitute outcome domain or outcome-informed P2. Producer NMD skips this stage/evaluation: P2/pure child/source_receipt/source_summary null, model_summaries empty; full load1/load2/NMD execution/phase evidence remain. B5=B4, B6=B5 on that path.

G. Complete P2 enters the closed adapter route. Read exact new Stage1 manifest; preflight every source ref/ancestor first. Match forecast/joined/config/definition/P2 and evaluation_as_of>cutoff. Read prior scope plus all strictly ex-ante scope ancestors before outcomes regardless node order. Prove night/cutoff/horizon and every entire100m cell: x0<=100cx and100cx+100<=x1, likewise y, not midpoint/area overlap. Then read/validate EVERY supplied observational CSV/coverage/support byte. Reuse complete link/quantity/RAW-DERIVED/observed-readiness rules. Select whole prior scope/horizon, including outside scored U; no shrink/fallback. Outside-U count2 is FN2. Invalid supplied data rejects before NMD. Coverage must match known P2 night/horizon even if scope missing; this invents no bbox and does not force unselected multi-night raw CSV records into forecast horizon. Record B6 after evaluation/pure child seal.

H. Final union includes all load1/producer/load2/forecast/model/code plus new domain/config/evaluation reader refs. Conflicting path/hash/original-size bindings reject before reads. Same context: exact code membership, reread each unique union ref with original hash/size parseFalse, membership again. These additional global reads are NOT retroactively added to either sealed Source2 phase. Record B7; construct only NEW source/outer facts, own/hash/cap/check whole outer output, then require actual final ledger still B7 and record B8=B7. Any late drift/expiry yields no partial success/external rows. Never rebuild P2 from changed bytes or reseal a child. No publication is added; later callers need their own reviewed final-publication boundary.

## 4. Phase accounting, ownership and caps

Each real Source2 load retains16MiB own first-read/rescan,256KiB profile/64KiB config/4MiB code-cycle-policy/256refs. Both and every preliminary/reread/final byte are global cumulative<=2GiB under original remaining<=300s. No pooling/refill or “one call” description. Forecast/domain small JSON<=4MiB; combined owned16MiB is an ownership bound, not a free read allowance.

Phase ledger exact13 typed nonbool integer fields:

```text
before_pre_admission_metadata,after_pre_admission_metadata,after_source2_load1,
after_post_admission_metadata,after_summary,after_compact_projection,
after_stage1,after_final_rescans,final_read_bytes,
source2_load1_validation_read_bytes,source2_load2_entry_read_bytes,
source2_load2_sealed_read_bytes,source2_load2_validation_read_bytes
```

First9 are B0..B8 monotone. Outer entry_initial=B0, actual=B8, transport=B8-B0. Disjoint adjacent differences sum B8-B0. Load2 is nested within B3..B4; never add it twice. Load1 actual_read_bytes=B2 and validation=B2-B1. Load2 entry=its actual-validation, sealed=its actual, validation=its own validation; B3<=entry<=sealed<=B4. Summary actual=B4. Derive summary_entry=original_child.actual_read_bytes-original_child.summary_read_bytes and require B3<=summary_entry<=B4; retain original child summary_read_bytes unchanged. Phase E whole actual charge is B4-B3, which can include charged producer-entry checks before summary_entry. The95 producer _context calls actual context.check before capturing its initial bytes, so a legitimate1B guarded read there is counted by transport without falsely adding it to the sealed child. Prior charges stay cumulative, not deltas. Failure retains actual caller charges, no invented successful receipt.

Keep100,000cells/144windows/4Munits,10,000areas/30,000candidate-area states; no prediction arrays, full120k preparation/chunk concatenation/arbitrary row consumer. Stage1 retains120k area-night/128nights/20k events/100k individuals, DAG16,384nodes/32,768edges/depth32. This interface is one night, not multi-night evidence or the five-night science floor.

Bound combined ownership BEFORE extra copies/growth and WHOLE fully sealed pure/wrapper output16MiB/2Mnodes/depth12, including retained cells/areas, source profile, reader reference/size records and the entire first admission. During compact construction include the original forecast/domain/config records before creating another owned projection/copy. Preserve the distinction between this nominal ownership contract and RSS. Keep existing bounded keys/strings/nonbool<=64-bit metadata. Count BOTH complete Source2 receipts, execution/nested forecast receipt, P2/config/domain/Universe/scores/ledger, duplicates, pure child and all hashes/phase/encoding overhead. Not independent allowances. An otherwise valid large summary may capacity-block transport. No clipping/field removal/cap raise/hard-preemption/RSS/full-night performance claim.

## 5. FIRST-origin and non-injectable state

Use internally constructed slotted/readonly state with private construction sentinel, same root/context identity and fixed methods. Ordinary constructor calls always reject, including a caller passing the module sentinel. Only the public invocation initializes the state inline; no exported factory accepts caller-selected state. Exact reader instance attribute membership is checked before the route. This is ordinary API admission, not loaded-process/object-level tampering confinement. No __dict__, stored external callable, writable guard/reader/result factory. Exact class alone is insufficient: static admission requires all slots, token/binding, genuine internally built guarded-reader exact state/no instance overrides, validated children/P2 and READY_STAGE1. Reject arbitrary/subclass/constructor misuse/__new__ incomplete/preconstructed writable/foreign state/conflicting modes/instance hooks before Reader or payload. Class/global/object.__setattr__ loaded-process tampering is not authenticated or sandboxed.

Fixed local guard first raises stored FIRST error if notNone, otherwise calls actual context.check directly, catches BaseException ONLY to store the FIRST object by identity and bare-raise. No truthiness/equality/clone/wrapper heuristics. Every shared CSV/pure/hash/copy/rescan/seal loop uses it; after each helper check stored first even if the helper swallowed it. Public outer failure first restores that SAME object, otherwise bare-raises. Internal capacity normalization is confined to known new pure sites and first restores FIRST; reader/Source2/producer errors stay outside those catches.

_csv catches StopIteration/UnicodeError/csv.Error and generator StopIteration may be transformed. Passing this guard records original parent before normalization; restore it without changing old helper/catches/context.check. Delegated Source2/producer retain existing tested boundaries; a new real origin loss there requires a separately scoped dependency repair, not class/message/cause equivalence or silent old edits.

## 6. Dispositions and trust

Source2 valid-late halts at C; G0 late retains ordinary ValueError/current early boundary; summary-owned late retains admitted-full-row checks before its own ScoreSummarySourceBlocked. Known contradictions only win within stages actually admitted/read. Producer NMD opens no evaluation file or partial metrics. Complete summary with missing/UNKNOWN/INCOMPLETE scope/coverage/individuals returns genuine NMD/empty per_night/pooled/paired_uncertainty while checking supplied facts. Provided missing top manifests error. Static missing source role files are explicit missing_inputs; actual caller FileNotFoundError is never converted to absence. DIAGNOSTIC_ONLY is not scientific/official PASS.

Fixed policy canonical POLICY_DIGEST/physical ref and target/source manifest/P2/config/feature/scope/horizon are exact DECLARED commitments. Locked_protocol_manifest remains separate and requires native predictions_sha256. It is neither called nor widened; no expected_protocol input is invented, and stream/P2/execution hash cannot impersonate native predictions. No issuer/history/prereveal/complete-outcome/SEARCH/biological/calibration/accuracy/T2 road-point trust, selection/registry/Champion/parent or production authority. All9false, NOT_VALIDATED, real qualified TRAIN/fit/parent0.

## 7. Seven decisive RED groups

1. Two real loads and one producer/G0 pass; true0 versus prior charges gives equal stable10/P2/streams/means but legitimate whole receipt/counter differences. Include a genuine1B guarded read during the producer-entry _context.check BEFORE its initial-byte capture: B3<summary_entry, child summary_read_bytes stays unchanged, phase E B4-B3 includes that1B, and the call must not be rejected by the old false equality. Assert all B/subphase relations, immutable full native children/key order, no overlay/context mutation; inter-load source/code/policy/config drift fails before outcomes.
2. Source2 valid-late plus safe-ref downstream poison gives own closure/rescan and downstream opens0. Known unsafe Source2 refs fail before payload. Admitted nested ORIGINAL/case/./backslash/trailing/ADS/DOS/junction targets fail before protected payloads. G0 late stays ValueError; summary late+last-row poison fails contradiction. Observe actual opens at both orderings.
3. Wrong version/IDs/order/fourth/recipe/model/TRAIN/config/feature/code/requirements/stream/native substitution or rehashed count reallocation rejects. Whole producer NMD leaks no subset/evaluation read. Missing Universe with known ledger/coverage wrong time/night/horizon and supplied malformed final CSV/ID/count rejects without bbox invention.
4. Physical whole-cell/domain/horizon/count proof; edge exclusion/scope shrink rejects before outcomes. Full denominator/outside-U count2 FN2; complete empty0 requires genuine explicit coverage, not silence. Tiny identical declarations produce unchanged old metric/tie/seed0 bootstrap behavior; no accuracy claim.
5. Arbitrary/subclass/writable/preconstructed/__new__/method/check/reader injection rejects before Reader/external rows0. SAME original first/later/final capacity/TypeError/Unicode/csv/StopIteration/Overflow/BaseException/falsey/equality objects through all helpers and seals; sticky FIRST survives later errors/internal normalized wrappers. Internal classifications remain correct.
6. Actual per-phase/global prior exhaustion/shared300 expiry, state/fully sealed own-hash overhead/combined complexity limits, later byte/original-size or membership insertion/deletion at final scan. No dropped fields/partial rows/results/cap reset. Genuine platform guards; no OS facade or giant4M fixture required.
7. Before edits seal actual accepted-main old Stage1/source/export/summary/pure/default program and full fixture/context/code declarations. Compare complete native+canonical result/key order/hash/ownership and read/open/check/callback/actually executed physical REPLAY with genuine archived old programs under SAME declarations. Preserve3270/old33/post3ad/95 reuse scopes, no fresh parent replay claim. New bridge uses genuine already-frozen synthetic models/receipts, fit/backend0; current104 and future new-code exact/fresh/main gates stay distinct.

Authored scope: NEW module, existing adapter only additive closed route, new focused test/spec/author files. No numerical helper, old loader/G0/model, requirements/parent/registry/Raw/policy/STATE/cycle/workflow edits. Root implementation dispatch is separate from scientific/production authorization; later integration still requires independent source review and exact/fresh CI.


## Implementation evidence clarifications

- Stage1 top/node/coverage observational refs retain the old `stage1_source_adapter.input_ref` namespace before payload reads. The broader config/model/runtime namespaces are only for the Source2/summary closure.
- After load1, exact existing G0 manifest/node/feature/bound-ref fields are validated before indexed metadata access. Valid-late Source2 still stops before any forecast payload read. Forecast/domain metadata remain at most4MiB. No broad catch converts caller errors into malformed metadata.
- Capacity/runtime normalization is confined to named new pure sites. Actual reader/account/Source2/producer errors propagate with their original object. The local guard restores the FIRST recorded parent error before any internal normalization.
- The final actual check runs before the final ledger equality test. A real charged read in that final check invalidates the output; sealed child ledgers are not repaired or resealed.
