# October source re-audit: existing PR39 and PR50

Read-only audit completed2026-10-25. This document persists that completed audit;
it does not perform another source search or register any source role.

- Main used for the completed audit:
  `d2f8c759ad9817cdcafab4c97c4fbdf5f4fb08b3`.
- Documentation-only branch base:
  `0255e101337513e5013ce31edf68c085240243a9`.
- PR39 exact head: `521dd1cce1c680a3a6b58f0396744f9b715cd06e`, open/unmerged.
- PR50 exact head: `86127f79163fd004cf65b5b6fc8ab2ad5f154ac8`, Draft/open/unmerged.

The authenticated GitHub connector supplied exact PR metadata, changed-file
lists and selected file contents. Native Git objects supplied byte/hash and
historical-tree comparisons. PR50's generated report ZIP was reconstructed and
read in memory; compressed/raw SHA, byte lengths and ZIP CRC were checked.
No source was promoted, no PR was merged and no repository Raw/processed,
policy, model, state or cycle file was written. No events or coordinates were
posted to an Issue. No additional upload is requested.

## Existing audit versus the current PR39 delta

Main already contains `docs/reviews/work-2026-10-21-data-audit.md` and
`docs/work/WORK_CHECKPOINT.md`. These record PR39 source verification at
`5d05e4889ebd37e50fd6e2eb29c7589b25b8e30a`: four genuine GPX originals,
56762 trackpoints, six owner-capture statements and one separate roadkill
reaction. These are source/trajectory consistency observations, not prediction
accuracy, certified search exposure or complete outcome coverage.

The exact Git diff from that previously audited head to current PR39 adds only
the following three derived audit files. The four GPX originals, capture CSVs
and exploration-session CSVs are unchanged; no additional primary field-log or
raw-chat original was introduced by this delta.

| Current PR39 added file under `evidence/audits/` | Bytes | SHA256 |
| --- | ---: | --- |
| `2026-10-06_08_14_15-search-stop-candidates.json` |10792|`bd03ab7e53a2039ad769921d722f37175cf4ecbfacb7ecdfc149bd01041035c5`|
| `2026-10-06_08_14_15-search-stop-candidates.md` |8524|`f543cad6fc1832f76be34e795117cb608c994a0c9b5ce219816d996a5017612c`|
| `2026-10-06_08_14_15-gpx-segment-partition.json` |51370|`e59730185e6cf3a6cf3373929207b5ca65bb735d26e5586d797fd3c2bbfcc22e`|

The JSON preserves the owner's reported methodology: tracking generally
represents Habu search, and personal captures, including zero-capture nights,
are reported as completely logged. It explicitly identifies this testimonial
as **not a source-bound audit receipt**. The partition remains provisional:
certified Negative0, confirmed rest0, three unknown-stop-purpose groups,
2124 points without source-recorded speed,177 jump candidates and six gaps.
These candidate classifications do not independently prove actually observed
road/time intervals or justify subtracting all stops as rest.

## PR39: present GPX and positive records

The following original identities were previously verified and remain the
manifest-bound identities at the current head. Direct GPX paths are
`data/raw/gpx/2026-10-06-探索.gpx` and
`data/raw/gpx/2026-10-08-探索.gpx`; the other two are losslessly stored beneath
`data/raw/gpx_archives/2026-10-14-探索.gpx.lines/` and
`data/raw/gpx_archives/2026-10-15-探索.gpx.lines/`.

| Night | Raw bytes | Points | Raw SHA256 |
| --- | ---: | ---: | --- |
|2026-10-06|2243186|8528|`f3f630b137b8a95e7d96b6250ca99657544ffb66fea6730b0e8fe238b4dd93dc`|
|2026-10-08|2421923|9143|`c6c20c07d4d2b2405517a1f9874f40a2bc8e177b9a43e8a6ecaa756231bd28c5`|
|2026-10-14|5359817|20481|`b783411c76288414e30155ec41d6d3de4cf98cb004878303f0a4386efddce943`|
|2026-10-15|4916290|18610|`4bc0d0e8cfca7b1cd12e29c2d242e9ef25f1716b719e68ff2680c23cf1b6d868`|

The current Git-byte capture CSVs retain three count1 owner-capture records per
night, separate from the October8 roadkill:

| File | Bytes | SHA256 |
| --- | ---: | --- |
|`data/processed/capture_events/2026/2026-10-14.csv`|678|`07eaa92a0e739592cb3f37d65aef78eeb257f959b1b369bc027209aa80ff30da`|
|`data/processed/capture_events/2026/2026-10-15.csv`|682|`81c76d95fedc5db460eb7690f68466d16a47449434b0463fbe085a544a3c756f`|

These six positive source records are useful review candidates, already covered
by the existing PR43/main cross-source reconciliation. They overlap six of that
recovered candidate set; they are **not six additional captures to append**.
Main's separate September28 five events/six capture occurrences also overlap
that broader source set. Preserve identities and crosswalks rather than adding
the views together.

The remaining positive-review work is the source/transcription selector,
quantity/species/owner and coordinate-derivation crosswalk, canonical individual
links and duplicate resolution, followed by a current source-bound runtime
review. PR39 itself adds no canonical individual table or raw-chat/TXT original.
Existing GPX proximity checks support time/location coherence but do not replace
those provenance checks. The independent active-search/complete-outcome
requirements for Negative labels must **not** be mechanically imposed on a
genuine positive capture merely because it is not yet training-ready.

