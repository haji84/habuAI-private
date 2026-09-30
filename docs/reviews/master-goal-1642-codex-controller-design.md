# Review: existing PDCA Chat / Codex as bounded development controller

## Decision

**Allowed, and a better minimum fit to the canonical owner request than mandating the AI- JARVIS/Compass runtime.** Issue #1642 requires a bounded, evidence-backed development loop and one PDCA Chat command. It does not require a particular daemon, Compass Goal identifier, endpoint or builder implementation. The owner explicitly chose a long-running Work session and delegation to Codex. Existing authorized Codex execution plus the GitHub connector can implement that loop while Actions remains the existing scientific backend.

The earlier Task 7 wording made one proposed implementation a prerequisite. The AI- audit correctly found that implementation unavailable/mismatched; it did not establish that all authorized development execution was unavailable. Correct the normative specification and plan explicitly, preserving the audit as evidence about the rejected adapter. Do not silently pretend its live acceptance passed.

This is a design approval, not a claim that the controller, durable receipts, production authority or end-to-end recovery already exist. A chat agent's current ability to modify a branch is necessary but insufficient proof of the finished product.

## Authority and repository scope

Canonical authority remains the owner's request and Issue #1642. Child development jobs are subordinate records, not new independent Goals. Bind their scope to that canonical issue, the command receipt, repository, evidence and the authorized plan.

Habu AGENTS.md requires branches, tests, evidence and PRs, prohibits unreviewed direct-main data writes, protects Raw/ORIGINAL, preserves cutoff and scientific rules, and prohibits secrets in commits. The proposed controller follows those requirements. Existing autonomous authorization covers ordinary bounded implementation, verification and PR work already within this goal. It does not waive protected-branch rules or turn future arbitrary requests into unlimited merge/deployment authority. Production activation still requires its actual reviewed/persisted gates.

AI- AGENTS.md is relevant when editing that repository or invoking its runtime/capabilities. Merely referencing an issue hosted there or reading its implementation does not make its runtime architecture mandatory for changes in Habu. Its safety constraints should not be evaded if that runtime is used, but there is no need to invoke it here. The AI- audit's Compass identity and pnpm executor blockers are therefore inapplicable to this alternative. Do not copy or modify AI- code under this design.

## Minimal architecture

Preserve Chat -> owner GitHub issue -> existing event/poller -> Habu Actions -> existing Python parent. Add an explicit asynchronous development boundary to the same parent, not a second scientific pipeline:

1. Actions runs audit/scoring/evaluation/research and persists a typed development request when a supported evidence-backed code need exists.
2. This active PDCA Chat's Codex controller observes the bound run through the existing authenticated connector, validates the request and claims a bounded attempt durably.
3. Codex executes the authorized branch/implementation/tests/independent-review/PR loop using existing tools and Habu's Python verification profile. Model text supplies hypotheses and requirements, never executable shell/workflow instructions.
4. The controller reads actual GitHub commit, PR, check-run/workflow and review state for the exact candidate revision, records verified receipts, and returns the resulting candidate or rejection.
5. The existing backend consumes that result and runs the next validation round. A code change creates a new run identity bound to the parent run/job; it cannot resume old scientific artifacts as if the code were unchanged.
6. Promotion is a separate gated transition. Producing a development PR is not promotion, and merging code does not prove a model meets scientific gates.

The owner makes one request; the controller keeps working and observing results within that same authorized session. No manual 'copy this request to Codex', extra GitHub button or new owner command is part of the normal path.

## Typed contracts and authority boundaries

DevelopmentRequest includes schema/version, canonical master reference, command ID, parent run ID, request ID/hash, repository, immutable base commit, source/evidence/protocol hashes, requirement IDs, diagnosed failure, expected measurable behavior, nonempty allowed paths, protected paths, fixed verification-profile ID, acceptance criteria, risk class, budget/attempt/round limits, and expiry if applicable. Evidence must resolve to artifacts whose hashes match the trusted parent run. A missing scientific dataset produces a data request/blocker, not a fabricated implementation need.

ControllerClaim includes request hash, attempt ID, previous ledger state/hash, lease timestamps, controller-session reference and remaining cumulative budget. The controller identity/session reference is audit metadata; an arbitrary string naming Codex is not proof of authorization.

DevelopmentResult includes request and attempt IDs, exact base/head/tree and patch hashes, changed paths, local test evidence, independent verifier evidence, PR ID/head SHA, actual CI run/check IDs with head SHA/conclusion, risk decision, artifacts and resulting candidate ID or rejection reason. Include trusted verification-profile and workflow identity so an unrelated green workflow cannot satisfy the gate. Later changes to the PR head invalidate prior CI/review receipts unless freshly bound to the new revision.

The backend accepts only enumerated contract fields and known artifact paths. It must not execute commands, import arbitrary modules, evaluate expressions, or widen allowed paths from request prose. Verify actual changed paths against policy independently of the builder. No Raw/ORIGINAL/governance/security/workflow modifications are implicitly authorized by a routine model-improvement request; separately authorized implementation work retains its own explicit scope.

## Durable execution and recovery

Use the existing repository report/evidence persistence and connector; no new credentials, endpoint or Actions permission is necessary. Persist append-only state transitions with expected previous ledger hash/revision:

REQUESTED -> CLAIMED -> IMPLEMENTING -> VERIFYING -> PR_OPEN -> CI_PENDING -> VERIFIED/REJECTED/BLOCKED -> RETURNED.

