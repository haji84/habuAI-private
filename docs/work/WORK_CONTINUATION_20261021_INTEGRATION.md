# Master Goal continuation: local premerge integration

Goal: haji84/AI-#1642. Task: HABU-WORK-20261021-PREMERGE-INTEGRATION.
Stage: Stage2/3. Attempt: 20261021-combined-candidate-1.

**Historical integration diagnostic, reconciled 2026-10-25:** all head,
unmerged-PR, hosted-CI and next-task statements below describe this dated
attempt. Its retained manifests and logs remain unchanged. For current
integration use `CODEX_PARALLEL_MASTER_20261025.md`, coordinator-owned
`CODEX_STATE_20261025.json` and freshly verified GitHub evidence; this document
does not report a current CI outage or reopen already integrated work.

Latest re-read main remains `27f4832a23f0a3826ce96b87afb4f2f1c58aa936`.
PR32 `123109a630b16f7af4e5cc41482ddd10839351b5`, PR33 `cd97e69a2d1cfb160b21f33a3e561be989d5ba8d`, and PR43 `76680cba924b72a9069a4d12b0819cae95fd5349` remain Draft/unmerged. Hosted execution has not recovered: latest inspected main poller39599605213 has a failed job with blank runner and zero steps. No manual retry, new spending, settings change or main merge was performed.

## Newly executed checks

The exact final PR43 source/test workspace was combined with the six reviewed files from PR32/33 in an isolated candidate. Its composition matches all287 expected file hashes. This is the existing authenticated partial source/test snapshot plus separately restored required sources, not a full clone of every main raw archive.

- Fixed dependency profile: **327 tests PASS**,57.399s, child and driver exit0, all287 file hashes unchanged. See `suite-exit.json`, complete log, pre/post maps and `composition.json` in the addendum evidence directory.
- The actual PR33 producer read the verified33-part OSM archive and emitted a six-window shard. The actual PR32 consumer received that exact unmodified snapshot after the real cutoff. **16,990 road cells ×6 windows =101,940 rows**, all **305,820 feature values** compared with the actual source CSV, five consumed hashes consistent.
- Actual source-ready12:44:47.573703Z <= completed12:44:47.590710Z < cutoff12:45:06.613552Z; real consumer as_of12:45:06.613696Z on2026-10-21. No fake clock or availability backdating was used. Candidate287 files and original33 transport parts remain unchanged.
- Producer `official_prediction_eligible=false`; consumer `official_issuance_authorized=false`. Auxiliary OSM eligibility, full-night coverage, environmental features, trained Champion, formal outputs, routes and trusted issuance remain separate gaps. These are integration diagnostics, not a formal forecast or scientific performance result.

Implementer roles: parent for composition/full suite; fix_pr33 for actual producer-consumer diagnostic. Independent verifier: review_pr32. No repository implementation files were edited by this task. AllowedPaths are this new documentation, its review and the new integration evidence directory only. The original checkpoint files and original manifest at PR44 commit `5a38e6d755bddd9c3bfb6beeaff6ae9fcf797e7c` retain their bytes and historical scope.

## Evidence preservation and limits

See `evidence/master-goal-1642/work-2026-10-21-integration/manifest.json`. The diagnostic scripts, full log, result receipts, source hashes, all pre/post maps and exact emitted snapshot are retained. The roughly41MB reproducible generated universe/feature payloads are kept in the transient diagnostic workspace, not duplicated as formal prediction records. Their hashes, sizes, source identities and execution parameters are retained. A fresh real-clock rerun will have different availability/cutoff timestamps and hashes. The saved diagnostic scripts retain original runtime paths. For a rerun, restore the isolated combined workspace from the pinned composition and verified OSM archive, use the pinned Python dependencies, and relocate the recorded ROOT paths to a fresh diagnostic workspace; do not run them as production intake or reuse an expired cutoff. The saved snapshot is a diagnostic artifact with auxiliary-only qualification, not ORIGINAL/P0 or a trusted availability receipt.

## CI recovery handoff

An already enabled ChatGPT conditional task named ハブAI CI復旧監視 was discovered and its prompt updated; its existing schedule was preserved. It now reads the private checkpoint and covers PR32/33/39/41/43/44 with exact-head/base CI, independent review, merge guards and fresh-main acceptance checks. Registration was confirmed successful; no new task or daemon was created. See `recovery-watch-handoff.json`. Task registration is not proof that any future run succeeds and does not complete the product's Task7/Task8 controller.

Next: detect actual execution recovery without unchanged retries, re-read heads and applicable reviews, run required exact-head/base CI, integrate only eligible revisions with an expected-head lease, and perform a separate fresh-main CI plus real bridge/poller or corresponding feature-builder smoke. If the execution environment cannot perform an acceptance step, retain NOT_EXECUTED/BLOCKED with evidence. Preserve raw bytes, event identities, Unknown eligibility,07:00 JST, scientific confirmation and immutable ORIGINAL/P0 rules. No fee/budget increase is authorized.

Main integration SHA: none new. Hosted CI: BLOCKED/FAILURE. Production E2E: NOT_EXECUTED_CI_BLOCKED. Master Goal: PARTIAL; Stage1 and final100m±10min scientific performance: NOT_VALIDATED.
