# Master Goal #1642 audit: 2026-10-29 JST

Authoritative goal: haji84/AI-#1642; execution issues64/86. Actual audited main:
`386dfd52cd0b4d80e87897f8e5ccf544fff7e135`. This is a source/CI audit, not a new
biological source certification or evidence of an actual future-night run.

## Architecture and stage contracts

The existing command bridge calls `scripts/run_pdca.py`, which owns the night
lock and supervised execution of `src/master_orchestrator.py`. The parent runs
nine stages: evidence audit, operational scoring, model evaluation, feature
research, candidate generation, candidate validation, development, promotion
decision and Champion handoff. Inputs, code/runtime identities, evidence
manifests and checkpoints bind recovery. Existing source/forecast/learning
contracts and registered research adapters are reused; no second pipeline is
introduced. Issuance remains separate: registry -> issue_prediction -> immutable
Freeze -> read-only PDCA. REPLAY cannot rewrite ORIGINAL.

## Requirement-to-implementation gaps

| Master requirement | Existing implementation | Actual remaining gate |
| --- | --- | --- |
| A: source/07:00/cutoff audit | evidence_audit, learning_snapshot, g0 contracts | Independently qualified active search, complete outcomes and training denominator remain unestablished. GPS passage never supplies Negative. |
| A: real GPX and logs | immutable intake, QC, source/outcome matrix | PR147 is unmerged, duplicates aliases, contradicts incoming-only documentation and fails3 full-suite inventory checks. No additional raw/log publication is authorized. |
| B: per-P0/Pn scoring | pdca_pipeline cutoff filtering and one-to-one matching | Strict official eligibility remains false; no authentic prospective P0 in this checkout. Fixture scores are diagnostic. |
| C: 1km Top10 >=90% | model_evaluation and full-universe score-summary adapters | Full eligible outcome denominator including outside-universe misses and untouched future-blocked confirmation are missing; gate NOT_EVALUATED/NOT_VALIDATED. |
| C: 100m +/-10min | immutable target contract and matching code | Issuer writes empty targets and NOT_PRODUCED. A registered feature-aware time-target executor is missing. |
| C/D: feature/calibration research | bounded research adapters; PR151 adds source-bound descriptive calibration | Real eligible data and independent seasonal/geographic/future confirmation remain absent. A descriptive calibration diagnostic is not a fitted calibrator. |
| E: candidate competition | registered baselines/candidates, bounded TRAIN-only preparation and REPLAY | No qualified real fit/confirmation evidence; no winner or improvement claim. |
| F: bounded development | branch/tests/CI/review, development request contracts | Parent development executor remains IMPLEMENTATION_BLOCKED; request records do not execute a worker by themselves. |
| G: Champion/promotion | append-only sandbox registry and promotion decisions | Trusted reproduction, reviewed durable production activation and all science gates remain required. Code CI cannot authorize production. |
| P0: ex-ante full inference | hash/cutoff-aware snapshot and sandbox issuer | Empty feature schema only; complete ex-ante road/terrain/weather/universe, genuine targets/counts and constrained A/B/C routes not established. |
| P0: times/SHA Freeze | canonical payload/sidecar, exclusive publication and append-only versions | Existing POSIX execution mechanics do not establish trusted production identity. No late/backdated original can be created. |
| Live prospective E2E | audit_next_real_night_e2e read-only observer | No next actual search/start or pre-departure P0 and post-return source pair has been supplied. official_e2e_complete remains false. |

Direct checkout checks found no `data/processed/model_learning.json`,
`features/learning_build.json`, `models/` or `predictions/original/`. Existing
CODEX_STATE qualification records retain their prior audit clock: qualified
Negative0, active-search sessions0, complete-outcome scopes0, training-ready
rows0, real-fit rows/nights0. Reading those records is not a fresh source audit.

## Existing PR and CI evidence

- PR150 merged as8ffde178. Its distinct main data CI40695679380 completed all10
  steps. It supplies a bounded observer and cannot issue or authenticate P0.
- PR146 merged as386dfd52. Distinct fresh-main data CI40718168041 completed all11
  steps; handoff40718167847 passed. Its private intake/supervision repair is
  accepted software scope only.
- PR151 original exact1ce29e86 CI40725267479 failed2050 total:2011 passes,
  38 skips,1 historical-v4 fixture failure. Repairf163dd3 preserves the production
  allowlist and has independent review; replacement exactCI40728970271 is
  tracked separately and is not presumed successful.
- PR147 exactb9dade03 fullCI40631594452 failed with3 source-inventory errors;
  its dedicated source checks passing does not authorize raw promotion.

## Bounded implementation and acceptance

The read-only preflight crashed on Windows because importing descriptive policy
constants loaded the POSIX registry. Extract unchanged constants to
prediction_authority_policy; leave registry locks, live sandbox contexts,
activation and inference untouched. A real subprocess regression reproduced
exit1/fcntl failure before repair. After repair readiness6 passed; observer32
had31 passes/1 actual Windows symlink-privilege skip. Actual start, historical
night, 07:00 boundary, unchanged P0 and false production/official flags remain
tested. See the implementation plan and independent review receipt. Full native
Ubuntu CI and a distinct fresh-main run remain required for acceptance.

No model/data schema or historical M0-M3 definition changes. Existing immutable
prediction, source, fold, training and candidate schemas remain authoritative.
Promotion policy is unchanged: independent locked evaluation and review plus
trusted authorized activation; atomic future-only promotion/rollback, preserving
prior Champions and ORIGINAL. Missing science returns NEED_MORE_DATA/BLOCKED.

## Human gates and deterministic next actions

GitHub metadata reports PUBLIC. Owner allows public code/non-sensitive results;
additional GPX/personal-log publication remains withheld. Visibility, permissions,
billing, raw modification and production trust boundaries are unchanged.

1. Repair151 in place, verify exact head, safely merge software, verify fresh main.
2. Independently review and freeze this separate preflight slice, then exact-head
   CI, safe code-only integration and fresh-main verification.
3. Resolve qualified active-search/outcome/individual evidence through original
   source review; obtain genuinely ex-ante full forecast inputs. Never create
   absent evidence or re-date historical availability.
4. Implement/validate supported full composite capabilities under existing
   contracts, independently reproduce eligible science and obtain privileged
   production activation only at its actual Human Gate.
5. At an owner-confirmed real future departure, execute trusted P0 or report
   PROVISIONAL_NOT_FREEZABLE; after actual return ingest original sources through
   an authorized private destination and run the existing PDCA once.

Completion: PARTIAL_BLOCKED / NOT_VALIDATED / NOT_COMPLETE. Formal Stage1 and
100m +/-10min, production P0, Champion promotion and real field E2E are unproven.
