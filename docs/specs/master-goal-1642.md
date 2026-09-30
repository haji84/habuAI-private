# Master Goal #1642: audited architecture and stage contracts

Authority: https://github.com/haji84/AI-/issues/1642 (2026-09-30T16:36:51Z).
Audit baseline: haji84/habuAI-private main c1acabe1e2e6f6959c0a949bd18c37f174480c5a.
Status: implementation specification; not a completion claim.

## Intent and invariants

One PDCA Chat command invokes every applicable backend stage without routine owner clicks. Prediction issuance is separate. Raw bytes and ORIGINAL P0/P1/P2... are immutable. Only a validated Champion is available to subsequent prediction issuance. Unknown is not Negative. Night boundary is 07:00 Asia/Tokyo. The formal KPI is 100m ±10min; Stage1 is 1km Area Top10 Recall >=0.90. Upstream failure cannot be hidden by downstream success. M0–M3 historical definitions are unchanged. Unsupported science is NOT_VALIDATED, absent evidence BLOCKED, incomplete implementation PARTIAL/BLOCKED, never PASS.

## Current state architecture

Chat creates owner Issue -> issues workflow OR scheduled poller -> scripts/run_pdca.py -> src/pdca_pipeline.py -> reports/pdca/night -> report branch/PR -> Issue response.
Prediction surface -> scripts/freeze_prediction.py -> predictions/original/night/version. Pipeline additionally reads recovered_original as ineligible historical diagnostics. Raw GPX/verified line archives + capture CSV -> grid exposure. Historical ORIGINAL score aggregation and precomputed legacy 10m diagnostic -> hypotheses -> unconditional NEED_MORE_DATA.

Verified main has 5 src modules, 10 scripts, 13 test modules, 3 Actions workflows. All relevant specs/code/tests were retrieved at pinned SHA. Remote main CI 36744155390 succeeded; command run 36744173827 succeeded at workflow level (not evidence of scientific completion). Local baseline: all 53 tests pass after byte-exact materialization. All 13 legacy GPX and September 28 archive are locally available and hash-verified. Historical isolated dry-run for September 28: PARTIAL, RECOVERED_ORIGINAL, 22,990 GPX points, 6 individual captures, 947 exposure units; formal targets NOT_PRODUCED. Candidate validation still incorrectly PASS in baseline and is a tracked defect. Tree has 13 direct legacy GPX and archived September 28 GPX, only September 28 processed capture/individual CSV, one recovered P0, no original/model registry directories. Legacy report is auxiliary only.

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

## Independent design review resolutions (normative clarification)

The first five slices establish foundations, not full Master acceptance. Follow-on slices 6–8 below are mandatory where applicable. IMPLEMENTATION_BLOCKED and DATA_BLOCKED are separate fields; NOT_VALIDATED is never a substitute for an unbuilt executor.

Promotion trust: hashes establish consistency, not issuer authenticity. Production promotion remains disabled unless evaluation is reproduced from pinned immutable inputs by the repository's verified runner and the exact candidate code/evidence/policy commit is covered by CI plus independent verification. Registry recomputes gates from fold predictions/labels, not supplied summary metrics. Synthetic inputs cannot establish production authority. The trusted execution environment must be supplied by the fixed production entrypoint, never a user-editable evidence flag. No new credentials or permissions are authorized by this contract.

Prediction handoff: scripts/issue_prediction.py must execute a registered Champion inference adapter on a hash-verified feature/universe snapshot, then Freeze its actual output. Merely attaching Champion identifiers to arbitrary --input JSON is insufficient. Trusted issued_at/frozen_at uses the issuer clock; forecast cutoff is a separate validated input bound. Caller backdating cannot select a historical Champion. The existing generic Freeze remains for externally issued records with explicit provenance limitations, never automatically upgraded to Champion-generated status.

ForecastUniverse v1 is an explicit referenced artifact with path/hash/available_at, geographic-domain definition, and all ex-ante eligible cell/time rows; held-out GPX never defines it. Learning rows refer to universe row IDs, including unobserved rows. Universe rows include exact latitude/longitude (or validated UTM coordinates), not merely a 100m cell index, so 250m aggregation is well-defined. Add measured search duration_seconds/distance_m when known, method/observer version, capture_count and capture_event_ids. Missing measured effort blocks an effort-corrected claim; observed-unit prevalence is honestly named and is not effort correction. Stage1 primary recall counts confirmed individual captures whose 1km cell occurs in Top10; multi-individual events use verified capture_count without duplicating event IDs across rows. Distinct-event recall is a separate secondary metric. Zero-positive nights have null recall and do not silently count as success. This protocol governs new evaluations only and does not rewrite historical M0–M3 definitions. 500/250/100m aggregation uses coordinates, not an integer cell division that would mishandle 250m boundaries.

