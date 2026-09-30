# Task 5 implementation report

Status: bounded bridge implementation ready for independent review. Whole Master Goal #1642 remains incomplete. No remote publication, Actions run, issue comment, merge, or production activation was performed by this implementer.

## Local commits and owned paths

- `d5ff609`: shared durable bridge, workflow integration, checkpoint hook/runtime identity, and 21 E2E tests.
- `a92da67d772e78929551066928a6c0e98702a891`: preserve specific recovery publication blockers; additional regression.
- Exactly seven owned paths: `.github/workflows/pdca-command.yml`, `.github/workflows/pdca-command-poller.yml`, `src/pdca_bridge.py`, `scripts/pdca_bridge.py`, `src/master_orchestrator.py`, `scripts/run_pdca.py`, `tests/test_master_e2e.py`.
- Parent docs, evidence, intake, requirements, schemas, raw files and ORIGINAL were not staged or changed by this implementer. Owned paths are clean after commits.

## Implemented contract

The existing issue workflow is now reusable through `workflow_call(issue_number)`. Poller discovers commands and delegates to the same executor. Executor uses the single job concurrency group `habu-pdca-executor`, no cancellation; callers do not hold that group. Existing contents/issues/pull-requests permissions remain unchanged. Runtime installation uses the already declared `requirements-analysis.txt` unchanged. It refetches the issue, enforces open owner issue/exact prefix/one real calendar date, and passes structured API/argv values rather than evaluating command text.

Scientific execution is reconstructed from a resolved trusted default-branch commit; an existing command stays pinned to its receipt and trusted ancestry is checked. Report branches never supply executable code. Command identity binds repository/issue/night/text hash, run identity binds full inputs/code/policy/actual Python and scientific dependency versions, and attempt identity carries reservation/deadline/lease. New issue with changed inputs creates a new run; identical scientific identity shares one run branch and PR. Kernel/incidental installed tools no longer perturb identity. Actual numpy, pandas, pyarrow, scipy and scikit-learn versions are included (missing versions are explicit).

`inspect_run_identity(root, night, execution_root=...)` exports the shared scientific identity algorithm. `run_master` now accepts optional `checkpoint_callback`, cumulative `budget_floor`, and timezone-aware `attempt_deadline`; existing direct API tests retain bounded custom budget scenarios. The fixed bridge invokes budget=300 only; master policy remains at most two rounds and three candidates. The bridge reserves at most 240 seconds per attempt and at most the remaining cumulative allowance. Receipt publication consumes part of that reserved window, never extends it. Lost attempts conservatively consume their whole reservation. Surviving checkpoints retain measured elapsed time; expired killed-active-stage recovery charges only through the recorded hard deadline, rather than indefinite transport downtime. Publication overhead during execution may be conservatively charged. Transport-only completion retries do not rerun science.

Control records use `pdca/command-<command_id>` and `pdca/run-<run_id>` branches, under `reports/pdca/<night>/bridge/`. Publication uses an isolated temporary git index, explicit allowed paths, expected-head checks and non-force fast-forward pushes. Synchronous callbacks publish every validated checkpoint generation, including committed stage output hashes. The publisher verifies checkpoint/checksum consistency and rereads the generation before acknowledgement. Compact manifests bind source SHA, complete inventory, scientific identity, file hashes/sizes and final result chain. Source snapshots are reconstructed from the pinned commit; bounded supplemental data may be carried explicitly, never supplemental executable/config code. No recursive staging or wholesale snapshot publication.

Recovery caps: 2,000 files, 20MiB total, 5MiB per file, including control publication. Cap/source failures expose explicit recovery BLOCKED reasons in a current FAIL/retryable execution receipt. No truncation or fake success. A successful local result is accepted only with current unique attempt output, matching identity/night, valid all-nine-stage manifest and finalization/checkpoint chain, and compatible exit status. Exit2 with current BLOCKED/FAIL is valid science reporting; crash/signal/missing output is execution FAIL. Old compatibility PASS cannot be reused.

Scientific BLOCKED/FAIL results are persisted before report PR/comment/handled marking. PR lookup and marked-comment upsert make partial publication recoverable. `pdca-handled` is explicitly distinct from scientific completion; neither command nor Master issue is closed. Discovery ignores stale processing labels and rotates least-recently-attempted commands so a persistent failure does not starve later work. Unavailable remote publication remains retryable, with last acknowledged generation authoritative.

