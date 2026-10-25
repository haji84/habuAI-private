# Stage1 source projection export v1

Approved bounded design against main
`d2f8c759ad9817cdcafab4c97c4fbdf5f4fb08b3`. This is an additive export of
already validated development projections, not a T2 source adapter, forecast
issuer, fitter, parent dispatch or source-authentication mechanism.

## API and unchanged defaults

```python
project_stage1_sources_v2(
    root, manifest_ref, forecast, prepared, *, candidate_config,
    expected_config_sha256, feature_definition_sha256, context
)
```

The implementation belongs to `src/evaluation/stage1_source_adapter.py`.
Use a private exact-bool `_export_projections=False` mode in `_evaluate`, with
the new API selecting True and the existing APIs retaining False. There is no
callback sink, global monkeypatch, duplicate source parser or second evaluation.
The new API follows the same configured-source-v2 admission, native candidate
binding, source validation, pure Stage1 evaluation and source rescan as
`evaluate_stage1_sources_v2`. It does not skip pure validation or bootstrap to
obtain projections cheaply.

The default `evaluate_stage1_sources` and `evaluate_stage1_sources_v2` return
their existing whole artifacts, signatures, hashes, numerical values, source
read order/counts and actual-read-byte receipts unchanged. Existing parent
request versions, their immutable REPLAY bytes and registry behavior are
unchanged. Export-only guards, copying and hashing execute only in the new mode.
No new parent request, publication path or persistent artifact is added here.

`forecast` and `prepared` remain mandatory complete strict-G0 and configured-v2
inputs. Their existing combined ownership, 120000-row cap, exact three ordered
candidates, config/feature-definition hashes, native model/prediction hashes,
TRAIN lineage, held-out night and fit chronology are checked before evaluation
payload reads. The function does not create a forecast, prepared models, targets
or observations when these inputs are absent. Such upstream missing data stays
blocked before invoking this API.

## Exact returned JSON

The bundle has exactly these fourteen fields:

```text
schema_version, purpose, stage1_result, universe, scores, ledger,
source_authentication, fit_authorized, scientific_authorized,
confirmation_authorized, selection_authorized, promotion_authorized,
production_authorized, receipt_sha256
```

- `schema_version` = `habu-stage1-source-projection-bundle-v1`.
- `purpose` = `DEVELOPMENT_EVALUATION_ONLY`.
- `stage1_result` is an exact owned copy of the already sealed result returned
  by the existing configured source-v2 path. Do not alter or reseal its contents
  merely to mark export mode. Its official/authentication/authority limitations
  remain intact.
- `universe`, `scores`, `ledger` are exact owned copies of the actual values
  passed internally to the pure configured Stage1 evaluator. Preserve nulls;
  do not construct placeholders. The universe/ledger retain existing v1
  schemas, and scores retain `habu-stage1-scores-v2`.
- `source_authentication` = `NOT_ATTESTED`. All six top-level `_authorized`
  fields are exact false booleans. No nested authority or authentication claim
  may be elevated.
- `receipt_sha256` seals the complete bundle except its own field.

`H(x)` means SHA-256 of canonical UTF-8 JSON: sorted keys, compact separators,
Unicode retained and nonfinite numbers rejected. For each nonnull U/S/L body,
`H(full body)` must equal the corresponding entry in
`stage1_result.source_receipt.projection_sha256` and the configured result's
`input_digests`. A null projection matches null in both places. The existing
`input_digests.config`, strict feature-definition and prepared-receipt bindings
remain authoritative declarations within that result; do not add competing
copies of them to the bundle.

The ledger's existing `ledger_sha256` separately hashes its body excluding only
that ledger self-hash field. It is not interchangeable with `H(full ledger)`.
The bundle and nested result receipts likewise have their own separate scopes.
Hash equality establishes declared consistency, not issuer truth, historic
availability, loaded-bytecode identity or trusted preregistration.

## Source guards and chronology

After owning/admitting configured prepared inputs, but before opening the first
source manifest or scope payload, export mode checks both `manifest_ref` and
the owned `forecast.receipt.manifest_ref`. Use the existing exact G0 byte-ref
grammar and snapshot namespace rules. Reject any casefolded path component in
`original`, `incoming`, `reports`, `sealed`, `confirmation`, and all C0/DEL
characters. Apply the shared `master_inventory.local_path` guard before
filesystem metadata/reads: trailing ASCII dot/space, colon, ambiguous `~digits`
components, traversal, root/ancestor reparse and containment rules remain active.
Do not normalize ambiguous spelling into an accepted path.

After reading source-manifest metadata, apply those export-only namespace and
path guards to every known node ref before opening any scope/outcome source
payload. Preflight the entire declared set, not only reachable-looking refs
encountered during reads. Existing DAG reachability/role/cycle checks still run.
All actual bytes, exact size/hash checks and final rereads use the existing
`G0ArtifactReader` and shared `ProspectiveReadContext`. Nested refs discovered
inside payloads retain the existing strict consistency checks; a source ref is
never permission to read a reserved namespace. The new export guards must not
broaden or otherwise change default v1/v2 admission behavior.

