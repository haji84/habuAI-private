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