For the zero-capture and full-search-denominator claims, the four session CSVs
under `data/processed/exploration_sessions/2026/` report0/0/3/3 captures. Their
counts and owner-methodology summary do not supply independently corroborated,
source-bound road/time SEARCH intervals and matching complete owner-outcome
recording evidence. No complete domain/night denominator is established.

## PR50: original GPX, two transcribed positives and generated report ZIP

The original GPX exists as a complete text-safe archive under
`data/raw/attachment_archives/gpx/7ee4f005cc27fb3d680bd05b7de19d5e9d33241b906c545bbb356c885a2849aa/`:
4675850 raw bytes,17731 points, raw SHA256
`7ee4f005cc27fb3d680bd05b7de19d5e9d33241b906c545bbb356c885a2849aa`.
Main already records PR50's archive integrity and its bounded directory-lookup
repair in `docs/work/CODEX_STATE_20261025.json`; the repair did not admit
scientific data.

The report archive is
`data/raw/attachment_archives/pdca_artifact/3cb92409ee699bdfc6923f680398cc7297688b3ac9/`.
Its raw ZIP is20796 bytes, SHA256
`3cb92409ee699bdfc6923f680398cc7297688b3ac9f298a1c613e42693d2bfa1`.
The exact current archive was decoded in memory and passed its compressed/raw
size and SHA checks and ZIP CRC. It contains13 generated report/CSV/reproduction
members, not a raw conversation original. Its manifest identifies the source
as assistant-generated PDCA evidence and has `source_ref: null`.

| Actual ZIP member / standalone Git file | Bytes | SHA256 |
| --- | ---: | --- |
|ZIP member `capture_events_2026-10-22.csv`|678|`1c466c0a4f41f26aa430e0310e866f82631ddf8bb6ce4df1270d8fae8eed1b72`|
|ZIP member `events_2026-10-22.csv`|5380|`e792118d953d96a170fb028c592b5406d61905933a26cce68f725a6ede848d1d`|
|`reports/pdca/2026-10-22/retrospective/evidence_manifest.json`|2094|`508bf54225215ce8436827c04f87cbfa142322df265c394c29ef178b614d6e83`|

Both count1 capture rows explicitly say they are user-chat hand-transcriptions,
not byte-exact originals. The standalone evidence manifest likewise states that
the source log is a user message rather than a byte-exact file. Thus two positive
statements and real GPX are present; independent reproduction of the original
owner wording is not supplied by this PR. Preserve/reconcile them as reported
positive candidates without calling the captures nonexistent or promoting
their labels automatically. A canonical individual/duplicate/source-selector
crosswalk and current source review remain separate qualification work.

The report's1113 GPX passage/no-capture-record units are explicitly provisional.
They prove neither independent active Habu search for every road/time footprint
nor source-bound complete capture outcomes. The total of two reported captures
does not itself establish full-scope completeness. Missing frozen P0/target
lineage separately prevents retrospective forecast-scoring authority.

## Existing reader capability and unchanged budgets

`src/evidence_audit.py` already supports PR39's direct GPX and line-GPX archive
formats in `_trajectories`, and its capture parser can read those CSV columns
diagnostically after ordinary reviewed integration. This is a format capability,
not permission to merge or to assign outcome roles. Current main's observation
policy has only the limited September28 source registration and empty sessions
and outcome-coverage lists; its fixed positive verifier does not authenticate
these October records by filename or matching flags.

PR50's XZ/Base64 `attachment_archives` format is **not** consumed by that
trajectory reader. `Audit.read` does not accept the `reports` namespace, and
capture CSVs inside the generated ZIP are not automatically discovered as
canonical capture sources. A bounded archive reader/derived-source crosswalk
would be an implementation task, using the existing shared reader, deadline,
actual-byte/point accounting and final rechecks. Merely adding that reader would
not authenticate the hand-transcribed owner statements or complete a denominator.

Current caps remain100MiB per read,512MiB total actual reads,4000 reads,
1000000 GPX points and300 seconds. The four PR39 GPX files total14941216 raw
bytes; together with PR50 they total19617066 raw bytes and74493 points. These
payload sizes do not justify increasing caps. **No full integrated parent audit
was run or claimed**: aggregate rereads, runtime, snapshots and all existing
sources must still pass the unchanged caps in any later integration.

## Disposition

The new PR39 material adds provisional derived diagnostics, not newly qualified
primary evidence. PR50 contains real original GPX and already-reported positive
transcriptions, with an additional reader-capability gap. No newly discovered
source in this bounded check establishes independent active search plus complete
owner outcomes. The owner's direction to use existing GitHub material is not a
new outcome-completeness attestation. Further broad source hunting or an upload
request is not part of this completed audit. Current presence or review does
not backdate historical source availability or establish ex-ante feature access.

September28 remains five source-qualified events/six capture occurrences; it
does not supply a complete denominator, eligible TRAIN rows or an untouched
confirmation cohort. No real fit, source-authentication upgrade, formal KPI,
selection, promotion, execution or production authority is granted here.