Validation policy is frozen before confirmation labels are revealed. Research/development nights and confirmation nights are disjoint; a night used for diagnosis/model selection cannot become independent confirmation evidence. Record research_used_nights and confirmation_used_nights in protocol. Primary paired improvement for valid probability outputs is night-aggregated Brier difference (Champion minus candidate); use deterministic night-cluster bootstrap with 2,000 draws and 95% interval on untouched confirmation nights; at most three pre-registered candidates, choose on development only, test one selected candidate once. Reusing revealed confirmation labels for subsequent selection invalidates confirmation and requires fresh prospective nights. A minimum five confirmation nights is an engineering floor, not sufficient proof. Cross-year validation is mandatory for a cross-year generalization claim; without it the claim is NOT_VALIDATED and broad cross-year production policy is not eligible. Initial full-scope promotion requires cross-year evidence; do not silently narrow scope to pass.

Mandatory full-scope gates are policy-owned: integrity, availability/leakage, Stage1 >=0.90, 500m/250m/100m and formal 100m±10min validated, comparison/ablation/calibration, independent confirmation, code verification and inference reproduction. Candidate cannot omit mandatory outputs to evade them. Count/activity/detection/routes/rerouting are conditional only on a declared approved product capability and evidence-backed applicability; missing requested executors remain implementation blockers. Separate execution_status, validity_status and gate_outcome from promotion decision.

Snapshot reads: parent copies consumed inputs into a content-addressed snapshot or verifies each read plus every consumed file at completion. Processed features/model/universe/protocol/code must be revalidated too, not only protected Raw/ORIGINAL. Changed or deleted input invalidates the run/checkpoint; no successful manifest is committed against a different input. Include runtime/dependency identity. Retries share a cumulative budget ledger and round number; fresh runner restoration must verify all checkpoint/output hashes.

Follow-on slice 6: feature-aware registered models, controlled univariate/multivariate/interactions, true retraining ablation, immutable REPLAY and confirmation split contracts, plus count/activity/detection and A/B/C route evaluator adapters with explicit measured-effort and graph-input contracts. Missing evidence blocks those adapters; merely having stage names does not implement them.
Follow-on slice 7: integrate an existing approved Goal/job development executor (audit haji84/AI- interfaces first) with allowed paths, tests, CI, verifier and PR state. Persist request/attempt/commit/evidence IDs, poll/recover using existing capability contracts; absent integration capability is an implementation/runtime blocker, no invented executor.
Follow-on slice 8: trusted production evaluation/promotion persistence, real inference issuance and live two-run event/poller idempotency. Use repository native verified PR/CI mechanisms without permission or security changes. Full Master completion remains blocked until these paths are exercised with machine evidence.

## Reviewed controller correction (normative; supersedes exclusive Task7 runtime dependency)

Canonical owner request explicitly delegates bounded implementation to Codex in this PDCA Chat. AI-/Compass/JARVIS is one audited optional executor, not a required dependency or separate authority for Habu changes. Use the current owner-authorized active PDCA Chat/Codex controller and existing authenticated GitHub connector. Actions persists typed evidence-bound development requests; this controller validates scope, claims bounded attempts, delegates implementation, obtains independent verification and exact-head CI/PR evidence, persists results and resumes the existing backend. Issue1642 remains the canonical Goal. No copied AI- runtime, guessed endpoint, new credentials/permissions or model-supplied shell. Habu repository governance still applies.

Persist request/attempt/state/operation IDs, immutable evidence/base/head/patch hashes, allowed/protected paths, fixed Python verification profile, verified CI workflow identity and cumulative budget. Reconcile real branch/PR/check state after interruption, reject divergent or stale heads, and never reset budgets by opening equivalent jobs. A code change starts a new scientific run linked to the parent. Missing data does not fabricate a code need. Normal active-session execution requires no additional owner instruction or button.

The controller must retrieve actual GitHub facts directly and independently reproduce candidate evidence; authentication or committed PASS fields alone do not grant promotion authority. Only the reviewed persisted production path can activate a scientifically eligible model. Caller trust flags remain forbidden. Current active-session liveness and durable restart correctness require separate live tests. Durable records do not prove automatic wake-up after the entire Work session has ended; no unattended wake-up claim is allowed without demonstrated platform support. See docs/reviews/master-goal-1642-codex-controller-design.md.

Task3 contract clarification after independent review: source_manifest roles are required and recognized; observed rows must bind label sources. feature_source_refs maps every feature to nonempty feature-role source paths also present in row.source_refs, and field availability cannot precede bound-source availability. Unobserved rows may have label_available_at=null and quality=UNKNOWN, retain required ex-ante provenance, and never enter fitted/scored label denominators. Canonical event IDs are unique across all nights/rows. Until a complete hash-bound outcome ledger includes outside-universe captures, computed recalls are explicitly restricted-universe diagnostics and Stage1 gate_outcome is NOT_EVALUATED. Full KPI evidence must not drop out-of-universe misses.
