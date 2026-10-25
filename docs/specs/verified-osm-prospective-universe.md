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

The coordinator accepted and the additive strict implementation now follows
this design. Independent producer review and exact-head Linux CI remain pending:

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

## Additive strict capsule API

`materialize_g0(repo_root, output_root, night, cutoff, first_window, window_count,
budget_seconds=300, _read_context=None)` uses a new, previously nonexistent output
root outside the source repository. The CLI selects it with `--strict-g0`;
omitting that flag retains the original six-window legacy producer and its
integrity-only meaning. Strict output currently partitions the complete declared
archived cell domain into one-window shards. It never allocates the full-night
cell×window product at once and never silently narrows the requested horizon.

All source reads, copied-file readbacks, decoded/expanded archive bytes, strict
initial reads and rescans share the same `ProspectiveReadContext`. A caller's
existing deadline and remaining actual-byte allowance can only tighten. Each
copy/generated file is opened exclusively, fsynced, and actually read back for
size/SHA equality. All ancestors, including ancestors above the selected root,
are checked against symlinks/junctions/reparse points before reads and writes.

The private staging directory contains the exact original relative part paths,
`data/processed/osm/cells.csv`, copied fixed policy/builder code, typed projection
descriptors, physical domain, every shard and validity sidecar, and the complete
manifest. The whole set passes strict validation and all final source rescans
before atomic publication of the new output root. Failure yields no success or
public manifest. Existing output roots are never overwritten. On POSIX, real
file/directory fsync is used; Windows truthfully reports
`FILE_FSYNC_ATOMIC_RENAME_ONLY`, without claiming a POSIX directory durability
barrier or installing a fake `fcntl`.

`features/osm-current-intake.json` binds the actual current source Git commit,
all ordered part byte references, the read/derive/copy/readback timestamps for
each part, pinned archive/CSV identities, and current run start/completion. It
states `historical_access=NOT_ATTESTED` and
`source_authenticity=NOT_ATTESTED`. CSV/projection/code/policy/shard sources have
their own mandatory four-stage readiness. The producer samples actual UTC wall
time during operations, rejects wall-clock reversal, and rejects completion at
or after the declared cutoff. There is no caller-provided readiness/backdate
argument. These records attest software operations, not source truth, historical
first access, current road regulations or whole-island traffic access.

The strict validator's `as_of` must be at least the cutoff. The producer finishes
before that future cutoff, so its internal all-set check deliberately uses the
declared cutoff as a **software rehearsal clock**. The outer result says
`AUXILIARY_G0_SOFTWARE_REHEARSAL_ONLY`, records `actual_completed_at`, labels
`validation_clock=DECLARED_FUTURE_CUTOFF_REHEARSAL`, and requires actual issuance
to revalidate at its real time. A nested strict declaration receipt must never be
presented as a current prediction. Issuance, fit, scientific and production
authority all remain false.

The exact strict manifest/ref and `feature_definition_sha256` are returned for
subsequent caller binding. Whole-domain model collection remains a separate API
with both 120,000-row and 16MiB canonical-row caps. Receipt success does not grant
chunked M2 ranking, concatenated subset Top10s, or full-night model computation.

## Recorded current-run checks

Synthetic new-kernel tests first rejected unsupported typed kinds, then passed
after the narrow extension. Producer tests first rejected its missing API, then
passed with real filesystem writes/fsync/readback. Adversarial checks cover all
33 part bindings, changed parts with recomputed metadata, exact CSV membership,
fixed recomputed feature values, narrowed domain, transport type/class rules,
missing/untrusted historical proof, complete rectangular coverage, no partial
publication, late clock/deadline cleanup, original-source final rescan mutation,
and real Windows junction input ancestors. ZIP decoding preflights remaining
capacity and every stream read is bounded by remaining bytes plus one rejection
byte, with all actual output bytes charged.

A real original-source run on 2026-10-25 completed 16,990 cells × one future
window × three static features in 2.734 seconds, with 157,253,104 actual bytes
charged across producer and validator. Original part SHA values were identical
before/after. The future declaration used operational night 2026-10-26,
cutoff 18:00 JST, horizon 19:00–19:10 JST; actual completion was
2026-10-25T05:04:51.200033Z. This is explicitly a small complete declared horizon,
not a completed full-night model or prediction. Runtime capsule outputs stay
outside Git; the original 33 parts are not recommitted.

The earlier 1.51GB 72-window bound above is validator-only. In this end-to-end
producer the additional required materialization readback makes three passes
over large generated artifacts, about 2.26GB before source-closure overhead.
Consequently a full 72- or 144-window producer can be capacity-blocked by the
unchanged 2GiB shared ledger. Readback is not hidden and limits are not raised.
The requested complete horizon must either pass as a whole or return a block;
no smaller subset is relabeled as the full night.

The full 72-window producer was actually run: it blocked after 181.484 seconds
at 2,147,483,649 actual bytes (the 2GiB maximum plus one rejection byte), returned
no success, and left no published output root. All canonical part SHA values
still matched. The 144-window producer has not been run; its greater byte lower
bound remains a capacity block, not a measured success. No hard whole-process
RAM bound is claimed from these runs; 128MiB/source remains the enforced input
file limit. Targeted Windows verification ran 147 tests: 146 PASS / one POSIX
symlink skip. The existing legacy POSIX materialization tests still require
Linux CI; they were not skipped or treated as successful Windows executions.

