# Request v3 source configuration implementation checks

Base: coordinator PR107 exact `5b0d5e090d3addd88dbfe5d8fbec66795f03018d`.
Branch: `codex/research-config-source-v3-20261025`.
This record reports implementer checks. Independent exact-source review and
coordinator Ubuntu CI/integration remain pending.

## Delivered boundary

New guarded source-profile loader plus narrow additive request v3 dispatch. The
pure config/learners, full-ledger Stage1 registry/source adapter, shared STATE,
cycle/freeze artifacts, Raw and ORIGINAL files are unchanged. Request v3 accepts
exact twelve fields; old requests retain their original shapes and dispatch.

The loader checks physical/canonical hashes, immutable-cycle envelope, fixed
policy, exact current code closure and strict four-stage effective readiness at
the training boundary. It consumes all bytes through one existing context with
the declared/actual 16MiB first-read-plus-rescan phase cap, retaining original
ref sizes. The parent passes remaining time and its check into pure v2, performs
post-fit/post-Stage1/pre-publication source scans and reuses v2 owned publication
and cleanup. It does not invoke the cycle CLI or an unchecked code reader.

Stage1 null reads no evaluation. Only the exact old ordered triplet reuses the
existing Stage1 adapter. Other requested triplets/orders are explicitly
IMPLEMENTATION_BLOCKED before opening the evaluation manifest; complete prepared
sets remain unmodified in development REPLAY. Insufficiency publishes no partial
set. Neither successful bytes nor receipt timestamps authenticate historical
availability, an issuer, currently loaded code, a campaign ledger or a freeze.
All scientific, fit, selection, promotion, confirmation and production authority
flags remain false.

## Verification

- New source-loader tests first failed because the API did not exist; new parent
  v3 tests first failed at the old exact request schema. Known omissions were
  then fixed under these controls.
- Final native Windows targeted run: **162 tests, 156 PASS, 6 existing POSIX
  skips, 35.920 seconds**. Modules: research_candidate_config_source (16),
  research_pdca_adapter (27), stage1_source_adapter, research_model_adapter,
  hba1_feature_candidate, codex_cycle_contract and codex_cycle_prewalk.
- The new actual Windows junction test rejects a linked root before any
  `Path.open`; cleanup removes the validated link itself with `os.rmdir` and
  retains its target. POSIX uses a real symlink instead.
- Actual strict TRAIN/forecast loaders consume the synthetic complete seven
  feature fixture (20 TRAIN rows / five nights, four forecast units). HB-A1 joins
  the complete three-candidate set; unsupported Stage1 remains unopened and the
  unmodified set is retained in REPLAY. Exact old triplet passes the existing
  synthetic Stage1 source projection (three declared individuals).
- Negative controls include each readiness equality, missing/unknown fields,
  effective-parent maximum drift, code omission/extra/duplicate/mutation,
  actual implementation SHA mismatch, policy/config digest drift, duplicate
  JSON, reserved/control paths, declared/actual capacity, reference ownership,
  final receipt hash expiry, post-fit/post-stage source changes, missing input
  DATA classification, no partial fit and actual post-publication expiry cleanup.
- Request-ref shadowing discovered while inspecting a failure result was fixed
  with an explicit request-path assertion. Failed v3 publication also removes
  its Stage1 dispatch success marker along with candidates/metrics/REPLAY.
- Same-runtime complete-output comparison against the archived parent source
  from base `5b0d5e0` passed for both v1 and v2, using separate fresh synthetic
  workspaces. Complete output digests: v1
  `0c5784ca813904a46bda84881660ced71f7f48be0da79562e33ebbe8588cc11a`, v2
  `21fef55970f5bb42ff50a549ae8ea990f18f6cc44d4acabcf778f7d196bfc1cc`.
- Four changed/new Python source/test files compile; `git diff --check` passes.

No native full-suite/Linux result is claimed. The six POSIX-specific paths in
the targeted set require the coordinator's exact-head Ubuntu CI; this Windows
run does not emulate fcntl, descriptor-relative cleanup or POSIX interruption.
No actual data was fitted, and no source qualification or scientific
performance claim was generated. A new complete runtime-code freeze is required
after coordinator integration; historical cycles are preserved.

