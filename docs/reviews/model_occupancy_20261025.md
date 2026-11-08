# Lane M1 implementation evidence, 2026-10-25

Status: **research implementation verified locally; science NOT_VALIDATED;
production unauthorized; exact-head Linux CI and final independent review pending**.
Base: `1bb22b7`. Branch: `codex/occupancy-shrinkage-20261025`.
This is an implementation report, not an independent scientific review.

## Scope and existing interfaces

Added a pure model-only gate in `src/models/research_selection.py` and HB-A0
in `src/models/occupancy_shrinkage.py`. No new parser, corpus builder, pipeline,
external dependency, raw observation or production adapter is introduced.
Historical M0–M3 definitions, parent orchestration, Raw/ORIGINAL and the fixed
G0 cycle manifest were not edited.

The gate consumes the exact serialized output of PR46
`src/training_corpus.py::select_training_rows`, inspected at
`179c45b9f58cd46aec8a97a127db713e80540229` and the repaired
`daf09612f4ffd2cd389b0011cb7c615eb49fef3d`. The repaired selector remains the
necessary upstream source/label/search/complete-outcome/feature-readiness gate.
An old selector output does not acquire new source qualification by passing
this model-only consistency validator.

`validate_selection(selection)` returns a deep copy in the same envelope shape.
It checks the canonical identity of accepted rows, corpus hash, source hash and
receipt maps, heldout night, fit cutoff, feature names and exposed nights against
`selection_sha256`. It also checks JSON safety/size, integer binary labels,
counts/readiness, duplicate row/unit/event identity, 07:00 JST night alignment,
600-second windows, earlier unexposed training nights, cutoff strictness,
feature coverage, finite numbers and nonprivileged qualification. UNKNOWN,
None, boolean labels and target fields as numeric predictors are forbidden.
Valid insufficient and positive-only selections retain NEED_MORE_DATA.

The selector includes *all* source-manifest entries, including sources belonging
only to rejected rows. It discards accepted per-row source bindings and feature,
label and audit readiness. Therefore the pure gate verifies global source hash
and aware-time format/identity, but cannot re-attest per-row source timing or
independent authenticity. A later unused source must not disqualify already
eligible older rows. The coordinator found this compatibility error in the
first helper version; a real-shaped rejected-row/future-source regression
reproduced it and fix `f31ff6a65ae9f9381805e6b90f948c9e58b93129` corrected it.

`validate_future_rows(rows, cutoff_time=..., universe_sha256=...,
heldout_night=..., feature_names=...)` consumes existing PR32 label-free joined
rows with `operational_night`, per-row cutoff, explicit coordinates and complete
feature value/source/time maps. It retains every supplied row and adds integer
`cell_x`/`cell_y`. Existing UTM52N projection is reused for geographic inputs.
Duplicate identifiers/space-time units, future/equal feature availability,
expired or misaligned windows, outcome/extra fields and inconsistent coordinate
representations fail. An explicitly empty forecast feature schema is valid for
the spatial-only recipe. Nonempty supplied features are validated, never filled
with zero or used as outcome-derived predictors.

Independent validation review found that the explicit-cell branch could bypass
the projected-point extent. The three offending easting-cell values 999, 9001
and 100000 failed a new rejection test before repair. Helper fix
`2faf5f81102d3e17c06bfd72dc793d4636aef1a8` restricts forecast cell origins to the
same EPSG:32652 bounds (1000..9000 easting cells, 0..100000 northing cells).
PR46's legacy TRAIN_ONLY cell domain is unchanged.

Here `universe_sha256` means `canonical_digest(joined_rows)`, **not** the byte SHA
of the upstream Universe JSON file. Integration must retain the upstream
`bound.universe_ref.sha256` separately. The supplied digest binds the entire
given row set and prevents altering/subsetting an already bound input. It cannot
prove that a caller supplied a genuine complete road universe or valid source
availability; PR32's upstream validation is still required.

Limits: <=20,000 accepted+rejected training rows, <=32 declared numeric features,
<=120,000 forecast rows, <=16 MiB input JSON and bounded strings/nesting/nodes.
The smaller input-byte limit is not applied to the expanded generated prediction
artifact: its hash includes every generated row using existing canonical
`master_contracts.digest`. Output rows remain bounded by the validated input
count; no candidate is silently truncated to meet a size limit.

