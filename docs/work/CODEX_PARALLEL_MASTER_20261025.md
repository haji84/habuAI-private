# HABU-AI Codex parallel development master contract (2026-10-25)

**Canonical repository:** https://github.com/haji84/habuAI-private
**Higher-priority goal:** https://github.com/haji84/AI-/issues/1642
**Status:** EXECUTION_HANDOFF_SPEC, **not** proof of scientific completion, deployed models, new CI results or an already-running autonomous worker.
**Execution coordinator:** Codex lead working from the current repo checkout. Specialist workers may be run concurrently in isolated worktrees/branches; GitHub Actions is the verification and evidence layer, **not** an always-on free autonomous agent.
**Read in order:** `AGENTS.md` → `docs/specs/master-goal-1642-source.md` → `docs/specs/master-goal-1642.md` → this file → `docs/work/CODEX_LANES_20261025.md` → `docs/work/CODEX_MODELS_20261025.md` → `docs/work/CODEX_ACCEPTANCE_20261025.md` → `docs/work/CODEX_STATE_20261025.json`.

## Owner's final objective

Build a scientifically defensible AI for Habu appearance, activity and owner captures on Amami-Oshima and Kakeroma. The complete product must take genuine ex-ante environmental, biological and geographic inputs and predict:
`Tonight` → 1km Top10 candidate areas → 500m → 250m → 100m road zone → **100m × 10-minute** target → genuinely drivable, constrained routes A/B/C.
Prediction issuance before search is separate from PDCA; `P0` is frozen pre-search; `P1+` is frozen version-by-version with cutoff; PDCA scores and researches outcomes; validated Candidate becomes a **future** Champion only after independent promotion gates, never by editing previous ORIGINAL records.

**First formal scientific gate:** 1km Area Top10 Recall ≥90% (using a genuinely eligible denominator and independently future-blocked outcomes). **Ultimate formal target:** 100m ±10min. Target thresholds are goals, not measured success or guarantees.

The owner asks for **parallel implementation to completion**, not more planning-only output. Do not ask for routine approvals or recurring GitHub buttons. Implement, test, independently review, repair in the same PR, integrate safe verified changes and select the next unblocked bounded slice. Do not claim background work or successful model training when no actual executor runs.

## What was directly verified at handoff

- Main already has `src/master_orchestrator.py`, `src/evidence_audit.py`, `src/learning_snapshot.py`, `src/model_evaluation.py`, `src/prospective_candidate_model.py`, `src/champion_registry.py`, `scripts/issue_prediction.py`, `scripts/run_pdca.py`.
- `src/model_evaluation.py` registers **uniform, historical_capture_prior, observed_unit_prevalence, duration_normalized_area_rate** as bounded research baselines. It explicitly lists missing formal time-target, feature retraining/ablation, confirmation lock and count/route executors. The baselines do **not** constitute a high-accuracy finished system.
- `src/prospective_candidate_model.py` contains a **research-only** L2-regularized feature logistic model with strict data/availability checks, not a production-authorized P0 predictor.
- `src/champion_registry.py` is sandbox lifecycle mechanics; `scripts/issue_prediction.py` is fail-closed for production without a trusted, separately approved activation authority. A passing toy/sandbox promotion is not deployment.
- `src/learning_snapshot.py` requires hash-bound ex-ante universe/feature/protocol receipts. It does not create historical forecast universes from observed GPX.
- PR #77–#84 historical August read-only audits were integrated: 12 actual-GPX nights, 231,715 raw points, 8,965 sampled 100m×10min bins, 3,491 **review-only noncapture candidates** clustered into 774 review packets, 75 fauna-linked priority packets, 99 strict sighting anchors. August log native bytes were independently matched (116,496 bytes, SHA-256 `130dedae6e04501f4be41fff4ff549a9cfc1a1840dcbb0126359b04465ab7e8c`). **No** searched-road unit, full capture ledger, formal Positive or formal Negative has been independently qualified from these historical candidates. 71 of the 75 have local slow/stopped motion, four have mixed/insufficient motion; the candidates were already selected partly on GPS speed, so this is **not independent validation**.
- Owner-confirmed **2026 August 47 personally captured Habu** (46 original capture statements, one two-animal note), 2026-10-20 dashboard cumulative **243**. The sum applies to that dated snapshot, **not** an assertion of today's running total. Species sightings, other people’s captures and roadkills stay in separate reaction evidence and never change the owner capture count.
- Archived September-25 OSM is a validated **auxiliary** road source. It is **not** an official GIS road network nor proof that those features were available at a historical August forecast cutoff.
- Existing **OPEN** PRs #32, #33, #46, #44, #45, #50 and #73 were found as of this handoff. Before opening replacement PRs inspect their exact diffs, latest HEAD, declared dependencies and check statuses. In particular **#32/#33/#46 may implement parts of the prospective Universe/Feature/Inference work**; DO NOT duplicate or auto-merge stale work.

