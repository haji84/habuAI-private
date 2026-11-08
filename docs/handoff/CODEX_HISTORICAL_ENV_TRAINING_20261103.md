# Codex execution handoff: historical environmental backfill → training → independent evaluation

Date: 2026-11-03. Repository: haji84/habuAI-private (currently PUBLIC). Master Goal: haji84/AI- Issue #1642. Continue existing PR #136 where appropriate; inspect #92/#147 and other existing PRs before touching anything. DO NOT open a duplicate PR.

## Deliverable / Definition of Done
Build a reproducible, provenance-bound 2025–2026 historical training dataset and candidate model, including the 2026-11-01 exploration night. Backfill weather, temperature, humidity, wind direction/speed, precipitation, 24/48/72h antecedent rainfall, residual surface moisture estimates, topography/DEM, road orientation and exposure, solar/radiative conditions where defensible, moonlight and tide (Koniya reference). Run strict time-forward evaluation and compare against the existing champion/baseline; record full evidence. Never claim production promotion or a formal P0 unless the existing authority gates are satisfied.

## Inputs to locate and reconcile
- Private personal Library: /ハブAI/ and its Raw, Derived, Evidence, PDCA folders. Obtain through an authorized private connector; do not assume Codex can access ChatGPT Library.
- Historical integrated DB: ハブDB_2025-2026_10-20統合更新版_9月51匹訂正版.xlsx (the older 50-capture September version is superseded as a *candidate*, not silently overwritten).
- 2026 October: 13 exploration nights / 14 GPX originals (Oct24 has two distinct tracks and an unmeasured gap), 36 owner captures; prior 10/20 reconciliation suggested 17 already registered and 19 candidates, but recheck against latest DB.
- 2026-11-01: 2 owner captures; one sighting at 19:23 corrected by owner to ヤマシギ. Include the owner's route-selection hypothesis: temperature × wind direction/speed × terrain shelter × residual moisture after earlier rain. Never treat that hypothesis as confirmed effect.
- Previous generated candidates: habu_fullperiod_candidate_PRIVATE_20261103.csv and habu_fullperiod_feature_readiness_PRIVATE_20261103.csv (reported 4094 candidate rows, zero source-qualified training units at that time). Confirm hashes and access before trusting these counts.
- GitHub current main includes src/prospective_candidate_model.py, models.research_selection source gating, docs/specs/leakage-safe-feature-candidate.md, docs/specs/g0-training-source-contract-v1.md, reports/osm_road_candidate_grid_report.md. OSM 100m road cells are supplementary, not official-road-GIS by fiat.

## Execution stages (do not stop at a plan)
1. Inventory latest HEAD, open PRs, private original files and hashes; produce canonical/duplicate/conflict/missing matrix. Do not ingest private GPS into public git or PR diffs. Check historical exposure before editing public history; no history rewriting without approval.
2. Normalize capture vs sighting/roadkill/missed capture/other-species records, preserve original text verbatim, 07:00 JST night boundary, retain independent identity of 2026-10-29 19:03 captured and escaped animals. Do not double-add captures. Missing species and ambiguous records remain unknown until verified.
3. Use source-attributed historical weather archives and tide observations/predictions with explicit station, coordinates, time zone, valid time, observation/forecast/reanalysis type, retrieval time, licence, missingness and source SHA. Regional Setouchi/Koniya data are not automatically true at every road. Never fabricate microclimate or surface wetness. Compute 24/48/72h rainfall windows only when source coverage supports them.
4. Match measured GPX to permissible road graph and 100m × 10min units; separate measured vs road-reconstructed vs unknown. Oct24 missing GPS cannot become measured or negative labels; reconstruction must preserve owner's confirmed Koniya→Agina→Katsuura→Aminoko→Route58→Uken ordering and separate time uncertainty. Negative units only where independent search exposure and complete capture-outcome coverage are proven by existing selector contract.
5. Derive slope/aspect/TPI/road azimuth/terrain shelter, relative wind and lagged moisture proxies with uncertainty and as-of provenance. Compare alternative lag horizons and interactions without leaking outcome information into features.
6. Run existing source-bound training selector, source-readiness validation, and training. Fail closed if zero qualified units; report exact blocker by night/field/source rather than inventing a fitted model.
7. Evaluate strict chronological walk-forward with embargo and genuine future nights untouched by fit/model selection; compare existing champion and simple baselines using Brier/calibration, 1km Top10 Recall and 100m ±10min metrics where measurable. Preserve immutable original P0/P1 and timestamps; retrospective reconstruction is diagnostic only.
8. Record executable commands, tests, CI run IDs, input/feature/code/model SHAs, source coverage, rejection reasons, candidate artifacts and independent verification. Only recommend champion promotion after evidence and human approval; no automatic production merge.

## Human gates
No costs, new paid API, public release, access/permissions changes, new private storage provisioning, history rewrite, irreversible data edits or main merge without explicit owner approval. Do not create new PRs for the same task; reuse existing PR and maintain Draft when needed. Public repo contains historical sensitive coordinate risk: only publish non-sensitive code/docs/synthetic tests/aggregate evidence. Private raw GPS, precise capture locations, full private derived data and secrets must remain private.

## Immediate next action
Check current PR #136 and #147 file inventories, latest candidate datasets and 51-capture corrected workbook, then implement a minimal real end-to-end source-qualified historical environmental backfill slice and run tests. Report exact passed acceptance criteria and unresolved blockers, not a future plan alone.
