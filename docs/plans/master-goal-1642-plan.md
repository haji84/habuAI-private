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

- [ ] Write adversarial regressions for every specified behavior and observe failures.
- [ ] Implement corrections without duplicating pipeline or changing KPI.
- [ ] Run affected unittest files and all existing tests, update overly permissive PASS expectation to truthful PARTIAL/NOT_VALIDATED with stronger assertions, not test weakening.
- [ ] Commit and report exact tests and remaining provenance limits; independent review required.

## Task 2: master contracts, evidence snapshot and durable parent

Allowed paths src/master_contracts.py, src/master_orchestrator.py, scripts/run_pdca.py, tests/test_master_orchestrator.py, schemas/master-*.json.
Interfaces: run_master(root:Path,night:str,budget_seconds:int=300)->dict; call existing run_pipeline for operational stage; later imports evaluate_models(root,night,budget_seconds)->dict and champion decision from Task 4. Missing module/adapter => BLOCKED implementation reason, not silent success.
Hash all consumed data/predictions/features/model/protocol/code; exclude mutable generated reports except explicit legacy report input. Record baseline input hashes and compare protected raw/ORIGINAL after run. Store reports/pdca/night/runs/run_id/{run_manifest,evidence_manifest,stage outputs}. Atomic checkpoint, deterministic run_id, stage output digests verified on resume. Local exclusive lock; duplicates return verified existing results, code/data/policy/Champion changes new ID. All required stage names returned even if missing predictions; independent research still attempted. Never return only early operational error. Existing reports/pdca/night/pdca_result.json is generated compatibility summary and master status governs it. On exception write FAIL for current run, never read old report as success. Record budget exhaustion and required retry conditions.

- [ ] Test missing evidence yields all stages with concrete blockers, raw/ORIGINAL exact, idempotency, changed inputs, corrupted checkpoint, interruption and budget exhaustion.
- [ ] Implement canonical contracts, safe path validation, atomic JSON and orchestration integration.
- [ ] Run contract/unit/CLI tests. Commit and independent review.

## Task 3: bounded model evaluation and research

Allowed src/model_evaluation.py, tests/test_model_evaluation.py, schemas/model-learning.json. Interface evaluate_models(root,night,budget_seconds=300)->dict with stages/results/evidence/decision fields consumed by orchestrator. Read LearningSnapshot contract only; absent audited snapshot BLOCKED with required fields, never convert legacy 10m data silently. Candidate families: uniform baseline, smoothed historical capture prior by area, smoothed exposure-normalized area rate; max3. Fit each held-out fold from earlier nights with label availability strictly prior to test night/cutoff; features by cutoff. Candidate universe independent of evaluation GPX. Identical folds/universe. Evaluate Stage1 1km Top10 per fold, then 500/250/100 metrics as separate stage statuses. Formal KPI not produced unless model emits actual time targets; report NOT_PRODUCED, never rename cell classification as formal KPI. Count/activity/detection/route/rerouting only if actually implemented; otherwise explicit missing executor BLOCKED. Research questions for missing features/uncertainty, descriptive associations on observed units; true model-feature ablation retrains supported feature-aware candidate or reports NOT_VALIDATED, never relabel spatial diagnostic. Calibration where probabilities valid; drift distribution comparison descriptive. REPLAY distinct immutable run artifacts. Reject nonimprovements; NEED_MORE_DATA with less than five held-out nights/cross-year/uncertainty/downstream evidence. No promotion on these simple baselines without all gates. Record remaining unsupported model/output adapters honestly in completion ledger.

- [ ] Adversarial tests for same-day/future features, labels, conflicting units, nonfinite values, absent universe, unknown label, upstream failure, insufficient folds.
- [ ] Implement bounded real computations and precise blockers for missing scientific/executable adapters.
- [ ] Synthetic reproducibility/model comparison tests plus historical snapshot availability audit. Commit and independent review.

## Task 4: Champion registry and prediction lineage

Allowed src/champion_registry.py, scripts/freeze_prediction.py, tests/test_champion_registry.py, tests/test_prediction_lineage.py. APIs validate_candidate(root,validation)->dict; promote(root,model_id,evidence_path,expected_previous)->dict; rollback(root,target_id,reason,expected_previous)->dict; champion_at(root,cutoff)->dict|None. Artifact and evidence hashes verified; no accepting caller boolean PASS. Decision gates from spec. Model records append-only; event/current pointer compare-and-swap and atomic under exclusive lock; rollback only previously validated model. Future Freeze consumes Champion by issuance timestamp, records event/model/data/features; rejects mismatched supplied lineage; existing records untouched. PDCA may produce a decision but production activation requires persisted verification, not local simulation. Tests may construct synthetic verified artifacts, must label evidence synthetic and prevent production activation unless explicit test sandbox.

- [ ] Test tampered evidence, absent gates, insufficient folds, concurrent CAS, rollback, historical issuance cutoff, next P0 after promotion and immutable previous ORIGINAL.
- [ ] Implement registry and freeze integration without loosening legacy semantics.
- [ ] Run focused tests and independent review; expose real-world promotion as BLOCKED if evidence absent.

## Task 5: bridge integration, historical dry-run and full E2E

Allowed .github/workflows/pdca-command.yml, .github/workflows/pdca-command-poller.yml, tests/test_master_e2e.py, docs/specs/master-goal-1642-status.md; parent integrates reviewed code. Shared workflow concurrency across both entry paths. Validate date using datetime.date, remove stale report before run, fail report on nonzero/unexpected termination, persist every status including BLOCKED artifacts. Duplicate command key/night + input snapshot prevents duplicate publication; recoverable processing marker with timeout or a single shared execution path. Do not change permissions/secrets. Existing owner authorization maintained.

- [ ] Test one CLI command reaches every stage including unsupported ones as BLOCKED/NOT_VALIDATED, no false master PASS; synthetic Champion lifecycle in sandbox.
- [ ] Run complete tests, historical September28 dry-run in isolated copy with exact evidence, protected hash comparison.
- [ ] Independent whole-branch review, publish bounded PR, inspect real CI and repair within scope.
- [ ] After eligible merge run actual bridge issue and inspect result/PR evidence. No fabricated full success if model learning snapshot/adapters missing. Keep Master Goal open with exact remaining requirements and next bounded slice.

## Completion ledger

Design covers every Issue bullet through gap matrix. This plan establishes safe executable foundations and explicitly identifies further adapters needed; it is not authorization to declare the full master complete when an adapter is still missing. Subsequent bounded slices must implement scientific adapters when their required evidence/contracts exist. Missing provenance/data cannot be manufactured to force completion.
