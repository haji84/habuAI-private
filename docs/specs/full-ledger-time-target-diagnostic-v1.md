# Full-ledger time-target diagnostic v1

Independent design for root review before implementation. Base:
`be045334a5ede3d5b92088e86b2b4852ccc8b6a1`. This specification does not implement
or authorize a model, source loader, parent dispatch, issuer or campaign.

## Purpose and API

```python
evaluate_time_targets(universe, frozen_targets, ledger, *,
    protocol, expected_protocol_sha256, budget_seconds=30, check=None)
```

Proposed `src/time_target_evaluation.py`: pure JSON computation, one operational
night and one already-produced prediction set. No file/network access, source
qualification, target generation, fitting, winner selection or publication.
Missing inputs return NEED_MORE_DATA; they never create targets or labels.

This adds strict full-universe/ledger binding to T2. Existing
`pdca_pipeline.score_prediction` already has fixed-radius/time maximum matching;
do not duplicate that algorithm or call spatial ranks formal time targets.
HB-B2 fitting and source-bound/parent integration remain separate unmet work.
Existing calibration arithmetic and M3 count-feasibility arithmetic are reused
elsewhere, not reimplemented here.

## Exact JSON projections

Every object has exactly the listed fields; unknown fields reject. `H(x)` is
SHA256 of UTF-8 canonical JSON (sorted keys, compact separators, Unicode retained,
nonfinite numbers forbidden), not a file-byte hash. A projection's self-hash
excludes only its own hash field. Digests are lowercase 64-hex. IDs are nonempty
printable Unicode strings of at most128 characters. Numeric bools reject.
Aware ISO timestamps are compared as instants; no narrower RFC annotation.
`universe`, `frozen_targets`, and `ledger` may individually be null; protocol is
always required. No placeholder universe is constructed for missing input.

**Protocol** (`habu-time-target-diagnostic-protocol-v1`) exact fields:

```text
schema_version, phase, g0_policy_sha256, target_semantics,
operational_night, cutoff_time, horizon_start, horizon_end, scope_sha256,
universe_sha256, targets_sha256, frozen_at, time_anchor,
radius_m, tolerance_seconds, matching_policy
```

Constants: phase=`DEVELOPMENT`, target_semantics=`OWNER_CAPTURE_EVENT_POINT_TIME`,
time_anchor=`WINDOW_MIDPOINT_300_SECONDS`, radius_m=100 (exact integer),
tolerance_seconds=600 (exact integer),
matching_policy=`ORDERED_DFS_MAX_EVENT_CARDINALITY_V1`.
`g0_policy_sha256` equals existing `codex_cycle_contract.POLICY_DIGEST`.
`expected_protocol_sha256` must equal H(protocol).
`universe_sha256`/`targets_sha256` are digests or null when no binding is yet
available; any supplied corresponding projection requires its nonnull matching
binding. `scope_sha256` is always a digest. `frozen_at` is aware or null; null
is a missing declared-freeze blocker, and a supplied freeze after cutoff rejects.
Equality `frozen_at == cutoff_time` is allowed. This declares chronology only:
the hash/timestamp is not proof of pre-reveal or pre-issuance authentication.
Future outcome-ledger hashes are **not** placed in a pre-reveal protocol.

**Universe** (`habu-time-target-universe-v1`) exact fields:

```text
schema_version, operational_night, cutoff_time, horizon_start, horizon_end,
scope, scope_sha256, forecast_receipt_sha256, joined_forecast_sha256,
units, universe_sha256
```

Scope exact: `{crs: "EPSG:32652", bbox_utm: [xmin,ymin,xmax,ymax]}`; it matches
the existing Stage1 scope grammar and H(scope)=scope_sha256.
Each unit exact: `{row_id, window_start_jst, utm_x_m, utm_y_m}`.
All points are finite explicit forecast points in the half-open prior scope and
UTM domain100000<=x<900000, 0<=y<10000000. No inverse UTM, cell-origin inference,
road geometry invention or HB-B1 `CELL_ORIGIN_PROXY_NOT_POINT_GEOMETRY` promotion.
Proxy/native-rank payloads cannot substitute for this exact point projection.
Numeric alignment alone is not proxy evidence: a legitimate explicit forecast
point may lie on a grid boundary. Genuine point/source provenance remains an
upstream dependency, not something a self-hash or shape validator authenticates.
The two forecast digests bind the upstream strict forecast receipt and complete
joined rows; this pure projection does not authenticate that upstream history.
The entire supplied universe is validated, indexed and hash-bound, never
restricted to selected targets, observed cells, captures or a convenient sample.

