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

## Current-main merge and final affected verification

Implementation checkpoint `7d3ab38fd52f9fa89d61b674d2889ff99d20a1dc` was clean
before normally merging actual main `699f0bda36b32caa2225d2d42962d590d561040b`.
The resulting tested source HEAD is `f9247fea7f576818278de057481881213b72a807`.
The merge used only command-local `core.autocrlf=false` with normal Codex identity;
no global config or existing Raw rewrite occurred. All14 newly inherited incoming
and Raw transport files matched their native main/Git blobs byte-for-byte,524265
bytes per seven-file copy. Both immutable provenance records also matched native
Git: received8576 bytes/SHA256
`e31eb1547eda0b92045bfb285f11a97ef74242e1196164bb69ccaf45c4d404d8`,
promotion13015 bytes/SHA256
`1b6c5c6cef876220427719805837a65d3d66968c1ff18ceaa895b59f50f92b8c`.

Against that current main, only the four approved implementation/test/spec/review
paths differ. The canonical runtime/test blobs in the table above remain exact;
an AST comparison still finds all non-local_path bodies/imports/constants identical.
Generic master_contracts.safe_path, Raw/incoming/intake records, policies,
requirements, workflows and coordinator state/cycles have no worker diff.

One fresh combined process loaded the following real unittest modules from tests,
using actual native Python3.12.14 with `-B -X utf8`. No filtering or fake POSIX was
used. It ran **262 tests in45.206s:251PASS,8 explicit platform skips and3ERROR**.

| Module | PASS | Explicit skip | ERROR |
| --- | ---: | ---: | ---: |
| `test_master_inventory` |36|5|0|
| `test_evidence_receipt_read_guards` |15|1|0|
| `test_gpx_attachment_intake` |31|1|0|
| `test_prospective_inputs` |64|1|0|
| `test_g0_forecast_contract` |60|0|0|
| `test_g0_training_source_contract` |14|0|0|
| `test_evidence_audit` |31|0|3|

Every error was ModuleNotFoundError for native-Windows `fcntl` on an existing
master_orchestrator import, specifically EvidenceAuditTests:

- `test_master_executes_audit_and_preserves_snapshot_inventory`
- `test_only_exact_osm_archive_is_inventoried_not_bridge_runtime`
- `test_zero_master_budget_never_invokes_auditor`

These errors are retained; the combined run is not described as all green.
The five owned skips cover four real POSIX symlink paths and one Linux orchestrator
integration. The other three skips are genuine POSIX checks in existing evidence,
GPX and prospective modules. All actual Windows junction metadata cases,63 frozen
ordinary controls, old/current whole ordinary outputs/read order, shared G0
receipt/count/tamper tests and callback/error identity controls passed.

Actual complete output is outside Git at
`C:\Users\qq113\OneDrive\ドキュメント\ChatGPT\ハブAI\.worktrees\local-path-static-reparse-verification-20261026\affected-tests.log`,
49457 bytes, SHA256
`dd7aef6ea77d32579729354aacea3fbf2d28c4949a4da1d34ce6c5f6a2f4174b`.
Separate orchestration wall time was46.735s. No full native suite or complete-input
data audit was repeated for this helper change. The older complete data audits
retain their actual source/runtime identities and are not relabeled as this code.

This is a native source/target verification receipt with the recorded Windows
limits. Actual Ubuntu/POSIX execution, independent source review and coordinator
source closure/exact-head/fresh-main gates remain required. The current source
change is not already included in the inherited frozen cycle; no current-cycle
validation, parent run or scientific qualification is claimed here.
