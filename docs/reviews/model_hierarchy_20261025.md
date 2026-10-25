# HB-B1 pure hierarchical ranking implementation, 2026-10-25

Status: software candidate only; science **NOT_VALIDATED**, production authority
false. No actual source-qualified dataset was fitted and no real performance was
measured. All numerical evidence below uses explicitly fictional, controlled
fixtures in the existing selector/joined-row shapes.

## Scope and dependencies

Lane M2 owns only `src/models/hierarchy_shrinkage.py`,
`tests/test_hierarchy_shrinkage.py` and this review. Base is `1bb22b7`.
The separately owned shared selection gate was consumed by cherry-picking
`48d081e0403515ecee9a65fd20679a6157c0c0f1`,
`f31ff6a65ae9f9381805e6b90f948c9e58b93129`, and
`2faf5f81102d3e17c06bfd72dc793d4636aef1a8` (local commits `d33a6d0`,
`0b83b49`, `8f76221`). Its actual PR46 envelope was read from inherited source commit
`179c45b9f58cd46aec8a97a127db713e80540229`; no alternate observation schema or
raw parser was introduced. The repaired upstream selector remains responsible
for real evidence qualification and per-row source/audit readiness.

The APIs are `fit_hierarchy(selection)` and
`rank_hierarchy(model, rows, *, cutoff_time, universe_sha256)`. A valid
insufficient/single-class selection returns `NEED_MORE_DATA`, `model=None` and
the real selection counts/blockers. Malformed data, unknown labels, duplicate
units, changed hashes and invalid future inputs raise `ValueError`.

## Fixed algorithm and geometry

This candidate is a Beta-Bernoulli empirical Bayes hierarchy, rather than a copy
of the existing feature logistic/prospective inference implementation. Global
mean is `(positives + 1)/(units + 2)` from Beta(1,1). Each successive node uses
`(node_positives + 4 * parent_mean)/(node_units + 4)` at 1000m, 500m, 250m,
100m, then the JST 10-minute clock slot. An unseen node inherits its parent.
Strength 4, the global prior and the recipe are fixed, serialized and hashed.
There is no hyperparameter tuning, MCMC, neighbor smoothing or calibration.

The selector retains integer EPSG:32652 100m cells, not original projected
points. Physical representative coordinates are `(cell_x*100, cell_y*100)`;
every spatial size independently uses floor of those coordinates divided by
that size. In particular, 250m is never approximated by integer division of a
100m cell index. Statistics are keyed by complete ancestor paths.

Both model and prediction explicitly disclose
`CELL_ORIGIN_PROXY_NOT_POINT_GEOMETRY`. A 100m cell can cross a 250m boundary,
so true point membership at 250m cannot be established from this selector.
The origin is neither a fabricated observation point nor a proven road zone.
Even when a future row contains a true projected point, scoring deliberately
uses its normalized cell origin to match the training representation.

Time is a cyclic category `((JST hour*60 + minute)//10) % 144` shared across
days. 23:50 is slot 143 and 00:00 is slot 0; there is no ordinal distance or
extra adjacent-slot smoothing. Operational nights retain the existing 07:00
JST boundary and strict availability/cutoff checks in the shared gate.

## Outputs and limitations

Every supplied future joined row, including unobserved cells and completely
new areas, receives one `unit_scores` row with its original row identity.
All five levels return deterministic global/conditional rank diagnostics.
1km Top10 contains ten unique areas, or all areas if fewer exist. Area scores
are their own hierarchy posterior means; no child-window count inflation,
observed-only universe filter, threshold filter or silent sampling is used.

`universe_sha256` binds the canonical complete *joined row array*. It is
distinct from the upstream Universe source-file SHA. Equal hashes prove bytes
and supplied coverage, not the source's completeness, authenticity or actual
ex-ante availability. The caller must retain the upstream hash/provenance too.
Model JSON binds the selection/corpus hashes, actual accepted training nights,
latest accepted unit timestamp, held-out night, fit cutoff, feature schema,
prior recipe, sufficient statistics and research flags.
Input features are provenance-bound but numerical predictors here are only
location and clock slot. Model/prediction integrity hashes are not signatures
or independent trusted model receipts.

