# Task6c design: count, activity, detection, formal time targets, routes and rerouting

Design-only recommendation for canonical Goal1642. Current shared repository was read, not modified. No nested agents or external data requests. No scientific validation or test execution is claimed. The objective is substantive bounded adapters with reproducible predictions and evidence-aware evaluation; unavailable observations must produce concrete blockers, not fabricated targets/outcomes.

## Scope and approach

Canonical master-goal-1642-source.md requires Tonight Activity/expected count, applicable detection, route optimizer A/B/C and evidence-supported rerouting; formal 100m±10min is mandatory in the full policy. Current model_evaluation.py emits spatial scores and explicitly reports these adapters missing. Existing priors must not be renamed into new outputs without implementing their mathematics.

Recommended approach: add a typed adapter registry and separate small statistical, time-target, topology and route-evaluation modules, reusing the audited snapshot/model/replay machinery. This is preferable to (a) bolting every metric into pdca_pipeline.py, which couples operational history to model research, or (b) adopting an external unrestricted navigation/model service, which adds unjustified dependencies and authority. Existing baseline families and historical M0–M3 definitions remain byte/semantically unchanged; any new candidate uses a new versioned family/protocol.

Implementation should be sliced: statistical+formal outputs; then graph/candidate routing; then real route outcome/rerouting evaluation. All can have executed synthetic contract tests while real scientific gates remain blocked.

## Shared contract

Every adapter has validate_inputs -> fit/predict -> evaluate and returns output envelope:
schema_version, adapter_id/version, execution_status, validity_status, gate_outcome, produced_outputs, applicability_policy_ref, model/protocol/universe/source hashes, training_cutoff, prediction_id/version/class, cutoff_time, forecast_window, assumptions, missing_requirements, predictions, metrics, evidence_refs.

No boolean “available” substitute for checking inputs. NOT_PRODUCED means no prediction existed; DATA_BLOCKED means a required artifact/fact is missing; IMPLEMENTATION_BLOCKED means missing executor; NOT_VALIDATED means executed calculation lacks scientific support. Requested capability cannot disappear through NOT_APPLICABLE. Promotion continues to require all canonical full-scope gates.

All ex-ante predictors, graph restrictions, current-position observations, planned effort, route policy and time-expanded universe must be bound to hashes and available by each own cutoff. Training rows and labels must be strictly before evaluated night/cutoff. Outcomes may arrive later as evaluation labels. P0/Pn separate, only outcomes strictly after own cutoff, within declared forecast horizon/night. Pn uses actual live observations <=its cutoff, never later trajectory. Confirmation splits and at-most-three candidate policy apply to registered selection, not a new unlimited candidate loop.

Task6b source_refs/availability contracts are dependencies. Referenced metadata string alone cannot certify historical access. Exact recovered OSM bytes are now available; this does not establish September28 prediction access.

## 1. Expected capture count: bounded exposure-conditioned intensity

### Required observations

Training row must include verified integer capture_count, canonical event IDs/individual multiplicity, measured search duration in hours e_i>0, search mode/observer protocol, complete outcome logging in that observed interval, coordinates/time/features and provenance. Zero effort plus positive capture is an inconsistent rate-model row to quarantine; captured outcomes without measured effort remain usable for other diagnostics, not this model. Unknown/out-of-search units are not Poisson zero observations.

Forecast has an explicit **planned** search-effort allocation e*_u over future universe units, frozen before the forecast. This can be a declared hypothetical schedule or selected route. It is not filled from future actual GPX. Display “expected captures conditional on the declared search plan,” not island-wide animal count.

### Models

