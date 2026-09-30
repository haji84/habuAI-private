## Owner goal

Surface=WORK.
Project=ハブAI.
Use a long-running Work session and carry this through as one master goal. Do not reduce this to a one-shot PDCA report.

### Final operating experience

The owner must be able to say only:

「今日のPDCA全部回して」

from the PDCA Chat surface.

Prediction issuance remains a separate operational surface, but it MUST be connected through immutable artifacts and model promotion:
Prediction surface -> ORIGINAL P0/P1/P2... Freeze -> PDCA reads only -> research/evaluation/improvement -> REPLAY/candidate validation -> approved Champion -> next prediction surface.

Never rewrite historical ORIGINAL predictions.

### Existing repository

Canonical private repo: haji84/habuAI-private

Before designing or changing anything:
1. Read AGENTS.md and all relevant docs/specs.
2. Audit current main implementation, workflows, tests, data layout, prediction storage, reports and existing PDCA bridge.
3. Treat current behavior as evidence, not assumed completeness.
4. Produce a gap matrix against every requirement below.
5. Reuse existing implementations where correct. Do not create parallel duplicate pipelines.

### Required parent orchestration

One PDCA command must orchestrate all applicable stages:

#### A. Data/evidence audit
- operational-night boundary 07:00 JST
- frozen prediction integrity, cutoff_time, model/data/feature hashes
- GPX completeness and recovery-quality classification
- capture DB and reaction DB
- weather/road-surface inputs
- 100m x 10min exposure
- Unknown != Negative
- duplicate/time/location audits
- future-information/leakage audit
- Gold/Silver/evidence-quality tracking
- reproducibility/evidence manifest

#### B. Operational PDCA scoring
- P0 separately
- P1/P2/P3... separately, each only after its cutoff_time
- ORIGINAL vs REPLAY separation
- FN/FP/error decomposition
- exploration-effort/exposure correction
- formal 100m ±10min KPI
- count/activity/route metrics where actually produced
- do not score outputs that were NOT_PRODUCED

#### C. Stage-gated model evaluation
- walk-forward / future blocking
- Stage1: 1km Area Top10 Recall >= 90% gate
- downstream 500m -> 250m -> 100m -> formal 100m ±10min
- Tonight Activity / expected count
- detection where applicable
- route optimizer and A/B/C route evaluation
- real-time rerouting evaluation where evidence exists
- calibration
- baseline comparison
- model-version comparison
- diagnostic and true model-feature ablation
- leakage audit
- drift monitoring
- useful secondary metrics such as PR-AUC/ROC-AUC/ranking/percentile only when valid for the task
- never let a downstream metric hide an upstream gate failure

#### D. Data and feature research
Automatically extract research questions from misses and uncertainty, then test supported candidates including:
- temperature, humidity, rain/rain-after, road surface
- wind
- tide level, high/low tide timing, spring/neap tide
- moon phase/moon illumination
- terrain/DEM
- road type
- season/month
- time of night
- recent biological activity
- exploration amount/exposure
- area transitions / hotspot movement
- neighboring-cell propagation
- large-individual history where valid
- geographic diversity
- interactions between features

Research discipline:
- univariate -> multivariate -> interactions
- control location/time/season where appropriate
- cross-year/future-blocked evaluation
- feature ablation
- distinguish association from causal claims
- generate new feature candidates
- contribution/importance analysis
- identify redundant/harmful features
- record evidence and uncertainty

#### E. Model competition and improvement
- generate hypotheses from diagnosed failures
- create bounded candidate models
- compare reasonable model families/baselines under identical future-blocked splits
- candidate REPLAY must never alter ORIGINAL
- rerun walk-forward and ablation
- compare Champion vs candidate
- reject non-improvements
- NEED_MORE_DATA when evidence is insufficient
- do not change the model because of one night's noise
- loop again when KPI gates remain unmet, within bounded compute/time budgets
- output an explicit promotion decision and evidence

#### F. Development loop
When an evidence-backed improvement requires code:
- bounded branch
- implementation
- tests
- CI
- independent verification where applicable
- PR
- safety/risk gate
- only validated changes become next-version candidates
- never mutate Raw evidence or ORIGINAL prediction history
- no silent weakening of tests/governance

#### G. Champion promotion and prediction integration
Prediction remains operationally separate, but integration is mandatory:
- maintain explicit Champion model/version manifest
- promotion requires defined gates and evidence
- atomic promotion/rollback
- next P0/P1+ prediction must record Champion/model/feature/data versions
- PDCA cannot edit old predictions
- newly promoted Champion is used only for future prediction issuance
- preserve prior Champions and reproducibility
- failed/uncertain candidate cannot silently become production Champion

### Automation / owner interaction

Existing Chat -> GitHub Issue -> Actions PDCA bridge is already implemented and E2E tested. Preserve it and extend the backend orchestration behind it.

Normal operation must require no GitHub button pressing by the owner.
Missing data/stages must return PARTIAL/BLOCKED with concrete reasons, never fabricated success.
Long jobs must persist manifests/checkpoints so recovery is possible.
Idempotency: duplicate command submission must not duplicate irreversible work or corrupt reports.

### Deliverables

Work must first produce:
1. current-state architecture map
2. requirement-to-implementation gap matrix
3. missing requirements discovered beyond this prompt
4. target architecture and stage contracts
5. data/model/evidence schemas
6. promotion/rollback policy
7. bounded implementation plan with dependency order
8. acceptance/E2E test matrix

Then hand implementation work to Codex in bounded slices. Codex must not redesign the architecture independently.

After implementation:
- run unit/contract/integration/E2E tests
- run a historical dry-run where evidence permits
- verify ORIGINAL immutability and no leakage
- verify one owner command reaches every applicable stage
- verify next prediction issuance consumes the promoted Champion without changing prior ORIGINAL
- document all BLOCKED stages honestly

### Completion criterion

Do not declare this master goal complete merely because the command bridge or current PDCA scoring works.

Complete means:
one owner PDCA command can automatically drive evidence audit -> operational scoring -> stage-gated model evaluation -> feature research -> candidate generation -> REPLAY -> validation -> bounded improvement/development -> promotion decision -> future Champion handoff, with immutable ORIGINAL history, reproducible evidence, failure recovery, and no routine owner GitHub clicks.

If a requirement is scientifically invalid or unsupported by available data, preserve the intent but mark it NOT_VALIDATED/BLOCKED and explain the evidence needed instead of inventing a result.

