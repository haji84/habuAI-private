# Task7: automatic backend continuation after reviewed code merge

Read-only seam design. Inspected current pdca_bridge.execute_command/discovery: command source is pinned, HANDLED receipts are validated/reused, and changed code creates a new scientific run. Preserve those properties. A development result JSON alone does not resume execution, and changing a completed command's source would invalidate its recovery contract.

## Selected mechanism

Create a deterministic subordinate **owner-authored command issue** through the existing active Codex GitHub connector after the actual development PR merge is verified. Use the same `[HABU PDCA] YYYY-MM-DD` title format and existing event/poller executor. The authenticated connector actor is the owner haji84, so this preserves the current owner filter. Actions must not impersonate that author or bypass the filter; it persists development requests, while the approved active chat controller submits continuations automatically. No second owner prompt or GitHub button is needed.

The new issue is a transport child of the original command and Issue1642, not a new Goal, independent authorization or fresh scientific budget. Original issue/receipt/run remain immutable and HANDLED as appropriate. A newly merged code version runs in a new manifest linked to the same root operation and cumulative ledger.

This needs a small explicit Task7 integration in the shared bridge: recognize a typed continuation reference, verify its reviewed source/parent/result/budget authority, and claim the continuation before running. Merely creating another ordinary issue would reset budget and lose lineage; that is insufficient. Do not create continuation issues until this handler is actually on reviewed main. Current Actions executes current deployed code, not the controller's unmerged local implementation.

## Fixed operation contract

`continue_backend(root_command_id, development_job_id, verified_result_ref)` is a fixed approved controller operation, not a model-supplied tool name or command string. It reads the durable job result and directly verifies actual GitHub facts before creating anything.

ContinuationIntent v1 contains:

- canonical master `haji84/AI-#1642`, repository, root command ID/issue, parent command/run ID and evaluated operational night;
- development job/request hash, completed attempt ID, result artifact path/hash, actual PR number and verified merged commit/tree;
- required reviewed source commit and inference/evaluation code closure, protocol/policy/input lineage, fixed reason/requirements addressed;
- root budget ledger reference, expected previous ledger event/hash, existing cumulative scientific seconds/rounds/candidate identities and development strategy/attempt consumption;
- continuation sequence and stable operation_id = hash(root command, job request, accepted result hash, continuation sequence); no workflow-run ID in this deduplication identity;
- allowed next stage(s), prerequisites and expiry/limits where applicable. Candidate selection/freeze/reveal state is inherited and cannot be reset by code merge.

Persist this intent through the existing verified controller/job record before attempting issue creation. Put only the typed intent reference/hash plus human-readable linkage in the issue body; body text is data, never code. The bridge validates the referenced durable record and actual source relation, not a `continuation=true`, PASS field or arbitrary URL. Use a versioned unambiguous machine block; reject malformed/multiple blocks and later command-body edits against the receipt hash.

## Source binding and merge races

Controller first fetches actual PR state/head/merge facts, checks exact accepted-result content and applicable CI/review, and observes default-branch source. Do not treat 'merge requested' or a returned local candidate SHA as deployed code.

At bridge claim, compare actual resolved default source to the intent's required source. Preferred strict rule: exact SHA match. If main advanced, pause this child before computation. Controller may reconcile the newer default commit by verifying ancestry and exact relevant code/data/protocol/policy closure and mint a new intent revision under the same operation/budget; do not silently execute arbitrary newer code or read an issue-provided checkout ref. If a relevant closure changed, require the corresponding result/review/CI verification and new scientific identity. A conservative mismatch blocker is preferable to changing the pin.

Once accepted, store source in the new child's ordinary receipt and retain its pin across retries. Backend can read the linked prior run evidence as evidence only; it cannot reuse prior-code stage outputs as a verified checkpoint under a new code identity unless an explicit compatible artifact contract allows it. All consumed references remain hashed and protected history unchanged.

## Two budget classes, neither reset by a child

**Scientific improvement campaign:** maximum three preregistered selectable candidate recipes and two improvement rounds, with the existing300-second scientific budget carried cumulatively across the root command's continuations. Record recipe identities across all versions so altered code/features cannot smuggle in a fourth candidate. Charge actual fit/research/evaluation work, failed strategies and retries. Before launch atomically reserve only remaining allowance; pass that value to the parent and verify final actual usage. Current bridge hardcodes SCIENTIFIC_BUDGET and per-run ledger; Task7 must integrate root-budget accounting explicitly. Reject/stop if no allowance remains; a child cannot be a new300-second command disguised as a retry.