These are observation-conditioned binary owner-capture ranking diagnostics.
Selection bias, effort and detection are not corrected. The implementation
does not compute calibrated ecological presence, independent confirmation,
official Stage1 Recall, formal 100m +/-10-minute targets/KPIs, captures/counts,
large-individual estimates or routes. Output flags remain `NOT_VALIDATED` and
production false. The independent outside-universe event denominator belongs
to the evaluator; this fitter/ranker never receives or trims that ledger.

## TDD and verification

Runtime: bundled Windows Python 3.12, invoked with `-X utf8`. Commands:

```text
python -X utf8 -m unittest discover -s tests -p test_hierarchy_shrinkage.py -v
python -X utf8 -m unittest discover -s tests -p test_research_selection.py -v
python -X utf8 -m unittest discover -s tests -v
git diff --check
```

- Initial RED: 12 failures with `HB-B1 hierarchy implementation is missing`.
- Initial GREEN: all 12 tests through the actual shared gate.
- Capacity RED: all 20,000 valid future rows passed the input gate, then an
  expanded hierarchy artifact incorrectly hit the input JSON byte cap.
  Generated artifacts now use the canonical artifact hash without reusing the
  input cap; no candidate is omitted. The complete 20,000-row output passes.
- A valid 20,000-row training selection produces a serializable, reloadable
  model; no fit subsampling occurs.
- Independent V review reproduced acceptance of rehashed invalid model
  metadata. Two regression tests reproduced 10 failures (unregistered family,
  confirmation qualification, same-night fit cutoff, invalid corpus SHA,
  extra authority field, invalid/bool/insufficient night counts, and
  consistently rehashed single-class parameters). Model reload now requires
  the exact root schema, fixed family/qualification, valid lineage/feature
  schema, cutoff before held-out night 07:00, typed/count-consistent evidence,
  >=3 nights and >=2 units of each class, in addition to parameter partitions.
- Follow-up V temporal probe: a rehashed 1900 fit cutoff was inconsistent with
  the October accepted rows. Three cutoff cases (1900, one second before the
  latest observation, equality) reproduced RED. The model now retains sorted
  unique accepted `training_nights` and `training_window_start_max`; reload
  checks actual night count, prior-night identities, strict latest-window/fit
  order, alignment and 07:00 operational-night consistency.
- Targeted M2: **18 tests PASS**, 8.465 seconds after the temporal repair.
  Capacity fixtures use in-domain two-dimensional cells and remain capped at
  the original 20,000; no load-test expansion was introduced.
- Shared gate: **25 tests PASS** on consumed dependency versions.
- Six-unit hand-check: global/1km/500m=1/2; positive 250m=5/7;
  100m=41/49; observed slot=311/343. New slots/cells/areas inherit the
  appropriate prior. The 250m boundary and UTC/JST midnight are checked.
- Full prospective fixture: all 14 rows in 13 areas retained; exactly 10
  unique 1km areas returned. No measured accuracy claim follows from this.
- Syntax compilation and `git diff --check` pass. Raw, ORIGINAL, shared state,
  G0 frozen manifests and production code are not changed by M2.

First full-suite run after the capacity repair: 363 tests, one failure and
105 errors in 19.540 seconds. The model metadata repair full run had 365
tests, one failure and 105 errors in 17.481 seconds. These are Windows/source-checkout blockers;
the failure inventory from the final-code full-suite run is recorded below.
Full Linux exact-head CI and post-integration checks remain the coordinator's
responsibility. No Windows check is bypassed or weakened here.

Final implementation source-byte SHA-256 (LF file reviewed locally):
`85cb9beddc6128522a35e45f7695976781bd01632adce4e6415a429450131b71`.
Independent V follow-up review of this temporal repair is pending; no final
review or CI PASS is claimed by this lane report.


## Final-code Windows full-suite failure inventory

