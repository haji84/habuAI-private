# Prospective forecast input binding v2 (preproduction only)

## Scope
This slice adds `src/prospective_inputs.py` and synthetic regression tests. It does **not** authorize production Champion inference, provide weather/DEM/route executors, create a real ForecastUniverse, issue an ORIGINAL forecast, or freeze P0. No historical data, GPX, observations, raw file or predictions are modified.

The primary entrypoint is `load_prospective_inputs(root, snapshot_path, snapshot_sha256, operational_night, as_of, model_feature_names=..., budget_seconds=30.0)`. It is deliberately read-only. The return value has `official_issuance_authorized=false` and `qualification=PREPRODUCTION_INPUT_INTEGRITY_ONLY`. The v1 sandbox issuance contract remains unchanged.

## Versioned feature snapshot v2

A snapshot JSON stored under `features/` has:

- `schema_version = "2.0"`
- `operational_night` and timezone-aware `cutoff_time`
- `universe = {path, sha256, available_at}`
- `features = [{path, sha256, available_at}, ...]` for each registered required numeric predictor
- `feature_schema_sha256 = sha256(canonical_json(sorted(feature_names)))`

The referenced `ForecastUniverse` remains v1 with `schema_version=1.0`, `source_type=EX_ANTE_FORECAST`, explicit `geographic_domain`, and `rows`. Every universe row must contain unique `row_id`, `operational_night`, `cutoff_time`, `window_start_jst`, and valid coordinates (UTM52N meters or latitude/longitude). Ten-minute windows must be in the stated operational night and strictly later than actual issuance time. Unit identity uses the 100m cell and the window instant normalized to UTC: JST and UTC spellings of the same instant cannot create separate units.

Each feature source has `schema_version=1.0`, `use_role=static_predictor|forecast_predictor`, `feature_name`, `available_at`, `operational_night`, `cutoff_time`, and `values` as a mapping from every ForecastUniverse row ID to a finite numeric value. No source can add or remove rows. Missing values are not imputed. Duplicate names, conflicting time/hash data, post-outcome fields or stale windows reject the whole join. Model feature names must match the snapshot exactly if a registered model declares them.

Known outcome schema keys (`label`, `observed`, `label_available_at`, `outcome`, `actual_capture`, `capture_event_ids`, `capture_count`, `gpx_trace`, `negative_observed`) are forbidden throughout the snapshot, universe and feature metadata, including nested dictionaries/lists, and cannot be `feature_name`. The feature `values` mapping has row IDs as keys; these identifiers are not schema fields and its values must be finite numbers. This is an exact known-name check, not a substring prohibition: a predictor such as `prior_capture_count_7d` remains eligible under the existing ex-ante role, scope and strict availability requirements. The check does not authenticate a predictor's semantics or provenance.

Each source read is bounded to 128 MiB and all distinct consumed raw inputs to 384 MiB, using bytes actually read rather than a prior file size. A bounded read may read one extra byte solely to detect and reject an overrun. The final recheck uses the same bounded limits with a separate scan budget. There may be at most 32 feature sources (34 consumed files including snapshot/universe), 2,000,000 universe rows and 400,000 joined numeric cells (`row count × feature reference count`). Feature count is checked before opening the universe; the cell count is checked before allocating output rows or reading feature sources. The feature cap follows the suggested 32-expanded-column engineering ceiling in `docs/plans/master-goal-1642-feature-models.md`; this validator does not implement model transformations. The cell cap is a conservative preproduction engineering limit: the original synthetic 2,000-row × 200-feature join (about 5 MB raw input) used approximately 86.5 MB additional peak RSS in the review environment. That original feature count now exceeds the stricter source cap. A six-window, 101,940-row universe with three numeric features fits the cell cap (305,820 cells); this capacity example establishes no scientific forecast performance. These limits bound multiplicative expansion, not total process memory; JSON/metadata and runtime overhead remain additional costs. Larger workloads require a separately reviewed streaming/storage design.

Validation uses a monotonic elapsed deadline, default 30 seconds. `budget_seconds` must be a finite positive number at most 300 (booleans are invalid), respecting the existing parent command's 300-second ceiling. A parent caller must supply its smaller remaining allowance rather than starting an independent budget. Checks occur around bounded source reads, hashes, JSON parsing/canonical validation, each metadata node, universe row, feature/join cell, and final recheck. Expiry raises `TimeoutError` and returns no rows. Individual reads/parses/hashes are cooperative operations: byte limits bound their input, but the deadline does not OS-preempt a blocking read or interrupt a single parse/hash. It detects expiry at the next check and prevents a successful return; it is not a hard real-time guarantee.

SHA-256 checks compare the exact raw bytes parsed for each source and sequentially recheck all consumed files immediately before returning. Returned rows are derived from hash-verified in-memory input bytes. The sequential filesystem recheck is **not an atomic snapshot**: a concurrent writer can change an already checked file while a later file is checked, or change a file after its check. A detected change rejects validation; successful validation makes no simultaneous-filesystem-state guarantee. An atomic publication boundary requires independently immutable/content-addressed storage or coordinated writer locking. A matching hash proves byte consistency only; it does not prove that a source was genuinely available before the historical cutoff, or that weather, GIS and capture-pressure measurements are authentic.

## Remaining production gate

1. Bind independently acquired, provenance-verified current environmental and road/terrain features and a full-scope prospective Universe. No backfilling of time/source or use of observed GPX as future-road universe.
2. Implement the registered feature-aware model adapter and its independently validated Champion/approved baseline. Integrate this validator into issuance using model identity and code closure, not merely a caller-provided feature list.
3. Add verified time-target generation, count/activity/detection applicability, A/B/C topology-constrained routes and their own evidence.
4. Complete Task8's trusted production registry, scientific reproduction, exact-head CI/review and immutable ORIGINAL publication. Validate an actual future-night E2E run. **Only then** issue official P0.

Until these are met: `PROVISIONAL_NOT_FREEZABLE`. Synthetic passes are development evidence only.
