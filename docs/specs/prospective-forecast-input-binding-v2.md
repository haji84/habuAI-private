# Prospective forecast input binding v2 (preproduction only)

## Scope
This slice adds `src/prospective_inputs.py` and synthetic regression tests. It does **not** authorize production Champion inference, provide weather/DEM/route executors, create a real ForecastUniverse, issue an ORIGINAL forecast, or freeze P0. No historical data, GPX, observations, raw file or predictions are modified.

The primary entrypoint is `load_prospective_inputs(root, snapshot_path, snapshot_sha256, operational_night, as_of, model_feature_names=..., budget_seconds=30.0)`. It is deliberately read-only. The return value has `official_issuance_authorized=false` and `qualification=PREPRODUCTION_INPUT_INTEGRITY_ONLY`. The v1 sandbox issuance contract remains unchanged.

## Versioned feature snapshot v2

A snapshot JSON stored under `features/` has:

- `schema_version = "2.0"`
- `operational_night` and timezone-aware `cutoff_time`
- `universe = {path, sha256, available_at}`
- `features = [{path, sha256, available_at}, ...]` for each registered required numeric predictor
- `feature_schema_sha256 = sha256(canonical_json(sorted(feature_names)))`

The referenced `ForecastUniverse` remains v1 with `schema_version=1.0`, `source_type=EX_ANTE_FORECAST`, explicit `geographic_domain`, and `rows`. Every universe row must contain unique `row_id`, `operational_night`, `cutoff_time`, `window_start_jst`, and valid coordinates (UTM52N meters or latitude/longitude). Ten-minute windows must be in the stated operational night and strictly later than actual issuance time. Unit identity uses the 100m cell and the window instant normalized to UTC: JST and UTC spellings of the same instant cannot create separate units.

Each feature source has `schema_version=1.0`, `use_role=static_predictor|forecast_predictor`, `feature_name`, `available_at`, `operational_night`, `cutoff_time`, and `values` as a mapping from every ForecastUniverse row ID to a finite numeric value. No source can add or remove rows. Missing values are not imputed. Duplicate names, conflicting time/hash data, post-outcome fields or stale windows reject the whole join. Model feature names must match the snapshot exactly if a registered model declares them.

Known outcome schema keys (`label`, `observed`, `label_available_at`, `outcome`, `actual_capture`, `capture_event_ids`, `capture_count`, `owner_capture_count`, `outcome_available_at`, `gpx_trace`, `negative_observed`) are forbidden throughout the snapshot, universe and feature metadata, including nested dictionaries/lists, and cannot be `feature_name`. Known names are checked without case distinctions; feature names also ignore surrounding whitespace for this exclusion. The feature `values` mapping has row IDs as keys; these identifiers are not schema fields and its values must be finite numbers. This is an exact known-name check, not a substring prohibition: a predictor such as `prior_capture_count_7d` remains eligible under the existing ex-ante role, scope and strict availability requirements. The check does not authenticate a predictor's semantics or provenance.

### Declared metadata consistency (2026-10-25 repair)

Explicit metadata cannot contradict the older `available_at` contract. On snapshot, universe and feature artifacts, and universe/feature references, the optional timestamps `source_received_at`, `derived_at`, `materialized_at`, `audited_at` may appear directly or in a `readiness` dictionary. If supplied, all values must be timezone-aware, direct/nested copies of the same field must agree, and the maximum supplied readiness must be strictly before cutoff and no later than any supplied internal/reference availability. An explicit `usable_at` must be at least that maximum, strictly before cutoff, and no later than declared availability. For example, `available_at=17:00` with `materialized_at=18:00` at an 18:00 cutoff is rejected; a later reference timestamp cannot hide that contradiction. Missing readiness is never filled from `available_at` or file mtime.

If `role` or `source_role` is explicitly supplied, universe references/artifacts must declare `universe`, feature references `feature`, and feature artifacts `feature`, `static_predictor` or `forecast_predictor`. A feature with `source_role=label` is rejected even if `use_role=forecast_predictor`. These declarations are consistency checks, not proof of the underlying source role or derivation.

An explicit feature or universe `valid_from`/`valid_until` pair, whether on the reference or its artifact payload, must be timezone-aware, nonempty and cover every complete selected ten-minute forecast window, including the last window's end. A missing endpoint, reversed interval or future/expired interval rejects the join. Valid-time and readiness are independent: a future forecast value can be physically valid after cutoff while its actual input readiness must precede cutoff. An interval covering the selected shard does not establish full-night coverage or correct variable-specific deployment semantics.