```text

----------------------------------------------------------------------
Ran 370 tests in 33.322s

FAILED (failures=1, errors=105)
```

Every failing test/class from this execution is listed below. No failure is omitted.

- `setUpClass (test_aug31_road_search_candidates.RealAug31RoadEvidenceTests)` — audit_aug31_road_search_candidates.RoadDiagnosticError: Aug31 original GPX SHA mismatch

- `setUpClass (test_august_75_fauna_motion_review.RealSeventyFiveFaunaPacketAdjudication)` — audit_august_fauna_sighting_context.SightingEvidenceError: Aug native Library TXT exact source no longer matches

- `test_forged_positive_in_gps_input_never_promotes (test_august_evidence_review_queue.AugustEvidenceReviewQueueTests.test_forged_positive_in_gps_input_never_promotes)` — ValueError: GPX digest mismatch: 2026-08-12

- `test_real_august_12_nights_remain_unknown (test_august_evidence_review_queue.AugustEvidenceReviewQueueTests.test_real_august_12_nights_remain_unknown)` — ValueError: GPX digest mismatch: 2026-08-12

- `setUpClass (test_august_fauna_sighting_context.RealAugustFaunaEvidenceTests)` — audit_august_fauna_sighting_context.SightingEvidenceError: Aug native Library TXT exact source no longer matches

- `test_exact_raw_native_august_txt_and_all_daily_capture_counts (test_august_native_evidence_packets.NativeCaptureByteSourceTests.test_exact_raw_native_august_txt_and_all_daily_capture_counts)` — audit_august_native_capture_original.SourceProvenanceError: Library native byte SHA or byte count does not match

- `setUpClass (test_august_native_evidence_packets.RealAugustEvidencePacketsTests)` — audit_august_native_capture_original.SourceProvenanceError: Library native byte SHA or byte count does not match

- `test_real_source_report_remains_candidate_only (test_august_sampled_exposure.SourceContract.test_real_source_report_remains_candidate_only)` — ValueError: GPX digest mismatch: 2026-08-12

- `test_adapter_preserves_failures_and_blocker_classes_without_writes (test_champion_registry.ChampionRegistryTests.test_adapter_preserves_failures_and_blocker_classes_without_writes)` — ModuleNotFoundError: No module named 'fcntl'

- `test_artifact_mutation_between_hash_and_decode_is_rejected (test_champion_registry.ChampionRegistryTests.test_artifact_mutation_between_hash_and_decode_is_rejected)` — ModuleNotFoundError: No module named 'fcntl'

- `test_candidate_validation_rejects_tampered_model_and_wrong_adapter (test_champion_registry.ChampionRegistryTests.test_candidate_validation_rejects_tampered_model_and_wrong_adapter)` — ModuleNotFoundError: No module named 'fcntl'

- `test_cas_concurrency_allows_one_transition (test_champion_registry.ChampionRegistryTests.test_cas_concurrency_allows_one_transition)` — ModuleNotFoundError: No module named 'fcntl'

- `test_changed_committed_evidence_or_event_fails_lookup (test_champion_registry.ChampionRegistryTests.test_changed_committed_evidence_or_event_fails_lookup)` — ModuleNotFoundError: No module named 'fcntl'

- `test_invalid_probability_state_rejected_even_without_matching_rows (test_champion_registry.ChampionRegistryTests.test_invalid_probability_state_rejected_even_without_matching_rows)` — ModuleNotFoundError: No module named 'fcntl'

- `test_orphan_event_before_pointer_commit_never_becomes_active (test_champion_registry.ChampionRegistryTests.test_orphan_event_before_pointer_commit_never_becomes_active)` — ModuleNotFoundError: No module named 'fcntl'

- `test_production_activation_ignores_self_declared_trust (test_champion_registry.ChampionRegistryTests.test_production_activation_ignores_self_declared_trust)` — ModuleNotFoundError: No module named 'fcntl'

- `test_restricted_summary_and_insufficient_folds_never_pass (test_champion_registry.ChampionRegistryTests.test_restricted_summary_and_insufficient_folds_never_pass)` — ModuleNotFoundError: No module named 'fcntl'

