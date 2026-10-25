# Time-target source adapter v1

Design against `0255e101337513e5013ce31edf68c085240243a9` (pending Stage1
projection-export integration). Root approved the bounded declared-cell-centre
direction before implementation. This document specifies a new standalone
source adapter; it does not implement or authorize target generation, fitting,
parent dispatch, publication, historical prereveal trust or a formal KPI.

## API and prerequisites

```python
from evaluation.time_target_source_adapter import evaluate_time_target_sources_v1

evaluate_time_target_sources_v1(
    root, stage1_manifest_ref, forecast, prepared, *,
    candidate_config, expected_config_sha256, feature_definition_sha256,
    candidate_id, frozen_targets_ref, protocol_ref,
    expected_protocol_sha256, context,
)
```

`context` is the caller's existing `ProspectiveReadContext`. `forecast` is the
complete strict G0 `{receipt, rows}` collection; `prepared` is the complete
configured-v2 three-candidate preparation. Config and feature-definition hashes
have their existing meanings. `candidate_id` explicitly identifies one of those
three candidates; no ranking, fallback, fourth candidate or selection occurs.
Missing/incomplete mandatory forecast or preparation is an admission error,
before evaluation reads. Do not manufacture a forecast or invoke pure T2 with
missing upstream prerequisites as a substitute.

`stage1_manifest_ref` retains the existing exact three-field G0 byte-ref grammar.
`protocol_ref` is mandatory. `frozen_targets_ref` is either null or a reference.
Both latter references have exactly G0 BOUND_FIELDS:
`{path, sha256, size_bytes, readiness, usable_at}`. Readiness has exactly the
existing four timestamp fields. Own all input JSON and ref primitives before
callbacks/read operations. A supplied protocol/target reference whose file is
missing rejects with ValueError; it does not become a null projection or a
fabricated protocol. Only an explicitly null target reference means missing
targets. Existing Stage1 missing-source behavior is unchanged.

## Reuse and ordering

1. Check the shared context, capture its initial actual-read counter, preflight
   owned references and admit the configured native prepared inputs using the
   existing `_configured_prepared` seam. Preserve its native model, recipe,
   TRAIN, full forecast-row, chronology and false-authority checks. Translate
   only the existing named capacity/budget exceptions as source-v2 does.
2. Independently reload the complete forecast with
   `g0.load_g0_forecast_rows`, the owned receipt's manifest_ref/night/cutoff,
   expected feature-definition hash and the same context. Compare exact typed
   canonical rows and stable receipt content as specified below. No subset,
   source-parser clone, manual reconstruction of G0 ref sizes or OSM exception
   widening is permitted.
3. Read the mandatory protocol and any supplied target artifact with the
   existing guarded G0 reader. Validate their known schema/hash/time/native
   lineage contradictions before opening Stage1 outcome payloads. Reuse pure
   T2 protocol/target validation against a complete known forecast row map;
   foreign selected rows and wrong midpoint times already reject here. Scope
   binding is completed after its real source projection exists.
4. Call `project_stage1_sources_v2` exactly once with the owned inputs and same
   context. Reuse its complete source validation, native admission, pure
   Stage1 computation, scope/coverage causality, missing-data rules and rescan.
   No callback sink or duplicate outcome parser is introduced. The repeated
   native admission inside that existing API remains its unchanged behavior.
5. Construct the separate full T2 point universe below, or retain null when
   the export's actual scope/universe is null. Pass that universe, the exact
   supplied target projection or null, and the export's exact ledger or null
   to `evaluate_time_targets`, using the supplied protocol/digest,
   `budget_seconds=min(30, context.remaining_seconds)` and `check=context.check`.
   All supplied contradictions are checked before a NEED result.
6. Reload the complete G0 forecast again under the same context and compare
   against the same owned input. Finally reread the protocol, supplied target,
   any preflight-bound refs and every exported consumed_ref using their exact
   already-bound byte refs, without reparsing outcomes. This single final
   combined ref pass is the rescan for those artifacts; an additional duplicate
   pass is unnecessary. Conflicting hashes or explicit sizes for one path reject.
7. Build and seal the bounded outer result only after all these reads. Check
   before and after its final hash/copy. No partial metrics or result escapes
   malformed input, capacity exhaustion or expiry.

The existing source defaults, signatures, results, read ledgers, model math and
physical legacy REPLAY artifacts remain unchanged. No new parent request or
persistent file is created by this adapter.

## Complete G0 revalidation and receipt identity

The G0 receipt does not retain its original issuance `as_of`. For both reloads,
use the bound forecast cutoff as the declared revalidation `as_of`; never use
the later evaluation wall-clock, which may already be past the horizon. This
checks forecast consistency at that cutoff and does not authenticate an original
issuance event. Preserve current G0 restrictions, including its existing
cutoff/night and future-horizon rules; do not narrow or relax the pure T2 API.

The loader receives a positive remaining budget no greater than its existing
maximum and `_read_context=context`. It may only tighten existing absolute
bounds, never replace the context, extend its deadline or reset charged bytes.
Its actual source/feature/code/policy validation and final rescan run normally,
including the exact existing auxiliary OSM transport paths.

