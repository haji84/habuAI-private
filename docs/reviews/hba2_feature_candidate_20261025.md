# Standalone HB-A2 implementation review

Branch `codex/hba2-candidate-20261025`, separate tree `.worktrees/hba2-candidate`.
Verified initial main/origin/main `a1d2a99de1ec7b0324e822c85c4e14a7e77c80eb`
was normally fast-forwarded to `5d4b84fcc0d9b54683f80b4fcace0818d7fb94bd`
before implementation. No reset, force update or other worker's source edits.

The approved design blob is `e0c37718d775a10824aa3afd8533a8300d451d40`.
Independent design review covered TRAIN/future float32 preflight before data/
backend classification, finalized unscaled native leaves with learning rate applied
once, exact typed receipt/runtime fields, and an unconditional genuine numeric CI
gate. Root explicitly authorized subsequent TDD. This branch changes only four
new files: model module, test module, spec and this review.

## Implemented boundary

`assess_hba2` and `fit_hba2` own bounded recipe/selection JSON, reuse the existing
strict research selector and seven-feature physical validation, and validate every
accepted TRAIN value as finite after standard-library binary32 conversion before
NEED_MORE_DATA or numerical-backend admission. Zero, insufficient or single-class
valid data returns NEED without backend import. Known contradictions are errors.
The software floor is 20 accepted rows/five prior nights, with the existing two
positives/two negatives minimum; this is not a scientific sample adequacy claim.

The lazy fit backend requires exactly the existing NumPy 2.2.6/SciPy 1.15.3/
scikit-learn 1.5.2 pins. Missing/wrong runtime yields CAPABILITY_BLOCKED with no
model; no fallback or global installation. The fixed public classifier recipe is
32 depth-two log-loss trees, zero initialization, seed zero, no tuning, weights,
holdout split or early stopping. The public monitor and checks before/after native
calls use the same parent deadline; one native stage/import/allocation remains
nonpreemptible and does not provide hard wall-clock termination.

The native exporter admits complete public tree structures and records canonical
JSON only. The pure interpreter uses exact float32 feature comparisons against
binary64 thresholds, then stage-ordered `raw += .1 * unscaled_leaf` exactly once
per tree, checking products and partial sums before stable logistic conversion.
No optimizer, split learner, pickle/joblib serialization or numerical-library
inference dependency is introduced. TRAIN export parity is against public raw
decisions and probabilities at absolute tolerance 1e-12. All stages release no
partial model or predictions on deadline/capacity failure, including after hashing.

All source/authentication/fit/science/selection/promotion/production flags retain
the existing research-only false/NOT_VALIDATED/NOT_ATTESTED meanings. A declared
code/requirement/package hash is not source authentication or trusted campaign
registration. This module does not read original records or seal REPLAY, does not
register HB-A2 in the three-candidate protocol, and performs no actual real-data
training. Existing source-qualified captures remain distinct from training-ready
rows. Raw/ORIGINAL, requirements, existing A1/core/selection, policy, parent,
registry, STATE and freeze are unchanged.

## TDD and honest native verification

The first owned-suite execution before the module existed failed 11 tests with
the explicit missing-module assertion. After implementation the guard/interpreter
cases passed. The row-cap sentinel test initially constructed its separate model
fixture inside the forbidden-copy patch; that test setup was corrected by preparing
the fixture before the patch. No production cap was weakened.

Native runtime has NumPy 2.3.5 and no SciPy/scikit-learn. Consequently no genuine
native classifier fit/export is claimed. The new suite has one explicit local
numeric skip, with the reason requiring genuine pinned Ubuntu execution. A separate
native negative test runs that gate with GITHUB_ACTIONS=true and confirms missing
pins fail rather than skip. No fake numerical package or fcntl shim is used.

The owned tests cover actual full-row binary32 overflow before NEED/backend,
known data/type/physical/date contradictions, exact recipe and receipt fields,
native missing-runtime status, finite JSON tree shape/reachability/depth/cycles,
genuine binary32 neighboring inputs around a binary64 split threshold, one-time
leaf scaling, finite partial sums, source authority/date/hash tampering, complete
strict future units, pre-copy row/combined actual-byte caps and final-hash expiry
for all three public APIs. Registry identity is checked unchanged.

The always-collected numeric CI gate cannot skip on GitHub Actions: it asserts
the three actual pinned versions, genuinely fits the public estimator and checks
every TRAIN/future raw score/probability plus genuine float32 neighbors of actual
selected native splits. It also checks repeated same-environment model identity,
a fixed two-feature nonlinear interaction fixture, rounded public predictions and
expiry raised through the actual native public iteration monitor. These numeric
assertions await real Ubuntu execution; their presence is not their success.

Native command: bundled Python `-B -X utf8`, one `unittest.TestSuite` collecting
the seven modules below through `discover('tests', pattern=...)`, with a nonzero
exit on any unsuccessful result. Combined execution: **208 tests, 206 PASS,
two explicit skips, 56.722s**.

