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

Tests exercise synthetic cell/time records and corrupted assumptions. The read-only original-byte probe below is evidenced; **durable source materialization, exact-head Linux GitHub Actions CI and independent producer review are not yet evidenced for this PR**. A passing synthetic test would not establish those facts. Pure builder import no longer imports `fcntl`; the durable publication entrypoint still requires the real POSIX implementation before any byte write. This enables Windows parsing/planning tests without a fake lock or a claim of Windows durable publication support.

As-of availability proof requires an independently authenticated intake/generation receipt. The OSM archive's date/metadata alone cannot prove forecast-time access in September 2026. Materialization must happen before the real prospective cutoff and future issuance may not use a backdated path/JSON.

Complete formal prediction still requires registered scientific Champion/approved baseline, multi-source features (current forecast weather, DEM-road shielding/wind, historical search pressure), formal 100m ±10min inference, fully supported A/B/C graph routing, trusted Task8 production activation and immutable P0 publication. Until then, output status is `PREPRODUCTION_INPUT_ONLY` and official requests return `PROVISIONAL_NOT_FREEZABLE`.

## 2026-10-25 strict migration audit and accepted next slice

PR33 source `cd97e69a2d1cfb160b21f33a3e561be989d5ba8d` was non-destructively
merged with main A1 and strict PR32 `de4ae4c`; main `fb06f76` was subsequently
reconciled. The audit changed no canonical source byte. A real read-only probe
decoded all 33 parts (6,460,688 bytes), verified the pinned 4,845,515-byte ZIP,
all-member CRC (112 files plus 3 directories), pinned 4,408,826-byte CSV and
16,990 unique eligible archived cells (15,329 Amami / 1,661 Kakeroma). All part
SHA-256 values were identical before and after. Canonical digest of the ordered
`{path,size_bytes,sha256}` part-reference list was
`00ddf784d144893ec1f9e7e9d5483c2401467742e71d72ccba32487d3c28f1bb`.

Compatibility probes confirmed two intentional strict blocks: original
`artifacts/...zip.parts` references are outside its generic source namespace,
and legacy `static` sources cannot have hidden parents. Wrapping CSV data in a
new raw JSON envelope or copying an original reference into `data/processed/`
would therefore hide lineage. Existing producer IDs/time-major row order,
metadata envelopes and missing four-stage readiness are also not strict G0.

The coordinator accepted this additive implementation design; it is not yet a
claim that the producer implements it:

1. Add only typed `osm_archive_part` (protocol), `osm_road_cells_csv` (protocol)
   and `osm_static_projection` (universe or feature) source kinds. Allow original
   paths only for exact ordered part000–032 transport nodes. Every part remains
   a real consumed SHA/size-bound source; generic static sources stay unchanged.
2. Bind CSV parents to those original parts and require an independently
   size/SHA-checked provenance reference. Decode the pinned ZIP, check safe
   bounded members/CRC, and compare the exact CSV member bytes with the declared
   derived CSV. Never execute archived scripts. Nullable event/physical validity
   is restricted to transport containers, with four readiness stages still required.
3. Bind each projection's fixed operation/version/code identity and CSV parent.
   Recompute physical cell membership, archived road length and axial cos/sin
   from actual CSV bytes; compare the domain and each row's numeric values.
   Preserve auxiliary class and unknown current road access/closures.
4. Use a separate derived capsule containing exact original-part replicas in
   their original relative namespace, real derived CSV, code/policy and explicit
   provenance. No external path indirection or canonical-source modification.
   Current-run read/copy/derive/durable materialize/check timestamps may be
   recorded truthfully; cached/ZIP/mtime metadata cannot recreate historical
   availability. Missing current-run proof remains `G0_INPUT_BLOCKED`.
5. Emit canonical cell-major UTC physical IDs, mandatory definitions, full
   declared future horizon partitions, all shards and per-row physical validity.
   Publish the full-set manifest last after complete source/shard validation and
   final rescan. Initial strict shards can use one window to keep parsed working
   sets smaller; six windows remains an upper bound, not a requirement.
6. Preserve 300s, 128MiB/source, 384MiB/shard, 32 features, 400,000 joined numeric
   cells/shard, 4,000,000 domain rows and shared actual-read 2GiB limits. These
   byte/expansion limits are not a proven 128MiB whole-process memory bound.
   Geography coverage means the declared archived cell set, not all-island or
   vehicle-access certification; all science/fit/production authority stays false.

Actual CSV-based encoding probes found 16,990 rows with three features occupy
11,768,108 canonical model-row bytes with short source paths; six windows require
about 70.6MB. Thus even the old 101,940-row shard exceeds the separate 16MiB
model collector limit. Full 72-window coverage is 1,223,280 rows and cannot be
ranked by concatenating subset M2 predictions.

With compact UTC identities, one-window universe/features require 5,856,338 bytes
and explicit physical-validity rows 4,621,420 bytes. The former strict validator's
four reads of joined artifacts plus two validity reads would require at least
2,351,912,784 bytes for 72 windows, before archive/code/manifest costs. Pure
`join_prospective_payloads` (dependency commit `f9bb409`) now reuses owned checked
payloads; legacy loading keeps its original bounded read/final rescan, and strict
keeps its own full-closure final rescan. Actual reads remain charged. Two reads
reduce that 72-window lower bound to 1,508,690,232 bytes; runtime success is still
unverified and every smaller remaining allowance applies. The corresponding
144-window set remains about 3.02GB and honestly capacity-blocked. A full-night
receipt would certify software/declaration coverage, not full-night prediction.

