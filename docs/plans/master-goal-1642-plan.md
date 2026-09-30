# Habu Master Goal #1642 Implementation Plan

> For agentic workers: use superpowers:subagent-driven-development. User authorized autonomous execution after design; do not ask routine confirmation. No worker redesigns architecture.

Goal: extend the existing command through audited scoring, model research/competition and validated future Champion handoff.
Architecture: docs/specs/master-goal-1642.md. Python existing dependencies. Canonical baseline c1acabe1e2e6f6959c0a949bd18c37f174480c5a. Snapshot imported through GitHub API because local clone authentication unavailable; remote commits must build on original full tree, not the incomplete local index.

## Global Constraints

- Raw bytes and ORIGINAL P0/P1/P2... are immutable.
- Unknown is not Negative. Night boundary is 07:00 Asia/Tokyo.
- Formal KPI is 100m ±10min. Stage1 is 1km Area Top10 Recall >=0.90.
- No silent test/governance weakening, fabricated data or success. Existing M0–M3 definitions stay frozen.
- Only registered bounded candidate models; never arbitrary model-generated shell/code.
- Retain existing command bridge and entrypoint. No external dependency/permission/security changes.
- All modifications use branch, tests, independent review and PR. Remote Actions evidence distinct from local tests.

## Review Focus

- Tampered/partial provenance must not become official scoring (Task 1).
- Concurrent rerun or corrupt checkpoint must not reuse stale success (Task 2/5).
- Future feature/label availability must invalidate model evidence (Task 3).
- Forged promotion or changed evidence must not select production model (Task 4).
- Data insufficiency versus missing implementation remains explicit in whole-chain E2E (Task 5).

## Task 1: operational integrity and truthful metrics

Allowed paths src/pdca_pipeline.py, scripts/freeze_prediction.py, tests/test_*pdca*.py, tests/test_recovered_prediction.py, tests/test_master_scoring.py, tests/test_canonical_evidence.py. Preserve old raw/predictions/reports.

Interfaces: keep run_pipeline(root,night), score_prediction(prediction,captures,night, exposure=None), verify_predictions(predictions). Existing score keys retained. Add optional exposure argument; no observed evidence means unmatched predictions UNKNOWN, precision based only on matched/observed-negative targets. Use fixed 100m and 10min in formal matching. Targets at/before cutoff not prospective. Deterministic maximum-cardinality one-to-one matches. Cell positives use same floor(UTM/100) and 10min bucket as evidence. Capture parser rejects noncapture/invalid counts/contradictory night, validates coordinates, no inferred captures from blank event types. Hash FAIL never downgrades; missing hashes not official eligible; payload class/night checks at pipeline. Historical scores validate and remain diagnostics; stage renamed or marked NOT_VALIDATED model evaluation. Missing candidate validation NOT_VALIDATED/BLOCKED, not PASS. Freeze checks input class/version ordering/date path and rejects REPLAY/retroactive class relabel; retain old existing records untouched. Full new Champion lineage is Task 4.

- [x] Write adversarial regressions for every specified behavior and observe failures.
- [x] Implement corrections without duplicating pipeline or changing KPI.
- [x] Run affected unittest files and all existing tests, update overly permissive PASS expectation to truthful PARTIAL/NOT_VALIDATED with stronger assertions, not test weakening.
- [x] Commit and report exact tests and remaining provenance limits; independent review required.

## Task 2: master contracts, evidence snapshot and durable parent

Allowed paths src/master_contracts.py, src/master_orchestrator.py, scripts/run_pdca.py, tests/test_master_orchestrator.py, schemas/master-*.json.
Interfaces: run_master(root:Path,night:str,budget_seconds:int=300)->dict; call existing run_pipeline for operational stage; later imports evaluate_models(root,night,budget_seconds)->dict and champion decision from Task 4. Missing module/adapter => BLOCKED implementation reason, not silent success.
Hash all consumed data/predictions/features/model/protocol/code; exclude mutable generated reports except explicit legacy report input. Record baseline input hashes and compare protected raw/ORIGINAL after run. Store reports/pdca/night/runs/run_id/{run_manifest,evidence_manifest,stage outputs}. Atomic checkpoint, deterministic run_id, stage output digests verified on resume. Local exclusive lock; duplicates return verified existing results, code/data/policy/Champion changes new ID. All required stage names returned even if missing predictions; independent research still attempted. Never return only early operational error. Existing reports/pdca/night/pdca_result.json is generated compatibility summary and master status governs it. On exception write FAIL for current run, never read old report as success. Record budget exhaustion and required retry conditions.

- [x] Test missing evidence yields all stages with concrete blockers, raw/ORIGINAL exact, idempotency, changed inputs, corrupted checkpoint, interruption and budget exhaustion.
- [x] Implement canonical contracts, safe path validation, atomic JSON and orchestration integration.
- [x] Run contract/unit/CLI tests. Commit and independent review.

