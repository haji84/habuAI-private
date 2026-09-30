# Existing bounded development executor audit

Read-only audit for Habu AI master Goal #1642. No implementation, remote mutations, runtime probes, dispatches, installs, credentials, or permission changes performed. No tests run.

## Revision and governance

AI- main resolved through GitHub to **5d2dfd49a3015536e42d8adf8aec403b024c9318** (2026-09-30); all implementation files below fetched at that exact revision. AGENTS.md, PROJECT_STATE.md, and ROADMAP.md read first from main. Main tree contains no AI_COMPANY_PAUSED file. Source availability is not live service availability.

AGENTS.md requires Unified Intake -> Intent Classifier -> Goal Resolver -> JARVIS Goal Controller ownership; capabilities cannot create independent development authority. Preserve explicit Goal/job scope, append-only state transitions, independent evidence and all credential/permission/security Human Gates. PROJECT_STATE.md reports some code/CI completion but leaves physical acceptance gaps: do not substitute these claims for current endpoint health or Habu integration proof.

## Exact existing interfaces

### Goal intake and durable execution

- `src/orchestrator/goal-controller-runtime.ts`: `UnifiedIntakeRequest` fields `source, text, id?, sourceContext?, idempotencyKey?, goalHint?, goalContract?`. `goalContract` has successCriteria and optional constraints, each list bounded to 16 strings of <=500 characters. Sources include github/event/codex/chat/jarvis/device. `GoalControllerRuntime.handle` classifies and deduplicates; explicit goalHint resolves against an active runtime Goal ID/title. Result action is ANSWER, INSPECT, EXECUTE_BOUNDED, or CONTINUE_GOAL. GitHub issue number #1642 is not automatically a Compass Goal ID.
- `src/app/api/jarvis/work/route.ts`: owner-session-authenticated POST `/api/jarvis/work` accepts `text, idempotencyKey?, goalHint?, goalContract?, requirementReferenceId?, requirement?`; proxies to broker `POST /api/jarvis/admin/work`.
- `scripts/jarvis-broker.ts:501-585`: broker work endpoint receives bounded text payload (64KB body), resolves Goal, stores queued WorkRun, schedules execution, returns accepted/executionScheduled/goalId/action/resolution/remainingCriteria. Broker admin path requires owner Bearer authentication (lines 236-237,347). GET `/api/jarvis/admin/work/<goalId>` reports run/progress. It defaults goalHint to the first active Goal if absent: Habu must bind the exact existing Goal explicitly.
- `scripts/jarvis-broker.ts:590-604`: separate POST `/api/jarvis/admin/development-intake` requires an existing trusted worker identity; fields deviceId/platform/ownerCommandId/text/connectivity/goalSnapshotDigest/causalParentId. It is not an unauthenticated generic webhook.
- `src/orchestrator/development-job.ts`: `createDevelopmentJob` requires jobId, goalId, requirementIds, acceptanceCriteria, definitionOfDone, baseRevision, approvalScope(taskScopeId,maxRisk,optional expiry), workItems. Only DevelopmentJobStateController commits transitions; job stores evidence, attempts, failure signatures, rejected strategies and history.
- `src/orchestrator/development-orchestrator.ts`: DevelopmentPlanningInput additionally binds objective, targetFiles, contextDigest and priorFailures. Plan produces test -> implementation -> independent verification work items, strategy/hypothesis and rollback plan. releaseAuthority=false.
- `scripts/jarvis-goal-executor.ts:61-120`: resident development selection uses context/Goal text, resolves base revision and repository files from **process.cwd()**, constructs bounded repository context, and routes builder. It is not a per-request arbitrary-repository checkout service. Persistent jobs/change sets are stored under Compass parent/self-development. GoalControllerExecutionBridge and ResidentDevelopmentGoalHost resume bounded attempts.

### Builder capability

- `src/orchestrator/builder-router.ts`: BuilderRequest = goalId,attemptId,strategyId,objective,context; optional files,baseRevision,hypothesis,previousFailureSignatures,previousStrategyFingerprints,localOnly,tddPhase. BuilderRouter rejects equivalent failed strategies and reports real_builder_capability_unavailable if no eligible real builder.
- `scripts/code-builder-worker-service.ts`: authenticated service defaults to loopback 127.0.0.1:8796. Existing CODE_BUILDER_TOKEN is mandatory, CODE_BUILDER_WORKSPACE fixes one workspace. GET /health reports detected engine/capabilities. POST /build takes BuilderRequest core fields. POST /verify supports bounded verification contracts.
- Codex invocation uses exec workspace-write, ephemeral mode, stdin prompt, process shell=false, bounded timeout (default 600000ms). Builder prompt prohibits commit/push/merge/deploy/credential/security changes. It returns changedPaths, patchDigest,candidateRevision,artifactDigest,artifactRef and execution evidence; it does not publish.
- `src/gai/http-worker-builder-capability.ts` implements this HTTP client and normalizes the result. `src/orchestrator/development-builder.ts` rejects forbidden requestedAuthority, path escapes, out-of-declared-scope changes and invalid digests; returns releaseAuthority=false.
- `src/orchestrator/runtime-builder-capability.ts` discovers local endpoint via existing CODE_BUILDER_LOCAL_URL+TOKEN or existing OS token file; remote endpoints via CODE_BUILDER_ENDPOINTS_JSON (HTTPS). Local-only health intentionally excludes codex/aider, requiring device inference with networkAccess=false.
- `.github/workflows/gai-code-builder-zbook.yml` installs/probes the fixed builder on a self-hosted Windows runner. It is **not** a reusable workflow_call job executor: dispatch/issues with a specific probe-title prefix are install/probe triggers. Do not invoke installation to satisfy Habu under the current no-permission-change scope.

