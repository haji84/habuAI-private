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

No full-suite, hosted CI, native Windows execution, actual source certification,
real-data model fit, formal time-target/B2 completion or production P0 is claimed.

## Integration requirement

The existing cursor points to
`protocols/development/cycles/20261029-p0-readonly-preflight-111-01.json`.
That immutable cycle binds the original `src/prospective_spacetime.py` digest.
The coordinator must create a new immutable cycle for the reviewed code, advance
only `protocols/development/current-cycle.json`, and preserve all old cycles.
The existing `python scripts/check_codex_cycle.py` gate remains required, followed
by exact-head data-intake CI, independent review, safe integration and a distinct
fresh-main verification. Existing unrelated lane state and scientific blockers
remain in force.