Start with auditable Gamma-Poisson baseline:
Y_i | r ~ Poisson(e_i r), r ~ Gamma(alpha,beta), shape/rate convention.
Posterior a=alpha+sum Y_i, b=beta+sum e_i.
For planned exposure E*=sum e*_u: expected count mu=E*a/b; predictive variance mu + E*²a/b². Predictive count law is Negative Binomial with shape a and success probability p=b/(b+E*). alpha,beta are positive, finite and fixed in preregistered protocol, not selected from confirmation labels. The initial slice must implement this actual baseline. Correction: requirements-analysis.txt already declares -r requirements-osm.txt, numpy==2.2.6, scipy==1.15.3 and scikit-learn==1.5.2; existing data-intake-tests CI installs that analysis profile. The parent authorizes Task5 shared executor installation of this existing profile without requirements changes or new dependencies. Use pinned SciPy 1.15.3 for stable distribution routines; the earlier claim that SciPy was undeclared was incorrect. Record and check exact runtime package versions against this profile in result/runtime provenance, together with protocol, code and input hashes. An absent or mismatched analysis runtime returns an explicit dependency/runtime binding error, not a silent alternate implementation.

Bounded quantile routine: use scipy.stats.nbinom.ppf(q, n=a, p=b/(b+E*)) for the declared predictive count distribution, with scipy.stats.nbinom.cdf/logcdf/logsf for tail and inverse checks where numerically appropriate. Treat E*=0 as degenerate at zero. Reject invalid/nonfinite parameters or returned values, unsupported ratios/overflow and failed monotonicity. Validate returned finite integer support values against the quantile definition (CDF(k)>=q and CDF(k-1)<q), using a declared numerical tolerance and stable tail checks near endpoints. Quantile probabilities, maximum supported output count, input shape/rate range and wall-time budget are explicit protocol-owned capacities; exceeding a capacity or failing numerical checks returns NUMERICAL_CAPACITY_EXCEEDED or NUMERICAL_NONCONVERGENCE with no interval. A finite verified analytic mean may remain available, but a missing interval is not calibrated or complete. Record package version, requested quantiles, numerical tolerances, capacity and elapsed time. No clipping, guessed tail endpoint or truncated renormalization to manufacture success. Handwritten CDF summation is not required.

Optional feature-aware registered candidate, within the existing analysis dependency profile only when explicitly included in the implementation slice:
Y_i ~ Poisson(mu_i), log mu_i=log e_i + beta0+x_i^T beta.
Minimize sum(mu_i-Y_i log mu_i+log Gamma(Y_i+1)) + lambda||beta_nonintercept||²/2.
Reuse the Task6b bounded optimizer approach where appropriate, or use the already-pinned scipy.optimize.minimize (for example L-BFGS-B) with this objective and analytic gradient X^T(mu-Y)+penalty. Bind the method/options and SciPy version in protocol/runtime provenance. Enforce maxiter/maxfun, convergence tolerance, elapsed-time budget, train-only scaling/imputation schema and finite checks; solver success alone is insufficient without objective/gradient/parameter checks. If that optional implementation cannot meet these checks, defer it explicitly; the Gamma-Poisson baseline remains mandatory. No additional dependency or requirements change is authorized. Hyperparameters/features are fixed or selected on development only. Rank-deficiency policy, nonconvergence, overflow and numerical-capacity failures return explicit fit errors, not a prior pretending to be a successful candidate. Do not share coefficients with Bernoulli spatial probabilities without a registered calibration relationship.

mu_u=e*_u exp(beta0+x*_u^T beta), predicted remaining count=sum mu_u. Conditional Poisson aggregation assumes the fitted conditional process; overdispersion/clustering diagnosed. Poisson prediction intervals must be labelled conditional/model-based and checked prospectively; do not claim calibrated biological uncertainty from formula alone.

### Evaluation

Verified actual individual count Y over exactly the forecast/search scope; MAE, signed error, count log score, interval coverage/width and zero-count calibration. Poisson deviance 2[Y log(Y/mu)-(Y-mu)] with Y=0 convention; mu=0,Y>0 gives infinite deviance, not clipped success. Aggregate metrics by night and pair identical test nights. Report plan adherence separately; recomputing mu using realized exposure is retrospective diagnostic only, never the original count forecast. Missing complete outcome ledger blocks error metrics even if a few captures were recorded.