## Independent exact-source review (reviewer-owned)

**Bounded code review PASS.** No blocking defect was found at source commit
`cb2a1c12ef3e3a181f3f6210c24d30479e66261a`, against base
`5b0d5e090d3addd88dbfe5d8fbec66795f03018d`. The independent reviewer changed
only this section, without editing implementation, tests, spec, Raw, ORIGINAL,
Freeze, shared state, policies or cycle artifacts. The implementer record above
remains a separate record of its earlier checks.

Exact reviewed Git blobs:

| Path | Blob ID |
| --- | --- |
| `src/research_candidate_config_source.py` | `c94ad002c2e4e146a0260757d9d0ef069a4d166e` |
| `src/research_pdca_adapter.py` | `25ef1b12826935058ba11903b789d0f6a8b290b6` |
| `tests/test_research_candidate_config_source.py` | `b0f41dc5c6f29e9b6b0adcf663662c1056020bdf` |
| `tests/test_research_pdca_adapter.py` | `3125eb4d27940a432fa50b836a9227852b309fdb` |
| `docs/specs/research-candidate-config-source-v3.md` | `a67e30cc0fcae0e15e22971ba8db50a6ec038571` |

SHA-256 of the two runtime Git blobs, independent of checkout line endings:
loader `19a9a66c3f4828ab36c6348efb64a6317fcd73b207ab70afb3d702cdb7071943`;
parent `0a98ed940e461b49dd85802e2dd4f0006f3245a1e8ff55c831120aec9b8ba104`.

### Fresh commands and counts

All commands used the native Windows runtime
`C:\Users\qq113\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe`
with `-B -X utf8`, from this worktree. No fake `fcntl`, actual field fitting or
sealed confirmation input was used.

The following runner, passed on standard input to that runtime, freshly ran
**162 unittest methods: 156 PASS, six existing platform skips**, in 30.346s:

```python
import sys, unittest
sys.path[:0] = ['src', 'tests', '.']
names = (
    'test_research_candidate_config_source', 'test_research_pdca_adapter',
    'test_stage1_source_adapter', 'test_research_model_adapter',
    'test_hba1_feature_candidate', 'test_codex_cycle_contract',
    'test_codex_cycle_prewalk')
loader = unittest.TestLoader()
suite = unittest.TestSuite(loader.loadTestsFromName(name) for name in names)
result = unittest.TextTestRunner(verbosity=1).run(suite)
sys.exit(not result.wasSuccessful())
```

`python -B -X utf8 ..\config-source-v3-review-probes-20261025.py .` freshly
passed **53 independent assertions**. The local external probe SHA-256 is
`41867e3d1679a886b01d3d4f39908a80b8ad77e8daf1238736730681ddf4fa05`.
The script remains outside the tracked source tree; its location/hash does not
imply publication or CI execution. Assertion counts are separate from unittest
method counts. `git diff --check` against the exact base also passed.

### Independent checks and disposition

The reviewer independently exercised actual temporary source files and the
actual strict TRAIN/forecast loaders. Whitespace-altered config bytes retain
distinct physical and canonical hashes. First-read plus first-rescan charges
equal twice the complete bound closure; a prior 123456-byte charge remains in
the same context. Neither its maximum byte allowance nor absolute deadline is
reset or restricted to the source phase's 16MiB. Source growth rejects using
the original receipt size rather than adopting a new stat result.

A valid late readiness declaration returns the data-block exception only after
consistency checks. Combining it with a bad canonical config hash, changed
policy bytes, changed code bytes or mismatched A1 implementation hash remains
invalid evidence. Adding an unregistered helper rejects the old closure.
Mixed-case sealed/confirmation/ORIGINAL, reports and incoming config paths
reject before a payload open. A combined declared first-read/rescan limit
rejects before any code payload read.

