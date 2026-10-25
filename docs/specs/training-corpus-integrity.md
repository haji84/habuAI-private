# PR46 training corpus integrity repair (2026-10-25)

## Baseline and scope

- Worktree: `features`; branch: `codex/pr46-eligibility-fix-20261025`.
- Original PR46 head: `daf09612f4ffd2cd389b0011cb7c615eb49fef3d`.
- Non-destructive, conflict-free merges: current-main
  `4a3605249dae6f22954aa3051541642ae47e3a53` via `c9f745c`, then exact
  PR32 `1dace8af7df5db2003d3da9949124c7434cbad29` via `8b0facb`.
- Implementation diff is measured from merged baseline
  `8b0facb3353271070ec72a2f9bc482c8b3472050`, not from the older PR46 head.
- Repair files: `src/training_corpus.py`, `src/train_spacetime_candidate.py`,
  `tests/test_training_corpus.py`, and this document. The existing fitter tests
  are in `test_training_corpus.py`; no second training pipeline is added.
- Remote PR46 branch remained `daf09612f4ffd2cd389b0011cb7c615eb49fef3d`
  when checked during implementation. Parent owns push, current source freeze,
  Linux CI, independent review and PR integration; PR remains Draft.

## Source-bound selector boundary

`select_training_rows(root, corpus_path, corpus_sha256, heldout_night,
fit_cutoff, *, require_features, exposed_nights=())` retains its API and
selection envelope.

Both corpus and bounded negative-receipt JSON now use an `object_pairs_hook`
that rejects duplicate keys at every object depth, including objects nested in
arrays and unknown metadata. It runs after the actual bytes and their SHA-256
have been checked. Canonical JSON alone could not detect a duplicate already
discarded by the default decoder.

A local `_source_path` guard retains the existing relative-path restrictions,
checks every existing absolute component (including the root and its ancestors)
with `lstat`, rejects symlinks, native junctions and Windows reparse attributes,
then checks resolved containment. It guards the initial corpus read, source
manifest hashing, negative receipt reads, and both final source/corpus rescans.
There is no new dependency on an unmerged master helper or private PR32 API.
This rejects static links before reading payload bytes; it does not claim an
atomic filesystem snapshot or defeat concurrent changes after the check.

The original caps remain 16 MiB corpus, 64 KiB scope receipt, 20,000 rows and
32 features. Source roles, independent active-search and complete-outcome
requirements, actual-byte SHA meanings, operational nights and strict cutoff
semantics remain unchanged. Missing eligibility evidence remains
`NEED_MORE_DATA`; UNKNOWN is not converted to a negative.

## Candidate fit boundary

Read-only audit found that the PR46 fitter's manually checked identity subset
accepted modified authority, qualification, event identity, fit boundary and
count assertions, including payloads with a recomputed selection digest.

`fit_candidate` now first obtains the validated copy returned by the existing
`models.research_selection.validate_selection`. The current selector envelope
was verified compatible without an adapter. The bounded fit, optimizer,
threshold defaults, output schema and development-only qualification are
unchanged. This shared gate validates exact structure and internal consistency;
it cannot reopen source files or re-attest discarded per-row readiness receipts.
Calling the source-bound selector remains required.

## Shared read-budget integration

The coordinator adds the optional `_read_context=ProspectiveReadContext` keyword
to the same selector and its internal read helpers. This is the existing shared
forecast byte ledger and absolute deadline, not a newly restarted child budget.
Actual corpus, source hashing, negative receipt reads and all final rescans are
charged to the same counter. Hashing streams bounded blocks; capacity exhaustion
stops before JSON parsing. The final selection seal is followed by another
deadline check, so no partial or late accepted rows are returned.

Five additional synthetic controls initially failed for the missing context API
or late sealing. They pass after integration: exact total actual-read accounting,
byte-cap early stop, already-expired caller deadline, expiry during final rescan
and expiry during final selection sealing. Calls without the optional context
preserve the legacy selection envelope and classification. This seam establishes
resource accounting, not source four-readiness or source authentication.

## Cooperative JSON deadline follow-up

Base `61127a94c6b9400044b551334316553af54120fd`, after the legacy candidate
merge. The shared context already prevented expired selections from being
returned. Independent review found extra JSON work could nevertheless begin
after hashing exhausted the absolute deadline, before the later check raised
`TimeoutError`. This is a cooperative scheduling gap, not a scientific admission
or result-return bypass.

Both corpus and negative-receipt readers now check the same optional context
after content hashing and before JSON parsing, pass it to the duplicate-key
object hook, and check again after parsing. The hook checks at object entry and
for each key/value pair. The corpus post-parse check precedes canonical encoding;
its existing post-encoding and final sealing checks remain. JSON decoding and
encoding are still synchronous operations, not OS-preemptible work.

TDD: four new controls failed on the old code: corpus hash expiry, negative
receipt hash expiry, parse expiry before canonical encoding, and object-hook
expiry (29 objects previously completed in total despite expiry after the first;
now one).
All still execute the actual hash/JSON/duplicate-key/encoding logic; wrappers
advance the shared test clock and observe work boundaries. Old and new versions
raise `TimeoutError`, while the repaired version stops the extra work earlier.