Current September28 supplies 5 events/6 individuals but lacks validated effort/log completeness and ex-ante plan. Recovered expected_count=4 can retain historical diagnostic absolute error2 under existing limitations; it is not evidence that this count adapter was issued or calibrated.

## 2. Tonight Activity: unresolved biological target plus supplementary proxy

True snake activity/abundance is not identifiable from catches alone. Do not introduce a biological activity index under that name. The real Tonight Activity requirement remains NOT_VALIDATED unless its scientific target is explicitly defined and supported by suitable evidence. A supplementary capture proxy does not satisfy or waive that requirement or its promotion gate.

Implement a declared output family **capture_activity_proxy** using the count rate evaluated at a fixed reference effort E_ref and reference observer/search mode, defined in protocol:
activity_expected_captures = E_ref * fitted_rate (or integrate standardized reference schedule across forecast units).
Optional percentile = empirical rank among training-night standardized predictions only, with fixed handling of ties and minimum history; it is relative to that reference population, not a probability.

A supplementary probability of at least one capture under the plan is a separately named output P(Y>=1)=1-exp(-mu) for Poisson, or 1-(b/(b+E*))^a for Gamma-Poisson predictive; use stdlib expm1/log1p for stable evaluation. Never call either detection probability or automatically equate it with Tonight Activity. Brier/log score on verified night event Y>=1; unknown outcome night excluded with reason. Zero captures observed under complete search can be a valid zero event, unsearched is unknown.

Block true biological activity validity until an explicitly defined target and independently measured activity/effort design exist. The supplementary proxy can execute but cannot close the real requirement. Any proposed redefinition of an owner-defined biological target requires specification review, not an adapter convenience decision.

## 3. Detection: independent opportunity denominator

Do not estimate detection from “captured / all logged captures,” capture density, or presumed presence in every traversed cell. A first implementable detector evaluator uses independent **known-positive opportunities**.

DetectionOpportunity schema:
opportunity_id,site/time,truth_status,truth_method,truth_source_ref,truth_available_at,observer_id,protocol_version,effort,detected(bool/null),detection_time,capture_event_refs,independence/depletion flags.
Truth must be established independently of the evaluated detector/search result; if the only evidence of presence is the same capture, denominator is outcome-selected and invalid.

For n known-positive independent opportunities, s detected:
p_hat=s/n for n>0; beta posterior Beta(alpha+s,beta+n-s) as declared regularized estimator. The initial prior alpha=beta=1 is explicitly preregistered; alternative positive finite priors require protocol approval, not a new numerical dependency. Compute intervals using scipy.stats.beta.ppf at declared probabilities under pinned SciPy 1.15.3, with cdf/logcdf/logsf checks as appropriate. Handle endpoints exactly, reject invalid/nonfinite shapes or outputs, and verify interval ordering, [0,1] support and inverse-CDF residual within a declared tolerance. Input size/shape range, requested tail range and wall-time capacities remain explicit. Capacity or convergence failures produce NUMERICAL_CAPACITY_EXCEEDED or NUMERICAL_NONCONVERGENCE with no interval; do not substitute [0,1] and call it computed. Allow an independently valid s/n estimate while recording interval failure. n=0 gives DATA_BLOCKED for observed sensitivity, never a posterior-only estimate presented as measured sensitivity. Record exact runtime version and protocol parameters. The previous integer-shape-only, n<=10000, handcrafted binomial-tail and60-bisection restrictions are superseded; no handrolled Beta CDF is required.

Aggregate/count sensitivity by observer/mode only with sufficient preregistered opportunities; repeat measures clustered by site/night. Known-negative independently verified opportunities allow false positive rate; otherwise false positive metric is NOT_VALIDATED, not zero. Prediction evaluation Brier/log loss uses future truth-confirmed opportunities. These posterior intervals assume the declared statistical model and are not scientific validation by themselves.