## HB-A0 calculation and outputs

`fit_shrinkage(selection)` fixes a global Beta(1,1) prior:

`p_global = (positive_units + 1) / (observed_units + 2)`.

For a 1km area, with fixed strength 4:

`p_area = (area_positive_units + 4 * p_global) / (area_observed_units + 4)`.

Coordinates are EPSG:32652 100m cells; the area ID is
`utm52n_1km_{cell_x//10}_{cell_y//10}`. These are conditional observed-unit owner
capture outcomes, not biological occupancy, encounter abundance or calibrated
island-wide probabilities. Supplied environmental features are validated as
part of the selector contract but are not learned by this location-only prior.
The fixed prior/strength is an engineering recipe, not a measured optimal fit.

The minimum is the existing selector's >=3 prior nights, >=2 positive units and
>=2 independently qualified no-capture units. Insufficient input returns
NEED_MORE_DATA with `model=None`. Malformed input raises ValueError. A successful
fixture calculation returns DEVELOPMENT_FIT_ONLY and a canonical hashed model
binding the fixed configuration, selection/corpus/source identities, fit cutoff,
training nights, class counts and all area parameters. It is always
NOT_VALIDATED with production/official authorization false.

Final independent validation review found that preserving training nights alone
allowed a rehashed model to move its cutoff to 2026-09-03T07:01+09:00, earlier
than its actual final fixture window at 20:00 that same night. The model now
also hashes `training_window_start_max`, derived from the actual accepted rows.
Reload requires an aware aligned 10-minute window in the final training night
and strictly before fit cutoff. Earlier and equal cutoffs, malformed/naive times,
and an inconsistent final night are rejected. Equivalent timezone representations
of the same instant are allowed. The regression reproduced the incorrect
acceptance before repair; this preserves available training-window evidence
without asserting source authenticity or discarded source-readiness evidence.

`predict_shrinkage(model, rows, cutoff_time=..., universe_sha256=...)` revalidates
the serialized model, fixed configuration, support/probability consistency and
fit/heldout boundaries, then scores *every* future supplied row. Unseen areas
use `p_global`. It records the model/input/output digest and target semantics,
and emits no formal targets, P0, count, routes or Champion authority.
Training Brier is explicitly DESCRIPTIVE_ONLY and independent confirmation is
NOT_PERFORMED. Calibration certification and selection-bias correction are absent.

## Actual evidence and remaining gates

**Actual source-qualified model fits: 0. Actual eligible real positives/negatives:
0/0. Real training/heldout nights: none.** All successful calculations above used
explicit small invented fixture arrays, never recovered historical observations
promoted to labels. No performance number or probability calibration was measured
on genuine future-blocked field data.

G0 code review PASS is not G1/G2 source qualification, a valid G3 forecast cohort,
independent G5 confirmation, G6 improvement, trusted G7 activation or genuine G8
prospective P0 evidence. Stage1 Top10 >=90% and 100m +/-10min remain NOT_VALIDATED.
Real fit is blocked until repaired source-bound selections, qualified binary
denominators, full ex-ante universes/features and locked evaluation folds exist.

## Verification on Windows

Runtime: bundled Python 3.12.14, standard-library numeric calculation, no NumPy or
SciPy model dependency added. Reproducibility uses deterministic selector order,
area accumulation and canonical JSON hashes. Model/code identity for a future
scientific run must also bind the reviewed commit and full integration closure;
the implementation-version string alone is not a trusted code attestation.

TDD: the first gate suite had 21 failures for missing implementation, and the
first shrinkage suite had 10 failures for missing implementation. They passed
after implementation. The later-source compatibility regression and additional
model boundary/capacity regressions reproduced their respective errors before
repair. Final targeted results:

| Command suffix after `python -X utf8 -m unittest discover -s tests` | Result |
| --- | --- |
| `-p test_research_selection.py -v` | 25 PASS |
| `-p test_occupancy_shrinkage.py -v` | 16 PASS |
| `-p test_model_evaluation.py -q` | 32 PASS |
| `-p test_prospective_candidate_model.py -q` | 8 PASS |
| `-p test_codex_cycle_contract.py -q` | 19 PASS |
| `-v` | 368 run; 1 failure; 105 errors; exit 1 |
| `git diff --check` | PASS |

