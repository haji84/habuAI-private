# Task6a private G0 materializer implementation plan

> Execute with TDD and independent review. Reuse existing PR155; the separate
> integration coordinator owns STATE/Freeze/push/merge after reviewed commits.

**Goal:** Materialize native Task6a observations into the existing source-bound
TRAIN_ONLY formats when independently supplied existing G0 components suffice;
otherwise preserve real diagnostics and precise BLOCKED reasons without fit.

**Architecture:** New `scripts/materialize_private_g0_sources.py` reuses native
`evidence_audit.audit_evidence`, unit keys and the existing G0 reader/selector.
Inputs are existing corpus and strict-manifest reference shapes. No new evidence
certificate, label parser, model family, source role or scientific threshold.

**Spec:** `docs/specs/g0-training-source-contract-v1.md`,
`docs/plans/master-goal-1642-training-corpus.md`, actual Task6a v1 envelope and
`training_corpus.py`. The separate `prepare_source` copies existing artifacts;
this adapter performs the observation/feature join without duplicating copying.

## Constraints

- Base9d494c66c5fa866114d7a407024bbaf2f51b6940; immutable raw/ORIGINAL/M0-M3.
- PUBLIC Git receives only code, synthetic tests and aggregate evidence.
- Native audit is performed at real current UTC; stored/self-resealed labels
  are never accepted as authenticated audit execution.
- Join canonical ledger events by existing physical unit key. Preserve event IDs
  and recorded quantities; never invent biological identities or timing precision.
- UNKNOWN remains unknown. Legacy sample-based Negative is insufficient without
  existing independent active-search AND complete-outcome600s scope receipts.
- Read source-provenance/feature columns from existing v1 corpus only. Ignore its
  caller-supplied labels/quality. Require unique physical joins and bound bytes.
- Preserve historical source availability. New derived/materialized/audit times
  are real new times, not moved before an old forecast boundary.
- Retrospective TRAIN may support a later future fit; historical forecast replay
  still needs its own ex-ante evidence. No invented historical P0/universe.
- Missing feature/validity/DAG components means BLOCKED/no strict TRAIN manifest.
  Complete supplied components are checked by unchanged real G0 selector.
- No fitter or production/Champion activation. Declared source consistency is
  NOT_ATTESTED; qualified real total remains null until evidence establishes it.
- One shared ProspectiveReadContext accounts native audit, references, final
  rescans and destination checks. Default standalone Task6a output stays intact.

## Interface and allowed files

`materialize_sources(source_root, private_output, *, night,
feature_corpus_ref=None, strict_manifest_ref=None, heldout_night=None,
fit_cutoff=None, forecast_cutoff=None, budget_seconds=300)`.

Create `scripts/materialize_private_g0_sources.py` and
`tests/test_materialize_private_g0_sources.py`; this limited plan is separate
from the coordinator's existing major specs. Optional shared-context plumbing
in `src/evidence_audit.py` plus focused tests is subject to coordinator agreement.

## Test and implementation sequence

- [ ] Baseline: existing evidence/G0/training tests with pinned Python.
- [ ] RED: missing components preserve native audit and BLOCKED, no candidate.
- [ ] RED: native positives preserve exact event IDs/counts; source/caller labels
  cannot create positives, exact physical conflicts fail.
- [ ] RED: sample Negative becomes UNKNOWN absent complete typed scope proofs;
  real supplied scope receipt rules remain the existing selector's rules.
- [ ] RED: valid existing synthetic feature/manifest components exercise the
  actual native audit and unchanged G0 selector after new readiness binding.
- [ ] Implement native audit, immutable private diagnostics and physical joins.
- [ ] Implement optional existing G0 projection/validity/DAG materialization,
  only after all joins and lineage/timing checks; no fallback feature values.
- [ ] Add hostile reference/hash/alias/duplicate/budget/late-failure/idempotency
  and forecast-vs-futureTRAIN time cases. Recheck originals and no completed
  receipt on failed final checks. Console output excludes personal payloads.
- [ ] Run affected suites; independent review on exact held code bytes.
- [ ] Reconcile available real artifacts privately; no duplicate route processing
  solely for version binding, no old0audit→global0 inference.
- [ ] Give reviewed commit and aggregate proof to integration coordinator. New
  source code needs new immutable Freeze and actual new exact-head Linux CI.
- [ ] Verify published HEAD/main CI and approved merge outcome; report actual
  learning counts, evaluation absence and source/field gates without success inflation.