Repeated-survey occupancy is a **separate future model**, not the minimum default. Under closure and no removal, latent z_s~Bernoulli(psi_s), y_sj|z_s~Bernoulli(z_s p_sj). For all-zero histories likelihood (1-psi_s)+psi_s product_j(1-p_sj); positive histories psi_s product_j p_sj^y(1-p_sj)^(1-y). At least replicated surveys, identifiability diagnostics, independent sites and closure justification are necessary. Habu capture removes individuals, violating naive closure; require explicit removal model or restrict to non-removal surveys. Defer occupancy fitting rather than invent a valid likelihood from captures-only data.

Current corpus has no independent opportunity/replicate survey ledger: execute schema/missing-input check, return DATA_BLOCKED with exact fields. No population/detection estimate.

## 4. Actual formal 100m±10min forecast targets

Spatial scores alone cannot be relabelled formal time predictions. Use a time-resolved registered count/intensity or Bernoulli model fitted only from eligible historical data and applied to a declared future 10-minute universe.

TimeTargetPolicy frozen before labels: target_budget K, time anchor rule (e.g. 10-minute window midpoint), spatial center rule, minimum score/calibrated-probability threshold, deterministic tie ordering, exclusion/suppression rule and individual/event matching semantics. Candidate anchors are actual ex-ante universe coordinates/window IDs, not selected around realized captures. Only target time>cutoff and within horizon/night.

One bounded algorithm:
1. predict mu_u (under explicit reference effort if comparing cells) or calibrated q_u=P(capture in unit);
2. sort score descending then (time,row_id);
3. greedily keep up to K, optionally suppress another anchor if <=200m and <=20min from an accepted anchor, as a **predeclared target-overlap policy**, not a changed KPI;
4. freeze target_id,point,time,source_unit,score/model hash with exact radius100m and tolerance10min.

No multiplicity from mu rounding. Default one target token predicts one individual; if event-level target is chosen, name separate metric. Multi-individual midnight event creates two outcome tokens with shared event_group_id and distinct individual IDs only if canonical count verified. Each target/outcome at most one match.

Evaluator: bipartite edges for distance<=100m AND abs(dt)<=600s, same operational night and outcome>cutoff. Maximum cardinality matching, deterministic secondary cost/tie rule. Report matched captures/confirmed total recall, matched targets/evaluable targets precision, FN/FP and UNKNOWN targets separately. Pre-cutoff observed labels do not establish post-cutoff target eligibility. Define eligible target outcome ascertainment over its applicable space-time region; a lone GPX sample near the anchor is insufficient proof of full no-capture outcome. Unsearched/unascertained unmatched target is UNKNOWN, never FP. Precision on verified-observed target subset is selection-conditioned; expose denominator and missingness. Formal radius/time stay fixed independently of broader diagnostics. Zero-positive nights null recall.

Match metric and per-cell probabilistic metrics remain separate. Top10 1km recall stage gate does not grant time-target validation automatically. Current formal TARGETS are NOT_PRODUCED in spatial-only model; future adapter can produce them without inventing historical ORIGINAL.

## 5. OSM node-topology graph and A/B/C route candidates

### Available vs missing

Recovered selected20 raw tile JSONs contain ordered way.nodes and node coordinates. Read-only inspection found only node/way elements: **no restriction relations**. Acquisition query selects highway ways+nodes, not relation completeness. Centerline geometries and 100m grid alone lose topology identity and cannot support safe graph reconstruction by crossing.

GraphInput: exact selected-source hashes (not all72 retained superseded tiles), source available_at/basis, domain polygon, node/way versions, access/oneway/layer/bridge/tunnel/barrier/conditional tags, turn-restriction records and completeness declaration, approved vehicle/mode, live closures, graph policy hash.

