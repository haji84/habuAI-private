# Foundation integration review: Tasks1–5 and recovered-source archive

Review scope: local foundation at a92da67 with Task5 repairs ongoing; canonical goal/spec, AGENTS, 112-row matrix, status, operational/Freeze/model/Champion/issuer code and archive records. Detailed Task5 security/recovery review belongs to review_slice2 and is deliberately not duplicated. No repository edits. Remote df35e/PR28 tree and final exact CI were not independently fetched here; remote merge eligibility is conditional on parent verification.

Verdict: foundation plus reviewed Task6a can be a legitimate reviewed main milestone, without completing the Master. Parent has accepted Task6a eligibility as a concrete pre-merge gate: finish Task5 repairs, implement/independently review Task6a, include it in PR28, refresh accounting and verify exact published-head CI before main integration. Do not equate local tests or stage coverage with scientific acceptance.

## Findings

### High — unresolved observation evidence still becomes negative/FP data

Paths: src/pdca_pipeline.py:build_exposure, score_prediction, run_pipeline (approximately lines221–233,290–292,501–502).

Every GPX-populated unit lacking a known capture receives label0/observation=observed_negative. The loader supplies coordinates/time/source hash but no audited search-role or complete-outcome eligibility, so passage, incomplete logs and spatial/trajectory-quality uncertainty are not checked. score_prediction consumes those rows as confirmed negative targets and precision denominators; build_exposure stage reports PASS. Global official-score ineligibility protects production claims but does not make these negative/FP artifacts true. This remains a direct Unknown!=Negative risk when the extended bridge publishes diagnostic results.

Resolution before accepting those metrics on main: either integrate reviewed Task6a eligibility or add a narrow conservative guard now so unverified units are UNKNOWN/null and cannot contribute FP; valid captures remain positive. This does not require completing the entire research/data builder before foundation merge. Tests requiring observed negatives must supply explicit matching eligibility. Do not waive the invariant by merely adding another top-level NOT_VALIDATED message. If parent elects to merge foundation before this repair, explicitly treat this as an outstanding known correctness defect and disable negative-dependent report metrics; do not report it as safe completed exposure correction.

### Medium — traceability matrix is stale and contradicts reviewed Task4

Path: docs/specs/master-goal-1642-gap-matrix.csv, especially R085/R087/R088/R090/R091/R105/R111/R112 and R101–109.

The CSV has exactly112 unique rows, appropriately separates implementation/real-data validation, and does not fabricate Master completion. However, R085 says no reviewed append-only registry exists; R087 says no reviewed CAS/rollback executor exists; R090/R091 likewise deny activation-time selection/history mechanics. Task4 now implements and reviews these in an isolated sandbox. R105 says no actual promoted-Champion inference/handoff has been implemented, whereas test-only actual inference exists. R112 still describes Task1/2 and lists Tasks3–8 all remaining. These are conservative underclaims, but they make the required requirement-to-implementation mapping inaccurate for the PR being merged.

Resolution: credit Task4 specifically as SANDBOX_MECHANICS/partial implementation with exact tests/review references, retain trusted production activation/real-data gaps. Update Task5 rows only after its review, distinguishing local implementation from live cross-runner evidence. Preserve the existing frozen baseline columns; update current columns rather than rewriting history.

### Medium — status wording implies deployed bridge before final review/merge

Path: docs/specs/master-goal-1642-status.md.

“Slice5 existing bridge/recovery implementation is now active” is ambiguous while parent reports repair review and main integration still pending. The document also labels the remote foundation head only “after slice1,” without a current tested integration head. Milestone entries are useful but need a single exact scope statement for this merge.

Resolution: use “implemented on PR branch; review/CI/live acceptance pending” until evidence changes. Record final PR head, exact CI run, independent final review, archive verification, remaining blockers and later merged main SHA without calling the Master complete. Keep earlier CI evidence as historical milestones, not final-head evidence.

## Verified strengths and limits

