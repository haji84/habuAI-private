# Detection opportunities and node-topology graph implementation plan

> For agentic workers: use subagent-driven development, TDD, independent review and exact-head verification. This implements the already-approved Task6c specification; it grants no new scientific, navigation, main or production authority.

**Goal:** execute the remaining independent-opportunity detection mathematics and real-node road topology conversion without inventing truth, negative labels, connections or passability.

**Architecture:** two pure bounded modules consume closed source-bound JSON, explicit protocol values and a single deadline. They produce research calculations and precise missingness. Existing numerical/source helpers are reused only where their actual semantics agree. Root alone integrates metadata/Freeze/GitHub, using the same PR155.

**Tech stack:** existing Python3.12 analysis profile, NumPy2.2.6/SciPy1.15.3/scikit-learn1.5.2. No dependencies, workflows, new services or permissions.

**Spec:** `master-goal-1642-output-routes.md` sections3 and5, AGENTS, Master1642, production/composite contracts. Read-only source/helper briefs support the implementation boundaries; they are not scientific evidence.

## Global constraints

- Base is reviewed source checkpoint52b78e2, with its own exact-head CI. Each author uses an isolated existing worktree and owns only two new paths. No root/STATE/source-cache/main/GitHub mutation by workers.
- Exact built-in JSON types before traversal/coercion; no custom callbacks or dynamic implementation selection. Reject nonfinite numbers, bool-as-ID/count, duplicate keys, cycles, huge/deep inputs. Enforce explicit capacities under implementation safety ceilings and one cooperative deadline.
- Missing data is not zero/Negative. Hash/source/availability consistency does not authenticate original observations or historical availability. All source/scientific/production authority stays false/unattested; real fit and model activation are separate.
- No real prior, quantile confidence level, detection support threshold, speed, utility weight or access policy is selected from outcomes. Unspecified registered parameters block that calculation. Keep private original bytes, original predictions, models and tally unchanged; public output has no new GPS/capture/log data.
- Independent source reviewer checks exact authored bytes. Later root integration requires a new immutable expanded Freeze and own exact-head CI, never inherited from52b or89a.

## Task D: independent-opportunity detection evaluator

Owner: existing_pr_review. Own `src/detection_evaluation.py` and `tests/test_detection_evaluation.py` only. API `evaluate_detection_opportunities(bundle, *, protocol, budget_seconds=30)`.

The closed bundle contains the registered opportunity cohort and source/readiness bindings. Each opportunity retains site/time, independent truth method/reference/availability, observer/mode/protocol/effort, detected bool-or-null and detection-time/outcome-source binding, capture references and independence/depletion/site-night cluster information. Different filenames or self-reported independence do not authenticate truth. No capture-only or GPX-derived known-positive denominator.

- [ ] Specify exact fields and RED tests for missing/cohort-selected denominators, same-capture truth, duplicate identity, unknown result, observer/mode/time scope and repeat/depletion contradictions.
- [ ] Validate bindings and preserve full-cohort/known-result/unknown counts. Compute only explicitly conditional declared-source diagnostics; no missing outcome silently becomes false or a scientifically complete denominator.
- [ ] Execute n>0 empirical sensitivity s/n and separately named Beta(1+s,1+n-s) regularized posterior. n=0 is DATA_BLOCKED with observed estimate null. Require actual pinned runtime, explicit quantile probabilities/tail range, inverse tolerances, shape/work/time caps and supported cohort/cluster policy. No invented95% interval or support threshold.
- [ ] Use actual scipy.stats.beta.ppf with CDF/log-CDF/log-SF inverse verification, exact endpoints, support/order/finite checks. On interval capacity/nonconvergence preserve an independently valid empirical estimate only as a partial result; interval stays null.
- [ ] Known-negative absence leaves false-positive rate unvalidated; future prediction absence leaves Brier/log loss unproduced. Repeated-survey occupancy and biological TonightActivity remain separate.
- [ ] Run RED/GREEN, numerical hand-CDF/Uniform/boundary/tail/runtime/deadline/type/no-write controls. Commit only owned paths and return author receipt for independent review.

