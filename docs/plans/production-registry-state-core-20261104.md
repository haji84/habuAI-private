# Conditional production-state core implementation plan

> For agentic workers: use subagent-driven development, TDD, independent review and exact-head verification. This is the existing Task8 state-machine design, with no live registry/genesis/production authorization.

**Goal:** implement source-consistency checks, unpublished event/issuance commit construction and ambiguous-response reconciliation under an existing predecessor.

**Architecture:** extend the existing pure `production_registry` library. A separate fixed active-host operation must obtain/authenticate real facts, run actual source/scientific gates and perform any authorized connector write. Candidate JSON, snapshots, test transports and saved receipts never instantiate trusted production context. The current host can use its approved connector; absence of a repository SDK is not proof that host execution is impossible.

**Tech stack:** existing Python standard library only. No new dependency, credential, service, permission, deployment or storage configuration.

**Spec:** `master-goal-1642-production-trust.md`, `master-goal-1642-codex-controller.md`, `master-goal-1642-controller-continuation.md`, AGENTS and Master1642. The read-only next-slice brief/host addendum are private audit context, not source or deployment authority.

## Constraints and ownership

Owner: production_audit; isolated existing worktree from reviewed root61fa7b0. Own only `src/production_registry.py` and `tests/test_production_registry.py`. Root owns metadata, code Freeze, host integration and GitHub. Preserve existing `prepare_transition_proposal` behavior and IDs.

All new positive results are **supplied-fact consistency only** and every production/official/source-authentication flag remains false/unattested. `observed_at` in the pure API is a supplied time, not a trusted clock. No filesystem, network, transport, dynamic loader, callback, serialized context, actual Genesis/ref choice, publication or model activation is implemented by these functions.

The nonprivileged core requires an explicit closed supplied policy for anchor/ref/path/record/issuance layout. It never selects an actual production layout or default namespace. The coordinator must separately freeze and review the actual host binding/durable layout before privileged operations; current missing predecessor/genesis and enabling approval remain blockers. A caller's complete/verified/PASS fields are checked as declarations, not authenticated proof.

## APIs and tasks

- [ ] Define exact snapshot/policy/event/issuance/pending/observation fields and RED cases before implementation. Reject foreign types before traversal/encoding; bind complete canonical bytes under strict size/depth/work/deadline caps.
- [ ] `validate_registry_snapshot(snapshot, *, policy, budget_seconds=30)`: validate the complete supplied anchored chain/tree/pointer and immutable record/model/intent/reviewed-code references. A partial suffix or truncated inventory is not a complete existing-state proof. Missing existing anchor/predecessor BLOCKS; no Genesis invention.
- [ ] `prepare_activation_commit(snapshot, intent, gate_decision, *, policy, observed_at, expected_ref_sha, expected_previous_event_sha256, budget_seconds=30)`: construct only unpublished canonical event/pointer additions with **exactly S as sole parent**. No future self-commit hash inside its own event. PROMOTE and ROLLBACK retain separate semantics; rollback requires a previously activated compatible model. Scientific gate JSON cannot grant authority.
- [ ] `prepare_issuance_commit(snapshot, inference_record, *, policy, observed_at, expected_ref_sha, expected_event_sha256, budget_seconds=30)`: preserve selected event, source/model/code/output identities, prospective time/window and immutable version bytes. Propose the next contiguous Pn only; same version/different bytes conflicts. Local failed-CAS artifacts never become ORIGINAL. Old ORIGINAL/history stays unchanged.
- [ ] `reconcile_publication(pending, observed_history, *, policy, budget_seconds=30)`: preserve pending operation identity/bytes across timeout/restart. ACK_ONLY requires exact proposed object/record in the supplied validated current or descendant history; a sibling or differing bytes is CONFLICT; missing/incomplete observations remain ACK_UNKNOWN/BLOCKED. Never silently rebase, restamp, change a consumed version or rerun science. An unknown commit SHA after create ambiguity cannot be invented.
- [ ] TDD both orders of activation/issuance race, siblings, stale predecessor, lost ACK, exact committed child/descendant, rollback to never-active/unsupported code, bad pointer/chain/path collision, missing complete-state facts, altered inference/seal, late P0, duplicate Pn and immutable-history/no-write/custom-type/deadline controls.
- [ ] Commit only the two owned files with actual test/log/source hashes and private author receipt. A different reviewer verifies exact bytes and source/privacy/authority boundaries. Root creates the expanded immutable code Freeze and new exact-head CI before public checkpoint.

## Subsequent fixed host operations

The four approved operations remain `prepare_activation`, `verify_merged_intent`, `activate_reviewed_intent`, `issue_current_prediction`. Their reviewed runner must call fixed actual host connector methods, normalize fresh complete facts and recheck moving identities. Test fakes belong only to a separate sandbox harness; ordinary inputs cannot choose a tool name, transport, endpoint, credentials, trusted flag, clock or facts file as authority. No saved JSON restores an authenticated context after restart: the host reacquires actual facts.

Actual current acceptance should be an authentic NEED_MORE_DATA/BLOCKED with zero activation: real qualified source/confirmation/formal evidence is unavailable, PR155 remains Draft/unmerged, no approved production registry or Genesis exists. The conditional core tests are not live CAS, real prospective P0, model improvement, production approval or a persistent unattended worker.
