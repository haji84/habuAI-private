# PR #45 Windows sidecar-path repair (2026-10-25)

- Lane: bounded inherited-PR integrity repair; Master Goal: haji84/AI- Issue #1642.
- Existing PR: https://github.com/haji84/habuAI-private/pull/45 (Draft/Open).
- PR base HEAD: `706470fd69c5e7da1371eb768782d1a9cc7da8cb`.
- Existing remote branch: `fix/p0-pdca-freeze-integrity-20261021`; unchanged at local verification.
- Repair branch: `codex/pr45-sidecar-path-20261025`.
- Current main rules: `c39e6d86489348a925217460c3c98709f513c613` AGENTS/handoff; current immutability and science/authority gates retained.
- Owned paths: `src/pdca_pipeline.py`, `tests/test_p0_pdca_freeze_integrity.py`, this review record.

## Reproduction and smallest change

An independent temporary-file probe on the inherited head used identical prediction bytes and a corrupt sidecar. A slash `_path` returned `FAIL/MISMATCH`, but the equivalent backslash `_path` returned `PASS/NOT_CHECKED`. The native Windows loader emits the latter representation.

The verifier now checks that `_path` is a string and normalizes only backslash separators for comparison with its independently constructed canonical ORIGINAL path. Filesystem reads still use the canonical path and unchanged `safe_path`, never the supplied `_path`. No path resolution, traversal collapsing, symlink following, hash normalization or byte normalization was added.

The regression fixture is a controlled temporary record with a fixed independent digest `1371f25b0429307ebd7fe9cc039c469b8c3b6369fa96b9a5b2593d235a8dea3f`. It is not an issued prediction. Existing `freeze_prediction` import moved into its original test class setup so verifier-only regressions can run without the Linux Freeze writer; the seven original tests are retained and still execute normally where the writer is supported.

## Executed verification

Environment: Windows, Python 3.12.14. No dependencies, locking implementations, permissions or CI settings were changed.

| Check | Actual result |
| --- | --- |
| Baseline full target before test edits | 1 module-import error: missing `fcntl` |
| New path regressions before production fix | RED: 8 tests; 6 assertion failures from backslash/native-path bypass, 2 symlink-creation privilege errors |
| New six executable path regressions after fix | GREEN: 6 passed; valid sidecar `MATCH`, missing sidecar `PARTIAL/MISSING`, corrupt sidecar `FAIL/MISMATCH`, changed bytes `FAIL/NONCANONICAL_BYTES`, traversal `FAIL/INVALID`, native loader cannot bypass |
| Full target after fix | 15 tests; 6 passed, 9 errors: 7 missing `fcntl`, 2 Windows symlink privilege errors; no assertion failures |
| Full suite after fix | 215 tests; 123 passed, 92 errors: 89 missing `fcntl`, 1 missing `sklearn`, 2 Windows symlink privilege errors; no assertion failures |
| `git diff --check` | Passed |
| Protected-path diff | No Raw/ORIGINAL/recovered-original/report/source receipt/requirements/workflow/permission edits |
| Remote HEAD check | Still the assigned PR base HEAD |

Full target command (requires Linux Freeze support and symlink support for a complete PASS):

```text
python -X utf8 -m unittest discover -s tests -p test_p0_pdca_freeze_integrity.py -v
```

Locally executable regression subset, run in addition to the full target and suite:

```text
python -X utf8 -m unittest discover -s tests -p test_p0_pdca_freeze_integrity.py -k test_valid_sidecar_is_checked -k test_missing_sidecar_is_partial -k test_corrupt_sidecar_fails -k test_noncanonical_record_bytes_fail -k test_loader_native_path -k test_canonical_night_traversal -v
```

Full-suite command: `python -X utf8 -m unittest discover -s tests -v`. Symlink checks were not skipped, and `fcntl` was not mocked. Local symlink behavior is `NOT_EXECUTED_ENVIRONMENT_BLOCKED` because creation failed with WinError 1314. Both symlink regression cases remain for Ubuntu verification. Full failing names are recorded below.

## Integration and authority

Read-only `git merge-tree` analysis of inherited PR HEAD against main `c39e6d86489348a925217460c3c98709f513c613`, merge base `27f4832a23f0a3826ce96b87afb4f2f1c58aa936`, reported a clean textual composition without conflict markers. GitHub metadata also reported `mergeable=true`. This does not prove final-head CI, independent review or semantic integration. No merge/rebase was performed.

