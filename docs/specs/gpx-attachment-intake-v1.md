# GPX attachment archive intake v1

Status: design for a bounded reader addition; implementation requires coordinator
approval. Base: `9c06f3d8b059439991f444dee8c7b30f35b2b6bc`.

## Purpose and ownership

Consume byte-preserved GPX in the existing text-safe XZ/Base64 attachment format
as trajectory diagnostics. Preserve every Raw byte. Do not restore a file, merge
PR50, promote an original, register an observation role, or extract captures from
generated reports. This is reader compatibility, not scientific qualification.

Proposed implementation ownership is new `src/gpx_attachment_archive.py`, new
`tests/test_gpx_attachment_intake.py`, and a narrow hook/finalization addition in
`src/evidence_audit.py`, plus this spec and a separate review document. Leave the
restore CLI, direct/line GPX implementations, policy, parent, source registrations,
Raw, workflows and requirements unchanged. No new dependency is needed.

`scripts/text_safe_byte_archive.restore_file` documents the native transport but
must not be called by the audit: it reads outside Audit accounting, decompresses
in one unbounded operation and writes an output file.

## Existing namespace and shared reader

At the base, `Audit.read` checks `Path(path).parts[0]` against
`{'data','evidence','policies','features','protocols'}`. Therefore the canonical
`data/raw/attachment_archives/gpx/...` paths are already allowed through `data`.
Do not modify `INPUT_PREFIXES` or add an exception. `reports` remains forbidden.
The helper applies a narrower grammar before delegating to this existing reader.

All payload reads, including rereads, use the same actual `Audit.read` callable;
all work uses the same `Audit.tick` callable and deadline. No direct
`Path.read_bytes`, alternate reader, fresh Audit, clock replacement or counter
reset is permitted. Preflight every new path with `master_inventory.local_path`
before its metadata operation or open. This adds portable-component, containment,
symlink, junction and reparse checks only for the new intake paths; it does not
refactor legacy readers. Ordinary caller-check exceptions retain their identity.

## Helper interface and lifetime

The proposed helper module exposes:

```python
discover_gpx_attachment_archives(root, *, check)
# -> (ordered_manifest_paths, membership_snapshot)

read_gpx_attachment_archive(root, manifest_path, *, read, check,
                            remaining_decoded_bytes)
# -> (raw_gpx_bytes, transport_crosswalk)
```

`read` supports the existing `read(path, *, max_bytes=None)` contract. `check` is
the caller's existing check, not a replacement timer. Paths are repository-relative
POSIX strings. The decoded allowance is an exact nonnegative integer supplied by
the hook from its aggregate remaining allowance. Bytes and crosswalk are owned
phase material; the helper does not publish a sealed complete audit. Its caller
must perform the final rereads and membership checks below before returning an
audit. Exposing this helper does not promise that disk bytes cannot change after
it returns. Do not label its return a final source-authentication receipt.

## Bounded discovery and pre-open ordering

Only this exact layout is supported:

```text
data/raw/attachment_archives/gpx/<64 lowercase hexadecimal raw SHA256>/
    manifest.json
    part_000.b64
    ...
```

No recursive discovery, user-supplied glob, alternate root or filename-derived
destination is used. `pdca_artifact`, arbitrary attachment kinds, ZIP members and
`reports` are outside this hook.

1. Validate the fixed anchor spelling, then call `local_path` before checking
   existence/type or enumerating it. A missing anchor yields no archives and no
   new checks, sources, requirements or output fields. An existing anchor must
   be a normal directory.
2. Enumerate only immediate children with `os.scandir`, checking the shared guard
   for each yielded entry and before/after enumeration. Guard each full relative
   path before entry metadata. Every child must be a normal directory named by
   exactly 64 lowercase hexadecimal characters. Do not follow a directory link.
3. Guard each archive directory before enumerating it. Before opening any of its
   payloads, collect a bounded membership list: one `manifest.json` plus regular
   files named `part_<index>.b64`. Reject nested directories, links, portable name
   aliases and other members. Bound entries before appending/sorting; the complete
   new subtree may contain at most 4000 entries per discovery pass. Check every
   entry, rather than sorting an unbounded iterator first.