Night is `[date 07:00 JST, next date 07:00 JST)`. Require
night_start <= horizon_start < horizon_end <= night_end and
cutoff_time < horizon_start, with cutoff in that operational night.
Units are unique by row_id **and**
`(floor(x/100), floor(y/100), UTC-normalized window_start)`.
Window starts align to600 seconds, are strictly after cutoff, and their entire
half-open600-second intervals lie inside the horizon/night. Protocol and universe
night/cutoff/horizon/scope digests must agree. Arithmetic/date overflow rejects.

**Frozen targets** (`habu-time-target-set-v1`) exact fields:

```text
schema_version, produced, model_sha256, prediction_sha256,
universe_sha256, targets, targets_sha256
```

`produced` is exact bool. Each target exact:
`{target_id, universe_row_id, predicted_time}`. IDs and selected universe rows
are unique; each referenced row must exist. Point is that row's exact explicit
forecast point; predicted_time is its window_start+300seconds and is strictly
after cutoff and within the same horizon/night. No score threshold, target
selection or coordinates are inferred from actual outcomes.
Model/prediction hashes are digests or null; null with produced=true is a missing
lineage blocker. `universe_sha256` must match the known protocol/universe binding
when produced=true. When produced=false require targets=[], and allow a null
universe binding and null lineage hashes; nonnull hashes still validate.
**produced=true with targets=[] is a valid issued abstention**, not missing
output, provided lineage/freeze and complete denominator exist.

**Ledger** is the existing exact `habu-stage1-ledger-v1`, unchanged:

```text
top: schema_version, source_refs, complete_scopes, events, ledger_sha256
ref: path, sha256, bytes
scope: operational_night, scope_sha256, horizon_start, horizon_end,
       declaration, coverage_ref, source_paths
event: event_id, operational_night, datetime, utm_x_m, utm_y_m,
       individual_ids, source_paths
```

Reuse `evaluation.full_ledger_stage1._ledger` strict validation (or a narrowly
extracted shared validator), including its source/ref/identity/count/domain
checks. Do not clone or relax the schema. Require only the protocol's night;
any supplied scope/horizon must match it even when universe is absent. With a
universe, pass a real night/scope view derived from it; without one, validate
independent supplied contradictions using the existing missing-universe path.
No default individual, inferred count or invented canonical identity.
DECLARED_COMPLETE with its existing source/coverage bindings is required for
metrics; UNKNOWN/INCOMPLETE/missing coverage is NEED_MORE_DATA. The declaration
is not authenticated issuer truth or certified real-world completeness.

## Eligibility, matching and denominators

All provided event points/time/IDs and cross-input contradictions are validated
before any NEED_MORE_DATA return. Events must be in the fixed prior geographic
scope and complete horizon, hence strictly post-cutoff. Invalid supplied events
are not silently filtered away. Every eligible scope event stays in the primary
denominator, including events outside the forecast universe.

Build the full universe key index once. For an event, floor its exact UTM point
to a100m cell and floor its JST instant to a half-open600-second window, compared
in UTC. If that cell/window key is absent from the full universe, the event is
an **outside-universe FN and has no matching edge**, even when a nearby target
is within100m/600seconds. An event in an unselected but eligible universe unit
may match a selected neighbor target by the physical tolerance below.
This eligibility condition is specific to this new diagnostic version; the old
operational scorer has no universe argument and retains its original behavior.

Order targets by target_id and events by event_id. Add an edge only for an
eligible-universe event with `hypot(dx,dy) <= 100` and `abs(dt_seconds) <= 600`.
Use exact supplied EPSG32652 points, no rounding before comparisons. This is the
same projected distance as existing `distance_m` **after** its WGS84->utm52n
projection, not a geodesic or road-network-distance claim.
Per-target neighbors sort by `(distance_m, abs(dt_seconds), event_id)`.

Use maximum **event** cardinality matching, at most one event per target and one
target per event. Ordered DFS follows those target/neighbor orders; a fresh
seen-event set is used per augmentation, with owner reassignment on successful
unwind. It does not minimize global distance or optimize individual count.
Extract/reuse a pure ordered iterative-edge helper (proposed
`src/event_matching.py`) that reproduces the old recursive owners mapping
exactly without reordering supplied neighbor arrays. The old scorer keeps its
own sorting, geometry, expansions, rounding,
signature, default behavior and whole output; no new legacy deadline or cap.

Primary: `event_recall = matched_events / complete_events`, null if zero events.
FN = complete_events-matched_events. Secondary:
`secondary_individual_coverage = individuals_in_matched_events / total_individuals`,
null if zero individuals, using the **same** event matching without count-based
tie optimization. One event with two IDs is one primary event and contributes
two individuals if matched. This is not Stage1's individual-primary recall.
Return match identities and both denominators explicitly. An issued empty
abstention scores event_recall=0 when complete_events>0, null when zero.
Unmatched targets are UNKNOWN: precision and false_positives remain null.
An anchor Negative unit does not prove ascertainment over the100m/±600s footprint.

## Bounds, completion and return

