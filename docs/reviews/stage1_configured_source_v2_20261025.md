# Configured Stage1 source v2 implementation review

Branch `codex/stage1-configured-source-v2-20261025` starts at pure review
`82e302235f21e370755536f6ffe850455bbd36ec`, normally merges reviewed preparer/parent
`cb2a1c12ef3e3a181f3f6210c24d30479e66261a` and main
`c2abdd990c60aafa5289652fb9e4bdaea0879705`. The clean pre-edit merge is
`70b3fff12ecf7241603bca35b5b7188cc144e679`. No history reset or force update.

Owned changes are the source adapter, one new configured-source test module,
the new contract spec and this review. Parent/pure/config/model implementations,
Raw/ORIGINAL, evidence policy, historical receipts, STATE and freeze are unchanged.

The implementation reuses the existing source graph/CSV/causal/scope/rescan path
and native prediction binder. It adds one combined owned config/forecast/prepared
snapshot and configured lineage checks before evaluation reads, then projects to
the reviewed pure Stage1 v2. HB-B1 native recipe and ranking meaning remain intact.
Parent request v3 still explicitly blocks nonlegacy Stage1; this source API is a
separate callable and does not grant implicit parent opt-in.

## Pre-edit compatibility baseline

An unmodified native Git archive (`git -c core.autocrlf=false archive`) executed
four existing v1 fixtures. Native source SHA-256 was
`ffc0f686481f822b1409fef5645c72e1ef68f41c279af1fdf4205773822b9037`.
The complete external oracle JSON is 17,067 bytes, SHA-256
`dc6add19bed7b92bc7d3c08c07280551ec69af910321eefd4e8813427290b79c`.
Its full-result hashes and read-byte counts are readable constants in the new
test, and include all result/projection/receipt/consumed-source fields.

| Variant | Initial read bytes | Final read bytes |
| --- | ---: | ---: |
| Complete | 90,654 | 126,056 |
| UNKNOWN | 90,654 | 126,036 |
| Missing scope | 90,654 | 96,998 |
| Missing coverage | 90,654 | 123,816 |

All four whole-result SHA comparisons and counters pass after refactoring.
Tests obtain the unchanged policy's native HEAD blob when constructing synthetic
fixtures, avoiding Windows checkout CRLF contamination without rewriting sources.

## TDD and validation

The first new suite was run before implementation: the additive API assertion
failed and v2 callers failed because that API did not exist; both v1 baseline
tests already passed. Subsequent focused RED cases exposed a malformed receipt's
AttributeError and rehashed non-integer complete-count metadata reaching the
manifest read; v2 validation now rejects both as ValueError before I/O.

The configured suite covers all six ordered triplets, native hash and recipe
binding, malformed/rehashed lineage, full scope/count/outside-FN numbers, UNKNOWN
and missing data with empty metrics, shared byte/deadline exhaustion, actual
combined rather than separate JSON caps, final rescan mutation and late seal
expiry, unchanged mean semantics, exact manifest versioning, and retained parent
v3 nonlegacy block. Actual OS link tests reject payload reads before traversal;
Windows uses a real junction and removes only that link before fixture cleanup.
Native September-28 source CSVs produce five events/six individuals and honest
NEED_MORE_DATA with no complete denominator.

Final command receipts are recorded below after running the owned and related
targets. Windows cannot validate POSIX master/fcntl paths; those existing skips
remain Linux CI requirements, not passing executions on Windows.

HB-B1's fixed native recipe was also challenged with a changed parent strength
and recomputed native model/prediction/prepared digests. The RED case reached the
manifest read; the v2-only check now compares both recipe content and digest with
the existing `hierarchy_shrinkage.RECIPE`. It does not replace the native recipe
with null or alter any ranking calculation.

Commands use the bundled Python with `-B -X utf8 -m unittest discover -s tests -p`
and each following filename. Initial native Windows receipts at `42c49fa`:

| Test module | Tests | Passed | Existing POSIX skips | Elapsed seconds |
| --- | ---: | ---: | ---: | ---: |
| test_stage1_configured_source_adapter.py | 25 | 25 | 0 | 29.661 |
| test_stage1_source_adapter.py | 33 | 28 | 5 | 10.275 |
| test_full_ledger_stage1.py | 44 | 44 | 0 | 0.504 |
| test_research_model_adapter.py | 35 | 35 | 0 | 1.799 |
| test_research_pdca_adapter.py | 27 | 26 | 1 | 11.971 |
| test_research_candidate_config_source.py | 16 | 16 | 0 | 4.317 |

Total 180 tests: 174 PASS, six existing platform skips. Related targets ran after
the shared refactor; the final v2-only fixed-recipe check was then exercised by
all six configured orders and the new rehashed-recipe negative test in the final
owned-suite execution. `git diff --check` passed. No full native suite is claimed;
Linux CI and parent opt-in integration remain coordinator responsibilities.

## Native admission counterexample repair

