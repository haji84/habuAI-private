# Task6a handoff — executed evidence audit and derived learning builder

Status: implemented bounded Task6a; ready for independent review. Overall Master remains PARTIAL/BLOCKED, with no production or scientific approval. No remote operations, no raw/history changes.

## Interfaces and integration

- `src/evidence_audit.py`: `audit_evidence(root, night, *, verified_at=None, budget_seconds=300)` returns a hash-bound typed audit, source manifests, exact input hashes, source checks, compact GPX segment/point selectors, sampled coverage, eligible observations, independent outcome ledger, OSM resolution, recovered-response intake checks, and stable typed `input_requirements` (`code`, `kind`, `evidence_needed`, criterion). No capability ID is invented for data shortages. `audit_captures` is the shared strict capture parser.
- Inputs are contained source refs with SHA-256 binding and bounded reads. Raw intake receipts check promoted source bytes directly; incoming staging copies are not required or consumed. Source review is a source-bound declaration, not an authenticated scientific authority. Future receipts/reviews fail rather than making labels prematurely available. `checked_at`, first verified receipt, qualification time/basis, and immutable audit identity remain distinct; unchanged prior qualifications must be reused through a future hash-bound proof rather than backdated.
- `policies/observation_evidence.json` supplies source reviews and sessions. A session binds trajectory bytes, search/passage interval evidence, and a recording policy listing explicit capture files and `ALL_CAPTURES_RECORDED`. Source-qualified clean GPX segments may supply searched noncapture units; GPX alone, missing capture files, transit/unknown purpose, or anomalous segments remain UNKNOWN. Measured duration/distance is consecutive within-unit GPS measurement, not fabricated observer effort/version.
- Explicit capture identity/type, aware time, finite coordinates and exact positive count are required. Count 2 remains one canonical event/two individuals. Conflicting event IDs, rejected rows and invalid individual links are reported. Raw JSON capture statements are checked against summaries and processed event time/count; a match does not invent location authority. Unknown exact quantities remain rejected diagnostic source selectors, never default count 1.
- Full outcome coverage has an accepted input path: policy `outcome_coverage` refs bind a declaration with night, EPSG:4326 bbox domain ref, all capture-source hashes, and evidence of `COMPLETE_CAPTURE_LOG_FOR_DOMAIN_AND_NIGHT` over JST 07:00 to next 07:00. Known unresolved/conflicting/rejected captures prevent completeness. Valid explicitly complete empty capture CSV can establish a zero ledger; missing CSV cannot. The ledger retains all known qualified captures independently of the forecast universe, including outside-universe events. Complete declared scope is separate from authenticated scientific denominator validity.
- OSM reads only the explicitly approved `artifacts/Habu_AI_OSM_Road_Grid_2026-09-25.zip.parts` namespace: exact 33 parts, strict base64, archive SHA, bounded ZIP sizes/members, CRC, path/type checks, and exact manifest payload hash/size resolution. Bundled code is never executed. `archive_members` counts files; `unique_payload_hashes` separately handles duplicate file content. Current receipt availability does not establish historical OSM availability.
- `src/learning_snapshot.py`: `build_learning_snapshot(root, night, audit)` requires an explicit `features/learning_build.json` referencing hash-bound ex-ante universe/protocol/optional feature files and availability receipts. It never invents a historical universe from GPX. Generated rows preserve nullable UNKNOWN labels, exact coordinates, event/count lineage, label/feature timing, and measured effort only where supported.
- Generated `reports/learning_evaluation/<night>/` is an isolated evaluation workspace. Referenced universe/protocol/feature bytes are copied exactly; compact derived label evidence binds original audit/input hashes and selectors. Existing `data/processed/model_learning.json` is retained byte-for-byte. `_snapshot_matches` is unchanged. Generated files (4 MiB each / 10 MiB total maximum) are validated by Task3 `_validate` before publication, immutable on repeat, and bound by normal checkpoint report hashes. Tests prove generated artifact tampering fails resume.
- Master now executes the audit and builds a derived workspace before model evaluation. Missing ex-ante universe remains a typed data blocker. Operational scoring reuses the completed master audit via optional keyword `audited_evidence`, avoiding duplicate scans/reset budgets. Existing two-argument direct pipeline callers remain supported; three existing test wrappers forward the optional keyword without weakening their assertions.
- `build_exposure` alone yields UNKNOWN. Summaries separate sampled from observed counts, preserve null rates for no eligible observations, and do not turn missing completeness into FP.

## Runtime bounds

Master checks its shared remaining budget before starting audit and skips dependent stages with RUNTIME_BLOCKED when audit cannot run. A zero-budget master invokes no auditor and still emits all nine stages, without reading a nonexistent report. Audit checks deadline in source/row/point/segment/session/archive loops, with 1,000,000 GPX points, 4,000 source reads, and 512 MiB cumulative source-read ceilings (100 MiB individual source ceiling). ZIP additionally caps 10,000 members / 300 MiB expanded bytes / 100 MiB member. Budget exhaustion discards observation output and emits typed RUNTIME_BLOCKED, distinct from missing data or integrity FAIL. Individual bounded parse/hash/decompression operations are cooperative, not OS-preempted; the existing master snapshot inventory/copy behavior is unchanged.

