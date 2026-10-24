# Codex parallel lanes, ownership, dependency DAG and bounded handoff contracts

Authority: [Master handoff](CODEX_PARALLEL_MASTER_20261025.md), Master Goal [#1642](https://github.com/haji84/AI-/issues/1642). **Current code must be audited; names below assign WORK, not assert completion.** Each task begins with exact HEAD and a small Gap. Worktree/branch required per worker. Coordinator alone writes shared state and integrations.

## G0: one short serialization barrier before broad parallel modelling

Read `src/evidence_audit.py`, `src/learning_snapshot.py`, `schemas/model-learning.json`, `src/model_evaluation.py`, `docs/plans/master-goal-1642-training-corpus.md`, `docs/plans/master-goal-1642-feature-models.md`, `docs/plans/master-goal-1642-composite-inference.md` and **open** PR #32/#33/#46. Define the minimal shared interfaces in an RFC/contract-test PR (do not rewrite parent interfaces). Independently hostile-review schema, eligibility and feature availability *before* parallel branches consume them.

Freeze the following for one development cycle: observation type/label/effort, source hashes, event date, 07:00 time handling, forecast valid time, collected/usable time, spatial geometry, universe composition, model target/score semantics, fold split assignment, metric denominators, sealed-confirmation selection. Document schema version and code hash. An unknown row has label=null, not 0. Until the contract passes, independent worker tasks can audit/read/design/tests but cannot silently invent their own row schema.

## Active lanes after G0 (run concurrently when resources allow)

| Lane | Owner, independent output | First bounded task | Interfaces / files uniquely owned | Must return before downstream |
| --- | --- | --- | --- | --- |
| **E** Evidence eligibility & source audit | source-qualified, **UNKNOWN-safe** observation/ascertainment view | Reassess PR #84 four motion-uncertain packets, then the remaining 71; compare real sighting/capture/roadkill/source GPX and genuine search-vs-transit evidence; separately test completeness-of-capture recording and individual ID ledger | new `src/observation_eligibility_*.py`, `tests/test_observation_eligibility_*.py`, private `reports/evidence_review/`; **do not edit** `data/raw/` or source `src/evidence_audit.py` without boundary review | hashed candidate rows, complete/partial/unknown reasons, source-linked review packets; **never** quietly promote 3,491 cells |
| **F** Forecast universe and feature research | forecast-only feature materialization and validated source availability | inspect and reuse **open PR #32/#33**; implement ex-ante road candidate universe joining terrain/road/weather, time windows/label-free feature snapshots, source receipts and strict cutoff | existing PR #32/#33 owned portions; new `src/feature_*_v2.py` only where no collision; `tests/test_feature_*_v2.py` | code fails closed when weather/DEM/road/precise availability missing; no August P0 retrocreation |
| **M1** Occupancy/detection-probability models | fit/predict interface, calibrated area probabilities for a defined target | build honest shrinkage/hierarchical spatial+seasonal baseline and regularized GAM/logistic/GBDT **conditional on eligible binary target denominator**; benchmark historical-prior/uniform and `prospective_candidate_model` | `src/models/occupancy_*.py`, `tests/test_occupancy_*.py`; no modifying `src/model_evaluation.py` concurrently with other model workers | eligible objective, sample count, source/time hashes, probability calibration/coverage diagnostics, NEVER fabricated negatives |
| **M2** Hierarchical road/time ranking | 1km Top10 then conditional 500/250/100/10min score ladder | implement hierarchical ranking with spatial regularization / Bayesian smoothed priors, temporal cyclic features, geography constraints and candidate set accounting; compare ranking models and tree/boosting **only where real eligible rows exist** | `src/models/hierarchy_*.py`, `tests/test_hierarchy_*.py`; reuse open **PR #46** after exact diff audit rather than duplicate | 1km Top10 denominator including eligible out-of-universe misses; 100m×10min timestamp alignment; no false gate successes |
| **M3** Count, activity, detection and ensemble | distinct target heads and fair ensemble/stacking proposals | explicit effort-offset count (Poisson/NB/zero-inflated *if identifiable*), activity vs detectability distinction, seasonal/event-size head if individual count/size is verified; ensemble of M1/M2 only with OOF TRAIN predictions | `src/models/count_*.py`, `src/models/ensemble_*.py`, `tests/test_count_*.py`, `tests/test_ensemble_*.py` | if effort/individual IDs missing return `NEED_MORE_DATA` rather than fit fake rates or large-Habu claims |
| **V** Independent evaluation/hostile reviewer | **do not write fit code**, owns canonical fold manifests, sealed confirmation protocol, model comparison and adversarial falsification | implement day/night+island+future-blocked and geographic holdouts, embargo, masks, confidence intervals, repeatability, label leakage challenge, external-baseline; verify all methods on genuine eligible test data | `src/evaluation/locked_protocol_*.py`, `tests/test_locked_protocol_*.py`, `docs/reviews/model_*.md`; must not change training labels or model code | signed/hash-bound protocol and independent evidence; BLOCKED when test coverage too small |
| **I** Integrator / UI / Champion bridge | sole authority to modify shared orchestration when contracts pass | inspect actual main interfaces and open PRs, wire selected audited model to `src/model_evaluation.py` and `src/master_orchestrator.py` via adapters, fit/report in isolated REPLAY; preserve sandbox Champion gate until authorized trust prerequisites | `src/model_evaluation.py`, `src/master_orchestrator.py`, `src/champion_registry.py`, `scripts/issue_prediction.py`, UI and E2E tests **only this lane** | one PDCA command end-to-end with explicit PARTIAL/BLOCKED, repeat/resume, future-only Champion consume, no historical P0 edits |

**Worker count is adaptive**. If Codex does not have independent sessions or runner capacity, run E+F+V first; M1/M2/M3 can develop pure interfaces/fixtures in parallel but must not spend compute fitting ineligible data. Do not start seven full training jobs by default. Use short bounded tasks with CI budget/resource caps.

## Dependency and merge DAG

```text
CURRENT main / Master Issue 1642
   │
   ├─ audit existing open #32/#33/#46 and repository safety state
   │
   └─ G0 shared schema+fold+eligibility contracts ── [review, exact-head CI]
         ├─ E: true searched road / complete capture / canonical events ─┐
         ├─ F: ex-ante universe / valid-time + usable_at features ───────┤
         ├─ M1: calibrated occupancy proposals (blocked fit until E+F) ─┤
         ├─ M2: hierarchy/time rankers (blocked fit until E+F) ──────────┤
         ├─ M3: count / activity / ensemble (blocked fit until E+F+M1/M2)┤
         └─ V: sealed folds/target metrics + independent review ──────────┘
                                      │
                         V compare frozen eligible artifacts
                                      │
             I adapters + model-versioned REPLAY / CI / E2E
                                      │
                science gates / trusted authority gate
                ├─ fail ⇒ NEED_MORE_DATA / BLOCKED + bounded next task
                └─ pass ⇒ authorized Champion future-only handoff
                                      │
                     legitimate future P0/Pn + post-night PDCA
```

**Avoid premature dependency flattening**: M1/M2/M3 module implementation may run while E/F are BLOCKED; training/evaluation/probability claims may not. Likewise a model never becomes a Champion because CI passed on simulated fixtures.

## Coordinator lane contract (copy as worker prompt header)

```text
You are Codex worker <LANE> for haji84/habuAI-private.
Authoritative Master Goal: haji84/AI- Issue #1642.
Read AGENTS.md and docs/work/CODEX_PARALLEL_MASTER_20261025.md,
CODEX_LANES_20261025.md, CODEX_MODELS_20261025.md and CODEX_ACCEPTANCE_20261025.md.
Do not replace architecture or bypass evidence gates. Do not work outside YOUR
assigned file ownership. Work in a fresh branch/worktree from current main;
list OPEN existing PRs before new feature implementations.
First deliver a small source-grounded Gap/contract + test; then implement
the smallest useful bounded slice, tests, CI, failure repair on the same PR,
independent review, exact-head proof and safe integration request.
Source-only/fixture-only evidence is never a scientific PASS. Treat absent
evidence as UNKNOWN or NEED_MORE_DATA. Do not add production authority,
billing, secrets, network/public exposure or breaking data changes.
Return commit, PR URL, test/run links, exact files, sample counts/fold evidence,
scientific PASS/PARTIAL/BLOCKED, blockers, next unblocked task.
```

## Merge/conflict discipline

- Begin by inspecting open #32, #33, #46, #44, #45, #50, #73. Rebase/reconcile *without* force-pushing away other evidence; if a PR owns the same feature, repair **that PR** rather than create a duplicate.
- Lane code stays within owned namespace. Shared `model_evaluation.py`, `src/evidence_audit.py`, `master_orchestrator.py`, `champion_registry.py` belong to **I/E integrator gate only**. No direct competing edits across tasks.
- V signs the evaluation contract before candidate comparison; final model selection is frozen *before* untouched confirmation is exposed. Distinct challenger fits may run simultaneously on identical eligible TRAIN folds; publishing test/confirmation outcomes to fitting workers early is forbidden.
- Reuse previous PRs; Fixer repairs the existing branch. One logical feature slice per PR, not one PR per failed test. No bypass of exact-head CI or SHA drift.
- On dependency mismatch, stop the integrating branch, record an issue with precise blocking schema/file field, fix on owning lane, then rerun consumers.
- After validated merge, run tests on fresh main and update `CODEX_STATE_20261025.json` in one coordinator-controlled follow-up change. If an automated loop cannot persist a runner, stop cleanly and provide an immediately restartable GitHub/Work command, not a claim of continuous execution.

## Lanes' mandatory output record

Each bounded PR must include:
`lane_id`, `base_main_sha`, `current_head_sha`, `master_requirement_ids`, `owned_paths`, `deps`, `source_sha256[]`, `eligibility_counts` (eligible/unknown/rejected), `input_cutoff_utc/JST`, `target_semantics`, `test_command`, `ci_run_url`, `review_status`, `scientific_status`, `blocked_reason`, `merge_decision`, `next_unblocked_slice`.

To claim a metric PASS include `fold_manifest_sha`, `universe_sha`, `denominator_capture_event_ids`, `observed_exposure_proof`, `prediction_time_cutoff`, `model_sha`, `n_train_nights`, `n_validation_nights`, `n_independent_confirmation_nights`, `denominator`, `numerator`, and valid uncertainty interval. If any are absent, classify formally `NOT_VALIDATED`.
