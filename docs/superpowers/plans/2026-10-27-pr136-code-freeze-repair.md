# PR #136 development code freeze repair

> For agentic workers: execute this bounded repair inline; use an independent reviewer before reporting the repair as reviewed.

**Goal:** repair the stale development code snapshot in existing Draft PR #136 without changing scientific evidence, approvals, validators or dashboard behavior.

**Architecture:** retain all historical cycle manifests byte-for-byte. Add a new `DEVELOPMENT_CONTRACT_ONLY` cycle covering the current conservative code closure and advance the existing hash-bound cursor. This grants neither scientific nor production authority.

**Tech stack:** existing Python unittest, SHA-256 and GitHub Actions.

**Spec:** owner repair request for https://github.com/haji84/habuAI-private/pull/136 ; existing `AGENTS.md`, `src/codex_cycle_contract.py` and `protocols/development/g0-policy-v1.json`.

## Constraints and review focus

- Preserve Raw, ORIGINAL predictions, scientific protocols, historical cycle manifests and official approvals.
- Keep mixed exploration nights, 07:00 Asia/Tokyo rollover, confirmed zero-capture search nights and duplicate/conflict rejection.
- Bind every current code path, including `scripts/import_owner_batch.py`; preserve all existing fail-closed checks.
- No main integration, production deployment, security-policy change or PR #92 integration in this bounded repair.
- Confirm snapshot identity rather than claiming the unreviewed PR already has formal approval.

## Diagnosis

Observed PR head: `083eb2905b27f9e9d501e591f8804665c818b039`.
Observed main: `eaf32341393add34a19fe3f1d9ec27a0cd88585f`.
The supplied earlier head `2a05696df27f523bbbe7ae76266ad948cf098819` is an ancestor; it is not the latest source tested here.

The cursor is correctly byte-bound to `protocols/development/cycles/20261026-hba2-preparation-v3-01.json` (file SHA-256 `6629839727ff9b7a89ec817bf6cb4d9726b65c5289f4b5988aa4cb4f9511404a`). That historical snapshot covers 102 code paths and exactly matches the main dashboard builder. PR #136 intentionally changes that builder and introduces one new Python script, making 103 paths. There are no other changed or missing entries in the code closure.

| Builder source | SHA-256 |
| --- | --- |
| Historical manifest and observed main | `7644e8f6bf32cabaeb490d08458b7dfb8b31f4ff29cb66aabfbb3d87ff0d5926` |
| Supplied earlier PR head | `9691dc88ab2ad55bc9bb3c3c898257b25aa5d82a265278972c755bb1ba18b7f0` |
| Observed latest PR head | `297e6006e0ea5595b5b952820c2d5446b38f95323975443ca710ee7b986a5d2d` |

Current failure reproduces with `python scripts/check_codex_cycle.py`: `HASH_MISMATCH: scripts/build_capture_dashboard.py`. Updating only that entry would still leave `scripts/import_owner_batch.py` outside the required closure.

Latest observed CI: dashboard run [40308434339](https://github.com/haji84/habuAI-private/actions/runs/40308434339) succeeded; intake run [40308434358](https://github.com/haji84/habuAI-private/actions/runs/40308434358) ran 1,754 tests successfully (32 skipped), then failed at the code-freeze check. The latter checked GitHub's synthetic merge `4ef34bd0ded2459e5c3a106afa8de61bcc3904d2`, so it must not be described as a direct head checkout.

## Task 1: additive development snapshot repair

Files: `tests/test_capture_dashboard.py`, a new `protocols/development/cycles/20261027-owner-intake-01.json`, and `protocols/development/current-cycle.json`.

- [x] Add a regression invoking `validate_current_cycle(ROOT)` against real repository bytes, requiring the dashboard builder and batch importer and verifying no science/fit/production authority.
- [x] Add a regression pinning the previous cycle's exact file SHA-256.
- [x] Observe the new real-repository regression fail on the stale snapshot.
- [x] Create a new cycle using the existing `code_paths` registry; retain the existing policy reference, set the observed main SHA and actual creation time, and advance the cursor to the new file hash.
- [x] Run targeted dashboard, intake, GPS, freeze and access-protection tests, direct code-freeze validation, dashboard build and export privacy checks.
- [ ] Independently review the bounded diff, run the full unittest suite, and update the existing PR branch using an exact-head lease.
- [ ] Inspect new CI conclusions for the repaired source head. Leave Draft and all merge/deployment blockers in place.

## PR #92 and publication boundaries

PR #92 head at investigation: `b80eec0a45e19271bb888113aef1167a911de79d`. It independently changes the builder, dashboard UI, tests and workflow and introduces reports for the same October 22/24 totals. It is not merged into observed PR #136. Thus it is a separate integration conflict, not the cause of the present stale-manifest failure. The existing `read_owner_effort_overlay` guard rejects either overlapping reconstruction file; preserve and test it. Reconciliation of both pipelines and full feature review remain merge blockers.

The repository metadata is public despite its name. This repair introduces only code hashes and aggregate diagnostics. The existing workflow forbids its deployment job on `pull_request`, requires `HUB_NATURAL_ACCESS_VERIFIED`, and checks both production and preview URLs before deployment. No live Access verification is claimed by this repair.

## Execution record

- RED: `python -m unittest discover -s tests -p test_capture_dashboard.py -k development_freeze -v` failed with the exact original `HASH_MISMATCH` before the cursor repair.
- GREEN: 84 targeted tests passed across capture statistics/effort/automation, mixed-night intake, smartphone GPS, frontend JS, code contract/cursor/prewalk and Access/bootstrap gates.
- Direct `python scripts/check_codex_cycle.py` passed: 103 input code paths, `CONTRACT_VALIDATED`, science `NOT_VALIDATED`, fit/production false, folds `UNALLOCATED`, confirmation `UNSELECTED`.
- `python scripts/build_capture_dashboard.py` and syntax checks for intake-core.js, field-core.js and field-app.js passed. Export privacy checks passed with total 249, 97 search nights and 11 zero-capture search nights.
- Historical cycles, policy, source code, workflows, Raw and predictions are unchanged by the repair.
- `git merge-tree --write-tree HEAD origin/feat/dashboard-pdca-owner-intake-sync-20261025` confirmed four content conflicts: dashboard/index.html, docs/hub-natural-dashboard.md, scripts/build_capture_dashboard.py, tests/test_capture_dashboard_frontend.py. The command did not change the working tree or merge the PR.
- The previous dashboard CI deployment job was `skipped`; no deployment is performed by this repair.
- Independent read-only reviewer `review_pr136_repair` returned PASS for this bounded repair with no Critical/Important/Minor defects. It independently verified all 103 code hashes, all 46 historical cycle files and unchanged policy, reproduced both the original HASH_MISMATCH and the subsequent CODE_CLOSURE if only the builder hash were changed, and ran 21 focused tests successfully. Both PR #92 overlap filenames were independently checked to fail closed. This review does not approve the whole feature, main integration or deployment. The full pinned-dependency suite is running; final repaired-source CI conclusions will be linked from PR #136 after the branch update.