Build directed multigraph:
- deduplicate type+OSM ID by explicit version rule; missing version tracked, equal-version conflicting payload fails;
- connect only consecutive real node IDs in a valid way; missing node breaks adjacency, no straight gap bridge;
- coordinate crossing or overlapping XY alone **never** creates an edge/junction;
- shared actual node can represent physical connection including ramps across layers; preserve per-way layer/bridge/tunnel, require compatible topology/transition or flag ambiguous connection. Do not blanket-disconnect every layer difference, and do not auto-connect different-node crossings;
- enforce explicit vehicle/access no/private exclusion from normal route according to existing policy; unknown access remains unknown, not permission;
- respect oneway=yes/-1 and roundabout direction; turn restrictions require edge-state traversal (previous edge,current node) and forbidden/only turn transitions. Missing/incomplete restriction/conditional-access coverage means topology candidate can exist but real navigational compliance **NOT_VALIDATED/BLOCKED**;
- evaluate conditional tags only for supported explicit semantics/time/vehicle; unsupported rule -> exclude affected edge or block route, not silently permit;
- barriers/closures similarly require known passability; no ferry/island jump or off-road connector from proximity;
- clipping at domain creates edge-local boundary vertices, not cross-way junctions. Start/end snap needs validated node/edge projection with max distance and access constraints; no arbitrary bridge across river/grade.

Hash sorted graph nodes/edges/transition constraints and upstream refs. Current-time field restrictions may be Pn inputs only when available by Pn cutoff. OSM is auxiliary; legal/current passability unknown without validation. It may support auditable research candidates now, not a guaranteed safe route recommendation.

### Travel and effort

Each edge has geometry-derived length L_e; traversal time t_e=L_e/v_e + declared dwell/turn costs. v_e must be measured historical mode-specific speed or an explicit planning assumption bounded by applicable known limits; road class does not fabricate a measured speed. Tag maxspeed is legal cap, not travel speed. No source for speed -> require owner/approved policy planning scenario, label time estimate unvalidated. Prediction uses route arrival times to select universe windows; missing future universe beyond horizon blocks those rewards.

RoutePlan input: cutoff,horizon,start,end/return requirement,time budget,vehicle/search mode,closure refs,travel profile,approved utility/risk profile and K/budget limits. Cells/time encountered across overlapping edges deduplicated; visiting the same forecast unit twice does not double-count the same expected reward without a registered revisit/removal model.

Reward is **expected capture proxy under allocated search time**, not summed arbitrary ranking scores. mu_u(d_u) from intensity plus unit search-effort allocation. J(R)=sum_unique_u mu_u(d_u) - lambda_t*T(R) - lambda_u*U(R), with U defined only from actual uncertainty metadata, no invented “danger score.” Transit not recorded as search gets no search reward. If only spatial scores available, output ranking-based route utility in different units, expected captures=null.

### Bounded candidate optimizer

Use deterministic budgeted beam search on contracted *topologically valid* graph corridors/time-expanded states; fixed shortlist of at most50 ex-ante reward waypoints, beam64, depth20, max10000 expanded states and explicit elapsed budget, all protocol-owned and recorded. These are proposed engineering limits, not scientific constants. Dijkstra/edge-state shortest paths respect direction/restrictions and return feasibility. State includes current node/time, remaining budget and rewarded unit IDs; lower-bound return travel prunes impossible states. No unbounded graph enumeration. If exhausted, return feasible incumbent with search_exhausted flag; never assert global optimum.

A: highest expected utility incumbent under approved weights.
B: alternative with bounded overlap with A (e.g. shared directed-edge length /min(route lengths)<=rho fixed in policy), maximize same utility.
C: alternative minimizing a declared travel/uncertainty objective subject to explicit minimum expected reward and divergence constraints.
A/B/C labels/weights must be declared, not silently arbitrary. If three feasible diverse routes do not exist, return fewer with concrete reason; never clone a route as three choices. A route cannot be called “safest” from OSM missingness alone.

