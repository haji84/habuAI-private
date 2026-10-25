# HB-A1 retrained ablation review

## Cross-runtime test oracle correction

PR106 Ubuntu run `40173137953` ran 1027 tests (21 skipped) and failed three new
tests that compared a serialized model SHA to the fixed Windows golden
`f90609a3ad2ca43aaab2db27363d2db810b38c061b17fb3b813f5dc4085212b2`.
The reported Ubuntu SHA was
`ec5d65f392d86440e484e437a8066b313c9c19bfc3671cec6b91bfa009acaffc`.
Those failures do not establish a difference between old and extracted numeric
implementations **on the same runtime**. Both use Python 3.12; the exact cause of
the cross-runtime low-level floating-point difference was not independently
localized here. No alternative hash is whitelisted and no numeric tolerance or
production implementation is changed.

The test oracle now uses an immutable full pre-extraction source fixture:

| Identity | Value |
| --- | --- |
| Source commit | `d9bd4d66e61ac20a4491230d2f5faec8634dff8f` |
| Source path | `src/prospective_candidate_model.py` |
| Git blob | `978c97c0fff6e89f57dda28430c92cc6ee80f716` |
| Git-blob UTF-8/LF bytes | 18,127 |
| SHA-256 | `aac9841c2013569966bc16ab2bb914ae893e873d8f299aa74a411db3a876a01a` |
| Local test fixture | `tests/fixtures/prospective_candidate_model_d9bd4d66.py.txt` |

The fixture is copied byte-for-byte from that Git blob, not regenerated from the
new core. Tests normalize checkout CRLF to Git LF, verify the pinned source SHA
before compile, then execute that checked local text in its own namespace.
No Git, network or downloaded runtime code is needed by CI. It is outside the
runtime source inventory and cannot act as another model/candidate dispatcher.
Its original gate/helper/optimizer/serializer/ranker bodies are preserved rather
than maintaining a hand-rewritten mirror of the new core.

The three brittle assertions now require complete model dictionaries and model
digests to match this independent reference on the active runtime. The main
equivalence test additionally compares complete serialized model text and complete
rank dictionaries. Reference fitting still succeeds with the production shared
core and current score function replaced by exceptions, proving oracle isolation.
A deliberately changed core intercept produces a different model and SHA, proving
the oracle still detects a numerical regression.

A new metamorphic test applies the same one-ULP `exp` perturbation to both old
and current implementations. Before repair it reproduced the problem locally:
the hardcoded golden assertion failed (`a824bfa3...` versus `f90609a3...`). After
repair their complete same-runtime artifacts match exactly under that variation,
without accepting an arbitrary platform hash. Native Windows Python 3.12.14
also matches the preserved old source exactly. These are synthetic software
regressions; actual Ubuntu same-runtime comparison remains for the new exact CI.

Only tests, the pinned test fixture and this review record change. The numerical
core, 320 epochs/LR/L2/scaling, serialized runtime schema, authority flags and
configuration source are untouched; the current runtime code freeze is unchanged.

## Coordinator integration metadata reconciliation

After the standalone implementation passed independent review, the coordinator
updated the companion calibration diagnostic's stale implementation-blocker text.
It now names the three still-missing parent dispatches (registered three-slot
HB-A1, retrained ablation and source-bound calibration), rather than claiming the
new standalone computation does not exist. Its numerical metrics and authority
flags are unchanged. The 22 diagnostic tests passed; the independent reviewer
checked the small source/test change and requested the corresponding present-tense
specification correction, which is included. Earlier immutable cycle01 is retained;
the updated runtime receives a new cycle02 before remote integration.

## Independent review

Verdict: PASS for the standalone software capability and nonselectable
development diagnostic. No blocking finding remains at exact phase-2 commit
`37929bec4789d622916b345d0ede64b22822d20f`, following numeric-core extraction
`d1baf869cf11c3cc3554bd8df6583309a73fbc09`. This is not a source, scientific,
confirmation, selection or production approval.

The independent reviewer read both changes and the fixed API specification, then
extracted `src` and `tests` directly from the exact Git commit into a separate
native-byte snapshot. Reviewed canonical Git-blob identities are:

| File | SHA-256 |
| --- | --- |
| `src/prospective_candidate_model.py` | `cb4587db85ba1707f0e84db2f96567695d36c4c353f8898e64aba8e3930ce2dc` |
| `src/models/hba1_feature_candidate.py` | `7ae0e155b3ab0670099f46674f2e9720a51ccd38c9a7440b631d2112a2dbdf2a` |
| `tests/test_hba1_feature_candidate.py` | `4c473a58bd26dc4d4673297014a00ba5fd7fa4bfb14d0d3f5433fc98e734fec6` |

Independent execution on that snapshot passed:

- External hostile/metamorphic harness: 30/30, 2.776 seconds.
- New HB-A1 tests: 28/28, 1.732 seconds.
- Existing prospective-model tests including the shared numeric core: 40/40,
  8.339 seconds.