## Task G: source-bound OSM node graph

Owner: pr151_final_review. Own `src/route_graph.py` and `tests/test_route_graph.py` only. API `build_route_graph(graph_input, *, policy, budget_seconds=30)`.

Closed GraphInput fields are schema_version/sources/domain/context/coverage/closures/policy_sha256. Each source contains exact raw_json_utf8, SHA, byte size, available_at and availability_basis; bounded unchanged UTF-8 encoding verifies the original source before strict JSON parsing. Domain binds actual polygon/CRS/canonical SHA separately from any original-file hash. Context explicitly specifies night/cutoff/horizon/mode. Coverage claims and source-bound closures retain domain/time/mode/availability scope and cannot establish authenticated completeness.

- [ ] RED tests for coordinate-crossing false junctions, real shared-node ramps, missing middle nodes, bool IDs, unknown versions and equal-version conflicting payloads.
- [ ] Implement explicit version selection and directed multigraph edges from consecutive real node IDs, retaining parallel-way identity and structural tags. Never bridge a missing node, XY crossing, ferry/island gap or nearby road.
- [ ] Apply explicit supported oneway/roundabout/access/barrier/closure semantics. Unknown access is unknown. Preserve node-via no/only turn restrictions as edge-state constraints; unsupported conditional/via-way/except grammar is blocked, never ignored as unrestricted.
- [ ] Implement genuine edge-local polygon clipping where supported, including holes/crossing segments and private boundary-vertex identity per way edge. Existing coarse clipping is unsuitable. Unsupported/ambiguous geometry must be quarantined with explicit PARTIAL/IMPLEMENTATION_BLOCKED reasons rather than presented as full coverage.
- [ ] Canonically sort/hash graph, restrictions and upstream source/domain/policy/context. Preserve explicit missingness/version/exclusion/coverage diagnostics. Navigation remains blocked without source/current-access/restriction validation, even if supplied JSON claims completeness.
- [ ] TDD for topology/direction/restrictions/domain holes/boundary nonjunctions/raw bytes/cutoff/capacity/deadline/custom-type/no-write invariants. Characterize actual selected20 cached OSM sources privately if available; no reacquisition. Commit only owned paths for independent review.

## Integration and subsequent work

### Task U: native count unit details required by conditional routing

Owner: existing_pr_review, after fixing the Detection author checkpoint. Own only existing `src/count_activity.py` and `tests/test_count_activity.py` in a separate branch from52b. Independent review is separate from this writer. This is the existing Task6c planned-exposure output, not a new rate model or owner-plan selection.

API: `predict_gamma_poisson_units(model, planned_effort_inputs, *, protocol, budget_seconds=30)`. Reuse the same native validators/projector/moment kernel. Preserve existing `predict_gamma_poisson` behavior and its complete deterministic numerical payload for existing callers; volatile operational duration remains separately identified. A distinct new envelope carries the unchanged aggregate prediction plus source-bound per-unit details.

- [ ] RED for missing raw future plan/model, changed bindings, future actual-GPX replacement, modified original allocation, duplicate IDs, and numerical underflow/missing moments.
- [ ] Run the existing actual source-plan projector and model gates under one deadline, never accept projected rows or caller-authenticated booleans. Return row_id/night/cell/window/planned seconds/native mean-or-null/numerical status with original plan/domain/projection/model/protocol hashes.
- [ ] Preserve exact allocation IDs/start/end/duration and source lineage from validated original JSON; projection10-minute totals do not reconstruct unknown exact timing. No altered/subset owner plan is created or frozen.
- [ ] Derive per-unit moments through shared existing arithmetic, not a route-side a/b kernel or per-unit SciPy quantile loops. Expose one common Gamma rate, not invented spatial differentiation. Do not sum marginal variances/quantiles as an aggregate interval.
- [ ] Preserve missing/partial/underflow statuses, unknowns and every false authority flag. Bind the complete deterministic unit envelope and rerun immutability/runtime/budget/old aggregate parity tests.
- [ ] Commit only the two owned files and obtain independent source review. Root owns eventual sole-registry schema/port binding and the new full Freeze/CI.

