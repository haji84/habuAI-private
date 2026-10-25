# Closed August positive source-occurrence family v1 — design only

This branch starts at **candidate**, not main,
`f9cf42a261db052601b31bd92d0513b656232920` on
`codex/aug31-positive-source-occurrence-20261026`. This document authorizes no
implementation, runtime descriptor creation, source qualification or registration.
The coordinator must review this design and integrate actual PR121 software and
PR122 Aug31 registration into main before dispatching runtime work. This branch
owns only this new specification; source/tests/descriptors/policy/STATE remain untouched.

The first implementation/data-acceptance target is **only the Aug29 statement
starting at native line 9654**, one recorded occurrence. The other 27 frontier
records are not approved by this design. A frontier entry, its SHA, a review flag
or a passing JSON reader is not scientific authentication or data approval.

## Observed source frontier and limits

Read-only frontier evidence is the external private file
`august-remaining-source-feasibility-20261026.json`, 90229 bytes, SHA256
`8a00593c27e57f5fdf954a29b18ac38f7558e392ad1d2f0dc570d91feca7d8c6`.
Its native input base was actual main
`699f0bda36b32caa2225d2d42962d590d561040b`. It is investigation evidence to
reproduce, not a runtime reference outside the input snapshot or an approval list.

The preserved UTF-8 source is
`evidence/recovered_sources/2026-08-habu-log-10506-lines-library-read.txt`,
116496 bytes/10506 lines, SHA
`130dedae6e04501f4be41fff4ff549a9cfc1a1840dcbb0126359b04465ab7e8c`.
There are 46 capture statements/47 statement quantity/17 nights, not 47 proved
distinct animals. Owner August 47 and dated October-20 cumulative 243, original
receipts and historical false fields remain unchanged.

| Frontier class | Statements / quantity | Treatment |
| --- | --- | --- |
| Source/GPX-consistent remaining frontier | 28 / 28, ten nights | Candidates only; first admission target is Aug29 alone |
| Early Aug1/2/3/5/9/11 | 14 / 14 | Text/original coordinates exist; corresponding original GPX absent from the verified main catalog/inventory, so requested point proof remains missing |
| Aug19 lines 5249/5259 | 2 / 3 | Defer possible occurrence overlap, 300 seconds/90.099m; do not resolve identity from GPS |
| Current Aug31 lines 10110/10492 | 2 / 2 | Existing separately reviewed profile; excluded from remaining-family selection |

Eleven of the 28 candidates have existing workbook aliases with stored
`target_role=反応`: Aug12 lines 2631/2770/2994/3030, Aug13 3176/3470,
Aug15 3833/4156/4186 and Aug17 4279/4609. Their primary-versus-derived role
crosswalk needs explicit independent review; they are excluded from the initial
new data admission. Do not rewrite the old rows or count aliases as captures.
Sightings, other-person reports, Hime Habu, roadkill and other event types stay
outside this positive-only slice. No claim that all possible duplicates have
been disproved follows from the existing proximity triage.

The private investigation parsed 199896 points with the unchanged `gpx_audit`
code, 28.563s, 279772992 native-Git bytes plus 52872810 actual XML-read bytes.
This is a separate analysis measurement, not proof that a future combined runtime
audit fits its caps. Incoming files and restored manifests with identical raw
SHA are transport aliases, not additional capture or independent witness evidence.

## Smallest first record

Aug29 native lines **9654–9663**, exact bytes **[107486,107604)**, 118 bytes,
SHA `5ccb0b1454360fe58a638f3eea54b86922aab3d7ffe78d87bd19d164b09b33d4`.
Native clock `2026/08/29 23:58`, interpreted JST
`2026-08-29T23:58:00+09:00`; coordinate lines 9661/9662 contain original decimal
strings. The statement says `捕獲`, `ハブ捕獲130~150メス`, `とぐろ`, `道路脇`,
`ドライ`, with empty place. Size 130~150 is not quantity or authenticated measured
length. Count one means **one recorded singular capture occurrence**, not a
permanent individual ID or independently established exact biological total.

Original GPX `data/raw/gpx/2026-08-29__legacy.gpx`: 3576827 bytes, SHA
`23686f0561ffc72e7310943f98f2953afdfa1908b683fdd101e9f7cfa28b6efe`,
13565 points. Selected actual point index 3222/sequence 28616 is .573297m/
47.999s away, HDOP 4.687, neighboring gaps 1s/1s, neither excluded nor a break.
Retain the unrelated 148.999s whole-track gap/one break. No interpolation.
Day count one is investigation context; do not silently add `dashboard/` to the
runtime input namespace. Existing source-bound owner month context remains 47;
this v1 count is the expressly limited statement-occurrence interpretation.

## Reuse boundary: one family, no per-night algorithms

