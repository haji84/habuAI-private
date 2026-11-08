# Source-bound development Stage1 adapter

Base `71f04564e8c200b7dc2cd8bd595310ed6de7242c`. This connects the existing
pure full-ledger evaluator to the existing development-only research request.
It does not change model recipes, G0 schemas, evidence policy or scientific gates.

## Request and execution order

The original `habu-research-model-request-v1` keeps its exact ten fields and old
behavior. Explicit `habu-research-model-request-v2` has those fields plus
`stage1_manifest`, an exact `{path,sha256,size_bytes}` byte reference. Sources
are not implicitly discovered. No sealed/confirmation path is permitted.

Training and strict forecast validation, and preparation/hash binding of the
same three candidates, finish before any evaluation outcome payload is opened.
The opt-in adapter then reads its separate source manifest. This initial parent
connection evaluates the single requested development night. It does not create
a multi-night fitting/selection driver or new confirmation workflow.

`evaluate_stage1_sources(root, manifest_ref, forecast, prepared, *, context)`
uses the parent's existing `ProspectiveReadContext` and `G0ArtifactReader`.
The pure evaluator gains only an optional `check=None` callback; all original
numeric behavior and its default API remain unchanged. The shared callback is
checked throughout projection, bootstrap, hashing and return, in addition to
the pure evaluator's existing local upper bound.

## Source manifest

The exact manifest fields are `schema_version`, `purpose`, `operational_night`,
`evaluation_as_of`, `forecast_manifest_sha256`, `joined_universe_sha256`,
`scope_id`, `captures_id`, `individuals_id`, `coverage_id`, `source_nodes`,
`readiness`, `usable_at`. Version is `habu-stage1-source-contract-v1`; purpose
is `DEVELOPMENT_EVALUATION_ONLY`. Root IDs may be null to describe missing
inputs; contradictory supplied values still fail validation.

Each node has exactly `id`, `ref`, `source_kind`, `role`, `parents`, `readiness`,
`usable_at`. Roles are `scope`, `captures`, `individuals`, `coverage`, `support`;
kinds are `RAW` (no parents) and `DERIVED` (explicit nonempty parents).
These are declarations, not evidence of an authenticated original issuer.
References and node IDs are unique; all nodes must be reachable from the four
declared roots. The existing shared readiness DAG checks four readiness times,
their parent maxima, cycles, depth, edges and node budgets. Source and manifest
readiness must be strictly before the separate `evaluation_as_of`.

This first contract restricts an outcome/individual/coverage lineage to actual
observational RAW/derived records. Standing policy and generic `support` nodes
cannot occur in that closure; a future typed non-observational prerequisite
contract would be needed to support that composition. Prior scope/support
closure is separate and ex ante. Every one of the four readiness stages for
the captures/individuals and all observational ancestors must be at least the
latest actual record timestamp. Coverage and its ancestors must also follow
the actual records in its exact CSV references, including UNKNOWN/INCOMPLETE
declarations with no listed IDs. Complete coverage additionally follows horizon
end. The manifest's four own stages cannot predate those bound observations.
Later audited/usable times cannot hide a pre-event source-received timestamp.

All scope ancestors must additionally be ready strictly before forecast cutoff.
Development outcome/individual/coverage sources may arrive after the event and
forecast cutoff but before evaluation. They never become prospective predictors.
Runtime namespaces are the already-snapshotted `data`, `evidence`, `features`,
`policies`, `protocols/development`, `src` and `scripts` namespaces. `incoming`,
`reports`, predictions/ORIGINAL and sealed/confirmation components are rejected.
All declared references are preflighted before opening any source payload.

The scope JSON has exact fields `schema_version`, `operational_night`,
`cutoff_time`, `horizon_start`, `horizon_end`, `scope`. Version is
`habu-stage1-scope-source-v1`. Scope is the pure evaluator's exact EPSG:32652
half-open `bbox_utm`. It contains every forecast unit, matches the forecast
night/cutoff and the entire bounded forecast horizon, and was available before
cutoff. It is not inferred from captured/observed rows. There is no automatic
conversion of an EPSG:4326 coverage box into a larger UTM completeness claim.

Capture and individual sources use the existing canonical CSV columns:

- Captures require `event_id`, `operational_date`, `event_time_local`,
  `event_type`, `event_count`, and one explicit coordinate pair: `latitude`,
  `longitude`, or `utm_x_m`, `utm_y_m` in EPSG:32652. Event type is capture,
  count is an explicit positive integer. Existing coordinate conversion is
  reused for WGS84 actual points, without changing scope geometry; a supplied
  UTM pair is checked directly. Supplying both pairs is rejected as ambiguous.