This repair preserves the old v2 producer envelope and return qualification. It does **not** add a new schema/mode, require optional metadata from existing producers, or certify an absent declaration. It closes reproduced contradictions: owner-capture/case-alias target names, explicitly label-role sources, late readiness, and valid-time outside the forecast window. The synthetic regression first returned two rows for each contradiction and now rejects them.

Independent review reproduced two further ambiguity/path escapes. Every JSON object now rejects duplicate keys during decoding, including nested metadata, universe rows, references and feature `values` row IDs. A matching raw SHA cannot authorize conflicting duplicate declarations: `source_role=label` followed by `source_role=feature`, a late readiness followed by an earlier duplicate, or outcome-bearing metadata overwritten by `{}` all reject before interpretation. The decoder checks the shared deadline while building each object, rather than accepting Python's last-key-wins interpretation.

Before every source read and final rescan, the local wrapper calls the reviewed `master_inventory.local_path` guard, with deadline checks before and after. The shared guard checks every absolute ancestor (including ancestors above the supplied root) and descendant for symlinks, Windows junctions and other reparse attributes, then requires the resolved source to remain under the resolved root. It does not import the private development-cycle validator or change shared path contracts. Actual Windows regressions cover an initially external `features` junction, substitution during the final rescan, and a junction above the supplied workspace root. The ancestor case rejects before any `Path.open`. Tests remove only the verified temporary junction with `os.rmdir`, preserve its external sentinel, and retain POSIX symlink regressions for Linux. These checks reject observed path indirections; they do not make path checking/opening atomic against a hostile concurrent replacement process.

Each source read is bounded to 128 MiB and all distinct consumed raw inputs to 384 MiB, using bytes actually read rather than a prior file size. A bounded read may read one extra byte solely to detect and reject an overrun. The final recheck uses the same bounded limits with a separate scan budget. There may be at most 32 feature sources (34 consumed files including snapshot/universe), 2,000,000 universe rows and 400,000 joined numeric cells (`row count × feature reference count`). Feature count is checked before opening the universe; the cell count is checked before allocating output rows or reading feature sources. The feature cap follows the suggested 32-expanded-column engineering ceiling in `docs/plans/master-goal-1642-feature-models.md`; this validator does not implement model transformations. The cell cap is a conservative preproduction engineering limit: the original synthetic 2,000-row × 200-feature join (about 5 MB raw input) used approximately 86.5 MB additional peak RSS in the review environment. That original feature count now exceeds the stricter source cap. A six-window, 101,940-row universe with three numeric features fits the cell cap (305,820 cells); this capacity example establishes no scientific forecast performance. These limits bound multiplicative expansion, not total process memory; JSON/metadata and runtime overhead remain additional costs. Larger workloads require a separately reviewed streaming/storage design.

Validation uses a monotonic elapsed deadline, default 30 seconds. `budget_seconds` must be a finite positive number at most 300 (booleans are invalid), respecting the existing parent command's 300-second ceiling. A parent caller must supply its smaller remaining allowance rather than starting an independent budget. Checks occur around bounded source reads, hashes, JSON parsing/canonical validation, each metadata node, universe row, feature/join cell, and final recheck. Expiry raises `TimeoutError` and returns no rows. Individual reads/parses/hashes are cooperative operations: byte limits bound their input, but the deadline does not OS-preempt a blocking read or interrupt a single parse/hash. It detects expiry at the next check and prevents a successful return; it is not a hard real-time guarantee.

SHA-256 checks compare the exact raw bytes parsed for each source and sequentially recheck all consumed files immediately before returning. Returned rows are derived from hash-verified in-memory input bytes. The sequential filesystem recheck is **not an atomic snapshot**: a concurrent writer can change an already checked file while a later file is checked, or change a file after its check. A detected change rejects validation; successful validation makes no simultaneous-filesystem-state guarantee. An atomic publication boundary requires independently immutable/content-addressed storage or coordinated writer locking. A matching hash proves byte consistency only; it does not prove that a source was genuinely available before the historical cutoff, or that weather, GIS and capture-pressure measurements are authentic.

## Remaining production gate