Before owned copying/building indices, preflight and reject over-cap inputs:
16MiB canonical JSON,2M JSON nodes, depth12,120000 full universe units,
100 targets,20000 events,100000 individuals,20000 source refs,2M stored edges.
Scalar strings are at most1024 characters and keys at most128; enforce specific
field bounds too. Check container width before extending the pending walk and
stop a bounded streaming encoder at the cumulative16MiB limit; no unbounded
`json.dumps` allocation before checking size.
No truncation or partial forecast/metric. Validate/index universe in O(U), event
membership in O(E); edge construction is bounded by T*E<=2M, not U*E. Check each
edge insertion before growth. Matching remains cooperatively deadline-bounded;
no hard preemption or optimal runtime guarantee is claimed.

`0 < budget_seconds <= 30`, finite non-bool number; check is callable or null.
One deadline is created at API entry; the parent callback remains active during
copy/validation/indexing/edge/matching/hash loops. A shared helper creates no new
clock. Check before and after final seal. Capacity raises a ValueError subclass
with CAPACITY_BLOCKED; timeout raises TimeoutError with RUNTIME_BLOCKED; malformed
or contradictory input raises ValueError. None returns partial metrics/matches.

Exact output fields:

```text
schema_version, status, operational_night, protocol_sha256, input_digests,
blockers, metrics, matching, unmatched_target_ids, unmatched_event_ids,
outside_universe_event_ids, precision, false_positives,
source_authentication, prereveal_authentication, statistical_adequacy,
fit_authorized, scientific_authorized, confirmation_authorized,
selection_authorized, official_100m_10min_kpi_computed,
production_authorized, receipt_sha256
```

Version=`habu-full-ledger-time-target-diagnostic-v1`;
status=`DIAGNOSTIC_ONLY` or `NEED_MORE_DATA`. input_digests exact:
`{universe, targets, ledger}` (canonical projection digests or null).
blockers is a sorted unique subset of `UNIVERSE_REQUIRED`, `TARGET_SET_REQUIRED`,
`TARGETS_NOT_PRODUCED`, `LEDGER_REQUIRED`, `COMPLETE_LEDGER_REQUIRED`,
`DECLARED_FREEZE_REQUIRED`, `PREDICTION_LINEAGE_REQUIRED`.
metrics exact when computed:
`{event_numerator,event_denominator,event_recall,false_negative_events,
individuals_in_matched_events,individual_denominator,secondary_individual_coverage,
total_targets,matched_targets,unknown_targets,outside_universe_events}`.
Each matching entry exact `{target_id,event_id,distance_m,time_delta_seconds}`;
return matches/unmatched IDs in target/event ID order. Missing/unproduced input,
freeze/lineage gaps or incomplete ledger yield metrics={} and all match/ID lists
empty, after validating all supplied known contradictions. Precision/FP are
always null. Authentication fields=`NOT_ATTESTED`, adequacy=`NOT_ASSESSED`, all
six authorization/official booleans=false. receipt_sha256 seals the whole output
except itself. No numeric result or self-hash grants formal/confirmation PASS.

## Required RED and compatibility evidence

- Greedy counterexample; exhaustive/random small graphs against original ordered
  recursive owners; permutation-invariant strict T2 assignment/metrics under
  correspondingly rebound input hashes (content hashes need not be invariant).
  Frozen original
  scorer oracle from the base, evaluated on the same runtime, must preserve whole
  outputs/assignment rather than compare cross-libm golden model hashes.
- Exact100m/600s inclusivity and just-outside values; aware UTC aliases;07:00,
  window endpoints, freeze==cutoff allowed, target==cutoff rejected, late freeze
  rejected even alongside missing data; extreme date overflow.
- Outside-U event near a target is still FN; eligible unselected neighbor may
  match; events outside fixed scope/horizon reject; full universe above cap
  blocks without sampling; no U*E scan.
- Duplicate event/individual/unit/target identities; one event/two individuals;
  equal-cardinality alternatives with different counts keep the declared
  non-count tie result and separate primary/secondary denominators.
- Produced=false vs produced=true/empty abstention with positive and zero-event
  complete ledgers; incomplete/missing projections; malformed+missing rejects;
  unknown targets never become FP from GPX or anchor-unit negatives.
- All hash/row/point/window lineage mismatches; explicit proxy/inferred geometry
  refusal; unknown fields, bool/nonfinite/recursive/oversize input; edge/copy caps,
  parent callback and expiry during matching and final output hash.

Actual strict forecast/source proof, complete capture ledger, trustworthy target
freeze, untouched confirmation and sufficient independent nights remain caller
and future source-adapter gates. September28's real5events/6individuals are not a
complete denominator or issued T2 forecast. Stage1/G0 thresholds, five-night floor,
model definitions, campaign selection, parent registry, Raw/ORIGINAL and existing
operational numerical results are unchanged by this design.
