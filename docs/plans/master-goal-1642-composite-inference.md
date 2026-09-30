# Minimal composite inference contract: Tasks 6b/6c and 4/8

Read-only design. Current Task4 validates a single schema-v1 family, hashes only model_evaluation.py, assumes empty feature schema and hardcodes probability families; issuer always emits no formal targets. Those guards correctly reject unsupported inference today. Replace them with a shared fixed capability registry and explicit schema-v2 composite contract; do not simply remove validation.

## One registered candidate is one complete recipe

A candidate is a frozen composite recipe, not an independently selected model per output. Protocol preregisters at most three recipe IDs (including required baseline), each fixing all learned components, transforms, hyperparameters, output policies, graph/travel/utility policy and dependency edges. All component choices are frozen before confirmation. Selection uses development only and confirms one composite once. Swapping a count model, target threshold or route utility after observing confirmation creates a changed candidate requiring fresh confirmation; it cannot keep the old Champion ID/evidence.

Shared components may be fitted once and reused by hash. Ablation variants and A/B/C route alternatives remain non-promotable diagnostics/predictions, not hidden extra competitors. If any variant is eligible for selection, it occupies one of three candidate slots. Count all fits/searches against the common two-round/300-second budget. Champion is a fixed comparator; it is not an additional newly searched candidate.

## CompositeModel v2

Canonical immutable fields:

- schema_version='2.0', kind='registered_composite', recipe_id, protocol/policy hashes, model_id/model_sha256;
- components: ordered records containing component_id, registered adapter ID/version, role, dependency component IDs/output names, fixed config hash, feature/input schema hashes, fitted-state artifact hash, training-data hash/cutoff, expected output schema/capabilities;
- output_bindings: product output name -> exact component/output schema/semantics; no implicit union of arbitrary produced_outputs strings;
- code_manifest reference/hash: exact reviewed inference closure and runtime/dependency lock identity;
- training_cutoff: latest actual cutoff across learned components, plus per-component cutoffs; evidence references and immutable input-policy references;
- applicability_policy reference/hash, mandatory capability list and conditional capability declarations fixed by product policy, never by candidate convenience.

Model hash covers every field except its own model_id/hash, recursively binding all referenced component/state/config/schema artifacts. Keep validation status/Champion lifecycle in registry events rather than mutating a fitted artifact. No code, dynamic import name or shell command from model data is executable. Backward-compatible v1 verifier remains for old models with their original output limitations; no automatic promotion of a v1 baseline to full composite capability.

The fixed registry maps reviewed adapter IDs to Python callables and capability schemas. It validates each component state, allowed dependencies, dimensions, units and output semantics. Dependency graph must be acyclic and small. Unknown adapters, duplicate writers, incompatible units/semantics, missing dependencies, hash mismatch or unregistered output capability fail closed.

## Fit and predict boundary

Provide fit_recipe(recipe, audited_training_bundle, protocol, budget)->CompositeModel plus fit evidence. Every learned component and transform receives only eligible training data; no confirmation-label object is passed. Stateless components such as target selection and route search bind frozen config rather than pretending to fit. Shared data does not imply shared coefficients: Bernoulli occupancy and effort-conditioned count retain distinct states and semantics.

Provide predict_composite(model, InferenceBundle, budget)->PredictionBundle. Existing predict_model(model, universe_rows) stays the v1/individual spatial adapter compatibility API; do not overload it with hidden reads or arbitrary route context. Task6b's feature-aware spatial component may extend its supported family registry, while composite dispatch is an explicit new entrypoint.

InferenceBundle binds operational night, P0/Pn cutoff/horizon, ex-ante universe and feature artifacts, source availability, planned effort, graph/travel/constraint policies and optional live position/visited-event context. Validate at the boundary, then execute only fixed dependency order. It must not contain future outcome labels or future actual GPX. Missing required inference inputs yields an explicit per-capability blocker; never fill from realized outcomes or emit plausible placeholders.

Suggested dependency graph: audited features -> binary/spatial probabilities; separate count-rate state + planned effort -> expected count; eligible time-resolved scores + frozen target policy -> actual formal targets; graph/travel policy + ex-ante spatial/count output -> route alternatives; prior route + live pre-cutoff context -> rerouting. Detection estimator consumes its independent-opportunity fitted state/context and has distinct semantics. Count may depend on an ex-ante chosen route allocation only if route selection used a fixed reference-intensity field first: prohibit a cyclic 'count needs route, route needs final count' graph.