Current Aug31 code fixes two rows, one 17906-point GPX, its note/size/sex, source
paths and CSV hashes. Do not clone a new verifier per night, mutate module
globals or reinterpret the old profile. Extract only a private closed crosswalk
core accepting an explicit descriptor; retain Aug31's public functions as fixed
facades over their existing descriptor. The default facade must perform no new
family descriptor reads, change no proof fields, self hashes, source reads or
point charges.

The shared core handles bounded exact reads, native selectors/decimal coordinates,
typed CSV occurrence joins, actual GPX parsing, unchanged `mark_point_anomalies`
and `match_capture_to_points`, typed proof comparison and final reference rereads.
It must not add a numerical matcher, source-role flag shortcut, arbitrary source
loader, model/controller/permission framework or global mutable registry.

Proposed new family ID: `august-owner-capture-source-occurrence-v1`. The 28-record
candidate frontier remains private investigation context, not a runtime catalog,
required read, admission set or additional pin layer. The first implementation
does not commit or revalidate all 28 candidates to admit the one Aug29 record.

Initial admission is closed by one **immutable code-pinned admission descriptor**
whose selected primary slice is exactly Aug29 line 9654. This is a software input
bound, not scientific approval. Other source selections must fail known-scope
validation in v1 rather than silently obtain roles. Later expansion requires an
explicit coordinator-reviewed descriptor/pin change and independent source/data
gates, not another family/profile implementation or an `approved=true` edit.
Admission pins form an immutable, bounded family-specific set. A later approved
descriptor is appended, never substituted so that an earlier registered review
loses its pinned definition. Previously accepted descriptor bytes and
proof meanings remain valid; simultaneously declared subsets must be disjoint.

## Proposed exact data shapes and API

These are design names, not files or interfaces created by this commit.

Admission descriptor exact fields:

```text
schema_version = habu-august-source-occurrence-descriptor-v1
family_id
primary_ref                 {path, size_bytes, sha256}
native_byte_proof_ref       {path, size_bytes, sha256}
owner_context_ref           {path, size_bytes, sha256}
gpx_ref                     {path, size_bytes, sha256, point_count}
records                     ordered array, initially the sole Aug29 record
captures_ref                {path, size_bytes, sha256}
occurrences_ref             {path, size_bytes, sha256}
expected_counts             exact event and source-occurrence counts, initially 1/1
expected_gpx_qc             exact whole-track and selected-point QC expectations
```

Each record has exact native line/byte/slice selectors, interpreted JST/night,
coordinate line selectors, exact expected source note/place/surface/behavior/
microhabitat and literal size/sex projection, singular-occurrence count basis,
bound GPX reference and legacy alias references/disposition. No source coordinate
or quantity may be supplied as an unconstrained replacement. Values are checked
against pinned native bytes; recorded occurrence count is strict integer one,
never bool/float. Primary identity includes its SHA, byte start/end and native
slice SHA. The descriptor binds all three primary refs, the one original GPX,
exact selectors/expected attributes, both derived CSV refs/counts and unchanged
QC; it accepts no unrestricted path, selector or quantity. For the initial Aug29
row legacy alias references are empty; other rows remain non-admitted.

The initial descriptor's full physical-byte SHA/size and canonical paths are
code-pinned. Its record array contains only the one Aug29 slice. Private frontier
membership cannot satisfy admission. Unknown fields/versions, unsupported
selectors or a rehashed altered descriptor reject before any qualification.

New batch paths use one protected family prefix, for example:
`data/processed/capture_events/source_reviews/august-2026/<batch>.csv`, the
corresponding `data/processed/individuals/source_reviews/august-2026/<batch>.csv`
and `evidence/source_reviews/august-2026/<batch>.json`. Batch names are bounded
canonical ASCII identifiers. Paths remain inside existing data/evidence snapshot
namespaces; no dashboard/incoming/reports expansion is proposed. Each batch and
review is immutable; adding another batch cannot rewrite an older review.

Proposed public family functions:

```python
reproduce_sources(descriptor_ref, *, read_ref, tick, consume_point)
verify_review(review, *, read_ref, tick, consume_point, now)
```

Resolve only the code-pinned admitted descriptor, then run the shared private
core. All actual I/O goes through guarded caller readers. The exact family review
metadata extends the current source-consistency metadata with `descriptor_ref`;
it binds the captures SHA, actual reviewed_at, RESEARCH_EXPOSED, selected-only
scope, all false authority fields, NOT_ESTABLISHED device/biological identity,
computed typed proof and proof SHA. It cannot be accepted merely for its metadata.
Public family proof records the actually selected event/occurrence count,
crosswalks and per-night unchanged GPX QC. Aug31 v1 proof shape stays exact.

## Protected admission and duplicate boundary

