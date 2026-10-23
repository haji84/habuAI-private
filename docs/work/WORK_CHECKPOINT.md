# Habu AI Work execution checkpoint — 2026-10-21

Master authority: https://github.com/haji84/AI-/issues/1642
Private canonical repository: https://github.com/haji84/habuAI-private
Status: IN_PROGRESS / PARTIAL. No production or scientific completion claim.

## Verified current repository state

Latest re-read main: `27f4832a23f0a3826ce96b87afb4f2f1c58aa936`. No main integration occurred in this session. Main remains the canonical source; candidate branches are not substituted for it.

| Task ID | Implementer / independent verifier | Current evidence and disposition |
| --- | --- | --- |
| HABU-WORK-20261021-CI34 | parent Work controller / authenticated GitHub job and account UI | Included Actions 2,000/2,000 minutes, account Actions budget $0, Usage blocked. Issue34 now records a confirmed account gate. No billing/security/visibility changes. |
| HABU-WORK-20261021-PR32 | fix_pr32 / review_pr32 | Existing PR32 head `123109a630b16f7af4e5cc41482ddd10839351b5`; fixed-dependency-profile local 287 tests PASS, independent 18 and targeted 41 PASS. Known-outcome, UTC identity, actual-byte and work-budget corrections. Draft, unmerged. Exact-head CI39594265389 fails before runner allocation (0 steps). |
| HABU-WORK-20261021-PR33 | fix_pr33 / review_pr33 | Existing PR33 head `cd97e69a2d1cfb160b21f33a3e561be989d5ba8d`; fixed-dependency-profile local 263 tests PASS, targeted17 and independent adversarial/real-OSM review PASS. Actual source availability, late-publication cleanup and output-path guards. Draft, unmerged. Exact-head CI39593746339 fails before runner allocation (0 steps). |
| HABU-WORK-20261021-DATA43 | data_audit / review_pr33 plus parent | Existing PR43 head `76680cba924b72a9069a4d12b0819cae95fd5349` is the sole continuation PR for the recovered quantity-corrected originals, staged receipts, corrected legacy display and reproducible source tests. Fixed-dependency-profile full suite269PASS (52.122s, exit0), all11manifest blobs and281candidate-file hashes unchanged. Exact final branch SHA/tests appear in the evidence manifest. Incoming source is not canonical label admission. |
| HABU-WORK-20261021-LEDGER | parent / independent checkpoint reviewer | Original112 requirement IDs retained, current audit columns added, one stale Task6a NOT_IMPLEMENTED statement corrected. Historical status milestones remain historical. |

PR32/33 trees were compared with their original exact heads after update: only each PR's existing three files changed, zero deletions. No Raw/ORIGINAL/model/Champion/dependencies/workflows/permissions changes in either repair. Exact file hashes and separate implementations/reviews are in this checkpoint's evidence bundle.

## Data findings that must survive restart

- PR39 head `5d05e4889ebd37e50fd6e2eb29c7589b25b8e30a`: four actual GPX nights verified. PR41 head `28c42bf91420d38ae1ca276b106982edb3f0d5bf`: ten stored archives fully recoverable; its earlier prose claiming pending transfer is stale. PR42 head `4e003cd1036f32ce09bb1be6e909c6edbbff4931`: only4/25 transport parts, still incomplete and not a source of recoverable originals.
- PR43 audited source head `415837c3713a167794149770f1228190fa158fe6`: its original ZIP and 07h workbook archives are complete. The quantity-corrected workbook/validation ZIP absent at that head were recovered byte-for-byte through the existing authorized file workflow and staged append-only on the same PR.
- September: 50 owner-capture events / 51 individuals. October selected transcription:17 /17. Combined:67 events /68 individuals, distinct from1,117 new source events and3,853 historical event-view rows.
- All67 capture encounters associate with actual GPX within100m and600s. Two individuals at the same encounter do not become two independent spatial observations. This is historical data association, never prediction accuracy or official KPI evidence.
- The 15 September original GPX files are preserved in a 7,945,041-byte ZIP, SHA-256 `162b01718cd2916e2b3bdfa61f506e54a63ee4d54e03bd73672cb9804e324ecb`. Independent QA matched all69,910,267 original bytes,264,406 timed points and50 September log links. September2/28 are intentional copies of existing MAIN sources, not new observations. Search role, complete coverage, Negative and Gold eligibility remain unassigned.
- Main's September28 five events/six individuals and PR39's October14/15 six events/six individuals overlap this candidate:11 events/12 individuals. Preserve/link existing identities; do not append duplicates. Two source-derived record IDs change after quantity corrections, so matching cannot rely on the old ID string alone.
- The recovered quantity-corrected workbook reintroduces101 old capture-display operational-night errors. It remains immutable forensic source, not an authoritative latest table. The derived314-row CSV changes only the101 night fields, preserves all other columns and23 unparseable timestamps, and is a candidate only. Legacy capture labels are not newly verified owner captures.
- The primary3,853-event master has3,834 parseable timestamps with zero observed night errors and19 unparseable timestamps; do not say all3,853 were timestamp-validated. The new1,117 rows are all parseable and correctly attributed.