## TDD and verification

- Initial missing-module/interface tests RED before implementation; core transport tests GREEN.
- Callback, budget-floor and forbidden supplemental code tests RED before integration; then GREEN.
- Shared-workflow test RED against original duplicate workflows; then GREEN after reusable executor.
- Timeout-after-publication and publication-cap regressions both RED, then GREEN.
- Omitted recovery inventory regression RED, then GREEN with inventory/identity/result binding.
- Queue starvation regression RED, then GREEN with least-recent attempt discovery.
- Specific publication-limit reason regression RED (only generic exit75 was retained), then GREEN.
- Final full command: `python -m unittest discover -s tests` — **187 tests passed**, 17.644s, including 22 Task5 E2E tests.
- Scoped `git diff --cached --check` passed before both commits; Python bridge compilation passed.
- Transport verification uses real commits/fetch/push with a local bare repository and separate fresh restore roots. It includes an actual `os._exit(77)` immediately after acknowledged stage publication, then fresh-runner restore and continued cumulative budget.
- Tests also cover two command issues converging on one run/PR, injected comment failure, changed source versus pinned old command, expired lost-attempt allowance shared across issues, path traversal/hash corruption, cap rejection, stale PASS, current exit2, immutable protected bytes, and isolated Champion promote/infer/change/rollback while production remains blocked.

## Historical September 28 evidence

Final isolated copy run at the final implementation source:

- Run `911a980f54fc7806649f72870b0f31416e85a5444ec9202d8663f70641539f7d`; exit 2; overall **BLOCKED**, completed=False; all nine stages recorded.
- Copied exact inventory: 171 files, 72,909,935 bytes. All 45 raw/ORIGINAL protected files remain byte-identical in both original workspace and isolated copy.
- Operational scoring is PARTIAL: retrospective recovery only, no strict formal 100m±10min targets, no P1+, no validated held-out model evaluation.
- Four model/research/candidate stages are DATA_BLOCKED on missing audited `data/processed/model_learning.json`.
- Evidence audit remains NOT_VALIDATED; approved development executor and Task8 trusted production reproduction/activation remain IMPLEMENTATION_BLOCKED.
- Machine-readable evidence: `/workspace/scratch/fb45a4f31791/task-5-historical-result.json`; final attempt: `/workspace/scratch/fb45a4f31791/task-5-historical-final/final-attempt-september28.json`.

## Limitations and parent acceptance still required

1. Actual GitHub Actions/reusable-workflow execution, API publication, PR/comment recovery and live owner command have not been exercised here. Local bare Git and fake API tests are not remote acceptance. Parent must publish through its authorized API path, inspect exact-head CI, independently review, merge only if eligible, and perform live bridge acceptance afterward.
2. Local interpreter/runtime is CPython3.12.14, numpy2.3.5, pandas2.2.3, scipy1.17.0, scikit-learn1.8.0, pyarrow NOT_INSTALLED. Actions installs the existing pinned analysis profile. The difference is recorded honestly and produces different scientific IDs; an unfinished command cannot silently resume under a different runtime/reset budget. Remote pinned-profile CI remains necessary.
3. This workspace contains raw/prediction material outside its reconstructed local git index. The historical dry-run proves exact local computation/protection, not that these bytes already exist in a remote trusted source commit. Real recovery requires parent full-tree publication plus pinned inputs, or bounded explicitly included data. Missing large source inputs cannot be silently declared recoverable.
4. Recovery guarantees only last successfully pushed/verified checkpoint. Hard kill before acknowledgement loses that uncommitted generation. Remote unavailability can prevent publishing a failure too; no handled state is claimed then. Exhausted cumulative allowance remains explicit and cannot be reset through another issue/output root.
5. Remote comment creation has no transactional idempotency key. Serialization, query-before-create and marker-upsert provide practical retry recovery, not transactionally exactly-once messaging. Branch push is non-force and rejects normal concurrent divergence; independent review should assess remote mutation assumptions.
6. Source checkout is deliberately restricted to regular tracked files; symlink/submodule sources block recovery instead of executing them. Bundle limits are engineering limits, not scientific thresholds. Existing direct master API custom budgets are retained for explicit tests; production bridge budget stays fixed300.
7. Parent-owned status doc should say Task5 local foundation implemented/review pending, 187 tests pass, historical BLOCKED, remote CI/live bridge pending, scientific/data/trust follow-ons6–8 still required. No claim of complete Master or production Champion readiness.

