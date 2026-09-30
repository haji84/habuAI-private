# Independent Task 4 review

Reviewed bounded Task 4 commit `96c6cb0`, complete Task 4 brief including parent clarifications, normative specification, implementation report, seven changed paths and relevant inference contract. No implementation edits, nested agents or full-suite rerun.

**Spec compliance: changes required. Code quality/integrity: changes required.** No Critical finding or production-activation bypass identified. Three Important findings below. Production gate reproduction and Task8 authority remain intentionally unavailable; sandbox mechanics are not scientific validation and their isolation is appropriate.

## Important 1 — Atomic publication omits staging-directory durability

**`scripts/freeze_prediction.py:99–116`**.

Freeze fsyncs the two files, renames their staging directory to the immutable version, and fsyncs the destination parent. It never fsyncs the staging directory itself. File-data fsync plus a different parent-directory fsync does not establish durable directory entries for `prediction.json` and `sha256.txt`. The rename provides atomic visibility during normal execution, but a filesystem/host crash can leave the committed version directory without guaranteed durable child entries. That undermines the explicit crash contract that a completed publication cannot reserve an empty/partial immutable P0.

Focused instrumentation recorded exactly three fsync targets: the staged prediction file, the staged hash file, and the night directory. There was no staging-directory fsync before rename. This is a durability analysis backed by observed call ordering, not a claim that a power-loss experiment was performed. The existing injected rename-failure test correctly proves process-level cleanup, but not this durability property.

Required repair: after writing/fsyncing both files, fsync the staging directory before rename; retain the final destination-parent fsync, and ensure newly created parent-directory links are durably established where required by the supported local-filesystem contract. Add an ordering/failure regression for the directory sync without introducing a destructive power-loss test.

## Important 2 — Model verification skips probability bounds by using an empty inference universe

**`src/champion_registry.py:98–118`**, especially line 117; related probability bounds are enforced inside the per-unit loop in `src/model_evaluation.py:350–361` at this reviewed state.

`verify_model` delegates fitted-state validation to `predict_model(model, [])`. Although this checks family/hash/nonnegative scores, the probability upper bound is checked only when iterating inference rows. An invalid uniform or prevalence model with a probability above one is therefore accepted as a verified supported artifact. This is parameter integrity, not a missing scientific promotion gate.

Reproduction: construct the existing self-consistent model fixture with uniform `parameters.default=1.5` (valid matching model ID/hash/code/version/output metadata). `verify_model` returns it; `validate_candidate` reports BLOCKED rather than invalid evidence FAIL; sandbox `promote` commits it and `champion_at` returns it. Actual nonempty inference subsequently rejects it, so this probe does not publish invalid probabilities or bypass production activation. It does establish a committed model that the registered adapter cannot execute on an ordinary universe.

Required repair: validate the entire fitted parameter domain independently of whether any prediction rows are supplied. For probability families require every default/area probability to be finite and within [0,1], including areas absent from the current universe; keep score-only family semantics separate. Reject malformed model state before copying/committing a registry record. Add out-of-range default and out-of-range area-parameter regressions for both verification and sandbox activation.

## Important 3 — Issuer validates ten-minute alignment in the supplied timezone rather than JST

**`scripts/issue_prediction.py:68–73`**.

The issuer parses `window_start_jst`, checks its operational night through `night_for`, but tests `start.minute % 10` before converting to Asia/Tokyo. An aware timestamp in a timezone whose offset differs from JST by a non-ten-minute multiple can pass while the actual Japanese window is misaligned. Task3 correctly normalizes window timestamps to JST before this check; the issuance boundary should preserve that invariant.

Reproduction: in the otherwise valid issuance fixture, change the sole universe row to `2026-09-30T18:00:00+05:45`, update its bound hashes, and issue at 20:00 JST. Issuance succeeds, although the actual window is **21:15 JST**, not an aligned ten-minute unit. The record remains SANDBOX and has no formal time-target output; this is a concrete input-contract defect in the mechanical issuer, not a claim of production scientific success.

Required repair: normalize the parsed window to JST before checking minute/second alignment (or explicitly reject non-JST encodings under a documented equivalent contract). Preserve absolute-time prospectiveness checks. Add equivalent-timezone tests with both aligned and misaligned resulting JST windows.

## Verified boundaries and review evidence

Six selected existing tests passed: historical selection/ABA lifecycle, orphan-event inactivity, production trust-flag denial, prepublication rename-failure cleanup, promotion blocked during inference/publication, and changed actual Champion inference preserving old output. Additional probes reproduced the parameter and timezone defects and inspected fsync ordering. The implementer/parent's 158-test full-suite result was read, not repeated here.

The reviewed production APIs remain fail-closed before reading forged production state. No JSON or CLI flag enables the ephemeral sandbox capability. Sandbox events/predictions are visibly qualified and cannot become ORIGINAL through that issuer. Registry locks cover selection, inference and publication; CAS uses event hashes rather than model IDs; only current-pointer ancestry is active; orphan records do not win lookup; rollback requires prior committed artifact history. The generic external Freeze rejects execution-lineage claims, and installed model adapter identity is bound by version/code hash. Strict serialization rejects nonfinite JSON numbers. Current outcome-coverage/formal/confirmation/scientific verifier gaps are explicitly BLOCKED and must remain so until later reviewed implementation.

No additional Minor finding is raised. These repairs should remain bounded to model-state validation, publication durability and timezone normalization; they do not require enabling production authority or implementing later scientific gates.
