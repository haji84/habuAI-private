# Feature-aware candidate predictor: research only, never an ORIGINAL P0

This module provides a deterministic empirical feature-aware research baseline. **No real trained production model is claimed** until source-audited multi-night observations, terrain/weather snapshots, review and independent confirmation are provided.

## Model
- `src/prospective_candidate_model.py`: the existing seven-feature, standard-library L2 logistic occurrence routine is retained, with features `temperature_c`, `humidity_pct`, `precipitation_mm`, `slope_deg`, `tpi_m`, `road_length_m` and `wind_cross_road_proxy`.
- `train_candidate(history, *, training_cutoff, holdout_nights=2, training_selection=None)` requires the repaired source-bound TRAIN_ONLY selector's serialized result. Missing, malformed, insufficient or incompatible selections raise `CandidateInputError` prefixed `SOURCE_TRAINING_BLOCKED`. The function uses the validated copy from `models.research_selection.validate_selection`; it does not duplicate the selector or make a new corpus adapter.
- Every history row must match exactly one accepted selection row, and every accepted row must be represented in history. Binding uses operational night, actual numeric 100m cell coordinates, normalized window instant, all seven feature values, and the binary `owner_capture_count > 0` outcome. Selection fit cutoff must equal the requested training cutoff. Rehashing a changed selection cannot bind it to unchanged history.
- GPX passage, speed or an `exposure_proof` string never qualify a negative. The source selector must already require independent active Habu search and complete owner capture-outcome recording for the scope. UNKNOWN cannot enter accepted binary labels. Other species, sightings and roadkill do not become personal captures.
- Existing capture event IDs remain in the selection identity. This occurrence routine never creates individual IDs from counts, does not authenticate individual multiplicity, and counts a positive observation unit once even if its supplied owner count exceeds one.
- History retains its historical forecast/window, feature source SHA, outcome source SHA, count and outcome availability checks. Features must be available **strictly before** the historical forecast cutoff; equality is rejected. Labels must be available strictly before the fit cutoff.
- At least five training nights plus two strictly later **internal development split** nights are required. Both partitions come from the same source-selected corpus. The development Brier is descriptive, not untouched confirmation or strict external Stage1 recall. The optimizer remains fixed at 320 epochs with the existing L2 penalty and step size.
- New fits emit `habu-prospective-candidate-v2`, `development_split_nights`, `development_units`, `development_brier_diagnostic`, `independent_confirmation=NOT_PERFORMED`, and `training_selection_sha256`. New artifacts omit the misleading `untouched_holdout_nights` field. The legacy `holdout_nights` keyword remains accepted for call compatibility. Existing serialized v1 artifacts are not rewritten; diagnostic ranking can still read their numeric state without granting new authority. All model output remains `DIAGNOSTIC_WALK_FORWARD_CANDIDATE_ONLY`.
- Prospective scoring returns ranked 1km area candidates, linked 500m/250m zones and 100m ×10minute candidate probabilities for an explicit future operational night; only known ex-ante source rows qualify.
- Future rows contain exactly the seven predictors plus `operational_night`, `cell_id`, `window_start_jst`, `forecast_cutoff`, `features_available_at`, `weather_source_role`, and `features_source_sha256`. Outcome, exposure and unknown metadata fields are rejected even when null or empty. Feature availability must strictly precede forecast cutoff, and forecast cutoff cannot follow actual issuance.
- Scores are **within a caller-provided candidate road universe** and are not certified to cover off-universe capture events, all legally drivable roads or all observed searches. Therefore the official Stage1 Top10 Recall and formal 100m±10min KPIs are **not computed**. Three fully drivable A/B/C routes are not produced.

## Source boundary and remaining prerequisites

The pure shared gate checks exact envelope structure, internal consistency,
readiness assertions, event uniqueness and selection digest. It does **not**
authenticate source bytes, observation/search claims, source roles or omitted
per-row readiness receipts. Its source metadata are caller assertions, not
trusted attestations. The repaired source-bound selector must run first; source
authentication and the shared four-readiness closure remain separate gates.
Neither a hand-built gate fixture nor a SHA string creates scientific authority.

Base `a331e22e1905f66a598d5ce2c93dbbdc6a090912` has the shared gate but not the
PR46 source selector. The optional dependency test skips **only** when importing
`training_corpus` raises `ModuleNotFoundError` naming that module. If present,
the real selector must execute; transitive import problems, malformed fixtures
and implementation failures propagate as failures. This repair adds no second
selector and does not silently certify a model when that dependency is absent.