Both freshly loaded row arrays must equal the entire supplied owned row array
in canonical typed JSON and joined-row digest. Receipt comparison removes
**only** `actual_read_bytes` and `validation_read_bytes` from each receipt, then
compares the complete remaining typed objects. Unknown/changed fields therefore
reject. Supplied counters must still be nonnegative non-bool integers with
validation_read_bytes <= actual_read_bytes; their historical values are declared
phase counters, not authenticated observations of this invocation.

Let `H` be SHA256 of canonical UTF-8 JSON: sorted keys, compact separators,
Unicode retained, nonfinite values rejected. Preserve `H(full owned supplied
forecast receipt)` as the point universe's forecast_receipt_sha256. Reload
counters naturally increase and must not silently change a predeclared universe
or protocol hash. Also bind `H(stable receipt excluding exactly those counters)`.
Report fresh reload counters separately. The outer final actual_read_bytes is
the final shared counter for this call; its delta from entry is validation bytes.

## References, declared availability and freeze

Before metadata/payload reads, retain export-mode snapshot namespace, C0/DEL,
reserved-component and shared portable-path guards. Refuse casefolded original,
incoming, reports, sealed and confirmation components, ambiguous Windows
spellings, traversal and root/ancestor reparse links. Preflight all known G0
manifest source/code/provenance refs before the loader opens their payloads,
retaining G0's role-specific namespaces and exact pinned OSM exceptions. Do not
apply the more general Stage1 namespace grammar to reject or broaden those
special G0 transport paths. The export API owns Stage1 node preflight.

Protocol file size is at most64KiB; target file size is at most256KiB. Reject
declared oversize before reads. Reader size+one rejection behavior, byte hashes,
duplicate-key/nonfinite rejection and cumulative charging remain in force.

For a supplied target ref, call `g0.validate_readiness` with its four stages,
usable_at and the forecast cutoff. All four stages must additionally be >= the
selected native model's admitted common fit_cutoff. No fit/availability is
inferred from a filename, Git commit, mtime or historical observation date.
Validate protocol readiness the same way, with the target usable_at as a parent
when a target ref exists: protocol usable_at must equal the maximum of its four
stages and that parent. Both usable_at values are strictly before cutoff.

The protocol body is the existing exact T2 protocol. Its nonnull frozen_at must
be >= protocol usable_at and <= cutoff. Null preserves pure T2's declared-freeze
blocker. Pure T2's equality frozen_at==cutoff remains allowed. The protocol binds
the target projection's self-hash and point-universe self-hash; it never embeds
future outcome-ledger hashes. These declarations establish consistency only,
not trusted historic prereveal, issuer authentication or untouched confirmation.

Normalize only transport-identified missing protocol/target files to ValueError;
do not catch ordinary context errors as missing data or swallow caller exception
identity. Supplied-but-missing files remain errors even alongside null targets,
missing scope, incomplete coverage or absent declared freeze.

## Point universe and external target selection

Use the unchanged `habu-time-target-universe-v1` schema. Obtain scope,
scope_sha256 and full horizon from the export's actual Stage1 universe; verify
them against protocol and strict forecast chronology. Stage1 area_ids are never
cast to point units. Copy every forecast row, in its original complete order,
to `{row_id, window_start_jst, utm_x_m, utm_y_m}`. The count/IDs/keys must match
all verified G0 rows exactly. Bind the original supplied receipt H and its
canonical_joined_rows_sha256, then compute the universe's existing self-hash.
If actual scope is absent, universe remains null; no bbox is inferred from
captures, selected targets, observed extrema or cell bounds.

Geometry is exactly `DECLARED_G0_CELL_CENTRE`: copied source-declared coordinates
`(cell_x*100+50, cell_y*100+50)`, not measured road anchors or HB-B1 cell-origin
proxies. No inverse projection, coordinate rounding or new geometry is created.

Targets are the exact existing `habu-time-target-set-v1` object read from the
supplied artifact, without filling null fields. Each nonnull model_sha256 and
prediction_sha256 must equal the explicit selected prepared candidate's actual
admitted native hashes, including produced=false/empty cases. Null lineage
retains existing pure NEED behavior. The common native fit_cutoff is already
bound to each native model by configured admission.

Those native hashes identify spatial prediction inputs, not an issued time-target
model or a commitment to the external target selection. The target file's byte
ref, projection self-hash and bound protocol separately identify the caller's
declared selection. No native score threshold/rank, target creation, winner
selection or timing algorithm is inferred. Produced=true with an empty target
array remains valid abstention when the existing prerequisites hold.

## Exact output and hash scopes

The outer object has exactly seventeen fields:

```text
schema_version, purpose, point_geometry, stage1_bundle, universe, targets,
time_target_result, source_receipt, source_authentication,
prereveal_authentication, fit_authorized, scientific_authorized,
confirmation_authorized, selection_authorized, promotion_authorized,
production_authorized, receipt_sha256
```