## TDD and tests

Initial new auditor tests failed for missing implementation; builder tests failed for missing implementation; GPX-only regression initially failed with inferred negatives. The final zero-budget regression failed because the auditor was called; resource-limit regression failed for missing bounds. A future-review regression failed because it could label negatives at an earlier audit time. Each was verified green after its bounded implementation.

Commands used:

- `python -m unittest discover -s tests -p test_evidence_audit.py -q` — final 22 passed.
- `python -m unittest discover -s tests -p test_learning_snapshot.py -q` — final 7 passed, including actual master generated workspace, unchanged input inventory, repeat/resume, and corruption rejection.
- `python -m unittest discover -s tests -q` — **226 passed in 40.840s**. Log: `/workspace/scratch/fb45a4f31791/task-6a-final-tests.log`.
- `git diff --check` — clean.

Adversarial coverage includes receipt/archive corruption, UTC/JST boundaries and naive time rejection, per-segment duplicate/backward/gap/speed issues, count2/individual links/conflicting IDs, missing source vs explicit empty complete CSV, absent roles/session bounds, retained outside-universe positives, false/backdated availability, source mutation, OSM duplicate file content vs file count, all-UNKNOWN rows, immutable supplied learning inputs, checkpoint recovery and generated artifact corruption, and exhausted shared audit budgets.

An initial full run found two existing subprocess adapter tests failing due to eager private model-validator imports inside the new builder. Imports now occur only after builder prerequisites exist, preserving model-adapter isolation; the complete final suite passes.

## Final historical run and protected inputs

Executed in isolated `/workspace/scratch/fb45a4f31791/task6a-real-run-final`, copied from exact current master input inventory. Script `/workspace/scratch/fb45a4f31791/task6a_verify_final.py`; machine proof `/workspace/scratch/fb45a4f31791/task-6a-real-verification-final.json` contains source hashes and requirement details.

- Run ID `d32551b1f02d93d4cc821e952d7fb97817037ea3c68ba42168e4445924403931`; 7.635 seconds; all nine stages; overall BLOCKED. Evidence audit PARTIAL; operational scoring PARTIAL; learning/model stages BLOCKED; development/trusted promotion/handoff still blocked.
- All 14 actual GPX sources checked: 266,737 points (13 raw historical tracks plus Sept28 archive 22,990). One zero-time delta and 210 speed-outlier segment diagnostics; no fabricated cleaned source.
- Requested Sept28: 947 sampled units UNKNOWN, 0 eligible observations, 6 diagnostic captured individuals, 0 canonical qualified events; denominator NOT_ESTABLISHED. Missing outcomes for other nights stay UNKNOWN.
- OSM: 99 of 99 manifest refs resolved, 112 file members, 82 unique payload hashes. No obsolete missing-byte blocker retained.
- Recovered response intake: 6 raw responses verified; 11 capture statements remain candidates; 0 canonical labels admitted.
- 51 protected repository raw/prediction/report files SHA-256 unchanged. Audit report 357,901 bytes, within compact recovery artifact limits.
- Audit digest `8c9a98ac9bf6e2ed2b5976225cdd8b916682c34c2367d6d7e00f1dcca1a89e1a`.

The earlier 14.927s proof remains `/workspace/scratch/fb45a4f31791/task-6a-real-verification.json`; its OSM `82` field counted unique payloads, not file members. The final proof explicitly corrects this and includes raw-log/budget guards.

## Remaining limitations / next slices

- No authenticated authority for manual review/coverage declarations is implemented here. Source/hash/time/scope consistency is checked; all science remains NOT_VALIDATED. Production activation is still Task8 fail-closed.
- Actual historical sources lack the required role/session/completeness and historical ex-ante universe proofs. Existing v1 builder stays strict. This is not a claim that August observations cannot train future October models: parent-approved Task6b TRAIN_ONLY corpus design must reuse immutable audit-qualified source/availability evidence without inventing historical forecast universes.
- Persisting/reusing an earlier qualified audit as authority is not implemented in v1; the report separates current qualification time from received time so future reuse can verify the original immutable proof. Re-audit does not silently claim it occurred earlier.
- Full coverage is established only for a supplied source-bound domain/night declaration, never globally from no events. Task3 restricted-universe recall remains diagnostic and cannot promote. This slice does not implement formal model outputs or the trusted complete recall gate.
- Current GPX QC conservatively disqualifies an entire affected segment; raw data and point/segment selectors are retained for a future separately reviewed cleaning policy.
- Audit work is cooperatively time bounded and source size/read/point capped; a single bounded parser/hash operation is not forcibly interrupted. Existing master input inventory/copy work is outside this new auditor's bounds.

Local implementation commit: `3dcc2f8` (`Audit source eligibility and build immutable learning workspaces`), ten explicitly owned source/test paths only. No parent docs, archives, raw inputs, or historical prediction/report files staged.
