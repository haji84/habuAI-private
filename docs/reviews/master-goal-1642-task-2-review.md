# Independent Task 2 review

Reviewed commit range `9639c41..55795f8`, the Task 2 brief/report, normative spec including independent-review resolutions, contracts, orchestrator, CLI, tests and current Actions consumers. No implementation changes. The reported 97-test suite was not repeated; three focused probes were executed.

**Spec compliance: changes required. Code quality: changes required.** The snapshot inventory, stable identity, locked execution, explicit missing-adapter blockers and conservative input revalidation are sound foundations. However, recovery does not yet verify every completed-stage artifact and the operational boundary can lose failure semantics or leave stale success on an exception. No Critical finding; three Important findings below. Missing future model, Champion and development implementations are intentionally BLOCKED and are not findings against Task 2.

## Important 1 — Completed-stage artifacts are unverified during interrupted-run recovery

`src/master_orchestrator.py:204–213, 319–325` (also resume verification at 157–162).

`save()` checkpoints the stage JSON envelope, but generated files referenced by it are added to `output_hashes` only after the entire pipeline exits. A hard stop in model evaluation therefore leaves a completed operational stage whose generated report/CSV are not checkpointed. `_snapshot_matches()` excludes generated reports and new REPLAY files, so resume accepts changes to these artifacts and reuses the completed stage. The finalizer then hashes the changed bytes, effectively certifying the alteration.

Reproduced using a subprocess model adapter that calls `os._exit(77)` after operational scoring completes. The operational report was absent from checkpoint outputs. Replacing `snapshot/reports/pdca/2026-09-30/pdca_result.json` with `{"tampered":true}` and resuming returned BLOCKED with no CHECKPOINT_INVALID; the tampered artifact survived and entered final hashes. This violates verified output recovery independently of the intentional missing-adapter blockers.

Persist each stage's generated artifact inventory/digests before marking that stage complete. Treat uncommitted artifacts from an interrupted stage explicitly (reject or remove/recompute); do not silently adopt them as verified evidence. Add a killed-worker test that corrupts a completed stage's referenced artifact before resume, plus an injected new REPLAY artifact case.

## Important 2 — Malformed operational payload can escape finalization and retain stale PASS

`src/master_orchestrator.py:254–260, 331–337`.

The operational payload is stored without blocker-field validation, then its blocker lists are consumed outside the exception guard. A payload with `implementation_blockers: [{}]` reaches `dict.fromkeys()` and raises `TypeError`. No current-run FAIL manifest/compatibility result replaces the old report. This directly violates the exception/current-run failure contract and exposes the existing Actions stale-report reader.

Reproduced by precreating a compatibility result with `overall_status: PASS`, then mocking the operational adapter to return `{overall_status: PASS, stages: [], implementation_blockers: [{}]}`. `run_master` raised `TypeError: unhashable type: 'dict'`; the old PASS remained byte-identical.

Validate the operational result before saving it, and include aggregation/artifact collection/finalization failures in the durable failure path. Also test generated-artifact validation failures during finalization, which currently run outside that guard.

## Important 3 — Operational nested failure is trusted as PASS when its summary disagrees

`src/master_orchestrator.py:254–258`.

The parent directly trusts `result['overall_status']` without checking child stages. A malformed/inconsistent adapter response with `overall_status: PASS` and an inner stage `status: FAIL` is published as an operational stage with status PASS, validity VALIDATED and gate PASS. Its reason even contains the inner failure. The current missing adapters prevent aggregate PASS, but do not repair the false validated operational evidence. Task 2 explicitly requires stage errors not to become success.

A targeted mock reproduced exactly this response. Validate operational stage structure and aggregate consistency; an invalid or internally contradictory result must become FAIL while independent model research still runs. Test a contradictory PASS/FAIL payload and missing/invalid stage structure.

## Separate integration needs for later Actions work

These are unresolved cross-slice contracts, not missing Task 2 adapters:

- The fixed input namespace allowlist excludes `evidence/` and `model_specs/`. This is an integration requirement rather than a demonstrated current read gap while those inputs are not consumed. Before enabling adapters that reference them, extend the declared consumed-input inventory/snapshot contract and fail on unsupported external references; do not assume arbitrary future inputs are already covered.
- Current workflows upload and potentially `git add reports/pdca/$NIGHT` recursively. That now contains full input/code/model snapshots and checkpoints, not merely summary reports. Define the exact persisted artifact set, retention/size treatment, and content-verified restore procedure for a fresh runner; neither workflow currently restores a previous checkpoint before running. Local flock alone does not provide event/poller cross-run idempotency.
- The workflows currently read a preexisting compatibility file after command failure without binding it to this invocation. They must validate the current run result and execution outcome; Important 2 demonstrates a concrete exposure until this integration is fixed.
- `pdca_report.md` and `exposure_units.csv` are now under `runs/<id>/snapshot/reports/pdca/<night>/`, while only `pdca_result.json` is republished at the old top-level path. Consumers must use documented run-relative references or an explicit publication view. Preserve historical snapshot immutability when adding that view.

The existing local concurrency, ordinary duplicate, byte-preservation, and input-change tests provide useful coverage. The reported full-suite pass is implementer evidence; this review's independent execution was limited to the three focused reproductions above. No remote Actions verification or production/scientific success is claimed.
