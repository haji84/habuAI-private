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
