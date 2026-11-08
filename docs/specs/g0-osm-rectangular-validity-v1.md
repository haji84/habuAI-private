# G0 auxiliary OSM rectangular validity v1

Status: concrete design for coordinator/independent review; implementation is
not approved by this document. Base main
`756441d7b2c758c6c81318935a50a7524afc94b1`, 2026-10-26.
This commit contains this specification only. No runtime, test, source,
authority, STATE, cycle or policy change is included.

## Gap and chosen boundary

PR33 already supplies pinned33-part archive -> CRC-checked ZIP -> exact CSV ->
fixed auxiliary OSM projection, complete declared-horizon shards, truthful
current-run readiness, full closure rescan and safe whole-capsule publication.
Reuse `materialize_g0`, `_g0_shard`, strict `_shard` and the existing owned join.
The missing capability is a72-window producer completing under its existing
cumulative2GiB limit, not a missing whole-night loop.

A read-only existing-encoder probe on the actual16,990-cell CSV measured
11,089,536 large JSON bytes per one-window shard, of which5,131,171 bytes are
repeated per-row/per-feature validity intervals. Three physical passes across
72 shards require2,395,339,776 large bytes before source closure/metadata.
The recorded actual earlier72-window run blocked at2GiB+1 and published nothing.

Chosen approach: add a compact, exact, typed encoding for the existing OSM
static per-unit validity relation. Preserve every physical row/check, source
read and cap. Alternatives are a more invasive incremental owned-readback
validator session, or a new bounded compressed transport; neither is required
for this slice. Increasing caps, collecting the whole product, skipping reads
or concatenating subset model ranks is excluded.

## Additive producer API and compatibility

Proposed keyword-only addition:

```python
materialize_g0(..., budget_seconds=300, _read_context=None,
               validity_encoding='per_row_v1')
```

Exactly two supported strings: `per_row_v1` and `osm_rectangular_v1`. Unknown,
wrong-type or explicit None selections reject before source reads/writes.
Omitting the keyword retains the existing per-row payload/default behavior.
No legacy `materialize` signature or legacy <=6-window behavior changes.

Proposed CLI option is
`--validity-encoding {per_row_v1,osm_rectangular_v1}`. Explicit use requires
`--strict-g0`; a non-strict invocation rejects instead of silently ignoring it.
No new output-parent creation or publication fallback is introduced.

The new mode only changes the validity sidecar representation. Universe,
feature values, v2 snapshot, physical row order, complete manifest/partition
logic, fixed definitions and source kinds remain the existing contracts.
Code/source/manifest hashes naturally bind the changed implementation and
sidecar bytes. Default compatibility does not mean pretending new code bytes
have the old frozen code hash, or asserting identical wall-clock receipts from
two independently timed actual runs.

## Exact new sidecar payload

Example for the first one-window shard:

```json
{
  "schema_version":"habu-g0-osm-static-validity-v1",
  "domain_id":"domain",
  "snapshot_id":"s000-s",
  "cell_range":[0,16990],
  "time_range":[0,1],
  "feature_sources":{
    "road_axial_cos":["s000-road_axial_cos"],
    "road_axial_sin":["s000-road_axial_sin"],
    "road_length_m":["s000-road_length_m"]
  },
  "rule":"EACH_CANONICAL_UNIT_WINDOW_600S"
}
```

These seven top-level keys are exact; no `rows`, overrides, trusted/coverage
flags or extra keys are accepted. `domain_id` and `snapshot_id` are bounded
source-node identifiers, resolve to the actual enclosing manifest's domain and
shard snapshot nodes, and must equal those IDs.
Each range is exactly two nonboolean integers, half-open indices in the
already validated sorted cell array and UTC600s window array. They must equal
the enclosing shard's resolved cell/time partition endpoints, not a superset,
subset, arbitrary cell coordinates or wall-clock timestamps. Zero-width,
reversed, outside, boolean, float, null and unhashable values reject as ValueError.