The downstream route calculation must separately bind original future units to real graph geometry/nodes, use explicit speed/search timing and honor direction/edge-state restrictions. Reward only uniquely visited feasible units of the **same original fixed plan**; transit has no search reward. A feasible subset remains a conditional original-plan scenario, never a new authenticated owner intent. Spatial ranking without supported native count detail has expected captures=null. All route/navigation/scientific/production authority remains blocked pending its actual proof.

### Task I: sole registry connection for native detection and planned-unit details

Owner: pr151_final_review. Own only existing `src/output_adapters.py`, `src/composite_inference.py` and their two test files. Reuse the exact reviewed Detection1af and Gamma-unitc8 functions. Add fixed version1 IDs `gamma_poisson_planned_units_v1` and `independent_opportunity_detection_v1`; no caller-selected registry, source validation flags or dynamic implementation.

- [ ] TDD the fixed eight-adapter table, new typed inputs/ports and deterministic complete native envelopes. Preserve successful existing six-adapter numerical semantics/IDs. Bind and explicitly exclude only volatile operational duration paths; complete model/source/plan/protocol/status/numerical payloads stay hashed.
- [ ] The Gamma state/config/input contract remains native model, `{protocol}` and `{plan}`. Emit `planned_count_units` only from actual native unit execution, never fake zero for absent/underflow means or a complete port for missing mandatory data. Original allocations and common Gamma dependence remain visible.
- [ ] Detection uses stateless state `{}`, config`{protocol}`, input`{bundle}` and output`detection_opportunity_diagnostic`. A known-subset diagnostic remains PARTIAL; n=0 or no valid estimate produces no port. This is not a biological Activity, population detection, source authentication or scientific promotion capability.
- [ ] Bind Gamma plan/night/as-of/horizon as in the existing count adapter. Detection assessment must be no later than composite cutoff, with all sources strictly before native assessment; later truth cannot enter an earlier inference. Verify transitive local code closure and shared budget/type/capacity/error behavior through the same composite dispatcher.

Keep the existing32MiB adapter JSON ceiling. A full71MiB graph is an internal native geometry computation, not a prediction port. A future route adapter must return bounded routes plus graph identity/summary/missingness, with no full graph or private raw serialization in PredictionBundle. Root independently reviews the fixed dispatch changes and owns final Freeze/CI/GitHub.

### Task R: bounded conditional route candidate calculation

Owner: existing_pr_review, after the fixed unit-output author checkpoint; own only new `src/route_planning.py` and `tests/test_route_planning.py`. Base contains native reviewed grapha34 and native unitc8 (plus any reviewed repairs), with no second graph/model dispatcher.

API: `plan_route_candidates(graph_input, decision_input, *, graph_policy, policy, budget_seconds=30)`. The fixed native graph builder and native Gamma unit predictor execute under one shared deadline; caller-supplied computed graph or unit means cannot replace them. Closed decision inputs bind the exact graph policy/domain/context, native model/count protocol/original raw future plan, source-plan identity and allocations, unit-to-real-graph-node associations, start/end/return requirement, time budget and explicit travel profile. Every source/profile/link availability is strictly before its own cutoff. Primitive JSON/capacity/callback guards apply before all helpers.

