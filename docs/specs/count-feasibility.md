# Pure count feasibility v1

Approved bounded M3 contract, 2026-10-25. This is a declaration-consistency
diagnostic, without count fitting, rates, parent dispatch or scientific authority.
It does not replace HB-A1 or historical M0–M3. Existing binary selection retains
event IDs but discards individual counts, measured effort and row source scope.
Stage1's 1km/night ledger is not an active-search 100m/600s count dataset.

## Interface and exact contracts

`assess_count_feasibility(selection, count_projection=None,
effort_projection=None, *, budget_seconds=30, check=None)` returns a new JSON
diagnostic. It reuses `research_selection.validate_selection` and its identity.
The fixed target is
`OWNER_CAPTURED_HABU_INDIVIDUALS_DURING_MEASURED_ACTIVE_SEARCH`, never encounter,
abundance, detection probability or unmeasured total Habu activity.

Both projections have exact keys: `schema_version`, `selection_sha256`,
`corpus_sha256`, `target`, `owner_id`, `observer_id`, `method_version`, `units`,
`source_nodes`, `readiness`, `usable_at`, `rows`, `projection_sha256`.
Count schema is `habu-count-ledger-projection-v1`, units `individuals`;
effort schema is `habu-active-search-effort-projection-v1`, units
`active_search_seconds`. SHA is the canonical digest of all fields except
`projection_sha256`. Owner/observer/method must agree across projections.

Each node has exact `id`, `ref`, `source_role`, `source_kind`, `parents`,
`readiness`, `usable_at`. Ref is `{path,sha256,size_bytes}`. Kinds are `RAW` or
`DERIVED`. Count roles are existing corpus `label` and `complete_outcome`;
effort roles are `search_evidence` and `active_search`. Event and individual
references require label nodes, complete scopes require complete_outcome nodes,
measurement references require search_evidence nodes and active scopes require
active_search nodes. A label source may support both event and individual data.
Every source path/hash/received time must bind the selection's global manifest.
Missing registration is NEED_MORE_DATA; known-path conflicting hashes/times,
unknown node IDs, aliases between families, forbidden/sealed paths and role
contradictions are invalid. All declared nodes must be used by a row or ancestor.

Common unit keys are `{row_id,night,cell_x,cell_y,window_start_jst}`. Each
projection must cover every accepted selection row once, with exact physical
100m cell/night and UTC-normalized 600s window. Missing rows need more data;
extra/duplicate rows are invalid. Count row adds `count`, `events`,
`individual_source_ids`, `complete_scope`. Each event has exact `event_id`,
`event_time`, `individual_ids`, `outcome_source_ids`. Effort row adds
`active_search_seconds`, `active_intervals`, `measurement_source_ids`,
`active_scope`. Event IDs exactly cover the selection's IDs, but individuals
come from the separate ledger. Explicit count must match the explicit individual
ledger: one event with two individuals is count two. No missing count is filled
from event IDs, individual IDs, binary labels or monthly totals. Global duplicate
event/individual IDs and contradictory binary/count claims are invalid.

Each scope has exact common unit keys plus `owner_id`, `observer_id`,
`method_version`, `declaration`, `active_intervals`, `source_ids`.
Outcome declaration is `DECLARED_COMPLETE` or `UNKNOWN`; search declaration is
`DECLARED_ACTIVE_SEARCH` or `UNKNOWN`. Neither declaration authenticates anything.
Intervals have exact `{start,end}`, normalized UTC half-open, sorted/disjoint,
nonempty and wholly within the unit. Measured seconds are explicit, finite,
nonboolean and equal the interval durations. Complete outcomes must cover all
active intervals, including for positives. Adjacent complete-scope pieces jointly
cover a measured interval; gaps do not. Every event must lie in an actually
declared measured active interval and its declared complete-outcome scope.
One global owner/observer/method is declared: active intervals cannot overlap
across different selected rows/cells, even under equivalent timezone spellings.
This rejects duplicated exposure without inferring travel time or road geometry.
Actual event coordinates are not re-attested:
`EVENT_GEOLOCATION_NOT_REATTESTED` is always a limitation.

Null count/individual IDs/effort/scope, zero effort or missing independent scope
returns NEED_MORE_DATA, without zero imputation or partial fit rows. Provided
structural/temporal/source contradictions raise ValueError, even alongside
missing data. All four readiness times and parent max must be strictly before
the fit cutoff using the shared pure readiness graph. Event evidence cannot be
ready before its event, measurement/scope evidence before measurement/scope end.
These causal lower bounds apply to each of the four own stages and propagate
as a maximum through all actual-observation RAW/DERIVED ancestors in one reverse
topological pass. A later derived receipt cannot launder impossible early raw
bytes. Unknown/missing counts cannot hide known unbound source nodes, source
conflicts, or a declared event outside its complete scope.
Finalization after an observation is allowed before fit; these retrospective
effort intervals are never exposed as P0 features or forecast universe inputs.

## Bounds and meaning

The selection and both projections together are preflighted to 16MiB before
owned copies. Limits: 20,000 rows/events, 100,000 individuals, combined 16,384
nodes / 32,768 edges / depth32, and 1,000,000 cumulative raw-SHA ancestry
memberships. Every insertion checks deadline/cap before allocation; no bulk
union/update can bypass it. Input copy, encoding, DAG, row checks, canonical
seal and final return share the same elapsed deadline (default30s, maximum300s)
and optional stricter caller check. No filesystem/network/sealed-data read occurs.
Non-JSON/cyclic/nonfinite/boolean numeric/unknown fields fail closed; no caller
input is mutated. Capacity errors are distinct from missing scientific evidence.

Complete nonempty declarations return `DECLARED_CONSISTENCY_ONLY`, not eligible
or authenticated. Other valid incomplete requests return NEED_MORE_DATA. Always:
`source_authenticity=NOT_ATTESTED`,
`source_authentication=CALLER_DEPENDENCY_REQUIRED`,
`statistical_adequacy=NOT_ASSESSED`, and fit/scientific/official/production
authorization false. Binary selection class/night thresholds do not establish
count adequacy. No Poisson/NB model, exposure rate, fitted parameters, scientific
success, fourth candidate or integration permission is returned.

## Implementation plan

Goal: enforce the approved pure declaration interface in the three owned files.
Architecture: existing selector identity → new explicit count/effort projections
→ bounded pure readiness/lineage and unit checks → diagnostic only.
Tech stack: Python standard library and existing pure selector/readiness helper.

- [x] Add synthetic count/effort fixtures and failing tests in
  `tests/test_count_feasibility.py`, including two individuals in one event,
  complete zero versus unknown, aliases, duplicates, fit equality and scope.
- [x] Implement `src/models/count_feasibility.py` with the shared pure helpers,
  combined preflight/deadline and per-insertion lineage cap; make targets green.
- [x] Test no file/network/mutation, cap/deadline failures during encoding and
  final seal, positive-only declarations without statistical adequacy claims.
- [ ] Run count tests plus existing selector/readiness regressions; independent
  exact-commit review, then coordinator-owned main reconcile/CI/integration.

## Bounded worker verification

The missing-module RED was recorded before implementation. Explicit regression
REDs were also recorded for cross-cell overlapping effort, orphan source masking,
adjacent scope union, ancestor causal bounds, and oversized numeric budgets.
The final worker run passed 31 count tests plus 74 existing selector/readiness
tests (105 total, 3.480 seconds). Worker execution of the external independent
hostile harness passed all 52 probes. Exact-commit independent review and Linux
CI remain coordinator obligations; none of these synthetic checks qualifies
historical count/effort evidence or authorizes fitting.
