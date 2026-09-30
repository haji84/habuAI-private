# Task 4 fix-round 1 independent re-review

Scope: `96c6cb0..f3c7763`, prior three Important findings, original Task 4 brief and updated remediation report. The narrow shared inference-validator edit was parent-authorized. Unrelated parent documentation/matrix changes were ignored. No code edits, nested agents or full-suite rerun.

**Spec compliance: one narrow repair remains. Code quality/integrity: changes required for directory ancestry durability.** No Critical finding or production bypass. Findings 2 and 3 are ADDRESSED. Finding 1 is PARTIALLY ADDRESSED: staging-directory durability and cleanup are fixed, but the added new-parent durability loop stops too early for supported recursively created roots.

| Prior finding | Disposition | Evidence |
|---|---|---|
| Staging/publication durability | PARTIALLY ADDRESSED | Both files are fsynced, then staging directory, then rename and destination parent. Failed staging sync cleans pending output without reserving P0. However, recursively created ancestors above root.parent are not fully synced; narrow remainder below. |
| Empty-universe validation misses invalid probabilities | ADDRESSED | Default and every area value are checked before the row loop, including unused areas. Both probability families reject values above one; existing finite/nonnegative checks remain. Score-only families retain values above one and probability=null. |
| Window alignment checked outside JST | ADDRESSED | Parsed timestamps are converted to Asia/Tokyo before ten-minute alignment validation. Equivalent UTC/+05:45 encodings of aligned JST windows pass, while the reproduced 21:15 JST window fails. Absolute-time prospectiveness remains enforced. |

## Remaining Important — Newly created root-parent link is outside the sync loop

`scripts/freeze_prediction.py:72–73, 105–116` at `f3c7763`.

`root.mkdir(parents=True, exist_ok=True)` can create both the requested root and its previously absent ancestors. The new ancestry loop stops after syncing `root.parent`. If that directory was itself created by this call, its own directory entry resides in the next ancestor, which is never fsynced. The existing regression uses an already-existing TemporaryDirectory root, so it cannot exercise this branch.

Focused reproduction: start with existing temporary directory T and call Freeze using root `T/new-parent/new-root`, with both nested directories absent. Publication succeeds. Instrumented actual fsync calls include `T/new-parent` and descendants, but never T. Therefore the new `new-parent` link is not durably established under the intended local-filesystem crash contract. This is an observed ordering gap, not a performed destructive power-loss experiment.

Required bounded repair: establish durability through the parent of every directory created by recursive root/output setup, including the first already-existing ancestor, with a retry policy that does not assume visible directories from an earlier failed sync are durable. Alternatively, explicitly validate an existing root-parent prerequisite before creating directories if that restriction is the chosen supported API contract. Add a nested-absent-root regression and an ancestor-sync failure/retry case. Keep current staging cleanup/order and final parent fsync behavior.

## Independent checks

Six selected regression tests passed: complete probability-state rejection; valid score-only values above one; staging/file/rename/parent fsync ordering; failed staging sync cleanup/retry; equivalent-timezone JST alignment; concurrent contiguous freezes. An additional actual-call instrumentation probe found the nested-root ancestry gap above. The reported 163-test full suite is implementer/parent evidence, not a suite repeated in this review.

No other Important regression was identified in this fix. Production authority remains fail-closed; sandbox lifecycle remains explicitly mechanical and does not establish scientific validation. Changes to the actual inference code hash correctly prevent old adapter-bound model artifacts from being silently relabeled as current.

## Final narrow re-review — approved at `7a95ff9`

Reviewed exact commit `7a95ff9b3fbcf3b01c9dab7f3fa0dccf6f2afc09` against `f3c7763`, limited to the remaining ancestor-durability finding and its failure/retry regression. Read the finalized round-2 implementation report.

**Remaining finding 1: ADDRESSED. Final spec-compliance and code-quality/integrity verdict: approved for bounded Task 4.** All three original Important findings are now addressed; no remaining Critical/Important issue identified in these scoped reviews.

Freeze now rejects a missing root parent before creating any directory and creates only the immediate root beneath the already-existing durability boundary. Its existing sync loop therefore covers the parent of every directory that this supported operation can create. Retries still repeat ancestor syncing rather than assuming a visible directory from a failed attempt is durable.

Both focused tests passed independently: nested absent-parent roots fail before creation while an immediate new root succeeds; injected existing-ancestor fsync failure publishes no P0, and a subsequent attempt demonstrably syncs the same ancestor again before publishing P0. No broader suite or destructive power-loss test was repeated. The report's 165-test full-suite pass remains implementer/parent evidence.

Approval preserves the stated restriction that the root parent must already exist and the supported local-filesystem/fsync contract. Probability validation and JST normalization approvals from round 1 stand. Production authority, scientific gate reproduction and full Master completion remain intentionally BLOCKED; sandbox success remains mechanical evidence only.