Independent review of `42c49fa` found a blocking gap despite the initial 25-test
suite passing: recomputed hashes could hide a changed native uniform/HB-A0/HB-B1
fit cutoff behind an unchanged common prepared cutoff. The original source
returned DIAGNOSTIC_ONLY and pooled 2/3 for those inputs. Admission of HB-A0/B1's
native structure and common fit/night identity was missing. This was a software
consistency failure; it does not establish any scientific performance result.

Before the repair, new tests reproduced all three future-cutoff cases reaching
the first evaluation open. Separate RED cases covered native-valid but different
earlier cutoffs/held-out nights, malformed native structure, and uniform `.99`
contradicting its own fixed Beta counts. The v2-only candidate gate now reuses
`occupancy_shrinkage._validate_model` and `hierarchy_shrinkage._checked_tables`,
with checks before/after the native calls. It binds every actual native fit cutoff
to the common prepared cutoff and each existing native held-out field to the
common forecast night. Uniform's existing exact envelope, recipe, typed support
and fixed probability identity are checked locally because it has no separate
native admission helper. No fitted numeric routine or score projection changes.

The independent external harness `stage1-source-admission-review-probes-20261025.py`
was run in both modes: original `42c49fa` accepted all 14 adverse inputs; repaired
working source rejected all 14. Tests also exercise native capacity translation
to the existing parent capacity error and shared expiry immediately after both
native admission helpers. The v1 route never enters this new gate.

Post-repair commands use the same `-B -X utf8` unittest invocation above:

| Test module | Tests | Passed | Existing POSIX skips | Elapsed seconds |
| --- | ---: | ---: | ---: | ---: |
| test_stage1_configured_source_adapter.py | 30 | 30 | 0 | 31.289 |
| test_stage1_source_adapter.py | 33 | 28 | 5 | 10.504 |
| test_research_pdca_adapter.py | 27 | 26 | 1 | 11.841 |
| test_research_model_adapter.py | 35 | 35 | 0 | 1.916 |
| test_full_ledger_stage1.py | 44 | 44 | 0 | 0.502 |
| test_research_candidate_config_source.py | 16 | 16 | 0 | 4.449 |

Total 185 tests: 179 PASS and six existing POSIX skips. All four v1 whole-receipt
hashes/read-byte counters pass inside the new suite. `git diff --check` passes.
The correction changes only v2 native admission; Linux/full integration remains
the coordinator's subsequent CI responsibility.

## Independent exact-source review

**Bounded code review PASS after the admission repair.** No unresolved blocking
defect was found at `6a777ccb801d403a39a06b1ced2ced1ff31a85be`, compared with
unedited base `70b3fff12ecf7241603bca35b5b7188cc144e679`. Initial implementation
`42c49fa3e6772bdcf3f3f9263820d16e1029ac86` was not approved. The reviewer did
not edit source, tests, spec, model, pure evaluator, parent, Raw/ORIGINAL, policy,
STATE or freeze files. The only tracked reviewer edit is this section.

Frozen reviewed Git blobs:

| File | Blob ID | SHA-256 of Git blob bytes |
| --- | --- | --- |
| `src/evaluation/stage1_source_adapter.py` | `211c70376e079d003cfabf88588a3c41bd45b020` | `388bf18b1f4f90fb29d48fe0c4f58579bae925d281f99b27eb0e79baa038ada6` |
| `tests/test_stage1_configured_source_adapter.py` | `953879dc6078a5b5cadb8d68494d2bf528b53897` | `92d95289fb496526ee3b4d46a631bac4a56b66a7e10a68acec1dc8fa567cff6e` |
| `docs/specs/stage1-configured-source-v2.md` | `4a32622d3fa16c095a8b702a52a9ace7df551edb` | `14d637ed10f22a7f2789049cba1446e51ff46c7c4ddffab79f21113477b295d6` |

### Finding reproduced and repair independently verified

The original implementation accepted rehashed native claims contradicting the
prepared fit lineage: uniform/B1 training cutoffs and A0 fit cutoff after the
forecast, or at a different earlier instant; A0/B1 held-out-night drift; invalid
uniform recipe/schema/probabilities; and B1 `NOT_FITTED` status. All 14 direct
counterexamples returned `DIAGNOSTIC_ONLY` and fixture recall 2/3. Those were
software admission failures, not evidence of real model skill.

The reviewer executed the archived original source to preserve the reproduction.
At the repaired commit, all 14 reject with `ValueError` while `Path.open` is
patched to fail if reached, establishing rejection before even the evaluation
manifest opens. Extra independent checks reject boolean/null native cutoffs,
boolean support counts for all three native model types, contradictory wrapper
TRAIN digests and rebound prediction cells before any file open. Native
structural admission plus common fit/night equality closes the finding. Three
native cutoffs expressed as equivalent UTC instants still succeed with unchanged
2/3 fixture metrics; the repair does not require timestamp string equality.

### Fresh native verification

Runtime:
`C:\Users\qq113\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe`,
with `-B -X utf8`, from this worktree. No fake `fcntl` or real scientific fit was
used. The following standard-input runner freshly ran **185 methods: 179 PASS,
six existing platform skips**, in 60.418s:

