# Task6a independent review — pinned 3dcc2f8

Scope: `a42d914..3dcc2f8`, the bounded evidence-audit plan/design, implementation report, evidence auditor, learning builder, master/operational integration and relevant tests. Later worker repairs are outside this review. No repository implementation changes, nested agents or full-suite rerun.

**Spec compliance: changes required. Code quality: changes required.** No Critical finding; seven Important findings below. All were reproduced with small disposable fixtures. The first false-negative finding is already being repaired separately; retain it in this pinned-head record until re-review.

The implementation has useful real foundations: exact receipt/archive checks, explicit current versus historical availability, source selectors, GPX segment diagnostics, UNKNOWN defaults, outside-universe outcome retention, exact OSM namespace, derived evaluation workspaces and checkpoint artifact verification. The blockers are defects in those implemented contracts, not demands to fabricate missing historical data or implement unrelated future science.

## Important 1 — Known unresolved capture becomes an observed negative

Files: `src/evidence_audit.py:310–328, 342–365`; downstream `src/learning_snapshot.py:67–85`.

Session eligibility checks only its listed capture files and `bad_sources`. It does not reconcile other known unqualified captures against the session. `_units` first labels searched cells zero, then only overrides cells for `canonical_eligible` captures. A known but unresolved positive in the same cell/time is skipped, leaving a false negative. Full-domain coverage correctly reports unresolved known capture, but that does not invalidate the already-qualified negative.

Minimal probe: use `fixture(root, True, empty=True)` from `tests/test_evidence_audit.py`; add a separate `data/processed/capture_events/unqualified.csv` containing `OTHER,capture,1,2026-09-28T21:00:00+09:00,28.15,129.3`; add the normal complete-coverage declaration for the original empty source. Audit returns PARTIAL, `UNRESOLVED_KNOWN_CAPTURE`, denominator NOT_ESTABLISHED, **and label 0 at 21:00**. Using the existing `build_request` fixture then returns builder PASS with labels `[0, null]`.

Action: reconcile eligible sessions/units against all known capture candidates and unresolved quantities/conflicts/links before asserting noncapture. A located unresolved event masks at least its matching unit to UNKNOWN; unresolved events that cannot safely be localized must conservatively prevent the affected scope's completeness. Retain valid qualified positives independently. Verify the builder cannot carry the contradicted zero forward.

## Important 2 — Empty bytes or an unrelated CSV header pass as a complete zero log

File: `src/evidence_audit.py:155–158, 323–326, 392–410`.

`csv.DictReader` has no required-header/schema validation. A zero-byte source or a one-line `not_a_capture_schema` file yields no rows, no rejections and no source failure. With valid matching receipt/review/declaration hashes, session and full-domain coverage accept it as a complete empty capture log. This is materially different from the intended valid, explicitly empty, schema-bearing capture CSV.

Minimal probe: start with the qualified empty fixture; replace `captures.csv` with either `b''` or `b'not_a_capture_schema\n'`; update receipt byte size/hash and all dependent review/source-reference hashes, retaining valid source bindings; add `complete_coverage`. Both cases return **audit PASS**, **label 0**, **ESTABLISHED_FOR_DECLARED_DOMAIN**, no failed checks and no requirements.

Action: validate the source schema even when it has zero rows and record which concrete sources were successfully parsed as capture logs. Sessions/coverage must reference those audited capture sources, not merely any hash-valid file carrying an `outcome_label` role. Keep the valid header-only empty CSV case working; malformed/unknown-format files cannot establish zero outcomes.

## Important 3 — Legitimate noncapture rows poison capture-log completeness

File: `src/evidence_audit.py:162, 182–183, 203, 405`.

Every event type other than capture is treated as a rejected capture and puts its entire source in `bad_sources`. Thus an otherwise complete mixed observation log with an explicit sighting or roadkill is indistinguishable from an unresolved malformed capture. The global `captures['rejected']` guard additionally blocks every declared complete scope, even for a safely classified noncapture elsewhere.

Minimal probe: add `S,sighting,1,2026-09-28T21:00:00+09:00,28.15,129.3,2026-09-28` to the valid qualified empty capture fixture, with all receipt/reference hashes correctly updated. Audit returns PARTIAL, rejected `NOT_EXPLICIT_CAPTURE`, session `CAPTURE_LOG_NOT_ELIGIBLE`, coverage `UNRESOLVED_CAPTURE_SOURCE`, and the searched unit becomes UNKNOWN. No capture ambiguity exists in this explicit sighting row.

Action: separate recognized noncapture/reaction records from rejected ambiguous/invalid capture candidates. Preserve and report both categories; only unresolved records that may affect the capture scope should block its completeness. Test a legitimate mixed capture/sighting/roadkill log alongside malformed/blank/ambiguous capture cases. This is not permission to count sightings as captures or ignore an ambiguous event.

## Important 4 — Trajectory and individual-link errors are not propagated consistently

Files: `src/evidence_audit.py:190–206, 249–270, 497`.

GPX point-level schema problems are recorded only inside segment `issues`; aggregate status considers `a.checks` and requirements. A fully rejected trajectory can therefore coexist with audit PASS. Some individual-link failures similarly set `individual_link_status='FAIL'` without emitting a failed check or quarantining the associated evidence.

Verified probes:

- Qualified fixture with complete coverage, GPX replaced by one point whose timestamp lacks timezone, and every receipt/review/reference hash correctly rebound: trajectory quality REJECTED, zero valid points, issue TIMEZONE_REQUIRED, but **audit PASS**, no failed checks or requirements, and complete-domain coverage established.
- Qualified count-two fixture plus individual rows `I1,C,1`, `I2,C,2`, `ORPHAN,NO_EVENT,1`: `individual_link_status=FAIL`, but aggregate only PARTIAL with no failed checks; source-qualified positive and negative units remain emitted. Coverage notices the link error, but the audit integrity contract does not propagate it as FAIL.

