# Master Goal #1642: audited architecture and stage contracts

Authority: https://github.com/haji84/AI-/issues/1642 (2026-09-30T16:36:51Z).
Audit baseline: haji84/habuAI-private main c1acabe1e2e6f6959c0a949bd18c37f174480c5a.
Status: implementation specification; not a completion claim.

## Intent and invariants

One PDCA Chat command invokes every applicable backend stage without routine owner clicks. Prediction issuance is separate. Raw bytes and ORIGINAL P0/P1/P2... are immutable. Only a validated Champion is available to subsequent prediction issuance. Unknown is not Negative. Night boundary is 07:00 Asia/Tokyo. The formal KPI is 100m ±10min; Stage1 is 1km Area Top10 Recall >=0.90. Upstream failure cannot be hidden by downstream success. M0–M3 historical definitions are unchanged. Unsupported science is NOT_VALIDATED, absent evidence BLOCKED, incomplete implementation PARTIAL/BLOCKED, never PASS.

## Current state architecture

Chat creates owner Issue -> issues workflow OR scheduled poller -> scripts/run_pdca.py -> src/pdca_pipeline.py -> reports/pdca/night -> report branch/PR -> Issue response.
Prediction surface -> scripts/freeze_prediction.py -> predictions/original/night/version. Pipeline additionally reads recovered_original as ineligible historical diagnostics. Raw GPX/verified line archives + capture CSV -> grid exposure. Historical ORIGINAL score aggregation and precomputed legacy 10m diagnostic -> hypotheses -> unconditional NEED_MORE_DATA.

Verified main has 5 src modules, 10 scripts, 13 test modules, 3 Actions workflows. All relevant specs/code/tests were retrieved at pinned SHA. Remote main CI 36744155390 succeeded; command run 36744173827 succeeded at workflow level (not evidence of scientific completion). Local baseline 53 tests: 52 pass, archive restoration temporarily blocked by incomplete local snapshot; materialization is tracked separately. Tree has 13 direct legacy GPX and archived September 28 GPX, only September 28 processed capture/individual CSV, one recovered P0, no original/model registry directories. Legacy report is auxiliary only.

## Audit findings beyond prompt

1. Integrity worst-status can downgrade FAIL to PARTIAL; unhashed payloads still score.
2. Formal scoring accepts payload radius/tolerance overrides; uncovered targets treated as precision failures.
3. Freeze accepts historical/replay payloads, skipped versions and missing lineage; hash alone is not issuance proof.
4. GPX filename-based completeness is not five-class evidence; pipeline does not use search-role eligibility.
5. Exposure positivity uses radius from first sample instead of matching grid cell; input order changes labels.
6. Historical score aggregation is mislabeled walk-forward, does not verify historical hashes, and can use later nights.
7. Output overwrite and stale exposure CSV prevent immutable run reproduction.
8. Capture parser accepts blank/non_capture types, coerces count <=0 to 1, trusts contradictory operational date.
9. Event workflow and poller have different locks, can duplicate jobs; processing label lacks crash recovery lease.
10. Reading an existing report after execution failure can report stale success; poller closes failures as completed.
11. Naive GPX timestamps and segment/coverage quality are not enough for Gold.
12. Greedy target matching is order-dependent; use deterministic maximum-cardinality matching.

## Selected architecture

Extend the existing Python entrypoint, not a second command/pipeline. Alternatives rejected: standalone replacement duplicates scoring/bridge; autonomous arbitrary code execution inside Actions violates bounded development and review. Existing scoring remains an explicit operational subpipeline with corrected integrity and metrics. A parent orchestrator runs data audit, operational scoring, evaluation, research, candidate REPLAY, validation, development request, promotion decision, future handoff. Missing prerequisite affects dependent stages only.

Implementation modules:
- pdca_pipeline.py: operational evidence and scoring, truthful legacy diagnostics.
- master_contracts.py: statuses, schemas, hashes, canonical serialization, safe identifiers, atomic files.
- master_orchestrator.py: stage DAG, checkpoint, content-addressed run manifest, input evidence audit, resumability.
- model_evaluation.py: bounded registered candidate families, future-blocked evaluation/research and REPLAY evidence.
- champion_registry.py: validated append-only model records, compare-and-swap Champion events, rollback and prediction lookup.
- scripts/run_pdca.py: existing entrypoint calls parent orchestrator; legacy output shape remains available to bridge.
- scripts/freeze_prediction.py: prediction-only issuer reads selected Champion lineage; never invoked by PDCA.

