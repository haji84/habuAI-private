# Task 5 repair-round 1 independent re-review

Reviewed exact commit `75ca7de61f89160d0fe504ab28b35771a0889cbc` against `a92da67`, using an isolated archive of that commit so later Task6a edits could not affect execution evidence. Scope: prior three Important findings, bounded-read Minor, actual CLI discovery wiring, and command/scientific source-binding regression. Read updated implementation report. No implementation edits or nested agents.

**Spec compliance: one narrow repair remains. Code quality/security/integrity: changes required on shared completed-run reuse.** Findings 1 and 3 and the bounded-read Minor are ADDRESSED. Finding 2 is PARTIALLY ADDRESSED. No Critical report-code execution bypass found.

| Prior finding | Disposition | Evidence |
|---|---|---|
| HANDLED receipt contradicts verified result | ADDRESSED | Dedicated verifier restores committed bundle, verifies checkpoint/result and matches scientific status, boolean completion, result hash, ledger, budget and identity. Duplicate execution calls it before returning. |
| Mixed prior report tree carried into report publication | PARTIALLY ADDRESSED | `publish` and HANDLED validation now reject differences outside allowed regular report artifacts. New-command reuse of a COMPUTED shared run still omits this check before advertising that run's PR; reproduction below. |
| One malformed receipt aborts discovery | ADDRESSED | Per-command read/shape/validation failures become diagnostic entries and are queued behind healthy work without changing ledgers. Actual discovery CLI invokes the real authoritative verifier, writes discovery diagnostics, and the poller uploads them. |
| Blob caps checked after materialization | ADDRESSED | Committed report/control blob size is checked before `git show`; declared per-file/count/aggregate bundle limits are checked before loading file bodies. Trusted source reads retain their separate larger-input contract. |

## Remaining Important — New command can advertise a mixed completed run branch

`src/pdca_bridge.py:605–621, 673–685` at `75ca7de`.

The branch-integrity check is correctly applied when extending a report branch and when revalidating an existing HANDLED command. A distinct new issue sharing an already-COMPUTED scientific run follows a different path: it restores the existing run head and verifies its manifest, then creates/reuses that branch's PR, comments and marks the new command HANDLED. No `assert_report_tree(run_head, scientific_source)` occurs along that path. Because this path does not append to the run branch, the guard inside `publish` never runs for it.

Reproduced with actual local bare Git and the real executor:

1. Execute issue 1 to legitimate BLOCKED/HANDLED, producing its COMPUTED run branch.
2. Externally fast-forward that run branch with `src/injected.py`, leaving its scientific bundle/manifest unchanged.
3. Execute issue 2 with the identical scientific inputs.
4. Issue 2 returns HANDLED and points to the shared run/report branch, which still contains the injected source addition.

The restored computation remains pinned to trusted source; no report code was executed. The remaining defect is the report-only publication/advertisement boundary, the same prior Important finding rather than a new broad scope item.

Required bounded repair: after resolving the shared run's scientific source and before any restore/reuse or PR/comment publication, verify the entire run head against that source. Putting the same guard at the trusted restore boundary can also protect other callers. Add the new-issue/shared-COMPUTED mixed-head regression; preserve legitimate README-only source sharing and normal unchanged HANDLED reuse. Do not rewrite/discard the external branch or rerun science to conceal the conflict.

## Substantive validation and preserved behavior

Six selected committed regressions passed independently (12.20 seconds): handled-result tamper rejection, mixed-tree publication refusal, authoritative handled discovery, pre-materialization blob cap, README-only source sharing/duplicate reuse, and malformed/missing receipt queue isolation.

Additionally executed the actual `scripts/pdca_bridge.py` discovery `main()` against the real local-bare-Git fixture, using the actual `verify_handled_receipt` and all restore/checkpoint/result validators. Only the GitHub issue/default-source API was stubbed; no validator PASS was mocked. A valid issue-1 HANDLED receipt produced `issue=2`, pending `[2]`, and no failures. Altering issue 1's status/completion/result hash produced `issue=2`, pending `[2,1]`, and a concrete authoritative-result mismatch in `artifacts/bridge/discovery.json`. Thus the helper behavior is wired into the real entrypoint rather than merely tested in isolation.

The separate `command_source_commit` and scientific `source_commit` are correctly used for their respective branch bases in the reviewed paths. The README-only regression confirms a newer command branch can retain its trusted newer base while sharing an older equivalent scientific run; duplicate receipt validation still succeeds. This separation should remain intact in the narrow remaining repair.

The reported 195-test suite is implementer/parent evidence, not a full suite repeated here. No new historical computation, live Actions, GitHub publication or scientific/production completion is claimed. All earlier runtime/data/executor/trust limitations remain.