The narrow `_declarations` seam must recognize this family prefix **before** a
generic legacy-role branch, including omitted/unknown profiles and ASCII-case,
backslash/dot aliases. Only canonical spelling is accepted. The new profile
outside the family paths, or family data without the proper profile/descriptor,
fails closed. Old Sept28 and Aug31 policy behavior is otherwise unchanged.

Preflight all new-family declarations before role updates. Strictly parse the
family's policy/review/descriptor JSON, reject duplicate keys and typed
numeric substitutions, and guard every initial reference. If new-family entries
are present, any needed strict policy reparse occurs before those updates and
under the same ledger; old inputs with no family entries retain old reads.

Primary occurrence identity is **(native primary SHA, exact byte slice)**,
independent of CSV name, batch, row ID, GPX filename, normalized-block SHA or
transport manifest. Reject duplicate keys across batches/aliases and overlapping
selectors of the same original. Preflight the complete code-pinned admitted
descriptor set and new-family policy declarations globally, then stage
updates until verification/disjointness pass: a valid entry followed by a bad or
duplicate one cannot leave a new role qualified, in either order. Known Aug31
slices and Aug19 deferred slices cannot be selected via renamed files. New row
keys are stable source-occurrence references, never permanent animal identities.

## Budgets, preservation and acceptance

One existing Audit deadline/read/point ledger covers descriptor reads,
CSV/GPX bytes, hashing, all point charges, proof/review checks, final rescans and
result seal. No reset, private reader or fallback. Pre-copy bound the descriptor
to 128KiB, depth64/nodes16000; initial admission is one record/one occurrence
link/one pinned GPX, with no implied capacity or admission for the other 27.
Use fixed source sizes, bounded read+1 and actual byte charges. Preserve 300s,
512MiB, 4000 reads and one-million-point caps. Never force all28 into one audit,
raise caps or return partially qualified data on budget failure. Native XML/QC
calls remain cooperative/non-hard-preemptive; static path guards do not promise
general hostile concurrent-filesystem confinement.

**Before any extraction/runtime edit**, after actual PR121/122 main integration:

1. Capture the existing Aug31 public proof/typed review verification and complete
   public audit under that fixed main, with its real registered review/policy.
   Preserve immutable old program bytes, full result/self+physical hashes,
   consumed hashes, actual read/point counts and exact read/open order.
2. Materialize the complete native Git tree with NUL-safe inventory. Verify every
   blob/path/size/hash before/after; execute that snapshot's own code. Preserve the
   historical Sept28 e1e16 artifact unchanged and document its old362 catalog;
   the independently corrected old native input inventory is387 including25
   Japanese-path files. Do not regenerate any old golden from refactored code.
3. After implementation compare whole Aug31/Sept28 objects and their typed proof,
   self receipt, reads/points/order exactly on the same old inputs/runtime. A new
   family descriptor must not become an extra legacy input or read.

Future TDD must first fail for missing API/dispatch, Aug29 mismatch and cross-batch
duplicate cases. Cover stale/rehashed wrong refs and proof, bool/int/float types,
extra/orphan rows, wrong size/sex/quantity/time/night, source selectors outside
the admitted descriptor, GPX aliases/points/entities/HDOP/gaps, JSON duplicates,
first-valid/later-bad permutations and real Windows junction/POSIX links before
opens/scans. Callback exception identity and cap/deadline classification survive.
Late source/review/descriptor change and final-seal expiry leave no public qualified
events/units. The 27 other frontier selections cannot be silently admitted.

First software verification uses only private provisional Aug29 review/policy
fixtures and an actual full-native combined source-only audit under unchanged
caps. Record actual measured counts, code/commit/tree, full inventories and exact
known provisional changes; do not infer capacity from the investigation. This is
not parent PDCA, G0 execution, a fit or a scientific validation.

Independent exact-source review and genuine Ubuntu exact/fresh-main gates precede
a separately dispatched registration stage. It creates a new review at actual
current time and the sole selected-source policy entry, without overwriting old
reviews or backdating availability. No Negative/search/complete outcome scope,
prereveal status, TRAIN/fit, confirmation, selection, model registration,
promotion, production or additional user/security authority is granted here.

## Future ownership boundary, not implementation authorization

After design acceptance the coordinator may separately allocate one new pure
closed core/family adapter and tests, a narrow Aug31 fixed-facade delegation and
family-only `_declarations` seam, the Aug29 admission descriptor and author
record. Existing Sept28 source/tests/goldens, Raw/original GPX/text/receipts,
owner47/243, historical model definitions, master/parent dispatch, STATE/cycles,
requirements/workflows and permissions are not implementation targets. Exact
paths and runtime authorization must be dispatched later; this commit changes
only this design file and waits for coordinator review.
