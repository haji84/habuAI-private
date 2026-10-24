# Codex parallel acceptance, CI/QA gates, recovery and completion matrix

**Higher authority:** Issue [#1642](https://github.com/haji84/AI-/issues/1642). A code/CI PASS is not a scientific/prospective PASS. This matrix preserves existing upstream blockers rather than inventing field evidence.

## Concrete snapshots to preserve at handoff

| Evidence | Observed status and invariant |
| --- | --- |
| Original 2026 August | owner confirmed **47 personal captures** (46 native capture event statements; exactly one explicitly two Habu). Through **2026-10-20** historical dashboard total **243**, not necessarily current lifetime count. |
| Source and GIS | Native August user Library TXT 116,496 bytes SHA256 \`130dedae6e04501f4be41fff4ff549a9cfc1a1840dcbb0126359b04465ab7e8c\`; September25 OSM is auxiliary, post-hoc for August. |
| 12 historic August actual-GPX nights | 231,715 GPS points, 8,965 position/time candidate bins (100m×10min); 3,491 **review-only** no-capture candidate bins (NOT formal Negative); 774 groupings. |
| Witness/source-linked triage | 705 restored original fauna sightings on 12 GPX nights; 75 priority groups, 99 original strict sightings, 94 distinct candidate bins, 71 slow/stopped vs four ambiguous packet contexts, 39 source events with distinct timestamped GPS clusters (NOT 39 independently verified repeated Habu searches). |
| Scientific eligibility | full searched roads **0 certified**, capture ledger completeness **not certified**, canonical individual IDs **not all verified**, supervised historical Positives/Negatives **0 formally qualified**. |
| Current model readiness | \`src/model_evaluation.py\`: four registered baseline families. \`src/prospective_candidate_model.py\`: strict research-only candidate. Production Champion is sandbox-only/untrusted in \`src/champion_registry.py\`; cannot activate by setting a flag. |
| Open inherited work | open PRs **#32, #33, #46, #44, #45, #50, #73**, must be audited rather than replaced or blind-merged. |

All numbers above are historical evidence anchor values, **not** limits that a new legitimate independent source can never extend. New data must be separately source-bound, audited and versioned; do not alter these frozen receipts to retrofit expectations.

## Mandatory gates

| Gate | Status needed for code merge | Status needed for science / product advancement |
| --- | --- | --- |
| **G0 Contract** | common versioned schemas, source roles, locked metric definitions, approval-safe migration plan; existing tests and independent hostile review | metrics and fold denominator frozen before reading confirmation |
| **G1 Source** | exact input/file SHA, true 07:00 night, GPS point QC, coordinate/time and organism role parser with lossless source selectors | authority + actual source bytes, verified identity, no unresolved owner-count conflict |
| **G2 Observation** | UNKNOWN-safe candidates and missing evidence reason codes, no synthetic Negative on missing GPS/transit/slow/other fauna | proven active Habu search in the cell/time **and** coverage-complete owner capture outcomes for its scope; valid individual identities |
| **G3 Forecast Inputs** | prospective Universe + feature snapshot versioned & hash-bound; missing data BLOCKED | all model-visible ex-ante features (and provenance/geometry) available before the actual issuance cutoff; full eligible road candidate universe |
| **G4 Model Training** | several pure bounded candidate fit/predict methods; honest \`NEED_MORE_DATA\` if zero eligible labels | real eligible training nights with observation target and denominator; no sealed label reading by fitter |
| **G5 Evaluation** | deterministic source/seed/fold contract and hostile tests of leakage/mask/collapse | independent future-blocked real heldout folds, exact Stage1 Top10 numerator/denominator/uncertainty, formal 100m±10min only if produced |
| **G6 Contest/PDCA** | same-fold baselines and new candidates, reproducible REPLAY, actual train-only ablations, drift/uncertainty report | demonstrably better Champion candidate without required metric regression, upstream gate passing |
| **G7 Integration** | guarded adapter into existing master orchestrator and model registry, clean CI, atomic checkpoint/recovery; sandbox tests | trusted activation authority, explicit owner approval for critical operations, strictly future-only model promotion |
| **G8 Product E2E** | one owner request traverses all 9 stages and reports BLOCKED honestly if incomplete | genuine prospective pre-search P0, real P1+ freeze and subsequent capture/GPX PDCA, stage gate validation, three legal route alternatives, next forecast consumes authorized Champion |

**G8 may not be declared complete** merely because G0–G7 pass simulated fixtures.

## Source audit / observation stress tests (Lane E)

- No fabricated GPS path when a time gap, spike, duplicate timestamp or source GPS error occurs; each sampled source identifier unique.
- 07:00 JST rollover incl 00:00–06:59, daylight/time zones, road crossing ambiguous, forestry/farm road restrictions.
- Aug12/Aug13/Aug29 missing paired session markers stay UNKNOWN, even if low-speed + frog sighting.
- Aug21 a complete no-capture ledger is NOT established just because the text has no \`捕獲\` entry.
- Aug31 2 source captures count in owner August47; raw TXT/GPS proximity and distinct source-block SHA do not by themselves certify two canonical unique individual IDs.
- Aug19 nearby five-minute/90m capture statements remain duplicate-review candidates; an explicit two-individual capture event contributes quantity two.
- Himehabu, frogs, birds, reptiles, other-person captures and Habu roadkill must never become owner-captured Habu positives or implied Habu absences.
- The 3,491 source-review bins are NOT eligible training Negatives unless real search scope + complete outcome recording independently pass, then certify unit-by-unit rather than bulk-promote.

## Model fairness/adversarial regression tests (M1/M2/M3 + V)

- A held-out night has one or more true events in a road segment *outside* the prospective universe: the miss remains in eligible evaluation denominator.
- A future capture becomes a feature (directly or via lag/window aggregation): leakage detection FAIL.
- A post-night/reconstructed OSM/weather/capture provenance \`usable_at\` is later than past cutoff: reject an apparent high retrospective score.
- Different model families do not silently score different target denominators, candidate universes or hidden confirmation nights.
- Ineligible \`UNKNOWN\` rows do not become zeros via pandas fillna, categorical encoding, permutation, sample weighting, resampling or calibration.
- Too few distinct source-qualified nights / positive-only-only outcomes: probability and formal performance return \`NOT_VALIDATED\`, with actual counts not a flattering 0.99.
- Model features missing in future deployment but present in retrospective training: matched-availability tests BLOCKED. Multiple fitted folds may not share a future learned scaler/calibrator.
- Check held-out source hashes, geography/night grouping, sealed confirmation not deserialized in fitter, truly retrained ablation, true same-denominator baseline improvement, paired uncertainty and drift.
- Ensemble weights learned only on OOF train folds; confirmation results not used to reselect members, threshold, hyperparameters or route scoring. Selection logs SHA frozen first.
- Model fit deterministic enough for reproducibility: seed, code SHA, dependency lock, input SHA, model SHA, selection manifest and if nondeterministic mark and bound tolerance.
- Do not overpromise accuracy: Stage1 ≥90% is unmet until documented external real evidence passes, and 100m±10min similarly.

## Route/P0/Champion negative tests (Lane I)

- No fake A/B/C drivable route on unverified/excluded OSM/forest access or missing complete road graph; return \`NOT_PRODUCED\`.
- Same sampled historical 100m cells cannot become a past P0 universe just because OSM materialized later.
- Historical ORIGINAL P0 or Pn bytes may not change under replay, retraining, source correction, merge or restart. Check exact SHA before and after.
- Any force-promote / credential switch / missing independent reviewer / untrusted runner must fail closed. Allow only already-approved sandbox lifecycle mechanics without human approval.
- Repeated identical PDCA request idempotently resumes from hashed checkpoints, cannot duplicate model promotion, labels or PRs; failed runs leave recoverable blocker manifests.
- Post-merge fresh-main E2E must refer to actual model hash/version; if authorized production not available return \`BLOCKED_TRUSTED_ISSUER\` and never claim the user can already receive a formal P0.

## Required commands and execution pattern

Read actual repository and requirements first; do not assume third-party packages are installed. Start each worker with targeted fast tests. CI must be **exact PR head** and runner actually executes jobs.

\`\`\`bash
git status --short
git rev-parse HEAD
python -m unittest discover -s tests -p 'test_august_75_fauna_motion_review.py' -v
python -m unittest discover -s tests -p 'test_evidence_audit.py' -v
python -m unittest discover -s tests -p 'test_learning_snapshot.py' -v
python -m unittest discover -s tests -p 'test_model_evaluation.py' -v
python -m unittest discover -s tests -p 'test_prospective_candidate_model.py' -v
python -m unittest discover -s tests -v
git diff --check
\`\`\`

If a named test file does not exist in current main, detect that explicitly and locate the supported equivalent. Do not report a non-existent test as PASS. GitHub Actions source run and private artifact URLs should be recorded in lane PR and state. Check actual nightly source counts before claims.

## Final required owner-deliverable evidence bundle

\`\`\`text
docs/work/CODEX_STATE_20261025.json  (revised state in reviewed PRs)
docs/reviews/<lane>/<night-or-cohort>/... (non-private aggregate assessment)
evidence/model_research/<run_id>/manifest.json
  source_digests, target_contract_sha, feature_availability,
  eligible/unknown/rejected rows, completed fold selection, test raw counts,
  model/baseline hashes, competitor ablations, comparison/uncertainty,
  sealed confirmation closure, reviewer, CI exact-head+fresh-main runs
reports/pdca/<night>/... (existing parent outputs; never falsely write OFFICIAL)
predictions/replay/<night>/... (candidate-only, not ORIGINAL)
models/candidates/... (only if validated for research scope)
models/champion/... (trusted approved authority ONLY)
\`\`\`

Private Habu coordinates, road paths, owner-uploaded logs/individual IDs and sensitive audit payloads remain in private controlled paths/artifacts, not a public downstream dashboard or unreviewed issue body.

## Practical terminal decision policy

\`\`\`text
IF tests/CI fail -> FAIL / smallest repair on same PR / retry within bounded budget
ELSE IF raw/GPS proof missing -> DATA_BLOCKED, continue other lanes
ELSE IF active search or complete outcome missing -> UNKNOWN, no negative training
ELSE IF ex-ante universe/source availability missing -> FEATURE_BLOCKED, no historical P0 scoring
ELSE IF independent confirmation missing -> SCIENCE_NOT_VALIDATED, no Champion
ELSE IF candidate worse or uncertain -> REJECT / NEED_MORE_DATA, keep current baseline
ELSE IF trusted activation unavailable -> PRODUCTION_BLOCKED, candidate remains research
ELSE IF all reviewed gates and owner-critical approvals pass -> future-only Champion promotion
THEN fresh-main verification, checkpoint and next bounded slice
\`\`\`

Do not terminate the Codex project merely because an interim task produced docs, a PR or a pretty number. The coordinator must continue **while an unblocked authorized task and actual executor budget remain**; otherwise leave reproducible backlog state and a precise next invocation without claiming work is running after the current session.