## Hard scientific and security constraints (non-negotiable)

1. Immutable `data/raw/**`, `predictions/original/**`, `predictions/recovered_original/**`, original P0/Pn Freeze files, source receipts. Do not delete or rewrite past files or modify model thresholds merely to make tests pass.
2. Operational night ends **07:00 Asia/Tokyo**; 00:00–06:59 belong to the prior search night. P0/Pn cutoff strictly earlier than input availability and forecast issuance as defined by the canonical contracts; forbid leakage.
3. No fabricated trajectories, search routes, weather, road lines, capture individuals, labelling or synthetic performance masquerading as real. `UNKNOWN != Negative`. **PASSAGE + slow GPX + frog sightings are NOT certified active Habu search.** To promote a searched noncapture observation, independent road/time active-search evidence AND applicable complete capture-outcome accounting are needed; scientific label promotion remains blocked until both qualify.
4. Distinguish **personal Habu captures**, other-person Habu captures, direct Habu sighting, Himehabu and other fauna, Habu roadkill and unclassified encounters. Monthly owner counts do not independently authenticate individual IDs. Near-time/location capture statements require dedup review.
5. All training cohort rows carry target semantics, actual observational effort/detection scope, source SHA lineage, event time, valid time, ingestion/audit and `usable_at`, 100m×10min bin and zone IDs. Positive-only history is not a clean probability denominator or proof of noncapture coverage.
6. Ex-ante forecast features must be available **strictly before the evaluated prediction cutoff**. Later retrospective measurements may support appropriately gated later fitting when valid and available; they do not retroactively become inputs to a historical P0 or proof of old forecasting skill. No historic replay forecast may impersonate an ORIGINAL forecast.
7. Challenge the **evaluation denominator**: include out-of-universe confirmed captures as misses if applicable; compare same dated eligible universe and protocol across candidates; freeze target, split, metric and model selection **before sealed confirmation reveal**. Never silently reuse revealed nights as fresh confirmation.
8. Never claim achieved 90%, 100m±10min, promotion, or model improvement without independent future-blocked real evidence and auditable numerator/denominator with uncertainty. A desire for high accuracy is not a measured result.
9. Restrict external network/rate/fees to existing permissions and provider terms. No secrets in logs, PR descriptions or public artifacts. User approval required **before** billing, external publication, persistent infrastructure/public exposure, privilege/auth changes, breaking source migrations, production model authority or Master Goal architecture changes.
10. Parallel agents never share a mutable working tree. Own explicit files/lane branches, no racing commits to `main`; no PR proliferation for repeated fixes. The integrator must check exact-head CI and full changed-file hashes.

## Orchestration and artifact flow

```text
Owner Master Goal #1642 + AGENTS.md
  └─ Codex Coordinator (tracks state and blockers, limited Actions budget)
      ├─ Lane E / original evidence, search-vs-transit, outcome completeness
      ├─ Lane F / forecast universe + feature availability + research
      ├─ Lane M1 / calibrated occupancy and honest probability baselines
      ├─ Lane M2 / spatiotemporal ranking and 1km→100m/10min hierarchy
      ├─ Lane M3 / event/count, detection, large-individual and ensemble studies
      ├─ Lane V / sealed confirmation, negative controls, adversarial comparison
      └─ Lane I / adapter integration, Champion lifecycle and future P0/Pn
                    ▲ integration consumes only reviewed, bounded artifacts
      independent hostile review (separate model where available) throughout
```