1. Bind independently acquired, provenance-verified current environmental and road/terrain features and a full-scope prospective Universe. No backfilling of time/source or use of observed GPX as future-road universe.
2. Implement the registered feature-aware model adapter and its independently validated Champion/approved baseline. Integrate this validator into issuance using model identity and code closure, not merely a caller-provided feature list.
3. Add verified time-target generation, count/activity/detection applicability, A/B/C topology-constrained routes and their own evidence.
4. Complete Task8's trusted production registry, scientific reproduction, exact-head CI/review and immutable ORIGINAL publication. Validate an actual future-night E2E run. **Only then** issue official P0.

Until these are met: `PROVISIONAL_NOT_FREEZABLE`. Synthetic passes are development evidence only.

## G0 model-input compatibility remains blocked

Audited policy reference: current main `c39e6d86489348a925217460c3c98709f513c613`, `protocols/development/g0-policy-v1.json`, and `docs/work/G0_CONTRACT_20261025.md`. The v2 validator remains an integrity-only preproduction gate, **not** a G0-qualified model-input adapter. Its return does not authorize fitting, scientific evaluation, confirmation, production Champion inference or P0. Required next-slice blockers are:

- Complete source/derivation closure with all four required readiness timestamps (`source_received_at`, `derived_at`, `materialized_at`, `audited_at`) and conservative `usable_at=max(required readiness)` for every consumed source and derived artifact. Optional supplied timestamps checked here are not that closure, and matching hashes do not authenticate historic receipt times.
- Required per-source roles and independently audited feature/source/derivation bindings; generic numeric feature artifacts or a role declaration alone cannot turn label/actual-GPX evidence into predictors.
- Mandatory feature definitions/units/version/code identity, physical valid-time at the appropriate row/window resolution, and forecast-versus-measured/deployment semantics. Optional global `valid_from`/`valid_until` checks do not supply missing scientific definitions.
- Independently verified complete candidate domain/horizon and a bounded full shard-set coverage contract. Existing all-row feature joins, 100m/600s uniqueness, 32 features, 400,000 numeric cells and 2,000,000 rows stay unchanged. A six-window shard is not a full-night universe, and out-of-universe outcomes remain part of V's independently complete denominator.

That strict G0 adapter and coordinated producer migration require their own reviewed bounded slice. Existing #33/#46 producers can still obtain only `PREPRODUCTION_INPUT_INTEGRITY_ONLY` from this API; absence of the above contracts is not scientific permission. No raw file, ORIGINAL, model, workflow, shared state or production authority is modified by this repair.

## Additive strict G0 forecast declaration API

`src/g0_forecast_contract.py` adds two distinct read-only entrypoints:

```python
validate_g0_forecast(root, manifest_ref, operational_night, as_of,
    expected_feature_definition_sha256=registered_definition_digest,
    budget_seconds=30.0)  # complete validation receipt, no rows
load_g0_forecast_rows(root, manifest_ref, operational_night, as_of,
    expected_feature_definition_sha256=registered_definition_digest,
    budget_seconds=30.0)  # {receipt, rows}, complete bounded collection only
```

The caller must bind the registered recipe's strict definition digest. Passing the
old names-only digest cannot establish strict definition identity. Neither API
fits or evaluates a model. All receipts retain `fit_authorized=false`,
`scientific_execution_authorized=false`, `production_authorized=false`, and
`source_authenticity=NOT_ATTESTED`. Qualification is
`STRICT_G0_FORECAST_DECLARATION_VALIDATED`: hash/metadata consistency is neither
historic receipt authentication nor proof of scientific feature semantics.
Legacy `load_prospective_inputs` remains unchanged in qualification and accepts
its existing producer envelope; it never infers this strict manifest.

The manifest schema is `habu-g0-forecast-contract-v1`. Its exact fields are
`schema_version`, `operational_night`, `cutoff_time`, `readiness`, `usable_at`,
`policy_ref`, `domain_id`, `source_nodes`, `features`,
`feature_definition_sha256`, `horizon`, `cell_partitions`, `time_partitions`,
and `shards`. Unknown fields are rejected in every defined envelope. A byte
reference is exactly `{path,sha256,size_bytes}`; a readiness-bound reference
adds exactly `{readiness,usable_at}`. Paths are portable relative paths under
`features/` or `data/processed/`; only code references may instead use
`src/*.py` or `scripts/*.py`, and only the fixed policy reference may use
`protocols/development/g0-policy-v1.json`. Raw/ORIGINAL and sealed outcomes are
not source namespaces. Duplicate JSON keys reject at every depth, even when
their exact ambiguous raw bytes have a matching SHA. Feature numbers, cell
indices, partition indices and byte sizes reject booleans; JSON nonfinite values
reject before semantic interpretation.