Final full-suite log:
`C:\Users\qq113\AppData\Local\Temp\habu-m1-fullsuite-cutoff-repair-20261025.log`.
The full suite was **not** PASS. Categories were 84 missing-fcntl errors,
1 missing-sklearn error, 4 missing-bash/file errors, 16 original-source byte/hash
errors, and one native-byte verification message mismatch. No new model/helper
test failed. Raw checks were preserved; no test or original source was bypassed
to produce a green result. Exact-head Ubuntu CI remains necessary.

The failure/error identities follow, grouped by their final exception, so every
nonpassing test from this actual run remains visible.

### audit_aug31_road_search_candidates.RoadDiagnosticError: Aug31 original GPX SHA mismatch

- `ERROR: setUpClass (test_aug31_road_search_candidates.RealAug31RoadEvidenceTests)`

### audit_august_fauna_sighting_context.SightingEvidenceError: Aug native Library TXT exact source no longer matches

- `ERROR: setUpClass (test_august_75_fauna_motion_review.RealSeventyFiveFaunaPacketAdjudication)`
- `ERROR: setUpClass (test_august_fauna_sighting_context.RealAugustFaunaEvidenceTests)`

### ValueError: GPX digest mismatch: 2026-08-12

- `ERROR: test_forged_positive_in_gps_input_never_promotes (test_august_evidence_review_queue.AugustEvidenceReviewQueueTests.test_forged_positive_in_gps_input_never_promotes)`
- `ERROR: test_real_august_12_nights_remain_unknown (test_august_evidence_review_queue.AugustEvidenceReviewQueueTests.test_real_august_12_nights_remain_unknown)`
- `ERROR: test_real_source_report_remains_candidate_only (test_august_sampled_exposure.SourceContract.test_real_source_report_remains_candidate_only)`

### audit_august_native_capture_original.SourceProvenanceError: Library native byte SHA or byte count does not match

- `ERROR: test_exact_raw_native_august_txt_and_all_daily_capture_counts (test_august_native_evidence_packets.NativeCaptureByteSourceTests.test_exact_raw_native_august_txt_and_all_daily_capture_counts)`
- `ERROR: setUpClass (test_august_native_evidence_packets.RealAugustEvidencePacketsTests)`

### ModuleNotFoundError: No module named 'fcntl'

