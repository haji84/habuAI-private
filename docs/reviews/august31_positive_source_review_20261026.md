# Aug31 source-occurrence verifier, implementation record

This implements the approved fixed two-statement profile. It does not register
either statement: the final review JSON is absent and the repository policy is
unchanged. The two committed CSVs are diagnostic until a separately authorized,
independently reviewed registration after actual Ubuntu code CI.

## Meaning and immutable source binding

The original UTF-8 text is 116496 bytes, SHA256
`130dedae6e04501f4be41fff4ff549a9cfc1a1840dcbb0126359b04465ab7e8c`.
Exact unmodified slices are lines 10110–10119, bytes [112368,112489),
SHA `0e3ef4d50ff5cf9c98b3e0012d9fc75e7a24d6667e0f6b5f259ed5a86e7b4581`,
and lines 10492–10500, bytes [116249,116392),
SHA `6bd4b0ed2c572d9b0bd39f8137456e53c7721028f7f88e6e03e4a822c88bceea`.
The source line-ending bytes are included. The older normalized block hashes are
not presented as native slice hashes.

Both are singular owner capture statements, consistent with the existing owner
Aug31 count of two. Neither literally establishes a permanent biological ID.
`AUG31SRC-L10110` and `AUG31SRC-L10492`, and their `-OCC01` links, are explicitly
new derived source-record/occurrence references. Two occurrences do not prove two
distinct physical animals. Size `100~120` is a source size range, not quantity or
verified exact measured length. The first event's place remains empty.

The preserved original GPX is 4753470 bytes, SHA
`870047567bb0d9bafca0789f768fda3b7b90eb5788f259d043cdb885ce219bd1`.
Unchanged matching/QC gives 17906 points, zero excluded, one unrelated break and
maximum gap 50.826 seconds. Selected residuals round to .849m/26.001s and
.002m/9.999s, HDOP 4.687/3.0 with one-second neighbors. No interpolation or
complete-search assertion is made. The existing owner record remains byte-exact,
including its historical `log_byte_exact_native_original_verified=false`; the
separate later native-byte proof does not rewrite old evidence. Owner 47/243,
the unresolved Aug19 possible overlap, other August statements and all Raw are
unchanged.

Derived capture CSV: 413 bytes, SHA
`137c04b5abe6713c1668633fe10afa61f601a5c0a8d5331471d71f8cbf0a972f`.
Derived occurrence CSV: 378 bytes, SHA
`6d0c01d185722044bf976f2858461990518dffe6ee402815269ad94f5f242947`.
Tests compare these native Git bytes with the exact original-source projection;
only an explicit pre-commit development fallback reads untracked working files.
Runtime has no Git/network dependency.

## Runtime and failure boundaries

The new module consumes only supplied guarded `Audit.ref`, `Audit.tick` and point
callbacks. It verifies all six fixed references, actual native sizes/hashes,
strict bounded JSON, exact selectors/CSV/link fields, actual point matching and
canonical typed proof; it rereads all references. The auditor additionally
guards initial fixed CSV/review reads, executes this proof before role update,
rereads the review and retains its existing full consumed-input rescan/final seal.
There is no new deadline, private reader, namespace or cap.

The new fixed CSV cannot use an omitted/unknown/legacy profile. Only its exact
canonical path is admitted. ASCII-case, backslash and dot-component aliases are
recognized as this same new path and rejected before generic legacy admission.
Canonical-plus-alias or repeated declarations reject before any new role update,
in either order. This guard does not rewrite Sept28 or general policy semantics.

All authority fields are false; device authentication and permanent biological
identity remain NOT_ESTABLISHED. Availability uses actual current review/audit
time, never an inferred August received/usable time. No Negative, search scope,
complete outcome coverage, training, confirmation, issuance or production claim
is granted. Failure/expiry clears public qualified units/events through the
existing audit failure boundary. The failure manifest can still report previously
checked declaration metadata; it is not a successful reusable qualification.
Known shared-helper metadata-only lstat/other legacy enumeration limitations and
cooperative, non-hard-preemptive parsing/matching limits remain unchanged.

## Actual TDD and native verification

- Before implementation, missing verifier API and the legacy role-only Aug31
  admission each failed. Both became green after the fixed verifier/dispatch.
- A valid new declaration followed by missing/unknown-profile declaration left
  `outcome_label` set: two actual failing assertions in 3.398 seconds. New-path
  duplicate preflight fixed this. Both orders, valid duplicates and valid Sept28
  mixed with rejected Aug31 declarations pass.