Tests validate exact optimum only on small enumerable synthetic graphs; production algorithm calls itself bounded heuristic. Uncertainty/sensitivity across declared speed/rate scenarios is reported, not disguised as empirical confidence.

## 6. Real route outcome ledger and evaluation

RouteDecisionLedger is append-only and separate from prediction/raw history:
decision_id,night,Pn,prediction_id,cutoff,issued_at,graph/model/universe hashes,planned route IDs with ordered edge sequence/arrival intervals/search allocation/utility,chosen_route_id,decision policy/propensity if randomized,actual-start/end,actual trajectory refs,matched-edge segments+confidence,actual search-role/effort intervals,outcome completeness,capture event IDs and detection-opportunity refs,departures/closures/reasons,availability receipts.

Actual route matching uses topology/time-aware constrained map-match to audited GPX with explicit error/gap bounds; ambiguous or unmatched intervals remain unresolved. Do not shortest-path-fill a GPS dropout as actual travelled evidence. Actual captures assigned once to eligible actual interval, preserve individual counts.

For chosen/executed route report actual time/distance, search effort, captures per verified search-hour/km, planned-vs-actual timing/edge adherence, forecast error for declared outcome scope. Different choices unexecuted -> NOT_OBSERVED outcome. A/B/C predicted utility comparison is model diagnostic, not observed improvement. Captures observed near B while following A do not establish what would happen if B were chosen.

Route benefit requires a predeclared prospective comparison: randomized feasible route/strategy with logged known nonzero assignment propensity, or a justified observational design. Optional IPS estimator V_hat(pi)=N^-1 sum I(A_i=pi(X_i))*Y_i/p(A_i|X_i); positivity, stable outcomes, known propensity and no hidden interference essential; uncertainty clustered by night. Do not implement IPS on arbitrary guessed propensities or deterministic historical route choice. Repeat captures/depletion and travel constraints can invalidate simple counterfactual assumptions. Without design, benefit NOT_VALIDATED even if route adherence calculation passes.

## 7. Real-time rerouting

A new version Pn appends a RouteDecision at live cutoff; it never rewrites P0/P(n-1). Inputs: observed current node/position timestamp<=cutoff, elapsed/remaining budget, live closures/weather/encounters available<=cutoff, visited cells/event IDs, current prior route version. Safe decision algorithm: rerun same bounded optimizer on remaining feasible graph/horizon and declared updated model state; exclude completed traversal and account for already rewarded/captured units using explicit no-double-credit policy. Compare estimated remaining utility to continuing old feasible plan under **the same current information**; switch only if difference exceeds preregistered hysteresis/extra travel cost threshold and minimum update interval. Closure may force feasibility reroute regardless of utility.

Evaluate after-cutoff remaining outcomes only; compare frozen P0 planned remaining prediction and actual issued Pn forecasts separately. Ledger records both hypothetical continue-old and selected-new forecasts, but only executed path has observed outcome. A changing cumulative capture total is not reroute gain. Causal rerouting improvement requires prospective policy comparison; current single-night data cannot identify it.

## Proposed minimal file scope and integration

New modules:
1. src/output_adapters.py — registry/envelopes/shared input validation and explicit applicability.
2. src/count_activity.py — mandatory Gamma-Poisson baseline using the existing pinned SciPy analysis profile, supplementary activity proxy/count metrics; optional bounded Poisson GLM only if included in the approved slice.
3. src/detection_evaluation.py — independent-opportunity estimator/evaluator; no occupancy default.
4. src/time_target_evaluation.py — actual frozen target construction and formal matching wrapper reusing corrected core geometry/matching where possible.
5. src/route_graph.py — topology/direction/access/restriction graph, pure reader of audited OSM artifact.
6. src/route_evaluation.py — bounded candidates, immutable decision/outcome ledger validation, adherence/rerouting metrics.
Tests corresponding to each plus one integration fixture; docs/specs/output-route-adapters.md to record approved semantics. Targeted edits only to model_evaluation adapter dispatch/registration, master_orchestrator consumed-input inventory/results, and future Champion inference registry once Task4 interface stabilizes. No shared repo edits made by this design author. No raw/ORIGINAL migration, workflow permissions, dependency changes or external routing APIs.

