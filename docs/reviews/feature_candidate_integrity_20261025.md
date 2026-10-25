# Feature candidate inference integrity repair, 2026-10-25

Base: `c0df86e7ab73c6a388e6e934a569e56f2e9721a6`.
Owned scope: `src/prospective_candidate_model.py`, its existing test file and
this review. This is a serialized-model admission repair, not a new candidate
algorithm or source/scientific certification.

## Reproduction and repair

An independently executed copy of the base module ranked the existing valid
synthetic fixture at `0.33976141`. Adding 10 to the intercept while retaining
the original `model_sha256` changed that probability to `0.99991178`; both
outputs carried the same SHA. Incomplete means/scales/coefficients could also
reach `_score` and its truncating `zip`, or leak an ordinary exception.

`rank_future` now admits an owned JSON snapshot before validating forecast rows
or scoring. It reuses the existing bounded research JSON copier: depth 12,
2,000,000 nodes, 16 MiB canonical bytes and 4,096 characters per string. The
snapshot's SHA is recomputed using the historical serializer's canonical JSON
settings, excluding only `model_sha256`.

Validation requires a supported v1/v2 diagnostic model, false authority flags,
seven finite means, seven finite positive scales and eight finite coefficients.
Boolean numeric values are rejected. Feature order is fixed to the existing
seven predictors. The minimal historical v1 format may omit `feature_names`
and selection metadata; any present feature list must match. V2 requires its
original full metadata, selection SHA and `NOT_PERFORMED` confirmation status.
Declared split dates must be valid, increasing and unique, precede the fit
cutoff and remain chronologically disjoint. Present counts and diagnostic
Brier must agree with the producer's existing structural bounds.

The old minimal v1 fixture remains verbatim, including its original content
and hash construction. A new full-v1 metadata regression also preserves its
serialized bytes and numerical output. No old serialized artifact is rewritten.
Scoring uses only the checked snapshot, so later caller-side model mutation
cannot change the numerical state associated with the returned SHA.

This SHA validates content consistency, not who trained a model, authenticity
of its sources or numerical re-execution of its fit. Rehashing a different
otherwise valid model creates a different content identity; it does not grant
source, official prediction or production authority.

## Verification

- RED: six new test methods against the base behavior produced 40 failures and
  five errors, counting subtests. The valid full-v1 regression already passed.
- GREEN: `python -B -X utf8 -m unittest discover -s tests -p
  test_prospective_candidate_model.py -v`: **31 tests PASS**, no skips.
- Related suite: candidate, research selection, training corpus, development
  walk-forward, prospective spacetime and fixed research adapter:
  **139 tests, 138 PASS and one POSIX-only skip** on native Windows. The skip
  is the existing source-symlink fixture, not a model-integrity test.
- The actual stale-hash repro is now `CandidateInputError: Candidate model
  digest mismatch`, before `_score` is called. Rehashed malformed vectors,
  nonfinite/bool values, zero/negative scales, feature order, authority,
  metadata, cyclic/oversized/non-JSON envelopes and caller mutation are covered.
- Existing v1/v2 fixture probability remains `0.33976141`; seven means,
  coefficients to 12 decimal places and development Brier `0.19376964` pass.
  AST comparison confirms every pre-existing function except `rank_future`
  remains unchanged, including the 320 epochs, L2, feature checks and 5+2 split.
- `git diff --check` passes. Raw, ORIGINAL, receipts, shared helpers, parent
  dispatch, fixed three-candidate protocol, state, policy and cycle are untouched.

Logs are in the native runtime's temporary directory:
`feature-candidate-integrity-red-20261025.log`,
`feature-candidate-integrity-green-20261025.log` and
`feature-candidate-integrity-related-20261025.log`.
Coordinator source freeze, independent review, PR publication and exact-head
Ubuntu CI remain separate work. No real field observations were fitted or
scientific accuracy/Champion/production eligibility established by these tests.
