# August 31 positive source-occurrence profile v1

Status: DESIGN ONLY, awaiting coordinator review before runtime/data/policy edits.
Design base: actual main `45c183bba7710d0b568220630b63a70c3a7cac83`.
Branch: `codex/aug31-positive-source-occurrence-20261026`.

## Purpose and exact boundary

Reproduce exactly two preserved owner-log capture statements on the August 31
07:00-JST operational night, using exact native text bytes and original GPX.
Allow a later, independently reviewed positive-only source registration through
an executed fixed profile. An occurrence means one recorded capture occurrence;
it is not a permanent animal identifier or proof that these are two biologically
distinct animals. Preserve the owner's August 47 and dated cumulative 243.

This is the same level of limited source-consistency qualification used for the
September 28 five events/six occurrences. Neither profile authenticates a field
device or establishes permanent biological identity. Do not add those as special
August prerequisites, or require SEARCH/complete noncapture outcomes to recognize
a positive capture statement. Conversely, do not mistake source consistency for
a complete denominator, measured effort, TRAIN eligibility or generalization.

No other August record, especially the August 19 close pair, is admitted. No
Negative, searched-road interval, complete night/domain, prereveal forecast,
confirmation, fit, official score, promotion or production permission follows.

## Observed audit facts and byte proofs

The read-only audit independently read native Git blobs at the design base.
Controlled temporary copies were used for the existing audit/parser, without
normalizing, overwriting or promoting any original. No new IDs or labels were
assigned during the audit/design.

| Existing source | Native bytes | SHA256 |
| --- | ---: | --- |
| `evidence/recovered_sources/2026-08-habu-log-10506-lines-library-read.txt` | 116496 | `130dedae6e04501f4be41fff4ff549a9cfc1a1840dcbb0126359b04465ab7e8c` |
| `evidence/recovered_sources/2026-08-native-original-library-byte-proof.json` | 1408 | `a62dd9d612766f6626e2561a0705dbb14cfd1d862e4afc84efec40da34494745` |
| `data/raw/gpx/2026-08-31__legacy.gpx` | 4753470 | `870047567bb0d9bafca0789f768fda3b7b90eb5788f259d043cdb885ce219bd1` |
| `data/reconstructions/habu_captures/2026-08-count-correction-owner-confirmed-47.json` | 2551 | `4fe0fcd7c7e4f67f51d86fc6962d5c2b5ae78d9c04b86412356937f773158c92` |
| `dashboard/baseline_2026.json` | 38548 | `29b25fa73bbe8f291caa314bd66239023c4292802aa70eb508f310775603e110` |

The full native text has 10506 UTF-8 lines. Calling the existing
`audit_august_native_capture_original.audit_original` on its native temporary
snapshot reproduced 46 capture statements/47 statement quantity/17 nights,
matching the stored day totals and owner-confirmed month. All 46 source
coordinate pairs and existing review block hashes are distinct. This is not proof
of 47 distinct animals or exhaustive capture reporting.

Both selected blocks say `捕獲` and `ハブ捕獲100~120オス`. Exact selectors below
use one-based inclusive native line spans and zero-based half-open byte ranges.
The slice includes the listed original line-ending bytes, with no rstrip, strip,
newline replacement, BOM removal or synthetic final newline:

| Selector | First occurrence | Second occurrence |
| --- | --- | --- |
| Native clock | `2026/08/31 21:43` | `2026/09/01 1:17` |
| Interpreted JST | `2026-08-31T21:43:00+09:00` | `2026-09-01T01:17:00+09:00` |
| Native lines | 10110–10119 | 10492–10500 |
| Native byte range | [112368,112489) | [116249,116392) |
| Slice bytes | 121 | 143 |
| Slice SHA256 | `0e3ef4d50ff5cf9c98b3e0012d9fc75e7a24d6667e0f6b5f259ed5a86e7b4581` | `6bd4b0ed2c572d9b0bd39f8137456e53c7721028f7f88e6e03e4a822c88bceea` |
| Original latitude/longitude lines | 10117 / 10118 | 10499 / 10500 |

The existing `index_events` review block hash uses rstrip plus a newline; it must
not be relabeled as an exact native byte-slice hash. Whole-file SHA, byte offsets,
line spans and the exact slice hashes above are the runtime source binding.

The two source coordinates are 8379.2m apart. The original GPX has 17906 parsed
points, zero excluded points and one segment break from an unrelated 50.826-second
gap. Unchanged `gpx_audit` matching/QC gave selected residuals 0.849m/26.001s and
0.002m/9.999s, HDOP 4.687/3.0, no selected excluded point or segment break, and
one-second neighboring intervals. Do not interpolate the gap or call the whole
track complete search coverage.