`feature_sources` must equal the exact feature-name -> one actual feature-node
ID list already resolved from the shard's bound snapshot. Its names must be
exactly the three current `OSM_FEATURE_UNITS` names. Every feature definition
must be version1/static_predictor with the existing units and one corresponding
validated `osm_static_projection` parent. All projections must have passed the
existing pinned33 parts, ZIP/CRC, exact CSV, code/provenance and recomputation
checks in `_validate_osm_sources`; eligibility must derive from the already
validated `osm_sources` and `typed_features`, never a filename/kind/header claim.
Generic `static`/`forecast`, mixed, planned, lagged or non-OSM predictors
cannot use this encoding, even if they use the same feature names.

The domain must be auxiliary and bind exactly one validated typed
`candidate_cells` OSM projection; existing full archived CSV cell equality
must have passed. A generic domain or a narrowed archived domain cannot gain
eligibility merely because its three predictors happen to be typed OSM.

The sidecar still uses the existing source kind `validity`, role `protocol`,
FORECAST_INPUT allowed use, auxiliary class and exact actual feature-node
parents. No new G0 source kind/deployment or source-namespace allowance is added.
Its own bound byte ref/readiness/max usable time, and its parent closure, remain
mandatory. A newly generated JSON descriptor is not source authentication.

## Meaning and mandatory checks

The fixed rule denotes, for every canonical unit `(cell,t)` in precisely that
rectangle and for each required feature, physical validity `[t,t+600s)`.
It is a closed representation of the entire checked relation, not a fallback
for absent validity data. Do not infer validity from availability or treat
hashes, a broad declared interval, or the rule string itself as evidence.

Strict validation must retain all existing physical-row checks: each expected
sorted cell/window occurs once, exact canonical row ID, UTC window equality,
correct100m center, night/cutoff binding, row count, feature source coverage and
actual CSV-recomputed numeric equality. For every such unit, derive the exact
window interval and retain `_cover` for each required source and feature node.
The enclosing snapshot, universe and validity-node intervals must still
cover their entire shard. Four readiness stages and dependency maximum usable
time remain strictly before cutoff, with the existing current-intake chronology.

Keep the existing per-row `habu-g0-validity-v1` branch and read order unchanged.
The seam is the existing `_shard` sidecar read/validation at base lines758-772:
add exact schema dispatch there and a small pure checker for the new
typed form; unknown/malformed schema is ValueError, with no fallback to the
other form. Existing duplicate-JSON, namespace/reparse, reference ownership,
finite/bool, source DAG and all-or-none coverage checks remain in force.
`pi.join_prospective_payloads` does not consume sidecars and is already the
checked pure owned join; it requires no change.

One producer call selects one encoding for all its shards. Validator dispatch
is independently exact for each sidecar: a complete manifest may mix old
per-row and new rectangular shards when every shard passes its full applicable
contract. There is no global encoding field or cross-shard mode state. A single
sidecar mixing `rows` and rectangular keys, or compact mode with non-OSM/mixed
predictors, is invalid. This clarification is the coordinator's final decision
after V's exact6101094 design review; TDD implementation is approved.

The producer's compact branch must never build the redundant per-row physical
interval dictionary first. It still constructs only one bounded shard's rows
and numeric values at a time. The checker must use the existing bounded row
loop and callbacks rather than expand the descriptor into a full sidecar tree.
No full-night Cartesian materialization, new source graph or optimizer exists.

For exactly the same bound universe/feature bytes and declarations, partition
and row order, old and compact validity forms must return identical joined
rows and `canonical_joined_rows_sha256`. Sidecar/manifest/consumed byte hashes
must differ appropriately. Equal numeric values in two actual runs with
different readiness or feature-source bytes do not imply equal joined digests.

## Resources and publication

Use the same existing `ProspectiveReadContext` through producer and validator.
Each generated artifact is still written exclusively, fsynced and physically
read back; validator initial reads and complete final rescan remain actual
billed reads. Original reads, archive decode/expanded member bytes, code,
policy, current-run proof, all metadata and every rescan remain charged.
No new deadline, context reset, exempt cache or trust flag is introduced.
Propagate caller check exceptions without replacing their identity; check all
new loops and boundaries through final hash/return/publication cleanup.