**Master implementation-completeness jobs:** building missing bounded adapters/tests/CI under the already authorized Master is engineering work, not automatically one of the two scientific hypothesis rounds or one of three selectable models. Give it a separate durable job/attempt/cost/time/path scope. It still has finite approved limits and failure-strategy history; code-version changes or new child issues cannot reset an exhausted implementation attempt budget. A mere declaration 'implementation job' cannot exempt actual candidate fitting/selection from scientific accounting.

Tests/CI and infrastructure wait time are recorded separately from scientific runtime; do not debit arbitrary queue wait as model compute or erase compute because a runner died. A continuation following an implementation job may run the newly available science if the root has allowance. If the original root's science budget is genuinely exhausted, emit BUDGET_EXHAUSTED with its remaining conditions. Do not implicitly expand limits just to preserve a desired outcome. Further bounded Master engineering can continue where already authorized, but not silently renew the same scientific campaign.

## Durable issue creation and execution idempotency

Issue creation has no atomic client idempotency key. Implement intent/reconciliation, not a claim of exactly-once creation:

1. Persist CREATE_PENDING with operation_id, immutable intent hash and expected previous root/job ledger state.
2. Fetch existing owner-authored child issues and stored child reference matching the exact operation marker and intent; reconcile before each retry, including after a network timeout.
3. If absent, create issue using the connector; persist actual returned issue number/URL and CREATED. If response is ambiguous, refetch before creating again.
4. Claim one canonical issue for the operation in the durable continuation ledger using the existing single-writer/CAS publication discipline. If duplicate issues exist, select a deterministic canonical one and mark the rest duplicate-handled without running science. The winner must be fixed before any irreversible/scientific execution; do not rely on a comment scan alone to serialize two controllers.
5. Shared bridge executor atomically verifies operation ownership/root budget lease and binds child receipt. Ordinary event/poller duplicate delivery then uses existing Task5 deduplication.
6. Controller follows the actual child run/result, records RETURNED with verified child source/run/artifact hashes and propagates remaining requirements to the root command. It continues the bounded loop without waiting for another owner instruction.

A root budget/job ledger must be durable across fresh runners. Extend existing report-only transport state under an explicit allowed reports path, with expected-ref/direct-parent conflict detection; no new permissions or separate service. Validate root/parent provenance and lease expiration. Stale controller claim cannot overwrite a newer result. Failed publication cannot become HANDLED just because science completed. Task5 bundle hashes/HANDLED status prove consistency/transport completion, not independent scientific authenticity or promotion authority.

## Minimal implementation seam

Add the versioned continuation intent/ledger validator and fixed controller operation to Task7's development_handoff/controller module. Narrow parent integrations in pdca_bridge: authorize existing owner command first; resolve trusted continuation reference; validate source/parent/result; claim operation/budget; run existing command with remaining allowance; append usage/result. No forked executor or second scientific pipeline. Add a parent-orchestrator budget/context parameter only if needed to preserve run-manifest root linkage; explicitly version the result contract and maintain ordinary root-command behavior.

Normal commands without a continuation marker remain as Task5 implements. Marked commands with an absent/unsupported/malformed contract fail clearly; they must not fall through into an ordinary fresh-budget execution. Current bridge's source pin and existing HANDLED receipts are never rewritten to enable continuation.

## Tests and live acceptance

Contract tests: wrong root/master/repository, bot-authored issue, tampered intent/result, unmerged PR, wrong merge tree, newer unrelated/changed default source, ambiguous multiple markers and edited child body fail before model execution. Valid owner child runs exactly the reviewed source and records new run ID plus immutable parent linkage.

Recovery tests: interruption before creation, after remote creation before local receipt, after claim before science, after science before publication and after HANDLED before root update; reconcile to one canonical execution and cumulative usage. Two concurrent issue submissions/controllers cannot double-reserve a scientific round or reset failed strategy budget. Existing event/poller duplicate protection still passes.

Budget tests: parent used200seconds -> child gets at most100; exhausted root -> no scientific restart; second round cannot spawn a third; fourth selectable recipe rejected; bounded adapter-implementation job does not itself count as a model candidate, while its actual scientific fits still do. Reusing code versions/operation IDs cannot bypass either ledger.

Live active-session test after handler merge: an actual owner command produces a useful bounded development request; controller executes its approved branch/test/independent review/PR/CI path; obtains actual merged-default facts; persists intent; creates the owner-authored child via existing connector; existing event/poller invokes reviewed backend; controller verifies new source/run linkage and returns combined result to the original command without another user message. When data is insufficient, expected result is authentic BLOCKED/NEED_MORE_DATA, not synthetic production acceptance. Exercise one interrupted/reconciled attempt from a clean workspace, observing no second scientific execution or budget reset.

Automatic wake-up after the entire Work session ends remains a separate unproven liveness capability. This mechanism supplies durable restart correctness and automatic continuation in the already active authorized chat; it does not claim Actions can restart that chat.
