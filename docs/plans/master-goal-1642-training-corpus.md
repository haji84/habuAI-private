# Separate retrospective training observations from prospective evaluation universes

Read-only Task6b refinement. Current Task6a must remain scoped to audited evidence/outcomes/observation units; no evaluator-v2 expansion is needed in that worker.

## Finding

**The gap is real.** Current model_evaluation._validate requires every LearningSnapshot row to reference an EX_ANTE_FORECAST universe row; requires universe/protocol availability and protocol frozen_at before that historical row's prediction cutoff; binds row features to the same cutoff; and requires learning rows to cover the entire forecast universe. This is appropriate for reproducing historical forecasts but unnecessarily excludes retrospective observations from all future fitting.

An audited August capture/observation imported September30 may legitimately train an October model once its sources, label and chosen features are available. That does not establish August forecast availability, an August universe, historical operational predictions or independent confirmation. The missing historical universe should not permanently forbid such training. Conversely, moving September30 source availability into an August field to appease v1 would fabricate provenance.

Preserve v1 semantics. Add an explicit versioned training-only path rather than relaxing its cutoff checks or giving all rows a new later cutoff.

## Minimal v2 separation

Introduce LearningBundle v2 with independently hashed references:

- TrainingObservationCorpus: audited retrospective TRAIN_ONLY observations, their source/feature versions and readiness.
- ForecastEvaluationCohorts: explicit ex-ante universe and feature snapshot per held-out cohort/cutoff, independent outcome/ascertainment ledger references, and cohort purpose DEVELOPMENT_FORECAST or SEALED_CONFIRMATION.
- Protocol/selection/freeze/confirmation-consumption references and immutable fit_as_of/evaluation boundary.

Corpus is not a forecast universe and has no `universe_row_id`, original prediction version or invented historical forecast cutoff. It includes schema_version/kind, geographic/observation scope, derivation recipe/code hash, source manifest, audit-policy/result refs, research exposure history, and rows. Each row has canonical observation_unit_id, operational night, exact spatial coordinate/unit and event/window timestamps, source refs and source bytes hashes, label state, label availability, capture event/individual identities and verified counts, search/ascertainment eligibility, quality and optional measured effort. Coordinates must come from actual audited observation evidence, not invented predictions.

Feature values have their own feature definition/version, source bindings, physical valid-time/window, record/source availability, materialized_at and usable_at; include derivation dependencies, permitted use and target-leakage checks. Preserve label, feature, observation/effort and universe source roles. One source can have separately audited typed projections; calling an entire GPX file a generic feature source must not make future actual trajectory eligible for forecasting.

An unknown unit may be retained for audit but has label=null and is excluded from supervised outcome denominators. A confirmed positive lacking reliable effort may support event/occupancy fitting if its target semantics permit; it does not support exposure-rate fitting. An observation unit with only a binary capture mention and unresolved individual count can be eligible for an explicitly defined binary target but cannot silently enter individual-count models/Stage1 totals. Current recovered sources remain quarantined until Task6a/canonical reconciliation admits those roles; this schema change grants no label eligibility itself.

## Time rules

Distinguish three independent questions:

1. **What happened/what did the feature describe?** Event time and feature valid-time establish historical alignment and causal/semantic suitability.
2. **When did the system obtain and qualify it?** Availability/materialization/audit timestamps establish earliest permissible use by a particular model fit.
3. **Was it available at a past forecast cutoff?** Required for replaying/evaluating that historical forecast, not for all later training uses.

A TRAIN_ONLY row is eligible for a future fit only when the event night precedes the held-out night, all required source/label/feature/audit readiness is strictly earlier than the effective training boundary, and the row satisfies the model's target/observation contract. Effective boundary is no later than min(declared fit cutoff, evaluated operational-night start at07:00JST, forecast information cutoff). Equality is excluded consistently with AGENTS. For final prospective fitting, choose a cutoff before the target operational night; Pn does not automatically authorize within-night training when the repository requires earlier-night training.

Define per-role `usable_at` conservatively as the maximum of proven source availability and required label/feature derivation/audit readiness. Do not backdate a new derived artifact merely because its raw source is old. If historical reproducibility uses a recipe that was genuinely available earlier, preserve that proven recipe/version history separately; otherwise receipt-time readiness is the honest default.

Feature historical validity is not implied by availability before October fitting. Examples: a road map received September30 needs evidence it describes August topology before being attached to August observations; an August weather archive can provide valid August measured weather without proving August forecast access; a biological-history feature for an August unit must exclude that unit's target capture and all later events. Transform scaling/selection still fits only eligible training rows. No outcome-derived feature is rescued by relabeling it retrospective.

Forecast/weather product semantics must match deployment: measured weather and an archived issued weather forecast are different features. A model trained on later observed future weather cannot claim realistic forecast skill when deployment supplies a forecast of that weather without an explicit reviewed mapping/error model. Calendar/time/location transforms may be reconstructed from real historical observation metadata for future training, but still do not prove an earlier model existed.

## Eligibility and sampling safeguards