Constants: schema_version=`habu-time-target-source-diagnostic-v1`,
purpose=`DEVELOPMENT_EVALUATION_ONLY`, point_geometry=`DECLARED_G0_CELL_CENTRE`.
Both authentication fields are NOT_ATTESTED and all six authorization fields
are exact false booleans. No top-level status is added: time_target_result
retains the pure status and all its official/authentication limitations.
stage1_bundle is the exact sealed export bundle; universe is the T2 point
projection or null; targets is the exact owned supplied projection or null;
time_target_result is the exact sealed pure T2 result. Do not mutate/reseal
nested results to change their flags or counters.

source_receipt has exactly:

```text
candidate_id, input_lineage, external_target_selection, projection_sha256,
consumed_sha256, forecast_revalidation, initial_read_bytes,
actual_read_bytes, validation_read_bytes
```

input_lineage has exactly:

```text
candidate_config_sha256, feature_definition_sha256, forecast_manifest_ref,
forecast_receipt_sha256, forecast_declaration_sha256, joined_forecast_sha256,
prepared_input_sha256, prepared_receipt_sha256, model_sha256, prediction_sha256
```

Here prepared_input_sha256=H(full owned prepared), prepared_receipt_sha256 is
its existing self-hash, forecast_receipt_sha256=H(full original owned receipt),
forecast_declaration_sha256=H(the stable comparison receipt), and native hashes
come from the explicitly selected admitted candidate.

external_target_selection has exactly:
`{origin, protocol_ref, frozen_targets_ref, protocol_sha256, targets_sha256,
declared_frozen_at}`. Origin is CALLER_PROVIDED_DECLARATION. Preserve both
readiness-bound refs exactly, including null target ref. protocol_sha256 is
H(protocol) and equals expected_protocol_sha256. targets_sha256 is the target
self-hash excluding its own hash key, or null. Preserve the protocol frozen_at.

projection_sha256 has exactly `{universe, targets, ledger, stage1_bundle}`;
each value is H(the complete actual projection/bundle) or null. The first three
equal time_target_result.input_digests exactly. These complete-body digests are
distinct from projection self-hashes and physical file hashes.

consumed_sha256 is the conflict-checked union of both actual G0 reload maps,
exported source-consumption hashes and wrapper reader bindings. It covers all
consumed sources without inventing sizes missing from G0's receipt. Exact
protocol/target refs and exported refs retain their existing physical sizes.
forecast_revalidation has exactly entry/final, each containing the corresponding
fresh loader's `{actual_read_bytes, validation_read_bytes}`. Nested Stage1
actual_read_bytes remains its earlier phase counter; later wrapper reads appear
only in the final outer counter/delta. All counters are nonnegative exact ints.
receipt_sha256=H(the complete outer object excluding only its own hash field).

## Bounds, failure behavior and acceptance

Preserve the shared maximum2GiB actual-byte/remaining-time context and all
existing G0/source/model caps. Keep16MiB combined owned JSON,2M nodes/depth12,
width-before-growth and bounded streaming hash/copy checks for wrapper inputs
and the complete returned object, including its receipt. Preserve pure T2's
120000 units/100 targets/20000 events/100000 individuals/2M edges and its other
field limits. Caps are ceilings, not a promise that every count-maximal combined
bundle fits16MiB. No truncation, chunk concatenation or cap increase.

Sequential source rechecks and owned JSON detect ordinary changes; they are
not atomic hostile snapshots, loaded-bytecode/issuer authentication, hard
preemption or permission enforcement. A later publisher must recheck consumed
bindings again before publishing its own artifact. This API writes nothing.

Required RED/independent evidence includes:

- Mandatory forecast/prepared admission before evaluation reads; both complete
  G0 reloads, typed full-row/stable-receipt equality and changed counter handling.
- All six configured orders and explicit candidate bindings; native fit after
  any target readiness; nonnull wrong native hashes; null lineage/target and
  issued-empty abstention, with all known contradictions still validated.
- Area-vs-point universe rejection, exact full row copy, cell-centre semantics,
  foreign/omitted/duplicate rows, midpoint/scope/horizon/freeze and parent-ready
  contradictions, including cutoff equality and honest missing scope/coverage.
- Byte hashes versus projection self/full hashes, appended/same-size mutation,
  missing provided files, reserved/portable aliases and actual available-platform
  link containment before forbidden opens; unchanged allowed OSM transport.
- Final forecast/source/target mutation, remaining+one accounting, every final
  rescan charge, combined copy/hash capacity, callback identity and final-seal
  expiry on both DIAGNOSTIC_ONLY and NEED results; no partial return.
- Complete default source-v1/v2/export/legacy-parent artifacts and receipts
  unchanged. Real September28 five events/six individuals do not supply a
  mandatory forecast, target issue/freeze or complete denominator.

Source truth, training eligibility, prereveal trust, target generation, model
fit, parent integration, formal100m/10min performance, selection, confirmation
and production authority remain outside this slice. Implementation starts only
after root review of this concrete design; coordinator owns later CI/freeze/PR.
