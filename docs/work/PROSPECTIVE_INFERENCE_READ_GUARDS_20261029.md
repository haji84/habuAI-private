# Prospective candidate inference: bounded source rechecks

## Scope and baseline

Implementation evidence for a software reliability repair, based on main
`ef750b6c051e393eb8af82da77d20bd110af07e5`. Independent acceptance, the new
development-cycle freeze, exact-head CI and fresh-main verification are separate
integration gates; this document does not claim those gates have passed.

The existing prospective candidate inference checked model bytes, loaded and
rechecked the forecast inputs, then rescanned all sources through
`master_contracts.file_hash`. That final reader had no source-size or cumulative
read-byte ceiling. It also used a path guard that did not inspect ancestors of
the supplied root. Initial model loading used the same weaker path guard.

## Reproduced failure and correction

Five real-file regressions fail against the exact original source:

1. A parent-directory symlink substituted after the input loader returned was
   followed, and inference still returned a prediction when the bytes matched.
2. An input grown beyond the existing source limit after validation was opened
   by the final rescan before it eventually reported a digest mismatch.
3. A byte budget one byte below the total actual reads still returned a result.
4. Model bytes were opened through an ancestor symlink before the loader rejected
   that path.
5. A model grown beyond its smaller model limit was opened by the final rescan.

The repair reuses `prospective_inputs.ProspectiveReadContext`, its guarded local
path resolver and bounded byte reader for model reads and final rechecks, and
passes the same context through the existing input loader. The existing 128 KiB
model limit and 128 MiB per-source limit remain. The existing 384 MiB read ceiling
now accounts for initial reads and every rescan cumulatively across inference.
Inputs that exceed the cumulative actual-read ceiling return `InputCapacityError`
instead of silently completing with unaccounted I/O. A source read may consume
one extra sentinel byte to detect a limit breach, as the existing reader specifies.

The model's numerical computation, thresholds, selected rows, output fields,
qualification and production authority are unchanged. Sequential path and digest
rechecks are not an atomic filesystem snapshot or a hard interruption of an
in-progress operating-system read.

## Executed verification

Python 3.12.14 on Linux, using only temporary synthetic files:

```bash
python -B -m unittest discover -s tests -p test_prospective_inputs.py -v
python -B -m unittest discover -s tests -p test_prospective_spacetime.py -v
```

- Input suite: 65 discovered, 63 passed, two explicit native Windows junction
  skips, zero failures/errors.
- Candidate inference suite: 15 passed, zero skips/failures/errors.
- Original source with all candidate tests: the ten existing tests passed and
  all five new regressions failed, with no import or fixture errors.
- The exact cumulative byte boundary succeeds; one byte below it is rejected.
- A valid source-join-to-inference run produced the same 2,428 canonical result
  bytes before and after the change, SHA-256
  `27d46b285a71154f3c384af95e1017f7636862cffd787accbb176c7f15d10c01`.
  All six synthetic input files retained their hashes. It emitted two unit
  predictions and one development candidate, with
  `official_issuance_authorized=false` and formal status `NOT_VALIDATED`.

Those local checks did not execute the full suite or hosted CI. Native Windows
execution, actual source certification, real-data model fit, formal time-target/B2
completion and production P0 are not claimed.

## Hosted CI failure and test-call repair

The first exact-head hosted run,
[40751294754](https://github.com/haji84/habuAI-private/actions/runs/40751294754),
tested commit `90922183fbe2b2db71aa6f91f46ea2b7b84c239f`. Its full unittest step
ran 2,056 tests in 1,139.715 seconds and failed with one error and 38 skips.
`test_prior_verified_eligible_rows_can_fit_nonofficial_candidate` still called
the internal `_read_candidate_model` helper without its required `budget` and
`check` keyword arguments. The later hosted cycle and secret-file checks were
skipped; this run is not a CI PASS.

The same existing test reproduced the `TypeError` locally before repair. The
test now supplies a real `ProspectiveReadContext` and `_LocalByteBudget`, with
the same 128 KiB model-file limit used by inference. Its original full model
equality, training provenance, nonofficial authority and absence-of-ORIGINAL
assertions remain. An added assertion confirms that the shared context charged
exactly the model bytes read. No production source or published cycle changes
are needed for this test-call correction.

After this correction, actual local synthetic-file suites passed:

- Training corpus: 52 discovered, 49 passed, three native Windows junction skips.
- Prospective inputs: 65 discovered, 63 passed, two native Windows junction skips.
- Candidate inference: 15 passed, no skips.
- Total across these disjoint suites: 132 discovered, 127 passed, five skips,
  zero failures/errors. The focused one-test RED/GREEN is a subset, not an
  additional passed test.
- `python -B scripts/check_codex_cycle.py`: `CONTRACT_VALIDATED` for the unchanged
  published candidate code/cycle.

Latest amended-head hosted CI and fresh-main verification remain required. The
failed earlier run cannot satisfy either gate. The repository's full hosted CI
also includes existing source-audit tests; the synthetic-only scope above applies
to this local repair verification, not to every test in hosted CI.

## Integration requirement

The original main cursor pointed to
`protocols/development/cycles/20261029-p0-readonly-preflight-111-01.json`.
That immutable cycle binds the original `src/prospective_spacetime.py` digest.
The PR now adds
`protocols/development/cycles/20261029-prospective-inference-read-guards-01.json`
and advances only `protocols/development/current-cycle.json`, preserving all old
cycles. Its local validation does not replace exact-head hosted data-intake CI,
independent review, safe integration or distinct fresh-main verification. This
test-only follow-up preserves both the original and new published cycle bytes.
Existing unrelated lane state and scientific blockers remain in force.