- Individuals require `individual_id`, `event_id`, `individual_index`,
  `operational_date`, `event_time_local`. IDs are explicit and globally unique;
  each event's exact count, timestamp, night and indices are cross-bound.
  An event with two linked IDs contributes two individuals. No ID is invented.

Duplicate headers, ragged rows, nonfinite/bool-like coordinates, incorrect
07:00 nights, duplicate/conflicting IDs, missing counts or links are invalid.
All rows are validated, including rows outside the selected scope/horizon.
Only the predeclared scope/horizon selects denominator membership. An eligible
individual inside scope but outside the forecast universe remains a miss.

Coverage JSON has exact fields `schema_version`, `declaration`,
`operational_night`, `scope_sha256`, `horizon_start`, `horizon_end`,
`captures_ref`, `individuals_ref`, `event_ids`, `individual_ids`. Version is
`habu-stage1-coverage-source-v1`; declaration is `DECLARED_COMPLETE`, `UNKNOWN`
or `INCOMPLETE`. It binds the exact scope, horizon and both source byte refs,
and its IDs equal all source-selected events and individuals, not the subset
of forecast cells. Completeness is an explicit source assertion; absence of
a capture line, an empty table or a list of known positives does not prove it.

## Projection, result and persistence

The complete strict forecast rows determine every candidate's area set.
The existing Task6 arithmetic mean of all native unit scores per 1km area is
used for all candidates. HB-B1's `rank_score_diagnostic` remains a rank score,
not a probability. Model/prediction hashes, row IDs, geometry, night, window
and joined-universe identity must match the prepared set. Uniform remains first;
no extra candidate, selection rule, observed-only filtering or new fit is added.

Missing/noncomplete sources yield `NEED_MORE_DATA`, empty per-night/pooled/
uncertainty metrics and specific blockers. Candidate preparation remains useful.
This includes a nonnull node reference whose file is absent: only the existing
transport's exact missing-input exception is classified as missing. Supplied
malformed metadata, wrong source bytes or causal contradictions still fail.
An absent top-level request/manifest cannot establish this contract and retains
the parent's existing input-block behavior. Missing scope does not exempt other
supplied coverage from its schema, timestamp, source-ref and known-ID checks.
Invalid supplied declarations fail the opt-in request with no new REPLAY.
Budget/capacity exhaustion returns a runtime block with no metrics. Complete
inputs invoke the existing pure evaluator, preserving its individual numerator/
denominator, outside-universe misses, seed 0 / 2,000 paired NIGHT draws and
five-night-floor/adequacy warnings. A one-night diagnostic is insufficient.

The result is `DECLARED_CONSISTENCY_ONLY`, with source authentication
`NOT_ATTESTED`. All official, scientific threshold, confirmation, selection,
promotion, fitting and production authority flags remain false. Even perfect
diagnostic recall is not a formal Stage1 pass. Existing September28 five events/
six occurrences have no complete denominator and must remain NEED_MORE_DATA.

The parent includes this result and its byte/readiness/projection receipt in
the existing single immutable content-addressed REPLAY. All training, forecast
and evaluation sources are rechecked with the same guarded reader before
publication. No independent deadline or byte ledger is created. Existing caps
are preserved, and row/node/byte bounds are checked before collecting copies.

For v2, stage construction and its budget check precede publication. A late
failure removes only a new link owned by that invocation. Windows opens a
DELETE/attributes handle, compares its file-descriptor device/inode identity
and sets disposition on that same handle. POSIX pins every ancestor with
`O_DIRECTORY|O_NOFOLLOW`, atomically claims the public leaf into a new private
0700 quarantine and compares the claimed inode before deletion. A foreign claim
is restored with a no-replace hardlink if possible; its quarantine link is
retained with explicit original/recovery paths, even when restoration is
contested. Interrupted claims retain and report recoverable bytes. Pre-existing identical
REPLAYs are retained. If safe ownership cannot be re-established after a path
replacement/reparse, no success is returned and an untrusted-residual warning
is reported; cleanup does not delete the replacement. The v1 output and order
are unchanged. Cooperative checks bound controlled work; they do not constitute
OS-level process preemption or immunity to adversarial live filesystem races.
Private-quarantine ownership is a local cooperative-process boundary, not
general confinement against another process with the same user privileges.
Unsupported handle/dir-fd deletion fails closed with a residual; there is no
v2 fallback to public-path check-then-unlink.

The public adapter requires outputs from the existing strict G0 loader and
fixed3 preparer. It owns bounded JSON snapshots, rechecks prediction/model
digests and every predicted unit, and reads the strict forecast manifest again
to bind horizon. This joins those upstream guarantees, not an alternative G0
validator or an original-issuer authentication mechanism.
