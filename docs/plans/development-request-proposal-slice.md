# Declared bounded development request implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Root implements inline; the Task7 plan prohibits implementer subagents. Independent whole-slice review remains required.

**Goal:** Create strictly typed, content-bound implementation-completeness scope proposals without admitting or executing a job.

**Architecture:** Extend the existing bounded pure development handoff module with a request builder and inspector. One fixed capability mapping derives paths, strategy, tests and finite engineering limits. Caller declarations remain unauthenticated; no controller, lease, external write or scientific execution is added.

**Tech Stack:** Existing Python standard library, canonical JSON SHA-256, JSON Schema.

**Spec:** `docs/plans/master-goal-1642-codex-controller.md`, `docs/reviews/master-goal-1642-controller-risk-check.md`, `docs/specs/master-goal-1642.md` normative controller correction.

## Global constraints

- Canonical master `haji84/AI-#1642`, repository `haji84/habuAI-private`.
- Missing data produces data requirements, not fake code jobs.
- No model-supplied commands, arbitrary path scopes, credentials, permissions or workflow changes.
- Science accounting remains cumulative300 seconds, two rounds, three preregistered recipes. Engineering proposal limits cannot exempt actual fitting/evaluation.
- A pure proposal proves declared consistency only. Request admission, authenticated facts, actual missing-capability inspection, durable job/strategy budget, claims/results, publication and backend return remain separate unimplemented gates.
- Preserve all existing science ledger and Git report APIs and artifacts.

## Review focus

- Changed source/evidence/expiry must change request identity but cannot change the stable root/capability/strategy key.
- A stale free-text blocker, current missing data or already present executor must not propose an executable job.
- Rehashed requests cannot widen paths, verification profile, acceptance criteria or engineering limits.
- Caller-declared deployed prerequisites, clocks and matching evidence hashes cannot establish authority.
- Malformed/oversized known input must fail before an early data/prerequisite return; detached results must survive caller mutation.

## Task1: Pure fixed-scope proposal contract

**Files:** Modify `src/development_handoff.py` and `tests/test_development_handoff.py`; create `schemas/development-job.json` and `docs/reviews/development_request_proposal_20261025.md`.

**Interfaces:**

- `propose_development_request(provenance, need) -> dict`: bounded detached JSON proposal decision, with `request` or null and false authority flags.
- `inspect_development_request(request) -> dict`: own/validate the exact request, rederive all fixed fields and verify its content digest; no I/O or authority.
- Fixed capability `CONFIGURED_STAGE1_PARENT_DISPATCH_V2`, strategy `REUSE_SOURCE_STAGE1_V2`, requirements R005/R026. This is the still-missing parent connection, not E's already-active source adapter implementation.
- Prerequisite: caller declares source contract `habu-stage1-source-contract-v2` deployed. Declared installed parent produces ALREADY_IMPLEMENTED; absent prerequisite produces PREREQUISITE_REQUIRED. DATA_REQUIREMENT and unmapped capability produce no request. Neither declaration is trusted admission.
- Exact provenance: master/repository, root and parent command SHA-256 IDs, parent run SHA-256, operational night, source commit SHA-1, protocol SHA-256, observed/expiry timestamps, nonempty bounded evidence refs. Evidence refs are canonical relative JSON paths inside that exact parent run's reports namespace with lowercase SHA-256 and positive exact-integer byte size.
- Exact need: `kind` (CODE_CAPABILITY/DATA_REQUIREMENT/UNMAPPED), `capability_id`, `capability_installed`, `prerequisite_schema` (nullable bounded string; unknown version produces PREREQUISITE_REQUIRED), `prerequisite_deployed`. Exact bools; no defaults or prose-to-command extraction.
- Fixed allowed paths: `src/research_pdca_adapter.py`, `tests/test_research_pdca_adapter.py`, `docs/specs/research-configured-stage1-parent-v2.md`, `docs/reviews/research_configured_stage1_parent_v2_20261025.md`. No prefix wildcard or caller extension.
- Fixed verification profile `HABU_PYTHON_EXACT_HEAD_REVIEW_V1`; exact acceptance IDs preserve old versions, call reviewed source-v2 with shared context, bind exact three candidates, keep false authority, run exact-head/fresh-main Ubuntu CI.
- Proposed finite engineering caps: two attempts,3600 active seconds per attempt,7200 cumulative active seconds,600-second lease. These are schema constraints only; no consumed-budget ledger or execution permission is created.
- Stable strategy key hashes only canonical master/repository/root/capability/strategy. Request SHA hashes all request content except itself.
- Bounded snapshot uses the existing1MiB/10000-node/depth12 pure JSON guard, plus tighter provenance ref count/path bounds. At most16 refs/256KiB each/1MiB declared aggregate; observed<expiry<=observed+24h. All shape/known value checks precede no-request decisions.

- [x] Write tests for valid exact derived request/no authority, stablekey across changed source/evidence, strict evidence/provenance, no-job cases, rehashed scope/profile/limit injection, bounded data and no I/O.
- [x] Run new tests and observe missing API assertion failures.
- [x] Implement the two APIs and exact JSON schema without touching existing ledger semantics.
- [x] Run original ledger17 plus new proposal tests; run existing publisher/connector targets where affected. Record exact counts and real versus synthetic scope.
- [ ] Commit source/tests/schema/plan/review record.
- [ ] Obtain independent whole-slice source/adversarial review and fix actual findings through RED→GREEN.

## Completion boundary

This slice is complete only as a declared scope proposal/strict inspector.
It does not fulfill the complete Task7/controller/live one-command acceptance.
No actual job is opened while E's prerequisite remains unreviewed/undeployed.
Future source changes cannot reset job attempts using the stable strategy key;
enforcement still requires authenticated admission and a durable job ledger.