Audited actual GPX may determine historical TRAIN_ONLY observation locations and search effort when its source quality/role/completeness permits. This is observation sample construction, not a held-out candidate universe. No absent capture log becomes zero; no sparse passage/spatial-only reconstruction becomes temporal negative; no fake path bridges missing coverage. Unknown and conflicting units remain explicit excluded records with reasons.

Observation-conditioned sampling is a target limitation. Positive-only observations cannot train calibrated Bernoulli occurrence probabilities or exposure-normalized rates without the required observation denominator. A spatial prior may use verified positives under its explicit semantics; use model-specific eligibility, never a global 'all rows valid for every family'. Retrospective GPX selection can be biased toward searches/hotspots; report this and do not claim island-wide biological presence/activity/detection from it.

Global canonical event IDs and unit identity prevent duplicates across corpus/cohorts/source copies. Repeated measurements belong to their true units; a target event cannot enter both training and that fold's held-out labels. Same-night units remain on the same side of the split. Outcome ledger coverage remains independent of candidate universe so out-of-universe captures are counted as misses. Historical research-exposed nights are permanently ineligible as untouched confirmation even if they are later imported into a new corpus or protocol ID.

## Fit/evaluation interface

Add a pure validated training selector, for example:

`select_training_rows(corpus, model_target_contract, fit_boundary, excluded_nights, protocol) -> EligibleTrainingSet`

It returns deterministic rows, exact accepted/rejected IDs with reasons, target/feature schema, data/code hashes, availability maximum and observation-scope limitations. `fit_recipe` consumes that typed set plus frozen configuration; it never discovers a candidate universe from training data. Models serialize training corpus/selection hash and actual fit cutoff.

`predict_composite` consumes an independently validated future ForecastUniverse/feature snapshot. Every forecast row must be ex-ante and available strictly before that cohort cutoff, including unobserved candidate units. Features are joined by explicit forecast row identity, never from held-out GPX or only labeled learning rows. Training locations cannot silently restrict prediction support to visited/capture cells.

For each DEVELOPMENT_FORECAST or confirmation fold, compute eligible training rows from the corpus as of that fold's real boundary. A September30 arrival is excluded from August/September29 folds and can be admitted for an October fold. Do not use the new corpus to manufacture old walk-forward predictions. Historical TRAIN_ONLY partition analyses may be useful exploratory diagnostics, but must be named retrospective development analyses and never credited as historical forecast availability or independent confirmation.

In the simplest Task6b confirmation design, train one selected model before the first untouched confirmation night and freeze all predictions/model/protocol before reveal. Newly received data after that freeze cannot alter it. A subsequent future model may use new data under a new development cycle, with fresh confirmation rather than recycling revealed nights. The three-candidate/two-round/300-second limits and code/inference closure remain unchanged.

## Materialization and minimal integration

Task6a's audited outcome ledger/observation units can later feed a deterministic corpus builder. Builder reads hash-bound audited artifacts and preserves rejected/unknown rows with reasons; no automatic canonical promotion of recovered response summaries. It creates a new immutable processed corpus in a run, leaving Raw/ORIGINAL/source bytes untouched. A corpus lacking features may be useful to a registered feature-free prior while feature-aware fitting reports the actual missing feature contract.

Later Task6b scope: one `src/training_corpus.py` selector/validator/builder boundary, `schemas/training-observation-corpus.json`, additive bundle-v2 dispatch in model_evaluation.py, and tests/test_training_corpus.py. Reuse Task6a evidence types and Task6b model fit/inference, do not duplicate parsers or create a second scientific pipeline. If Task6a already exposes a compatible selector, extend that module rather than adding redundant code. Keep v1 tests and semantics intact; no silent auto-conversion of a forecast snapshot into training-only or vice versa.

## Essential regressions

- August audited observations received September30 train a future October model without an August forecast universe; those same rows are excluded from August/September29 replay folds.
- Source/feature/label/audit time equal to training boundary is excluded; timezones and07:00 boundary enforced; a declared historical timestamp cannot override later proven receipt readiness.
- Retrospectively aligned measured weather is allowed only under its declared training feature semantics; future-weather/target-derived/incorrect-valid-time covariates fail their contract.
- Unknown search role/incomplete logging produces no negative; positive-only data cannot produce calibrated probability/effort-rate claims; unresolved count never defaults to1.
- Observation GPX yields train-only eligible units but cannot fill or filter held-out forecast universe; unseen/unobserved future universe rows remain prediction candidates.
- Adding a September30 source leaves all earlier legitimate historical fold outputs unchanged; future model identity changes with accepted new corpus content.
- Global duplicate/conflicting IDs, cross-split event overlap and same-night leakage fail; complete independent outcomes preserve outside-universe misses.
- Previously research-exposed August nights cannot become confirmation through a fresh bundle/protocol ID; changed confirmation outcomes do not change development selection/frozen predictions.
- Missing feature/source/corpus artifact and midrun replacement return explicit blockers/failure, not inferred data; immutable Raw/ORIGINAL hashes remain exact.

Conclusion: admitting properly audited retrospective TRAIN_ONLY observations for future fits corrects an overrestrictive schema coupling. It does not relax any held-out forecast availability, observation-quality, outcome-denominator or confirmation-independence requirement.