## Approved bounded repair and implementation record

Goal: close the old source/leakage entrance while preserving its numerical
routine. Architecture: additive required selection keyword, shared pure gate,
complete history-to-selection binding, and strict forecast-only input boundary.
Tech stack: Python standard library and the existing research gate.

Worktree `legacy-source-gate`, branch
`codex/legacy-source-training-gate-20261025`, exact base
`a331e22e1905f66a598d5ce2c93dbbdc6a090912`. Parent approved the small design
before implementation. Owned files are this specification,
`src/prospective_candidate_model.py` and its existing test file only.

- [x] Confirm clean isolated baseline and existing eight target tests.
- [x] Prove GPX-only training admission, selection/history mismatch, strict
  cutoff equality, outcome contamination and split misdescription with RED tests.
- [x] Apply the smallest source/shared-gate and row-binding changes; retain
  seven predictors, 320 epochs, original penalty/step and five-plus-two split.
- [x] Verify hand-checked numeric regression and v1 diagnostic read compatibility.
- [x] Add actual-byte synthetic corpus/negative-receipt integration that invokes
  the existing PR46 source selector when installed and detects source mutation.
- [ ] Parent: integrate PR46 dependency, create new source freeze, independent
  review and exact-head Linux CI. Raw/ORIGINAL, historical models, receipts,
  predictions, STATE, current-cycle and authority remain outside this repair.

RED evidence: missing selection accepted (one failure); shared-envelope/history
binding (12 assertion failures plus the expected old GPX-only restriction
rejecting a valid selected input); cutoff equality (two failures); future outcome
and nested metadata contamination (10 failures); untouched-split misdescription
(one failure); declared forecast cutoff after issuance (one failure).

The synthetic regression preserves means
`[22.5,85.0,0.2,13.5,-1.5,31.5,0.5]`, coefficients within 1e-12,
development Brier `0.19376964`, and one future score `0.33976141` from the old
routine. These are software regression numbers, not real predictive performance.

## Why there is no real training PASS yet

The main branch still lacks `data/processed/model_learning.json` and a validated merged observed-exposure dataset covering multiple eligible historical nights; the available historical log and GPX records are fragmented. The auxiliary OSM archive has validated bytes and an accessible 100m candidate-cell table but its legal/current road universe status is unresolved. The official GSI DEM for these cells is not yet ingested with spatial coverage and hashes.