- `test_retry_same_transition_is_idempotent_and_code_identity_is_bound (test_champion_registry.ChampionRegistryTests.test_retry_same_transition_is_idempotent_and_code_identity_is_bound)` — ModuleNotFoundError: No module named 'fcntl'

- `test_rollback_requires_prior_committed_validated_record (test_champion_registry.ChampionRegistryTests.test_rollback_requires_prior_committed_validated_record)` — ModuleNotFoundError: No module named 'fcntl'

- `test_sandbox_context_cannot_be_reused_after_exit (test_champion_registry.ChampionRegistryTests.test_sandbox_context_cannot_be_reused_after_exit)` — ModuleNotFoundError: No module named 'fcntl'

- `test_sandbox_lifecycle_preserves_artifact_and_historical_selection (test_champion_registry.ChampionRegistryTests.test_sandbox_lifecycle_preserves_artifact_and_historical_selection)` — ModuleNotFoundError: No module named 'fcntl'

- `test_score_only_fitted_values_above_one_remain_valid (test_champion_registry.ChampionRegistryTests.test_score_only_fitted_values_above_one_remain_valid)` — ModuleNotFoundError: No module named 'fcntl'

- `test_master_executes_audit_and_preserves_snapshot_inventory (test_evidence_audit.EvidenceAuditTests.test_master_executes_audit_and_preserves_snapshot_inventory)` — ModuleNotFoundError: No module named 'fcntl'

- `test_only_exact_osm_archive_is_inventoried_not_bridge_runtime (test_evidence_audit.EvidenceAuditTests.test_only_exact_osm_archive_is_inventoried_not_bridge_runtime)` — ModuleNotFoundError: No module named 'fcntl'

- `test_zero_master_budget_never_invokes_auditor (test_evidence_audit.EvidenceAuditTests.test_zero_master_budget_never_invokes_auditor)` — ModuleNotFoundError: No module named 'fcntl'

- `test_actual_thirteen_file_crosswalk (test_gpx_outcome_source_matrix.MatrixTests.test_actual_thirteen_file_crosswalk)` — build_gpx_outcome_source_matrix.SourceMatrixError: Historical QC SHA differs from repository raw GPX

- `test_master_failed_audit_never_calls_model_adapter (test_learning_snapshot.LearningSnapshotTests.test_master_failed_audit_never_calls_model_adapter)` — ModuleNotFoundError: No module named 'fcntl'

- `test_master_generated_workspace_is_recoverable_without_input_exemption (test_learning_snapshot.LearningSnapshotTests.test_master_generated_workspace_is_recoverable_without_input_exemption)` — ModuleNotFoundError: No module named 'fcntl'

- `test_master_passes_shared_budget_into_builder (test_learning_snapshot.LearningSnapshotTests.test_master_passes_shared_budget_into_builder)` — ModuleNotFoundError: No module named 'fcntl'

- `test_legacy_chronological_walkforward (unittest.loader._FailedTest.test_legacy_chronological_walkforward)` — ModuleNotFoundError: No module named 'sklearn'

- `test_authoritative_owner_and_calendar_validation (test_master_e2e.BridgeTests.test_authoritative_owner_and_calendar_validation)` — ModuleNotFoundError: No module named 'fcntl'

- `test_bundle_hash_and_checkpoint_hash_corruption_are_rejected (test_master_e2e.BridgeTests.test_bundle_hash_and_checkpoint_hash_corruption_are_rejected)` — ModuleNotFoundError: No module named 'fcntl'

- `test_bundle_tamper_traversal_and_size_caps_fail_closed (test_master_e2e.BridgeTests.test_bundle_tamper_traversal_and_size_caps_fail_closed)` — ModuleNotFoundError: No module named 'fcntl'

- `test_changed_source_new_issue_changes_run_but_old_receipt_stays_pinned (test_master_e2e.BridgeTests.test_changed_source_new_issue_changes_run_but_old_receipt_stays_pinned)` — ModuleNotFoundError: No module named 'fcntl'