- Production Champion APIs remain fail-closed. Sandbox contexts are allocated isolated ephemeral roots and cannot be selected by ordinary evidence JSON/CLI. Promotion validation explicitly reports absent real evidence and authority. This is safe foundation mechanics, not the completed production admission implementation.
- Generic Freeze rejects executed-Champion lineage fields, appends contiguous versions, refuses existing destinations, checks prospective targets and uses a staged/fsynced directory publication. The issuer executes registered fitted models and its sandbox namespace stays separate from original history. All records retain unvalidated official provenance.
- Master orchestration snapshots source inputs and runs operational/model adapters against the snapshot; it does not invoke the prediction issuer. Model REPLAY is separate, hash-bound and immutable. Current model evaluation uses diagnostics and refuses full KPI/confirmation/production claims; missing substantive adapters remain explicit.
- Current evidence audit/search eligibility is incomplete, and formal/count/activity/detection/routes/development/trusted handoff remain incomplete. These are acceptable explicit Foundation-versus-Master distinctions, except that missing eligibility must not create negative labels as noted above.
- Six archived saved-response artifacts are correctly classified as recovered response representations, not original XLSX/TXT or historical availability proof. I independently checked every incoming/raw pair against its recorded SHA-256 and size and checked all six canonical_label_eligible flags are false. Source/event candidate material remains in evidence/recovered review artifacts; no new canonical labels are admitted. This is additive archival, not fabricated biological data.
- Status describes recovered auxiliary OSM bytes without pretending they establish historical feature availability. Current source inventory does not include artifacts/, but current model adapters do not consume those OSM archive bytes. Future Task6a/6c consumers must integrate their hashes/snapshot namespace before use; this is not current scientific feature support.

## Verification performed

Focused operational scoring, model evaluation, Champion registry and prediction-lineage suite:85 tests passed using `PYTHONPATH=tests:src python -m unittest test_master_scoring test_champion_registry test_prediction_lineage test_model_evaluation -q`. Initial package-style invocation had two import errors due to tests importing sibling modules by bare names; rerunning with the tests path fixed collection. This is a test invocation constraint, not a discovered product regression. No full-suite or remote exact-head result is claimed by this review.

CSV audit:112 rows/112 unique IDs; current counts52 PARTIAL,38 IMPLEMENTATION_BLOCKED,12 DONE design/prerequisite items,10 IMPLEMENTED. Those counts are inventory only and do not imply a completion percentage. Archive verification:6 incoming/raw pairs, hashes/bytes and canonical-ineligible flags matched.

## Concrete safe main integration gate

1. Integrate independently reviewed Task6a observation eligibility after Task5 repairs; verify that unsupported units stay UNKNOWN and cannot produce FP. Parent explicitly chose this gate instead of merging the known defect. Refresh the112-row current-state columns through accepted Tasks4/5/6a, preserving baseline/method/master-validation fields. Other concurrently unfinished Tasks6b/c–8 edits remain outside the reviewed merge scope.
2. Complete independent Task5 repair review and parent verification. Keep permissions/secrets unchanged and production activation disabled. Existing no-GitHub-button requirement remains a future live acceptance claim until demonstrated.
3. Parent reports the historical171-file inventory reconciles as162 exact remote blobs,6 pending Task5 code files and3 local Task1 review documents absent remotely (possibly alternate names); recovered raw bytes match. This parent-supplied inventory finding must be reconciled before final publication so missing consumed review documents cannot cause different run identities. Publish final delta by constructing the remote tree on canonical complete baseline/remote PR ancestry. Local reconstructed history/untracked baseline materialization is not a safe push/force-push source. Compare final remote tree against full baseline: existing raw, ORIGINAL/recovered prediction and baseline artifact blobs unchanged; only approved added archive paths and scoped code/docs/tests/workflows differ. Verify no baseline files silently disappear and no whole run snapshots/unrelated untracked material enter PR.
4. Verify final PR head SHA and exact-head CI after the last code/docs change, required independent reviews, no unresolved serious findings and no unexpected paths. Earlier green CI is insufficient. Merge only the reviewed exact head through normal PR controls; no force push/main write bypass.
5. After merge inspect actual main CI and invoke the existing bridge once under the owner authorization, then a duplicate/fresh-runner case within Task5's tested scope. Expect authentic BLOCKED/PARTIAL outcomes and all stage contracts, not scientific PASS. Check authoritative current result identity and artifacts; compare all preexisting protected hashes again.
6. Record foundation merge and live evidence on the canonical goal, leave Master open and preserve Tasks6a/b/c,7,8 as concrete remaining implementation/evidence milestones. No synthetic production or retrospective prediction rewrite is permissible to make acceptance green.

The remaining lack of real learning universe/complete outcomes/untouched cross-year confirmation does not prevent a safe foundation PR. It prevents scientific validation and production promotion. Missing implementation must continue to be named separately from that data insufficiency.
