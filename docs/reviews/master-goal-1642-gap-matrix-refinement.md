# Master Goal #1642 gap-matrix refinement

Updated only `docs/specs/master-goal-1642-gap-matrix.csv` in the repository. No code, tests, workflows, data, predictions or reports were edited; no commit was made.

## Scope and evidence cutoff

Individually reviewed R001–R112 against the exact owner-source snapshot, current normative specification, Tasks1–8 plan, architecture review, existing development-executor audit, and reviewed Task1/2 implementation/report/re-review evidence. Task1 includes fix `317c8341c508503a866c803c65b2a0344dcfeb81`; Task2 includes fix `4e5a2ca78ad1583cb513d34bcf8f343962d7847b`.

Task3 files appeared while this documentation work was running. They are intentionally not counted as completed or reviewed implementation. Tasks3+ retain their explicit missing executors, inputs and live-acceptance obligations.

## Changes

- Preserved all 112 canonical IDs, their order, sections, exact requirement text, `baseline_implementation`, `master_validation` and `acceptance_reference` values.
- Added `baseline_evidence_paths` and `baseline_gap`, preserving the original evidence/gap cells exactly while allowing the existing `evidence_paths` and `gap` columns to describe current reviewed state accurately.
- Replaced generic current mappings with requirement-specific source/review evidence, missing implementation/data/runtime needs, planned slices and concrete acceptance checks. Existing tests are distinguished from planned tests.
- Marked completed audit/design deliverables R001–R004 and R093–R100 as `DONE`, with `real_data_validation=NOT_APPLICABLE`. Schema/policy design completion explicitly does not claim all runtime validators or promotion executors exist.
- Reflected reviewed local Task1/2 behavior: integrity and prospective scoring, explicit diagnostic limits, shared exposure units, immutable version handling, snapshot/manifests, fail-closed recovery and stage-status validation.
- Kept feature, model, development and Champion requirements specific: forecast-time weather/source availability, measured effort, qualifying observation roles, independent confirmation, actual inference, Habu-specific authorized builder/verification/publication, and trusted production persistence are separately identified.
- Distinguished local recovery/idempotency from fresh-runner Actions restoration, event/poller publication deduplication, and live whole-chain acceptance. Stage-name coverage is explicitly not executor completion.
- Kept `master_validation=NOT_VALIDATED` for every row. Historical September28 evidence is labeled diagnostic only; no official KPI, scientific acceptance or Master completion was inferred.

## Status interpretation

`IMPLEMENTED` describes the reviewed local behavior named in that row's gap/evidence, not production or scientific validation. `PARTIAL` preserves real foundations while identifying remaining work. `IMPLEMENTATION_BLOCKED` identifies an absent reviewed executor rather than disguising it as insufficient data. `DONE` is limited to delivered audit/design artifacts. Missing data and runtime capabilities are stated separately in `missing_data_or_executor`.

`real_data_validation` is conservative: `NOT_APPLICABLE` for documentary deliverables, `HISTORICAL_DIAGNOSTIC_ONLY` for the historical dry-run row, and `NOT_VALIDATED` elsewhere. Synthetic/local tests appear as engineering evidence in acceptance/review references, not as real-world scientific validation.

## Verification

- CSV round-trip passed; exactly 112 unique ordered IDs R001–R112 remain.
- Independently re-read the pre-edit snapshot and verified canonical fields plus both preserved baseline cells match exactly for every row.
- Every current evidence file path resolves locally; every updated status/slice/test/blocker/gap field is populated.
- Removed all generic `Specific implementation and evidence required by:` placeholders from current blocker cells.
- Confirmed every `DONE` row has documentary `NOT_APPLICABLE` real-data status and every master-validation cell remains `NOT_VALIDATED`.
- Searched source, scripts, tests and workflows for matrix/header consumers; none were found. Added baseline columns therefore have no identified runtime consumer impact.
- Scoped `git diff --check` passed. CSV output uses LF line endings, removing the earlier CRLF whitespace warnings without changing field content.
- No full test suite was rerun for this documentation-only change. Repository status showed the CSV as the only tracked modification made by this task; concurrent Task3 untracked files were left untouched.

The matrix remains an evidence-backed work ledger, not a percentage or completion claim. Canonical remote-tree materialization, new remote CI and live full-chain behavior were not independently verified by this cleanup.