- Source SHA/count/cutoff: controlled temporary fixture only; no new real observation source, label, forecast cutoff or scientific target.
- Eligibility counts: unchanged; no observational rows admitted or relabelled.
- Scientific status: `NOT_VALIDATED`; no prospective P0, production authority, model accuracy, canonical individual identity or complete capture ledger established.
- CI/review status: final-head Ubuntu verification and independent parent review pending; no CI PASS claimed.
- Merge decision: retain Draft. No push, main integration, shared STATE change or data certification by this worker.
- Next action: coordinator independently reviews final repair SHA, updates the existing PR branch, runs exact-head Ubuntu CI and keeps other audits separate.

## Full-suite failing names

ModuleNotFoundError: No module named 'fcntl': 89 errors.

```text
test_adapter_preserves_failures_and_blocker_classes_without_writes (test_champion_registry.ChampionRegistryTests.test_adapter_preserves_failures_and_blocker_classes_without_writes)
test_artifact_mutation_between_hash_and_decode_is_rejected (test_champion_registry.ChampionRegistryTests.test_artifact_mutation_between_hash_and_decode_is_rejected)
test_candidate_validation_rejects_tampered_model_and_wrong_adapter (test_champion_registry.ChampionRegistryTests.test_candidate_validation_rejects_tampered_model_and_wrong_adapter)
test_cas_concurrency_allows_one_transition (test_champion_registry.ChampionRegistryTests.test_cas_concurrency_allows_one_transition)
test_changed_committed_evidence_or_event_fails_lookup (test_champion_registry.ChampionRegistryTests.test_changed_committed_evidence_or_event_fails_lookup)
test_invalid_probability_state_rejected_even_without_matching_rows (test_champion_registry.ChampionRegistryTests.test_invalid_probability_state_rejected_even_without_matching_rows)
test_orphan_event_before_pointer_commit_never_becomes_active (test_champion_registry.ChampionRegistryTests.test_orphan_event_before_pointer_commit_never_becomes_active)
test_production_activation_ignores_self_declared_trust (test_champion_registry.ChampionRegistryTests.test_production_activation_ignores_self_declared_trust)
test_restricted_summary_and_insufficient_folds_never_pass (test_champion_registry.ChampionRegistryTests.test_restricted_summary_and_insufficient_folds_never_pass)
test_retry_same_transition_is_idempotent_and_code_identity_is_bound (test_champion_registry.ChampionRegistryTests.test_retry_same_transition_is_idempotent_and_code_identity_is_bound)
test_rollback_requires_prior_committed_validated_record (test_champion_registry.ChampionRegistryTests.test_rollback_requires_prior_committed_validated_record)
test_sandbox_context_cannot_be_reused_after_exit (test_champion_registry.ChampionRegistryTests.test_sandbox_context_cannot_be_reused_after_exit)
test_sandbox_lifecycle_preserves_artifact_and_historical_selection (test_champion_registry.ChampionRegistryTests.test_sandbox_lifecycle_preserves_artifact_and_historical_selection)
test_score_only_fitted_values_above_one_remain_valid (test_champion_registry.ChampionRegistryTests.test_score_only_fitted_values_above_one_remain_valid)
test_master_executes_audit_and_preserves_snapshot_inventory (test_evidence_audit.EvidenceAuditTests.test_master_executes_audit_and_preserves_snapshot_inventory)
test_only_exact_osm_archive_is_inventoried_not_bridge_runtime (test_evidence_audit.EvidenceAuditTests.test_only_exact_osm_archive_is_inventoried_not_bridge_runtime)
test_zero_master_budget_never_invokes_auditor (test_evidence_audit.EvidenceAuditTests.test_zero_master_budget_never_invokes_auditor)
test_master_failed_audit_never_calls_model_adapter (test_learning_snapshot.LearningSnapshotTests.test_master_failed_audit_never_calls_model_adapter)
test_master_generated_workspace_is_recoverable_without_input_exemption (test_learning_snapshot.LearningSnapshotTests.test_master_generated_workspace_is_recoverable_without_input_exemption)
test_master_passes_shared_budget_into_builder (test_learning_snapshot.LearningSnapshotTests.test_master_passes_shared_budget_into_builder)
test_authoritative_owner_and_calendar_validation (test_master_e2e.BridgeTests.test_authoritative_owner_and_calendar_validation)
test_bundle_hash_and_checkpoint_hash_corruption_are_rejected (test_master_e2e.BridgeTests.test_bundle_hash_and_checkpoint_hash_corruption_are_rejected)
test_bundle_tamper_traversal_and_size_caps_fail_closed (test_master_e2e.BridgeTests.test_bundle_tamper_traversal_and_size_caps_fail_closed)
test_changed_source_new_issue_changes_run_but_old_receipt_stays_pinned (test_master_e2e.BridgeTests.test_changed_source_new_issue_changes_run_but_old_receipt_stays_pinned)
test_checkpoint_callback_persists_before_hard_exit_and_fresh_restore (test_master_e2e.BridgeTests.test_checkpoint_callback_persists_before_hard_exit_and_fresh_restore)
test_checkpoint_publication_limit_retains_specific_blocker (test_master_e2e.BridgeTests.test_checkpoint_publication_limit_retains_specific_blocker)
test_compact_bundle_restores_fresh_workdir_and_valid_exit_two (test_master_e2e.BridgeTests.test_compact_bundle_restores_fresh_workdir_and_valid_exit_two)
test_corrupt_receipt_is_audited_without_starving_later_command (test_master_e2e.BridgeTests.test_corrupt_receipt_is_audited_without_starving_later_command)
test_crash_cannot_reuse_stale_pass (test_master_e2e.BridgeTests.test_crash_cannot_reuse_stale_pass)
test_discovery_only_suppresses_verified_durable_handled_receipt (test_master_e2e.BridgeTests.test_discovery_only_suppresses_verified_durable_handled_receipt)
test_discovery_retries_do_not_starve_later_commands (test_master_e2e.BridgeTests.test_discovery_retries_do_not_starve_later_commands)
test_expired_lost_attempt_reservation_is_shared_across_issue_ids (test_master_e2e.BridgeTests.test_expired_lost_attempt_reservation_is_shared_across_issue_ids)
test_fixed_bridge_budget_cannot_be_reset_by_new_attempt (test_master_e2e.BridgeTests.test_fixed_bridge_budget_cannot_be_reset_by_new_attempt)
test_handled_receipt_cannot_override_verified_scientific_result (test_master_e2e.BridgeTests.test_handled_receipt_cannot_override_verified_scientific_result)
test_identity_ignores_kernel_and_incidental_packages (test_master_e2e.BridgeTests.test_identity_ignores_kernel_and_incidental_packages)
test_new_issue_cannot_advertise_mixed_completed_shared_run (test_master_e2e.BridgeTests.test_new_issue_cannot_advertise_mixed_completed_shared_run)
test_nonobject_and_missing_receipts_leave_healthy_command_discoverable (test_master_e2e.BridgeTests.test_nonobject_and_missing_receipts_leave_healthy_command_discoverable)
test_publication_refuses_mixed_report_tree_without_discarding_it (test_master_e2e.BridgeTests.test_publication_refuses_mixed_report_tree_without_discarding_it)
test_publication_time_cannot_extend_reserved_deadline (test_master_e2e.BridgeTests.test_publication_time_cannot_extend_reserved_deadline)
test_recovery_never_imports_supplemental_source_code (test_master_e2e.BridgeTests.test_recovery_never_imports_supplemental_source_code)
test_report_blob_size_is_checked_before_materialization (test_master_e2e.BridgeTests.test_report_blob_size_is_checked_before_materialization)
test_restore_requires_complete_inventory_and_result_binding (test_master_e2e.BridgeTests.test_restore_requires_complete_inventory_and_result_binding)
test_sandbox_lifecycle_and_full_master_keep_production_blocked (test_master_e2e.BridgeTests.test_sandbox_lifecycle_and_full_master_keep_production_blocked)
test_scientific_dependency_change_creates_new_run_identity (test_master_e2e.BridgeTests.test_scientific_dependency_change_creates_new_run_identity)
test_skeletal_handled_receipt_does_not_hide_command (test_master_e2e.BridgeTests.test_skeletal_handled_receipt_does_not_hide_command)
test_stale_processing_label_does_not_hide_unfinished_command (test_master_e2e.BridgeTests.test_stale_processing_label_does_not_hide_unfinished_command)
test_transport_cas_and_explicit_paths_leave_worktree_untouched (test_master_e2e.BridgeTests.test_transport_cas_and_explicit_paths_leave_worktree_untouched)
test_transport_enforces_caps_for_receipts_too (test_master_e2e.BridgeTests.test_transport_enforces_caps_for_receipts_too)
test_two_commands_converge_and_partial_publication_recovers (test_master_e2e.BridgeTests.test_two_commands_converge_and_partial_publication_recovers)
test_unconsumed_source_change_can_share_run_without_mixed_report_tree (test_master_e2e.BridgeTests.test_unconsumed_source_change_can_share_run_without_mixed_report_tree)
test_workflows_share_executor_without_permission_changes (test_master_e2e.BridgeTests.test_workflows_share_executor_without_permission_changes)
test_budget_exhaustion_has_all_stages_and_retry_conditions (test_master_orchestrator.MasterTests.test_budget_exhaustion_has_all_stages_and_retry_conditions)
test_budget_retry_requires_larger_limit_and_preserves_ledger (test_master_orchestrator.MasterTests.test_budget_retry_requires_larger_limit_and_preserves_ledger)
test_cli_uses_master_and_reports_missing_implementations (test_master_orchestrator.MasterTests.test_cli_uses_master_and_reports_missing_implementations)
test_code_policy_and_champion_identity_changes_invalidate_previous_run (test_master_orchestrator.MasterTests.test_code_policy_and_champion_identity_changes_invalidate_previous_run)
test_concurrent_cli_commands_share_one_verified_run (test_master_orchestrator.MasterTests.test_concurrent_cli_commands_share_one_verified_run)
test_contradictory_operational_pass_cannot_validate_failed_child (test_master_orchestrator.MasterTests.test_contradictory_operational_pass_cannot_validate_failed_child)
test_corrupt_checkpoint_rejected (test_master_orchestrator.MasterTests.test_corrupt_checkpoint_rejected)
test_corrupt_stage_output_rejected_not_reused (test_master_orchestrator.MasterTests.test_corrupt_stage_output_rejected_not_reused)
test_duplicate_reuses_verified_run_and_input_changes_make_new_run (test_master_orchestrator.MasterTests.test_duplicate_reuses_verified_run_and_input_changes_make_new_run)
test_final_manifest_references_an_existing_verified_checkpoint (test_master_orchestrator.MasterTests.test_final_manifest_references_an_existing_verified_checkpoint)
test_generated_artifact_validation_failure_replaces_stale_pass (test_master_orchestrator.MasterTests.test_generated_artifact_validation_failure_replaces_stale_pass)
test_hard_interruption_charges_inflight_time_before_resuming (test_master_orchestrator.MasterTests.test_hard_interruption_charges_inflight_time_before_resuming)
test_independent_model_adapter_receives_snapshot_and_generated_replay_survives (test_master_orchestrator.MasterTests.test_independent_model_adapter_receives_snapshot_and_generated_replay_survives)
test_interrupted_run_rejects_tampered_completed_stage_artifact (test_master_orchestrator.MasterTests.test_interrupted_run_rejects_tampered_completed_stage_artifact)
test_interrupted_run_rejects_uncommitted_new_replay_artifact (test_master_orchestrator.MasterTests.test_interrupted_run_rejects_uncommitted_new_replay_artifact)
test_interrupted_stage_resumes_and_preserves_elapsed_budget (test_master_orchestrator.MasterTests.test_interrupted_stage_resumes_and_preserves_elapsed_budget)
test_interruption_persists_fail_and_budget_ledger (test_master_orchestrator.MasterTests.test_interruption_persists_fail_and_budget_ledger)
test_malformed_adapter_blockers_become_fail_not_exception (test_master_orchestrator.MasterTests.test_malformed_adapter_blockers_become_fail_not_exception)
test_malformed_operational_blockers_replace_stale_pass (test_master_orchestrator.MasterTests.test_malformed_operational_blockers_replace_stale_pass)
test_midrun_learning_mutation_fails_even_with_snapshot (test_master_orchestrator.MasterTests.test_midrun_learning_mutation_fails_even_with_snapshot)
test_missing_evidence_returns_every_stage_and_honest_blockers (test_master_orchestrator.MasterTests.test_missing_evidence_returns_every_stage_and_honest_blockers)
test_missing_operational_stage_structure_fails (test_master_orchestrator.MasterTests.test_missing_operational_stage_structure_fails)
test_operational_exception_still_attempts_independent_research (test_master_orchestrator.MasterTests.test_operational_exception_still_attempts_independent_research)
test_original_and_raw_bytes_preserved (test_master_orchestrator.MasterTests.test_original_and_raw_bytes_preserved)
test_paths_cannot_escape_and_symlink_inputs_rejected (test_master_orchestrator.MasterTests.test_paths_cannot_escape_and_symlink_inputs_rejected)
test_provenance_and_model_specs_are_snapshotted_and_identity_bound (test_master_orchestrator.MasterTests.test_provenance_and_model_specs_are_snapshotted_and_identity_bound)
test_tampered_generated_operational_artifact_invalidates_resume (test_master_orchestrator.MasterTests.test_tampered_generated_operational_artifact_invalidates_resume)
test_master_scoring (unittest.loader._FailedTest.test_master_scoring)
test_format_only_prediction_mutation_is_detected (test_p0_pdca_freeze_integrity.P0ToPDCAIntegrityTests.test_format_only_prediction_mutation_is_detected)
test_frozen_p0_to_gpx_capture_pdca_is_diagnostic_not_official (test_p0_pdca_freeze_integrity.P0ToPDCAIntegrityTests.test_frozen_p0_to_gpx_capture_pdca_is_diagnostic_not_official)
test_missing_sidecar_stays_diagnostic_not_official (test_p0_pdca_freeze_integrity.P0ToPDCAIntegrityTests.test_missing_sidecar_stays_diagnostic_not_official)
test_pdca_aborts_before_reading_observations_on_corrupt_frozen_p0 (test_p0_pdca_freeze_integrity.P0ToPDCAIntegrityTests.test_pdca_aborts_before_reading_observations_on_corrupt_frozen_p0)
test_real_freeze_bytes_and_sha_sidecar_agree (test_p0_pdca_freeze_integrity.P0ToPDCAIntegrityTests.test_real_freeze_bytes_and_sha_sidecar_agree)
test_sidecar_corruption_is_fail_not_a_missing_provenance_warning (test_p0_pdca_freeze_integrity.P0ToPDCAIntegrityTests.test_sidecar_corruption_is_fail_not_a_missing_provenance_warning)
test_symlinked_sidecar_is_rejected (test_p0_pdca_freeze_integrity.P0ToPDCAIntegrityTests.test_symlinked_sidecar_is_rejected)
test_pdca_e2e (unittest.loader._FailedTest.test_pdca_e2e)
test_prediction_lineage (unittest.loader._FailedTest.test_prediction_lineage)
test_run_pdca (unittest.loader._FailedTest.test_run_pdca)
```