- `test_checkpoint_callback_persists_before_hard_exit_and_fresh_restore (test_master_e2e.BridgeTests.test_checkpoint_callback_persists_before_hard_exit_and_fresh_restore)` — ModuleNotFoundError: No module named 'fcntl'

- `test_checkpoint_publication_limit_retains_specific_blocker (test_master_e2e.BridgeTests.test_checkpoint_publication_limit_retains_specific_blocker)` — ModuleNotFoundError: No module named 'fcntl'

- `test_compact_bundle_restores_fresh_workdir_and_valid_exit_two (test_master_e2e.BridgeTests.test_compact_bundle_restores_fresh_workdir_and_valid_exit_two)` — ModuleNotFoundError: No module named 'fcntl'

- `test_corrupt_receipt_is_audited_without_starving_later_command (test_master_e2e.BridgeTests.test_corrupt_receipt_is_audited_without_starving_later_command)` — ModuleNotFoundError: No module named 'fcntl'

- `test_crash_cannot_reuse_stale_pass (test_master_e2e.BridgeTests.test_crash_cannot_reuse_stale_pass)` — ModuleNotFoundError: No module named 'fcntl'

- `test_discovery_only_suppresses_verified_durable_handled_receipt (test_master_e2e.BridgeTests.test_discovery_only_suppresses_verified_durable_handled_receipt)` — ModuleNotFoundError: No module named 'fcntl'

- `test_discovery_retries_do_not_starve_later_commands (test_master_e2e.BridgeTests.test_discovery_retries_do_not_starve_later_commands)` — ModuleNotFoundError: No module named 'fcntl'

- `test_expired_lost_attempt_reservation_is_shared_across_issue_ids (test_master_e2e.BridgeTests.test_expired_lost_attempt_reservation_is_shared_across_issue_ids)` — ModuleNotFoundError: No module named 'fcntl'

- `test_fixed_bridge_budget_cannot_be_reset_by_new_attempt (test_master_e2e.BridgeTests.test_fixed_bridge_budget_cannot_be_reset_by_new_attempt)` — ModuleNotFoundError: No module named 'fcntl'

- `test_handled_receipt_cannot_override_verified_scientific_result (test_master_e2e.BridgeTests.test_handled_receipt_cannot_override_verified_scientific_result)` — ModuleNotFoundError: No module named 'fcntl'

- `test_identity_ignores_kernel_and_incidental_packages (test_master_e2e.BridgeTests.test_identity_ignores_kernel_and_incidental_packages)` — ModuleNotFoundError: No module named 'fcntl'

- `test_new_issue_cannot_advertise_mixed_completed_shared_run (test_master_e2e.BridgeTests.test_new_issue_cannot_advertise_mixed_completed_shared_run)` — ModuleNotFoundError: No module named 'fcntl'

- `test_nonobject_and_missing_receipts_leave_healthy_command_discoverable (test_master_e2e.BridgeTests.test_nonobject_and_missing_receipts_leave_healthy_command_discoverable)` — ModuleNotFoundError: No module named 'fcntl'

- `test_publication_refuses_mixed_report_tree_without_discarding_it (test_master_e2e.BridgeTests.test_publication_refuses_mixed_report_tree_without_discarding_it)` — ModuleNotFoundError: No module named 'fcntl'

- `test_publication_time_cannot_extend_reserved_deadline (test_master_e2e.BridgeTests.test_publication_time_cannot_extend_reserved_deadline)` — ModuleNotFoundError: No module named 'fcntl'

- `test_recovery_never_imports_supplemental_source_code (test_master_e2e.BridgeTests.test_recovery_never_imports_supplemental_source_code)` — ModuleNotFoundError: No module named 'fcntl'

- `test_report_blob_size_is_checked_before_materialization (test_master_e2e.BridgeTests.test_report_blob_size_is_checked_before_materialization)` — ModuleNotFoundError: No module named 'fcntl'

- `test_restore_requires_complete_inventory_and_result_binding (test_master_e2e.BridgeTests.test_restore_requires_complete_inventory_and_result_binding)` — ModuleNotFoundError: No module named 'fcntl'

