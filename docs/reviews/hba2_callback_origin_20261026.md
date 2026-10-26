# HB-A2 caller callback-origin repair

Author scope: `src/models/hba2_feature_candidate.py`, new `tests/test_hba2_callback_origin.py`, and this record only. Base is verified main `00f7c5613c40f5358732fa36499845218a7ccab0`; isolated branch `codex/hba2-callback-origin-20261026`. ROOT explicitly dispatched this minimal internal repair after independent V triage/design PASS at LOW risk. No candidate registration, model/numeric algorithm, source/feature/label contract, requirements, baseline M0–M3, A1/base/selector, parent, policy, Raw, STATE, cycle, permission or production change is included.

## Problem and final behavior

All three public APIs (`assess_hba2`, `fit_hba2`, `predict_hba2`) run the caller's check through A1's `_budget` inside A2's `_run` classification branches. A caller-raised HBA1CapacityBlocked/ResearchInputCapacity was replaced by HBA2CapacityBlocked; KeyError/TypeError/IndexError/OverflowError/RecursionError was replaced by ValueError. Keeping the original only in `__cause__` lost the caller's abort identity and origin. This was not a numerical fit or tree inference failure.

Only `_run` changes. For a callable parent check, a named forwarding guard records the exact raised BaseException and bare-raises it. Each existing classification branch checks object identity before its original internal normalization. None and noncallable values are passed to the existing budget validator unchanged. There is exactly one `base._budget` call and one original absolute local deadline; no cap/clock reset or additional parent callback. The wrapper catches only the caller check, not validators/model math/imports. Internal structure/capacity errors and import-operation-origin capacity retain the old classifications.

Old module: 21,362 native bytes / SHA-256 `3a30d1650f90cce8bd7d5258e3deac1b188d4c3a888ec2af75993ff809c47692`.

Fixed module: 21,767 native bytes / SHA-256 `43706bf221fcb2e9dfbb16b3dc8db5cb68e31e14e06a4dcd8fe8b4a115d2dd36`.

An AST comparison removes only `_run` from each genuine old/current module and requires every other top-level definition, import, constant, schema, recipe, flag and numeric routine to remain exact. It also checks that the new runner has one budget call. Existing A2 tests remain 26,340 B / `90099ac9467e1f8a979dfcd53fe84612e53766b94b2388fd855b8cb5b3e69193`; all eight other sealed source/test/spec files remain byte-identical. The ordinary native code fingerprint changes naturally; no old recipe/model/receipt is rewritten or resealed as a consequence.

## Pre-edit evidence and native baseline

Before any source or regression-test edit, the new worktree was clean at the exact base. It was created with command-local `core.autocrlf=false`, without global Git configuration changes. Nine genuine Git source/test/spec blobs were materialized and matched byte-for-byte to the worktree. The complete original A2 module and its original runner were saved outside Git. Original runner:396 B / `d453770003331654cd10ac9713f089d208fbcc15a6e9ffb2a650cdb54cd7d51a`.

Baseline directory (private): `.worktrees/hba2-callback-origin-baseline-00f7-r2-20261026/`. `baseline-receipt.json`:13,272 B / `62a271749164de382212d0c78fe89178aa54c5a81b1d8f91a9018b7cfcc7ff2b`. It records actual UTC, fixed `PYTHONHASHSEED=0`, all original file identities, complete owned inputs and twelve immutable normal artifacts (three public entries × None/callable parent × native/canonical encoding). The APIs use existing explicit synthetic fixtures: valid assessment, a valid insufficient fit returning NEED_MORE_DATA without backend, and a hand-declared JSON tree interpreter model, not a fitted estimator. No real TRAIN or backend fit is represented.

Successful external callback counts were5405 for assessment,2143 for the insufficient fit, and5468 for prediction, and are retained exactly. None-check cases have zero external callback invocations, not zero internal guard checks. Output insertion key order, every field and digest are compared; no receipt/model/recipe field is excluded. Input fixture timestamps are fixed declarations; actual wall/monotonic clocks were not mocked or backdated.

The first private capture script omitted the project root on its import path, so fixture import stopped before any public API operation or baseline receipt. That script and partial nine-file snapshot remain retained in `.worktrees/hba2-callback-origin-baseline-00f7-20261026/`. R2 adds the correct root import path and writes to a new directory; no failed artifact or golden was overwritten. This is a harness import error, not a product or source failure.