4. Read the manifest through `read(..., max_bytes=65536)`, then validate all known
   schema/size/selector contradictions. Derive the exact expected filenames
   `f'part_{i:03d}.b64'` from integer indices `0..part_count-1`. Compare the entire
   observed membership to that exact set before opening any part. Lexical sorting
   is not a substitute for numeric indexed ordering.
5. Recheck each member's guarded path immediately before its read. Obtain actual
   SHA/size from the bytes read, without another unaccounted file access. Read
   parts in exact numeric order. The fixed manifest path and expected part paths
   are the only payload paths this helper may pass to `read`.

Discovery returns a deterministic bounded snapshot distinguishing a missing
anchor from an existing one and recording root child names/types and every archive
member name/type. It is caller-private phase state, not an authority declaration.
The same guarded discovery is used to compare membership later; a newly inserted
archive or part is a change even if no previously consumed byte changed.

## Exact native manifest

Require strict UTF-8 JSON with duplicate object keys and nonfinite constants
rejected. Require an object with exactly these **15** fields:

```text
schema_version, original_filename, kind, source, source_ref,
raw_size_bytes, raw_sha256, compression, compressed_size_bytes,
compressed_sha256, transfer_encoding, encoded_chars, part_chars,
part_count, part_glob
```

The fixed values are `habu-text-safe-byte-archive-v1`, `gpx`, `xz`, `base64` and
`part_*.b64` for schema/kind/compression/encoding/glob respectively. Never execute
or interpret the glob. Hashes are exactly 64 lowercase hexadecimal characters;
the parent directory name must equal `raw_sha256`.

Sizes/counts are exact nonboolean positive integers. Raw and compressed bytes are
each at most 100MiB. `part_chars` is a positive multiple of four, at most 1MiB;
`part_count` is at most 4000 and equals `ceil(encoded_chars / part_chars)`.
`encoded_chars` must equal `4 * ceil(compressed_size_bytes / 3)` and is bounded
by that formula applied to the compressed cap before buffers are allocated.
Every part except the last has exactly `part_chars` ASCII bytes; the last has
exactly the positive remainder. No whitespace/newline normalization is performed.

`original_filename` and `source` are nonempty strings, at most 1024 and 4096
characters respectively; `source_ref` is null or a nonempty string of at most
4096 characters. Reject NULs. These fields are preserved as declared descriptive
metadata only. Never use them as paths, timestamps, source authentication,
receipt evidence or independently verified owner wording.

The native format has no `trackpoint_count` or availability fields. Do not insert
an expected point count or derive receipt/first-availability time from a filename,
GPX timestamp, manifest source text, PR date or the intake date.

## Decode and capacity contract

Validate the complete membership, manifest and declared bounds before part I/O.
Use strict Base64 validation; no fallback alphabet, ignored junk or text rewriting.
Decode bounded parts in order (part boundaries are multiples of four), computing
the compressed size and SHA over the exact joined compressed bytes. Verify both
against the manifest before XZ decompression. Do not allocate the complete encoded
text merely to decode it. Enforce exact actual lengths as well as declared lengths.

Use `lzma.LZMADecompressor(format=lzma.FORMAT_XZ, memlimit=128*1024*1024)` with
bounded compressed input/output steps, shared checks between steps and a bounded
`max_length`. Check before/after construction, decode, hashing and joins. Enforce
the lesser of declared raw size, 100MiB and the aggregate remaining decoded
allowance while producing bytes; detect one excess byte before retaining it.
Require EOF, no unused/trailing data, no concatenated stream and exact raw size
and SHA. Never use unbounded `lzma.decompress`, a temporary output, or a subprocess.

The hook separately tracks at most 100MiB of decoded new-archive GPX bytes for
the entire audit; this prevents compressed files from multiplying retained decoded
memory across archives. Charge produced decoded bytes to that allowance, including
work later rejected. It is a derived-data capacity, not fictitious physical reads.
Keep actual read counters exclusively for actual reader calls/bytes. The decoder
memory limit bounds its working state; it is not a claim of a 128MiB process RSS.

