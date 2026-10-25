# Typed planned-effort projection v1 — design for review

Base: main `699f0bda36b32caa2225d2d42962d590d561040b`, 2026-10-26.
This document proposes a standalone pure projection. No runtime, test, G0 kind,
policy, registry, source, STATE or cycle changes are included. Implementation
requires the coordinator's independent design review. No actual data is fitted.

## Current gap and reuse

PR32 is merged (`9cf729a` → `fb06f76`) and PR33 is merged (`6a177eb` →
`c0df86e`). Their strict forecast/source reader and auxiliary OSM producer are
the existing foundation, not work to duplicate. Current G0 explicitly blocks
`planned_effort` in both `_source_graph` and `_definitions`; this is a missing
typed capability, not a policy prohibition. The fixed G0 policy remains intact.

At the audited main699 snapshot, GitHub code searches found only code/spec/test
mentions of `planned_effort`; no `planned_active_search_seconds` source was
found. A tracked source-scope scan examined 363 files under data/evidence/
features/protocols/policies: 343 UTF-8 text files, excluding 20 GPX/archive files;
ten typed/Japanese planned-search markers had no matches. This is a scoped
absence finding, not proof that every owner plan or every GitHub branch was
searched. No source-qualified planned allocation is presently established.
Existing actual captures, GPX and other originals remain present and unchanged.

`count_feasibility` requires independent measured active intervals, complete
outcomes and explicit individuals. `constant_poisson_diagnostic` has only a
scalar counterfactual scenario, not a source-bound future plan. Neither can
manufacture this input, authenticate a plan or consume the new projection as
measured training exposure.

Considered approaches: generic static JSON wrapping hides the planned/actual
distinction and is rejected; route/GPX interpolation needs a separate reviewed
geometry/travel contract and is deferred. The proposed first slice parses one
fixed original plan format with explicit cell/time/seconds and only intersects
its declared active intervals with existing 100m/600s units. It adds no learner,
generic source graph, routing engine or parallel forecast pipeline.

## Proposed pure API and exact input contracts

Proposed future owned module: `src/g0_planned_effort_projection.py`, with its
own synthetic test. It is outside `src/models/`.

```python
project_planned_effort(raw_plan_bytes, domain, bindings, *,
                      expected_domain_sha256, expected_identity,
                      as_of_time, context)
```

The API performs no filesystem/network/clock-based receipt generation, fitting,
publication or parent dispatch. `raw_plan_bytes` is exact UTF-8 JSON bytes or
None. The first supported original format is deliberately narrow; free text,
CSV, route coordinates, GPX, retrospective effort projections and arbitrary
`habu-g0-source-v1` envelopes are not accepted as this format. A later parser for
a real provider format needs its own original-byte provenance review.

Domain exact fields:
`{schema_version, operational_night, cutoff_time, horizon, cells}`.
Version is `habu-planned-effort-domain-v1`; horizon is `{start,end}` and cells are
sorted unique `[cell_x,cell_y]` EPSG:32652 100m indices using existing G0 bounds
(x1000..8999, y0..99999). Domain SHA is canonical JSON SHA256 of this entire
object, compared with the caller's expected SHA and original plan's domain SHA.
This binds geometry/scope; it does not certify all island roads or car access.
Expected identity has exact `{owner_id,observer_id,method_version,crew_size}`;
it must equal the raw plan header. This is an independently passed caller
binding, not identity authentication. No owner/method is filled from outcomes.

Bindings exact fields: `{source, domain, code, projection}`. Source/domain/code
each have exact `{ref,readiness,usable_at}`, where ref has the existing exact
`{path,sha256,size_bytes}`. Projection has exact `{readiness,usable_at}`.
Source ref SHA/size must match the supplied raw bytes. Domain/code physical
refs are caller bindings, not files the pure API pretends to read. Their actual
bytes and issuer qualification remain an existing guarded-loader dependency.
Code path is fixed to this projection module; its SHA is an assertion until
an outer loader verifies the actual snapshot bytes. Original source paths are
portable and reject sealed/confirmation/ORIGINAL segments; a derived projection
cannot be reclassified as RAW by copying its path or adding a flag.
Every component also rejects ASCII trailing dot/space, colon and DOS short-name
spellings matching `~[0-9]+(?:\.|$)`, following the existing portable lexical
rule without filesystem access. Unicode and ordinary internal spaces remain valid.

Raw plan exact fields:
`{schema_version, plan_id, revision_id, issued_at, owner_id, observer_id,
method_version, crew_size, purpose, operational_night, domain_sha256, horizon,
coverage, allocations}`.
Version is `habu-planned-search-source-v1`; purpose is
`FUTURE_DECLARED_ACTIVE_HABU_SEARCH`; coverage is `DECLARED_COMPLETE` or UNKNOWN.
One owner/observer/method and exact integer crew_size1 are supported. Multiple
observers/crew are explicitly CAPABILITY_BLOCKED; this does not ban their later
typed support. IDs/text are bounded and nonempty. Revision identity is explicit;
this function cannot prove that a revision was the actual latest issued plan.

