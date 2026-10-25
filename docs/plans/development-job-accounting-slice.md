# Bounded development job accounting implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans. Root implements inline. Independent whole-slice source review is required.

**Goal:** Preserve implementation attempt, active-time and lease history across interruption and fixed Git report publication without granting execution authority.

**Architecture:** A focused pure module replays a strict event union and derives accounting from immutable requests/history. A separate fixed transport module reconstructs canonical origin/state/events and verifies the full linear Git history. Reuse existing byte/mode/JSON primitives and GitTransport, leaving scientific ledger and executor semantics untouched.

**Tech Stack:** Existing Python standard library, canonical JSON SHA-256, existing GitTransport and real temporary bare Git tests.

**Spec:** `docs/plans/master-goal-1642-codex-controller.md`, `docs/plans/master-goal-1642-controller-continuation.md`, `docs/reviews/master-goal-1642-controller-risk-check.md`, independent design review recorded in the current connected session.

## Global constraints

- Canonical master `haji84/AI-#1642`, repository `haji84/habuAI-private`.
- Engineering caps: two attempts per root+capability,3,600,000 active milliseconds per attempt,7,200,000 cumulative milliseconds,600-second maximum lease.
- All root/request admission, authenticated facts, execution, scientific, selection and production flags remain false. Observed clocks/active time are CALLER_DECLARED_NOT_ATTESTED.
- Scientific work still needs its separate cumulative300-second/two-round/three-recipe accounting; an engineering purpose does not exempt fitting/evaluation.
- No Raw/ORIGINAL/model/policy/workflow/permission/controller/continuation changes.
- Maximum32 events,1MiB owned snapshot,10,000 nodes,depth12. No new ledger/job identity to bypass exhaustion or capacity.

## Review focus

- Changing source/request/run/night/strategy cannot reset aggregate job identity or attempts.
- Pausing for a long CI wait fences the worker and retains the same attempt/remaining allowance without a live lease or active-time charge.
- At lease equality only expiry is valid; stale ordinary completion cannot refund conservative expiry charges.
- Actual overrun must be recorded at its full bounded reported value, including late accounting incidents, without resurrecting an expired worker or double charging.
- Competing Git writers, ambiguous push, historical canonical tamper and changed anchor/base must reconcile or reject without reset.

## Task1: Replayable pure implementation accounting

**Files:** Create `src/development_job_ledger.py`, `tests/test_development_job_ledger.py`, `schemas/development-job-ledger.json`, `docs/specs/development-job-accounting-v1.md`, `docs/reviews/development_job_accounting_20261025.md`.

**Interfaces:**

- `new_development_job(request) -> ledger`: validate the strict declared request and propose a zero-event origin. Origin includes version/master/repository/root/capability/job_id/anchor_night/fixed limits. Anchor night is fixed only for storage and never changes with later requests.
- `inspect_development_job(ledger) -> summary`: fully validate/replay immutable history; derive attempts/charged/reserved/remaining, current generation/phase and budget-exceeded state. Do not accept saved totals.
- `append_development_job(ledger, *, expected_tip, transition) -> ledger`: strict START/CHECKPOINT/SETTLE/EXPIRE union. No arbitrary commands, event IDs, attempts, paths, source flags or PASS facts.
- `job_id=SHA({master_issue,repository,root_command_id,capability_id})`; operation ID adds fixed strategy only, attempt ID adds ordinal1/2 only. No source/run/night/scope version in aggregate identity.
- START inputs exact kind/request/now/lease_until. Declared observation<=now<request expiry is required, without authenticating the clock. Derive canonical attempt/operation/ordinal/allowance/generation from replay. One open ACTIVE or WAITING_CI attempt at most. Request/source/strategy immutable within one attempt; next source requires the second attempt under the same job.
- CHECKPOINT exact kind/attempt_id/generation/active_ms/phase/now/lease_until. ACTIVE report is nondecreasing, within allowance and before lease expiry. Every checkpoint fences the previous generation and derives the new generation from event sequence. WAITING_CI requires lease_until=null; its active checkpoint cannot increase until resumed. Resume same attempt at the same active total with a new bounded lease/generation.
- SETTLE exact kind/attempt_id/generation/active_ms/now. Healthy ACTIVE settles before expiry; WAIT settles only at its exact checkpoint total. Close once; exact identical prior settlement at current tip is idempotent. Ordinary altered/stale completion rejects.
- SETTLE reported overrun is accounting-only: known immutable attempt and ACTIVE-issued generation, reported active_ms greater than its allowance and greater than any prior actual report. WAIT/closed fence generations cannot originate active increases. Accept even after expiry/settlement; charged=max(previous charged,reported actual), never clip or double charge. Mark the entire job terminal budget_exceeded/remaining0. Fence/close other open workers, conservatively charging their active reservations; paused CI attempts retain only checkpoint charge. New START/renew/resume prohibited. Max report86,400,000ms is a metadata bound; excess explicitly CAPACITY_BLOCKED/unreconciled, never zero or clipped.
- EXPIRE exact kind/attempt_id/generation/now, ACTIVE only now>=lease_until. Charge the remaining reserved allowance in full, fence and close. WAIT has no lease and no expiry charge.
- Common event sequence/previous_sha256/event_sha256/now; origin/event hash chains, strict integers/booleans and non-reversing declared time. Compare derived canonical bytes including types. Repeated settlement is no-op only after reconciling the current tip; stale tip append always rejects.