- `test_sandbox_lifecycle_and_full_master_keep_production_blocked (test_master_e2e.BridgeTests.test_sandbox_lifecycle_and_full_master_keep_production_blocked)` — ModuleNotFoundError: No module named 'fcntl'

- `test_scientific_dependency_change_creates_new_run_identity (test_master_e2e.BridgeTests.test_scientific_dependency_change_creates_new_run_identity)` — ModuleNotFoundError: No module named 'fcntl'

- `test_skeletal_handled_receipt_does_not_hide_command (test_master_e2e.BridgeTests.test_skeletal_handled_receipt_does_not_hide_command)` — ModuleNotFoundError: No module named 'fcntl'

- `test_stale_processing_label_does_not_hide_unfinished_command (test_master_e2e.BridgeTests.test_stale_processing_label_does_not_hide_unfinished_command)` — ModuleNotFoundError: No module named 'fcntl'

- `test_transport_cas_and_explicit_paths_leave_worktree_untouched (test_master_e2e.BridgeTests.test_transport_cas_and_explicit_paths_leave_worktree_untouched)` — ModuleNotFoundError: No module named 'fcntl'

- `test_transport_enforces_caps_for_receipts_too (test_master_e2e.BridgeTests.test_transport_enforces_caps_for_receipts_too)` — ModuleNotFoundError: No module named 'fcntl'

- `test_two_commands_converge_and_partial_publication_recovers (test_master_e2e.BridgeTests.test_two_commands_converge_and_partial_publication_recovers)` — ModuleNotFoundError: No module named 'fcntl'

- `test_unconsumed_source_change_can_share_run_without_mixed_report_tree (test_master_e2e.BridgeTests.test_unconsumed_source_change_can_share_run_without_mixed_report_tree)` — ModuleNotFoundError: No module named 'fcntl'

- `test_workflows_share_executor_with_read_only_pr_permission (test_master_e2e.BridgeTests.test_workflows_share_executor_with_read_only_pr_permission)` — ModuleNotFoundError: No module named 'fcntl'

- `test_budget_exhaustion_has_all_stages_and_retry_conditions (test_master_orchestrator.MasterTests.test_budget_exhaustion_has_all_stages_and_retry_conditions)` — ModuleNotFoundError: No module named 'fcntl'

- `test_budget_retry_requires_larger_limit_and_preserves_ledger (test_master_orchestrator.MasterTests.test_budget_retry_requires_larger_limit_and_preserves_ledger)` — ModuleNotFoundError: No module named 'fcntl'

- `test_cli_uses_master_and_reports_missing_implementations (test_master_orchestrator.MasterTests.test_cli_uses_master_and_reports_missing_implementations)` — ModuleNotFoundError: No module named 'fcntl'

- `test_code_policy_and_champion_identity_changes_invalidate_previous_run (test_master_orchestrator.MasterTests.test_code_policy_and_champion_identity_changes_invalidate_previous_run)` — ModuleNotFoundError: No module named 'fcntl'

- `test_concurrent_cli_commands_share_one_verified_run (test_master_orchestrator.MasterTests.test_concurrent_cli_commands_share_one_verified_run)` — ModuleNotFoundError: No module named 'fcntl'

- `test_contradictory_operational_pass_cannot_validate_failed_child (test_master_orchestrator.MasterTests.test_contradictory_operational_pass_cannot_validate_failed_child)` — ModuleNotFoundError: No module named 'fcntl'

- `test_corrupt_checkpoint_rejected (test_master_orchestrator.MasterTests.test_corrupt_checkpoint_rejected)` — ModuleNotFoundError: No module named 'fcntl'

- `test_corrupt_stage_output_rejected_not_reused (test_master_orchestrator.MasterTests.test_corrupt_stage_output_rejected_not_reused)` — ModuleNotFoundError: No module named 'fcntl'

