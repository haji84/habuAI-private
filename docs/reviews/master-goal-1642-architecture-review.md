# Independent design review: Master Goal #1642

Scope: read-only review of AGENTS.md, canonical owner snapshot, proposed spec and five-task plan, gap matrix, and relevant baseline freeze/workflow code. No repository changes. This reviews the proposed architecture, not implemented acceptance results.

Verdict: suitable direction for a safe foundation PR after the contract gaps below are resolved; not a plan that can deliver the whole owner goal in its current five slices. The explicit completion caveat is correct and must survive implementation/reporting. Missing implementation is not evidence insufficiency.

## Important findings

### 1. High: the five slices deliberately stop before required execution exists

Task 3 promises only uniform and two spatial-history candidates, descriptive research, and BLOCKED/NOT_PRODUCED for formal temporal, activity/count, route and other unsupported adapters. The development stage creates a request, not branch -> implementation -> test -> CI -> independent verification -> PR execution. Task 4 provides a local registry, with production activation left to an unspecified reviewed persistence workflow. These are honest foundations but cannot satisfy the owner's automatic whole-chain experience. The final ledger says subsequent slices must implement them, without dependency order, concrete deliverables or executable handoff contracts.

Resolution: name this milestone Foundation and explicitly schedule bounded follow-on slices for research/feature-aware models, remaining applicable evaluators, development executor and persisted production handoff. For every requirement record IMPLEMENTED, DATA_BLOCKED or IMPLEMENTATION_BLOCKED separately. Do not close the master based on all stage names appearing or an all-synthetic E2E. Actual data can block scientific validation; it does not excuse leaving the generic executor unimplemented.

### 2. High: promotion trust is not established by artifact hashes

Spec calls evidence signed-by-content while correctly acknowledging no identity. Task 4 verifies artifact hashes and recomputes gates, but neither defines a trusted origin for splits, fold predictions/labels, policy/code identity and CI results nor specifies independently recomputing metrics from those immutable records. An attacker or accidental caller can create mutually consistent fabricated evidence and hashes. A self-declared synthetic flag can also be removed. The production write/approval mechanism is explicitly deferred.

Resolution: define the trust boundary: trusted runner must evaluate immutable dataset/model/protocol artifacts; registry independently recomputes required metrics or verifies trusted CI/runner attestation bound to exact candidate commit, evidence hash, policy and protected activation workflow. Caller-supplied metrics, code hashes and synthetic flags must not establish authority. Fail production closed until that mechanism exists. Test fully self-consistent forged evidence, not only tampered single files or boolean PASS.

### 3. High: freeze lineage is not proof that the Champion produced a prediction

Baseline freeze accepts arbitrary JSON from --input; Task 4 says to consume Champion lineage and reject mismatched supplied lineage. Correct metadata can still be attached to arbitrary predictions. There is no inference adapter or reproducible prediction artifact contract in the plan, so 'next issuance consumes the promoted Champion' could be tested as tagging only. Also spec alternates 'issuance timestamp' and 'issuance cutoff' for registry selection; user-supplied created_at/cutoff_time must not backdate Champion selection or future-only activation.

Resolution: require prediction surface to execute a registered Champion inference adapter, or verify its immutable, independently reproducible output, and bind output hash to inference inputs/model. Define trusted issued_at/frozen_at versus forecast cutoff semantics, activation ordering and prospective horizon. Test materially different Champion outputs and reject correctly tagged arbitrary output; reject caller backdating to select an earlier model. Preserve existing historical limitations rather than retroactively requiring historical lineage.

### 4. High: LearningSnapshot omits data needed by a planned model and its evaluation

Rows encode observed boolean and binary label but no search duration/distance, observer/search method, valid effort denominator or capture count. Task 3 promises an 'exposure-normalized area rate'; observed row count alone is a unit-occupancy denominator, not necessarily effort correction. candidate_universe_sha256 is a hash without a referenced universe artifact or schema enumerating candidate cells/times and availability. If implementations rank only rows that survived observation eligibility, evaluation GPX can leak into the forecast universe despite the prose prohibition.

Resolution: separate forecast universe artifact (all eligible cell/time units with ex-ante availability and domain definition) from ex-post observation/label evidence. Add explicit measured effort fields and applicability, or rename the candidate honestly as observed-unit prevalence without claiming effort normalization. Define capture-event versus occupied-unit Stage1 recall, duplicate event handling, 500/250/100 aggregation and observation support. Test an unobserved high-ranked candidate and variable search duration.

### 5. High: adaptive improvement can reuse its own held-out evidence