Each allocation has exact
`{allocation_id,cell_x,cell_y,start,end,planned_active_search_seconds}`.
The original explicitly declares continuous intended active Habu search in that
cell during `[start,end)`. Timestamps are aware, whole-second precision;
seconds is an exact nonboolean integer equal to end-start. A smaller claimed
duration inside a longer interval is temporally ambiguous and rejects; there is
no proportional spread/interpolation. Source seconds are checked, never inferred
from GPX points, slow motion, binary labels, event counts or monthly totals.
Each allocation requires start<end and positive seconds; a full zero plan has
an explicitly complete empty allocation list, not fictitious zero-length work.

## Physical and time rules

Normalize comparisons and output windows to UTC. Operational night is the
existing 07:00 JST day. Horizon starts strictly after actual-as-declared as_of,
as_of >= cutoff, and contains aligned 600s half-open windows inside one night;
end may equal the next 07:00. Plan/domain night and horizon agree exactly.
Cutoff/as_of may precede that operational night; only the forecast horizon is
required to lie within the declared night. A prior-night issue/cutoff is valid
when all readiness/issue bounds and cutoff <= as_of < horizon start hold.
All allocation cells must belong to the already declared domain, and all
intervals must be wholly inside its horizon. An out-of-domain allocation or
outside-horizon interval is rejected, never silently dropped or clipped away.
Only bin intersections inside an otherwise fully valid allocation are computed.

Allocation IDs are globally unique. Sort by normalized start/end and reject
any positive overlap for the one observer, across cells as well as within a
cell; timezone aliases cannot duplicate effort. Adjacent intervals are legal.
No invented travel time, road transition or route feasibility is inferred.
One observer has at most600 planned active seconds per unit and at most the
horizon's wall-clock seconds overall. Multi-crew addition is not implemented.

For unit u, output seconds is the exact sum of durations of intersections of
its 600s window with valid allocations to its cell. A source's exact seconds
must equal the sum of its bin contributions. Example: a continuous declared
20:05–20:15 allocation of600s contributes300s to each adjacent window. No
uniform-use assumption is made about a partly active interval: such a source
must explicitly supply its active subintervals instead.

Readiness uses the existing four fields and public
`g0_forecast_contract.validate_readiness`; fixed source/domain/code dependencies
use its parent maximum rather than a new generic DAG. Source issue is strictly
before cutoff; every raw source readiness stage is >= issue and < cutoff.
Domain/code readiness is also strictly before cutoff. Projection own stages
cannot precede plan issue; its effective usable_at is max(own four, source,
domain, code usable times), strictly before cutoff. Missing/contradictory
readiness rejects. Valid known late availability is DATA_BLOCKED, not backdated.
Future planned interval end is not a measurement-completion lower bound: this
is declared intent, unlike actual measured effort's causal chronology.

## Complete output, zero and failure meaning

Success status is `DECLARED_PLAN_PROJECTED`, never G0-qualified/authenticated.
Return one new sealed JSON result with version, source/ref/plan/revision IDs,
domain and raw source SHA, fixed recipe/code bindings, night/cutoff/as_of,
readiness/usable_at, full rows, counts, blockers, limitations and authority flags.
Fixed recipe is `SUM_EXPLICIT_ACTIVE_INTERVAL_INTERSECTIONS_SECONDS_V1`;
feature is `planned_active_search_seconds`, unit seconds for one observer.

Rows cover the complete declared cell×window product in G0 cell-then-window
order. Each row has exact `{row_id,operational_night,cell_x,cell_y,
window_start_utc,planned_active_search_seconds}` with existing canonical physical
ID `cell_x:cell_y@YYYY-MM-DDTHH:MM:SSZ`. A value describes the whole 600s window,
even when intended activity occupies only part of it. This standalone shape
is not accepted by a model/G0 API as a feature snapshot.

Zero is permitted only for a known full plan: DECLARED_COMPLETE explicitly
means its allocation list is the entire plan for this domain/horizon. A unit
without an allocation then has zero *planned* seconds. Missing raw bytes or
UNKNOWN plan coverage returns NEED_MORE_DATA, rows=[], no invented zero table
or partial totals. Supplied known contradictions still reject first. Planned
zero never establishes actual non-search, a Negative label, capture absence,
measured exposure, a Poisson training denominator or a complete outcome ledger.

Malformed/duplicate JSON or schema, hash/scope/seconds conflict, boolean/nonfinite
numeric data, unknown fields, actual outcome/GPX payloads, duplicate/overlap and
out-of-domain allocations raise ValueError. Missing source/unknown coverage or
valid late availability are DATA_BLOCKED. Capacity/expiry are explicit separate
resource failures with no partial result. Missing code/domain/readiness is not
a healthy optional field; schema violations are not disguised as source absence.

