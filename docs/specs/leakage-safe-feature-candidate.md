# Feature-aware candidate predictor: research only, never an ORIGINAL P0

This module provides a deterministic empirical feature-aware baseline for the strict P0 pipeline. **No real trained production model is claimed** until source-audited multi-night exposure units, terrain/weather snapshots, review and independent holdout are provided.

## Model
- `src/prospective_candidate_model.py`: L2-regularized logistic occurrence baseline fitted on GPS-verified road-time units with features `temperature_c`, `humidity_pct`, `precipitation_mm`, `slope_deg`, `tpi_m`, `road_length_m` and `wind_cross_road_proxy`.
- Training records must carry operational night, 100m projected road cell, 10-minute future window, historical forecast cutoff, features availability time, source SHA, verified actual GPX passage, owner Habu capture count, observation source SHA and outcome availability date. Other species, sightings and roadkill do not become personal captures.
- At least five training nights plus two strictly later untouched holdout nights; any training with outcome labels or feature data unavailable at their respective cutoffs **throws an error**. Missing GPX passage does not create negative samples.
- Holdout Brier metric is explicitly *diagnostic*, not strict external Stage1 recall. All model output is tagged `DIAGNOSTIC_WALK_FORWARD_CANDIDATE_ONLY`, not validated.
- Prospective scoring returns ranked 1km area candidates, linked 500m/250m zones and 100m ×10minute candidate probabilities for an explicit future operational night; only known ex-ante source rows qualify.
- Scores are **within a caller-provided candidate road universe** and are not certified to cover off-universe capture events, all legally drivable roads or all observed searches. Therefore the official Stage1 Top10 Recall and formal 100m±10min KPIs are **not computed**. Three fully drivable A/B/C routes are not produced.

## Why there is no real training PASS yet

The main branch still lacks `data/processed/model_learning.json` and a validated merged observed-exposure dataset covering multiple eligible historical nights; the available historical log and GPX records are fragmented. The auxiliary OSM archive has validated bytes and an accessible 100m candidate-cell table but its legal/current road universe status is unresolved. The official GSI DEM for these cells is not yet ingested with spatial coverage and hashes.

Current weather E2E [PR #67](https://github.com/haji84/habuAI-private/pull/67) actually contacted the weather API and saved 2-site future-night source bytes, but these do not substitute for the historical *as-issued* forecasts required to train and fairly evaluate weather sensitivity.

## Production gate remains closed

`src/champion_registry.py` and `scripts/issue_prediction.py` still allow only sandbox test issuance. A candidate model JSON or a positive mock test does not grant trusted production authority. A future P0 must bind actual model, code, weather/terrain/road and source availability hashes, be created before physical search start and frozen without mutation. At 07:00 JST the exploration night boundary resets.

Next milestones in Issue #64: (1) audited actual multi-night learning records, (2) complete ex-ante road universe + real DEM/weather forecast snapshots (3) scientific holdout validation including outside-universe misses, (4) trusted authorized production issuer, (5) first real pre-search ORIGINAL P0 + subsequent ground-truth P0-vs-Pn PDCA.