Main has no August canonical event/individual CSV. The implementation gap is a
reviewed derived crosswalk and runtime profile, not absent primary text/GPX.
Existing recovered workbook rows for 11 other August statements are one-to-one
aliases of native records (all retain stored `target_role=反応`); their worksheet
IDs are not additional captures or physical-identity proof. They are outside this
two-record profile. The unresolved August 19 source lines 5249/5259 are five
minutes/90.1m apart, despite good GPX matches; GPS does not resolve their possible
overlap. No disposition of that pair or revision of owner 47 is proposed here.

## Proposed implementation ownership and dependencies

This design commit owns only this spec. If approved, the bounded implementation
would own exactly:

- New `src/aug31_positive_source_review.py` and
  `tests/test_aug31_positive_source_review.py`.
- The narrow fixed-profile dispatch in `src/evidence_audit.py`, with focused
  regressions in the new test. No other capture/scoring algorithm changes.
- New derived `data/processed/capture_events/2026/2026-08-31.csv` and
  `data/processed/individuals/2026/2026-08-31.csv`.
- New `evidence/source_reviews/2026-08-31-positive-source-review.json` and
  `docs/reviews/august31_positive_source_review_20261026.md`.
- Only after independent exact-source/actual-record PASS: one additive entry for
  the fixed new CSV in `policies/observation_evidence.json`. Existing Sept28 entry,
  empty sessions and empty outcome_coverage remain exact.

No Raw, original GPX/text/proof receipt, dashboard, owner-count correction,
Sept28 source/verifier/review, legacy report or M0–M3 artifact is owned. No new
original copy, incoming capsule, synthetic raw log or invented old receipt is
needed. Existing sources and proposed derived artifacts already fall under
master inventory `data`/`evidence`; no namespace/registry expansion is proposed.

Before final implementation verification, coordinator normally merges the
reviewed read-guard PR118/current main. The profile additionally uses guarded
`checked_ref -> a.ref` for every reference, as Sept28 does. Shared helper ordering
and unrelated legacy scanner limits remain those of the reviewed main; this
profile does not claim to repair their known metadata/enumeration boundaries.

## Fixed profile and derived projection contract

Profile ID: `aug31-owner-capture-occurrence-crosswalk-v1`.
Fixed outcome CSV: `data/processed/capture_events/2026/2026-08-31.csv`.
Public helper mirrors the existing integration seam:

```python
reproduce_sources(refs, *, read_ref, tick, consume_point)
verify_review(review, *, read_ref, tick, consume_point, now)
```

Neither function opens paths, creates an Audit, writes data or grants authority
by itself. The caller supplies the actual shared `Audit.ref`, `Audit.tick` and
point-accounting callback through guarded bridges. Reuse existing strict review
JSON parsing and numeric GPX matching/QC; do not modify Sept28's pinned parser or
introduce another numerical matching algorithm. The new bounded bytes-to-XML
adapter may parse an owned BytesIO payload, never call path-based parse_gpx or
read a file outside the supplied reader.

The event CSV uses Sept28's existing column schema. Proposed event keys
`AUG31SRC-L10110` and `AUG31SRC-L10492` are explicitly **new derived source-record
keys**, bound to this profile/full-source SHA/line selectors; they are not IDs
found in the original. Each legacy individual-table row has the corresponding
`-OCC01` key and `individual_index=1`. These are occurrence-link keys, not newly
discovered physical animals. The verifier requires exactly two event rows and
two occurrence links, one-to-one, with no copied/extra/orphan/duplicate IDs.

`event_count=1` means the singular capture statement as one recorded occurrence,
consistent with Sept28's singular-statement interpretation. The size range
`100~120` is not quantity or an exact measured length. Keep size_note/sex/behavior/
microhabitat/surface as exact source text; copy event_place only if explicitly
present, otherwise empty. No reverse geocoding. Coordinates are exact original
decimal strings, compared with Decimal rather than float rounding. JST is the
documented interpretation of this Japanese field log, not a claimed timezone
offset physically present in the original text.

Review metadata must bind schema `1.0`, fixed profile/path/CSV SHA, the exact
source_refs, actual reviewed_at, `RESEARCH_EXPOSED`, current-source-consistency
scope, and use_roles diagnostic_only or outcome_label. Require
independent_device_authentication and permanent_biological_identity both
NOT_ESTABLISHED. Fix all negative/search/completeness/training/confirmation/
official/promotion/production authority fields false. Stored counts/Library proof
are corroborating provenance, not independent per-animal authentication or
evidence of historical input availability.

`source_refs` is an exact closed mapping: native_log, native_byte_proof, gpx,
owner_count_record, captures, individuals. Every ref is exactly
{path,sha256,size_bytes}, with positive nonboolean bounded integer size. The first
four runtime source paths/sizes/hashes are pinned above. The dashboard identity
is read-only audit context, not a runtime prerequisite that freezes future
legitimate dashboard updates. New CSV/individual hashes and exact bytes
are generated deterministically and reviewed before registration, then fixed in
the profile/review. No arbitrary path, alternate source, role flag or new raw
statement can satisfy the profile.