## Stage contract

Every stage returns {name,status,reason,requires,evidence,metrics,implementation_version}. Status enum PASS/PARTIAL/BLOCKED/FAIL/NOT_VALIDATED/NOT_APPLICABLE. PASS requires executed validation. NOT_APPLICABLE requires evidence-backed explanation; absence is not nonapplicability. Aggregate cannot PASS with PARTIAL/BLOCKED/FAIL/NOT_VALIDATED. A valid NEED_MORE_DATA decision is not validation success.

Order/dependencies:
1. evidence_audit: snapshot all read sources, quality, duplicate/time/location, availability; fail closed on integrity.
2. operational_scoring: hashes, class/night/cutoff validation, P0 and P1+ independently, recovered scope separate, strict fixed KPI; uncovered targets UNKNOWN. Counts only when produced and observation completeness supports them.
3. model_evaluation: eligible dataset + protocol; Stage1 then 500/250/100 spatial then formal spatiotemporal. Other output families independently NOT_PRODUCED or NOT_VALIDATED. Baselines and candidates share identical held-out nights and universe.
4. feature_research: failures/uncertainty produce questions; univariate then adjusted multivariate then interactions on available audited features; association only. Missing covariates and lack of cross-year support are explicit.
5. candidate_generation/replay: bounded registry only, training before evaluation night/cutoff; write only predictions/replay or run artifacts, never original.
6. candidate_validation: compare Champion/baseline, true retraining ablation, calibration/drift, upstream gates, sufficient independent future folds; reject deterioration, NEED_MORE_DATA on uncertainty.
7. development: evidence-backed code need -> bounded request with allowed paths, tests, cost/risk, verifier, PR evidence. No code or workflow executes from a model-supplied string. Missing approved executor is BLOCKED, no arbitrary dynamic shell.
8. promotion_decision: evaluates signed-by-content evidence (hashes, not invented cryptographic identity), decision REJECT_CANDIDATE/NEED_MORE_DATA/ACCEPT_CANDIDATE. ACCEPT is candidate eligibility, not a direct production write.
9. champion_handoff: production activation only with validation and development/CI evidence when code changed; no historical rewrite. It may be NOT_APPLICABLE when candidate explicitly rejected.

Budget: max 3 registered candidates and max 2 improvement rounds per command; bounded wall clock default 300 seconds, checked between stages/folds. Exhaustion persists checkpoint and BLOCKED reason; no infinite self-improvement. Do not relax any KPI to fit budget. Parallel duplicate execution shares one command identity; artifact content key includes input, code, protocol, policy and Champion hashes. Retry validates existing checkpoint hashes. New inputs create a new run, never silently reuse old evidence.

## Data / Model / Evidence schemas

RunManifest v1: schema_version, run_id, operational_night, command_key, code_sha256, input_manifest_sha256, policy_sha256, champion_before, stages[], created_at, updated_at, overall_status, completed(false unless all applicable stages validated), budget, checkpoint_sha256. Run ID hashes night + inputs + code + policy + Champion. Report compatibility pointer is not authoritative historical evidence.

EvidenceManifest v1: entries[{path,sha256,size_bytes,source_type,available_at,quality,recovery_class,search_role}], missing[], input_snapshot_sha256. Hash every consumed source. Missing availability/role is unknown. Recovery classes: COMPLETE_REAL_GPX, HIGH_QUALITY_GPS_RECONSTRUCTION, PARTIAL_RECONSTRUCTION, SPATIAL_ONLY, UNRECOVERABLE. Gold requires validated real trajectory/time/location/search coverage; Silver supports only declared partial/diagnostic evaluation. Spatial-only never creates temporal negatives. Quality is not inferred from a filename. Initial implementation must report unresolved eligibility instead of inventing Gold.

