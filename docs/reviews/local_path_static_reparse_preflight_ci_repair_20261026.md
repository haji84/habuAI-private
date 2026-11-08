# PR120 genuine-link test fixture repair

This is a test-only repair on parent
`5e6cbd476e083cd2dadd63a2916217d26ed494bd`. It does not change the runtime,
source policy, data, STATE, cycle, or production/scientific authority.

## Observed failure and cause

The actual Ubuntu job [40212040377 / 121225128855](https://github.com/haji84/habuAI-private/actions/runs/40212040377/job/121225128855)
ran 1479 tests in 605.806 seconds: **1 failure, 32 skips, NOT PASS**.
The sole failure was `CycleContractTests.test_junction_reference_is_rejected`:
`AssertionError: ValueError not raised`. The later frozen-cycle and secret-file
steps were **SKIPPED**, not successful. The real POSIX helper and engine tests
in this job passed; that does not make the complete failed job successful.

Before editing, the unchanged failing test was independently rerun on native
Windows: **1 test, 1 failure, 0.083 seconds**, with the same assertion. It made
ordinary directories pretend to be junctions by patching `Path.is_junction`.
The reviewed helper instead inspects actual no-follow file attributes. The
mock no longer represented a filesystem link; no runtime guard repair was
justified by this failure.

## Replacement fixture

The same test now first validates the ordinary temporary contract. It saves
its own `src` directory, creates a separate sibling temporary directory with
the **same expected helper bytes**, and links `src` to that directory. Thus
an unrelated hash mismatch or missing file cannot substitute for rejection.

On Windows it executes genuine `cmd /c mklink /J` and checks native
`is_junction()`, `is_symlink() == False`, and the actual reparse attribute.
On POSIX it creates a genuine directory symlink and checks its no-follow
link mode. The test has no platform skip and fabricates no OS/stat attributes.
`ValueError` containing **REPARSE** remains mandatory on both branches.

Delegating observers around `Path.open` and `os.scandir` record calls without
resolving the observed paths. Both lists must stay empty during rejection,
including any external payload open or target-directory scan. Finally the
fixture removes **only the link**, restores the saved local source directory,
checks both external helper and unrelated sentinel bytes unchanged, then
validates the restored ordinary contract again. Temporary cleanup therefore
does not recursively remove a linked target.

## Fresh verification

Runtime: bundled Python, `-B -X utf8`, real Windows filesystem.

| Command scope | Result |
| --- | --- |
| Unchanged predicate-mock test, before repair | 1 failure / 1 test, 0.083s |
| Repaired genuine Windows junction test | 1/1 PASS, 0.202s |
| Cycle contract, cursor, inventory, G0 forecast and G0 training modules | 140 tests: 135 PASS, 5 genuine platform skips, 0 failures/errors, 14.108s |
| Changed test compiled in memory; `git diff --check` | PASS |

The five skips in the combined command are the existing inventory tests for
four POSIX symlink paths and one Linux/fcntl engine integration. The repaired
cycle test actually ran; its POSIX branch still requires the next real Ubuntu
job. No fake fcntl or OS substitution was used.

The combined command loaded `test_codex_cycle_contract`,
`test_codex_cycle_cursor`, `test_master_inventory`,
`test_g0_forecast_contract`, and `test_g0_training_source_contract` with
`sys.path[:0] = ['src', 'tests']` and `unittest.TextTestRunner(verbosity=2)`.

All 96 frozen runtime references plus policy were checked byte-for-byte
between Git HEAD, index and the existing native snapshot
`habu-native-source-freeze-gbpeufs1`. Pointer/cycle physical bytes also match.
The snapshot's actual `scripts/check_codex_cycle.py` returned
`CONTRACT_VALIDATED`, code SHA
`d3bb83b1392dc5413e450aec8545712d21e522dfb3fa08ffa1a99d2977e7cdfa`,
cycle contract SHA
`ab585f5b4452ee412df0bcbe77a641f85dd8c8acee21fbc3acd4c48c44bf72a6`,
with fitting and production authorization false. This local check does not
relabel the skipped steps of the failed Ubuntu job as passing.

Only the existing test file and this new record are proposed for commit.
Independent repair review and a successful exact-head Ubuntu rerun remain
integration gates. Existing static-path/TOCTOU and other-enumerator limitations
are unchanged; this repair grants no source-authentication or scientific credit.
