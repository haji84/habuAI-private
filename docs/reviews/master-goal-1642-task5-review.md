# Independent Task 5 review

Scope: implementation `d5ff609` plus final blocker-propagation delta `a92da67`; full Task 5 brief/integration design, repository AGENTS.md and normative specification; shared workflows, bridge helpers, CLI/orchestrator integration and E2E tests. Read-only review, temporary local-bare-Git probes, no implementation edits or nested agents. No real GitHub API writes or Actions execution.

**Spec compliance: changes required. Code quality/security/integrity: changes required.** No Critical execution-boundary bypass identified. Three Important findings and one Minor hardening observation follow. The final `a92da67` delta correctly retains specific recovery-cap/source errors without converting a crashed worker into scientific success.

## Important 1 — HANDLED receipts can override the verified scientific result

`src/pdca_bridge.py:520–528` and `347–358` at `a92da67`.

Completed-run recovery verifies the run bundle and authoritative manifest, but the HANDLED path then returns the command receipt without binding its scientific status, completion flag or result digest to that verified result. Discovery is even weaker: it suppresses any receipt having state HANDLED and the matching command object, regardless of whether durable run/result evidence exists. The design requires a valid terminal receipt, not a self-declared terminal state.

Reproduced with the existing real-bare-Git fixture: execute issue 1 to a legitimate BLOCKED, completed=false, HANDLED receipt. Fast-forward its command branch changing only `scientific_status` to PASS, `completed` to true and `result_sha256` to 64 zeros. Leave the actual run/bundle unchanged. Duplicate `execute_command` restores/verifies the true BLOCKED result but returns PASS/true and the bogus digest. Separately, `discover_commands` with only `{state: HANDLED, command: matching_command}` returns no pending command.

Required repair: validate terminal receipt structure and bind source/run/result/aggregate fields to the authoritative durable run before returning it or suppressing discovery. Reject or explicitly reconcile inconsistent metadata; never report receipt PASS over manifest BLOCKED/FAIL. Incomplete/corrupt terminal claims must remain visible for recovery and cannot reset scientific budget. Add regressions for altered status/completion/digest and a skeletal HANDLED receipt, alongside unchanged legitimate duplicate reuse.

## Important 2 — Subsequent report publication preserves non-report changes from its base tree

`src/pdca_bridge.py:125–150`, especially `base = expected_previous or source_commit` and `read-tree(base)`.

The new-file allowlist protects only the paths supplied to this call. Once a report branch exists, its entire current tree becomes the isolated-index base without checking that non-report paths still match the pinned trusted source. An external fast-forward made before the expected-head check can add/modify source or workflow files; the next bridge publication silently carries those files into the report PR. CAS protects a concurrent divergent push, but does not establish that the accepted base is report-only.

Reproduced using real Git commits: publish an allowed receipt to `pdca/probe`; manually fast-forward that branch with `src/injected.py`; publish another allowed receipt using that current head as expected_previous. Publication succeeds and `transport.read(new_commit, 'src/injected.py')` returns the injected code. The ordinary worktree remained isolated. No code from this branch was executed in the probe—the separate pinned-source execution boundary remains effective—but the generated report PR is no longer limited to report paths as promised.

Required repair: before extending an existing report branch, verify its non-report tree against the pinned source (including file modes/type changes and deletions), or construct a trusted-source tree carrying only explicitly validated report artifacts. Reject unexpected outside changes instead of republishing them under the bridge's report-only description. Add a regression for source/workflow additions/modifications on a previous report head while preserving normal report-generation recovery and non-force CAS.

## Important 3 — One malformed receipt aborts discovery for every later command

`src/pdca_bridge.py:347–359`; `scripts/pdca_bridge.py:21–29`.

The discovery loop catches invalid command fields, but invokes `receipt_lookup` outside that guard. The actual callback parses remote JSON directly. One malformed/missing receipt artifact (or a non-object JSON value subsequently used with `.get`) aborts the entire discovery job before later eligible issues are considered. This defeats the intended recoverable queue/fairness behavior; the same corrupt oldest command can stop each scheduled poll indefinitely.

A focused two-issue probe made receipt lookup raise ValueError for issue 1 and return no receipt for issue 2. `discover_commands` raised rather than returning issue 2. This is distinct from the existing fairness test, which covers only well-formed RETRYABLE records.

Required repair: isolate per-command receipt read/parse/validation failures, retain a concrete recovery diagnostic for the affected command, and continue considering other eligible commands. Do not treat corruption as HANDLED or discard its budget ledger. Add malformed JSON/non-object/missing-artifact cases with a later healthy issue and assert continued discovery without scientific execution/reset of the corrupt command.

## Minor — Restore caps do not bound blob materialization

`src/pdca_bridge.py:98–104, 233–254`.

`GitTransport.read` materializes all `git show` output before restore checks actual byte length. Manifest/control-record reads are likewise unbounded until after reading. Consequently the 5MiB/20MiB limits constrain accepted artifacts, not memory consumed reading a corrupted oversized remote blob whose declared size is small. Restore still rejects the mismatch before writing, so this is not an acceptance bypass.

Recommended hardening: inspect committed blob type/size (`git cat-file -s` or equivalent) and enforce a caller-supplied maximum before loading report/control bytes, or use a bounded streaming reader. Keep trusted source reconstruction's separate larger-input contract explicit. This observation comes from code inspection; no memory-exhaustion experiment was performed.

## Checks and preserved boundaries

Six selected existing E2E tests passed independently (6.45 seconds): acknowledged-checkpoint hard exit and fresh restore; compact restore/current exit2; two-command convergence and interrupted comment publication; stale-PASS crash rejection; exhausted shared reservation across issues; and specific publication-limit reason propagation. Additional probes reproduced all three Important findings above. The implementer/parent's 187-test full-suite result and historical all-nine-stage BLOCKED dry-run were read, not repeated as a full suite here.

The two workflows converge on one reusable executor with one job-level concurrency group, unchanged contents/issues/pull-requests permissions and no caller/child lock deadlock. The helper refetches owner authorization, validates the calendar date and passes structured arguments; issue text is not evaluated as code. Actual execution is reconstructed from a trusted default-branch ancestor, never a report branch. Source reconstruction rejects symlinks/submodules; restored generated paths are run-prefixed and hash/size checked; checkpoint and finalization chains are verified; supplemental executable/config source is rejected. Publication uses a separate index and non-force pushes. The missing base-tree check above does not negate these execution protections.

The runtime change records actual Python and the existing analysis-profile dependency versions while removing kernel/incidental-package noise. Requirements themselves remain unchanged. Different actual dependency versions create different identities; unfinished incompatible-runtime recovery is explicitly blocked instead of resetting budget. The fixed 300-second cumulative ledger, bounded reservations, lease recovery and synchronous acknowledged checkpoint publication make the local hard-kill evidence substantive. Remote comment creation remains practically recoverable, not transactionally exactly-once.

Real Actions/reusable-workflow execution, exact-head remote CI and live owner-command/report/PR/comment recovery remain separate acceptance work. These local findings must be repaired/reviewed first; no full Master, scientific or production activation completion is claimed.
