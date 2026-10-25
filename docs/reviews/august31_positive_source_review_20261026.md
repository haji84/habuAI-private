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

Pending the code checkpoint, normal reviewed PR119 merge and complete native Git
tree source-only run. No final registration is authorized by this record.