- `ERROR: test_adapter_preserves_failures_and_blocker_classes_without_writes (test_champion_registry.ChampionRegistryTests.test_adapter_preserves_failures_and_blocker_classes_without_writes)`
- `ERROR: test_artifact_mutation_between_hash_and_decode_is_rejected (test_champion_registry.ChampionRegistryTests.test_artifact_mutation_between_hash_and_decode_is_rejected)`
- `ERROR: test_candidate_validation_rejects_tampered_model_and_wrong_adapter (test_champion_registry.ChampionRegistryTests.test_candidate_validation_rejects_tampered_model_and_wrong_adapter)`
- `ERROR: test_cas_concurrency_allows_one_transition (test_champion_registry.ChampionRegistryTests.test_cas_concurrency_allows_one_transition)`
- `ERROR: test_changed_committed_evidence_or_event_fails_lookup (test_champion_registry.ChampionRegistryTests.test_changed_committed_evidence_or_event_fails_lookup)`
- `ERROR: test_invalid_probability_state_rejected_even_without_matching_rows (test_champion_registry.ChampionRegistryTests.test_invalid_probability_state_rejected_even_without_matching_rows)`
- `ERROR: test_orphan_event_before_pointer_commit_never_becomes_active (test_champion_registry.ChampionRegistryTests.test_orphan_event_before_pointer_commit_never_becomes_active)`
- `ERROR: test_production_activation_ignores_self_declared_trust (test_champion_registry.ChampionRegistryTests.test_production_activation_ignores_self_declared_trust)`
- `ERROR: test_restricted_summary_and_insufficient_folds_never_pass (test_champion_registry.ChampionRegistryTests.test_restricted_summary_and_insufficient_folds_never_pass)`
- `ERROR: test_retry_same_transition_is_idempotent_and_code_identity_is_bound (test_champion_registry.ChampionRegistryTests.test_retry_same_transition_is_idempotent_and_code_identity_is_bound)`
- `ERROR: test_rollback_requires_prior_committed_validated_record (test_champion_registry.ChampionRegistryTests.test_rollback_requires_prior_committed_validated_record)`
- `ERROR: test_sandbox_context_cannot_be_reused_after_exit (test_champion_registry.ChampionRegistryTests.test_sandbox_context_cannot_be_reused_after_exit)`
- `ERROR: test_sandbox_lifecycle_preserves_artifact_and_historical_selection (test_champion_registry.ChampionRegistryTests.test_sandbox_lifecycle_preserves_artifact_and_historical_selection)`
- `ERROR: test_score_only_fitted_values_above_one_remain_valid (test_champion_registry.ChampionRegistryTests.test_score_only_fitted_values_above_one_remain_valid)`
- `ERROR: test_master_executes_audit_and_preserves_snapshot_inventory (test_evidence_audit.EvidenceAuditTests.test_master_executes_audit_and_preserves_snapshot_inventory)`
- `ERROR: test_only_exact_osm_archive_is_inventoried_not_bridge_runtime (test_evidence_audit.EvidenceAuditTests.test_only_exact_osm_archive_is_inventoried_not_bridge_runtime)`
- `ERROR: test_zero_master_budget_never_invokes_auditor (test_evidence_audit.EvidenceAuditTests.test_zero_master_budget_never_invokes_auditor)`
- `ERROR: test_master_failed_audit_never_calls_model_adapter (test_learning_snapshot.LearningSnapshotTests.test_master_failed_audit_never_calls_model_adapter)`
- `ERROR: test_master_generated_workspace_is_recoverable_without_input_exemption (test_learning_snapshot.LearningSnapshotTests.test_master_generated_workspace_is_recoverable_without_input_exemption)`
- `ERROR: test_master_passes_shared_budget_into_builder (test_learning_snapshot.LearningSnapshotTests.test_master_passes_shared_budget_into_builder)`
- `ERROR: test_authoritative_owner_and_calendar_validation (test_master_e2e.BridgeTests.test_authoritative_owner_and_calendar_validation)`
- `ERROR: test_bundle_hash_and_checkpoint_hash_corruption_are_rejected (test_master_e2e.BridgeTests.test_bundle_hash_and_checkpoint_hash_corruption_are_rejected)`
- `ERROR: test_bundle_tamper_traversal_and_size_caps_fail_closed (test_master_e2e.BridgeTests.test_bundle_tamper_traversal_and_size_caps_fail_closed)`
- `ERROR: test_changed_source_new_issue_changes_run_but_old_receipt_stays_pinned (test_master_e2e.BridgeTests.test_changed_source_new_issue_changes_run_but_old_receipt_stays_pinned)`
- `ERROR: test_checkpoint_callback_persists_before_hard_exit_and_fresh_restore (test_master_e2e.BridgeTests.test_checkpoint_callback_persists_before_hard_exit_and_fresh_restore)`
- `ERROR: test_checkpoint_publication_limit_retains_specific_blocker (test_master_e2e.BridgeTests.test_checkpoint_publication_limit_retains_specific_blocker)`
- `ERROR: test_compact_bundle_restores_fresh_workdir_and_valid_exit_two (test_master_e2e.BridgeTests.test_compact_bundle_restores_fresh_workdir_and_valid_exit_two)`
- `ERROR: test_corrupt_receipt_is_audited_without_starving_later_command (test_master_e2e.BridgeTests.test_corrupt_receipt_is_audited_without_starving_later_command)`
- `ERROR: test_crash_cannot_reuse_stale_pass (test_master_e2e.BridgeTests.test_crash_cannot_reuse_stale_pass)`
- `ERROR: test_discovery_only_suppresses_verified_durable_handled_receipt (test_master_e2e.BridgeTests.test_discovery_only_suppresses_verified_durable_handled_receipt)`
- `ERROR: test_discovery_retries_do_not_starve_later_commands (test_master_e2e.BridgeTests.test_discovery_retries_do_not_starve_later_commands)`
- `ERROR: test_expired_lost_attempt_reservation_is_shared_across_issue_ids (test_master_e2e.BridgeTests.test_expired_lost_attempt_reservation_is_shared_across_issue_ids)`
- `ERROR: test_fixed_bridge_budget_cannot_be_reset_by_new_attempt (test_master_e2e.BridgeTests.test_fixed_bridge_budget_cannot_be_reset_by_new_attempt)`
- `ERROR: test_handled_receipt_cannot_override_verified_scientific_result (test_master_e2e.BridgeTests.test_handled_receipt_cannot_override_verified_scientific_result)`
- `ERROR: test_identity_ignores_kernel_and_incidental_packages (test_master_e2e.BridgeTests.test_identity_ignores_kernel_and_incidental_packages)`
- `ERROR: test_new_issue_cannot_advertise_mixed_completed_shared_run (test_master_e2e.BridgeTests.test_new_issue_cannot_advertise_mixed_completed_shared_run)`
- `ERROR: test_nonobject_and_missing_receipts_leave_healthy_command_discoverable (test_master_e2e.BridgeTests.test_nonobject_and_missing_receipts_leave_healthy_command_discoverable)`
- `ERROR: test_publication_refuses_mixed_report_tree_without_discarding_it (test_master_e2e.BridgeTests.test_publication_refuses_mixed_report_tree_without_discarding_it)`
- `ERROR: test_publication_time_cannot_extend_reserved_deadline (test_master_e2e.BridgeTests.test_publication_time_cannot_extend_reserved_deadline)`
- `ERROR: test_recovery_never_imports_supplemental_source_code (test_master_e2e.BridgeTests.test_recovery_never_imports_supplemental_source_code)`
- `ERROR: test_report_blob_size_is_checked_before_materialization (test_master_e2e.BridgeTests.test_report_blob_size_is_checked_before_materialization)`
- `ERROR: test_restore_requires_complete_inventory_and_result_binding (test_master_e2e.BridgeTests.test_restore_requires_complete_inventory_and_result_binding)`
- `ERROR: test_sandbox_lifecycle_and_full_master_keep_production_blocked (test_master_e2e.BridgeTests.test_sandbox_lifecycle_and_full_master_keep_production_blocked)`
- `ERROR: test_scientific_dependency_change_creates_new_run_identity (test_master_e2e.BridgeTests.test_scientific_dependency_change_creates_new_run_identity)`
- `ERROR: test_skeletal_handled_receipt_does_not_hide_command (test_master_e2e.BridgeTests.test_skeletal_handled_receipt_does_not_hide_command)`
- `ERROR: test_stale_processing_label_does_not_hide_unfinished_command (test_master_e2e.BridgeTests.test_stale_processing_label_does_not_hide_unfinished_command)`
- `ERROR: test_transport_cas_and_explicit_paths_leave_worktree_untouched (test_master_e2e.BridgeTests.test_transport_cas_and_explicit_paths_leave_worktree_untouched)`
- `ERROR: test_transport_enforces_caps_for_receipts_too (test_master_e2e.BridgeTests.test_transport_enforces_caps_for_receipts_too)`
- `ERROR: test_two_commands_converge_and_partial_publication_recovers (test_master_e2e.BridgeTests.test_two_commands_converge_and_partial_publication_recovers)`
- `ERROR: test_unconsumed_source_change_can_share_run_without_mixed_report_tree (test_master_e2e.BridgeTests.test_unconsumed_source_change_can_share_run_without_mixed_report_tree)`
- `ERROR: test_workflows_share_executor_with_read_only_pr_permission (test_master_e2e.BridgeTests.test_workflows_share_executor_with_read_only_pr_permission)`
- `ERROR: test_budget_exhaustion_has_all_stages_and_retry_conditions (test_master_orchestrator.MasterTests.test_budget_exhaustion_has_all_stages_and_retry_conditions)`
- `ERROR: test_budget_retry_requires_larger_limit_and_preserves_ledger (test_master_orchestrator.MasterTests.test_budget_retry_requires_larger_limit_and_preserves_ledger)`
- `ERROR: test_cli_uses_master_and_reports_missing_implementations (test_master_orchestrator.MasterTests.test_cli_uses_master_and_reports_missing_implementations)`
- `ERROR: test_code_policy_and_champion_identity_changes_invalidate_previous_run (test_master_orchestrator.MasterTests.test_code_policy_and_champion_identity_changes_invalidate_previous_run)`
- `ERROR: test_concurrent_cli_commands_share_one_verified_run (test_master_orchestrator.MasterTests.test_concurrent_cli_commands_share_one_verified_run)`
- `ERROR: test_contradictory_operational_pass_cannot_validate_failed_child (test_master_orchestrator.MasterTests.test_contradictory_operational_pass_cannot_validate_failed_child)`
- `ERROR: test_corrupt_checkpoint_rejected (test_master_orchestrator.MasterTests.test_corrupt_checkpoint_rejected)`
- `ERROR: test_corrupt_stage_output_rejected_not_reused (test_master_orchestrator.MasterTests.test_corrupt_stage_output_rejected_not_reused)`
- `ERROR: test_duplicate_reuses_verified_run_and_input_changes_make_new_run (test_master_orchestrator.MasterTests.test_duplicate_reuses_verified_run_and_input_changes_make_new_run)`
- `ERROR: test_final_manifest_references_an_existing_verified_checkpoint (test_master_orchestrator.MasterTests.test_final_manifest_references_an_existing_verified_checkpoint)`
- `ERROR: test_generated_artifact_validation_failure_replaces_stale_pass (test_master_orchestrator.MasterTests.test_generated_artifact_validation_failure_replaces_stale_pass)`
- `ERROR: test_hard_interruption_charges_inflight_time_before_resuming (test_master_orchestrator.MasterTests.test_hard_interruption_charges_inflight_time_before_resuming)`
- `ERROR: test_independent_model_adapter_receives_snapshot_and_generated_replay_survives (test_master_orchestrator.MasterTests.test_independent_model_adapter_receives_snapshot_and_generated_replay_survives)`
- `ERROR: test_interrupted_run_rejects_tampered_completed_stage_artifact (test_master_orchestrator.MasterTests.test_interrupted_run_rejects_tampered_completed_stage_artifact)`
- `ERROR: test_interrupted_run_rejects_uncommitted_new_replay_artifact (test_master_orchestrator.MasterTests.test_interrupted_run_rejects_uncommitted_new_replay_artifact)`
- `ERROR: test_interrupted_stage_resumes_and_preserves_elapsed_budget (test_master_orchestrator.MasterTests.test_interrupted_stage_resumes_and_preserves_elapsed_budget)`
- `ERROR: test_interruption_persists_fail_and_budget_ledger (test_master_orchestrator.MasterTests.test_interruption_persists_fail_and_budget_ledger)`
- `ERROR: test_malformed_adapter_blockers_become_fail_not_exception (test_master_orchestrator.MasterTests.test_malformed_adapter_blockers_become_fail_not_exception)`
- `ERROR: test_malformed_operational_blockers_replace_stale_pass (test_master_orchestrator.MasterTests.test_malformed_operational_blockers_replace_stale_pass)`
- `ERROR: test_midrun_learning_mutation_fails_even_with_snapshot (test_master_orchestrator.MasterTests.test_midrun_learning_mutation_fails_even_with_snapshot)`
- `ERROR: test_missing_evidence_returns_every_stage_and_honest_blockers (test_master_orchestrator.MasterTests.test_missing_evidence_returns_every_stage_and_honest_blockers)`
- `ERROR: test_missing_operational_stage_structure_fails (test_master_orchestrator.MasterTests.test_missing_operational_stage_structure_fails)`
- `ERROR: test_operational_exception_still_attempts_independent_research (test_master_orchestrator.MasterTests.test_operational_exception_still_attempts_independent_research)`
- `ERROR: test_original_and_raw_bytes_preserved (test_master_orchestrator.MasterTests.test_original_and_raw_bytes_preserved)`
- `ERROR: test_paths_cannot_escape_and_symlink_inputs_rejected (test_master_orchestrator.MasterTests.test_paths_cannot_escape_and_symlink_inputs_rejected)`
- `ERROR: test_provenance_and_model_specs_are_snapshotted_and_identity_bound (test_master_orchestrator.MasterTests.test_provenance_and_model_specs_are_snapshotted_and_identity_bound)`
- `ERROR: test_tampered_generated_operational_artifact_invalidates_resume (test_master_orchestrator.MasterTests.test_tampered_generated_operational_artifact_invalidates_resume)`
- `ERROR: test_master_scoring (unittest.loader._FailedTest.test_master_scoring)`
- `ERROR: test_p0_readiness (unittest.loader._FailedTest.test_p0_readiness)`
- `ERROR: test_pdca_actions_pr_handoff (unittest.loader._FailedTest.test_pdca_actions_pr_handoff)`
- `ERROR: test_pdca_e2e (unittest.loader._FailedTest.test_pdca_e2e)`
- `ERROR: test_prediction_lineage (unittest.loader._FailedTest.test_prediction_lineage)`
- `ERROR: test_run_pdca (unittest.loader._FailedTest.test_run_pdca)`