LearningSnapshot v1 at data/processed/model_learning.json: schema_version, candidate_universe_sha256, source_manifest entries with available_at/hash, rows[]. Row: row_id, operational_night, cutoff_time, label_available_at, cell_x, cell_y (UTM52N 100m grid), window_start_jst, observed (boolean), label (0/1/null), features{numeric feature:value}, feature_available_at{feature:timestamp}, quality, source_refs. Unknown/unobserved label is null. All features/universe for held-out prediction must be available by cutoff; training rows and labels strictly before evaluated night/cutoff. Same unit collisions/conflicts are rejected. Ex-post exposure/GPX is eligibility/label evidence only, never a P0 predictor or forecast universe. Entire row/snapshot hashes recorded. Existing data is not silently converted without required availability/quality evidence.

ModelManifest v1: model_id, family, hyperparameters, model_sha256, feature_schema_sha256, training_data_sha256, training_cutoff, code_sha256, protocol_sha256, evidence_refs[], status(CANDIDATE/CHAMPION/RETIRED), produced_outputs[]. Missing output stays NOT_PRODUCED.

ValidationEvidence v1: candidate/model/input/code/protocol/policy hashes, baseline/champion IDs, exact split IDs, folds[], metrics per stage, ablation[], leakage status, calibration/drift, uncertainty, development verification when code changed, decision, reasons[], required_conditions[]. A self-declared pass boolean is insufficient: verify referenced artifacts and compute decision from metrics/coverage. Cross-year generalization cannot pass on a one-year dataset.

Prediction lineage for newly issued predictions: champion_id, registry_event_id, model_sha256, feature_schema_sha256, data_sha256, created_at, cutoff_time, frozen_at, input source availability, model training_cutoff. P0/Pn version sequence and night/class validated; PDCA has no API for historical writes. Existing historical records remain byte-identical, with their original provenance limitations reported.

## Promotion / rollback policy

Never promote because of one night. Initial conservative engineering policy requires >=5 distinct held-out nights, at least two calendar years for a cross-year claim, Stage1 recall >=0.90, all declared downstream gates passing, positive paired improvement with uncertainty excluding no improvement, no regression on required metrics, true feature ablation, leakage PASS and immutable full lineage. This minimum is a guard, not a statistical claim of adequacy: uncertainty and coverage may require more. Policy is versioned; no automatic weakening. Missing Champion may compare an explicit baseline but cannot fabricate a production Champion.

Append-only model files and promotion/rollback events; current.json updates atomically under exclusive lock and expected previous event/hash. Every event contains previous/next IDs, model/evidence hashes, activated_at. Retry same transition idempotent; conflicting concurrent transition rejected. Rollback targets a previously validated Champion only and records reason. Prediction lookup selects event active at issuance cutoff, so later promotion cannot relabel earlier P0/Pn. Existing prediction versions cannot be amended. Remote production activation must be persisted/reviewed through repository workflow; a local test pointer is not production activation.

## Acceptance matrix

Integrity: tamper + missing hash retains FAIL; class/night mismatch rejected; historical score integrity checked.
Time: 06:59:59/07:00; exact cutoff excluded; feature/label availability leak rejected; train fit precedes night; future directories excluded.
Scoring: fixed 100m/10min; boundary cases; maximum matching; unknown targets never FP; no target outputs NOT_PRODUCED; P0/Pn and recovered remain separate.
Data: wrong capture type/count/date rejected; cell positivity deterministic; missing quality/coverage no Gold; raw/ORIGINAL before-after hash equality.
Model: identical folds/universe, insufficient nights/classes BLOCKED, upstream fail blocks promotion, real retraining ablation, cross-year absence NOT_VALIDATED, non-improvement rejected.
Recovery: interruption resumes verified checkpoint; corrupt checkpoint recomputed/rejected; duplicate command no second publication; changed source/code/policy yields new run; stale prior report cannot look successful.
Champion: reject missing/tampered evidence; compare-and-swap conflict; atomic activation; rollback preserves history; next issuance uses new version and old ORIGINAL hash remains exact.
Bridge: owner command invokes all applicable stages; failure report returns reasons; original trigger preserved, event/poller mutual exclusion and recoverable lease; CI/unit/contract/integration/synthetic E2E plus historical dry-run. Synthetic PASS proves mechanics only, never real-world KPI.

## Completion accounting

Track every Issue requirement in master-goal-1642-gap-matrix.csv with implementation and validation separately. Master Goal remains open until live one-command chain and future prediction handoff are verified. Data/science blockers may truthfully remain reported, but missing executors and unimplemented stages are not called completed. No percentage inferred from file counts/tests.
