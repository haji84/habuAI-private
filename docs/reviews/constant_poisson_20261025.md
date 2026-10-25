# Constant Poisson diagnostic implementation

Approved specification: `docs/specs/constant-poisson-diagnostic-v1.md`,
`52e5393489eddfd26f7d3272d6e1f2fb52c209a5`; base main
`9c06f3d8b059439991f444dee8c7b30f35b2b6bc`.

Plan: first record missing-API RED with independent closed-form likelihood and
maximum controls; implement the three bounded pure APIs; then exercise whole
cohort admission, zero boundary, portable JSON model integrity, conditional
likelihood edge cases and shared-resource failures. Existing count feasibility
is called exactly once per fit and is not modified. No TRAIN/source parser,
forecast, registry, parent, historical M3, state or permission is changed.

Only synthetic fixtures may be fitted. Actual qualified count TRAIN remains0.
Constant-rate homogeneity, independence, ascertainment and generalization remain
unproved; all authority flags are false. Conditional scenarios are caller-supplied
counterfactual scalars, not actual or ex-ante planned future effort. Existing G0
planned_effort remains CAPABILITY_BLOCKED.

## Verification

Native Windows Python3.12.14, no numerical backend/OS facade or installation:

- Initial actual RED:3 missing-module failures for the analytic six-individual /
  1800second fit, independent likelihood-maximum controls, checked detached JSON
  export and conditional Poisson scenario. All subsequently passed.
- Independent working-source finding1: adding receipt_sha256 after its only
  bounded encoding could let the complete returned JSON exceed its cap. Author
  regression reproduced3 RED subcases (fitted, NEED and scenario). `_finish`
  now streams the complete sealed JSON under the same cap/guard, then checks
  again; those cases pass. No limit was raised.
- Independent working-source finding2: scenario's initial owned copy preceded
  model-row preflight. Author regression was RED with a real six-row model,
  MAX_ROWS=5 and an owned-copy sentinel. Validator/scenario now share the same
  pre-model count check, before either initial copy; GREEN.
- Final authored29 tests and131 unchanged count/selector/G0 forecast/training
  regressions:160/160 PASS,5.313s. Exact command below. No skips.
- Initial related invocation loaded146 passing cases plus one fixture-import
  error: G0 training tests import `test_training_corpus` as a top-level fixture.
  Adding existing `src`/`tests` directories to that invocation's sys.path fixed
  the harness; no existing test or product code was changed.

The closed fixture gives rate1/300 and training log likelihood
`-6-3*log(2)` within1e-12, and beats independent alternative-rate likelihoods.
Unequal measured exposure verifies pooled count/seconds rather than average
row rates. All-zero and positive-only consistent cohorts fit diagnostically,
despite binary readiness being NEED; missing/UNKNOWN/zero-effort rows never
yield a subset model. Feasibility is called exactly once and its complete sealed
assessment remains unchanged.

Checked JSON tests cover stale/rehashed parameter/statistic/recipe/identity/flag
changes, type and signed-zero differences, deterministic row-order fsum, source
identity changes without coefficient changes, and detached inputs/exports.
Model identity contains no cached libm likelihood or platform values. Closed
likelihood/mean controls use explicit numerical tolerances; a finite1000.000...
mean was not rounded to satisfy an exact1000 assertion. There is no platform
hash allowlist, cross-libm whole-receipt golden or expected-hash regeneration.

Scenario controls distinguish exact ZERO_MASS from finite-log probability
underflow, and reject nonfinite arithmetic, rate overflow, conditional-mean
overflow and a positive product rounding to zero. A deliberately reconstructed
coherent numerical model tests that integrity cannot authenticate its opaque
historical source digests. That is explicitly a new declaration, not proof that
those digests attest the reconstructed cohort.

Capacity, elapsed budgets, smaller child remaining budgets, expiry after each
model/fit/NEED/scenario seal and after scalar math/export are tested. Caller
exceptions retain their object identity even when their class is normally
classified by the existing child gate; a private callback carrier passes through
those handlers and is unwrapped at the public boundary. No partial result is
returned after a failure. Sorting, JSON parsing and standard-library arithmetic
remain cooperative rather than hard-preemptible operations.

Reproduce the successful target/regression run from the worktree with the
bundled Python and `-B -X utf8`:

```python
import sys, unittest
sys.path[:0] = ['src', 'tests']
suite = unittest.defaultTestLoader.loadTestsFromNames([
    'tests.test_constant_poisson_diagnostic', 'tests.test_count_feasibility',
    'tests.test_research_selection', 'tests.test_g0_forecast_contract',
    'tests.test_g0_training_source_contract'])
result = unittest.TextTestRunner(verbosity=1).run(suite)
sys.exit(not result.wasSuccessful())
```

Independent exact-source review and coordinator-owned Ubuntu integration remain
separate gates. Existing count feasibility/selection/G0, registry, historical
M0-M3 and original data are byte-unchanged by this implementation.

The Independent review section is reserved for the reviewer.


## Coordinator integration checkpoint

Independent exact-source review6ba5a782 approves sourcea8dae913: fresh external
22/22PASS0.345s, authored29/29PASS0.441s/no skips; module19349canonical bytes,
SHA256 `6e2a45ed000f214c74c57ed66e5351f753d55da1f157b7fa5ad9688598406c56`.
After normal merge of actual PR115 mainc860795, coordinator reran the same160
new/affected regressions:160/160PASS6.801s/no skips. Runtime and tests remain
byte-identical to the independently reviewed source; only metadata follows.

New immutable cycle `20261025-constant-poisson-diagnostic-01` freezes95native
Git-index runtime references. Actual native snapshot CLI CONTRACT_VALIDATED,
codeSHA `4c76ae781a18d084c8ec56f40304756dac15e8bd9086af3bd11168552233254c`,
cycleSHA `71fd8e27cf473eaaaaf4b4ef160ac6acf069ff44fbf45976f8909ea44023aab8`.
Prior cycles and the PR115 failed attempt remain preserved. STATE reconciles
actual PR115 exact1387/sk23/326.041s and fresh1387/sk23/529.985s, including actual
POSIX backend/link checks, cycle CLI and secret guard PASS. New Poisson exact/
fresh Ubuntu gates remain pending. Synthetic numerical fitting is not source
or scientific fit authorization; real qualified TRAIN/scientific fits remain0.