The result self-hash covers all fields except itself, checked through final
return. Raw SHA is physical bytes; domain/recipe/result SHAs are separately
named canonical digests. No generic `trusted`/`is_plan`/issuer boolean is accepted.
An internally consistent manufactured JSON plan remains an unauthenticated new
declaration: bytes, claimed times and hashes never prove owner signature,
historical availability, actual issuer or pre-reveal freeze.

## Resources, shared transport and remaining boundaries

Require the existing `ProspectiveReadContext`; use its check throughout hashing,
bounded parsing/copy, sorting, every allocation/bin/row, encoding and final seal.
No independent deadline class or fresh per-shard budget is introduced. Callers
that load files use existing G0ArtifactReader with this same context and its
actual byte/rescan ledger; they retain the <=300s/2GiB outer limits. Pure parsing
of already supplied bytes does not fabricate or double-charge file reads.

Before owned copies: raw plan <=4MiB; raw+domain+bindings combined <=16MiB;
JSON <=2million nodes/depth12, strings<=4096/keys<=512; allocations<=20000.
Include expected identity/as_of/expected SHA in the combined preflight. For raw JSON, a checked
lexical token/depth/string/number-length scan must precede decoding/allocation;
number tokens are <=64 characters before conversion to Python numbers.
do not first json.loads an unbounded token and only inspect its tree afterwards.
Reject duplicate keys at every level and check the shared deadline immediately
before/after decoding. For existing JSON objects, bound pending-node insertion
before copying; no bulk allocation is allowed to precede capacity checks.
Retain G0 domain ceilings100000cells/144windows/4millionrows, then apply this
first whole-table collector's stricter <=120000rows and <=16MiB output cap.
Check the Cartesian row count before building it. All caps apply together;
there is no truncation, sampling or shard concatenation. The archived OSM
16990×72 full night exceeds this collector and is explicitly CAPACITY_BLOCKED.
Larger all-shard publication is a later capability, not implied by this design.

Always retain NOT_ATTESTED source authenticity,
CALLER_DEPENDENCY_REQUIRED source/issuer/availability authentication and
NOT_ASSESSED scientific/statistical validity. Fit, science, selection,
promotion, confirmation, official and production authority flags are false.
This slice leaves G0 planned_effort CAPABILITY_BLOCKED, does not alter the
three-candidate registry and does not connect count/parent inference. Planned
data cannot be relabelled as static/forecast or actual observation effort.

Any later G0 adapter must reuse the existing guarded reader/final rescan and
explicit source/deployment closure with reviewed original format/namespace,
current raw/code/policy availability and required full-shard validity; it may
not hide original ancestors in a processed JSON wrapper. Any later count
forecast remains conditional on the frozen declared plan, separately checks
measured training effort/complete outcomes, and reports adherence separately.
Outside-universe confirmed captures remain in the independent full-scope FN
ledger even when planned effort was zero; plans cannot shrink that denominator.

## Synthetic acceptance cases after approval

Test raw physical/canonical SHA separation, duplicate keys/unknown fields,
one600s interval crossing a bin edge, split adjacent intervals, explicit full
zero plan versus UNKNOWN/missing, zero-not-Negative, all four readiness equality
and causal issue bounds, wrong night/07:00/endpoints/timezone aliases, duplicate
IDs, same-observer cross-cell overlap, crew/method/owner mismatch, outside-domain
allocation rejection, no output on any missing/extra row or resource failure,
precopy/copy/encode/final-seal expiry, owned-input mutation and no I/O. Bind a
small complete domain by source hash and preserve all actual original bytes.
Run existing G0 planned/lagged rejection and count-feasibility tests to prove
that the standalone projection does not open either authority boundary.

Current design-only verification: the existing G0 planned/lagged capability
test plus31 count-feasibility tests pass (32 tests,0.426s). This executes no
new projection implementation and establishes no planned-source availability.

## Coordinator approval — 2026-10-26

Root independently reviewed exact16d67b9 and approved standalone TDD
implementation in the new module/test/review only. G0/policy/source/STATE and
actual-fit boundaries remain unchanged. Clarifications superseding the draft:
raw JSON numbers are integers only (no bool/float/nonfinite), with at most20
digits per integer token before decoding. Domain/code physical byte refs remain
unverified by the pure API; domain canonical SHA and raw plan physical SHA have
distinct meanings. None/UNKNOWN must not hide known structural/time/scope
contradictions. Source/issuer/readiness declarations never authenticate themselves.

After independent exacte7193c1 review, root approved the portable lexical
repair and local datetime-overflow normalization (ValueError for unsupported
domain ranges, without wrapping caller callback exceptions). Root also removed
the implementation's extra same-night cutoff restriction; the horizon-only
operational-night and strict readiness/issue requirements above remain binding.