## Task 3: bounded model evaluation and research

Allowed src/model_evaluation.py, tests/test_model_evaluation.py, schemas/model-learning.json. Interface evaluate_models(root,night,budget_seconds=300)->dict with stages/results/evidence/decision fields consumed by orchestrator. Read LearningSnapshot contract only; absent audited snapshot BLOCKED with required fields, never convert legacy 10m data silently. Candidate families: uniform baseline, smoothed historical capture prior by area, smoothed exposure-normalized area rate; max3. Fit each held-out fold from earlier nights with label availability strictly prior to test night/cutoff; features by cutoff. Candidate universe independent of evaluation GPX. Identical folds/universe. Evaluate Stage1 1km Top10 per fold, then 500/250/100 metrics as separate stage statuses. Formal KPI not produced unless model emits actual time targets; report NOT_PRODUCED, never rename cell classification as formal KPI. Count/activity/detection/route/rerouting only if actually implemented; otherwise explicit missing executor BLOCKED. Research questions for missing features/uncertainty, descriptive associations on observed units; true model-feature ablation retrains supported feature-aware candidate or reports NOT_VALIDATED, never relabel spatial diagnostic. Calibration where probabilities valid; drift distribution comparison descriptive. REPLAY distinct immutable run artifacts. Reject nonimprovements; NEED_MORE_DATA with less than five held-out nights/cross-year/uncertainty/downstream evidence. No promotion on these simple baselines without all gates. Record remaining unsupported model/output adapters honestly in completion ledger.

- [x] Adversarial tests for same-day/future features, labels, conflicting units, nonfinite values, absent universe, unknown label, upstream failure, insufficient folds.
- [x] Implement bounded real computations and precise blockers for missing scientific/executable adapters.
- [x] Synthetic reproducibility/model comparison tests plus historical snapshot availability audit. Commit and independent review.

## Task 4: Champion registry and prediction lineage

Allowed src/champion_registry.py, scripts/freeze_prediction.py, tests/test_champion_registry.py, tests/test_prediction_lineage.py. APIs validate_candidate(root,validation)->dict; promote(root,model_id,evidence_path,expected_previous)->dict; rollback(root,target_id,reason,expected_previous)->dict; champion_at(root,cutoff)->dict|None. Artifact and evidence hashes verified; no accepting caller boolean PASS. Decision gates from spec. Model records append-only; event/current pointer compare-and-swap and atomic under exclusive lock; rollback only previously validated model. Future Freeze consumes Champion by issuance timestamp, records event/model/data/features; rejects mismatched supplied lineage; existing records untouched. PDCA may produce a decision but production activation requires persisted verification, not local simulation. Tests may construct synthetic verified artifacts, must label evidence synthetic and prevent production activation unless explicit test sandbox.

- [x] Test tampered evidence, absent gates, insufficient folds, concurrent CAS, rollback, historical issuance cutoff, next P0 after promotion and immutable previous ORIGINAL.
- [x] Implement registry and freeze integration without loosening legacy semantics.
- [x] Run focused tests and independent review; expose real-world promotion as BLOCKED if evidence absent.

## Task 5: bridge integration, historical dry-run and full E2E

Allowed .github/workflows/pdca-command.yml, .github/workflows/pdca-command-poller.yml, tests/test_master_e2e.py, docs/specs/master-goal-1642-status.md; parent integrates reviewed code. Shared workflow concurrency across both entry paths. Validate date using datetime.date, remove stale report before run, fail report on nonzero/unexpected termination, persist every status including BLOCKED artifacts. Duplicate command key/night + input snapshot prevents duplicate publication; recoverable processing marker with timeout or a single shared execution path. Do not change permissions/secrets. Existing owner authorization maintained.

- [ ] Test one CLI command reaches every stage including unsupported ones as BLOCKED/NOT_VALIDATED, no false master PASS; synthetic Champion lifecycle in sandbox.
- [ ] Run complete tests, historical September28 dry-run in isolated copy with exact evidence, protected hash comparison.
- [ ] Independent whole-branch review, publish bounded PR, inspect real CI and repair within scope.
- [ ] After eligible merge run actual bridge issue and inspect result/PR evidence. No fabricated full success if model learning snapshot/adapters missing. Keep Master Goal open with exact remaining requirements and next bounded slice.

## Completion ledger

## Review-driven contract clarifications for all tasks

Read the normative Independent design review resolutions in the spec before implementation. These supersede ambiguous earlier prose. Foundation tasks 1–5 do not close Master. Follow-on 6–8 remain required. No production promotion from caller-supplied metrics or self-declared synthetic flags.