- [x] Write failing tests for each transition and the five review-focus classes, including two request versions sharing the job, old-worker generations, long CI waits, extreme aware clocks, late positive overrun delta and capacity rejection.
- [x] Run tests and observe missing API assertion failures.
- [x] Implement the pure module/schema without editing original science/request APIs.
- [x] Run pure tests plus existing handoff invariants; record actual versus synthetic scope.
- [ ] Commit pure source and obtain independent exact-source review before transport implementation proceeds.

## Task2: Fixed report-only Git persistence

**Files:** Create `src/development_job_reports.py`, `tests/test_development_job_reports.py`; extend only this slice's spec/review.

**Interfaces:**

- `publish_development_job(root,ledger,*,root_report_source_commit,expected_remote_head,expected_tip) -> TRANSPORT_ACK_ONLY` constructs fixed GitTransport(root,'origin'). Explicit private transport seam for tests only, never a public fake/trusted flag.
- Branch `pdca/development-{job_id}`; prefix `reports/pdca/{origin.anchor_night}/bridge/development/{job_id}/`. Fixed origin/state/sequence-eventSHA files. Immutable source base is separate from attempt code source.
- Reuse only existing `_report_tree`, `_read_report_blob`, `_report_json`, `_report_bytes` bounded primitives. Do not parameterize or replace scientific semantic `_report_view`/`_validated`.
- Zero-event bootstrap requires absent remote branch and absent base namespace. Existing branches require matching immutable origin/base, exact expected head/tip and one new semantic event. Validate all historical prefix states, raw canonical bytes, exact regular-file paths/modes and one-event linear commit deltas. Reject no-op/merge/tamper/foreign/source rewrites.
- At most34 distinct paths,1MiB per blob,16MiB cumulative actual materialized bytes including history/rereads, preflight before decode. Metadata/fetch is outside the counter and not hard-preemptible.
- Non-force direct-parent conflict protection; ambiguous pushes and already-published exact prefixes return latest ledger/head/tip only, all authority false. No claim of server exact-old-SHA CAS against administrator ref deletion/rewind.

- [ ] Write tests and observe missing report API failures.
- [ ] Implement fixed canonical report persistence.
- [ ] Run actual native bare-Git bootstrap/append/restart, after-preparation sibling race, lost push response, latest expired ACK, foreign/raw/history/mode/cap/anchor/base rejection tests.
- [ ] Obtain independent whole-slice review; freeze the complete native Git-index closure and publish one PR with exact Ubuntu/fresh-main verification.

## Completion boundary

Pure accounting and transport do not authenticate a root, request, worker, clock,
actual runtime, live lease or CI result. They do not execute implementation or
science and cannot resume the backend. Actual worker hard-stop, authoritative
admission, existing-campaign migration, trusted runtime overrun and controller
result/merge/continuation acceptance remain separate requirements. Never call
pure-only completion durable restart safety; require the real Git transport tests.
