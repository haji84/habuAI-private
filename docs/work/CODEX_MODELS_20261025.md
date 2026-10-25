# HABU-AI high-accuracy multi-model research and competition contract

**Purpose:** develop several genuinely different candidate model families, compare them under the same eligible inputs/folds, and improve the goal metrics with evidence. This is **NOT** a promise that a high recall number can be obtained from the present historical data. The owner wants **scientific accuracy**, not arbitrarily high backtest percentages.

## Four distinct targets. Never conflate them

| Head | Correct target | Examples of disallowed shortcuts |
| --- | --- | --- |
| **T1. Area ranking** | rank **all eligible 1km areas in a future-night universe**, top 10, evaluated against independently confirmed Habu encounter/capture events with clear denominator and missed outside-universe events | rank only historical captured areas; count no-GPX cells as true negatives; claim 90% on cherry-picked nights |
| **T2. Road/time presence or *observable response*** | 100m road-zone × 10min (target formal precision ±10min) with specifically defined event/observable detection target, real observation effort and source quality | treat every GPX passage, no capture mention, sighted frog, roadkill or unseen road as proof of live Habu absence |
| **T3. Owner capture count / encounter count** | effort-conditioned personal Habu capture/encounter distribution, with one source event containing two individuals counted properly, and distinguish detection probability from animal activity | assume capture ability/detection=1, use number of GPS points as effort-hours, claim observed counts equal total Habu abundance |
| **T4. Route utility + large Habu / alternate objectives** | A: max expected captures, B: highest captures per time/distance, C: geographic diversification / verified large-individual opportunity / unexplored-high-uncertainty, always with vehicle-access and owner constraints | present an imaginary routable map from raw GPX or unverified forestry-road access; infer Habu size from a monthly total |

**Gates:** formal Stage1 1km **Top10 Recall ≥90%** on future-blocked eligible confirmation; final 100m±10min. Distinguish numerical model performance from route utility and organism ecology. A fold with insufficient denominator is `NOT_VALIDATED`, not zero, PASS or random imputation. Substage 500/250/100m scores cannot hide failure at 1km.

## Existing model implementations to reuse

- `src/model_evaluation.py`: exact research baselines `uniform`, `historical_capture_prior`, `observed_unit_prevalence`, `duration_normalized_area_rate`. Retain historical baseline definitions/IDs **M0–M3** as frozen. Some baseline types require outcome denominators; if ineligible, return BLOCKED rather than force training.
- `src/prospective_candidate_model.py`: actual research-only L2 logistic/7 feature candidate with `train_candidate` and `rank_future`, strict `usable_at`, never production authorized.
- Existing open **#32** source-bound future universe/feature contract, **#33** OSM→prospective road/time universe and **#46** candidate inference and TRAIN_ONLY fit must be audited/diffed and reused where sound.
- Parent `src/master_orchestrator.py`, `src/champion_registry.py`, `scripts/issue_prediction.py` own integration, not individual learner implementations.
- Relevant design docs: `docs/plans/master-goal-1642-feature-models.md`, `docs/plans/master-goal-1642-training-corpus.md`, `docs/plans/master-goal-1642-composite-inference.md`, `docs/specs/leakage-safe-feature-candidate.md`.

## Competing model families and phased readiness

| Candidate ID (new, not M0–M3) | Model/approach | Inputs needed; minimum gate | Fair benchmark / what may actually be delivered |
| --- | --- | --- | --- |
| HB-A0 | Uniform and spatially smoothed historical priors | independently verified positives and known eligible future candidate universe; probability claim only with known observation denominator | simple registered baseline, spatial prior, cold-start and area-rank comparisons |
| HB-A1 | Calibrated regularized GLM/GAM logistic; seasonal/cyclic and smooth area terms | validated binary outcome/effort, environmental feature available_at before cutoff; enough diverse nights | calibration curve, Brier/log loss, probability fit, area ranking |
| HB-A2 | Tree gradient boosting / histogram boosted trees / RF alternative | enough labelled/independent eligible nights; no dependence on massive bespoke toolchain; weather/terrain feature hashes | nonlinear interactions and ablation vs A1 and priors |
| HB-B1 | Hierarchical Bayesian/empirical Bayes spatial-temporal area model | true spatial/time target and eligible source-linked events, area denominators where needed | shrinkage for sparse 1km grid; conditional ranks at 500m/250m/100m |
| HB-B2 | Conditional 100m×10min ranking using hour, road context, moon/tides, current conditions and exposure, optionally survival/hazard | actual temporal search effort; 100m×10min event timestamps, no future metadata | time-aware Hit@K/recall/±10min, route-zone credibility, no event hallucination |
| HB-C1 | Effort-aware Poisson/NB count with optional zero inflation if identifiable | independently measured active search exposure and complete owner capture results; no pseudo-zero | count MAE/Poisson deviance/interval coverage; activity/detection separately |
| HB-C2 | Detection/availability and spatiotemporal persistence submodels | replicated true search trials, independent capture and sighting channels; enough distinct nights | assess detection vs activity confounding and true rainy/after-rain effects |
| HB-C3 | Large-individual/seasonal count conditional head | canonical unique Habu IDs and reliable measured length class; segment effort | report large-Habu valid sample size; otherwise `NEED_MORE_DATA` |
| HB-ENS | Calibrated ensemble/stacking of validated subheads, OOF only | stable same-denominator OOF fold predictions from A/B/C, no holdout re-use | compare individual models, ensemble and ablations on same locked protocol |

