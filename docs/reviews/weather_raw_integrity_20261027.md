# Archived weather raw-to-normalized integrity repair

Author implementation record; independent acceptance is pending Root/C review.
Base: `950cf33b143af98a5b1791b77cc4789ab253c7df`.
Branch: `codex/weather-raw-integrity-20261027`.

The weather asset audit previously checked the original body's SHA and each
derived hour's night, but did not check that stored numeric values came from
those bytes. A genuine call to the existing acquisition normalizer, using a
fixed synthetic response and clock, produced a valid archived bundle. Changing
only its derived temperature, humidity or precipitation still returned
`SOURCE_VERIFIED_NOT_PRODUCTION_READY`. These three public audit controls failed
as expected before the fix: one test method, three failures, 0.049s.

`validate_archived_sample` now reuses the existing `_normalize` implementation
with the exact archived UTF-8 body and declared original receipt time, night and
sampling point. It compares the complete normalized sample using finite JSON
encoding, which also distinguishes bools from numbers and preserves row order.
The asset audit invokes this offline check after its existing availability,
raw-SHA, resolution and night guards. No provider parser is duplicated. All
original acquisition functions, URL construction, clocks, response limits and
append-only archive behavior remain unchanged. The audit's source-capture
cutoff equality behavior remains unchanged; this does not relax stricter
feature-availability requirements elsewhere.

## Actual verification

Commands used the bundled Python on native Windows with `-B -X utf8`. Fixed
response bodies entered through the existing `fetcher` seam; no network, model
fit, cycle CLI or full source-audit execution occurred.

- Original focused acquisition and asset modules: 13/13 PASS, 0.231s.
- Required temperature/humidity/rain regression: actual RED 3 failures/0 errors,
  0.049s; after implementation GREEN 1 method/3 subcases, 0.040s.
- Final focused command `python -B -X utf8 -m unittest
  tests.test_acquire_exante_weather tests.test_audit_p0_exante_assets -v`:
  19/19 PASS, 0 skips, 0.465s. The six new methods cover the three primary
  alterations, all other weather variables, bool substitution, omitted/reversed
  rows, extra fields, changed hours, grid/URL/receipt selection, corrupt SHA,
  malformed or nonfinite original response data, and offline input preservation.
- Complete pre-edit/post-edit acquisition bundle bytes and complete asset audit
  bytes match exactly. The synthetic declared clock is
  `2026-10-24T10:00:00+09:00`; it is not a claim of an actual historical retrieval.
  Bundle SHA256: `63865cdeb3b49863e554b3fe07aa0c3535b526d07b96fcf3aaf86f2fd8be84ff`.
  Audit SHA256: `21032d7868397580abbb60802ca94fbc37e2d84f612ecb71f6cee0d0d39469f0`.
- In-memory compilation of both scripts and the affected test passed. AST
  comparison confirmed all original acquisition functions and all original test
  methods are unchanged; the original acquisition test file is byte-identical.
  LF and whitespace checks passed. No whole-suite or Ubuntu result is claimed.

Private evidence is under
`.worktrees/weather-raw-integrity-author-20261027/`: original raw-Git-matching
scripts/tests and complete `before/` and `after/` bundles/audits,
`normalized-values-RED.log`, `normalized-values-GREEN.log`, `focused-final.log`,
and `scope-verification-r2.json`. The first scope report used a filename suffix
that also matched the test filename and mislabeled one check; the corrected r2
uses the exact script path. Both reports are retained, with no product change
or omitted test caused by that author-harness issue.

## Scope and remaining feature gaps

This is internal consistency, not attestation of provider origin, run identity,
the declared receipt clock or site. A coherently replaced/rehashed response and
metadata are not authenticated by this repair. The scripts still cannot issue
P0 or validate road-scale interpolation, scientific training or production.
Original raw data, shared STATE/cycles/policy, models, requirements and workflows
were not changed. No actual new weather source was acquired or registered.

The read-only feature inventory at PR143 source
`5047fa768b6c527ecb7651e528c35c70aeb9ab8d` found reusable two-site hourly weather
acquisition, typed full-road auxiliary OSM projection, GSI PNG probing and a
hashed DEM road join. That tracked snapshot has no captured weather bundles,
real DEM rasters/probe PNGs or genuine planned-effort source in the inspected
namespaces; uninspected workflow artifacts remain UNKNOWN. The OSM trio supplies
road length/bearing but not the complete fixed seven A1/A2 physical features.
Real prospective weather mapping and full-road DEM/geometry coverage remain
necessary. Planned-effort and lagged-observation G0 kinds remain capability
blocked. No posthoc August OSM, ex-post weather backfill, interpolation, invented
search effort or zero-valued substitute was added. Full gap map and exact file
inventory are private alongside the author evidence. SOURCE positives remain
distinct from qualified TRAIN; Negative/search-complete/real TRAIN fit and
scientific validation remain zero/unestablished.