Current weather E2E [PR #67](https://github.com/haji84/habuAI-private/pull/67) actually contacted the weather API and saved 2-site future-night source bytes, but these do not substitute for the historical *as-issued* forecasts required to train and fairly evaluate weather sensitivity.

## Production gate remains closed

`src/champion_registry.py` and `scripts/issue_prediction.py` still allow only sandbox test issuance. A candidate model JSON or a positive mock test does not grant trusted production authority. A future P0 must bind actual model, code, weather/terrain/road and source availability hashes, be created before physical search start and frozen without mutation. At 07:00 JST the exploration night boundary resets.

Next milestones in Issue #64: (1) audited actual multi-night learning records, (2) complete ex-ante road universe + real DEM/weather forecast snapshots (3) scientific holdout validation including outside-universe misses, (4) trusted authorized production issuer, (5) first real pre-search ORIGINAL P0 + subsequent ground-truth P0-vs-Pn PDCA.


## Verification results (2026-10-25)

Native Windows CPython 3.12.14:

| Final regression file | Run | PASS | Skip |
| --- | ---: | ---: | ---: |
| `test_prospective_candidate_model.py` | 25 | 24 | 1 (PR46 module absent) |
| `test_research_selection.py` | 26 | 26 | 0 |
| `test_occupancy_shrinkage.py` | 16 | 16 | 0 |
| `test_hierarchy_shrinkage.py` | 18 | 18 | 0 |
| `test_research_model_adapter.py` | 13 | 13 | 0 |
| `test_model_evaluation.py` | 32 | 32 | 0 |
| Total | 130 | 129 | 1 |

Commands: `python -X utf8 -m unittest discover -s tests -p <file> -v`.

A separate read-only cross-tree dependency run put the existing PR46
`features/src` at the end of `sys.path`; this repair's own `src` remained first.
Module `__file__` values confirmed that the candidate came from this branch and
`training_corpus` from features head
`38ddc8f19e54153f58dcbaae1a2a35cd45da6245`. **All 25 candidate tests passed with
zero skips**, including real corpus/source byte hashes, independent negative
receipt structure, selector-to-fit binding and changed-source-byte rejection.
This is an explicit integration probe, not a claim that PR46 is on this base.
The parent must still run the same test in the integrated tree and Linux CI.

Full native discovery was run before the final declared-cutoff-after-issuance
one-condition repair: **509 tests, 114 errors, 1 failure, 5 skips; exit 1**.
There were 395 passing-test lines; setup-class failures make subtraction from
`testsRun` inappropriate. Final focused regressions include the last repair.
No green whole-suite result or Linux result is claimed.

| Observed failure cause | Count |
| --- | ---: |
| Missing Windows `fcntl` | 91 errors |
| Missing `sklearn` | 1 error |
| Native symlink privilege (`WinError 1314`) | 2 errors |
| Missing Bash executable | 4 errors |
| Existing historical source SHA/size checks | 16 errors |
| Owner-count assertion reaches source-byte gate first | 1 failure |

The historical byte failures are the same classes already recorded in prior
main-based Windows audits. The owner-count assertion expected
`Owner-confirmed August 47` but instead encountered
`Library native byte SHA or byte count does not match`. With
`core.autocrlf=true`, historical source checkout bytes can differ from their
native Git blobs. No original source was rewritten to hide those failures.
The five skips are four existing Linux-only master controls and the explicit
PR46 dependency control. Full log: `%TEMP%/legacy-source-gate-full-20261025.log`;
final focused logs: `%TEMP%/legacy-source-gate-final-test_*-20261025.log`.

<details>
<summary>Every failure/error name from the native full run</summary>

```text
ERROR: setUpClass (test_aug31_road_search_candidates.RealAug31RoadEvidenceTests)
ERROR: setUpClass (test_august_75_fauna_motion_review.RealSeventyFiveFaunaPacketAdjudication)
ERROR: test_forged_positive_in_gps_input_never_promotes (test_august_evidence_review_queue.AugustEvidenceReviewQueueTests.test_forged_positive_in_gps_input_never_promotes)
ERROR: test_real_august_12_nights_remain_unknown (test_august_evidence_review_queue.AugustEvidenceReviewQueueTests.test_real_august_12_nights_remain_unknown)
ERROR: setUpClass (test_august_fauna_sighting_context.RealAugustFaunaEvidenceTests)
ERROR: test_exact_raw_native_august_txt_and_all_daily_capture_counts (test_august_native_evidence_packets.NativeCaptureByteSourceTests.test_exact_raw_native_august_txt_and_all_daily_capture_counts)
ERROR: setUpClass (test_august_native_evidence_packets.RealAugustEvidencePacketsTests)
ERROR: test_real_source_report_remains_candidate_only (test_august_sampled_exposure.SourceContract.test_real_source_report_remains_candidate_only)
ERROR: test_adapter_preserves_failures_and_blocker_classes_without_writes (test_champion_registry.ChampionRegistryTests.test_adapter_preserves_failures_and_blocker_classes_without_writes)
ERROR: test_artifact_mutation_between_hash_and_decode_is_rejected (test_champion_registry.ChampionRegistryTests.test_artifact_mutation_between_hash_and_decode_is_rejected)
ERROR: test_candidate_validation_rejects_tampered_model_and_wrong_adapter (test_champion_registry.ChampionRegistryTests.test_candidate_validation_rejects_tampered_model_and_wrong_adapter)
ERROR: test_cas_concurrency_allows_one_transition (test_champion_registry.ChampionRegistryTests.test_cas_concurrency_allows_one_transition)
ERROR: test_changed_committed_evidence_or_event_fails_lookup (test_champion_registry.ChampionRegistryTests.test_changed_committed_evidence_or_event_fails_lookup)
ERROR: test_invalid_probability_state_rejected_even_without_matching_rows (test_champion_registry.ChampionRegistryTests.test_invalid_probability_state_rejected_even_without_matching_rows)
ERROR: test_orphan_event_before_pointer_commit_never_becomes_active (test_champion_registry.ChampionRegistryTests.test_orphan_event_before_pointer_commit_never_becomes_active)
ERROR: test_production_activation_ignores_self_declared_trust (test_champion_registry.ChampionRegistryTests.test_production_activation_ignores_self_declared_trust)
ERROR: test_restricted_summary_and_insufficient_folds_never_pass (test_champion_registry.ChampionRegistryTests.test_restricted_summary_and_insufficient_folds_never_pass)
ERROR: test_retry_same_transition_is_idempotent_and_code_identity_is_bound (test_champion_registry.ChampionRegistryTests.test_retry_same_transition_is_idempotent_and_code_identity_is_bound)
ERROR: test_rollback_requires_prior_committed_validated_record (test_champion_registry.ChampionRegistryTests.test_rollback_requires_prior_committed_validated_record)
ERROR: test_sandbox_context_cannot_be_reused_after_exit (test_champion_registry.ChampionRegistryTests.test_sandbox_context_cannot_be_reused_after_exit)
ERROR: test_sandbox_lifecycle_preserves_artifact_and_historical_selection (test_champion_registry.ChampionRegistryTests.test_sandbox_lifecycle_preserves_artifact_and_historical_selection)
ERROR: test_score_only_fitted_values_above_one_remain_valid (test_champion_registry.ChampionRegistryTests.test_score_only_fitted_values_above_one_remain_valid)
ERROR: test_master_executes_audit_and_preserves_snapshot_inventory (test_evidence_audit.EvidenceAuditTests.test_master_executes_audit_and_preserves_snapshot_inventory)
ERROR: test_only_exact_osm_archive_is_inventoried_not_bridge_runtime (test_evidence_audit.EvidenceAuditTests.test_only_exact_osm_archive_is_inventoried_not_bridge_runtime)
ERROR: test_zero_master_budget_never_invokes_auditor (test_evidence_audit.EvidenceAuditTests.test_zero_master_budget_never_invokes_auditor)
ERROR: test_actual_thirteen_file_crosswalk (test_gpx_outcome_source_matrix.MatrixTests.test_actual_thirteen_file_crosswalk)
ERROR: test_master_failed_audit_never_calls_model_adapter (test_learning_snapshot.LearningSnapshotTests.test_master_failed_audit_never_calls_model_adapter)
ERROR: test_master_generated_workspace_is_recoverable_without_input_exemption (test_learning_snapshot.LearningSnapshotTests.test_master_generated_workspace_is_recoverable_without_input_exemption)
ERROR: test_master_passes_shared_budget_into_builder (test_learning_snapshot.LearningSnapshotTests.test_master_passes_shared_budget_into_builder)
ERROR: test_legacy_chronological_walkforward (unittest.loader._FailedTest.test_legacy_chronological_walkforward)
ERROR: test_authoritative_owner_and_calendar_validation (test_master_e2e.BridgeTests.test_authoritative_owner_and_calendar_validation)
ERROR: test_bundle_hash_and_checkpoint_hash_corruption_are_rejected (test_master_e2e.BridgeTests.test_bundle_hash_and_checkpoint_hash_corruption_are_rejected)
ERROR: test_bundle_tamper_traversal_and_size_caps_fail_closed (test_master_e2e.BridgeTests.test_bundle_tamper_traversal_and_size_caps_fail_closed)
ERROR: test_changed_source_new_issue_changes_run_but_old_receipt_stays_pinned (test_master_e2e.BridgeTests.test_changed_source_new_issue_changes_run_but_old_receipt_stays_pinned)
ERROR: test_checkpoint_callback_persists_before_hard_exit_and_fresh_restore (test_master_e2e.BridgeTests.test_checkpoint_callback_persists_before_hard_exit_and_fresh_restore)
ERROR: test_checkpoint_publication_limit_retains_specific_blocker (test_master_e2e.BridgeTests.test_checkpoint_publication_limit_retains_specific_blocker)
ERROR: test_compact_bundle_restores_fresh_workdir_and_valid_exit_two (test_master_e2e.BridgeTests.test_compact_bundle_restores_fresh_workdir_and_valid_exit_two)
ERROR: test_corrupt_receipt_is_audited_without_starving_later_command (test_master_e2e.BridgeTests.test_corrupt_receipt_is_audited_without_starving_later_command)
ERROR: test_crash_cannot_reuse_stale_pass (test_master_e2e.BridgeTests.test_crash_cannot_reuse_stale_pass)
ERROR: test_discovery_only_suppresses_verified_durable_handled_receipt (test_master_e2e.BridgeTests.test_discovery_only_suppresses_verified_durable_handled_receipt)
ERROR: test_discovery_retries_do_not_starve_later_commands (test_master_e2e.BridgeTests.test_discovery_retries_do_not_starve_later_commands)
ERROR: test_expired_lost_attempt_reservation_is_shared_across_issue_ids (test_master_e2e.BridgeTests.test_expired_lost_attempt_reservation_is_shared_across_issue_ids)
ERROR: test_fixed_bridge_budget_cannot_be_reset_by_new_attempt (test_master_e2e.BridgeTests.test_fixed_bridge_budget_cannot_be_reset_by_new_attempt)
ERROR: test_handled_receipt_cannot_override_verified_scientific_result (test_master_e2e.BridgeTests.test_handled_receipt_cannot_override_verified_scientific_result)
ERROR: test_identity_ignores_kernel_and_incidental_packages (test_master_e2e.BridgeTests.test_identity_ignores_kernel_and_incidental_packages)
ERROR: test_new_issue_cannot_advertise_mixed_completed_shared_run (test_master_e2e.BridgeTests.test_new_issue_cannot_advertise_mixed_completed_shared_run)
ERROR: test_nonobject_and_missing_receipts_leave_healthy_command_discoverable (test_master_e2e.BridgeTests.test_nonobject_and_missing_receipts_leave_healthy_command_discoverable)
ERROR: test_publication_refuses_mixed_report_tree_without_discarding_it (test_master_e2e.BridgeTests.test_publication_refuses_mixed_report_tree_without_discarding_it)
ERROR: test_publication_time_cannot_extend_reserved_deadline (test_master_e2e.BridgeTests.test_publication_time_cannot_extend_reserved_deadline)
ERROR: test_recovery_never_imports_supplemental_source_code (test_master_e2e.BridgeTests.test_recovery_never_imports_supplemental_source_code)
ERROR: test_report_blob_size_is_checked_before_materialization (test_master_e2e.BridgeTests.test_report_blob_size_is_checked_before_materialization)
ERROR: test_restore_requires_complete_inventory_and_result_binding (test_master_e2e.BridgeTests.test_restore_requires_complete_inventory_and_result_binding)
ERROR: test_sandbox_lifecycle_and_full_master_keep_production_blocked (test_master_e2e.BridgeTests.test_sandbox_lifecycle_and_full_master_keep_production_blocked)
ERROR: test_scientific_dependency_change_creates_new_run_identity (test_master_e2e.BridgeTests.test_scientific_dependency_change_creates_new_run_identity)
ERROR: test_skeletal_handled_receipt_does_not_hide_command (test_master_e2e.BridgeTests.test_skeletal_handled_receipt_does_not_hide_command)
ERROR: test_stale_processing_label_does_not_hide_unfinished_command (test_master_e2e.BridgeTests.test_stale_processing_label_does_not_hide_unfinished_command)
ERROR: test_transport_cas_and_explicit_paths_leave_worktree_untouched (test_master_e2e.BridgeTests.test_transport_cas_and_explicit_paths_leave_worktree_untouched)
ERROR: test_transport_enforces_caps_for_receipts_too (test_master_e2e.BridgeTests.test_transport_enforces_caps_for_receipts_too)
ERROR: test_two_commands_converge_and_partial_publication_recovers (test_master_e2e.BridgeTests.test_two_commands_converge_and_partial_publication_recovers)
ERROR: test_unconsumed_source_change_can_share_run_without_mixed_report_tree (test_master_e2e.BridgeTests.test_unconsumed_source_change_can_share_run_without_mixed_report_tree)
ERROR: test_workflows_share_executor_with_read_only_pr_permission (test_master_e2e.BridgeTests.test_workflows_share_executor_with_read_only_pr_permission)
ERROR: test_budget_exhaustion_has_all_stages_and_retry_conditions (test_master_orchestrator.MasterTests.test_budget_exhaustion_has_all_stages_and_retry_conditions)
ERROR: test_budget_retry_requires_larger_limit_and_preserves_ledger (test_master_orchestrator.MasterTests.test_budget_retry_requires_larger_limit_and_preserves_ledger)
ERROR: test_cli_uses_master_and_reports_missing_implementations (test_master_orchestrator.MasterTests.test_cli_uses_master_and_reports_missing_implementations)
ERROR: test_code_policy_and_champion_identity_changes_invalidate_previous_run (test_master_orchestrator.MasterTests.test_code_policy_and_champion_identity_changes_invalidate_previous_run)
ERROR: test_concurrent_cli_commands_share_one_verified_run (test_master_orchestrator.MasterTests.test_concurrent_cli_commands_share_one_verified_run)
ERROR: test_contradictory_operational_pass_cannot_validate_failed_child (test_master_orchestrator.MasterTests.test_contradictory_operational_pass_cannot_validate_failed_child)
ERROR: test_corrupt_checkpoint_rejected (test_master_orchestrator.MasterTests.test_corrupt_checkpoint_rejected)
ERROR: test_corrupt_stage_output_rejected_not_reused (test_master_orchestrator.MasterTests.test_corrupt_stage_output_rejected_not_reused)
ERROR: test_duplicate_reuses_verified_run_and_input_changes_make_new_run (test_master_orchestrator.MasterTests.test_duplicate_reuses_verified_run_and_input_changes_make_new_run)
ERROR: test_final_manifest_references_an_existing_verified_checkpoint (test_master_orchestrator.MasterTests.test_final_manifest_references_an_existing_verified_checkpoint)
ERROR: test_generated_artifact_validation_failure_replaces_stale_pass (test_master_orchestrator.MasterTests.test_generated_artifact_validation_failure_replaces_stale_pass)
ERROR: test_hard_interruption_charges_inflight_time_before_resuming (test_master_orchestrator.MasterTests.test_hard_interruption_charges_inflight_time_before_resuming)
ERROR: test_independent_model_adapter_receives_snapshot_and_generated_replay_survives (test_master_orchestrator.MasterTests.test_independent_model_adapter_receives_snapshot_and_generated_replay_survives)
ERROR: test_interrupted_run_rejects_tampered_completed_stage_artifact (test_master_orchestrator.MasterTests.test_interrupted_run_rejects_tampered_completed_stage_artifact)
ERROR: test_interrupted_run_rejects_uncommitted_new_replay_artifact (test_master_orchestrator.MasterTests.test_interrupted_run_rejects_uncommitted_new_replay_artifact)
ERROR: test_interrupted_stage_resumes_and_preserves_elapsed_budget (test_master_orchestrator.MasterTests.test_interrupted_stage_resumes_and_preserves_elapsed_budget)
ERROR: test_interruption_persists_fail_and_budget_ledger (test_master_orchestrator.MasterTests.test_interruption_persists_fail_and_budget_ledger)
ERROR: test_malformed_adapter_blockers_become_fail_not_exception (test_master_orchestrator.MasterTests.test_malformed_adapter_blockers_become_fail_not_exception)
ERROR: test_malformed_operational_blockers_replace_stale_pass (test_master_orchestrator.MasterTests.test_malformed_operational_blockers_replace_stale_pass)
ERROR: test_midrun_learning_mutation_fails_even_with_snapshot (test_master_orchestrator.MasterTests.test_midrun_learning_mutation_fails_even_with_snapshot)
ERROR: test_missing_evidence_returns_every_stage_and_honest_blockers (test_master_orchestrator.MasterTests.test_missing_evidence_returns_every_stage_and_honest_blockers)
ERROR: test_missing_operational_stage_structure_fails (test_master_orchestrator.MasterTests.test_missing_operational_stage_structure_fails)
ERROR: test_operational_exception_still_attempts_independent_research (test_master_orchestrator.MasterTests.test_operational_exception_still_attempts_independent_research)
ERROR: test_original_and_raw_bytes_preserved (test_master_orchestrator.MasterTests.test_original_and_raw_bytes_preserved)
ERROR: test_paths_cannot_escape_and_symlink_inputs_rejected (test_master_orchestrator.MasterTests.test_paths_cannot_escape_and_symlink_inputs_rejected)
ERROR: test_provenance_and_model_specs_are_snapshotted_and_identity_bound (test_master_orchestrator.MasterTests.test_provenance_and_model_specs_are_snapshotted_and_identity_bound)
ERROR: test_tampered_generated_operational_artifact_invalidates_resume (test_master_orchestrator.MasterTests.test_tampered_generated_operational_artifact_invalidates_resume)
ERROR: test_master_scoring (unittest.loader._FailedTest.test_master_scoring)
ERROR: test_format_only_prediction_mutation_is_detected (test_p0_pdca_freeze_integrity.P0ToPDCAIntegrityTests.test_format_only_prediction_mutation_is_detected)
ERROR: test_frozen_p0_to_gpx_capture_pdca_is_diagnostic_not_official (test_p0_pdca_freeze_integrity.P0ToPDCAIntegrityTests.test_frozen_p0_to_gpx_capture_pdca_is_diagnostic_not_official)
ERROR: test_missing_sidecar_stays_diagnostic_not_official (test_p0_pdca_freeze_integrity.P0ToPDCAIntegrityTests.test_missing_sidecar_stays_diagnostic_not_official)
ERROR: test_pdca_aborts_before_reading_observations_on_corrupt_frozen_p0 (test_p0_pdca_freeze_integrity.P0ToPDCAIntegrityTests.test_pdca_aborts_before_reading_observations_on_corrupt_frozen_p0)
ERROR: test_real_freeze_bytes_and_sha_sidecar_agree (test_p0_pdca_freeze_integrity.P0ToPDCAIntegrityTests.test_real_freeze_bytes_and_sha_sidecar_agree)
ERROR: test_sidecar_corruption_is_fail_not_a_missing_provenance_warning (test_p0_pdca_freeze_integrity.P0ToPDCAIntegrityTests.test_sidecar_corruption_is_fail_not_a_missing_provenance_warning)
ERROR: test_symlinked_sidecar_is_rejected (test_p0_pdca_freeze_integrity.P0ToPDCAIntegrityTests.test_symlinked_sidecar_is_rejected)
ERROR: test_symlinked_record_is_rejected_for_both_path_separators (test_p0_pdca_freeze_integrity.PredictionSidecarPathTests.test_symlinked_record_is_rejected_for_both_path_separators)
ERROR: test_symlinked_sidecar_is_rejected_for_both_path_separators (test_p0_pdca_freeze_integrity.PredictionSidecarPathTests.test_symlinked_sidecar_is_rejected_for_both_path_separators)
ERROR: test_p0_readiness (unittest.loader._FailedTest.test_p0_readiness)
ERROR: test_bash_syntax (test_pages_bootstrap.PagesBootstrapTests.test_bash_syntax)
ERROR: test_followup_needs_production_url (test_pages_bootstrap.PagesBootstrapTests.test_followup_needs_production_url)
ERROR: test_no_access_approval_blocks (test_pages_bootstrap.PagesBootstrapTests.test_no_access_approval_blocks)
ERROR: test_preview_deployments_required_disabled (test_pages_bootstrap.PagesBootstrapTests.test_preview_deployments_required_disabled)
ERROR: test_pdca_actions_pr_handoff (unittest.loader._FailedTest.test_pdca_actions_pr_handoff)
ERROR: test_pdca_e2e (unittest.loader._FailedTest.test_pdca_e2e)
ERROR: test_prediction_lineage (unittest.loader._FailedTest.test_prediction_lineage)
ERROR: test_baseline_disagreement_blocks_more_labels_not_less (test_reconcile_actual_gpx_exposure.RealSourceReconciliationTests.test_baseline_disagreement_blocks_more_labels_not_less)
ERROR: test_frozen_baseline_count_conflict_still_blocks_any_label (test_reconcile_actual_gpx_exposure.RealSourceReconciliationTests.test_frozen_baseline_count_conflict_still_blocks_any_label)
ERROR: test_no_automatic_positive_eligibility_even_if_count_equal (test_reconcile_actual_gpx_exposure.RealSourceReconciliationTests.test_no_automatic_positive_eligibility_even_if_count_equal)
ERROR: test_real_archive_events_and_monthly_conflict_are_quarantined (test_reconcile_actual_gpx_exposure.RealSourceReconciliationTests.test_real_archive_events_and_monthly_conflict_are_quarantined)
ERROR: setUpClass (test_recover_remaining_august_nights.RemainingAugustTests)
ERROR: setUpClass (test_recover_two_habu_nights.TwoNightSourceTests)
ERROR: setUpClass (test_remaining_august_road_candidates.RealRemainingElevenNights)
ERROR: test_run_pdca (unittest.loader._FailedTest.test_run_pdca)
FAIL: test_owner_monthly_count_does_not_override_missing_raw_event_bytes (test_august_native_evidence_packets.NativeCaptureByteSourceTests.test_owner_monthly_count_does_not_override_missing_raw_event_bytes)
```

</details>