| Module | Tests | PASS | Skip |
| --- | ---: | ---: | ---: |
| test_hba2_feature_candidate.py | 19 | 18 | 1: unavailable genuine pinned backend |
| test_hba1_feature_candidate.py | 28 | 28 | 0 |
| test_research_selection.py | 26 | 26 | 0 |
| test_prospective_candidate_model.py | 43 | 43 | 0 |
| test_research_model_adapter.py | 35 | 35 | 0 |
| test_stage1_configured_source_adapter.py | 30 | 30 | 0 |
| test_research_pdca_adapter.py | 27 | 26 | 1: existing POSIX master path |

The native runtime can neither claim pinned numerical execution nor POSIX master
execution. `git diff --cached --check` is run before the source commit. Full Ubuntu
numerical CI, independent source review and root freeze/integration remain required
before the branch is accepted for main. No complete native/full-suite or scientific
PASS is claimed from these bounded target receipts.

## Import-admission counterexample repair

Independent review of exact `8498558` found a runtime classification gap: when
distribution metadata matched the pins but NumPy import raised the representative
binary-ABI ValueError (`numpy.dtype size changed`), the exception escaped instead
of the specified sealed CAPABILITY_BLOCKED/no-model receipt. A targeted import-only
injection reproduced this RED before source repair. No estimator was faked and no
numeric fit was performed by that counterexample.

The repair is restricted to the lazy numerical import statements. Expected
ImportError/ValueError/OSError failures now produce the existing capability
classification, with exception type in the issue tag. Timeout and known capacity
exceptions propagate before that handler. Its parent guard is checked again;
an original caller ValueError raised there retains its identity. The surrounding
contract validators, export/interpreter and real estimator fit are not included
in the handler. No error is turned into NEED_MORE_DATA or numerical success.

New controls cover ABI ValueError, native load OSError, ImportError, timeout and
capacity propagation, plus caller-check error identity before and immediately
after the failed import. Owned execution: 21 tests, 20 PASS and one explicit
unavailable-pinned-backend numeric skip, 0.398s. Final combined rerun follows below;
genuine pinned numerical and POSIX acceptance still require existing Ubuntu CI.

A second targeted RED at the same admission boundary used the genuine installed
NumPy import, expired the parent immediately on its return, and observed an
attempt to import SciPy while expired. Each lazy import now has its own immediate
pre/post guard outside import exception classification. No subsequent import is
attempted when the previous import exhausted the parent deadline. Only one
nonpreemptible import remains the acknowledged limit, rather than the entire
sequence of package imports.

The external eight-case import harness passes 8/8 with numeric_fit_executed=false:
ImportError/ModuleNotFoundError/ABI ValueError/native OSError capability blocks;
TimeoutError/capacity/MemoryError propagate; and NumPy-return expiry makes zero
further imports. Final owned suite: 22 methods, 21 PASS and one explicit missing
pinned numeric skip (0.439s). The independent reviewer also reported six unchanged
related modules freshly passing 189 methods (188 PASS, one existing POSIX skip,
58.460s). A final implementer core-regression receipt follows below.

Final implementer combined core run used the same bundled `-B -X utf8` command
with HB-A2/A1/research_selection/legacy/prospective preparer modules: **154 tests,
153 PASS and one explicit pinned-backend numeric skip, 12.375s**. All eight
external import probes passed after the final guard change. `git diff --check`
passes; the same four owned paths alone form this repair commit. No installation,
numeric-fit success, new requirement/authority or scientific result is claimed.
## Independent source and nonnumeric review

Independent reviewer `/root/config_review` reviewed source commit
`8ad5a7004bc9371f299f44e82b1e49409c85651e`, following the original implementation
`84985580b62e49423039a6272b59b646e42dbde3` and approved design blob
`e0c37718d775a10824aa3afd8533a8300d451d40`. The tree was clean before this
review-only section. Result: **source/guard review PASS; genuine pinned numerical
fit/export/parity NOT EXECUTED locally and still required in Ubuntu CI**. This is
not an integration, scientific, real-data training or production acceptance.

Canonical Git identities at the reviewed source commit:

| File | Git blob |
| --- | --- |
| src/models/hba2_feature_candidate.py | fae2754218f6386c7acacd91f5b6d11a97cc41e9 |
| tests/test_hba2_feature_candidate.py | 9ca9eac0410f9b048bc89094bd19098a0ab6e184 |
| docs/specs/hba2-feature-candidate.md | e884473f744c07354adf2a46f73dfcd16e3234d3 |