Action: emit explicit aggregate source checks for strict schema/time/location failures and invalid individual identities/links. Decide and encode appropriate invalidation scope, preserving unrelated diagnostic evidence while preventing source errors from looking like an all-PASS audit. Distinguish ordinary conservative QC limitations (for example a gap) from malformed evidence; not every diagnostic must become a fatal whole-corpus failure. Add tests asserting aggregate status/eligibility, not only nested issue strings.

## Important 5 — Existing learning input bypasses a relevant failed audit

Files: `src/learning_snapshot.py:23–37`; `src/master_orchestrator.py:329–355`.

The builder returns NOT_APPLICABLE for an existing `data/processed/model_learning.json` before checking audit FAIL. Master blocks the model branch on audit BLOCKED, not FAIL, and passes the existing learning snapshot to Task3 without the actual failed audit dependency. Task3's optional `upstream_status` field does not reflect this run's audit automatically.

Minimal probe: use the real three-night `ModelEvaluationTests.fixture`; add a receipt for its exact `evidence/observations.json` label source with correct hash but wrong byte size. Run the real master. Result: overall FAIL and evidence_audit FAIL, but builder NOT_APPLICABLE, **six computed folds and six REPLAY artifacts**, model_evaluation NOT_VALIDATED, and **candidate_generation PASS**. These computations consume a source whose actual receipt audit failed.

Action: preserving an existing learning input must not bypass validation of its relevant source/audit dependencies. Propagate the current audit failure into affected evaluation stages, or explicitly prove source-disjoint independence before continuing diagnostics. Do not rely on a caller-supplied learning flag. The overall FAIL prevents a false whole-run success, but does not repair the invalid child evidence or unnecessary execution. Operational scoring with a valid prediction does check audit FAIL; this finding concerns the existing-learning model branch.

## Important 6 — New builder work is outside the shared cooperative budget

Files: `src/learning_snapshot.py:18, 38–120` (especially line 110's no-op validator callback); `src/master_orchestrator.py:342–355`.

Master checks remaining budget before entering the model branch, but the new builder accepts no remaining-budget/deadline callback. Source hashing, feature/reference loops, row generation, validation and publication proceed without checks. It passes `lambda: None` to Task3 validation. The total 10MiB generated-output cap is checked only after computation; it is not a work/read/deadline budget. Only after building does master pass the depleted remaining budget to evaluation.

Minimal controlled-clock probe: real qualified fixture plus `build_request`; master limit 10 seconds; advance the shared monotonic clock from 0 to 11 during the first real builder `safe_path` source operation. Builder still returns **PASS**, publishes four generated files including model_learning, and only the subsequent model stage becomes BLOCKED. No full dataset or slow wall-clock sleep was needed.

Action: pass the parent's existing absolute deadline or shared check callback into the builder; check it in source/row/reference/publication loops and pass it to `_validate`. Return typed RUNTIME_BLOCKED on exhaustion and avoid publishing a successful derived snapshot after expiry. Add cumulative read/reference limits if necessary before allocating the entire generated corpus. Keep parent accounting and operational audit reuse; do not start a fresh independent budget.

## Important 7 — Builder extends a ledger while retaining its old content hash

File: `src/learning_snapshot.py:96–100`.

The audit correctly sets `ledger_sha256=digest(ledger_without_hash)`. The builder copies that ledger and adds `outside_universe_event_ids`, retaining the old digest. The resulting snapshot therefore publishes a ledger whose declared content hash does not describe its contents, despite builder PASS. This undermines the full-denominator lineage interface even though Task3 currently keeps restricted recall unvalidated.

Minimal probe: the unchanged existing qualified fixture plus `build_request` produces builder PASS and `outside_universe_event_ids=['C']`; `ledger['ledger_sha256'] == digest({k:v for k,v in ledger.items() if k!='ledger_sha256'})` is **false**.

Action: keep the original immutable ledger unchanged and place the universe-relative projection in a separate object referencing its digest, or explicitly preserve the parent-ledger hash and compute a new digest for the derived ledger. Validate both references before publication. Add an assertion covering the actual emitted ledger digest, not only its events/counts.

## Verification scope and retained limits

All probes ran against the reviewed implementation in temporary directories before their corresponding repairs. Mutation probes regenerated the receipt sizes and dependency hashes so their observed results were caused by semantic validation defects, not accidental stale-hash failures. Initial exploratory stale-reference fixture output was discarded and is not evidence for any finding above.

No full suite was repeated; 226 passing tests and the historical 14-GPX/266737-point, 947-UNKNOWN, 51-protected-file proof remain implementer evidence. The isolated builder-workspace and checkpoint/tamper tests are appropriate foundations, but do not cover the semantic gaps above. New tests should retain valid explicitly complete empty logs, all-UNKNOWN behavior, individual-count preservation, outside-universe outcomes and immutable source inputs.

Manual source-review/coverage declarations establish checked consistency, not authenticated scientific authority; this review does not demand an authentication redesign in Task6a. Actual historical role/completeness/ex-ante data may legitimately remain missing. Original recovered statements still have zero canonical admissions. Production trust, full scientific Stage1 gates and future model adapters remain outside this bounded approval.

Unchanged dependencies, exact remote-tree materialization, new remote CI and live Actions behavior were not independently reverified here. **Do not merge pinned 3dcc2f8 until the verified Important issues are addressed and scoped re-review passes.**