Do not implement all as new packages immediately. Each lane first runs a *feasibility/data contract* check. If no eligible samples, deliver interface, controlled unit tests and `NEED_MORE_DATA` blocker. Avoid confounding many model labels with many effectively identical predictors. Test meaningful architectural diversity and inference closure, not model-count for its own sake.

## Candidate feature registry research priorities

Group features with units, source, whether forecast/as-issued or retrospective measurement, geography resolution, valid_at, first_available_at, usable_at and missingness. All feature transforms use only TRAIN-fold statistics.

1. **Atmospheric**: temperature, humidity, rainfall intensity and lag, dry→wet transitions, rain-after window, pressure, wind speed and *road-relative* wind direction, local road wetness proxy.
2. **Astronomy/tides**: sunset, elapsed dark hours, moon phase, illumination, altitude, local moon visibility (modelled, not measured unless source), tide height, ebb/flood, minutes from high/low tide, spring/neap; tide observations may not imply inland ecological causality.
3. **Geography/roads**: official/auxiliary road-source class, forest/agricultural access where valid, 100m zone, available DEM, slope/aspect, valley/ridge, cutbank/ditch, canopy/nearby cover, roadway bearing, wind exposure, forest edge, approximate coastal distance, island/geographical offset.
4. **Ecology/activity**: month/season, previous **already available** verified Habu captures, separately sourced Habu sightings/roadkill, prey/frog/bird evidence and zero-lag masking, recent search effort/capture pressure, cell neighborhood and area transitions, verified size class and breeding hypotheses.
5. **Observation/exposure**: audited GPX source quality, actually searched length/dwell/time/repeat passes **only if genuinely attested**; detection conditions; route preferences; missing sampling as UNKNOWN, not zero.
6. **Interaction hypotheses**: rain×temperature, moon×canopy, wind×roadside orientation, night-time×season, tide×proximity to coast, pressure change×post-rain, terrain×rain; research candidates only with controlled ablation.

**Explicit leakage traps:** future actual captured/sighted outcomes as today's predictor; full-night real weather in a model claiming an issued weather forecast; the September25 OSM map claimed as August31 prior input; deriving a `forecast universe` from GPX-only visited cells; same-night capture pressure from events after P0 cutoff; selecting features with sealed confirmation labels; post-hoc label eligibility granted because a model scored well.

## Fitting protocol and model interface, shared across workers

G0 must freeze a model target contract, training-selector and evaluation plan, e.g.:

```text
TargetContract {
  schema_version, target_type, event_species_role, outcome_definition,
  spatial_resolution_m, temporal_window_min, matching_tolerance_minutes,
  required_search_proof, required_outcome_completeness, individual_id_policy,
  full_denominator_policy, exposure_offset_policy, source_eligibility_policy
}
EligibleTrainingSet {
  snapshot_sha256, fit_before, target_contract_sha256, source_ref_digests,
  accepted_unit_ids, rejected_unit_ids_and_reasons, unknown_unit_ids,
  cohort_night_ids, available_at_max, effort_semantics, n_training_nights
}
CandidateFit {
  id, family, model_version, recipe_sha, feature_schema_sha, training_set_sha,
  protocol_sha, code_and_dependency_sha, actual_fit_finished_at, fit_cutoff,
  serialized_parameters, deterministic_seed, training_status,
  leakage_check_status, declared_prediction_head_capabilities
}
Prediction {
  model_sha, universe_sha, input_feature_snapshot_sha, issue_as_of,
  cutoff_time, night, area_id_1km, zone500, zone250, roadzone100, tenmin_slot,
  ranking_score_or_probability_with_explicit_semantics, uncertainty,
  immutable_candidate_prediction_sha
}
```