### Existing branch / test / PR executor

`src/orchestrator/safe-pr-capability.ts:232-329` exports `createSafePrProposalCapability({cwd?,token?,repository?,releaseGateDecision?})`, capability name **repository.propose_pr**.

Action input: title, optional body, files[{path,content}], optional taskAuthorization/taskScopeId.
Bounds: <=3 files, <=100000 total bytes, only src/, tests/, docs/, scripts/. Blocks .github/, AGENTS.md, PROJECT_STATE.md, ROADMAP.md, package.json, pnpm-lock.yaml. Implements fixed pnpm lint/test/build checks, verifies base current with origin/main, creates autonomy/run-<runId> branch, stages scoped files, commits, normal-pushes and opens GitHub PR against main. Auto-merge requires the release decision plus scoped authorization. This is actual code, not merely a design document.

Important integration limits: it writes candidate files before branch creation; caller must provide isolated clean checkout. Check profile is hardcoded for AI- pnpm; it also includes AI- requirement traceability reconciliation. It does not expose a general public HTTP submission endpoint. Habu Python code and >3-file improvements cannot be passed straight through without a separately scoped repository adapter.

### Release / CI / recovery

- `src/orchestrator/development-release-gate.ts`: decisions OPEN_PR, ENABLE_AUTO_MERGE, WAIT_FOR_MERGE, WAIT_MAIN_CI, DEPLOY_PRODUCTION, VERIFY_PRODUCTION, COMPLETE (plus blocked/human/offline states). Requires task-scoped active authorization, trusted change classification, independent candidate-bound verification, current base, passing checks and no unresolved review requirements. Non-bypassable protected conditions remain Human Gates.
- `src/orchestrator/http-development-release-capability.ts`: configured authenticated client only. GET **<release-url>/state?jobId=...&changeSetId=...&taskScopeId=...**; POST **<release-url>/actions** body action,operationId,jobId,changeSetId,taskScopeId,candidateRevision,artifactDigest and Idempotency-Key header. HTTPS or loopback HTTP only.
- `scripts/jarvis-goal-executor.ts:116-121` requires paired **GORIQ_SELF_DEVELOPMENT_RELEASE_URL / GORIQ_SELF_DEVELOPMENT_RELEASE_TOKEN**. If Goal text requires PR/merge/release and these are absent, it explicitly throws SELF_DEVELOPMENT_RELEASE_CAPABILITY_MISSING. ResidentDevelopmentGoalHost refuses missing release capability. **No production server for this /state + /actions interface was identified in inspected files**; do not equate client contract with deployed publisher.
- Release gate currently models completion through exact Production deployment and post-deployment evidence. Habu PR-only or merge-and-CI-only completion needs explicit outcome mapping; never fabricate Production evidence.
- `.github/workflows/goriq-pr-ci-recovery.yml` plus `scripts/goriq-pr-ci-recovery.ts`: actual failure-triggered CI fixer for existing same-repository open PRs only. Trigger workflow_run CI failure, PR event, same current head. Trusted control checked out from main separately from PR target; Windows runner, 75-minute bound. Script permits source repair paths derived from PR, rejects protected/security/governance/test changes, strips builder credentials/disables push for builder, reruns fixed pnpm checks, rechecks remote head, and commits/pushes scoped verified correction. Bounds: 3 strategies x3 attempts, same-failure strategy escalation, 3 local verification attempts. This creates no initial Habu job/PR and needs Python check adaptation.
- `docs/runbooks/codex-pr-fixer.md` is an older manual runbook with 3 attempts and no merge authority; current AGENTS.md is progress-aware RC2. Prefer executable contracts and current governance rather than treating old runbook as universal policy.
- `scripts/goriq-self-development-acceptance.mjs` explicitly uses deterministic fixtures; its green result would not prove a live Habu builder/publisher. The live-acceptance workflow has its own isolated fixture/device scope, not Habu automatic improvement acceptance.

## Integration conclusion for #1642

Reuse the **Goal-owned typed intake/job, builder result envelope, independent verification and separate publication contracts**, not a Habu arbitrary command/shell runner. A PDCA finding can become a bounded child-job proposal bound to exact master runtime Goal, repository+base SHA, allowlisted paths, criterion IDs, immutable evidence hashes, hypothesis, risk, attempt budget, and stable idempotency key. That is an integration recommendation, not an existing Habu endpoint.

Concrete remaining blockers:
1. Establish exact #1642 <-> Compass Goal identity and existing authorized intake transport; no available endpoint/session/token or live worker proven here.
2. Provide authorized Habu-isolated checkout selection: existing resident controller/builder are process/workspace-bound, not multi-repository.
3. Bind existing authority to Habu repo/path scope, prevent ORIGINAL/raw/holdout modifications and security/workflow changes. Empty files scope currently weakens builder-result path allowlisting; require nonempty explicit allowlist.
4. Supply fixed **Python** verification profile and independent evaluator (holdouts/leakage/ORIGINAL invariants) instead of hardcoded pnpm. No arbitrary commands from PDCA findings.
5. Connect or verify a real authorized publication executor implementing release state/actions; current capability/client separation is not proof it is installed/configured.
6. Persist child job, attempt, candidate SHA/hash, CI/PR and verification receipt; retries must deduplicate and reject stale/current-head conflicts. An issue/report alone is not development execution.
7. Treat recurring future improvements under their actual approved scope/expiry; current task authorization cannot silently become unlimited future merge/deploy authority.
8. Exact same code must undergo a read-only availability check and one scoped live acceptance before claiming automatic future PDCA code improvement. None was dispatched in this audit.

All source links can be anchored at https://github.com/haji84/AI-/blob/5d2dfd49a3015536e42d8adf8aec403b024c9318/<path>.