The fixed policy is checked by both raw reference SHA and the independently fixed
canonical digest `741ce69c523a2d5cb1e010c4ca4ff49d02682fdd644d5aa4b9b54ed87c49a97a`.
`policy_file_sha256` and `policy_canonical_sha256` are different receipt fields;
changing only whitespace changes the former. A caller cannot substitute policy.

Every source node is exactly `{id,ref,source_kind,role,allowed_use,parents,
readiness,usable_at,event_time,valid_time,source_class}`. `allowed_use` must be
`FORECAST_INPUT`. Source identifiers are bounded ASCII letters/digits/underscore/
hyphen. `source_class` is `official`, `auxiliary`, or `mixed` for derived data;
the validator derives the latter classification from raw ancestors. It rejects
a declaration that hides auxiliary ancestry as official. Every node must be
reachable from the domain or an explicit shard root and every required source
must be read, hash-checked and rescanned. This checks the declared complete
closure; it cannot discover undeclared real-world computation ancestors.

Supported source/deployment pairs are intentionally limited in this first version:

| source_kind | role | required binding |
| --- | --- | --- |
| `static` | `feature` or `universe` | parent-free static evidence, event time before cutoff |
| `forecast` | `feature` | parent-free forecast evidence, issue time before cutoff |
| `cell_domain` | `universe` | exactly the required static universe sources |
| `forecast_universe` | `universe` | exactly the declared cell-domain node |
| `feature_values` | `feature` | exact registered feature source IDs, static or forecast deployment |
| `snapshot` | `protocol` | exact universe and all required feature-value nodes |
| `validity` | `protocol` | exact required feature-value nodes |

Raw static/forecast evidence uses the exact envelope `{schema_version:
"habu-g0-source-v1",source_kind,source_class,event_time,valid_time,data}`. Its
metadata must match the source node; the opaque measurement `data` is inspected
for known outcome keys but is not scientifically authenticated by this adapter.
Actual future trajectories, held-out outcomes, sealed confirmation and untyped
target projections are rejected. Planned ex-ante effort and audited lagged
history are policy-permitted concepts; `planned_effort`/`lagged_observation`
currently raise `ForecastCapabilityError` (`CAPABILITY_BLOCKED`) because their
safe typed projection/time matrix is not implemented. This is not a policy ban.
Raw GPX never supplies the forecast universe. A future typed lagged adapter must
check past event/measurement validity before cutoff, independently of its
derived future prediction-window applicability; this version does not pretend
past raw validity covers future windows.

Every source, derived node, policy reference, feature code reference and manifest
requires all four `source_received_at`, `derived_at`, `materialized_at`,
`audited_at` timestamps. `usable_at` must equal the maximum of these and all
required parent/code readiness, and must be strictly before the actual own
prediction cutoff. No timestamp comes from file mtime. A forecast's physical
`valid_time={start,end}` must cover each complete selected prediction window;
readiness remains before cutoff even when validity is in the future.

Each feature definition is exactly `{name,units,version,definition,
definition_sha256,code_ref,deployment,required_source_ids}`. `definition_sha256`
binds UTF-8 definition text, and `code_ref` binds exact implementation bytes.
`deployment` is `static_predictor` or `forecast_predictor`; required raw source
kinds/roles must match it. The strict definition digest is canonical JSON of
definitions sorted by name, replacing each `code_ref` with just its three byte
identity fields. It covers units/version/definition/deployment/source binding and
code identity. Readiness metadata is forecast-specific and not part of the model
definition identity. The receipt preserves this `feature_definition_sha256`
separately from `legacy_feature_names_sha256=digest(sorted(feature_names))`.

The domain artifact is exactly `{schema_version:"habu-g0-cell-domain-v1",crs:
"EPSG:32652",source_class,required_source_ids,cells}`. `cells` is a sorted unique
list of physical `[floor(utm_x/100),floor(utm_y/100)]` indices. The declared
future `horizon={start,end}` is an aligned UTC-normalized half-open interval of
600-second windows, entirely within the operational night. End at the following
07:00 JST is allowed; start equal to actual `as_of` is rejected. Domain membership
is ex ante, not selected from observed GPX or positives. Coverage proves the
declared domain, not authentic completeness of island roads or an independently
complete capture denominator.