ModuleNotFoundError: No module named 'sklearn': 1 errors.

```text
test_legacy_chronological_walkforward (unittest.loader._FailedTest.test_legacy_chronological_walkforward)
```

OSError: [WinError 1314] symlink privilege unavailable: 2 errors.

```text
test_symlinked_record_is_rejected_for_both_path_separators (test_p0_pdca_freeze_integrity.PredictionSidecarPathTests.test_symlinked_record_is_rejected_for_both_path_separators)
test_symlinked_sidecar_is_rejected_for_both_path_separators (test_p0_pdca_freeze_integrity.PredictionSidecarPathTests.test_symlinked_sidecar_is_rejected_for_both_path_separators)
```


## Independent review follow-up: static junction/reparse boundary

The initial separator repair was committed as `b4baf12726418b4f45c29c6332387b72d0344845` and pushed by the coordinator. Independent V review then reproduced a Windows junction bypass: an ORIGINAL P0 directory redirected to a sibling directory outside the workspace could return `PASS/MATCH`. Windows junctions report `is_junction=True` and `is_symlink=False`, so the previous shared `safe_path` alone did not reject them. This follow-up supersedes the initial verification counts above for the final repair head.

The bounded local `_prediction_path` helper retains `safe_path`, rejects symlink/junction/reparse attributes for every existing component including root ancestors, and verifies resolved containment. Both sidecar and prediction-record verification use it. The loader also checks the prediction base, each candidate version directory, and each record before reading JSON. No G0 module dependency or shared `master_contracts` edit was introduced.

