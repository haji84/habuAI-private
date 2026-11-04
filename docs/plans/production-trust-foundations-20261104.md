# Production trust foundations implementation plan

> For agentic workers: use superpowers:subagent-driven-development. The owner authorized autonomous implementation; this plan implements the existing Task 8 design without enabling production authority.

**Goal:** implement independently testable, data-only validation and transition construction needed by the approved production trust path.

**Architecture:** retain the existing authorized Codex controller and GitHub connector as the external trust boundary. These pure functions validate supplied facts or construct unpublished proposals; neither authenticates supplied JSON, reproduces model science, writes remote state, nor authorizes activation.

**Tech stack:** Python 3.12, standard library, existing `master_contracts.canonical_bytes` / `digest`, unittest; no dependency or permission changes.

**Spec:** `docs/plans/master-goal-1642-production-trust.md`, `docs/specs/master-goal-1642.md`, Task 8 in `docs/plans/master-goal-1642-plan.md`.

## Global constraints

- Base is actual merged main `9ad62594bb0199a246c9a4959056579df4f9a6cc`; PR #136 integration was explicitly approved and completed.
- Preserve every raw source, original prediction, historical Freeze, model and canonical tally byte-for-byte.
- Do not accept candidate callbacks, executable deserialization, transport, authority flags or a serialized ProductionContext.
- Missing facts are BLOCKED; contradictory facts FAIL. Structural consistency never grants source authentication, scientific validation or production authority.
- Registry genesis/ref/layout decisions, live activation, formal ORIGINAL publication and later main integration remain outside this pure slice.
- Publish only code, synthetic controls and non-sensitive aggregate evidence. Private receipts stay outside Git.

## Review focus

- A coherent invented JSON bundle must remain unauthenticated and unable to activate production.
- PR head, synthetic merge checkout and default-branch merged content are different identities; compare exact tree/parent/closure semantics.
- Incomplete pagination, old attempts, dismissed reviews and unrelated green jobs must never satisfy required facts.
- A transition proposal must have exactly the supplied predecessor as its sole parent; a read-then-write race is not remote CAS.
- Malformed, oversized or custom Python objects must fail closed without I/O or candidate execution.

## Task 1: supplied exact-fact consistency

Files: create `src/production_verification.py` and `tests/test_production_verification.py`.

Interface: `verify_exact_facts(facts: dict, *, intent: dict, policy: dict, max_seconds: float = 1.0) -> dict`.

- [x] Observe RED for absent verifier and adversarial repo/revision/workflow/review/completeness cases.
- [x] Validate bounded built-in JSON; bind repository/task/PR/base/head/tree, consumed closure, exact workflow definition/run/attempt/event/jobs/steps and actual checkout.
- [x] Verify effective exact-revision independent reviews and merge/squash/rebase content mapping without inventing ancestry requirements.
- [x] Return supplied-fact CONSISTENT/BLOCKED/FAIL with source authentication NOT_ATTESTED, science NOT_REPRODUCED and production authority false on every branch.
- [x] Run focused unittest plus independent malformed-input, no-I/O and forgery controls; commit only owned files.

Task1 source commit `ee2dfce964e9d2cc8054de36c7836d2c87a416aa`, integrated as `b371ff7` before Task2. Author42 tests passed; independent42 passed and1,183 scalar mutation controls retained all authority flags false. Fixed a reproduced custom-metaclass callback bug and oversized-string pre-allocation issue before acceptance. Independent receipt SHA `8f5dacf3cedea4918b622e30c2e11bbd38934265159eac853940c0a08e90bc07`.

Subsequent independent optional-job shape finding was repaired in local commit `d93c369`;46 tests and63 independent controls pass. Final exact repair review SHA `295de4808bded7c27a86dfa5608b0c7509642343fc7c741dcba3b7ade82ea9c8` supersedes initial review as final-source acceptance.

Final whole-branch terminal-hierarchy finding was repaired in local commit `367f8ac`;48 tests plus36 independent controls pass. Final source review SHA `368948dd8e9fcc68e205268d590d5bf1783530686a84b0b32582f3fdfb06b865`. Current integrated133-test evidence and immutable cycle124-02 supersede the retained preliminary131-test/cycle124-01 checkpoint.

## Task 2: unpublished single-parent transition proposal

Files: create `src/production_registry.py` and `tests/test_production_registry.py`.

Existing-predecessor only. The API must bind supplied predecessor commit/event, immutable intent and artifact hashes, and policy-owned scope before constructing deterministic canonical additions and a commit specification with `parents=[predecessor]`. It must emit a proposal, never an activated event or authenticated production state.

Interface: `prepare_transition_proposal(predecessor: dict | None, intent: dict, *, policy: dict, expected_ref_sha: str | None, expected_previous_event_sha256: str | None, max_seconds=1.0) -> dict`. The predecessor supplies the existing commit/event and path-to-SHA inventory. The intent binds repository/task, requested operation, exact reviewed-intent reference and code/model/evidence/protocol/policy hashes. Policy supplies the existing approved scope/layout; this function does not authenticate that policy. Output contains canonical proposal-record addition and a pointer-update descriptor with expected prior file/event hashes. It never generates active-model pointer bytes or a trusted actual-time ActivationEvent.

- [x] Freeze the minimal function/data contract with the coordinator before implementation; reuse existing canonical serialization, not report transport authority.
- [x] Observe RED for same-input determinism, sibling proposals, stale predecessor/event, malformed/multiple parent, overwrite/deletion/path escape and missing genesis prerequisites.
- [x] Implement pure construction with no I/O, clock authentication, transport, actual promotion, rollback or genesis creation.
- [x] Run focused unittest and independently review hash binding, immutability, race semantics and explicit false authority; commit only owned files.

Task2 source commit `94cf8cd9eec18e7290a847bc460213d76b1c5320`, integrated as `23a34e8`. Author19 new +32 related tests passed. Two independent reviews passed scoped proposal construction: one19-test/437-external-invocation review and one51-test/245-scalar-mutation review. Receipts `25b8bf1879356e68d6e8d7623c51460d8e2a03a0ed2e9a31c340d2f04c1a1512` and `d1df2d349a50e546a8477645e25440ceba592b9d51aac03a559a7f5bbb2b2542` retain the unexecuted/untrusted boundaries.

## Task 3: integrate and retain evidence

Coordinator owns this plan, review report, handoff state and a new immutable development cycle/cursor. Review both implementation commits before integration.

- [x] Integrate reviewed commits in the existing isolated coordinator workspace; record exact source/test SHA and RED/GREEN receipts.
- [x] Generate a new byte-bound development Freeze over the actual code closure; keep all earlier cycles unchanged.
- [x] Run affected integration/Freeze tests; audit no protected-source or production-state change.
- [ ] Obtain independent whole-branch review; repair findings on the same logical branch.
- [ ] Publish one logical production-trust foundation Draft PR after checking existing PR scope; obtain exact-head CI. Do not merge it under the approval specific to PR #136.
- [ ] Record main #136 fresh-CI/functional evidence separately from new feature CI. Keep data blockers, missing executors and real-field validation distinct; Master remains open.

## Deliberate remaining work

This slice does not complete substantive scientific reproduction, authenticated controller fact acquisition, remote registry CAS/ambiguity recovery, compatible model loading, registered composite inference, formal P0 issuance/publication or real P0-to-PDCA acceptance. Those require their own implementation and evidence under the existing design; absent real observations do not excuse leaving a generic executor unimplemented.