Task2 additional acceptance: replace processed learning input mid-run -> FAIL; change source before resume -> new run or invalidated checkpoint; no stale success. Include execution_status/validity_status/gate_outcome where applicable and implementation_blockers separately from data_blockers. All consumed inputs rehashed before final success. Shared runtime/dependency identity and cumulative round/budget ledger.

Task3 result contract: {schema_version:'1.0', stages:[{name,status,reason,requires,evidence,metrics,implementation_version}], candidates:[], folds:[], replay:[], research_questions:[], decision:{decision,reasons,required_conditions}, implementation_blockers:[], data_blockers:[]}. Actual canonical inference interface predict_model(model:dict, universe_rows:list[dict])->list[dict] must be added before production handoff. Avoid calling unit prevalence effort correction. Explicit immutable universe and availability are required. Any lacking contract returns specific blocker without invented rows.

Task4 owns new scripts/issue_prediction.py and tests/test_prediction_lineage.py in addition to earlier paths. It must execute predict_model from a verified registered model; exact output must change when known test Champions differ. Generic imported payloads do not automatically gain Champion origin. Production activation fails closed pending trusted runner/CI adapter; sandbox lifecycle requires an explicit isolated sandbox path controlled by tests, not an evidence boolean.

### Follow-on Task 6: substantive model/research and conditional output adapters

Depends on Tasks2–4 and accepted Learning/Universe contracts. Files src/feature_research.py, src/model_evaluation.py, src/route_evaluation.py; tests/test_feature_research.py, tests/test_route_evaluation.py. Freeze development/confirmation split artifact before fitting; fit feature-aware registered models with train-only transforms, univariate -> adjusted multivariate -> bounded interaction candidates, true retraining ablation; select using development only and validate once on untouched confirmation. Measured effort required for effort-corrected claims. Count/activity models require complete-session event counts and duration; detection requires observation-process labels; route evaluation requires approved ex-ante graph, travel costs, constraints, route outputs and observed route evidence. Test missing inputs explicitly DATA_BLOCKED. No new unsupported biological or causal claim.

### Follow-on Task 7: approved bounded development executor

Use current owner-authorized active PDCA Chat/Codex plus existing GitHub connector, as reviewed in docs/reviews/master-goal-1642-codex-controller-design.md. AI-/Compass adapter is optional and is not a blocking prerequisite. Implement src/development_handoff.py, fixed controller protocol/helper under scripts/, schema and tests, minimal orchestrator integration and a concrete controller runbook. Actions persists typed requests bound to master1642/command/run/evidence/base/scope; active controller claims, delegates Codex, verifies changed paths/tests/independent review/exact-head CI/PR through real connector reads, persists receipts and resumes backend without another user instruction. No arbitrary model shell, new authority, credentials or permission changes. Persist/reconcile operation IDs and cumulative budgets across clean-controller restart. Actual active-session live acceptance is mandatory; automatic wake-up after Work session termination is a separate unproven capability, not inferred from durable JSON.

### Follow-on Task 8: verified production activation and live complete-chain acceptance

Depends on Tasks5–7. Bind candidate code/data/protocol/evidence commit to repository CI and independent verification, independently reproduce metrics from immutable fold records, persist CAS Champion event through reviewed PR with existing permissions. Test forged self-consistent evidence rejected. Exercise actual Champion inference on a future issuance, compare earlier ORIGINAL hashes. Run duplicate commands across distinct runner workspaces and verify one durable publication/transition. Only then evaluate Master completion against all 112 traceability rows. Scientific input insufficiency remains separately reported; unimplemented/runtime-blocked paths prevent completion.

Design covers every Issue bullet through gap matrix. This plan establishes safe executable foundations and explicitly identifies further adapters needed; it is not authorization to declare the full master complete when an adapter is still missing. Subsequent bounded slices must implement scientific adapters when their required evidence/contracts exist. Missing provenance/data cannot be manufactured to force completion.

## Execution order refinement

After reviewed foundations1–5, implement Task6a evidence audit/learning builder, then Task7 current Chat/Codex controller. Drive a useful remaining Task6b/c implementation through that controller for live consume/delegate/review/CI/return acceptance. Continue substantive scientific/output adapters before Task8 production trust and whole-master acceptance. This ordering removes implementation gaps; it does not convert missing data or unvalidated science into success. Feature-model detail: docs/plans/master-goal-1642-feature-models.md. Numerical/output/route details will be committed as their bounded briefs are finalized.

## Main integration gate refinement

Task5 independent review requires terminal receipt/result binding, report-only prior-tree verification and corrupt-receipt queue isolation. Whole-branch review also confirms that current GPX-only negative/FP eligibility needs Task6a before main integration. Therefore finish/re-review Task5, implement/review Task6a, publish explicit full-tree changes, verify exact-head CI, then integrate and exercise the real owner-command bridge. This is autonomous bounded repair, not a new Human Gate. Substantive controller/research/output/trust slices remain outstanding.
