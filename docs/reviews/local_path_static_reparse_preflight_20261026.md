# Static local-path preflight implementation record

Approved contract: `docs/specs/local-path-static-reparse-preflight-v1.md`, design
commit `0043dcc28a8c837dd414cb2c37f5b49cbd42a3d9`. This worker owns only the common
helper body, its tests, this author record and necessary spec clarification.
Generic safe_path, other runtime bodies, roles, budgets and coordinator metadata
are outside the implementation scope.

## Implementation and TDD checkpoint

The old native LF local_path function was frozen before the runtime edit as a
readable1179-byte literal, SHA256
`bf6bcdcd36fb76ea0ff2268ac68aca53293c2f8b93ad3eaae317576814ac9da1`.
Its loader verifies byte length/hash before compiling a distinct callable;
an actual changed-literal control is rejected. CI does not need Git history.

The initial actual Windows run of test_master_inventory had35 tests: six intended
metadata-order failures, no errors and five explicit POSIX skips (5.771s). The six
failures were contained, nested, root, root-ancestor, root-before-dotdot junctions
and the copy destination. Every failure showed real descendant lstat/stat calls
before rejection. Existing portable guards, the frozen oracle and all63 complete
ordinary return/error controls passed. The fix then ran35 with30PASS/five skips
in6.018s.

Only local_path changed: native lexical validation precedes metadata, then both
the raw root and joined path are walked anchor-first using each component's own
no-follow stat. Unresolved root `..` prefixes remain visible. Symlink mode and
Windows reparse attributes are classified from that result before any descendant;
the unchanged generic safe_path and final containment check run afterward. The
existing POSIX root/path Symlink messages and Windows Reparse message are retained.

A subsequent controlled test with the frozen old callable confirmed an additional
reason to check the raw root separately: a drive-less rooted relative join could
omit a root-ancestor junction from the final path and be accepted by the old
helper. The new helper rejects before descendant metadata. Ordinary non-link
rooted joins still match the original63-case matrix; no new root restriction was
introduced to obtain that rejection.

Additional controls compare complete inventory/copy/generated/reuse/code-identity
outputs and actual payload/hash order under identical source bytes. Shared G0
read/rescan receipts, byte counts and actual hash-tamper failures match the frozen
old helper. Ordinary OSError and caller timeout/capacity objects propagate by
identity, and the shared context's deadline/maximum/charged bytes remain unchanged
at caller check failures. A real shared-reader junction rejects without any byte
charge. Final local checkpoint:41 tests,36PASS/five genuine POSIX skips,8.345s.

Canonical native LF implementation at this checkpoint:

| File | Bytes | Git blob | SHA256 |
| --- | ---: | --- | --- |
| `src/master_inventory.py` |6609|`d8656f2750815aaf4cc6672bd77315a02762c2f7`|`7e84d2adc81806bd2d5279709dd315986f5297973d9f721f90abdcd03868f472`|
| `tests/test_master_inventory.py` |38247|`482fa2f8fe0fe2d5bde81754d27e1c63f5881258`|`4a235fda43028cf425a76f4bf22a9e369d44be740bab438b5b03d4cc03816fd4`|

An AST comparison against45c183b, excluding only local_path, found every other
module body/import/constant unchanged. This is a clean implementation checkpoint,
not final integration or independent review. The next step is a normal merge of
actual main699f0bda using a command-local byte-preserving checkout setting, verify
the newly inherited14 incoming/Raw payloads and two immutable provenance records,
then run the current affected targets before source release.

## Limits

The measured guarantee is zero descendant metadata through a known static
symlink/reparse component before rejection. Ancestor metadata, ordinary rooted-join
metadata outside the root before the old final containment decision, direct generic
safe_path callers, earlier legacy glob/enumeration and concurrent replacement races
remain outside this fix. No atomic handle-relative confinement claim is made.
Actual native POSIX symlink/message checks and full integration need genuine
Ubuntu CI; no fake fcntl, OS facade, permission change or dependency install is used.
No new science, source issuer, search completeness, fit or production authority is
granted. Independent source review and coordinator closure/freeze are pending.
