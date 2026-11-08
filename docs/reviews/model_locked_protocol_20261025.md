# Locked protocol metadata validator: design and implementation record

Base: reviewed G0 `b62b569d6214f22e10463488af5b9ad107c72469`.
Coordinator approved this bounded design on 2026-10-25. Parent Master Goal,
training-corpus/feature-model/composite plans and the fixed G0 policy govern it.

## Design

Implement one pure metadata validator, not an evaluator or evidence importer.
It receives a plan and an explicitly supplied exposure-history projection; it
never opens files or accepts labels. Existing artifacts are referenced by their
hashes. TRAIN_ONLY group metadata carries night, geography, corpus-selection hash
and aggregate readiness. Forecast cohort metadata separately carries night,
cutoff, geography, universe/feature hashes, feature readiness and an independent
outcome-ledger commitment. No historical forecast cutoff is invented for a
retrospective training group.

An alternative was adding folds directly to LearningSnapshot v1, which would
recouple retrospective training to historical forecast availability. A second
was implementing a complete sealed-outcome persistence service, which exceeds
this pure boundary and requires parent-owned trust/persistence integration.
The approved approach leaves both existing interfaces intact.

All recipes share one immutable set of folds/cohorts; at most three registered
recipes with uniform first. Frozen selection, model and prediction commitments
precede confirmation forecast cutoffs. Research-exposed and already consumed
confirmation nights cannot be reintroduced under new IDs. Exposure history is
mandatory and hash-bound, but even an empty supplied history remains an
unverified declaration, never authenticated evidence of untouched confirmation.

Each fold has a purpose, training-group IDs, forecast-cohort IDs, explicit
geographic holdout IDs and nonnegative integer embargo nights. Same-night train
and evaluation are forbidden regardless of group ID/geography. Training must
precede every evaluated night and the frozen embargo boundary; source readiness
must precede the minimum fit/frozen cutoff, forecast cutoff and evaluated-night
07:00 JST. Forecast features separately precede their own actual cutoff. Held
out geographies cannot occur in a fold's training scope. Development evaluation
nights precede all sealed confirmation nights, which are disjoint. A confirmation
fold's model is frozen once; confirmation nights cannot become later training.

Return deterministic protocol/fold identities and explicit structural counts,
while retaining `scientific_status=NOT_VALIDATED`, `fit_authorized=false`,
`production_authorized=false`, and Stage1 denominator `NOT_EVALUATED` until an
independent complete ledger is verified. Five confirmation nights is only a
declared engineering floor; metadata hashes do not prove independent coverage,
source authenticity, label eligibility or scientific adequacy.

## Implementation plan

Files: create `src/evaluation/locked_protocol_manifest.py` and
`tests/test_locked_protocol_manifest.py`; maintain only this implementation
record. No dependencies, shared STATE, original data, fitting code, G0 policy or
frozen G0 manifest changes.

Interface: `validate_locked_protocol(plan: dict, exposure_history: dict) -> dict`.
The history projection has exactly `research_used_nights` and
`confirmation_used_nights`, matching existing protocol vocabulary. The result
hash binds the entire plan and that exact history. Errors raise `ValueError` with
specific reason codes; no input is mutated.

1. Write fixtures with hand-checked past training nights, a development night and
   five future confirmation nights. Write failures for same-night laundering,
   embargo/readiness equality, late forecast inputs, geography overlap, reused
   research/confirmation, candidate/denominator narrowing and missing history.
2. Run the tests RED against the absent implementation, then implement strict
   fields, bounded canonical metadata, fixed-policy binding and fold checks.
3. Run targeted tests GREEN plus G0/handoff regressions. Run the project suite,
   recording the known Windows/Linux and checked-out-source limitations by name.
4. Review the final diff and immutable input/output behavior; commit the bounded
   source/tests/record for independent parent review and Linux exact-head CI.

Review focus: distinct IDs for the same operational night; a readiness timestamp
equal to a cutoff; an outside-universe event omitted by universe filtering;
fresh-cycle laundering of exposed confirmation; metadata authenticity confused
with scientific validation. No actual outcome read can be introduced to resolve
these blockers.

## Execution record

Implemented one pure validator with strict metadata fields, shared policy SHA,
bounded input, group/cohort/fold references and deterministic receipts. No real
cohort, outcome, model or measured accuracy is asserted by the synthetic tests.

TDD evidence: the initial test import failed because the requested module was
absent. After implementation, all 31 original behavior tests passed. A separate
readiness regression then failed because a claimed training selection could
predate its own observation night. The validator now rejects aggregate readiness
earlier than that night's 07:00 start, and all 32 tests pass (0.013s).

Additional targeted regressions: G0 19 PASS (0.278s), handoff 5 PASS (0.046s).
The validator leaves input objects unchanged, repeats exact receipt hashes,
executes with file-opening disabled, rejects supplied labels and per-recipe fold
masks, and preserves NOT_VALIDATED/NOT_EVALUATED/false authority on valid metadata.

Full project command was executed on this Windows runtime: **359 tests in
12.134s, one failure and 105 errors, exit 1**. This is not a green project suite.
The retained local log is
`C:\Users\qq113\AppData\Local\Temp\habu-v-fullsuite-20261025-_26wid91.log`.
Named failing groups include `test_champion_registry`, `test_master_e2e`,
`test_master_orchestrator`, `test_prediction_lineage`, `test_pdca_e2e`,
`test_master_scoring`, `test_p0_readiness`, `test_run_pdca`, and master-integration
cases in `test_evidence_audit`/`test_learning_snapshot`, which encounter the
existing Linux-only `fcntl` import. `test_legacy_chronological_walkforward` cannot
import the unavailable local `sklearn`. Four `test_pages_bootstrap` cases cannot
find the Bash executable. Historical actual-source tests (`test_aug31_road_search_candidates`,
`test_august_75_fauna_motion_review`, `test_august_evidence_review_queue`,
`test_august_fauna_sighting_context`, `test_august_native_evidence_packets`,
`test_august_sampled_exposure`, `test_gpx_outcome_source_matrix`,
`test_reconcile_actual_gpx_exposure`, `test_recover_remaining_august_nights`,
`test_recover_two_habu_nights`, `test_remaining_august_road_candidates`) encounter
the known checkout/native-source hash differences. The one assertion failure is
`test_owner_monthly_count_does_not_override_missing_raw_event_bytes` in
`test_august_native_evidence_packets`: source-byte failure occurs before the
expected owner-count diagnostic. No test protection or original byte was changed
to turn these environment/source failures green.

All **149 tracked Raw/ORIGINAL/recovered-ORIGINAL files** were SHA-256 hashed
before and after that full run; zero files changed.

Rulings: embargo length is a preregistered integer (0-365 nights), since the
normative policy does not authorize inventing a universal minimum; same-night
training is rejected even at zero embargo. This slice supports one static model
and prediction commitment for confirmation, so confirmation features must also
predate that freeze. Adaptive refitting or rolling confirmation is deliberately
outside this implemented protocol. An exposure-history declaration, including
an empty declaration, remains unverified and never authorizes scientific work.

Original G0 cycle closure will correctly be stale after adding this module;
the coordinator owns a later cycle manifest rather than rewriting the old frozen
manifest in this worker. Independent parent code review and exact-head Linux CI
remain required before integration.