- `test_duplicate_reuses_verified_run_and_input_changes_make_new_run (test_master_orchestrator.MasterTests.test_duplicate_reuses_verified_run_and_input_changes_make_new_run)` — ModuleNotFoundError: No module named 'fcntl'

- `test_final_manifest_references_an_existing_verified_checkpoint (test_master_orchestrator.MasterTests.test_final_manifest_references_an_existing_verified_checkpoint)` — ModuleNotFoundError: No module named 'fcntl'

- `test_generated_artifact_validation_failure_replaces_stale_pass (test_master_orchestrator.MasterTests.test_generated_artifact_validation_failure_replaces_stale_pass)` — ModuleNotFoundError: No module named 'fcntl'

- `test_hard_interruption_charges_inflight_time_before_resuming (test_master_orchestrator.MasterTests.test_hard_interruption_charges_inflight_time_before_resuming)` — ModuleNotFoundError: No module named 'fcntl'

- `test_independent_model_adapter_receives_snapshot_and_generated_replay_survives (test_master_orchestrator.MasterTests.test_independent_model_adapter_receives_snapshot_and_generated_replay_survives)` — ModuleNotFoundError: No module named 'fcntl'

- `test_interrupted_run_rejects_tampered_completed_stage_artifact (test_master_orchestrator.MasterTests.test_interrupted_run_rejects_tampered_completed_stage_artifact)` — ModuleNotFoundError: No module named 'fcntl'

- `test_interrupted_run_rejects_uncommitted_new_replay_artifact (test_master_orchestrator.MasterTests.test_interrupted_run_rejects_uncommitted_new_replay_artifact)` — ModuleNotFoundError: No module named 'fcntl'

- `test_interrupted_stage_resumes_and_preserves_elapsed_budget (test_master_orchestrator.MasterTests.test_interrupted_stage_resumes_and_preserves_elapsed_budget)` — ModuleNotFoundError: No module named 'fcntl'

- `test_interruption_persists_fail_and_budget_ledger (test_master_orchestrator.MasterTests.test_interruption_persists_fail_and_budget_ledger)` — ModuleNotFoundError: No module named 'fcntl'

- `test_malformed_adapter_blockers_become_fail_not_exception (test_master_orchestrator.MasterTests.test_malformed_adapter_blockers_become_fail_not_exception)` — ModuleNotFoundError: No module named 'fcntl'

- `test_malformed_operational_blockers_replace_stale_pass (test_master_orchestrator.MasterTests.test_malformed_operational_blockers_replace_stale_pass)` — ModuleNotFoundError: No module named 'fcntl'

- `test_midrun_learning_mutation_fails_even_with_snapshot (test_master_orchestrator.MasterTests.test_midrun_learning_mutation_fails_even_with_snapshot)` — ModuleNotFoundError: No module named 'fcntl'

- `test_missing_evidence_returns_every_stage_and_honest_blockers (test_master_orchestrator.MasterTests.test_missing_evidence_returns_every_stage_and_honest_blockers)` — ModuleNotFoundError: No module named 'fcntl'

- `test_missing_operational_stage_structure_fails (test_master_orchestrator.MasterTests.test_missing_operational_stage_structure_fails)` — ModuleNotFoundError: No module named 'fcntl'

- `test_operational_exception_still_attempts_independent_research (test_master_orchestrator.MasterTests.test_operational_exception_still_attempts_independent_research)` — ModuleNotFoundError: No module named 'fcntl'

- `test_original_and_raw_bytes_preserved (test_master_orchestrator.MasterTests.test_original_and_raw_bytes_preserved)` — ModuleNotFoundError: No module named 'fcntl'

- `test_paths_cannot_escape_and_symlink_inputs_rejected (test_master_orchestrator.MasterTests.test_paths_cannot_escape_and_symlink_inputs_rejected)` — ModuleNotFoundError: No module named 'fcntl'

- `test_provenance_and_model_specs_are_snapshotted_and_identity_bound (test_master_orchestrator.MasterTests.test_provenance_and_model_specs_are_snapshotted_and_identity_bound)` — ModuleNotFoundError: No module named 'fcntl'