PR143's own CI/integration is a separate coordinator gate. This author branch is
not pushed, merged, frozen or independently accepted by this record.

## Subsequent bounded author followup

The initial checkpoint above is immutable commit
`52b9faf477174e66f16d11be23bb19e63f78f437`. Before independent acceptance, a
SHA-consistent original response containing `10**400` in a forecast value or
provider latitude exposed `math.isfinite`'s `OverflowError` through the new
archived-validator path. A new public regression actually produced two errors
in 0.022s. Only the new validator's pure site/time/normalization conversion is
now wrapped: overflow becomes `WeatherAcquisitionError`, so the existing asset
audit returns `BLOCKED`. There are no callbacks or I/O inside that catch; the
old `_normalize`, acquisition behavior and global audit exception boundary are
unchanged. Target GREEN: one method/two subcases, 0.020s. Fresh final focused
modules: 20/20 PASS, 0 skips, 0.343s. Complete valid synthetic bundle/audit bytes
again match the pre-edit baseline. The RED/GREEN/final logs and `after-r2/` are
retained separately from the initial checkpoint evidence.

C's separately authorized GitHub artifact inventory subsequently found a real
retained historical bundle from weather workflow run `39980377200`, artifact
`12512767777`. Its unchanged original JSON is 18,594 bytes/SHA256
`5379340c4b65144096748044f32ad4080d19ade525d39c0fef13a3aaf8cb0e76`.
The two samples each retain 23 future hourly rows and original availability
`2026-10-23T15:41:12.787383+00:00` and
`2026-10-23T15:41:13.284528+00:00`. An offline author compatibility check accepts
the unchanged original samples and rejects all three derived-value alterations.
This adds no new fetch, original source publication, historical clock rewrite,
road mapping, TRAIN or scientific credit. The earlier gap map's tracked-source
absence remains correct; its uninspected workflow-artifact status is now
supplemented by this concrete retained hourly/two-point source. Remaining
artifacts and full-road feature coverage are not inferred from this one bundle.

## Independent cadence finding and narrow repair

C's independent control on immutable `f1ddc24c347a960ba4b9c64d06904d8bf95bf08c`
found that self-consistent raw/normalized half-hour times could pass while the
sample declared `resolution_minutes=60`. Root authorized an archived-validator
only repair. The author first reproduced public asset-audit RED with three
controls (30-minute spacing, off-hour one-hour spacing, missing/two-hour spacing):
3 failures/0 errors, 0.032s. Expanded RED added nonzero seconds and microseconds:
5 failures/0 errors, 0.033s. Each control first proves that the unchanged provider
normalizer returns the exact altered sample, so this is not a raw/derived-value
mismatch disguised as a cadence case.

Only `validate_archived_sample` now checks the admitted normalized future
timestamps: every timestamp must be on a whole hour (zero minute/second/
microsecond) and every adjacent pair must be exactly one actual hour apart.
There is no interpolation, missing-hour fill, timestamp rewrite or new provider
parser. Original acquisition and `_normalize` bodies remain byte-identical. A
single admitted timestamp can only establish its own alignment; no unseen
previous/next hour or complete operational-night coverage is inferred. Provider
rows outside the admitted future window are not promoted to new coverage.

Target GREEN: one method/five cadence subcases, 0.041s. Fresh focused modules:
21/21 PASS, 0 skips, 0.344s. Complete original synthetic bundle/audit bytes remain
identical (`after-r3/`). Logs `cadence-RED.log`, `cadence-expanded-RED.log`,
`cadence-GREEN.log` and `focused-final-r3.log` preserve the real failure/repair
sequence. The retained real two-site/23-hour samples are checked unchanged in a
separate final-source compatibility receipt. No 10-minute data, full-road
weather geometry, DEM, complete seven-feature input, new actual acquisition or
scientific/TRAIN/production authority is created. Final independent acceptance
belongs to Root/C after reviewing this new immutable source checkpoint.