A rejected loader path now returns `overall_status=FAIL` with `load_frozen_predictions=FAIL`, without observation reads or scoring. It does not write a failure report through a potentially unsafe root. Normal missing-sidecar `PARTIAL`, corrupt-sidecar `FAIL`, canonical-byte mismatch `FAIL`, and slash/backslash equivalence remain unchanged. This is a static filesystem-boundary check; it does not claim protection against concurrent hostile path replacement.

### Actual Windows junction TDD

- RED on the separator-only repair: five new tests, 17 assertion failures. This included junctions at root, predictions, original, night and P0; an ancestor of root; and a target contained inside root.
- GREEN after the local guard: all five new tests passed with real Windows junctions. Verifier rejects with `FAIL/INVALID`; loader rejects external invalid JSON by path validation before JSON decoding; pipeline returns load `FAIL` without score or report writes.
- Each fixture lives inside a freshly resolved temporary work directory. Link and resolved target are checked to remain inside that directory before `os.rmdir(junction)` removes only the junction. A target sentinel is checked afterwards. Recursive temporary cleanup runs after the link is gone; no external target directory is removed through a live junction.
- Junction-specific tests run on Windows and are explicitly platform-limited on Linux. Existing real symlink tests remain for Linux; Windows file-symlink creation still fails with WinError 1314 and is reported rather than hidden.