Keep existing limits: 100MiB per source read, 512MiB total actual reads, 4000 actual
reads, 1000000 total parsed GPX points and the caller's at-most-300-second audit
budget. Metadata scans, Base64, XZ, hashes and XML work consume the same deadline.
Existing `_gpx` counts each parsed point exactly once against the same `a.points`.
Check before/after its bounded XML parse; this is cooperative checking, not hard
preemption of one native decode/XML operation.

Malformed schema/selector/codec/size/hash/XML is an integrity failure. New helper
format failures use a dedicated `GpxAttachmentError(ValueError)` so the hook can
catch that narrow class rather than swallowing an arbitrary check's ValueError.
Normalize only known local format/path/codec operation errors at their operation
boundary, with shared checks outside those catches. Exhausted
time, read/point/decoded/discovery capacity or decoder working-memory allowance is
a runtime blocker using `AuditBudgetExceeded`; do not report it as missing field
evidence or swallow it in an archive-integrity catch. Catch only known format
errors around the corresponding operation, preserving ordinary check exceptions.
No partial decoded GPX may enter trajectory parsing after a helper failure.

## Trajectory hook, identities and crosswalk

Keep `_trajectories`'s existing direct and line-archive traversal and ordering.
Append new attachment sources after those sources, ordered by manifest path,
through the same raw-SHA `seen` set and the same `_gpx` parser. Its public return
shape remains `(reports, points)`; existing callers and old report shapes remain.

Each returned transport crosswalk has exactly these nine fields:

```text
schema_version, manifest_ref, parts, compressed, reconstructed,
declared_original_filename, declared_source, declared_source_ref, integrity
```

`schema_version` is `habu-gpx-attachment-transport-v1`; `integrity` is
`BYTE_EXACT_VERIFIED`. `manifest_ref` and each numerically ordered `parts` entry
have exactly `{path, sha256, size_bytes}` from actual bytes. `compressed` and
`reconstructed` each have exactly `{sha256, size_bytes}`. These are identities of
consumed material, not authentication of the named source or receipt issuer.

For a new archive, the existing source-manifest entry remains the physical
manifest identity: `path`, `sha256`, `size_bytes` and `source_id` identify its JSON
bytes. Add `reconstructed_sha256`/`reconstructed_size_bytes` and the crosswalk as
`attachment_archive` on that new source entry. Do this explicitly: `_gpx` currently
sets reconstructed metadata only when `expected_count` is nonnull. Pass `None`
for this native format; never fake a manifest count to trigger that branch.

The trajectory report's existing `sha256` identifies decoded GPX bytes. Point
`source`/`source_sha256` continue to identify the physical manifest and preserve
the existing segment/point selector convention. The crosswalk binds that physical
manifest and its actual parts to the reconstructed GPX selected by those indices.
The ordinary parser supplies actual count/QC; do not add invented point selectors.

Register the new physical source after verified transport even when its raw GPX
is a duplicate, so its crosswalk remains inspectable. A duplicate raw SHA emits
the existing duplicate diagnostic and adds no report, points or measured effort.
Different container/manifest hashes do not create different physical trajectories.
Do not replace physical manifest SHA with raw SHA or merge the two identities.

## Finalization and classification

After actual GPX parsing, compare guarded new-subtree membership to the discovery
snapshot. Persist only private finalization state on the audit for another such
comparison at the whole-audit boundary. A helper result is not independently
published between these boundaries.

The existing audit finalization already guards and rereads every `a.consumed`
path with `local_path` and `Audit.read`. All new manifest/part reads must enter that
same map. Reuse these actual final rereads rather than hiding or resetting their
costs; no separate unaccounted reader or assumed size/hash is permitted. Recheck
new-subtree membership after that whole consumed-file pass and immediately before
the final audit digest/check. Thus insert/delete/rename and existing-byte changes
both prevent a successful final result. Static reparse substitution is guarded
again. This remains ordinary non-atomic caller I/O, not a trusted atomic snapshot
or protection against arbitrary concurrent mutation after the final checks.