The reviewed module's actual native checkout-byte SHA-256 was
`3a30d1650f90cce8bd7d5258e3deac1b188d4c3a888ec2af75993ff809c47692`.
This records that checkout's bytes; Git blob and native-byte identities serve
different purposes and neither authenticates caller-declared recipe inputs.
The diff from base `5d4b84fcc0d9b54683f80b4fcace0818d7fb94bd` adds only the four
owned module/test/spec/review files. Existing A1, numeric core, selector, source
adapters, registry, requirements, policy, Raw/ORIGINAL and state/freeze files are
unchanged by this branch.

Two related import-admission counterexamples were found independently in the
original implementation. First, exact metadata pins followed by an import-time
ABI ValueError or native load OSError escaped rather than returning the specified
CAPABILITY_BLOCKED receipt. Second, expiring the parent immediately after a real
NumPy import returned still allowed the next SciPy import to start. The final
repair limits classification to one import operation at a time and checks the
same guard before/after each operation. ImportError/ModuleNotFoundError/ValueError/
OSError produce a sealed capability block with no model; timeout, capacity and
MemoryError propagate. Caller-check failures remain outside the classification
boundary. Neither repair catches contract validation or numeric/model arithmetic,
changes scientific status, or substitutes a fit.

Fresh independent commands used bundled Python
`C:\Users\qq113\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe`
with `-B -X utf8`, from `.worktrees/hba2-candidate`:

```powershell
python -B -X utf8 -m unittest discover -s tests -p test_hba2_feature_candidate.py -v
python -B -X utf8 ..\hba2-review-probes-20261025.py .
python -B -X utf8 ..\hba2-import-admission-review-probes-20261025.py .
```

Here `python` denotes the absolute bundled executable above, not an arbitrary
PATH interpreter. At exact `8ad5a700...`, owned tests ran **22 methods: 21 PASS,
one explicit unavailable-pinned-backend skip, 0.525s**. The first external harness
passed **165 assertions**; the second passed **8/8 controlled import-boundary
cases**. Both explicitly report `numeric_fit_executed=false`. External harnesses
are reviewer-owned files outside the branch and do not modify source. Their
actual SHA-256 values were respectively
`62ab2612c1ead015b0cfda2cd674f2347db9647ebcf6ef86397e4edb132f4e39` and
`aa53275b71700c118be006c3dade27a3782c8e6c653620e9f8e234bcb6328fce`.

The 165 assertions independently exercise every raw TRAIN/future feature's
invalid limits/types/float32 overflow, including insufficient TRAIN before any
backend; actual row counts, duplicate physical units/events/IDs, exposed nights
and chronology; rehashed recipe/model/runtime/count/class/authority mutations;
tree indices, leaf sentinels, cycles, shared/unreachable children and depth;
order-sensitive ordinary accumulation versus fsum, one-time leaf scaling, stable
extreme logistic conversion and nonfinite partial sums; complete future identity,
outcome leakage, strict feature availability and source namespace; caller input
ownership and complete hashes; no numerical import in pure prediction; actual
byte/node/pre-copy row caps and shared parent expiry. Hand-declared JSON tree
fixtures test the interpreter only and are not represented as fitted estimators.

The six existing related modules were also independently collected together via
`unittest.TestSuite(defaultTestLoader.discover('tests', pattern=p) for p in
patterns)`, then `TextTestRunner(verbosity=1)` and nonzero exit unless successful.
Patterns were test_hba1_feature_candidate.py, test_research_selection.py,
test_prospective_candidate_model.py, test_research_model_adapter.py,
test_stage1_configured_source_adapter.py and test_research_pdca_adapter.py.
That run completed **189 methods: 188 PASS, one existing POSIX master-path skip,
58.460s** during the import repair. Their sources/dependencies were unchanged by
the final repair. These are separate runs: in total 211 methods, 209 PASS and two
explicit skips; this is not a claim of one full native suite or a numeric PASS.

Static review confirmed the fixed public classifier recipe, exactly 32 exported
depth-two indexed trees, binary32 input preflight, finalized unscaled binary64
leaves, ordered `raw += .1 * leaf` once per stage, zero init and stable logistic;
TRAIN native/public unrounded admission at 1e-12; exact receipt/runtime fields;
one shared deadline through imports, native monitor, export, parity and final
sealing; and no fallback, fourth registration, source reader or publisher.
The always-collected genuine numeric test cannot skip on GITHUB_ACTIONS=true;
its native missing-pin negative control passes. Genuine pinned TRAIN/future raw
and probability parity, actual split neighbors, repeat identity, nonlinear fit
and native monitor expiry still need that test's actual Ubuntu execution at the
accepted source. No additional numeric proof is inferred from static inspection.

Native environment remains NumPy 2.3.5 without SciPy/scikit-learn. No package
installation, fake estimator/backend, real-source fit, real qualification or
authority change was performed. A2 stays standalone and all nine authentication/
scientific/authority fields retain their fixed research-only values. Trusted G0
readiness, actual source authenticity, cumulative campaign accounting, prereveal
freeze, candidate registration and parent integration remain separate boundaries.