All six legal ordered triplets produce the exact complete configured set with
Stage1 null and no evaluation call. REPLAY preserves the original pure v2
receipt hash and separate parent annotations. Reverse legacy order and an
A1-before-B1 set with requested Stage1 retain three candidates and REPLAY but
report `IMPLEMENTATION_BLOCKED`, without opening an existing malformed Stage1
manifest. For the supported legacy order, a reserved nested Stage1 capture
reference rejects before that payload opens. The authored suite additionally
executes the actual supported legacy Stage1 projection after prediction hashes
exist; no new configured source adapter is inferred from a pure Stage1 v2 API.

Adding code during actual preparation rejects at the post-fit membership scan
with no new REPLAY. Expiring the shared context inside the actual A1 numeric
core returns runtime-blocked with no candidates or REPLAY. A second invocation
that expires after reusing an existing immutable REPLAY clears its result but
retains the earlier artifact byte-for-byte, because it does not own that file.
The authored native publication-expiry test separately covers newly owned link
cleanup. All result authority fields checked remain false.

The reviewer loaded the archived parent module from the exact base into a
separate module and used fresh independent fixture workspaces for each version.
Complete v1 and v2 results **and physical REPLAY bytes** match the new parent.
Their independently recomputed result digests are, respectively,
`0c5784ca813904a46bda84881660ced71f7f48be0da79562e33ebbe8588cc11a`
and `21fef55970f5bb42ff50a549ae8ea990f18f6cc44d4acabcf778f7d196bfc1cc`.

### Scope limits retained

The reviewed transport uses one parent context capped at 2GiB and at most the
remaining 300 seconds. The source phase separately caps first reads plus its
first rescan at 16MiB; profile/config/file/registry limits remain
256KiB/64KiB/4MiB/256 entries. Further reads and REPLAY verification are charged
to the same global context. Membership enumeration, JSON parsing, legacy model
calls and hashing retain cooperative boundaries; no process-preemption or
atomic hostile-filesystem snapshot is established.

Consumed source consistency and declared readiness do not authenticate an
issuer, historical availability, loaded Python/native execution, a persistent
campaign budget/slot/exposure ledger, trusted pre-reveal freezing or
confirmation consumption. The pure ledger is not upgraded to trusted durable
state. Full configured source-bound Stage1 v2 integration remains absent;
unsupported sets must retain the reviewed implementation block until that
adapter is separately reviewed. No real-data science, calibration, improvement,
winner, official issuance, production authority or Master Goal completion was
established. A new complete runtime freeze, exact-head Linux CI and fresh-main
integration remain separate coordinator gates.

## Independent capability-metadata repair review (reviewer-owned)

**Bounded metadata review PASS** at
`dd746eb619bcdb5d9d764480152d03c9e244bba3`, parent
`1bd8f9557e683e5754be678786e459e5ccf267f4`. No blocking finding remains.
This section reviews only the later capability-description repair, without
altering the earlier exact-source review or granting new execution authority.

The runtime Git blob is
`src/research_model_adapter.py:bb49760d41ff575354a190f859744be462089ddd`.
Related reviewed blobs are tests
`da4c64a8f43679f469973f5b3db211481b0b723b` and
`3b76fb0150477116419ae993d2c4b333f9ba13c7`, and pure v2 spec
`6c0b59c558b56100634801b8bec5beed233cbcf8`.
Independent byte comparison confirms that the only runtime change is replacing
the two stale missing-parent/registry strings with
`CONFIGURED_STAGE1_SOURCE_PARENT_NOT_CONNECTED`. Parent dispatch, the existing
Stage1 source adapter and the pure Stage1 evaluator are byte-identical to the
parent commit. The remaining trusted campaign, pre-reveal consumption and model
comparison/winner-selection blockers are preserved in exact order.

Fresh native Windows verification used the runtime named above, `-B -X utf8`,
and the same standard-input unittest runner with modules
`test_research_model_adapter` and `test_research_pdca_adapter`:
**62 methods, 61 PASS and one existing POSIX skip**, in 13.299s. The v1 complete
fixture receipt, all five v1 function bodies and the fixed v1 registry still
pass their historical checks. `git diff --check dd746eb^ dd746eb` also passes.