## Independent review repair round 1

Commit: `75ca7de61f89160d0fe504ab28b35771a0889cbc`. Scoped to the existing bridge module/entrypoint, poller diagnostic upload, and E2E tests. No remote operations, dependency/permission changes, raw/ORIGINAL edits, or parent documentation staging.

All three Important findings from `task-5-review.md` were reproduced before repair:

1. A legitimate HANDLED/BLOCKED receipt modified to PASS/completed=true/bogus result digest was returned by duplicate execution. The regression failed RED. HANDLED now requires full durable bundle/checkpoint/result verification, trusted source/run bindings, and equality of status, boolean completion, result hash, budget ledger and identity. Discovery uses the same authoritative verifier; a skeletal terminal claim remains visible with a diagnostic. A valid unchanged duplicate still returns the prior result without science rerun.
2. An external fast-forward adding `src/injected.py` was retained in subsequent allowlisted receipt publication. The regression failed RED. Before extending a report branch, the full difference against its pinned source must contain only allowed regular report files. Outside additions/modifications/mode changes/deletions and deleted/nonregular report artifacts fail closed. The external branch is neither rewritten nor silently discarded.
3. Malformed receipt discovery now isolates per-command errors and records concrete FAIL diagnostics, retaining affected commands behind healthy work rather than treating them handled or resetting budgets. Missing-artifact/non-object/invalid-JSON and skeletal terminal claims have regressions. Discovery prints and uploads `artifacts/bridge/discovery.json`; permissions remain unchanged.

The review's Minor bounded-read hardening is also repaired: report/control `GitTransport.read` checks committed blob byte size with `git cat-file -s` before `git show`; declared aggregate bundle limits are checked before artifact materialization. A test confirms oversized report data never reaches `git show`, while trusted raw source reconstruction retains its distinct larger-input contract.

Preservation check: stricter branch validation exposed a legitimate case where a new default commit changes only an unconsumed README and shares the older scientific run. Receipts now record `command_source_commit` separately from scientific `source_commit`, keeping each branch's pinned base explicit. Existing receipts without this additive field default to their prior source binding. A RED→GREEN regression covers sharing and subsequent duplicate validation without relaxing report-only checks.

Final verification: `python -m unittest discover -s tests` — **195 tests passed**, 31.092 seconds, including 30 Task5 E2E tests. Scoped staged whitespace check and bridge Python compilation passed. Eight added review regressions preserve the prior hard-kill, fresh-runner, duplicate, budget and source-mutation coverage. Historical scientific findings above remain prior-round evidence; this integrity-only repair did not claim a new live run or scientific completion. Independent rereview and actual GitHub acceptance remain outstanding.

## Independent rereview repair round 2

Commit: `66ba37a0776c3161b317aecf1929f24bf61d43aa`. Exactly two paths: `src/pdca_bridge.py`, `tests/test_master_e2e.py`.

The new-issue shared-COMPUTED path could restore an existing run after an external fast-forward added source code, then advertise its mixed report branch. The exact local-bare-Git regression failed RED: issue1 completed legitimately; an external commit added `src/injected.py` to its run branch; issue2 then incorrectly became HANDLED. The repair places `assert_report_tree(bundle_commit, trusted_source_commit)` directly at the common `restore_bundle` boundary before any materialization. All restore/reuse callers now receive the same check, including new commands sharing completed runs. The regression verifies rejection before `ensure_pr`, no second comment or handled mark, and no mutation/discarding of the external branch. The separate command/scientific source binding remains intact.

Focused verification: `python -m unittest discover -s tests -p test_master_e2e.py` — **31 tests passed**, 32.005 seconds, including hard-kill recovery, fresh restore, shared runs, HANDLED binding, and unconsumed README/source-sharing preservation. Scoped staged whitespace check passed. The previous full suite at round1 remains 195 passed; the new regression brings the suite inventory to196 but a new full-suite run is not claimed. No remote operations or other implementation edits. Ready for narrow independent rereview; Task5 implementer is free and will make no further edits without a new assignment.