- An alias with an omitted profile actually reached legacy role admission on
  Windows: RED 1/1 (1.586s). Canonical-path enforcement fixed it. Folder ASCII
  case, `.CSV`, backslash and `./`, standalone and both canonical/alias orders,
  reject; shared portable-name restrictions are not relaxed.
- Real Windows junctions at CSV, review and GPX ancestors, plus a missing-profile
  CSV case, produce zero external payload opens. Cleanup removes only created
  junctions with rmdir before private temporary trees are deleted. Linux uses
  real directory symlinks; actual Ubuntu execution remains a coordinator gate.
- Changed/rehashed source refs, typed proof bool/int/float substitutions, review
  duplicate JSON/nonfinite numbers, duplicate/orphan/extra/mismatched rows,
  entity/size/point count, shared budgets, late source/review mutation and final
  success-hash expiry are covered. Ordinary ValueError, TimeoutError,
  AuditBudgetExceeded and MemoryError caller checks retain exact identity.

The immutable old auditor capsule is 42426 native LF bytes, SHA
`4d8de850a18a79899f17baf33cbd8ab7d6caeb606550771d3a692cdfba97ccf3`.
Before edits its complete result/input/read/open ledger on the fixed 45c183 native
input was captured externally (566151 bytes, SHA
`e1e16caac9986c8d0441dbf1ab4f167aa1907f1d3534dfe61f12efe1fa304904`).
Current code matched that entire canonical typed object, without exclusions or
golden regeneration: 362 immutable input files, 517 reads, 350684542 bytes,
289727 points, five positive events/units and zero Negative; compare 14.250s.

An initial native affected-target attempt ran 126 methods: 120 passed, three
genuine POSIX skips and three existing master-import errors (`fcntl` absent on
Windows). This is not a full-suite success. Subsequent failfast focused run:
72 methods, 70 passed/two genuine POSIX skips, 63.092s. Existing Sept28 21 methods
in the initial run passed 20/one POSIX skip. The separately selected 31 portable
evidence methods and final committed-snapshot measurements are recorded below.

Pre-PR119 native combined source-only temporary audit (not parent PDCA), actual
2026-10-25T16:02:16.902245Z: 542 reads/360570139 bytes/307633 points, 27.500s,
PARTIAL, seven source-qualified events/eight recorded occurrences/seven positive
units/zero Negative, denominator NOT_ESTABLISHED, scientific NOT_VALIDATED.
362 original input files remained unchanged. Temporary provisional review/policy
were not published. This is superseded for final input coverage by the complete
committed-tree run after the reviewed PR119 merge.

PR118 exact and fresh-main c042 Ubuntu evidence was supplied by the coordinator:
1464 tests/24 skips, including actual POSIX engines, cycle CLI and secret guard.
PR119 exact Ubuntu also passed; its fresh-main status is a separate gate. No
Ubuntu success is inferred from native Windows results.

## Final committed-tree verification

Code checkpoint `6738af3` owns only six approved implementation/test/derived/doc
files. The reviewed PR119 main `699f0bda36b32caa2225d2d42962d590d561040b` was
normally merged using one-command `core.autocrlf=false`, with no global config
change, yielding `621c8b6a487dd609e9d6915ccc4d76118d494d71`, tree
`49cbdb2c7addf6252ce91d50ca7ab0ec5fa1c946`. The seven new Raw transport files,
seven incoming files and two immutable intake records matched their native Git
blobs byte-for-byte immediately after checkout (16/16), without normalization.

The complete committed tree was materialized outside Git from native archive
bytes. Exact path inventory, Git blob-object SHA1, byte size and physical SHA256
were verified for **all 869 files / 181966878 bytes**, including code, docs,
Raw/data, evidence, incoming and policy. Full manifest SHA256:
`4a5d893f442edfcfbef1af19ec396d0fc6d964c1f5188793b243fdbdb58d0596`.
The auditor and new verifier were imported from that immutable snapshot itself
in a new genuine native Python process, not from the working repository.

Only two provisional private changes were made: append the sole new source
declaration to temporary `policies/observation_evidence.json` while retaining
all prior entries exactly, and create the temporary final-path review JSON.
Every other 868 committed files remained byte-identical. The audit changed no
input; the full physical snapshot manifest after the audit exactly equaled the
known provisional input manifest. All 220 consumed path hashes were rechecked.

