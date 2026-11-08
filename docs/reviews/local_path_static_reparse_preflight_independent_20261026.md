# Static local-path preflight — independent review

Date: 2026-10-26 JST. Approved design
`0043dcc28a8c837dd414cb2c37f5b49cbd42a3d9`, scoped to the common helper's static
metadata ordering. Independent source/native-target PASS, with genuine combined
Ubuntu/POSIX execution and coordinator source freeze remaining release gates.

## Exact source and oracle

Implementation `7d3ab38fd52f9fa89d61b674d2889ff99d20a1dc` normally incorporates
actual main699f0bd at merge `f9247fea7f576818278de057481881213b72a807`.
Final reviewed HEAD `c05a04f99ee4bdf4579a99b104b2d6b9383c0d7a` appends only62
lines of author evidence; runtime and tests are byte-identical across these heads.

| Native LF file | Bytes | SHA256 |
| --- | ---: | --- |
| src/master_inventory.py | 6609 | `7e84d2adc81806bd2d5279709dd315986f5297973d9f721f90abdcd03868f472` |
| tests/test_master_inventory.py | 38247 | `4a235fda43028cf425a76f4bf22a9e369d44be740bab438b5b03d4cc03816fd4` |

Git-native implementation/test blobs, index and source-only CRLF-decoded checkout
agree. Both compile without pycache and diff-check passes. Every non-local_path
module AST body/import/constant is identical to actual old mainc042; generic
master_contracts, including safe_path, is byte-identical. Only the four approved
helper/test/spec/author-record paths differ from the inherited main. No Raw,
policy, namespace, requirement, workflow, state or cycle change is present.
All14 inherited incoming/Raw payloads and both immutable provenance records also
match native Git/index/working bytes; no evidence normalization was performed.

The readable old-function literal is independently compared to the actual
pre-change native function, not extracted from the new implementation:1179 bytes,
SHA256 `bf6bcdcd36fb76ea0ff2268ac68aca53293c2f8b93ad3eaae317576814ac9da1`.
Its guarded loader compiles a distinct callable; modified-literal rejection runs.
CI needs no Git history, another checkout, new goldens or network for this oracle.

## Source reasoning

Existing lexical rejection remains before metadata. Native Path lexical checks
now also precede metadata for nonempty references, preserving empty-root form
and old dot/traversal/drive behavior. Raw root and joined candidate are each
walked in lexical anchor-to-leaf order, without resolving root '..' first.
Already checked identical prefixes are reused within this call.

Each first-visited component is classified from its own single lstat result:
S_ISLNK or Windows reparse attributes cause immediate rejection. No following
predicate is used to discover that static link. Checking the original root
separately prevents a drive-less rooted join from omitting an invalid root.
Only after successful preflight do unchanged safe_path and resolved containment
run, returning the same ordinary Path object/value. Native FileNotFound handling
is retained; other OSError types are not broadened into missing/data results.
Direct POSIX root/path Symlink messages remain in the source and authored tests.

## Fresh independent actual Windows evidence

External script outside the worktree:
`.worktrees/local-path-static-reparse-independent-probes-20261026.py`, SHA256
`942d5d90b2913b171723dbca99bffc99d4fdc9d2092f5f0e682d09244fdc9b11`.
Native Python3.12.14/MSVC, `-B -X utf8`, no OS/filesystem/fcntl facade:

```text
python -B -X utf8 ../local-path-static-reparse-independent-probes-20261026.py . exact-c05a
python -B -X utf8 -m unittest discover -s tests -p test_master_inventory.py
```

The external script executes actual immutable old source and the reviewed helper
against real temporary Windows junctions. Both path-level and os-level metadata,
resolve, open and scandir instruments delegate native operations. Trace-path
classification is purely lexical and never resolves the path being observed.
Baseline descendant Path.lstat counts independently reproduce:

| Shape | Actual old descendant lstats | Reviewed descendant metadata |
| --- | ---: | ---: |
| nested junction | 1 | 0 |
| root junction | 1 | 0 |
| root-ancestor junction | 2 | 0 |
| contained junction | 1 | 0 |
| root junction before '..' | 2 | 0 |

A sixth real-junction call shape, original root plus drive-less rooted join,
also rejects before any descendant metadata or resolution. In all six reviewed
static scenarios, the link itself receives one lstat/no-follow-stat; no following
link predicate, descendant metadata, resolve, payload open or scan occurs before
rejection. Contained targets are not exempt. Actual target sentinels stay exact;
cleanup removes only junctions, never recursively follows their targets.

The independent ordinary matrix compares **115 complete old/new outcomes**:
Path type/spelling or exception class, args, errno, winerror and filenames. It
covers absolute/relative/empty roots, missing and non-directory roots/prefixes,
root '..', ordinary rooted joins, missing leaves, Unicode/internal spaces/dots,
nonambiguous tildes and invalid references. All match on this native platform.
Portable aliases and dot/traversal errors reject before all traced metadata.

Fresh final-HEAD owned suite: **41 tests,36 PASS/five genuine platform skips,
7.248s**. The previous same-source merge-HEAD run was41/36+5,8.983s; it is not
counted as additional functionality. Four skips are actual POSIX symlink paths,
one is Linux orchestrator/fcntl integration. New native junction cases actually
run on Windows. Genuine POSIX behavior is not claimed from these Windows runs.

Fresh suite assertions include old/current whole ordinary inventory/copy/
generated/reuse/runtime-code results and actual payload/hash order; shared G0
ordinary receipt/rescan/byte-count equality and actual tamper rejection; zero
payload charge for static link rejection; unchanged context/caller timeout and
capacity objects; ordinary metadata OSError identity. Native controls preserve
missing/non-directory errors rather than substituting a new ValueError policy.

## Retained failures and bounded disposition

Independently checked the author's actual affected log physical identity:
49457 bytes/SHA256
`dd7aef6ea77d32579729354aacea3fbf2d28c4949a4da1d34ce6c5f6a2f4174b`.
It records262 tests/45.206s,251 PASS/eight skips/**three ERROR**, and ends FAILED.
All three errors are existing native-Windows missing-fcntl master imports:
`test_master_executes_audit_and_preserves_snapshot_inventory`,
`test_only_exact_osm_archive_is_inventoried_not_bridge_runtime`, and
`test_zero_master_budget_never_invokes_auditor`. That process is NOT_PASS and is
not silently converted to green or claimed as a full native-suite success.

The coordinator separately reported an initial103-test invocation with one
loader error for nonexistent `test_restore_gpx_attachment_archive`; this was an
invocation mistake, not a runtime finding. Its corrected four actual modules
ran102 tests:95 PASS/seven genuine platform skips,14.134s. Neither coordinator
command is represented as this reviewer's executed command. Actual combined
Ubuntu remains required, including the existing engine and POSIX tests.

No blocking defect remains in this exact reviewed static-order scope. The
inherited frozen cycle still describes the earlier helper; this review does not
claim a refreshed current-cycle CLI before the coordinator's new freeze.

This fixes static link-descendant metadata ordering only for local_path callers.
It does not fix direct generic safe_path use, legacy enumerators before the
helper, normal drive-less rooted paths' old outside-containment metadata,
concurrent replacement/TOCTOU, arbitrary filesystem behavior or overall process
confinement. No atomic/handle-relative, hard-preemption or new permission claim.
No source authenticity, historical availability, SEARCH/outcome completeness,
Negative/TRAIN/fit, confirmation, official issuance or production authority follows.