Do not run all lanes as independent architectures. Their names, shared manifests and test contracts are **one** system. Evidence/forecast schema and fixed folds are approved at boundary G0 before competing learners are connected. Unblocked implementation can proceed concurrently while blocked scientific model fits correctly return `NEED_MORE_DATA`.

## Definition of **complete** versus bounded implementation

**Product completion** requires one PDCA command to orchestrate evidence audit → P0/Pn version-specific scoring → feature research → multiple genuine candidate model fits → future-blocked/independent validation → Champion-versus-candidate decision → permitted Champion registration/rollback → next legitimate prediction surface; plus correct 3 A/B/C routes, operational history display, reproducible CI/E2E, checkpoints/restart, verified real prospective P0 and model/data hashes.

A lane's code/CI may pass while **scientific validation remains BLOCKED** if there are not enough source-qualified observations, independent confirmation nights, exact as-issued features or trusted production authority. A passed fixture or low-quality positive-only dataset does not justify making up those dependencies. In that case implement and demonstrate the fail-closed path, preserve the blocker and continue genuinely independent backlog work.

## Mandatory coordinator loop for each bounded slice

1. **Observe**: fetch current main SHA, open PRs, actions, scientific blockers, stage contract, exact source hashes; update the machine-readable state and exact result links.
2. **Select**: choose the first highest-impact unblocked slice from `CODEX_LANES_20261025.md`; use bounded branch with explicit file ownership and finish line. Keep maximum active tasks consistent with actual runners/budget; no fixed number of jobs.
3. **Delegate**: start distinct Codex workers in distinct branches/worktrees, each with lane-specific contract. Never use same worktree or source output paths concurrently. Evidence gate and models may implement concurrently, but production activation waits for all prerequisites.
4. **Implement**: unit/contract first, then code; no fake measurements, no loose grep changes, no unverified new input dependency. Include tests for absence of real data. Reuse open PR rather than new PR when fix belongs there.
5. **Check**: run targeted tests locally, GitHub Actions full suite, exact-head CI; record seed, inputs, environment, model and code hashes, test counts, all failure logs; independent reviewer checks leakage, schema, join granularity, authority and sample-selection bias.
6. **Repair**: every FAIL creates a specific smallest-fix task **on the same PR** and reruns all affected tests; no lowering thresholds, deleting blockers, skipping tests, accepting missing jobs as PASS or opening duplicate repair PRs.
7. **Integrate**: coordinate merge in dependency order only when current review and checks pass. Merge code can be accepted with an explicitly scientific BLOCKED result but must remain fail-closed for data/model use.
8. **Recheck**: verify after merge on **fresh main**: tests, intended files/SHA, no Raw/ORIGINAL modification, acceptance/E2E; update `CODEX_STATE_20261025.json`, evidence report and next slice. If a CI job cannot be run, mark `CI_BLOCKED`.
9. **Handoff**: explain progress as PASS/PARTIAL/BLOCKED/NOT_VALIDATED with actual artifact links, owner-only required input when appropriate, and next unblocked automated task. Do not claim persistent background processing unless a real workflow/automation was configured and verified.

## Existing code and PR reuse strategy

- Model evaluation: `src/model_evaluation.py` + `tests/test_model_evaluation.py`, research-only `src/prospective_candidate_model.py`.
- Evidence: `src/evidence_audit.py`, `src/learning_snapshot.py`, `scripts/audit_august_75_fauna_motion_review.py`, source-native receipts `evidence/recovered_sources/`.
- Forecast issuance: `scripts/issue_prediction.py`, `src/champion_registry.py`, `scripts/check_p0_readiness.py`; remains production blocked.
- Parent: `src/master_orchestrator.py`, `scripts/run_pdca.py`, Chat→Issue→Actions bridge (keep current owner one-command workflow).
- Prospectively viable components: inspect open #32/#33/#46 before changing future 100m grids or spatial candidate inference.
- Current source constraints: `docs/plans/master-goal-1642-training-corpus.md`, `docs/plans/master-goal-1642-feature-models.md`, `docs/plans/master-goal-1642-composite-inference.md`, `docs/specs/leakage-safe-feature-candidate.md`. These documents are design context, **not** evidence that modules described therein are already merged.
- Authoritative acceptance matrix and worker prompts are in the companion docs. Codex must not replace their agreed contracts without owner Human Gate.