Actual source-only audit time `2026-10-25T16:10:21.249894+00:00`:

| Measurement | Actual result |
| --- | --- |
| Status / elapsed | PARTIAL / 28.000 seconds |
| Shared actual reads / bytes / parsed points | 556 / 361618669 / 325364 |
| Unchanged caps | 4000 / 536870912 bytes / 1000000 points / 300 seconds |
| Source-qualified events / recorded occurrences / positive units | 7 / 8 / 7 |
| Negative / actual qualified TRAIN rows | 0 / 0 |
| Denominator / scientific validation | NOT_ESTABLISHED / NOT_VALIDATED |
| Consumed-path manifest SHA256 | `4dab96ba358df7704316923d79b20af4d918ae1248a01e31092b8cb491c60f35` |
| Audit self SHA256 (excludes own hash) | `82ea856a34220b52f77dc7df6b133aef4aeb77293ee3fa4842d83016a77c16df` |
| Complete audit physical canonical SHA256 | `6706c1f657b1a6679f0b4f67bac976ea3d66c364fb4fcb67177eaeeff853fc17` |
| External full receipt physical SHA256 | `1f261615e9c401c637f8b88c42307c52f5247d6754e64ff603bfb7009fbae1ef` |

Preparing the provisional proof separately used 12 reads/9749432 bytes/17906
points; it was not counted as the runtime audit or substituted for runtime
verification. The actual audit executed the full verifier again under its one
shared context. The provisional review was 3973 bytes, SHA
`33bf7085cf3ff5628bf0af3ec3aeccd23c9ed624a88022c27873425ac7831950`;
this is temporary evidence, not a registration timestamp to reuse.

Pinned native code SHA256:

| Snapshot code | SHA256 |
| --- | --- |
| `src/aug31_positive_source_review.py` | `c45bf601c0155dc524f4eee38b068c9a07d63fd38713a69c4b735832c23095dc` |
| `src/evidence_audit.py` | `4329ed74e1f58b63b3010beda76859beabe9b5f3be2f517efc8bc904a209cd4b` |
| Existing Sept28 verifier | `109f39a68d7f5db10adf991d7cc6e512d4fe58edfcc050cd2219d7de737928e8` |
| Existing GPX attachment reader | `72fb3506aa94d0c2f8706f5474bd28257b109981baad80d7d54c4b5790815a45` |
| Existing GPX matching/QC | `878ff42ec767e671bf9581ce2d1635c5282ffca469dc6f247654817b7c55779d` |
| Existing shared path guard | `1f108ce34e0f450cf4b438a912bb333df923fd50b0e6752760685c00df05db27` |

The external full-tree harness initially named the GPX helper incorrectly and
failed its setup manifest lookup before any audit; correcting that harness-only
filename was not a product fix or a product RED. No source changed after this
successful snapshot. Portable evidence regressions passed 31/31 in 12.293s;
the three fcntl-dependent master cases remain explicitly Ubuntu-only rather
than fake-imported or silently treated as passed. Final native committed-CSV
and whole-Sept28 exact-source reruns follow below. No registration, parent PDCA,
whole-night outcome completeness, biological uniqueness, fit or authority is
established by any of these measurements.

Final committed-CSV rerun: all 24 new methods passed, no skips, 57.447s.
Its snapshots read the two committed native CSV Git blobs and compare them with
the source projection. Final frozen-whole-Sept28 rerun against the exact same
pre-edit artifact passed in 23.734s: identical 566151 canonical bytes/SHA,
517 reads/350684542 bytes/289727 points and complete typed/read/open objects.
Concurrent native verification explains elapsed variation; numeric or identity
expectations were not relaxed. The initial three fcntl errors were not rerun or
called successes. Genuine Ubuntu remains required for those platform contracts.

Focused reproducible commands (bundled Python, `-B -X utf8`):

```text
python -B -X utf8 -m unittest tests.test_aug31_positive_source_review -f
python -B -X utf8 -m unittest tests.test_gpx_attachment_intake tests.test_evidence_receipt_read_guards -f
```

The full native-tree receipt and immutable pre-edit whole artifact are private
external verification records under the coordinator's `.worktrees` directory,
not new Raw, production evidence, historical registration or input requirements.
This document update changes no code or source input. Final review JSON remains
absent, policy/old Sept28 inputs remain byte-identical to reviewed main, and
independent exact-source review plus actual Ubuntu code CI are still pending.