The external harness is outside repository-owned code at
`../hba1-independent-probes-20261025.py`, SHA-256
`dbf1592407198a9c3faf50c3b784b6c28af71ffe6b151f5fd9f71bf053ebe134`.
It consumes the coordinator's pre-extraction 12-variant baseline,
`../hba1-legacy-numerical-baseline-20261025.json`, SHA-256
`057400bfd0c2f56ba6879c3626f7bdd0d0ea60dc68cfb31c274b4a34a43820d4`.
Every complete model dictionary, model hash and rank dictionary matched those
12 preserved variants exactly. Three additional shifted synthetic variants also
matched execution of the preserved `6c2d889` legacy source. `_validated_model`
and `rank_future` have no implementation diff in the extraction.

The shared core retains seven-feature order, 320 epochs, step 0.15, L2 0.04,
unpenalized intercept, row order, scaler floor and legacy sigmoid recipe. Masks
are exactly seven nonempty booleans. Each fit starts with fresh scalers and zero
coefficients on the same complete selected row set. Perturbing each dropped
column does not alter any fitted reduced state. The reduced fit differs from
deleting coefficients after a full fit. Its owned scalar snapshot survives
caller mutations; callbacks cancel projection, scaling, optimization and final
return. The extraction adds no clock or I/O.

The standalone `fit_hba1`, `predict_hba1` and
`describe_retrained_ablations` use that same core. The full model uses every
accepted training row, without silently invoking the legacy trainer's internal
last-two-night split. Engineering floors of 20 rows and five prior nights are
preserved. Their declared selection/source envelopes do not establish source
readiness or statistical adequacy independently.

The independent review found and reproduced the following defects before their
final repairs:

1. A model fitted through October 5 at 21:00 accepted a rehashed fit cutoff at
   October 5 at 07:01. The model now stores the actual maximum training window;
   reload checks its timezone, alignment, final training night and strict order.
   Cutoffs before and equal to that maximum reject; one second after it remains
   numerically valid without authenticating the claimed source history.
2. A canonical event used in one fold's TRAIN could move to a different night
   and unit in another fold's evaluation if absent from that fold's TRAIN. A
   bounded global event-to-physical-unit registry now rejects this movement.
3. An earlier evaluation's positive unit could become a later TRAIN negative,
   or the reverse, with empty event IDs evading the event registry. A bounded
   global physical-unit-to-binary-label registry now rejects both directions.

All three are covered by independently reproduced RED-to-GREEN probes. Same
physical unit, label and event can legally recur in later rolling TRAIN. A
different historical feature context remains allowed globally; each individual
full/ablation comparison still uses exactly the same frozen matrix. Canonical
event identity and binary truth consistency are distinct from source attestation.

A proposed missing-fold cutoff problem did not reproduce: all-fold preflight
already enforces selection fit cutoff before held-out 07:00, and future cutoff
within that operational night. Together those imply fit before forecast cutoff.
A contradictory later cutoff rejects even when an earlier fold lacks data; no
unnecessary algorithm change was made for that hypothesis.

Every recipe predicts the same full supplied future row set, then scores the
same known observed mask. Independent fixtures retain eight future predictions
while scoring four known units; the other four never become negatives. Mask
joins include row ID, night, UTC-equivalent window, physical cell and all raw
features. Flipping development labels changes metrics but not fitted model or
prediction hashes. The hand calculation `[1,1,1,0]`, full p=.75 and ablated p=.25
produces Brier .1875 and .4375, hence `ablated_minus_full_brier=+.25`; positive
therefore favors the full model. Paired summaries average nights equally. This
synthetic calculation is not an observed improvement or accuracy claim.

Preflight validates every fold before fitting. Insufficient support returns
`NEED_MORE_DATA` without models or partial metrics and cannot hide another known
contradiction. Unknown/bool labels, moved events, label flips, stale hashes,
invalid mask/group metadata, nonfinite fit state and prediction intermediates
reject. Finite extreme inputs that overflow are rejected before an invalid
linear score could be clipped into a plausible probability.

Combined-input byte/node and row/group/fold limits reject before parsing or
fitting as appropriate; no silent truncation occurs. All internal fits and
predictions share one public-call guard. All three APIs reject deadline expiry
after their final result digest. Existing validators have checks around bounded
operations; cooperative cancellation does not promise process preemption.
The independent no-I/O probe prohibits files, network, legacy internal fitting
and legacy area ranking. The ablation output contains evidence and diagnostics,
not a selectable model/candidate or a winner.

Every test here is synthetic. No real data fitting, raw/held-out read, source
qualification, confirmation experiment or production execution was performed.
The registry remains exactly `uniform`, `HB-A0`, `HB-B1`; HB-A1 is not appended as
a fourth candidate and is not wired into parent dispatch. Code, recipe,
selection and model hashes bind caller-declared content only, with
`source_authenticity=NOT_ATTESTED`, caller authentication dependency and all fit,
science, selection, promotion, official and production authorities false.
Actual-source fits and independent scientific confirmation remain unperformed.
The coordinator owns integration, the new source freeze, state and full Linux CI.
