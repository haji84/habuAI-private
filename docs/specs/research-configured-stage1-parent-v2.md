# Configured Stage1 source-v2 parent dispatch: request v4

Status: IMPLEMENTED_PENDING_EXACT_SOURCE_REVIEW_AND_UBUNTU_CI. Explicit request
v4 connects the existing configured source-v2 diagnostic. The independently
approved design below remains its contract. No real-data fit, deployed controller,
scientific result or new authority is established by this implementation.

## Purpose and existing contracts

The explicit development request may connect the reviewed configured Stage1
source-v2 API to the existing parent. Current request v3 prepares configured
three-slot sets, but permits source-v1 Stage1 only for the exact ordered legacy
triplet. Its other requested sets remain `IMPLEMENTATION_BLOCKED`. The separate
source-v2 API already supports all six legal configured triplets, full individual
denominators, outside-universe misses and the existing paired-night bootstrap.

The new request is an explicit opt-in. Reuse the current config source loader,
G0 TRAIN selector, strict full forecast loader, pure configured preparer,
`evaluate_stage1_sources_v2` and immutable REPLAY publisher. Do not introduce a
second evaluator, numerical learner, source registry, denominator policy or
model-selection algorithm.

This is the software capability `CONFIGURED_STAGE1_PARENT_DISPATCH_V2` /
`REUSE_SOURCE_STAGE1_V2` described by the bounded development-request plan. That
plan's proposal is not job admission, a root reservation, an authenticated source
fact or execution authority. This slice does not implement the Task7 controller,
durable root budget, lease, issue dispatch or backend continuation.

## Approaches and chosen proposal

1. Widen request v3 implicitly. This would change its explicit nonlegacy block,
   stored REPLAY schema and legacy read counts. It is excluded by the approved
   compatibility boundary.
2. Add request v4 and reuse the existing configured source-v2 path. This preserves
   the old version branches and adds only one reviewed parent connection. This is
   the proposed approach, subject to the independent design gate.

An additional v4-only native-admission call before Stage1 manifest preflight
preserves the source adapter's strongest ordering: all model/prediction bindings
are checked before even the evaluation manifest is opened. It reuses the existing
`stage1_source_adapter._configured_prepared` helper, discards its projection and
then calls the public source-v2 evaluator normally. There is no duplicated model
validator or payload reader. The repeated bounded copy/validation adds CPU only
in v4 and receives the same parent check; it grants no fresh budget. If this
private seam is rejected at design review, implementation must return for a
contract decision rather than silently weaken admission ordering or edit the
source adapter outside ownership.

That private helper does not provide the public API's exception normalization.
Wrap only the v4 admission call with the public-v2 equivalent named runtime
translations: `pure.Stage1CapacityBlocked`, `models.ResearchCapacityBlocked`,
`models.ResearchInputCapacity` and `models._hba1.HBA1CapacityBlocked` become
`pi.InputCapacityError`, retaining the original message and cause;
`pure.Stage1BudgetBlocked` becomes `TimeoutError`. Equivalently, v4 may classify
those exact exceptions directly as RUNTIME_BLOCKED. Ordinary `TimeoutError` and
`pi.InputCapacityError` from the shared check remain unwrapped, and other caller
check exceptions must retain their identity/type through the seam. Do not catch
broad `ValueError`/`Exception` as capacity, suppress a caller guard, reset a budget
or convert runtime exhaustion to DATA_BLOCKED or malformed evidence. Old v1-v3
exception handling and whole outputs remain unchanged.

## Exact request contract

Use `config/research-model-request.json` with
`schema_version: habu-research-model-request-v4`. Its exact twelve fields are:

| Field | Contract |
| --- | --- |
| `schema_version` | Exact request-v4 version above |
| `mode` | `DEVELOPMENT_ONLY` |
| `operational_night` | Canonical operational night, including 07:00 JST boundary |
| `fit_cutoff` | Existing aware common TRAIN fit cutoff |
| `forecast_as_of` | Existing aware forecast materialization boundary |
| `forecast_cutoff` | Existing strict forecast cutoff; fit strictly earlier |
| `feature_definition_sha256` | Exact strict complete feature-definition digest |
| `training_manifest` | Existing strict G0 TRAIN byte reference |
| `forecast_manifest` | Existing strict complete G0 forecast byte reference |
| `exposed_nights` | Existing unique canonical night list |
| `candidate_config_manifest` | Required source-bound config profile byte reference |
| `stage1_manifest` | Null, or a strict Stage1 source-v2 byte reference |

A byte reference has exactly `{path, sha256, size_bytes}` and hashes physical
bytes. No missing/default version, additional field, inline config, caller-supplied
prepared receipt or implicit current-cycle pointer is accepted. Retain each
existing reference validator, request cap, duplicate-JSON/nonfinite rejection,
night validation and strict cutoff/definition checks. The public parent function
signature remains unchanged; version selection is only in the byte-bound request.

