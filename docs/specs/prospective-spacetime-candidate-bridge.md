# Registered-candidate 100m × 10min inference bridge

Status: **PREPRODUCTION ONLY**. This bridge is a development component, not the formal Habu AI prediction issuer.

## Composition of existing work

1. PR #33: `build_osm_prospective_universe.py` reconstructs the existing verified OSM auxiliary road source and materializes a future-window `ForecastUniverse` with 100m UTM52N centers and three measured geometric features. Each current shard covers at most six 10-minute windows, **not the entire night**. Road legality/current closures are not validated.
2. PR #32: `prospective_inputs.load_prospective_inputs` reads that shard's v2 snapshot with exact content hashes, as-of cutoff, joined feature names, complete row coverage, leak exclusions, and bounded memory/work controls.
3. This **stacked PR** adds `prospective_spacetime.infer_candidate`. It consumes the PR #32 validator output and a hash-bound `models/candidates/*.json` envelope. It evaluates exactly the declared numeric predictor coefficients at each actual prospective 100m × 10min unit. The candidate envelope has a content digest, explicit implementation version, feature-schema SHA, training cutoff, cutoff-known JST clock sine/cosine terms, and sorted deterministic target ranking. The clock is encoded before exploration from each *future window timestamp*, not from observed activity.
4. Existing `scripts/issue_prediction.py` production authority remains blocked. This PR does **not** integrate an unvalidated score into `predictions/original`, `freeze_prediction.py`, main PDCA scoring, or Champion.

## Model candidate input

The only accepted model type is `linear_logit_100m_10min` with
`implementation_version=prospective-logit-candidate-v1`,
`qualification=UNVALIDATED_CANDIDATE`, exact feature coefficients,
training cutoff prior to issuance, a content-based model digest,
`produced_outputs=["unit_probability","spatiotemporal_ranking"]`,
a predeclared selection threshold and bounded maximum candidate target count. The only clock basis allowed is `jst_clock_cyclic`, with registered finite `sin` and `cos` coefficients (the feature-schema hash covers snapshot features, while the full model-content digest covers both temporal coefficients). These coefficients are not claimed to be fitted or validated.

The model envelope is intentionally **not** a trusted registry or calibrated model. It does not prove that coefficients were fitted on authentic past data, that supplied training_data_sha256 identifies an eligible training set, or that an independent confirmation study succeeded. Only the synthetic unit tests presently construct model parameters. Never call synthetic coefficients an observed relationship.

## Result contract

- `unit_predictions`: full, sorted 100m × 10min future universe with coordinate cell centers, model candidate score and actual future time window.
- `candidate_targets_100m_10min`: deterministic, thresholded top 100 maximum, as diagnostic ranked targets. These are **not** `targets_100m_10min` for official original P0 scoring.
- `official_issuance_authorized=false`, `formal_100m_10min_status=NOT_VALIDATED`, `prediction_class=CANDIDATE_DIAGNOSTIC_NOT_ORIGINAL`.
- `consumed_sha256`: snapshot, universe, feature sources and candidate-model file. Sources are rechecked after inference. This sequential recheck is not an atomic immutable snapshot.
- No historical data, Raw, Original, Champion, prediction model registry, API access or permissions are modified.

## Remaining verified acceptance gates

A. Exact-head CI PASS for PR #32, #33, this stacked PR and PR #45. Current hosted Actions is blocked by Issue #34; synthetic local tests are insufficient for main integration.

B. Independently verify production environmental inputs (temperature, rainfall, humidity, wind, moon, optional tide), terrain/DEM, road access and provenance, full-night 100m × 10min universe, as-of cutoffs and model-feature mapping. PR #33's OSM-only six-window shard is not that product.

C. Train and validate candidate model using *earlier* audited exploration observations and rigorous time-blocked walk-forward, explicit unknown-vs-negative handling and denominator coverage. Compare to M0–M3 and Stage1 Top10 Recall 90% gate. Do not adopt the arbitrary logistic fixture as learned coefficients.

D. Complete independent Task8 production activation, trusted and irreversible ORIGINAL P0 publication with receipts, and real-world cutoff enforcement before the GPX first point. An eligibility assertion in a JSON file must never unlock issuance.

E. Only after a **future real** P0 exists: collect later original GPX and deduplicated captures/reactions, link the frozen forecast by hashes/cutoff, score 100m ±10 minutes and capture/route outcomes if actually produced, perform independently verified scientific PDCA and retain Champion until improvement is proven.

There is no shortcut from a local candidate probability into an official capture forecast.

## Development-only historic learning slice (not promoted)

`src/training_corpus.py` adds a bounded selection API for a *subsequently materialized* `data/processed/` corpus with audited row identities, per-source byte hashes and receipt times. It enforces 07:00 JST attribution, earlier-night-only fit boundaries, globally unique capture IDs, explicit audited positives, Negative-only after qualifying SEARCH/PASSAGE plus all-captures-recorded and eligible GPS segment, and UNKNOWN exclusion. A missing feature or unproven valid time rejects a row rather than imputing it. Three prior nights and both observed classes are a minimum engineering gate, not a scientific adequacy claim. Retroactive receipt timestamps are not considered authenticated merely because a JSON file asserts them.

`src/train_spacetime_candidate.py` consumes **only** the selector's eligible historical rows. It uses a deterministic bounded L2 logistic fit with train-only feature standardization and cutoff-known JST cyclic time coefficients. It returns a numeric model envelope compatible with `src/prospective_spacetime.py` and descriptive training Brier, fit convergence and limitation metadata. Training Brier is **not** independent performance. There is no raw-source ingestion or production model activation side effect; code has no permission to write ORIGINAL/Champion.

`tests/test_training_corpus.py` uses synthetic receipt/row samples to challenge late-arriving sources, future-night leakage, exposed-night reuse, unknown/unsupported negatives, duplicate capture identities, cutoff equality, feature historical-validity refusal and byte tampering. These are proposed regression tests, not hosted CI PASS.

**Real input blocker:** `main` has no materialized `data/processed/model_learning.json` or properly audited `AUDITED_TRAIN_ONLY` corpus with source availability, observation-role verification, and historical covariate validity. The integrated historical GPX/DB candidate in PR #43 is still Draft, and Negative eligibility has not been established for all nights. It would be scientifically invalid to manufacture training negatives or coefficients from capture-only points. The selection path remains `NEED_MORE_DATA` until the actual evidence construction, validity/availability review and independent verification are completed.

**Next implementation, separately gated:** derive the corpus from trusted canonical `evidence_audit` artifacts without overriding UNKNOWN, provide past-valid weather/road/terrain/effort data and provenance, run development-only night-blocked walk-forward, freeze the selected model and untouched future confirmation protocol before revealing outcomes. No already-researched historical nights can be rebranded as independent confirmation. The production trusted issuer and official P0 remain blocked until all science and CI gates pass.