PredictionBundle contains composite hash, per-component state/input/output hashes, ordered execution receipts, actual capabilities emitted, per-output statuses and typed payloads. `produced_outputs` is computed from successfully executed outputs, checked against declared capabilities; it is not copied from the manifest. Legitimate zero expected count or zero targets after an executed policy is different from an absent adapter: retain execution receipt, empty-result reason and ensuing metric limitations. Targets include fixed 100m/600s semantics and actual coordinates/times; scores with timestamps alone do not satisfy the formal capability.

Task4 issuer selects the actual currently active composite, validates its complete code/state/input closure, invokes predict_composite and freezes the returned payload. Its inference_sha256 covers the whole PredictionBundle, not only spatial rows. Before atomic publication recheck all consumed source/state/code hashes, actual time and Champion event. Never accept externally supplied output plus a valid composite ID as inference proof. Pn uses a new immutable version, retaining its own cutoff and after-cutoff scope.

## Complete code identity and production reproducibility

Replace single-file code binding with a deterministic reviewed manifest of all inference-relevant modules: composite/adapter dispatch, feature transforms and fitting-state decoder, spatial/count/detection/time/graph/route algorithms, geometry, contracts, applicable schemas and numerical/runtime dependency identities. Bind actual imported implementations to this manifest; a model-supplied list cannot omit a changed helper. Prefer a fixed registry-owned closure list and verify it against the reviewed code tree. Fit/evaluation code identity is recorded separately and linked to training/validation evidence; prediction closure is not a substitute for proving how the model was trained.

The implementation may use a reviewed source-tree hash as the initial conservative closure, accepting that unrelated code changes invalidate compatibility. Do not hash only model_evaluation.py while new imported modules can change predictions. Record Python/dependency versions used, deterministic seeds/tie rules and numerical tolerances. Reproduction must compare complete structured outputs under the approved deterministic/tolerance contract; model IDs and self-reported PASS are insufficient. Task8 ties this evidence to exact CI/reviewed repository revision and trusted activation event without new Actions permissions.

## Applicability and gates

Policy owns mandatory spatial/stage/formal capabilities. A binary-only or count-only partial recipe can be useful research but cannot satisfy full-scope promotion. Missing complete outcome denominator, independent confirmation, cross-year support or formal validation remains blocked even if every inference adapter runs. None of those gates is waived by composite packaging.

Conditional capabilities require an approved product scope and evidence-backed applicability: route/rerouting depends on a declared mode, graph/constraints and live use case; detection requires independent known-positive opportunities. If the owner requests a capability and its data is absent, use DATA_BLOCKED; missing executor is IMPLEMENTATION_BLOCKED. NOT_APPLICABLE needs an affirmative policy/scope explanation, not missing data or a candidate omission. Absent inputs for a mandatory issuance capability prevent a full-scope production issuance; an explicitly policy-approved partial issuance must clearly retain its limitations and must not promote a partial candidate under full-scope gates.

Tonight Activity's biological target is unresolved. `capture_activity_proxy` is a separately named supplementary count-derived output and never a declared implementation or validation of biological Tonight Activity. Detection probability, encounter probability and expected captures remain distinct. No multiplicity of output names creates new evidence.

## Minimal integration and tests

Use Task6c src/output_adapters.py for fixed registry/shared envelope and a small new src/composite_inference.py for v2 validation/dispatch; do not create parallel registries. Parent integrates narrow edits in champion_registry.verify_model, issue_prediction snapshot/dispatch/payload, model_evaluation recipe selection and model schema. Preserve v1 behavior and Task4 sandbox/production authority separation until Task8 implements the trusted path.

Required joint tests: swapped component/config changes composite identity and requires revalidation; unknown adapter/cyclic graph rejected; changed helper outside model_evaluation invalidates code closure; missing feature/planned effort never defaults; actual spatial/count/target/route output changes with known changed component state; target generator executes on ex-ante inputs and cannot consume outcomes; model ID stamped onto arbitrary output rejected; empty-but-executed output distinguished from absent adapter; conditional missing data not NOT_APPLICABLE; proxy not biological Activity; per-output validation cannot hide mandatory formal failure; fourth recipe/selection-eligible ablation rejected; all component work shares deadline; complete inference reproduction and previous ORIGINAL hash preservation.
