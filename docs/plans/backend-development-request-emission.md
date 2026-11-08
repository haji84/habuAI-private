# Command-scoped backend development request emission

Root implements inline with TDD and independent exact-source review. This is a
bounded continuation of Task7, not root/job admission or an execution controller.
The independent read-only seam audit in the active session approved the design
below on2026-10-25. Existing master/scientific identity/checkpoints stay intact.

## Scope and contract

Own new `src/backend_development_request.py`,
`tests/test_backend_development_request.py`, a readable pinned legacy parent
fixture `tests/fixtures/research_parent_v3_5d4b84f.py.txt`, this plan/review,
and the narrow `src/pdca_bridge.py` terminal/optional-receipt verification hook.
No master/CLI/context/schema/model/policy/Raw/workflow/permission changes.

- Only canonical repository ordinary owner commands are eligible. Derive root
  and parent from the authorized command ID, run/source from the final verified
  terminal bundle. Ignore arbitrary body/root/PASS declarations. Continuation
  admission/handling remains a separate unresolved gate.
- Reuse `verify_handled_receipt` to verify the actual committed terminal result
  before proposing. Read the fixed source profiles and engineering schema as
  bounded mode100644 pinned Git blobs. Match their raw SHA/size against the
  verified recovery inventory. `protocol_sha256` here identifies the actual
  `schemas/development-job.json` engineering request contract; it is never the
  scientific protocol or master policy hash.
- Capability mapping is a closed raw-byte profile, not substring/AST/callable
  inference. Reviewed parent SHA0a98ed940e461b49dd85802e2dd4f0006f3245a1e8ff55c831120aec9b8ba104
  declares absence; reviewed source-v2 SHA388bf18b1f4f90fb29d48fe0c4f58579bae925d281f99b27eb0e79baa038ada6
  is the prerequisite. Unknown code/schema => no proposal. A reviewed v4 profile
  can subsequently be explicitly registered present; old v3 blockers remaining
  in a new parent must not trigger another job.
- Before a new proposal, refetch default source using the existing API. Require
  exact equality with final backend source; advancement yields no new proposal.
  A known mapped missing code capability is IMPLEMENTATION_COMPLETENESS even if
  data is also blocked. Data-only/free text/unmapped/absent prerequisite alone
  cannot create a job. Use the existing fixed request builder unchanged.
- Evidence is the verified bundle's actual small finalization checkpoint raw
  reference, which binds stage hashes. Enforce existing16refs/256KiB per ref/
  1MiB aggregate limits; do not truncate a large manifest/stage into fake proof.
- Persist only an actual declared scope proposal. Fixed path:
  `reports/pdca/{night}/bridge/development-request-{command_id}.json` on the
  existing command branch. Canonical LF envelope binds command/source/run/bundle/
  result, profile/schema refs, observation/expiry and exact pure decision.
  All six authentication/authority flags remain false.
- One CAS publish atomically adds sidecar plus COMPUTED receipt's optional
  `development_request_ref`; propagate actual head to later receipt writes.
  Retry reuses exact remote bytes/time/expiry, never refreshes allowance. Verify
  one historical addition/no later mutation of this fixed sidecar. Reconcile a
  lost reply by observing both matching sidecar and receipt; otherwise fail
  retryably while retaining the computed run, without scientific re-execution.
- Verify optional refs on new HANDLED receipts. Old HANDLED early-return path
  without the ref stays unchanged; no backfill/reinterpretation of old commands.
  Noncanonical repositories and no-proposal cases retain old receipts/results.
- Reuse fixed bounded metadata/blob guards,1MiB/blob and16MiB actual-read cap.
  Saved sidecars are historical declared consistency, not authentic root, current
  clock, live lease, job START, trusted CI, science allowance or backend return.
  Metadata/network/native operations are not hard-preemptible. Nonforce does not
  promise server exact CAS against administrator resets.

## Implementation sequence

- [ ] Add missing-API RED tests for fixed profiles, source advance, inventory/
  protocol/evidence binding, exact envelope/flags and no arbitrary scope.
- [ ] Implement bounded terminal observation and strict historical inspector.
- [ ] Add RED tests for actual bare-Git atomic sidecar/receipt CAS, retries/lost
  reply/history tamper/mode/caps and expiry reuse, then implement publication.
- [ ] Add the lazy terminal hook after final result verification; optional-ref
  HANDLED verification only. No science identity/checkpoint edits.
- [ ] Add genuine POSIX bridge execute/COMPUTED recovery tests, two command roots
  sharing one run, source adoption/default race and no-ref legacy compatibility.
  Native Windows tests use real Git and explicitly synthetic terminal proof
  seams; no fcntl facade or fake numerical fit.
- [ ] Run meaningful native targets and independent exact-source review, then
  coordinator closure/PR/exact Ubuntu/fresh-main verification. Record actual
  receipts and all remaining Task7/scientific conditions.