```python
import sys, unittest
sys.path[:0] = ['src', 'tests', '.']
names = (
    'test_stage1_configured_source_adapter', 'test_stage1_source_adapter',
    'test_full_ledger_stage1', 'test_research_model_adapter',
    'test_research_pdca_adapter', 'test_research_candidate_config_source')
loader = unittest.TestLoader()
suite = unittest.TestSuite(loader.loadTestsFromName(name) for name in names)
result = unittest.TextTestRunner(verbosity=1).run(suite)
sys.exit(not result.wasSuccessful())
```

Independent local commands:

- `python -B -X utf8 ..\stage1-source-admission-review-probes-20261025.py . --original`:
  archived initial implementation accepts all 14 counterexamples, reproducing
  the finding. Without `--original`, repaired code rejects all 14 before I/O.
  Current local probe SHA-256:
  `3b35986dfd5e52916ad052c38804b3b21372e9091547fa54040b4a6c03d18a78`.
- `python -B -X utf8 ..\stage1-source-v2-review-probes-20261025.py .`:
  **79 assertions PASS**. Probe SHA-256:
  `9588b1601cf431e0bef6327655b6e54490d36f8afcaf2e927af3c0142707e3d3`.
- A direct standard-input probe changed uniform/A0/B1 native cutoffs to
  `2026-10-13T09:00:00Z`, resealed their artifacts, and verified diagnostic status
  and all three 2/3 fixture denominators: **two assertions PASS**.
- `git diff --check 70b3fff HEAD`: PASS. Changed-file inventory remains the
  source adapter, its new test, spec and review only.

External probes are local artifacts outside the tracked source tree. Their
hashes do not imply publication or CI execution; assertions and reproduced
counterexamples are counted separately from unittest methods.

### Positive paths, source safeguards and legacy compatibility

Independent actual-loader probes execute all six ordered configured sets.
Outputs preserve exact candidate order, native model/prediction hashes, A1
recipe lineage, full outside-universe denominator and false authority flags.
HB-B1 keeps its native recipe/hash and ranking semantics while only its new
configured score recipe projection is null. Inputs remain unchanged, final
receipts seal correctly, and the inherited context's absolute deadline and
byte maximum are unchanged while actual reads accumulate. Combined byte/node
caps and shared expiry reject before evaluation I/O.

A native Windows junction points from the declared evidence namespace to a
separate temporary directory outside the fixture root. Evaluation rejects with
**zero linked or external payload opens**, preserving the sentinel bytes and
removing only the validated junction itself before cleanup. Known invalid capture
counts remain invalid even when scope/coverage roots are missing. Actual stored
September-28 Git CSV bytes still produce five events/six occurrences and
`NEED_MORE_DATA`, with empty per-night, pooled and paired metrics when no complete
scope/coverage exists.

The reviewer independently executed the exact unedited base source in a separate
module and compared full legacy result objects, not just selected fields, using
fresh fixtures and the base's native policy bytes. All four outputs and initial/
final cumulative read counts remain exactly equal:

| Case | Full result SHA-256 | Initial / final read bytes |
| --- | --- | ---: |
| Complete | `b0056b3d1eb8b496b769a33a92b0dd10df971fed15f4041176cbfe83dbdd02d1` | 90654 / 126056 |
| UNKNOWN | `007d47cec2c2784f54268eec38dac96bc21ebd3dd340d59feae5fa4c0f062f1d` | 90654 / 126036 |
| Missing scope | `6cc730ed1697ea0b663185a654cf4f78b4465c04d21c8903a3bb37bed3b5a0e1` | 90654 / 96998 |
| Missing coverage | `aaaa65a4e314bda46ff5058ab24cb3099798a2d98e6ed374f8042419e48ce6f5` | 90654 / 123816 |

The fresh related tests also exercise final-source mutation, final-seal expiry,
the unchanged parent v3 nonlegacy implementation block and native-capacity/error
translation. No model fitting algorithm, source DAG rule, scope algorithm, score
mean, bootstrap, pure evaluator or parent dispatch was changed by this slice.

### Approval limits

This API validates declared source/model consistency, not execution or issuer
truth. Config/forecast/prepared inputs share the existing 16MiB, 2,000,000-node,
depth-12 owned snapshot cap and complete row limits. Reads and cooperative
validation use the existing parent context; native validators are bounded and
bracketed by checks, without process-preemption or an atomic filesystem snapshot.
UNKNOWN, incomplete coverage and absent inputs grant no metrics or denominator.

Source authentication, historical readiness truth, preregistered persistent
campaign/consumption authority, independent confirmation, formal threshold,
selection, promotion and production remain unvalidated or false. The API alone
does not connect parent v3 to configured source-v2 evaluation. That explicit
parent integration, a new complete runtime freeze and exact-head Linux/fresh-main
verification remain separate coordinator gates. No scientific performance or
Master Goal completion is established by this approval.