Walk-forward restrictions protect training within individual folds, but the plan also generates hypotheses from diagnosed failures and permits two improvement rounds. Nothing prevents feature/model selection after examining the same held-out labels, then treating a positive paired result on those nights as independent validation. Five distinct nights and two calendar years do not fix adaptive test reuse, repeated peeking or multiplicity across three candidates/rounds. 'Uncertainty excluding no improvement' lacks metric, resampling unit and selection procedure.

Resolution: freeze protocol/model/selection rules before reveal; use nested temporal development and untouched confirmation folds or fresh prospective nights for promotion. Track which nights informed research or prior selection. Specify paired primary metric, night-level dependence-aware uncertainty method and handling of selection/multiplicity, zero-positive nights and coverage. Block promotion after tuning on confirmation labels.

### 6. Medium/high: reproducible manifest hashes do not alone create an immutable input snapshot

Task 2 says hash all consumed sources and records input manifests, but evaluator interfaces still take mutable root paths. Inputs can change between initial hash, stage reads and checkpoint completion. Only raw/ORIGINAL get explicit after-run comparison. Likewise snapshots available now need verifiable availability history, not caller assertions, to establish historical cutoff eligibility.

Resolution: consume a content-addressed read-only snapshot or validate each read against a pinned manifest and revalidate every consumed source before committing evidence. Include actual code, dependencies/runtime, protocol/policy and all feature/universe artifacts. Define availability provenance and which records are admissible historical evidence. Add mid-run learning-file replacement and resumed-run source replacement tests.

### 7. Medium: cross-year policy and stage policy are ambiguous

Spec requires two years 'for a cross-year claim'; Task 3 says NEED_MORE_DATA with insufficient cross-year evidence without qualification. Promotion says 'all declared downstream gates', which can let a candidate declare fewer outputs unless mandatory gates are defined independently in policy. Conversely a universal cross-year rule can indefinitely block an otherwise valid explicitly within-year operational model. Stage PASS also mixes successful execution and scientific threshold attainment.

Resolution: policy must explicitly list mandatory gates independent of candidate claims, plus conditional gates with evidence-backed applicability. Define whether cross-year is mandatory for production or merely a claim restriction; preserve owner intent and disclose unvalidated generalization. Separate execution status, scientific validity, gate outcome and promotion decision so 'valid NEED_MORE_DATA' is not PASS.

### 8. Medium: the gap matrix is a checklist, not yet requirement-to-implementation traceability

Most rows repeat section-wide prose and identical generic acceptance references. Reaction DB, weather inputs and every requested covariate appear as PARTIAL based on the same pipeline paths without per-item implementation evidence. Automation requirements (no routine clicks, persisted recovery, duplicate command handling) and the final completion criterion are not distinct mapped rows. There are no planned slice, executor, artifact or specific test columns. This allows a section-level foundation to be mistaken for individual requirement coverage.

Resolution: give each requirement its own current evidence, missing executor/data, planned slice, concrete acceptance test and implementation/real-data-validation statuses. Add automation/final-experience rows. Update exact statuses from inspected code; absent weather or reaction adapters should not inherit PARTIAL from unrelated exposure parsing.

### 9. Medium: task ownership and integration contracts are incomplete

Tasks 1 and 4 both own freeze_prediction.py; Task 2 imports Task 3 and Task 4 results whose schemas are described only as generic dictionaries. Development has no assigned module/task executor. Spec promises maximum two improvement rounds but the plan supplies no round transition/checkpoint schema or acceptance test. Shared Actions concurrency serializes execution but alone does not deduplicate publication or recover across fresh runners.

Resolution: order freeze changes explicitly, publish typed/versioned task result and artifact contracts before implementation, define round identities and budget accumulation across retries, assign development ownership, and specify a durable command/publication ledger whose scope distinguishes duplicate commands from intentional reruns with changed inputs. Test event and poller replay across separate clean workspaces, not only a local lock.

## Strengths worth retaining

The proposed architecture preserves the existing bridge and entrypoint; makes fixed KPI, unknown labels, recovery quality, original immutability and upstream gates explicit; corrects known baseline scoring/integrity defects; keeps REPLAY distinct; rejects arbitrary generated shell execution; and explicitly refuses to convert absent science/executors into success. Append-only Champion history, compare-and-swap, content-addressed runs and fail-closed missing adapters are appropriate foundations.

## Acceptance/completion decision

A foundation milestone may pass its engineering acceptance while overall master remains PARTIAL/BLOCKED with named implementation and evidence gaps. Whole-master acceptance additionally requires executable supported research/competition, the bounded development path, trusted persisted promotion and actual Champion-derived next prediction, exercised through the existing owner command with reproducibility/recovery. Unsupported scientific claims may remain NOT_VALIDATED with explicit evidence needs; unbuilt executors must never be silently reclassified as those scientific exceptions.
