# Independent constant-Poisson diagnostic review

Verdict: **PASS for the standalone declared-cohort numeric diagnostic**, exact
source `a8dae913453d9228bbd750d47443e0206dfb5ab5`, against approved specification
`52e5393489eddfd26f7d3272d6e1f2fb52c209a5`. Actual Ubuntu integration remains a
separate coordinator gate. This does not establish a qualified real cohort,
scientific adequacy, a source forecast, parent integration or execution authority.

## Exact release and independent execution

The author commit adds only the new pure module, its tests and author review.
Existing count feasibility, selection/G0 gates, model registry, parent code,
historical M0-M3 and originals are unchanged. Canonical Git blobs checked after
the fresh processes completed:

| File | Bytes | SHA256 |
| --- | ---: | --- |
| `src/models/constant_poisson_diagnostic.py` | 19349 | `6e2a45ed000f214c74c57ed66e5351f753d55da1f157b7fa5ad9688598406c56` |
| `tests/test_constant_poisson_diagnostic.py` | 25713 | `f93f1e12a732aebe1eb02c4fd26ca37938d3110bd88d72f2186acc5781b33cdd` |
| `docs/specs/constant-poisson-diagnostic-v1.md` | 15814 | `422c6c4f4c23565339246b19a311ddee1fa183dcd61cc0bbe5e5a3fc78d33f2f` |

Fresh independent executions on that exact release:

- External **22/22 methods PASS, 0.345s**, exit zero, including the final explicit
  unequal-exposure pooled-rate versus average-row-rate control.
- Authored **29/29 methods PASS, 0.441s**, exit zero; no skips.
- Both Python files compiled from their Git bytes; `git diff --check` passed.

Root/author separately report 160/160 methods PASS in 5.313s, including the 29
new and 131 unchanged gate regressions. This review did not repeat that broader
group or claim a native full-master/POSIX run. The independent harness is outside
the product Git tree at `.worktrees/constant-poisson-independent-probes-20261025.py`,
SHA256 `b8450510b1d8894e766ef55fdd72021e278ffa56e779dca74186d60d3d012465`.

The first external draft invocation had four fixture errors, not four product
defects: zero-only controls retained an unused outcome node, and one control
illegally reversed the selector's required deterministic row order. Only the
external fixtures were corrected: remove unbound nodes from the declared subset
and permute projection rows while preserving selector order. The subsequent
working-source 21/21 and 22/22 passes were provisional; the fresh exact-release
22/22 run above supplies the final independent gate.

## Concrete draft findings repaired

1. The draft `_finish` bounded only the object before adding `receipt_sha256`.
   An actual fitted fixture had 5201 pre-receipt bytes and 5285 complete bytes;
   an output-only 5284-byte cap still returned all 5285. The observer delegated
   the real streaming encoder and did not weaken input validation. Author tests
   reproduced three RED cases for fitted, NEED and scenario receipts. The final
   `_finish` streams the complete sealed output under the same cap/guard and
   checks again. All three independent complete-output cases now reject at the
   cap, without increasing it or returning partial data.
2. Root identified scenario model rows being owned before the row-count check.
   Independently confirmed with an actual valid six-row model, MAX_ROWS=5, and
   an observer around the real `_owned`: scenario copied one list before the
   capacity rejection, while standalone validation copied none. Author RED then
   shared `_pre_model` before both paths. The final independent sentinel confirms
   both reject before any owned-copy call. No large allocation was needed to
   demonstrate the ordering defect.

## Estimator and admission checks

The new API owns a bounded combined snapshot and calls the existing
`assess_count_feasibility` exactly once with remaining time and the shared guard.
An observer confirmed detached inputs, the unchanged complete sealed assessment
and no filesystem/network call. Caller mutation at the actual child-gate seam
does not change the owned result. No binary label, event count or GPX-derived
duration supplies a missing count/exposure.

The six-unit synthetic fixture contains three capture events but six individual
IDs and 1800 measured seconds. Independent closed-form controls verify
lambda=1/300, log likelihood `-6-3*log(2)` within 1e-12, and a strict likelihood
maximum against six alternative rates. Counts use integer sum; exposure uses
row-ID-ordered fsum. Permuting projection records preserves the ordered numeric
cohort/statistics while changed input hashes appropriately change model identity.
This checks a pooled exposure likelihood, not an average of individual row rates.

All-zero and positive-only complete declarations produce diagnostic models even
when binary readiness is NEED. Exact zero rate/log likelihood has no pseudocount.
Empty cohorts, any missing count/individual ledger/row, UNKNOWN complete scope,
missing effort or zero effort yield no model and no partial rate. Supplied owner,
type and same-observer cross-cell overlap contradictions still reject when other
data are missing. The existing source/availability gate is reused, not cloned.

## Checked model, scenario and resource controls

Independent rehashed-model tests reject changed rate/totals, integer-versus-float
or boolean statistics, false-versus-zero flags, alternate recipe, extra fields,
signed negative zero, physical duplicates and contradictory fit/window/heldout
chronology. JSON validation returns a detached owned object and recomputes the
cohort and analytic sufficient statistics. Opaque input/assessment hashes cannot
be re-attested from that compact table: a coherently reconstructed model remains
a new declaration with false authority, as the specification requires.

Twenty-five scenario masses were compared with an independent 80-digit Decimal
factorial/exponential oracle, with explicit 1e-12 relative-scale tolerance.
Closed cases distinguish no requested count, zero mean/count zero, structural
ZERO_MASS, and finite-log probability underflow. Boolean/nonfinite/out-of-range
inputs reject. Positive-product underflow, rate overflow and finite-rate mean
overflow raise NUMERIC_BLOCKED instead of clipping. The deliberately extreme
compact tables are numerical declarations, not assertions of physically measured
subnormal search intervals. Models contain no cached libm likelihood; no
cross-platform whole-receipt golden or hash allowlist is used.

The independent tests cover combined JSON/width/row caps before child admission,
complete final receipt caps, and expiry after model/fit/scenario hashes. Nine
caller exception classes retain object identity at all three public entries;
actual child-gate probes include ValueError and a named capacity exception.
The private callback carrier preserves that origin through existing child error
classification. Bounds remain cooperative for sorting/stdlib operations, not
hard preemption or hostile-thread isolation.

Every returned model/result keeps NOT_ATTESTED source authenticity,
CALLER_DEPENDENCY_REQUIRED source authentication, NOT_ASSESSED adequacy and all
six authorization fields exact false. Scalar exposure is a caller counterfactual,
not measured or ex-ante planned future effort. G0 planned-effort restrictions,
data qualification, source parsing, confirmation, registry and parent dispatch
remain unchanged. No actual source data were fitted by this review; real
qualified count TRAIN/scientific-fit evidence and official performance remain
unestablished.