### build_gpx_outcome_source_matrix.SourceMatrixError: Historical QC SHA differs from repository raw GPX

- `ERROR: test_actual_thirteen_file_crosswalk (test_gpx_outcome_source_matrix.MatrixTests.test_actual_thirteen_file_crosswalk)`

### ModuleNotFoundError: No module named 'sklearn'

- `ERROR: test_legacy_chronological_walkforward (unittest.loader._FailedTest.test_legacy_chronological_walkforward)`

### FileNotFoundError: [WinError 2] 指定されたファイルが見つかりません。

- `ERROR: test_bash_syntax (test_pages_bootstrap.PagesBootstrapTests.test_bash_syntax)`
- `ERROR: test_followup_needs_production_url (test_pages_bootstrap.PagesBootstrapTests.test_followup_needs_production_url)`
- `ERROR: test_no_access_approval_blocks (test_pages_bootstrap.PagesBootstrapTests.test_no_access_approval_blocks)`
- `ERROR: test_preview_deployments_required_disabled (test_pages_bootstrap.PagesBootstrapTests.test_preview_deployments_required_disabled)`

### reconcile_actual_gpx_exposure.ReconciliationError: GPX raw byte count conflict

- `ERROR: test_baseline_disagreement_blocks_more_labels_not_less (test_reconcile_actual_gpx_exposure.RealSourceReconciliationTests.test_baseline_disagreement_blocks_more_labels_not_less)`
- `ERROR: test_frozen_baseline_count_conflict_still_blocks_any_label (test_reconcile_actual_gpx_exposure.RealSourceReconciliationTests.test_frozen_baseline_count_conflict_still_blocks_any_label)`
- `ERROR: test_no_automatic_positive_eligibility_even_if_count_equal (test_reconcile_actual_gpx_exposure.RealSourceReconciliationTests.test_no_automatic_positive_eligibility_even_if_count_equal)`
- `ERROR: test_real_archive_events_and_monthly_conflict_are_quarantined (test_reconcile_actual_gpx_exposure.RealSourceReconciliationTests.test_real_archive_events_and_monthly_conflict_are_quarantined)`