- `test_tampered_generated_operational_artifact_invalidates_resume (test_master_orchestrator.MasterTests.test_tampered_generated_operational_artifact_invalidates_resume)` — ModuleNotFoundError: No module named 'fcntl'

- `test_master_scoring (unittest.loader._FailedTest.test_master_scoring)` — ModuleNotFoundError: No module named 'fcntl'

- `test_p0_readiness (unittest.loader._FailedTest.test_p0_readiness)` — ModuleNotFoundError: No module named 'fcntl'

- `test_bash_syntax (test_pages_bootstrap.PagesBootstrapTests.test_bash_syntax)` — FileNotFoundError: [WinError 2] 指定されたファイルが見つかりません。

- `test_followup_needs_production_url (test_pages_bootstrap.PagesBootstrapTests.test_followup_needs_production_url)` — FileNotFoundError: [WinError 2] 指定されたファイルが見つかりません。

- `test_no_access_approval_blocks (test_pages_bootstrap.PagesBootstrapTests.test_no_access_approval_blocks)` — FileNotFoundError: [WinError 2] 指定されたファイルが見つかりません。

- `test_preview_deployments_required_disabled (test_pages_bootstrap.PagesBootstrapTests.test_preview_deployments_required_disabled)` — FileNotFoundError: [WinError 2] 指定されたファイルが見つかりません。

- `test_pdca_actions_pr_handoff (unittest.loader._FailedTest.test_pdca_actions_pr_handoff)` — ModuleNotFoundError: No module named 'fcntl'

- `test_pdca_e2e (unittest.loader._FailedTest.test_pdca_e2e)` — ModuleNotFoundError: No module named 'fcntl'

- `test_prediction_lineage (unittest.loader._FailedTest.test_prediction_lineage)` — ModuleNotFoundError: No module named 'fcntl'

- `test_baseline_disagreement_blocks_more_labels_not_less (test_reconcile_actual_gpx_exposure.RealSourceReconciliationTests.test_baseline_disagreement_blocks_more_labels_not_less)` — reconcile_actual_gpx_exposure.ReconciliationError: GPX raw byte count conflict

- `test_frozen_baseline_count_conflict_still_blocks_any_label (test_reconcile_actual_gpx_exposure.RealSourceReconciliationTests.test_frozen_baseline_count_conflict_still_blocks_any_label)` — reconcile_actual_gpx_exposure.ReconciliationError: GPX raw byte count conflict

- `test_no_automatic_positive_eligibility_even_if_count_equal (test_reconcile_actual_gpx_exposure.RealSourceReconciliationTests.test_no_automatic_positive_eligibility_even_if_count_equal)` — reconcile_actual_gpx_exposure.ReconciliationError: GPX raw byte count conflict

- `test_real_archive_events_and_monthly_conflict_are_quarantined (test_reconcile_actual_gpx_exposure.RealSourceReconciliationTests.test_real_archive_events_and_monthly_conflict_are_quarantined)` — reconcile_actual_gpx_exposure.ReconciliationError: GPX raw byte count conflict

- `setUpClass (test_recover_remaining_august_nights.RemainingAugustTests)` — recover_remaining_august_nights.RecoveryError: Original GPX hash mismatch: 2026-08-13

- `setUpClass (test_recover_two_habu_nights.TwoNightSourceTests)` — recover_two_habu_nights.RecoveryError: Source GPX SHA differs from historical QC registry

- `setUpClass (test_remaining_august_road_candidates.RealRemainingElevenNights)` — audit_remaining_august_road_candidates.RemainingRoadAuditError: GPX SHA mismatch 2026-08-12

- `test_run_pdca (unittest.loader._FailedTest.test_run_pdca)` — ModuleNotFoundError: No module named 'fcntl'

- `test_owner_monthly_count_does_not_override_missing_raw_event_bytes (test_august_native_evidence_packets.NativeCaptureByteSourceTests.test_owner_monthly_count_does_not_override_missing_raw_event_bytes)` — AssertionError: "Owner-confirmed August 47" does not match "Library native byte SHA or byte count does not match"