Cell and time partitions are ordered contiguous `[start_index,end_index]`
pairs covering their axes exactly. Every rectangle appears once in `shards`,
whose exact records are `{shard_id,cell_partition,time_partition,snapshot_id,
validity_id}`. Duplicate shard/node bindings, missing rectangles, gaps, overlaps
and extra rectangles reject. Inside each shard, rows follow cell-then-time order,
use exact cell centers, and canonical IDs `cell_x:cell_y@YYYY-MM-DDTHH:MM:SSZ`.
This guarantees cross-shard physical uniqueness without allocating the entire
cell×window Cartesian product or a global set of millions of row IDs.

Each shard binds the existing v2 snapshot/universe/feature bytes with their
exact base envelopes and byte sizes added to its references. Optional metadata
accepted by legacy v2 does not replace strict node declarations. The validity
sidecar is exactly `{schema_version:"habu-g0-validity-v1",feature_sources,rows}`:
`feature_sources` binds each name to its exact feature-value node ID; `rows`
binds each canonical row ID and required feature name to a physical interval
covering that complete 600-second window. Extra/missing rows or features reject.
Every legacy v2 join and its internal final rescan are also executed and charged.

No successful receipt or rows are returned before all shards and a final
rescan of manifest, policy, code and complete source closure. Sequential rescans
detect changes but remain non-atomic. Returned rows derive from checked bytes;
hostile changes after a check require immutable storage or writer coordination.
The collector projects to the exact `models.research_selection.validate_future_rows`
shape, pre-adds `cell_x`/`cell_y`, and normalizes cutoff/window/availability to UTC.
`canonical_joined_rows_sha256` hashes exactly these returned rows in shard
cell-partition/time-partition order. `snapshot_refs` preserves original snapshot
raw-byte SHAs separately. A model's normalization must preserve the joined-row
digest; original snapshot hashes cannot substitute for it. Receipt-only validation
hashes the same projected row stream but grants no model-read capability.

Limits combine by their minimum: 32 features, 400,000 joined numeric cells and
2,000,000 rows per legacy shard, 128MiB per source, and legacy 384MiB per scan
remain intact. Strict totals are at most 256 shards, 100,000 physical cells,
144 windows, 4,000,000 declared rows, 16,384 source nodes, 32,768 edges and longest
parent depth 32. Manifest/domain/policy files are at most 8MiB. All actual bytes
read, including repeated strict reads, every legacy initial read/rescan and final
whole-closure rescan, share a 2GiB cumulative ledger and one absolute deadline
(default 30s, maximum 300s). The collector additionally requires the entire
domain to fit 120,000 rows and 16MiB canonical JSON including list punctuation.
It returns all rows or raises `ForecastCapacityError` with `CAPACITY_BLOCKED`;
it never samples or truncates. Capacity is not invalid scientific evidence.
A larger receipt can pass without model support: global/conditional ranks,
candidate-unit counts and Top10 are subset-dependent, so chunk rank-and-concat
does not implement a full-domain M2 model. JSON/runtime overhead means these
limits are not a hard process-memory bound, and cooperative deadlines do not
OS-preempt a single read/hash/parse operation.

`ProspectiveReadContext(budget_seconds,max_bytes)` is the public resource seam.
It exposes one absolute monotonic `deadline`, cumulative `bytes_read`,
`max_bytes`, checked `remaining_bytes` and checked `remaining_seconds`.
`check()` raises `TimeoutError` on expiry; `account(nonnegative_actual_byte_count)`
charges actual bytes and raises `InputCapacityError` (a `ValueError` subclass)
on capacity. Bool/negative counts reject. Nested readers must share the same
instance and charge every initial/read-again/rescan, including a rejection probe's
one extra byte, rather than infer sizes from stat or reset a fresh deadline.
`load_prospective_inputs(...,_read_context=context)` keeps legacy defaults while
respecting the smaller shared deadline and byte allowance. No resource seam
authenticates bytes or grants training role/qualification.

The pure helper `validate_readiness_graph(nodes,cutoff,check=...)` accepts exactly
`{id,parents,readiness,usable_at}` nodes, returns `{ready_by_id,topological_order}`
with aware UTC datetimes/parent-first IDs, and checks the same graph caps,
cycles/missing/duplicate parents and required max strictly before cutoff. It
checks the longest ancestry path even if parents were previously cached.
It reads no files and owns no forecast/training role semantics; callers must
select their own correct cutoff, supply their shared deadline check, and enforce
source role/byte/qualification policies separately.
