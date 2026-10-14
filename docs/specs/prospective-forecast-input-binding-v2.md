# Prospective forecast input binding v2 (preproduction only)

## Scope
This slice adds `src/prospective_inputs.py` and synthetic regression tests. It does **not** authorize production Champion inference, provide weather/DEM/route executors, create a real ForecastUniverse, issue an ORIGINAL forecast, or freeze P0. No historical data, GPX, observations, raw file or predictions are modified.

The primary entrypoint is `load_prospective_inputs(root, snapshot_path, snapshot_sha256, operational_night, as_of, model_feature_names=...)`. It is deliberately read-only. The return value has `official_issuance_authorized=false` and `qualification=PREPRODUCTION_INPUT_INTEGRITY_ONLY`. The v1 sandbox issuance contract remains unchanged.

## Versioned feature snapshot v2

A snapshot JSON stored under `features/` has:

- `schema_version = "2.0"`
- `operational_night` and timezone-aware `cutoff_time`
- `universe = {path, sha256, available_at}`
- `features = [{path, sha256, available_at}, ...]` for each registered required numeric predictor
- `feature_schema_sha256 = sha256(canonical_json(sorted(feature_names)))`

The referenced `ForecastUniverse` remains v1 with `schema_version=1.0`, `source_type=EX_ANTE_FORECAST`, explicit `geographic_domain`, and `rows`. Every universe row must contain unique `row_id`, `operational_night`, `cutoff_time`, `window_start_jst`, and valid coordinates (UTM52N meters or latitude/longitude). Ten-minute windows must be in the stated operational night and strictly later than actual issuance time.

Each feature source has `schema_version=1.0`, `use_role=static_predictor|forecast_predictor`, `feature_name`, `available_at`, `operational_night`, `cutoff_time`, and `values` as a mapping from every ForecastUniverse row ID to a finite numeric value. No source can add or remove rows. Missing values are not imputed. Duplicate names, conflicting time/hash data, post-outcome fields or stale windows reject the whole join. Model feature names must match the snapshot exactly if a registered model declares them.

SHA-256 checks compare raw input bytes, including each source, and recheck all consumed input files immediately before returning. A matching hash proves byte consistency only; it does not prove that a source was genuinely available before the historical cutoff, or that weather, GIS and capture-pressure measurements are authentic.

## Remaining production gate

1. Bind independently acquired, provenance-verified current environmental and road/terrain features and a full-scope prospective Universe. No backfilling of time/source or use of observed GPX as future-road universe.
2. Implement the registered feature-aware model adapter and its independently validated Champion/approved baseline. Integrate this validator into issuance using model identity and code closure, not merely a caller-provided feature list.
3. Add verified time-target generation, count/activity/detection applicability, A/B/C topology-constrained routes and their own evidence.
4. Complete Task8's trusted production registry, scientific reproduction, exact-head CI/review and immutable ORIGINAL publication. Validate an actual future-night E2E run. **Only then** issue official P0.

Until these are met: `PROVISIONAL_NOT_FREEZABLE`. Synthetic passes are development evidence only.
