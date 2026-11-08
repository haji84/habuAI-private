# Remaining original-plan route calculation and execution diagnostics

Continuation in the existing PR155. This implements conditional calculations already required by Master1642. It selects no actual route, production policy, storage layout or biological target, and does not authorize navigation or issuance.

Owner: pr151_final_review in an isolated lane from dc6e882. Four paths only: new `src/route_execution.py` and its tests, existing `src/route_planning.py` and its tests. A different reviewer checks the result. Root owns shared metadata, immutable code Freeze and exact-head CI.

## Entry points and native reuse

`diagnose_route_execution(original, execution, *, policy, budget_seconds=30)` and `reroute_remaining_plan(original, execution, *, policy, budget_seconds=30)` accept exact bounded builtin JSON. Original includes raw graph, native original decision, graph/route policies and the advertised deterministic original prediction SHA. Recompute the actual original native route result and require that SHA; supplied computed routes are not accepted.

Refactor the existing planner behind its unchanged v1 API into fixed private preparation and execution helpers. Construct the actual native graph and Gamma unit output once. Share one elapsed deadline and cumulative solver/work counters across original verification, diagnostic geometry and remaining-plan calculation. Ephemeral prepared graph state is never a public input or serialized prediction port. Preserve complete deterministic v1 outputs/IDs; only actual elapsed duration is volatile.

## Execution declarations

Selection and normalized-GPS observation sources contain exact raw UTF-8 JSON, physical byte size/SHA and all four readiness times. Check duplicates, finite values, depth, capacities and source/time lineage before use. They remain declared-source consistency, not source or owner authentication. Bind the actual original prediction SHA and selected A/B/C route SHA. Do not read any observation or source available after update-as-of. Selection must precede the observations used.

Current state is explicitly ARRIVED_VIA_EDGE or UNSTARTED_STATIONARY. Arrival binds actual preceding/current observations to real endpoints of the actual incoming directed edge under explicit accuracy, distance, age and gap limits. Preserve that edge as the initial turn state. No nearest-node snap, invented bridge, GPS interpolation or inferred map-matching/travel proof. Unknown position precision or incoming history blocks reroute admission. Unstarted stationary state requires the original start and a consistent explicit stationary declaration; it is not an authenticated absence of travel.

## Versioned remaining-plan semantics

The v2 result retains the original model, source cutoff, original owner-plan bytes, allocation IDs/times, graph/profile and return destination. It changes only the declared current start, incoming edge and departure clock. A return requirement keeps the original endpoint even when the new start differs; do not flip the v1 flag or move the endpoint. Keep previous-edge state through dwell and the first turn.

The deadline is **ORIGINAL_WALLCLOCK_DEADLINE**: min(original departure + original budget, forecast end). Waiting or restarting never renews that budget. Started/past allocations are skipped. Units spanning past and future cannot receive their original full mean, partial mean or a resealed subset plan. Conditional remaining offers do not renew owner intent, change the model, account for biological depletion, or create Pn. Current closures, hysteresis/switch recommendations and real navigation remain separate gates.

## Diagnostic scope and verification

Bounded point-to-selected-planned-edge distances use the existing UTM geometry. Return sample counts, within-threshold counts and unresolved values only. This is not continuous/topological/time adherence, active Habu search, measured search effort, capture outcomes or Negative labels. Unselected alternatives have actual outcomes NOT_OBSERVED. Biological and causal benefit remains NOT_VALIDATED.

The exact explicit policy owns association/proximity limits and JSON/point/native-work/time caps; no actual scientific default is selected. Test v1 parity, actual native reuse, original hashes, return/NO/ONLY state, exhausted original deadline, future observations, stale precision, mixed allocations, immutable inputs, unknown diagnostics, callback/type/capacity rejection and no I/O. All source/scientific/navigation/official/production authority flags stay false. Independent review and a new full Freeze/CI are required before publishing the source checkpoint; no real-field E2E is claimed.