The configured IDs are exactly one of these ordered triplets:

| Slot 1 | Slot 2 | Slot 3 |
| --- | --- | --- |
| uniform | HB-A0 | HB-B1 |
| uniform | HB-B1 | HB-A0 |
| uniform | HB-A0 | HB-A1 |
| uniform | HB-A1 | HB-A0 |
| uniform | HB-B1 | HB-A1 |
| uniform | HB-A1 | HB-B1 |

Use the existing exact config-v2 validator, full-seven-feature HB-A1 recipe and
source/code closure. Do not sort, substitute or admit HB-A2, an ablation or a
fourth candidate. The v4 Stage1 manifest must have source-contract-v2's exact
fifteen fields, including the matching config and feature-definition digests.
Source-contract-v1 cannot downgrade this path, including the legacy triplet.

## Dispatch sequence and read order

1. Guard and read the request with the existing shared reader. Check the request
   night, strict definitions and fit/forecast boundaries.
2. Load the source-bound config using the existing parent context and exact
   requested night/cutoffs/definition digest. Preserve its owned config and source
   receipt, original byte sizes, code membership and declared-readiness rules.
3. Before either TRAIN/forecast loader, preflight their manifests using the full
   existing config-loader `RESERVED` set: case-insensitive path components
   `sealed`, `confirmation`, `original`, `incoming`, `reports`. Reject nested refs
   before their target opens. Do not widen the snapshot input namespace.
4. Run the existing TRAIN and forecast gates under the same context. Compare
   both actual strict definition digests to the request/config. Prepare one whole
   configured set with the existing pure-v2 call, complete forecast universe,
   request cutoff and actual canonical joined-row digest. Recheck config bytes
   and current code membership after preparation.
5. An insufficient complete prepared set takes the existing DATA_BLOCKED path:
   candidates, Stage1 and REPLAY are absent. Null Stage1 performs no evaluation
   manifest or outcome read and preserves a complete prepared set in one REPLAY.
6. For non-null Stage1 and a complete set, run the existing configured native
   admission helper before opening its manifest. It must reject rehashed future
   or mismatching earlier native cutoffs, native held-out mismatch, unsupported
   model envelopes and changed recipe/probability/lineage claims before evaluation
   I/O. This includes uniform, HB-A0 and HB-B1 as well as HB-A1. Apply only the
   v4-specific named runtime exception translation described above; any cap or
   deadline failure releases no partial artifacts.
7. Preflight the Stage1 manifest with the same full `RESERVED` set before any
   referenced evaluation payload. A supplied Stage1-v1 payload is rejected here
   at the source-manifest gate, after native preparation/admission and before
   evaluation payload opens. Its version cannot be known before reading its
   manifest, so this is not a fit-before-input-schema rejection guarantee. No v4
   downgrade or fallback to the old source API is permitted. Call exactly:

   ```python
   evaluate_stage1_sources_v2(
       root, request['stage1_manifest'], forecast, prepared,
       candidate_config=config_source['config'],
       expected_config_sha256=config_source['receipt']['config_sha256'],
       feature_definition_sha256=request['feature_definition_sha256'],
       context=context,
   )
   ```

   Its existing combined config/forecast/prepared 16MiB, node/depth/row caps,
   native validators, strict source graph, four-stage RAW lineage causality,
   source scope/CSV/individual/coverage checks and source rescan remain intact.
   All three native hashes exist before evaluation payloads. HB-B1 retains its
   native rank-score and native recipe; the source-v2 projection alone uses null
   recipe identity for non-A1 candidates. Mean aggregation and pure-v2 metrics
   remain those of the reviewed source/evaluator, including outside-universe FN.
8. Merge TRAIN, forecast, config and Stage1 consumed digests. Reject conflicting
   bindings. Recheck all consumed inputs through the shared reader and all config
   original refs/code membership after evaluation and again before publication.
   A shared source cannot change between gates without failure. These sequential
   checks do not claim an atomic hostile-filesystem snapshot.
9. Construct the stages and pending REPLAY, check the shared context, publish
   through the existing deferred ownership-bound path and finish its readback,
   stage evidence and final ledger/context checks. Release the one complete result
   only if these checks pass. Preserve safe cleanup/reuse semantics below.

The manifest preflight inspects declared ref objects, not arbitrary nested files
as a new graph traversal. Existing source/config/TRAIN/forecast readers remain
responsible for their own bounded closure validation and guards before each open.
Tests must show nested RESERVED paths in each supported manifest are rejected
before those target bytes are read; no general untrusted-manifest executor is
introduced.

## Proposed v4 output and immutable REPLAY