- [ ] Align the exact decision/policy/output contracts before implementation. Policy explicitly owns every speed, time/turn/wait/search allocation assumption, units, utility/uncertainty weight, A/B/C constraint, overlap/diversity rule and bounded work parameter. No road-class speed, calibrated uncertainty, actual owner choice or safe-navigation claim is inferred. Unsupported geometry/association/plan semantics block that calculation rather than create proximity connectors.
- [ ] TDD native node association/domain/time/cell consistency, direction, NO/ONLY turns with previous-edge state, missing/unknown access/closures, start/end feasibility and source/hash/runtime/budget/type failures. Preserve native graph `ways` lookup and missingness; all candidate outputs remain NAVIGATION_BLOCKED/NOT_VALIDATED, even with supplied completeness flags.
- [ ] Implement bounded deterministic edge-state Dijkstra and beam search. Require explicit protocol bounds no larger than50 reward waypoints,64 beam width,20 depth,10000 expanded states and a shared elapsed deadline. Bound shortest-path work separately and account for it globally. State includes node/previous edge/time/remaining budget/rewarded original unit IDs. Enforce feasible return and forecast horizon; report incumbent/search exhaustion without claiming global optimality.
- [ ] A unit reward uses the actual native mean for its original planned effort only when the route can execute all its original allocation intersections at the unchanged times. Early arrival/wait/dwell must be an explicit scenario policy; late/partial coverage cannot receive the full-unit mean. Transit and repeated units have zero additional reward. Do not generate/reseal a subset as a new owner plan, silently move exposure or use future actual GPX. A conditional subset is labelled as such. Common Gamma rate implies equal exposure has equal expected count; no invented spatial biology, multiplied Bernoulli scores or summed marginal intervals.
- [ ] A maximizes declared utility among found feasible candidates; B uses the same utility with its declared overlap bound; C minimizes the declared travel/uncertainty objective subject to its explicit reward/divergence constraints. Return fewer routes with reasons if fewer feasible diverse candidates exist. No clones, safest label or observed benefit claim. Unsupported native count yields expected captures=null/explicit blocker; ranking scores are not count units.
- [ ] Test hand-enumerable synthetic optima, disconnected/one-way/restriction/cell-window cases, duplicate visits, impossible schedules, return constraints, unknown source/access and deterministic ties. Preserve all source bytes and old count/graph outputs. Commit only owned paths; independent review and own expanded Freeze/CI remain required before publication. Real route benefit, adherence/counterfactual evaluation, rerouting and issuer integration remain subsequent contracts.

Root verifies authored commits and independent findings, repairs on the same branches, integrates their actual reviewed bytes and freezes the new code closure. Run meaningful combined regressions and new exact-head CI on PR155. Conditional route optimizer/rerouting, actual route outcome ledger, trusted controller/context, live registry CAS/ACK recovery/compatible loader/issuer remain subsequent implementation. Unknown source qualifications, real scientific evaluation and prospective P0-to-PDCA remain explicit unmet gates; do not claim their completion from synthetic calculations.

### Task J: fixed adapter for conditional route scenarios

Owner: existing_pr_review; four existing adapter/composite source and test paths only. The accepted contract adds fixed version1 `conditional_route_candidates_v1` to the existing registry. Inputs are the raw native graph and decision inputs, config contains the graph and route policies, and state is the exact Gamma model already bound inside the decision. Reject differing models before the native call; do not replace either silently. Bind cutoff, operational night and horizon through the existing composite dispatcher.

Return the complete deterministic native route envelope, excluding only its operational elapsed duration. Keep missing routes, partial search, missing means and navigation blockers visible; no formal P0, complete mandatory port or safe route follows from a partial result. Preserve the prior eight adapters' complete deterministic execution payloads and IDs. The complete graph stays inside the native calculation; its SHA, diagnostics and policy bindings identify it without serializing private graph bytes into the port. Native route output has no graph-summary field, so the adapter must not invent one or recompute the graph merely to add it.

The implementation must remain inside the existing32MiB adapter input budget, freeze the transitive47-path local code closure, pass native route and composite regression controls, and receive an independent review. The resulting software checkpoint grants no data, scientific, navigation or production authority.