## Completion and noncompletion

Current main's source/spec/test snapshot was hydrated by authenticated API:228 unique Git blobs matched exact Git IDs;154 explicitly listed large/archive blobs were omitted from that parent snapshot. It is not a full clone. The independent data/OSM workspaces separately restored their pinned required originals; no full-main historical dry-run was fabricated from the partial copy.

Actual OSM ZIP/CSV hashes,16,990 auxiliary road cells and a maximum six-window101,940-row prospective shard were verified. This is not a full-night universe, legal/current road-passability proof, trained production model, official time-target forecast or route.

Scientific Stage1 Top10 Recall>=90% and final100m±10min performance remain NOT_VALIDATED. No Champion was promoted, no ORIGINAL/P0 was issued or rewritten, and no test fixture establishes real-world precision. Task7 durable development control and Task8 trusted production remain incomplete. No completed merge or production E2E is claimed.

## Runtime evidence boundaries

A fresh isolated Python3.12.14 environment installed the existing requirements-analysis.txt and requirements-osm.txt pins (numpy2.2.6, scipy1.15.3, scikit-learn1.5.2, pandas2.2.3 and pyarrow21.0.0); pip check passed. PR32 passed287 tests, PR33 passed263 tests and final PR43 source-plus-GPX candidate passed269 tests with unchanged pre/post file hashes in this environment. Earlier global-runtime logs are retained as separate historical local runs, because those library versions differed. The first PR43 workspace preflight found two stale ancillary receipt/report copies and failed their hashes; that failed receipt is retained unchanged. All11 files were re-synchronized from their frozen source manifests before the269-test run, whose pre/post manifests pass. See pinned-runtime/preflight-qualification.json. These local runs are not hosted CI or full production E2E. See pinned-runtime exit receipts and the manifest for PR43 final verification.

## Next bounded tasks, in dependency order

1. CI34: do not retry unchanged billing failures indefinitely. Wait for included allowance reset or explicit owner authorization of any paid budget change. The annotation's alternative payment-failure wording is not proof of failed payment. No new credentials, runner permissions or spending are authorized.
2. Once hosted execution is available, rerun the exact final PR32 and PR33 revisions, verify the workflow identity, latest attempt, runner, steps and test logs. If any head/base changes, reconcile source scope and repeat affected review/tests. Only then perform authorized ordinary merge.
3. Re-read main after each merge and run the corresponding integration/smoke checks. Unit-test CI success alone does not establish the scheduled poller/one-command bridge is recovered; run and retain a separate live smoke test.
4. Finish PR39/41/43 source integration only after their exact-head CI and independent scope review. Resolve incomplete PR42 as superseded/blocked source evidence without deleting it or counting it twice. Keep originals and old corrected versions.
5. Bind canonical event identities and only audited label/observation roles. Preserve ambiguous timestamps, legacy labels, unknown search role and incomplete logging. A GPX association does not by itself create a negative or a complete outcome denominator.
6. Continue existing Task6b TRAIN_ONLY corpus/feature-aware model plan, then real availability-bound weather/environment/DEM/road features and full future universes. Use retrospective history only for later fits once genuinely ready; no fabricated historical forecast access or fresh confirmation status.
7. Continue count/time/size/detection and topology-based A/B/C adapters under existing plans, then Task7 durable request/claim/result/recovery and Task8 independent production reproduction/registry/issuance. Missing independent confirmation and unspecified scientific thresholds remain explicit gates.

Persist each task's Goal/Stage/Task IDs, base/head hashes, AllowedPaths, attempt, tests/review/CI, integration SHA, E2E result and next/block reason. Reuse the existing task PR for repairs, reconcile remote heads before writes, and never reuse an old PASS against changed code.

## Liveness boundary

The existing Actions poller is configured every five minutes and the issue-open workflow remains in place, but hosted execution is currently blocked. No new background daemon, credential, service or wake-up mechanism was created. This checkpoint is durable restart state, not evidence that Work keeps running after its session ends or that the unimplemented Task7 controller has become autonomous.