Keep existing source chronology: the operational night starts at07:00 JST;
the fixed full scope/horizon and every scope ancestor are available strictly
before forecast cutoff. Observational captures/individuals/coverage lineage
is separate from ex-ante scope. Each of its four readiness stages must not
precede the bound actual records; complete coverage additionally follows the
declared horizon end. These requirements propagate to observational ancestors
and the manifest as already implemented. All readiness/usable-at declarations
must satisfy the existing evaluation boundary and DAG maximum rules. Later
retrospective evidence is not retroactively an ex-ante predictor.

UNKNOWN/INCOMPLETE coverage, absent scope/roots or an exactly classified missing
referenced file preserve the existing NEED_MORE_DATA result and empty Stage1
metrics. Missing projections stay null; an incomplete but nonnull ledger passed
to the pure evaluator stays nonnull. Preserve whichever real projections exist,
rather than flattening every NEED result to nulls. Do not suppress supplied
schema/hash/ID/link/causality
contradictions because another input is missing. Read-only September28 CSVs may
establish source-summary5events/6individuals without establishing scope,
complete denominator, universe, freeze or forecast performance.

## Bounds, ownership and completion

The caller's existing `ProspectiveReadContext` is mandatory; create no new clock
or byte ledger. Preserve its absolute deadline and already charged bytes. Any
restriction may only tighten existing bounds, never extend the deadline or
reset cumulative bytes. Existing per-source, DAG, event/individual and model-row
caps remain in force. Export is not an exemption from those caps.

After the normal pure evaluation, existing `reader.rescan`, source receipt
construction and Stage1 result seal, perform an owned combined bundle copy
bounded by16MiB canonical JSON,2M nodes and depth12. Enforce width/depth/type and
string/key limits before growth/copy, use bounded streaming encoding/hashing,
and retain the same context check in controlled loops and immediately before
and after the final bundle seal. No truncation or partial bundle on capacity,
malformed input or expiry; preserve existing capacity/ValueError/TimeoutError
semantics. Copying detaches normal caller-owned JSON and retains typed hashes.

Export adds no source read after the existing final rescan. Thus nested
`source_receipt.actual_read_bytes` retains its existing meaning and exact
value; only CPU-bound copy/hash/check work follows. Do not add a late rescan and
leave a stale nested byte receipt or hash. The existing caller publication
contract still rechecks all consumed bindings before publishing any later
artifact. This normal module/JSON ownership and source-snapshot consistency
boundary is not an atomic filesystem snapshot, hostile-thread sandbox or
hard-preemptive execution guarantee. Static guards and cooperative checks do
not authenticate source truth or defeat arbitrary live same-user interference.

## Geometry and excluded next work

Strict G0 rows contain source-declared100m cell-centre forecast coordinates
`(cell_x*100+50, cell_y*100+50)`. They are not measured road anchors, independent
geographic validation, or HB-B1 cell-origin points. This bundle's universe is
the Stage1 area universe; no T2 exact-point universe, midpoint target, native-rank
conversion, target selection, protocol/freeze wrapper or source-bound T2
evaluation is constructed. No calibration, matching, model, label, parent
registry, confirmation storage, Raw/ORIGINAL byte or security permission changes.

## Required regression evidence

- All six legal configured triplets; independent full bundle/body/nested receipt
  hashes; mutation of returned JSON cannot alter caller inputs or prior results.
- Existing four whole source-v1 artifacts/read-byte oracles, configured-v2
  outputs, legacy parent outputs and literal REPLAY bytes remain exact. Default
  calls never execute the export-copy/hash/read branch.
- Missing scope/coverage/file and real five/six inputs preserve NEED/nulls/empty
  metrics. Supplied known malformed hashes, IDs, links, dates, source roles and
  four-stage ancestral causality still reject alongside missing data.
- Reserved/C0/DEL and portable-alias initial manifest, forecast manifest and
  node refs reject before forbidden payload opens; real native junction/ancestor
  guards are exercised honestly on the available platform.
- Combined output capacity, existing collection caps, cumulative actual reads
  including remaining+1 rejection byte, final rescan failure and deadline expiry
  during/after bundle hashing return no partial export.

Backend-emitter legacy-positive fixtures must pin the historical adapter's
native LF capsule (37345bytes, SHA-256
`388bf18b1f4f90fb29d48fe0c4f58579bae925d281f99b27eb0e79baa038ada6`)
alongside their pinned old parent, including real-engine fixtures. Do not mix
old parent bytes with future HEAD adapter bytes or loosen runtime closed
profiles to repair a fixture. Historical source-profile tests and genuine POSIX
integration remain separate evidence gates.