## TDD and verification

Bundled actual Windows Python ran with `-B -X utf8` and process-local hash seed0. No fake fcntl, estimator/backend, source reader, clock or filesystem facade was used.

1. **Old test baseline:** existing A2 module22 methods,21 PASS/1 explicit local pinned-backend skip,0.499 s. Log4,004 B / `c004e547536ea44015e6e797cb2c43b30573ce516d387f9e28494278b140c92d`.
2. **RED before source repair:** new9 methods produced80 assertion failures/0 errors in0.478 s. The original module SHA was still3a30d165. Log84,813 B / `99e4c64ee8125ecf944fd9f18437748e10857a6c9ce550cc3c4640da86110236`. The failures were exact-object identity assertions, not fixture/load errors.
3. **GREEN:** the same9 methods PASS/0 skips in0.463 s. Log1,899 B / `4d6269f5066928f4dac426cd98463d420646173a6af6297a737591054893a389`.
4. **Affected final:** HBA1/A2/new callback modules plus research selection,85 methods/84 PASS/1 explicit pinned-backend skip in2.321 s (outer2.562 s). Log16,143 B / `cb84d49b9f72ac9dfcfbe4e8500f274370b16ea3d80b1869cb96db6a86de70fd`.
5. **Independent-program whole reseal:** the saved full pre-edit A2 source is compiled as a distinct module. Old and current public APIs both reproduce all twelve original artifacts, complete key order and parent callback counts. The twelve internal bad-check/actual256-byte capacity controls match original error class names/messages/causes. Result `.worktrees/hba2-callback-origin-verified-whole-20261026.json`:5,160 B / `ad33de82791158ab860fab85f290dfd1e407f20b0a8ee760a5f470a5b24eddb9`. Baseline files are only reread, never regenerated.

New regressions exercise seven previously wrapped classes plus HBA2CapacityBlocked/ValueError/TimeoutError/OSError/KeyboardInterrupt/SystemExit/MemoryError. Across all three public APIs, checks raise at the first guard, a later actual guard10, and after the real complete output digest returns. A delegating digest observer returns the genuine hash before the final check; no hash success is fabricated. This is126 identity subcases, including63 formerly changed-object subcases. Falsey callable controls, failures immediately after a genuine NumPy import return and after a classified import error account for the additional17 RED failures. No later SciPy/sklearn import follows the NumPy-return caller abort. Actual import-operation ResearchInputCapacity still normalizes to HBA2CapacityBlocked rather than being mistaken for a caller failure.

The hermetic new test carries the genuine pre-edit runner source and independently compiles it for complete normal public behavior comparisons. The separate author reseal uses the complete immutable old module, original inputs and saved artifacts; it is not merely a comparison of a few selected fields or a regenerated golden. Successful normal calls with a None parent and a callable parent are both covered.

Commands:

```text
python -B -X utf8 -m unittest discover -s tests -p test_hba2_callback_origin.py -v
python -B -X utf8 -m unittest discover -s tests -p test_hba2_feature_candidate.py -v
# One process: unittest discovery for test_hba*.py and test_research_selection.py
python -B -X utf8 .worktrees/hba2-callback-origin-verify-whole-20261026.py
git diff --check
```

The first three command families use the owned worktree as cwd. The private whole-reseal script is run from the shared workspace with hash seed0. Full exact/fresh Ubuntu and its already mandatory genuine pinned numeric fit/parity gate remain ROOT integration gates. The explicit local dependency skip is not numerical fit PASS. The broad native master suite was not repeated for this narrow repair; known platform/backend limitations are not hidden with facades or new skips.

## Scope and release limits

This repair does not change `_backend`, fit monitoring, tree validation/export/inference, float32 conversion, rounding, feature order, counts, target, seed, pinned versions, model/recipe schemas, flags or candidate limits. Existing default errors for invalid check=False/0/string and actual internal encoded-cap failure stay unchanged. No source-qualified fitting, heldout labels, parent/Stage1/A2 admission, confirmation, source audit, full-night performance, PR/remote operation or production activation was performed. All existing scientific/authority restrictions remain.

ROOT owns later verified-main union, new source closure/freeze, PR/CI and integration; this lane does not merge pending Stage1/data changes. Fixed-source independent V review is the next gate after the clean author commit. This author result is bounded local correctness evidence, not a substitute for that independent review or genuine Ubuntu CI.