Preserve300s,2GiB actual reads,128MiB/source,384MiB/shard,32 features,
400000 joined numeric cells/shard,100000 domain cells,144 windows,
4M domain rows,256 shards and the existing DAG caps. The separate whole-model
collector retains120000 rows AND16MiB. No cap is increased or reinterpreted as
a per-batch exemption.128MiB/source does not certify a whole-process RSS bound.

At measured current sizes, removing the repeated maps leaves5,958,365 large
bytes/window;72 x3 passes is1,287,006,840 bytes before compact descriptors,
metadata and closure. This is promising headroom, not a proven total or upper
runtime/memory bound.300s completion, actual peak RSS and a complete72-window
run remain unproved. A144-window theoretical three-pass large-file volume
already exceeds2GiB even with this encoding; do not advertise that capability.

All directories/barriers, existing-output preservation, native no-replace
publication, destination races, cutoff/deadline/interruption handling and
owned-output-only cleanup remain unchanged. Publish no success/output capsule
until the whole declared set and all final rescans pass. Failure returns no
smaller substitute horizon or partial successful rows/manifest.

## Proposed ownership after explicit implementation approval

- `scripts/build_osm_prospective_universe.py`: mode selection and compact write.
- `src/g0_forecast_contract.py`: narrow sidecar dispatch/check, existing row loop.
- New `tests/test_g0_osm_rectangular_validity.py`: synthetic codec, source scope,
  equivalence, producer integration, capacity and late-failure regressions.
- This spec and new `docs/reviews/g0_osm_rectangular_validity_20261026.md`:
  actual verification/limitations. Existing tests run unchanged.

Do not edit prospective_inputs, policy/cycle/STATE, Raw/ORIGINAL, old planned
tree, requirements, model packages, parent dispatch or registries. Coordinator
owns source-closure freeze, integration, GitHub and any actual-run ledger.

## TDD and release evidence required after approval

1. RED then GREEN: synthetic typed OSM fixture accepts the new exact form;
   old default payload still works; equal bound inputs yield exact same full
   joined rows/digest and counts. Keep generic static/forecast forms on old mode.
2. Change each key/range/ID/rule/source/class/feature set/type; require ValueError.
   Reject generic same-named predictors, non-typed domain, narrowed domain,
   unknown fields, dupe keys, boolean/equality loopholes and same-sidecar hybrid
   modes. Verify a completely checked old+rectangular mixed-shard manifest works.
3. Preserve all canonical unit, normalized timestamp, center, missing/extra row,
   missing/overlap/duplicate shard and cross-shard artifact-reuse rejections.
   Reject insufficient source valid-time despite early availability and vice
   versa. Check all four readiness boundary equalities and dependency maxima.
4. Actual shared ledger covers three reads plus closure; unchanged min caps and
   exhausted context fail with no partial result. Observe no giant validity
   tree construction; check caller mutation/deadline/final-rescan attacks.
5. Run existing strict G0, producer, source guards and model-collector regression
   tests unchanged. Execute real native publication races, directory barriers,
   cutoff/deadline and interruption cleanup on their supported platforms.
6. After review, record an actual33-source72-window prospective software
   rehearsal: full1,223,280 units/72 shards/3 features, exact manifest/joined
   digest, all billed bytes, actual wall duration/peak RSS, original before/after
   SHAs and no partial publication. No fabricated wall time or backdated
   readiness is permitted. A genuinely future declared cutoff/horizon for this
   software test is not an official P0 or historical availability proof.

Independent hostile review and exact-head Ubuntu CI are required; an estimated
size or synthetic fixture is not the final run. Any timing/capacity failure
remains honestly blocked, with no budget extension/skip/claim of convergence.

## Meaning and remaining blockers

All existing source authenticity/history/current-road-access NOT_ATTESTED flags
and fit/science/production false flags remain. This encoding only preserves a
declared archived auxiliary domain; it does not certify all-island driveability,
weather/DEM/wind, actual/planned effort, labels, outcome completeness or FN
denominators. Outside-universe confirmed captures are not removed from their
independent full-scope ledger. G0 planned/lagged capability remains blocked.
Model streaming/global hierarchy ranks and parent full-night inference remain
separate unimplemented protocols; receipt validation never authorizes them.
