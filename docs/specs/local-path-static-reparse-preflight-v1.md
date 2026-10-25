# Static reparse preflight for inventory local paths v1

Status: DESIGN ONLY. No runtime implementation is authorized by this document.

## Purpose and measured boundary

Move `master_inventory.local_path`'s static ancestor checks ahead of the first
legacy `safe_path` metadata operation. A known, unchanged symlink or Windows
reparse component must be rejected before metadata, enumeration or payload access
to any descendant through that component. The component's own no-follow metadata
is necessary and permitted. This is an ordering correction to an existing reader
guard, with no new source, scientific, permission or publication authority.

Design base: `45c183bba7710d0b568220630b63a70c3a7cac83`. Native source identities:

| File | Git blob | Bytes | SHA256 |
| --- | --- | ---: | --- |
| `src/master_inventory.py` | `e6fe8403529e1740110d7130cb37e119aaed0964` |5533|`1f108ce34e0f450cf4b438a912bb333df923fd50b0e6752760685c00df05db27`|
| `src/master_contracts.py` | `311ee2dc0c0a0766d19b05c85c91247a55f5e3ce` |6512|`8d027230f171d4ab7640689ea8e1b178cac320099c45ce97d317445e43f86686`|

The later PR118 evidence-reader change calls this same common helper; it does not
change these two blobs. The data-preservation tree and records are outside this
slice's write scope.

Actual native Windows11/Python3.12.14 inspection found that `Path.lstat` uses
`stat(follow_symlinks=False)`, while `Path.is_symlink` calls `lstat`. A junction's
own no-follow stat has the reparse attribute and tag `0xa0000003`, but its mode is
not `S_ISLNK`. Thus generic `safe_path`'s symlink-only probes miss a junction and
probe deeper paths before the later inventory reparse walk rejects it.

Prior controlled native traces measured **1, 1 and 2 descendant lstats** for a
nested junction, root junction and root-ancestor junction, respectively. Both
direct `safe_path` and `local_path` made those metadata probes; `safe_path`
returned a path while `local_path` eventually raised ValueError. Payload opens
were zero and the temporary outside sentinel was unchanged. These measurements
establish the remaining static metadata issue; they do not show an outside payload
read. No additional link demonstration is needed before implementation.

## Chosen scope and alternatives

The selected approach changes only the common inventory helper's ordering and
uses one no-follow stat result to classify each checked component. It covers
callers that already use `local_path`, preserves their existing budgets and avoids
changing the generic `safe_path` API throughout the repository.

Changing generic `master_contracts.safe_path` would affect direct legacy callers
and their error behavior without being necessary for this bounded correction.
Handle-relative platform I/O would address a larger concurrent replacement problem
and requires a separate design. Neither alternative is included here.

Future implementation ownership is limited to:

- `src/master_inventory.py`: `local_path` body and, only if needed, a private
  helper used solely by it. Other function bodies and constants remain identical.
- `tests/test_master_inventory.py`: metadata-order, compatibility and ordinary
  caller-output controls, including a small frozen readable old-helper literal.
- This spec, only for evidence-driven corrections, and a new author/independent
  record `docs/reviews/local_path_static_reparse_preflight_20261026.md`.

No generic `safe_path`, enumerator, namespace, allowed-root, evidence reader,
Raw/intake record, policy, requirement, workflow, state or cycle edit is included.
The coordinator owns later source closure/freeze and integration records.

## Exact preflight behavior

1. Keep the existing `Path(root)` conversion and PureWindowsPath checks on the
   supplied relative reference. Drive/absolute/traversal rejection and the exact
   portable-component rule remain before any metadata: trailing ASCII dot/space,
   colon and `~[0-9]+(?:\.|$)` are rejected. Unambiguous Unicode, internal spaces
   or dots, `tilde~name` and `x~1name` remain accepted.
2. Before metadata, also perform the existing native `Path(relative)` lexical
   checks that `safe_path` would perform for a truthy relative string. Preserve
   empty relative as the special root form; `.`/`./` remain invalid relative refs.
   Do not interpret POSIX filenames using Windows path-joining semantics.