Store bounded artifacts on deterministic job/attempt branches or established evidence branches, with links from the command receipt. Job identity derives from parent request hash and accepted scope. Before any external write, record intended operation ID and expected GitHub base/head; after interruption reconcile actual branch/PR/check state before retrying. Use deterministic branch identity and existing-PR lookup to avoid duplicate irreversible work. Never trust a stale lease as permission to overwrite a newer candidate or reset budgets.

A restarted controller must reconstruct from repository records, not conversation memory: fetch request/ledger, verify hashes and current remote head, reuse completed checks only for the exact revision, and continue at the first unfinished state. A pending CI wait is resumable without rerunning implementation. Compaction in the same session is handled by reading the same durable record. Raw/ORIGINAL before/after hashes and confirmation-label access history persist across attempts.

Concurrency must be real: if the available connector does not provide compare-and-swap for a mutable ledger, use immutable transition commits with one serialized publisher/branch reconciliation and reject divergent tips. A read-then-unconditional-write is not atomic simply because both operations use authenticated tools.

Budget applies to the whole job across controller/backend restarts, not each fresh session. Remote wait time and active execution should be recorded separately, with a declared retry bound. Exhaustion persists BLOCKED and required conditions; do not create a new request solely to reset the same failed strategy's budget.

## Active chat versus unattended execution

The current active Work session is the control plane. Actions can create requests, run scientific stages, persist receipts and await results; it does not acquire the ability to spawn this chat or invoke Codex merely by emitting JSON.

This architecture can satisfy the owner's one-command experience while the authorized chat controller remains active and demonstrably polls/continues. It can also support durable restart by an available controller. **It does not, by itself, prove autonomous wake-up after the Work session has ended or the platform has lost the agent.** Do not imply that GitHub events automatically restart this chat. If no already available authorized wake-up mechanism exists, report that specific unattended-resumption limitation; do not resurrect the JARVIS requirement or invent a new service.

No routine re-prompt is acceptable as the implemented normal path. Live acceptance must show the active controller consumes an actual backend request and returns a result without a second owner instruction. For unexpected controller loss, durable correctness can be proven separately from automatic liveness. If the master is claimed to include unattended recovery after complete session termination, that liveness gate remains open until an actual supported trigger is demonstrated. The canonical request's long-running Work session does not justify assuming an immortal session.

## Production trust using the existing connector

Existing authenticated GitHub reads can establish repository facts without expanding Actions permissions: exact commit/tree, expected CI workflow/check and head SHA, PR state, reviews, merge commit and default-branch ancestry. The controller must obtain those facts directly rather than accepting caller-supplied URLs/statuses. Record source response identities and observation time with the evidence bundle.

Independent reproduction must load pinned model, fold predictions/labels, dataset, protocol and policy and recompute scientific metrics/gates in a clean verifier context. A second agent repeating a candidate's summary is not independent reproduction. The verifier must have distinct execution/evidence and inspect raw artifacts; independent credentials are not automatically necessary, but shared credentials cannot by themselves establish independence. Synthetic E2E evidence proves mechanics only.

The fixed trusted production entrypoint should accept only a promotion event persisted through the authorized reviewed repository path, tied to exact reproduced artifacts and verified CI/review/main facts. An authenticated connector write alone is not scientific approval; anyone able to write ordinary report data must not thereby gain promotion authority. Do not expose a `trusted=true` input, caller-supplied runner flag, or importable function argument that bypasses production verification. If Actions cannot itself query all facts under its existing token, controller verification may prepare a reviewed, committed evidence envelope; production trusts the protected repository/event path, not the envelope's self-asserted authenticity.

CAS Champion transition verifies expected prior event/current model and candidate evidence. Use actual activation/merge observation time, never backdate an event to candidate evaluation time. Next prediction must execute the selected model's verified inference adapter and bind its exact output. Earlier ORIGINAL bytes remain unchanged.

## Concrete acceptance path

1. Unit/contract tests reject out-of-scope paths, executable command fields, altered evidence, stale heads, duplicate claims, forged CI summaries, unrelated green checks and premature development completion.
2. Local integration uses a fake connector transport to drive every state and interruption boundary, but remains explicitly synthetic.
3. Live in this authorized session: one owner command reaches Actions; a real evidence-backed bounded code request is persisted; controller claims it, performs a useful scoped implementation on a branch, tests it, obtains independent review, opens PR, observes actual exact-head CI, persists result and resumes the backend. Do not manufacture a production scientific improvement merely to make this exercise green. If only a test fixture is available, label live workflow mechanics as fixture acceptance, with real-data validation still blocked.
4. Restart the controller-side processing from a clean local workspace using durable records while the same authorization is available. Demonstrate no second PR, no duplicate code application, no budget reset, and correct CI reconciliation.
5. Verify actual reviewed main/promotion chain where scientifically eligible. Otherwise prove rejection/NEED_MORE_DATA on real evidence and retain the genuine scientific gate; do not promote to demonstrate plumbing.
6. Record whether the restart was automatic platform wake-up or deliberately exercised recovery. They prove different properties.

## Required specification correction

Replace Task 7's mandatory AI- Goal/job runtime dependency with: 'Use the current owner-authorized PDCA Chat/Codex controller and existing GitHub connector as the bounded development executor; persist and verify typed request/attempt/result contracts and resume the existing backend. Optional other executors require their own capability audit. Canonical authority remains Issue #1642. No unverified endpoint, new credentials/permissions or arbitrary model-supplied shell.'

Retain every scientific, protection, review, reproduction, persistence and activation gate. Remove only the unsupported assumption that one unavailable implementation is the sole permissible executor. Until the described controller integration and live recovery tests exist, mark those specific implementation/liveness gaps honestly rather than declaring either universal runtime impossibility or master completion.