Initial archive integrity failures record FAIL and supply no rows from that
archive. Late mutation/finalization failure must propagate to the audit's outer
failure path, clearing observation units/eligible outcome success as it already
does; runtime exhaustion yields BLOCKED. Never return a new successful/partial
scientific result sealed over failed final checks.

Without separate valid source qualifications, new sources retain
`use_roles=['diagnostic_only']`, `quality/recovery_class/search_role='UNKNOWN'`,
`historical_available_at=None` and ordinary current-presence availability (or an
independently verified applicable existing receipt). Reading a genuine trajectory
does not supply SEARCH, complete owner outcomes, Negative labels, canonical
individuals, qualified TRAIN or prediction skill. Do not change policy/session/
capture qualification or allow reports/hand-transcribed positives through this
slice. Existing independent positive qualification is neither granted nor denied.

## Acceptance and genuine regression fixture

Require targeted tests before implementation, independent review and exact-head
CI. Required controls:

- No anchor: compare complete canonical typed old/new audit objects, input hashes,
  actual read counts/bytes and read ordering against an immutable original-module
  fixture under identical actual runtime/inputs. No platform goldens or exclusions.
- Valid synthetic transport: exact reconstruction/crosswalk, ordinary timestamp,
  coordinate/segment QC, current availability and UNKNOWN labels; actual point
  accounting and direct/line/new duplicate combinations without double effort.
- Exact schema, boolean/oversize integers, hashes, kind, namespace, path aliases,
  unsafe/nested/extra/missing members and per-part lengths reject at the documented
  pre-open boundary. Prove symlink/junction targets have zero external opens.
- Base64/XZ corruption, hash/size mismatch, trailing/concatenated streams, output
  bomb, decoder memory, aggregate decode, entry/read/point/time caps and checks
  during parsing/final sealing fail with the correct integrity/runtime category.
- Mutate payload or membership after decode, after `_gpx`, during unrelated later
  reads and during final rereads: no successful sealed audit or retained qualified
  observations. Assert the real shared counter charges for every actual read.
- Existing audit/line/archive tests remain unchanged; restore CLI roundtrips stay
  unchanged. No new roles, capture parsing, output writing or source qualification.

CI uses bounded synthetic transport/XML fixtures and an immutable old-reader
capsule; it must not require PR50 Git objects, another local worktree, an unmerged
branch or network access. Main at the base has no attachment-archive subtree.
Do not persistently copy PR50 Raw into tests or the repository in this slice.

Separately run PR50 exact `86127f79163fd004cf65b5b6fc8ab2ad5f154ac8` as a genuine
manual regression, materializing its seven verified immutable transport files
byte-for-byte into an isolated temporary input outside Git, without checkout,
promotion or Raw edits. Record the actual parser points and complete actual read
ledger/budgets as a separate review receipt; this is not an always-available CI
fixture. The archive directory
is `data/raw/attachment_archives/gpx/7ee4f005cc27fb3d680bd05b7de19d5e9d33241b906c545bbb356c885a2849aa/`.
Its actual manifest is 601 bytes, SHA256
`5c5032c570f35880d5ab04ec10be27c90d8a19167264f222d57ecd5312ebb344`.
Six parts contain 523664 ASCII bytes; compressed XZ is 392748 bytes, SHA256
`23db6564258f4c09d99e974df03cfd0c849c65fe46e6f574cbccd98a8013c592`.
Decoded GPX is **4675850 bytes**, SHA256
`7ee4f005cc27fb3d680bd05b7de19d5e9d33241b906c545bbb356c885a2849aa`,
with **17731 actual trackpoints**. These numbers are fixture assertions, not new
manifest fields or a search/outcome claim. Manifest plus parts total 524265 bytes
per complete physical pass; additional actual reads are separately charged.

No full integrated parent run has been performed or promised by this design.
Any later actual source integration must independently pass unchanged aggregate
reads, snapshots, runtime and qualification gates. Existing PR39/PR50 presence,
manual capture transcripts, derived no-capture units and GPX passage do not make
a complete search denominator or a historical prereveal prediction.