3. Construct the candidate with the same native joining operation as `safe_path`
   (`root / Path(relative)`), or the original root for empty relative. Preserve
   both objects' spelling, relativity and unresolved `..` components. Do not call
   `resolve`, `realpath`, `normpath`, `exists`, `is_dir`, `is_symlink`, `is_junction`,
   `stat` with following enabled, `open` or `scandir` to prepare this preflight.
4. Visit the raw root's absolute lexical ancestor chain from anchor to root, then
   the candidate path's absolute lexical ancestor chain from anchor to leaf.
   `Path.absolute()` prepends the native current directory without resolving or
   normalizing `..`. Checking the root separately is necessary because a native
   drive-less rooted reference can reset the join's root while legacy `safe_path`
   still probes the supplied root first. Repeated identical lexical prefixes may
   reuse the already checked static result within this call.
5. For each first-visited prefix call `lstat` once, preserving the current
   `FileNotFoundError` continuation. Classify the returned object with
   `stat.S_ISLNK(info.st_mode)` and the existing
   `st_file_attributes & FILE_ATTRIBUTE_REPARSE_POINT` test. Reject immediately
   before inspecting any later descendant. Do not call an additional following
   predicate to classify that object. All reparse types, contained or external,
   stay rejected; a contained target is not an exception.
6. Preserve error class and established single-link messages. For an ordinary
   symlink with nonempty relative, an exact supplied-root symlink retains
   `Symlink root is forbidden`; a symlink on the relative path retains
   `Symlink path is forbidden: {relative}`. Root ancestors, root-only calls and
   Windows junction/reparse cases retain `Reparse inventory path is forbidden`.
   Build any relative-prefix classification lexically, before metadata. When
   multiple invalid components exist, the first offending checked ancestor wins;
   the guard must not follow an earlier link to discover a later preferred error.
7. After successful preflight, call unchanged `safe_path` for nonempty relative,
   retain the existing resolved containment test and return the same ordinary
   `Path` object value. Replace/reorder the old later reparse walk rather than
   using its predicates before preflight. Existing containment failures remain
   ValueError with `Inventory path resolves outside root`.

Ordinary OSError subclasses, including PermissionError and NotADirectoryError,
must propagate with their ordinary details/identity; do not broaden the current
FileNotFoundError catch or convert errors into missing/data-blocked results.
The function gains no deadline, callback, counter reset, byte allowance or clock.
Caller checks still run in their existing locations and propagate unchanged.

## Root, missing-path and lexical compatibility

There is no new requirement that roots be absolute, exist or be directories.
Existing roots containing `..` remain accepted when the old helper accepts them.
Before visiting `prefix/..`, the uncollapsed `prefix` must have been no-follow
checked. In particular, a static junction/symlink at that prefix must be rejected
before a normalization or parent traversal can hide it. A missing prefix continues
through the same FileNotFoundError policy; do not silently reject or canonicalize
the returned path. A non-directory prefix is not proactively converted into a
new ValueError: preserve the native old-helper return/error for that platform.

Native drive-less rooted references retain their existing final containment
behavior, including accepted forms that resolve within the supplied root and
rejected forms outside it. This slice does not add a new absolute-root or spelling
restriction to simplify the walk. Drive-relative/UNC/drive-qualified references
already rejected by the relative-reference guard remain rejected before metadata.

A throwaway candidate outside Git compared original and proposed ordering on
**63 actual native Windows cases: 63 equal, 53 returned paths and 10 errors**.
It checked complete return type/spelling or error class/args/errno/winerror/filename
for absolute/relative roots, empty and dot roots, roots with existing/missing/
non-directory prefixes before `..`, missing roots/leaves, non-directory roots,
normal/invalid relative refs and drive-less rooted forms. Windows returns some
nonexistent or non-directory-descendant Paths without requiring an existing
target; that behavior is deliberately preserved. These are design feasibility
controls, not a product implementation pass or POSIX simulation.

External control script:
`C:\Users\qq113\OneDrive\ドキュメント\ChatGPT\ハブAI\.worktrees\local-path-static-reparse-design-controls-20261026.py`,
SHA256 `b144aa8bacab67df3dce21532cb4a4c798ad245ce6e1e41e1f3bde53962549df`.
Its19245-byte actual report has SHA256
`1cd18836bde21a7467abe9e5e8a71444af0fb42650e484f1a94258f9813656ab`.
No repository runtime/test/index was changed by that comparison.

