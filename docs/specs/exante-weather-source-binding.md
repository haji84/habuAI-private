# P0 ex-ante weather + GIS source binding (research slice)

## What is actually implemented

- `features/weather_sampling_sites.json`: official published **reference points** for 奄美大島・名瀬港 and 加計呂麻島・生間, not centroids and not a 100m road grid. Source: Kagoshima Prefectural Oshima Bureau 2023 location table 1-1, https://www.pref.kagoshima.jp/aq01/chiiki/oshima/chiiki/zeniki/gaikyou/documents/105599_20230512090024-1.pdf .
- `scripts/acquire_exante_weather.py`: network acquisition from the Open-Meteo forecast API using two configured sampling points, fixed variables and HTTPS, storing exact response bytes in JSON, response SHA-256, retrieval timestamp/availability and hourly *future* rows within the 07:00 JST operational night. Atomic `xb` write prevents overwrite. It does **not** issue a forecast, interpolate weather to roads, certify source trust, or perform P0 Freeze.
- `scripts/audit_p0_exante_assets.py`: read-only source readiness across actual weather capture, existing OSM auxiliary road evidence, missing DEM, missing audited learning snapshot, and blocked production model authority. It reports the source state as `BLOCKED` until every production gate is met; no automatic false positive.
- Regression tests exercise request parameters, append-only capture, cutoffs, no later injection, invalid provider responses, and unavailable GIS/model authority.

## Prototype invocation

For a future operational night, in an environment with internet and appropriate non-commercial access:

```sh
python scripts/acquire_exante_weather.py --night 2026-10-24 --purpose noncommercial-research
```

The output provides the path and sha256 of an append-only evidence file under `evidence/exante/weather/YYYY-MM-DD/`. The example date is not a schedule and should be replaced by the actual future operational night. No scheduled workflow is enabled by this PR.

To inspect data availability before issuing any P0:

```sh
python scripts/audit_p0_exante_assets.py --night YYYY-MM-DD --cutoff 2026-10-24T17:00:00+09:00 --weather-snapshot evidence/exante/weather/YYYY-MM-DD/<captured-name>.json
```

Both CLI commands intentionally remain outside `scripts/issue_prediction.py` and `scripts/freeze_prediction.py` until production authority and model adapters are reviewed.

## Limitations and next required work

1. **Source scope:** only two sampling reference points and **hourly model forecasts**; not a road-by-road microclimate, not 10-minute weather observations, no calibrated precipitation nowcast, moon position or tide. The provider's `best_match` ensemble/model selection is not a certified immutable individual model run. Preserve actual retrieval bytes and available_at but do not assume the provider's timestamps authenticate themselves.
2. **Road:** 2026-09-25 OSM audit indicates **16,990 candidate 100m road cells**, 15,329 Amami and 1,661 Kakeroma. Archive has 33 base64 parts and a recorded ZIP SHA. The `scripts/verify_osm_road_archive.py` utility rebuilds those exact parts in memory, validates SHA-256, ZIP CRC, member safety and bytes. Auxiliary OSM is still not the authoritative, version-bound full ForecastUniverse; legal drivable access and pre-departure availability remain mandatory.
3. **Terrain:** `src/terrain_road_features.py` has transformation/math utilities, but no validated island-wide DEM-to-100m-cell raster binding exists on main. A utility is not evidence that a terrain feature was measured.
4. **Model:** `src/model_evaluation.py` supports bounded diagnostic spatial baselines only; `champion_registry.SCOPE=SANDBOX_MECHANICS`. No trusted production model or authorized issuer and no formal 100m×10-minute target model are currently available. `data/processed/model_learning.json` is absent from main.
5. **True P0:** a trained registered model must consume an ex-ante, hash-bound forecast universe and weather/road/terrain source snapshot, then issue and Freeze **before exploration start**. `ORIGINAL` is never reconstructed later. Review activation, stage hierarchy, 1km Top10 Recall ≥90%, and 100m±10min scoring on genuine future observations.

## Weather use conditions

Open-Meteo's free endpoint is restricted to **non-commercial** use; this implementation fails closed when passed `--purpose commercial`. Commercial use needs an appropriate licence/alternative provider. Check https://open-meteo.com/en/terms and https://open-meteo.com/en/pricing before any monetized service. Weather data attribution is required. Do not expose detailed capture locations or private GPX through this weather capture.

**Status: prototype source acquisition + strict evidence audit implemented; weather production certification, fully connected model, genuine automated P0 and formal KPI remain BLOCKED.** Tracked under Issue #64.


## 2026-10-24 OSM archive byte-verification addition

```sh
python scripts/verify_osm_road_archive.py --repo-root .
```

Checks all 33 base64 parts, the recorded zip SHA-256 `f4d7a9925c98830a0b6918f756abe49b2b0f2eb935fc49c2d4eb42a732884c17`, CRC of every ZIP member, zip-slip paths and bounded expansion. The pre-exploration source audit now **requires this actual archive verification** before returning `AUXILIARY_CANDIDATE_ONLY` for the 16,990 OSM road cells. Any byte mismatch is `BLOCKED`. It does not assert that a restored parquet alone proves current legal vehicle access, official GSI provenance, valid 100m road-zone labels, DEM integration, or an actual trained production model.
