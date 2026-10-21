# Verified OSM auxiliary roads → prospective ForecastUniverse shard

Status: **preproduction data materialization code**, NOT a successful production prediction.

## Canonical input and provenance

The source is the actual immutable OSM auxiliary road archive already in this private repository:

- `artifacts/Habu_AI_OSM_Road_Grid_2026-09-25.zip.parts/part_000.b64` through `part_032.b64`, strictly 33 ordered parts.
- Restored original ZIP SHA-256 `f4d7a9925c98830a0b6918f756abe49b2b0f2eb935fc49c2d4eb42a732884c17`.
- Extracted 100m candidate-cell CSV SHA-256 `33ea1df38351d9c2454bf2efc9b00432119e484d5d549a567bc8fd2d337151a4`, 4,408,826 bytes.
- Previous independent evidence audit documents 16,990 road cells: Amami Oshima 15,329 and Kakeroma 1,661. This evidence establishes stored source bytes and spatial coverage, not live traffic legality or model eligibility.

`scripts/build_osm_prospective_universe.py` verifies archive/CSV hashes before parsing, rejects duplicate/noneligible cells, and uses only the actual road grid's 100m UTM52N cell centers, measured processed road length, and axial direction. It never reads the evaluation-night GPX or capture outcomes.

Output rows cover every road cell for each explicitly selected future ten-minute window. Static explanatory features: `road_length_m`, `road_axial_cos`, `road_axial_sin`. Source class remains `osm_auxiliary`, **not official road GIS**. Missing current road regulations, DEM, wind and weather cannot be imputed from road orientation.

## Bounded execution

Example from a checked-out repository, **only with a future cutoff later than actual file generation**:

```bash
python scripts/build_osm_prospective_universe.py \
  --repo-root . \
  --output-root /tmp/habu-predict-candidate \
  --night 2026-10-15 \
  --cutoff 2026-10-15T18:00:00+09:00 \
  --first-window 2026-10-15T19:00:00+09:00 \
  --windows 6
```

Do not copy the example future date or cutoff without adapting to the actual night and current clock. The materializer verifies the clock at build start, after the source files have been written, fsynced and moved to their final paths, and after the snapshot has been published and fsynced. Each check must precede the cutoff strictly. Snapshot source references record the observed source-ready time as `available_at`; the feature payloads retain their earlier generation timestamp. The returned `completed_at` records completion of the snapshot publication. A manually asserted earlier availability or an artificial pre-cutoff timestamp is not accepted by this entrypoint.

`snapshot.json` is published last and is the completeness marker. If any write, fsync, rename or final cutoff check fails after the new shard directory has been created, that call's shard is removed and no success result is returned. Existing shards are never removed by this cleanup. A delayed build cannot leave a usable snapshot claiming pre-cutoff completion.

The output is placed in a new derived workspace (`features/forecast_builds/<night>/<creation-time>/`), with `universe.json`, three numeric feature sources and a hash-referenced v2 `snapshot.json`. The max one-hour shard is intentional to bound RAM and file size; this is **not a whole-night official universe**. A complete forecast horizon will require a separate reviewed orchestration that covers all required windows and preserves whole-scope denominator and route timing. The materializer is not the planned full-night production model.

The output root and the generated paths must remain outside the canonical repository. Existing symlinks in the output root, its ancestors, the shard directory chain or lock path are rejected before writing through them, using the repository's existing `safe_path` contract. An output root above the repository is also rejected when its generated descendants would enter the repository. Canonical raw bytes remain read-only.

The generated snapshot's format is for the v2 read-only validator proposed by PR #32. The two PRs are separate review slices; do not enable them as a production issuer or merge them merely because input hashes match.

## Acceptance and trust boundaries

Tests exercise synthetic cell/time records and corrupted assumptions. **Actual source materialization, original-byte verification in a clean runtime, exact-head GitHub Actions CI and independent review are not yet evidenced for this PR**. A passing synthetic test would not establish these facts.

As-of availability proof requires an independently authenticated intake/generation receipt. The OSM archive's date/metadata alone cannot prove forecast-time access in September 2026. Materialization must happen before the real prospective cutoff and future issuance may not use a backdated path/JSON.

Complete formal prediction still requires registered scientific Champion/approved baseline, multi-source features (current forecast weather, DEM-road shielding/wind, historical search pressure), formal 100m ±10min inference, fully supported A/B/C graph routing, trusted Task8 production activation and immutable P0 publication. Until then, output status is `PREPRODUCTION_INPUT_ONLY` and official requests return `PROVISIONAL_NOT_FREEZABLE`.

