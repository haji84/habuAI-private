# Live future-weather evidence and DEM-to-road-cell contract

This slice executes **real weather API requests in GitHub Actions** and defines an EPSG:32652, SHA-bound DEM-to-OSM 100m-cell join. Neither feature issues an ORIGINAL prediction or promotes a model.

## Live weather acceptance

GitHub Actions `.github/workflows/live-weather-e2e.yml` runs on this PR and by manual dispatch. It selects the next **unstarted** 07:00 JST operational night (not a historical night), calls two fixed Open-Meteo forecast reference points, and archives the exact two HTTP response bodies in one append-only JSON record under `evidence/exante/weather/<night>/`. Its report contains the digest, retrieval time, covered future forecast-hour count, and strict asset audit result. The actual record and report are uploaded as a 30-day private workflow artifact; they are **not** silently committed or labeled ORIGINAL P0. An outage or malformed API response fails this job.

Verify the LIVE source acceptance from an actual completed workflow run, not from the mocked unit tests. Live data is bound to its acquisition timestamp and must never be passed off as having been available earlier. One API run does not prove uninterrupted access or a P0 model.

## DEM join contract

`src/road_dem_join.py` supports projected ESRI ASCII DEM data supplied by a real, independently verified provider under **EPSG:32652**, plus source 100m candidate CSV from the OSM archive. It requires:
- exact SHA-256 for road CSV and DEM ASCII;
- explicit source availability times strictly before the future prediction cutoff;
- `utm52n_100m_X_Y` cell/coordinate consistency and OSM auxiliary provenance;
- 3×3 measured elevation support to calculate elevation, slope, downslope aspect, and local topographic position index;
- no interpolation/fabrication for missing/outside DEM cells.

Optional wind-vs-road orientation is **only a geometric incidence proxy**, not DEM-proven terrain wind shielding. Output is `SOURCE_JOIN_PARTIAL` if any cells lack coverage and always `formal_p0_eligible=false`. No real DEM source has been archived to this repo, so this implementation does **not** claim terrain completeness or a real island-wide feature raster.

Real GSI PNG DEM tiles may need a vetted source-preserving converter to projected ASCII with the correct coordinate reference, datum, nodata mask and hash provenance. Converting a WGS84 geographic raster by changing only its declared EPSG code is forbidden.

## Next blocked dependencies

- Demonstrate live weather E2E via actual Actions run.
- Restore OSM road archive into the actual candidate CSV and bind with correct SHA.
- Download or ingest official actual DEM and transform without changing source dates/provenance.
- Build hash-bound, leakage-safe `model_learning.json`, fit/evaluate a registered hierarchical 1km→100m predictor, implement the scoped 100m×10min target model.
- Establish trusted production issuer/Champion authority and immutable prospective P0 Freeze. Historical 10/22 ORIGINAL cannot be recreated.

See [Issue #64](https://github.com/haji84/habuAI-private/issues/64). The free Open-Meteo endpoint is research/non-commercial only under their terms.