Keep initial count/time slice <=one implementer scope and graph/route slice separate. All production writer paths remain run-scoped/content-addressed; input envelope hashes include ledger/protocol/graph. Implementation coordinator should explicitly resolve whether “Tonight Activity” proxy interpretation is already authorized rather than silently changing target semantics.

## Required tests and actual-data blockers

Tests must cover:
- count conjugate formulas/quantiles, exposure units, count2 event, missing effort, zero effort/count contradictions, quantile-capacity/overflow and inverse-CDF check errors, later-training-label exclusion, actual-effort leakage; optional optimizer convergence/failure only if that adapter is included;
- supplementary activity at-least-one mapping distinct from detection, percentile train-only, unknown outcome, and real Tonight Activity remaining NOT_VALIDATED;
- independent known-positive opportunities vs capture-selected denominator; duplicate opportunity, same-night dependence, no negative-truth FPR claim; Beta(1,1) uniform and known-CDF cases, PPF endpoints/monotonicity and inverse consistency, invalid shapes, capacity/nonconvergence rejection; exact pinned analysis-runtime binding and missing/mismatched-version errors; no new dependencies;
- time-target actual timestamps, exact100m/600s boundaries, cutoff equality excluded, matching competition, multi-individual tokens, K budget, unobserved UNKNOWN, no target reconstruction from captures;
- graph crossing-without-shared-node disconnected, bridge/tunnel overlap disconnected, explicit shared-node ramp handled, missing node break, reverse oneway, barriers, no/private, unsupported condition, no turn-restriction proof, island disconnect and bounded snap;
- route no reward double-counting, transit vs search, start/end/time constraints, deterministic budget stop, infeasible A/B/C diversity, no optimality claim, missing speed profile;
- ledger duplicate/changed decision rejected, actual-only scoring, uncertain map-match excluded, Pn after-cutoff only, no causal claim from unexecuted routes, stale live facts rejected;
- snapshots stable across rerun, same candidates/folds/protocol, research/confirmation separation, raw/ORIGINAL before-after equality.

Actual blockers remain: no historical ex-ante time/effort universe; no validated complete effort/outcome coverage for canonical training; no independent detection opportunities; no route decisions+real outcome ledger; no turn-restriction completeness in recovered raw; no measured speed/current access verification; no untouched prospective confirmation/cross-year validation. Recovered OSM **does** provide genuine static candidate geometry and node topology; do not repeat missing-bytes blocker.

Scientific limits: capture intensity conflates abundance/activity/detection/effort; observation-conditioned precision is selection-dependent; posterior intervals assume model/process and do not certify biology; repeated visits have depletion; learned spatial/time relationships need independent confirmation; route utilities are forecasts, not counterfactual outcomes. Building these executors removes implementation blockers, while their live evidence and scientific gates must remain independently reported.

## Owner route-purpose clarification

Preserve the established route purposes when a product policy instantiates A/B/C: A maximizes expected captures; B prioritizes expected captures per declared distance/time; C is a materially different diversification, large-individual or unexplored-high-expectation alternative. All three obey the same actual constraints, including forest-road exclusions when supplied. Large-individual reward requires a separately supported model/evidence and remains unknown without it; never invent such a bonus. C may use the explicitly approved diversification objective while reporting unsupported large-individual contribution as NOT_VALIDATED. The generic objectives above are algorithmic examples, not permission to silently redefine these user-facing route purposes. Freeze weights, denominator units, diversity thresholds and scope before evaluation.