Proof contains exactly the executed event_count=2, individual_occurrence_count=2,
permanent_biological_identity_verified=false, two ordered crosswalk rows, GPX QC
and false authority fields. Each row records event/occurrence key, CSV row/link
row, exact native source/line/byte/slice selectors, time/count basis, coordinate
line selectors and binding, actual GPX sequence/index/time/residuals/HDOP and
neighbor gaps. Compare canonical typed proof digests as well as recomputed proof
SHA; Python bool/int equality alone is insufficient.

## Admission, resources and publication

Extend only the fixed-profile branch of `_declarations`: recognize the new
profile at the new fixed path, retain the original Sept28 branch/size/proof logic,
and reject unknown profiles or profile/path substitution. Both new CSV and review
are guarded before first read, including missing-profile attempts. Strictly parse
the review; missing/legacy/unknown profile cannot grant outcome_label to the new
fixed CSV. Diagnostics without a qualifying role do not become positives.

Every qualifying audit must actually execute the verifier before source.update;
neither a committed PASS field nor a standalone test is sufficient. Validate
whole native SHA/size and exact slices before parsing their capture meaning.
Reject owner/species/type/time/night/coordinate/count/attribute mismatch, wrong
line/offset/hash, extra rows, repeated selectors, aliases or unrelated records.
For these fixed two statements require no other-person/roadkill/sighting marker.
Require their GPX point matches under the existing 100m/600s matcher, selected
point not excluded or a segment break, HDOP <=10 and positive neighboring gaps
<=30s. Preserve the actual unrelated GPX gap/QC instead of fabricating continuity.

Use one caller deadline/read/point ledger; charge every actual reference reread
and all 17906 parsed points. Check before/after owned parsing, hashing, matching
and sealing, and between points. No budget extension, new clock or alternate
reader. Fixed raw GPX is under 5MiB, native text under 128KiB, small context/CSV
refs under their fixed sizes and review at most 128KiB. Read with expected bound
plus one through existing a.ref, reject actual size/hash mismatch, and keep
100MiB/source, 512MiB total/4000 reads/1M points unchanged. No RSS or hard native
preemption promise. Recheck all profile refs and review after proof; retain the
whole-audit consumed-source final rereads/final seal checks. Late mutation or
expiry cannot retain qualified units/events; runtime failure remains BLOCKED.

Availability is the actual current reviewed/audited time under existing
max(source/review/now) rules. Do not infer a 2026 August received/usable time from
field clocks, filenames, Git dates, monthly totals, Library proof dates or a new
role flag. Preserve an existing missing-receipt requirement rather than invent
an old receipt. Registration waits for independently reviewed implementation and
actual records, uses the actual registration timestamp, and never backdates it.

## Acceptance before a later registration

- Actual native Git snapshot reproduces all pinned bytes, slice boundaries,
  original fields and selected GPX QC, with no runtime Git/network dependency in
  hermetic CI. Raw source fixtures must use native Git blob bytes on Windows;
  incompatible working checkout bytes must fail rather than be normalized.
- TDD missing API/gate first; reject missing/unknown/downgraded profiles, sole
  source or review substitution and truthful-authority field inflation.
- Mutate every input independently, including unchanged/rehashed proof with bool/
  int substitution; reject duplicate JSON/nonfinite values, duplicate/orphan keys,
  repeated/overlapping source slices, extra third row, wrong index/count/night,
  swapped original coordinates and a forbidden Aug19 source selector. Never
  resolve the Aug19 identity question merely from proximity or source block SHA.
- Actual Windows junction/POSIX symlink, growth, shared caps/deadline/point limits,
  caller-check identity, late ref/review mutation and final-seal expiry fail at
  the existing guarded/failure boundaries without retained qualified units.
- Preserve checksum-pinned **whole Sept28 behavior** under the same actual input
  snapshot/runtime: complete canonical typed outputs, hashes, read bytes/counts/
  order and existing source/role/proof results. Use the identical old input
  snapshot without the new August data/policy; changed combined inputs naturally
  have a different full audit identity. Reuse the existing checksum-pinned
  original-auditor capsule for the old/current comparison and collect the actual
  Sept28 whole receipt before implementation; do not regenerate expectations
  from new code or alter the old verifier. No exclusions apply. The only new
  behavior is this explicit second fixed positive-source profile when supplied.
- Native source-only parent audit with the provisional derived data must produce
  exactly two newly source-qualified occurrences/at most their actual positive
  units, zero new Negatives, denominator NOT_ESTABLISHED and scientific
  NOT_VALIDATED, without altering owner 47/243. Measure unchanged full aggregate
  caps on the actual combined input snapshot; per-cohort size is not that proof.
- Independent exact-source review and actual Ubuntu CI precede the sole additive
  policy entry. After registration repeat actual-source audit and verify all old
  source/Raw/ORIGINAL/owner totals remain byte-identical. Actual qualified TRAIN,
  fit and confirmation still require their separate existing gates.

No runtime, derived data, source registration or labels are implemented by this
design commit. Coordinator retains STATE/cycle/freeze/PR/integration ownership.