### recover_remaining_august_nights.RecoveryError: Original GPX hash mismatch: 2026-08-13

- `ERROR: setUpClass (test_recover_remaining_august_nights.RemainingAugustTests)`

### recover_two_habu_nights.RecoveryError: Source GPX SHA differs from historical QC registry

- `ERROR: setUpClass (test_recover_two_habu_nights.TwoNightSourceTests)`

### audit_remaining_august_road_candidates.RemainingRoadAuditError: GPX SHA mismatch 2026-08-12

- `ERROR: setUpClass (test_remaining_august_road_candidates.RealRemainingElevenNights)`

### AssertionError: "Owner-confirmed August 47" does not match "Library native byte SHA or byte count does not match"

- `FAIL: test_owner_monthly_count_does_not_override_missing_raw_event_bytes (test_august_native_evidence_packets.NativeCaptureByteSourceTests.test_owner_monthly_count_does_not_override_missing_raw_event_bytes)`

## Final implementation/test byte hashes

These SHA-256 values bind the new LF source/test bytes verified in this worktree; integration must also bind its actual reviewed Git commit and dependency closure.

- `src/models/research_selection.py`: `915fbe3bb52cbf211c3ed7974ac805c0bb87e70bc0378837544b0081d27dd714`
- `src/models/occupancy_shrinkage.py`: `48443068e2aeaacf7f9a638a604fe72d063aa3891bc1652f713f9e60c7e34c2a`
- `tests/test_research_selection.py`: `293e29f7f86f875e0ba55cdeb53fe53dd0d18b8a7559a020335c4b90ef89818e`
- `tests/test_occupancy_shrinkage.py`: `d6bfb7941fa9c063e9a0421a0b12c9651a7426a2294607529ff74a1abb59d584`