These are **illustrative interface fields**, not permission to overwrite existing v1 schema. Codex G0 worker must bind current `schemas/model-learning.json` and actual `learning_snapshot` adapters, add versioned extensions only when necessary and independently reviewed. Do not train with a source labelled `source_role=label` as a feature. Training fitting must be a pure function of approved TRAIN rows+frozen configuration. Confirmation outcome bytes cannot even be deserialized by the fitter.

## Locked future-blocked evaluation (Lane V owns this)

- Split by **operational night**, never random cell rows. Same night and duplicate event groups never appear on opposite sides.
- Compare distinct chronological train→validation→sealed confirmation cohorts; hold out geography/island/road context where feasible; evaluate shifts across seasons and years if actual qualified data exist.
- At each fold, require source/feature availability strictly before fit and issuance as applicable. The same historical GPX may legitimately be labelled later for a **future** model fit, but it never becomes historic issued forecast data.
- Every model and all baselines predict on the **same full eligible night universe** and identical frozen input snapshot, timeout and evaluation denominator. Missing model output is failure/NOT_PRODUCED, not a dropped hard case.
- Stage1 Top10: exactly ten unique 1km area IDs (or fewer only where true complete universe is smaller), full eligible nights/individual Habu event denominator, clear one-to-one event matching and outside-universe misses. At least **5 untouched held-out nights** as the conservative initial engineering minimum, and ≥2 years only where making cross-year generalization claims; real validity depends on sufficient events and independent exposure. Never call this number alone statistical adequacy.
- Report numerator, denominator, per-night results, confidence interval (e.g. night-block bootstrap; clearly note small-n), under-sampling, coverage, variation by rainfall/season/road/island, confusion and miss reasons. Stage1 90% threshold is necessary, not sufficient: compare competitor and baseline paired improvement on independent confirmation.
- T2 100m±10min: event-to-prediction space/time bipartite matching on predeclared window and live event identity; location/event timestamps verified; time-window coverage from independent ex-ante universe. Do not score an output the model never produced.
- Proper calibration only if probabilities truly denote the target on a valid denominator; positive-only ranks may use ranking metrics under declared limitations but **no Brier, ROC, AUC claims of calibrated Habu absence**.
- Compare complete-area recall, precision/expected capture utility, Brier/logloss where legitimate, calibrated intervals, top-k across geo/time hierarchies, latency, cost and failure-rate. Ablation must refit/recalibrate each feature-removal candidate **within TRAIN folds**, never just zero a feature at inference time.
- Confirmation selection sealed before REPLAY, model family/threshold/ensemble weights chosen on development folds only; sealed confirmation must stay unread until all candidates/plan frozen. Reuse revealed confirmation nights as DEVELOPMENT only; new confirmation required for another claim.
- If Champion candidate does not show robust evidence of meaningful improvement and all upstream gates, decision `REJECT` or `NEED_MORE_DATA`, not silent promotion.

## Prediction-model-to-route integration gate

A route optimizer is not just top 100m cells connected by straight lines. Real legal driveability and on-the-night road restrictions must be checked, including Amami and Kakeroma, forestry/farm roads, weather/landslide access and owner route constraints. Rank route A/B/C by:
- **A:** maximize expected verified-personal-capture opportunity;
- **B:** maximize expected opportunity per hour/km;
- **C:** diversified alternative with large-Habu objective only if canonical size histories qualify, otherwise high-uncertainty/unexplored value with explicit warning.

For each route store expected target semantics, start/end, path/road IDs, distance/time (actual road graph, no invented metrics), expected observation effort, repeat-search share, source and risk/unvisited share. Missing valid road graph, region restrictions or time budget ⇒ route status `NOT_PRODUCED`, never a synthetic complete route.

## Finish line and honest failure

A MODEL CODE/CI PASS means the algorithm can correctly train and score eligible data **when provided** and blocks unsafe inputs. SCIENCE PASS needs actual credible cohort, source and leakage evidence. HIGH-ACCURACY achievement specifically requires valid independent measured target gate, not a favorable synthetic fixture. PRODUCTION requires separate trusted authority approval and genuine future P0/Pn E2E, no silent activation.
