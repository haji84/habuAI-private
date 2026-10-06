# Habu AI Official Prediction Request Execution Contract v1.0

Status: Normative
Timezone: Asia/Tokyo
Operational-night boundary: 07:00

## 1. Trigger

The following user intents are OFFICIAL PREDICTION REQUESTS, including natural-language equivalents:

- 今日の予想
- 今夜の予想
- 今日どう？
- 予想出して
- 今日どこ行けばいい？
- 今夜何匹くらい？
- 今日のルート

A request does not become informal merely because it is short or conversational.

## 2. Forbidden shortcut

Chat, Work, GORIQ, Codex, or another controller must not answer an OFFICIAL PREDICTION REQUEST by manually combining remembered captures, a weather webpage, and narrative judgement while bypassing the canonical Habu AI prediction path.

A conversational estimate may be produced only as `PROVISIONAL_NOT_FREEZABLE` and only when the canonical path is unavailable or blocked. It must identify the exact missing or unvalidated components.

A manual estimate must never be labeled P0, ORIGINAL, official prediction, or Freeze.

## 3. Canonical execution sequence

The official path is:

Request
-> resolve operational night and cutoff
-> read canonical repository state
-> resolve active validated prediction model / Champion or approved baseline
-> build or load the ex-ante ForecastUniverse
-> build or load the feature snapshot using only information available by cutoff
-> acquire and bind current environmental inputs
-> execute model inference
-> execute area / road-zone hierarchy
-> execute route candidate logic
-> create prediction payload
-> validate lineage, cutoffs, hashes, and required outputs
-> Freeze immutable P0
-> return the frozen result to the user

No step may be silently replaced by human-style judgement.

## 4. Input families that must be represented

The exact registered model controls which features enter inference, but the prediction request must account for the available canonical evidence families below and must not silently ignore a supported family.

### Weather and environment
- temperature
- humidity
- rainfall and rain-after timing
- wind direction and wind speed
- pressure or pressure change when available
- observed or inferred road-surface state with provenance
- sunset / minutes since sunset
- moon illumination, altitude and moonset when supported
- tide only as an auxiliary feature unless validation promotes its role

### Terrain and road context
- DEM-derived elevation
- slope and aspect
- ridge / valley / foothill context when implemented
- terrain wind shielding / exposure
- road heading relative to wind
- road class and drivable status
- road-side context such as cut slope, ditch, retaining wall, vegetation/field edge when supported
- 1km -> 500m -> 250m -> 100m hierarchy

### Biological and historical context
- season and phenology
- recent owner captures
- sightings
- other-person captures
- roadkill / external reactions as separate reaction classes
- recent capture pressure
- recent search effort and traversals
- observed no-capture passages only where Negative eligibility is satisfied
- size / sex / behavior features where available and validated
- detection probability separate from occurrence probability when implemented

### Operational context
- route constraints
- vehicle-search assumptions
- exploration start/end window
- previously searched versus unsearched road exposure
- A/B/C route objective differences
- expected capture count
- size-class / large-individual probability when produced

Unsupported or missing features must be explicitly `NOT_PRODUCED`, `NOT_VALIDATED`, `UNKNOWN`, or `BLOCKED`; they must not be silently invented.

## 5. Terrain and wind rule

Wind must not be evaluated at municipality or named-area level alone when DEM/road geometry is available.

For route ranking, supported implementation must derive wind exposure or shielding using terrain and road context at the smallest available canonical road unit. A named place must not be called "windward" or "leeward" without evidence from the terrain/road calculation.

If the terrain-wind executor is unavailable, the route result is not official unless the active registered model explicitly does not require it and the prediction policy permits that model scope.

## 6. Official P0 Freeze gate

P0 may be frozen only when all mandatory prediction-time requirements for the active model/capability are satisfied.

At minimum the frozen payload must bind:
- operational_night
- cutoff_time
- issued_at / frozen_at
- prediction_version=P0
- prediction_class=ORIGINAL
- model_id / model_version
- model/spec hash
- code/runtime identity when available
- ForecastUniverse reference/hash
- feature snapshot reference/hash
- current environmental input references/hashes
- route input/constraint references where routes are produced
- expected count if produced
- area/road/time predictions required by the declared product capability
- A/B/C route candidates when route prediction is supported
- missing/not-produced declarations
- payload SHA-256

A text answer alone is not Freeze evidence.

## 7. Failure behavior

If canonical execution fails or a required input/executor is missing:

`status = PROVISIONAL_NOT_FREEZABLE`

The response must identify the blocking stage(s), for example:
- WEATHER_INPUT_BLOCKED
- TERRAIN_WIND_BLOCKED
- FORECAST_UNIVERSE_BLOCKED
- FEATURE_SNAPSHOT_BLOCKED
- MODEL_INFERENCE_BLOCKED
- ROUTE_OPTIMIZER_BLOCKED
- LINEAGE_BLOCKED
- FREEZE_WRITE_BLOCKED

The system must not hide a blocker by substituting a manual prediction.

## 8. Conversation behavior

When the user asks an OFFICIAL PREDICTION REQUEST, the assistant should execute first and then present the prediction.

It should not ask whether the user wants the "full" model, whether the user wants DEM considered, or whether the formal pipeline should be used. Those are already part of the request contract.

If the user then supplies live information during exploration, generate P1/P2/P3... using the existing immutable versioning rules. Never rewrite P0.

## 9. Evaluation consequence

A prediction that bypassed this contract is not an official ORIGINAL prediction and must not be included in official P0 scoring.

Historical conversational/manual forecasts may be retained as provenance but must be labeled noncanonical unless evidence proves they were produced by the canonical issuance path.

## 10. Principle

"今日の予想" means "run Habu AI and return its current official forecast", not "improvise a plausible Habu forecast in chat".