## Required implementation tests and independent review

Use TDD against the actual old helper. New metadata-order tests must first fail
because of the already measured descendant stat, then pass after the narrow fix.
Track actual native lstat/stat, resolution, payload open/hash and scandir calls;
the instrumentation itself must not resolve the tested path to classify it.

Required controls:

- Actual Windows nested, root, root-ancestor, contained and source/destination
  junctions: reject at the link's no-follow metadata with **zero descendant
  metadata**, zero outside payload open/hash and zero outside enumeration. Include
  a root lexical `junction/../...` case so early normalization cannot hide it.
  Remove only the verified temporary link before recursive fixture cleanup.
- Actual Ubuntu/POSIX symlinks for those supported shapes, including direct
  symlink root/path error strings, broken links and a symlink before root `..`.
  A genuine POSIX CI run is required; Windows platform skips are explicit limits,
  never replaced by a fake filesystem or fcntl facade.
- Preserve the existing portable alias lexical-before-metadata tests, valid
  Unicode/internal-name byte controls, traversal/absolute refs, deep/wide walk,
  source and destination copy, missing snapshot, generated artifacts and reuse.
- Self-contained original/candidate root matrix on each native platform. Freeze
  the exact baseline `local_path` function text as a readable test literal with
  its independently checked SHA before compiling it into a distinct callable;
  CI must not require Git history or another worktree. Test a changed literal is
  rejected by its integrity loader. Compare full returned Paths/errors, rather
  than only success booleans; do not hard-code Windows error details for POSIX.
  The exact native LF function at baseline lines24–45 is1179 bytes, SHA256
  `bf6bcdcd36fb76ea0ff2268ac68aca53293c2f8b93ad3eaae317576814ac9da1`;
  preserve it rather than extracting the oracle from the implementation under test.
- Ordinary-path old/current `inventory`, `copy_inputs`, `snapshot_matches`,
  `generated_artifacts` and runtime-code identity controls using identical actual
  source bytes. Compare complete inventories, copies, return values and actual
  payload read/hash order/counts. Source-code identity changes can legitimately
  change source-bound hashes; hold code inputs identical for the comparison,
  never regenerate old goldens from the new helper or skip differences.
- Shared G0/ProspectiveReadContext controls must preserve ordinary payload/ref
  receipts and actual read/byte counts, and retain zero payload charge on static
  link rejection. Caller timeout/check exceptions and local ordinary OSError
  instances propagate unchanged; no broad catch may hide them. Existing hash
  mutation/final reread failures remain failures, with no partial success artifact.
- Check all non-owned function bodies and generic `safe_path` are unchanged.
  Independent review must inspect actual prefix order and separately verify native
  Windows and actual POSIX results before claiming cross-platform completion.

Design baseline command on exact45c183b:
`python -B -X utf8 -m unittest discover -s tests -p test_master_inventory.py -v`
ran26 tests in3.943s:22 PASS and4 explicit native-POSIX skips. This is the old
baseline, not coverage of the unimplemented preflight. No full suite was rerun.

## Explicit limits and later gates

This closes the measured static-link descendant-metadata ordering only for
`local_path` callers. Direct generic `safe_path` users (including prediction and
training source paths), legacy glob/rglob/exists operations performed before this
helper, and other readers are not audited or changed here. Ancestor metadata
outside the workspace's lexical prefix is required to validate that prefix.
The contract is not a claim of overall filesystem confinement.

An attacker or another process can replace a component after preflight. The
later ordinary path operations are not an atomic, handle-relative transaction;
TOCTOU, concurrent ancestor substitution and arbitrary mount/filesystem behavior
remain outside this slice. Existing final hash/closure checks are retained but
must not be advertised as preventing every such race. This design adds no
permission, issuer authentication, historic availability, source qualification,
SEARCH completeness, training, confirmation, official prediction or production
authority. Code implementation, independent review, actual Ubuntu CI and current
source closure/fresh-main verification require separate coordinator dispatch.