The outer adapter result continues to use the current master schema and four
stage names. Keep all current base keys, decision shape, evidence structure and
candidate wrappers. Do not modify/reseal the pure prepared object or any native
model/prediction. In particular its generic
`CONFIGURED_STAGE1_SOURCE_PARENT_NOT_CONNECTED` blocker remains an immutable
standalone-preparer declaration: the separate v4 parent-dispatch status records
the connection actually exercised by this invocation, not global prerequisite
or campaign completion.

For v4, `stage1_dispatch` has exactly these eleven fields:

- `status`: `NOT_REQUESTED`, transient `NOT_RUN_DATA_BLOCKED`, or the exact
  completed source-v2 status (`DIAGNOSTIC_ONLY` / `NEED_MORE_DATA`). Transient
  preparation failure follows existing clearing behavior and is not a successful
  published dispatch.
- `registry`: `habu-stage1-scores-v2`.
- `source_contract_version`: `habu-stage1-source-contract-v2`.
- `candidate_config_sha256`: verified canonical config digest.
- `feature_definition_sha256`: verified strict feature-definition digest.
- `candidate_ids`: exact configured order.
- Five exact false flags: `trusted_pre_reveal_authorized`,
  `trusted_campaign_authorized`, `source_issuer_authenticated`,
  `loaded_bytecode_authenticated`, `confirmation_authorized`.

No `IMPLEMENTATION_BLOCKED` registry reason is added for a legal v4 set. Other
missing science/trusted-campaign/source-authentication capabilities stay blocked.
Requested Stage1 diagnostics are attached unchanged from source-v2; all formal,
selection, promotion, scientific-fit, confirmation, official and production
authority remains false. Candidate generation may PASS for synthetic mechanics;
candidate validation remains BLOCKED and the decision remains NEED_MORE_DATA.

The pending REPLAY retains the existing v3 content keys, with schema
`habu-research-model-request-v4`, the v4 dispatch and optional unchanged
`stage1_diagnostic`. `parent_dispatch` has the existing six keys:

- `status`: `CONFIG_SOURCE_STAGE1_V4_SOFTWARE_ONLY`.
- `source_authentication`: `NOT_ATTESTED`.
- `trusted_campaign_authorized`, `trusted_pre_reveal_authorized`,
  `loaded_bytecode_authenticated`, `confirmation_authorized`: false.

The existing content digest, physical JSON hash/newline, immutable path
`predictions/replay/{night}/research/{content_sha256}.json`, 64MiB output cap and
readback checks are reused. All consumed input evidence and actual cumulative
read bytes remain visible. Null Stage1 still records the v4 request/config and
`NOT_REQUESTED`; it cannot imply evaluation happened.

## Missing data, contradictions, resources and cleanup

| Situation | v4 behavior |
| --- | --- |
| Incomplete eligible TRAIN/full forecast | Existing DATA_BLOCKED; no partial candidate set, Stage1 or new REPLAY |
| Complete preparation, Stage1 null | Three candidates, no evaluation read, one development REPLAY; NOT_REQUESTED |
| Valid supplied source-v2 contract with null/unavailable scope/ledger root, UNKNOWN or incomplete coverage | Retain three candidates; Stage1 NEED_MORE_DATA with empty per-night/pooled/uncertainty metrics; one development REPLAY |
| Supplied invalid bytes/shape/hash/config/causality/native chronology/known identity contradiction | FAIL/REJECT_CANDIDATE; no released candidates/diagnostics/REPLAY and no new owned physical REPLAY |
| Source/profile absent or validly late config readiness | Existing DATA_BLOCKED; no new REPLAY |
| Shared cap/deadline exceeded, including hashes/rescans/publication/final construction | RUNTIME_BLOCKED; no released partial data; cleanup only owned new artifacts |

Actual stored September-28 source-qualified five events/six capture occurrences
do not establish a predeclared full scope, ex-ante model features, complete
denominator or qualified TRAIN set. A source diagnostic of that cohort remains
NEED_MORE_DATA/empty metrics. The parent may correctly stop earlier at TRAIN or
forecast gates. Neither outcome is a real-data fit or a zero-valued denominator;
no fabricated scope, negative row or placeholder ledger may bypass those gates.

Keep the same `ProspectiveReadContext`, absolute deadline at most 300 seconds and
cumulative 2GiB actual-byte ledger from request through final publication checks.
Existing local input/config/source/pure/output caps stay unchanged. Every recheck,
readback and reused-file read is charged; no new context, independent deadline,
cap increase or fresh three-candidate/campaign allowance is created. Native Python
or library operations cannot be hard-preempted between cooperative checks; bracket
them with the shared guard and never return a successful late result.