Native baseline was **48 tests: 47 PASS, one POSIX-only skip**. Final corpus
tests are **52: 51 PASS, one POSIX-only skip**; development walk-forward is
**7/7 PASS**, and the integrated legacy candidate suite is **25/25 PASS**,
including its real source-selector integration test. Combined final result is
**84 tests: 83 PASS, one skip**. Selection envelopes, duplicate rejection, byte
accounting, source SHA meaning, numerical fit, resource caps and authority are
unchanged. No new full-native or Linux success is claimed; parent owns exact
integration CI and source freeze.

Commands use `python -B -X utf8 -m unittest discover -s tests -p <file> -v`
for `test_training_corpus.py`, `test_development_walkforward.py`, and
`test_prospective_candidate_model.py`. Transient logs are
`training-corpus-json-deadline-red-20261025.log` and
`training-corpus-json-deadline-green-test_*-20261025.log` in the Windows temporary
directory. Only this document and the corpus source/test are changed by this
follow-up.

## Verification

Native Windows, CPython 3.12.14. All fixtures are synthetic.

1. Merged baseline: existing corpus/fitter tests 36/36 PASS.
2. New selector regressions against old implementation: 19 assertion failures,
   comprising 10 duplicate-JSON and 9 real Windows junction scenarios. The old
   selector actually read external target bytes before those failures.
3. Selector repair: 42 tests, 41 PASS / 1 POSIX-only skip.
4. Fitter regression against old fitter: five failures for authority,
   qualification, duplicated capture event, rehashed fit cutoff equal to the
   held-out night start, and false counts. A sixth UNKNOWN case already rejected
   by the old fitter is preserved.
5. Final related regressions: 151 tests, 149 PASS / 2 POSIX-only skips:

| Test file | Run | PASS | Skip |
| --- | ---: | ---: | ---: |
| `test_training_corpus.py` | 43 | 42 | 1 |
| `test_research_selection.py` | 25 | 25 | 0 |
| `test_prospective_inputs.py` | 58 | 57 | 1 |
| `test_prospective_candidate_model.py` | 8 | 8 | 0 |
| `test_prospective_spacetime.py` | 10 | 10 | 0 |
| `test_development_walkforward.py` | 7 | 7 | 0 |

Run each with `python -X utf8 -m unittest discover -s tests -p <file> -v`.

The real junction tests cover root, root ancestor, `data`, `data/processed`,
`evidence`, `features`, a link inserted after manifest binding before receipt
read, and links inserted before final source/corpus rescans. An observer wraps
real `Path.open` and counts reads resolved under the external fixture target;
all repaired cases count zero. Junctions are actual OS links (`is_junction`
true, `is_symlink` false), created with PowerShell. All paths are checked inside
one temporary work directory before moves/removal. Cleanup uses `os.rmdir` on
the junction itself, verifies a preserved target sentinel, removes the link
before temporary recursive cleanup, and restores the original fixture tree.
The POSIX symlink regression remains present for Linux CI.

Full native suite was run after selector repair and before the final two-line
fitter connection: **574 tests, 114 errors, 1 failure, 2 skips; exit 1**. The log
contains 463 passing-test lines; setup-class errors affect accounting, so this
must not be interpreted by subtracting errors from `testsRun`.

| Observed failure group | Count |
| --- | ---: |
| Windows lacks `fcntl` | 91 errors |
| Missing `sklearn` | 1 error |
| Windows symlink privilege (`WinError 1314`) | 2 errors |
| Bash executable unavailable in Pages bootstrap tests | 4 errors |
| Existing historical source SHA/size checks | 16 errors |
| Owner-count assertion encounters source-byte gate first | 1 failure |

The source-byte failures cover the Aug31 GPX, native Library TXT, August GPX
review/sample/reconciliation, crosswalk and remaining-night recovery tests.
`test_owner_monthly_count_does_not_override_missing_raw_event_bytes` expected
`Owner-confirmed August 47`, but the checkout failed earlier with
`Library native byte SHA or byte count does not match`. `core.autocrlf=true`
alters historical text checkout bytes; originals were not rewritten. The same
failure categories were recorded before this repair in the separate main-based
master audit. A green native full-suite result is not claimed. Parent requested
focused final regressions rather than repeating this known-failing Windows
full suite; final Linux CI remains pending.

Local transient logs: `training-corpus-red-20261025.log`,
`training-corpus-green-20261025.log`, `training-corpus-fitter-red-20261025.log`,
`training-corpus-full-20261025.log` and
`training-corpus-final-test_*-20261025.log` in the Windows temporary directory.

## Deferred work and authority

- Source four-readiness expansion awaits the shared closure API. This patch
  does not certify those missing scientific/source obligations.
- The legacy GPX-only training entrance and cutoff-equality issues recorded
  during the initial audit were repaired separately in
  `a8392d39d9d281d5593a2362edd212310ee432f1`, merged by `61127a94`.
  Its required selection binding and development-only semantics are documented
  in `leakage-safe-feature-candidate.md`; this JSON deadline follow-up does not
  change its numerical routine or authority.
- No raw, ORIGINAL, existing receipts/reports, predictions, permissions,
  STATE or current-cycle files were changed by the implementation diff.
- Tests establish bounded software behavior, not real-data authenticity,
  calibrated probabilities, scientific confirmation, official issuance or
  Champion authorization.