```text
python -X utf8 -m unittest discover -s tests -p test_p0_pdca_freeze_integrity.py -k junction -v
```

### Final local verification after the junction repair

| Check | Actual result |
| --- | --- |
| Full sidecar target | 20 tests: 11 passed, 9 environment errors (7 missing fcntl, 2 symlink privilege); zero assertion failures |
| Full repository suite | 220 tests: 128 passed, 92 environment errors (89 missing fcntl, 1 missing sklearn, 2 symlink privilege); zero assertion failures |
| Previous versus final error-name inventory | The same 92 names and error categories listed in the appendix above; no new error type |
| Protected-path diff | No Raw, ORIGINAL, recovered-original, existing reports, source receipts, requirements, workflows, permissions or STATE change |
| Remote before follow-up commit | Existing PR branch remained at b4baf12726418b4f45c29c6332387b72d0344845 |

The coordinator must independently review this additional commit and rerun Ubuntu CI at its exact final HEAD. A previous-head CI result cannot certify the junction repair. PR #45 remains Draft; no main merge, data admission, scientific validation or production authority is granted here.

## Independent final review and coordinator integration

V independently reran11 executable path/junction tests PASS and the original
real-junction counterexample now fails before loading/scoring/report writes.
The nominal GPX/capture synthetic pipeline still has match=1/formal=SCORED while
strict_official=false, scientific NOT_VALIDATED and NEED_MORE_DATA; bytes stayed
unchanged. This is synthetic validation only. Local source SHA-256 is
`4f3204fd704b6cfd7df1f199d29dbea55057eb546cd2b9c5aef1f4d5221a22cc`.
Parent independently reran5 native Windows junction tests PASS.

The source was cleanly reconciled with main60e27f20. A new immutable cycle02
binds63 current source refs and advances only the current-cycle pointer; old
cycles/policy are preserved. Native Git-index snapshot CLI: CONTRACT_VALIDATED,
fit/production=false. Exact final-head Ubuntu CI remains required before merge.

Separate known blocker: master_orchestrator inventory/snapshot precedes this API
and still uses generic safe_path/rglob, which the independent reviewer showed
can traverse a Windows junction. This local P0 repair does not establish whole-
master Windows reparse containment; full run_master was not executed on Windows
because fcntl is unavailable. No overall Windows boundary-complete claim.

Independent V final coordinator review also verified the new63ref cycle against
Git index bytes and snapshot CLI, pointer SHA, protected-path invariance and
truthful zero-fit/G0/master-inventory blockers. Result: CHECKPOINT_REVIEW_PASS.