`python -B -X utf8 ..\candidate-metadata-review-probes-20261025.py .` passed
**20 independent assertions**. Its local external SHA-256 is
`408a2818fcc05ef22ee2a53f2e1b3b938fdbb973047cfd861ecf3d5c731e7cbe`.
The reviewer loaded the archived pure module from the exact parent commit and
compared complete old/new success and insufficiency results. Replacing only
the old blocker list and recomputing that receipt's own hash makes each old
result exactly equal to the new one. Successful model and prediction artifacts
are identical; every checked authority flag remains false.

An actual temporary v3 workspace first published the old result, then the new
one. The old physical REPLAY stayed byte-for-byte intact while the new
content-bound result received a different immutable path; both files coexist.
A source-backed uniform/B1/A1 case with a requested existing malformed Stage1
manifest still returns `IMPLEMENTATION_BLOCKED` without opening that manifest,
retains the exact complete ordered candidate set and reports NEED_MORE_DATA.
There is no new evaluation read, fallback, reorder or parent-side resealing.

The new tag describes the remaining configured source-to-parent Stage1 v2 gap.
It does not deny the existing exact-order legacy Stage1 path, the pure Stage1
v2 evaluator or request-v3 source preparation. Source-layer API availability
alone will not remove this connection blocker. Trusted persistent campaign,
source/runner/pre-reveal authority, scientific comparison and production remain
unimplemented or unauthorized as previously recorded. This review makes no
claim about the separately prepared new cycle/freeze or exact-head CI. The
reviewer's only tracked change is this section; concurrent coordinator freeze
files were neither edited nor included in the review commit.

## Independent diagnostic-metadata repair review (reviewer-owned)

**Bounded metadata review PASS** at
`10b9519f5de63a97bff9be44ba23c5b2ffcf7784`, compared with
`06a8cc39b848fac513272b3e1fbdb24ebfdc3b70`. No blocking finding remains.
The only runtime delta removes the stale
`HB_A1_THREE_SLOT_PARENT_DISPATCH_NOT_IMPLEMENTED` item. Both remaining tags,
`TRAIN_ONLY_ABLATION_PARENT_DISPATCH_NOT_IMPLEMENTED` and
`SOURCE_BOUND_CALIBRATION_PARENT_DISPATCH_NOT_IMPLEMENTED`, remain accurate and
are checked as an exact ordered list. Spec wording now distinguishes existing
source-bound three-slot preparation from those unconnected diagnostic paths.

Reviewed Git blobs: module
`src/models/feature_candidate_diagnostics.py:60017d93e2bdae28ea5a615546135acaca34dfbf`,
test `bf9da7f70058eacad64551437b5cee86b7daa214`, and spec
`de18c6680db013bbce76ebac81fdaa3b3ab2e957`.

Fresh native command, using the runtime named above:
`python -B -X utf8 -m unittest discover -s tests -p test_feature_candidate_diagnostics.py -v`:
**22 tests PASS**, no skips, 0.141s. `git diff --check 06a8cc3 10b9519` passes.
`python -B -X utf8 ..\diagnostic-metadata-review-probes-20261025.py .` passes
**31 independent assertions** across six complete old/new result pairs:
ordinary, all-zero probabilities, all-one probabilities, positive-only, zero
rows and unequal per-night cohort sizes. Local external probe SHA-256:
`523e9be399f8841b05c70ba630953bb968b18299d18855ea48dcade3ab435327`.

The probe executes the archived module from the exact parent commit and the
new module on identical inputs. Excluding only `implementation_blockers` and
`diagnostic_sha256`, every output field is exactly equal, including all numeric
metrics, reliability bins, nulls, statuses, lineage and limitations. All six
authority flags remain false. Inputs and the prior returned receipt remain
unchanged; each new result has the expected fresh content hash. An independent
source-byte comparison confirms only the approved literal removal.

This does not add a fitter, evaluator, parent connection, calibration approval,
confirmation authority or artifact rewrite. Historical artifacts remain intact;
the reviewer's only tracked edit is this section. Concurrent coordinator
STATE/cycle/freeze work remains outside this review and commit. No current
cycle validity, new runtime freeze or Linux CI success is inferred from these
focused metadata checks.