Publication is deferred until source checks and stages finish. Late failure clears
candidate, diagnostic and replay return fields. Existing content reuse must survive
cleanup. A newly created own link/temp is deleted only through the current
handle-bound Windows or pinned-POSIX/quarantine ownership helper. If ownership
cannot be safely re-established, preserve foreign bytes and report truthful
untrusted residual paths with a blocked/failure result. Do not add path-check then
unlink fallbacks, recursive cleanup or same-user adversarial-process guarantees.

## Compatibility and TDD acceptance

Before product edits, native Git archive
`5d4b84fcc0d9b54683f80b4fcace0818d7fb94bd` supplied eight synthetic whole-result
oracles. Source native blob: 29,644 bytes, SHA-256
`0a98ed940e461b49dd85802e2dd4f0006f3245a1e8ff55c831120aec9b8ba104`.
The accompanying review records the full-result hashes, actual bytes and physical
REPLAY evidence. Future tests go only in the owned existing parent test module;
no additional fixture path is granted by this design.

1. Preserve all eight first/reused whole result digests, physical REPLAY bytes,
   file count, reference/content/physical hashes and measured read counts. Native
   policy fixture bytes must come from the pinned Git blob rather than Windows
   CRLF checkout normalization; actual runtime mismatches still fail. Keep the
   public parent signature and all legacy v1/v2/v3 version/field acceptance.
2. Add v4 request/ref/config rejection before fit: missing/extra request fields,
   inline/null config, unknown request version, invalid references, strict config
   hash/definition/order drift and unsupported fourth/HB-A2 selection. Separately,
   supply a correctly byte-bound Stage1-v1 manifest: assert native preparation
   and admission happen first, then source-manifest version rejection before any
   referenced evaluation payload opens, with no v4 downgrade or new REPLAY.
   v3 reversed/A1 Stage1 must still remain IMPLEMENTATION_BLOCKED before its
   manifest opens, with byte-identical REPLAY.
3. Exercise actual guarded config/TRAIN/forecast/source-v2/pure-v2 paths on all six
   legal ordered triplets, complete and UNKNOWN coverage plus null Stage1. Compare
   parent diagnostics/projection hashes to the public standalone source-v2 call.
   Synthetic two-event/three-individual fixture must retain 2/3 recall and the
   outside-universe individual miss, same full universe and 2,000/seed-0 bootstrap.
4. Before any evaluation manifest open, inject genuinely rehashed native model
   future/earlier cutoffs and held-out mismatch for uniform/A0/B1/A1; invalid
   uniform formula/probability, B1 status, A1 recipe and prepared/prediction
   binding. Confirm rejection with open sentinels, not merely exception text.
5. Guard all top/nested RESERVED refs, including code/manifest refs and mixed
   case. Real supported OS junction/symlink tests must show external-open count
   zero, with non-destructive fixture cleanup; no fake filesystem/platform.
6. Validate source-v2 known contradictions even with missing coverage. Recheck
   source/config/code mutation after fitting, Stage1 and stage construction;
   assert no new REPLAY. Resource tests expire the same actual context at native
   admission, evaluation/bootstrap, source rescan, publication/readback and final
   construction. For the v4 private admission seam, exercise each exact named
   capacity/budget class above, assert RUNTIME_BLOCKED with no exposed candidates,
   diagnostic or new physical REPLAY, and sentinel-prove no Stage1 manifest open.
   Ordinary shared-check TimeoutError/InputCapacityError must stay unwrapped;
   non-runtime caller-check exceptions must not be swallowed or relabelled as
   capacity. Preserve the old v1-v3 catches/oracles. Count cumulative actual bytes
   including reused artifact reads.
7. Exercise new-file and same-content reuse cleanup, post-native link interruption,
   replacement leaf, ancestor junction/symlink swap and truthful residual behavior.
   Existing POSIX quarantine tests remain genuine Ubuntu-only; do not fake fcntl.
8. Retain actual Sept28 no-complete-denominator evidence without inventing an
   otherwise unavailable real TRAIN/full forecast fixture. All test-only fits are
   synthetic. Run owned parent, both Stage1 source versions, pure Stage1,
   config-source, configured preparer and master dispatch regressions, then
   independent exact-source review and coordinator exact-head/fresh-main Ubuntu CI.

## Ownership and finish line

Only `src/research_pdca_adapter.py`, `tests/test_research_pdca_adapter.py`, this
spec and `docs/reviews/research_configured_stage1_parent_v2_20261025.md` are owned.
No source adapter, pure evaluator/preparer/config, model, G0 schema, master parent,
Raw/ORIGINAL, policy, dependency pin, workflow, controller, STATE or freeze edit.
The initial design and revision commits changed only the two documents. Code/TDD
was authorized after independent design PASS; exact-source implementation review
and coordinator Ubuntu CI remain separate gates. The coordinator owns final main
alignment, freeze, publication, PR/CI and merge.
