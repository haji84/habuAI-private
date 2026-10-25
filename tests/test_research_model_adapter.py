"""Synthetic computation tests; no fixture attests actual search or outcomes."""
import copy
import hashlib
import inspect
import socket
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from master_contracts import digest
from test_research_selection import bind_selection, future_fixture, insufficient_fixture, selection_fixture


class ResearchCompetitionTests(unittest.TestCase):
    def run_core(self, selection=None, rows=None, **options):
        from research_model_adapter import prepare_research_candidates
        rows = future_fixture() if rows is None else rows
        return prepare_research_candidates(
            selection_fixture() if selection is None else selection, rows,
            cutoff_time="2026-10-14T18:00:00+09:00",
            joined_universe_sha256=options.pop("joined_universe_sha256", digest(rows)),
            budget_seconds=options.pop("budget_seconds", 30), **options)

    def test_three_distinct_recipes_use_every_same_future_unit_including_unseen(self):
        result = self.run_core()
        self.assertEqual(result["status"], "DIAGNOSTIC_CANDIDATES_PREPARED")
        self.assertEqual([c["candidate_id"] for c in result["candidates"]], ["uniform", "HB-A0", "HB-B1"])
        ids = {r["row_id"] for r in future_fixture()}
        for candidate in result["candidates"]:
            self.assertEqual(set(candidate["forecast_row_ids"]), ids)
            self.assertEqual(candidate["joined_universe_sha256"], digest(future_fixture()))
            self.assertEqual(candidate["forecast_units"], 3)
            self.assertEqual(candidate["model_sha256"], candidate["model"]["model_sha256"])
        self.assertEqual(result["candidates"][2]["model"]["status"], "DEVELOPMENT_CANDIDATE_FITTED")

    def test_uniform_preserves_smoothed_legacy_definition_and_hierarchy_score_semantics(self):
        selected = selection_fixture()
        row = selected["accepted"][1]
        row.update(label=1, capture_event_ids=["extra-synthetic-event"])
        selected["counts"].update(positives=4, negatives=2)
        result = self.run_core(bind_selection(selected))
        uniform = result["candidates"][0]
        self.assertEqual(uniform["model"]["probability"], 5 / 8)
        self.assertEqual({r["probability"] for r in uniform["prediction"]["unit_predictions"]}, {5 / 8})
        hierarchy = result["candidates"][2]["prediction"]
        self.assertTrue(all("probability" not in r for r in hierarchy["unit_scores"]))
        self.assertTrue(all("rank_score_diagnostic" in r for r in hierarchy["unit_scores"]))

    def test_receipt_never_claims_source_authentication_metrics_winner_or_replay_publication(self):
        result = self.run_core()
        self.assertEqual(result["scientific_status"], "NOT_VALIDATED")
        self.assertEqual(result["source_authentication"], "CALLER_DEPENDENCY_REQUIRED")
        self.assertEqual(result["replay_status"], "PREPARED_NOT_PUBLISHED_OR_TRUSTED_SEALED")
        self.assertFalse(result["official_issuance_authorized"])
        self.assertFalse(result["production_activation_authorized"])
        self.assertEqual(result["validation_status"], "NOT_VALIDATED")
        self.assertNotIn("winner", result)
        self.assertNotIn("metrics", result)
        self.assertEqual(result["receipt_sha256"], digest({k: v for k, v in result.items() if k != "receipt_sha256"}))

    def test_deterministic_and_input_objects_are_not_modified(self):
        selected, rows = selection_fixture(), future_fixture()
        originals = copy.deepcopy((selected, rows))
        self.assertEqual(self.run_core(selected, rows), self.run_core(selected, rows))
        self.assertEqual((selected, rows), originals)

    def test_valid_insufficient_data_never_invokes_a_fitter_or_fabricates_a_model(self):
        from research_model_adapter import prepare_research_candidates
        for selected in (insufficient_fixture(), insufficient_fixture(positive_only=True)):
            with self.subTest(rows=selected["counts"]["accepted_rows"]), \
                 patch("research_model_adapter.fit_shrinkage", side_effect=AssertionError("no fit")), \
                 patch("research_model_adapter.fit_hierarchy", side_effect=AssertionError("no fit")):
                result = self.run_core(selected)
                self.assertEqual(result["status"], "NEED_MORE_DATA")
                self.assertEqual(result["candidates"], [])
                self.assertTrue(result["blockers"])
        with self.assertRaises(ValueError):
            prepare_research_candidates(None, [], cutoff_time="2026-10-14T18:00:00+09:00",
                joined_universe_sha256=digest([]), budget_seconds=30)

    def test_all_forecast_validation_precedes_any_fit_even_with_insufficient_training(self):
        rows = future_fixture()
        rows[-1]["label"] = 1
        for selected in (selection_fixture(), insufficient_fixture()):
            with patch("research_model_adapter.fit_shrinkage", side_effect=AssertionError("no fit")), \
                 patch("research_model_adapter.fit_hierarchy", side_effect=AssertionError("no fit")), \
                 self.assertRaises(ValueError):
                self.run_core(selected, rows)
        with self.assertRaises(ValueError):
            self.run_core(joined_universe_sha256="d" * 64)

    def test_missing_duplicate_or_rebound_candidate_output_is_rejected_without_partial_result(self):
        from models.occupancy_shrinkage import predict_shrinkage
        for mutation in ("missing", "duplicate", "digest", "hash"):
            def bad(*args, **kwargs):
                value = predict_shrinkage(*args, **kwargs)
                if mutation == "missing":
                    value["unit_predictions"].pop()
                elif mutation == "duplicate":
                    value["unit_predictions"][-1] = copy.deepcopy(value["unit_predictions"][0])
                elif mutation == "digest":
                    value["universe_sha256"] = "a" * 64
                else:
                    value["prediction_sha256"] = "a" * 64
                    return value
                value["prediction_sha256"] = digest({k: v for k, v in value.items() if k != "prediction_sha256"})
                return value
            with self.subTest(mutation=mutation), patch("research_model_adapter.predict_shrinkage", side_effect=bad), self.assertRaises(ValueError):
                self.run_core()

    def test_third_model_failure_does_not_publish_prepared_first_two(self):
        with patch("research_model_adapter.rank_hierarchy", side_effect=ValueError("synthetic failure")), self.assertRaisesRegex(ValueError, "synthetic failure"):
            self.run_core()

    def test_rehashed_scores_cannot_change_bound_night_window_or_cell(self):
        from models.occupancy_shrinkage import predict_shrinkage
        for field, wrong in (("cell_x", 7777), ("window_start_jst", "1900-01-01T00:00:00+09:00"),
                             ("operational_night", "1900-01-01")):
            def bad(*args, **kwargs):
                value = predict_shrinkage(*args, **kwargs)
                value["unit_predictions"][0][field] = wrong
                value["prediction_sha256"] = digest({k: v for k, v in value.items() if k != "prediction_sha256"})
                return value
            with self.subTest(field=field), patch("research_model_adapter.predict_shrinkage", side_effect=bad), self.assertRaises(ValueError):
                self.run_core()
        from models.hierarchy_shrinkage import rank_hierarchy
        def wrong_hierarchy_cell(*args, **kwargs):
            value = rank_hierarchy(*args, **kwargs)
            value["unit_scores"][0]["cell_id"] = "utm52n_100m_7777_30000"
            value["prediction_sha256"] = digest({k: v for k, v in value.items() if k != "prediction_sha256"})
            return value
        with patch("research_model_adapter.rank_hierarchy", side_effect=wrong_hierarchy_cell), self.assertRaises(ValueError):
            self.run_core()

    def test_insufficient_data_sealing_also_checks_deadline_before_return(self):
        from research_model_adapter import ResearchBudgetExhausted, _seal
        clock = [0]
        def late(value, field):
            result = _seal(value, field)
            clock[0] = 31
            return result
        with patch("research_model_adapter.time.monotonic", side_effect=lambda: clock[0]), \
             patch("research_model_adapter._seal", side_effect=late), \
             self.assertRaises(ResearchBudgetExhausted):
            self.run_core(insufficient_fixture())

    def test_expired_shared_budget_raises_before_fit_and_after_last_model(self):
        from research_model_adapter import ResearchBudgetExhausted
        with patch("research_model_adapter.time.monotonic", side_effect=[0, 31]), \
             patch("research_model_adapter.fit_shrinkage", side_effect=AssertionError("no fit")), \
             self.assertRaises(ResearchBudgetExhausted):
            self.run_core()
        from models.hierarchy_shrinkage import rank_hierarchy
        clock = [0]
        def late(*args, **kwargs):
            value = rank_hierarchy(*args, **kwargs)
            clock[0] = 31
            return value
        with patch("research_model_adapter.time.monotonic", side_effect=lambda: clock[0]), \
             patch("research_model_adapter.rank_hierarchy", side_effect=late), \
             self.assertRaises(ResearchBudgetExhausted):
            self.run_core()

    def test_invalid_budget_is_rejected_without_changing_existing_maximum(self):
        for budget in (True, 0, -1, float("inf"), float("nan"), 301, "30"):
            with self.subTest(budget=budget), self.assertRaises(ValueError):
                self.run_core(budget_seconds=budget)

    def test_pure_computation_never_opens_any_source_or_confirmation_payload(self):
        with patch("builtins.open", side_effect=AssertionError("no filesystem reads")), \
             patch.object(Path, "open", side_effect=AssertionError("no filesystem reads")):
            self.assertEqual(self.run_core()["status"], "DIAGNOSTIC_CANDIDATES_PREPARED")


class VersionedCandidateConfigTests(unittest.TestCase):
    def setUp(self):
        import research_model_adapter as adapter
        self.adapter = adapter
        from test_hba1_feature_candidate import fixture, recipe
        protocol, folds = fixture()
        self.selection = folds[0]['training_selection']
        self.rows = folds[0]['forecast_rows']
        self.cutoff = protocol['folds'][0]['cutoff_time']
        self.definition = 'f'*64
        self.config = dict(schema_version='habu-research-candidate-config-v2', mode='DEVELOPMENT_ONLY',
            candidate_ids=['uniform', 'HB-A0', 'HB-A1'], hba1_recipe=recipe(),
            feature_definition_sha256=self.definition)

    def call(self, **kwargs):
        function = getattr(self.adapter, 'prepare_research_candidates_v2', None)
        self.assertTrue(callable(function), 'versioned fixed three-slot preparer is missing')
        return function(self.selection, self.rows, candidate_config=self.config,
            expected_config_sha256=kwargs.pop('expected_config_sha256', digest(self.config)),
            cutoff_time=self.cutoff, joined_universe_sha256=kwargs.pop('joined_universe_sha256', digest(self.rows)),
            feature_definition_sha256=kwargs.pop('feature_definition_sha256', self.definition), **kwargs)

    def test_v1_function_bodies_and_complete_receipt_are_unchanged(self):
        adapter = self.adapter
        body = ''.join(inspect.getsource(getattr(adapter, name)) for name in
            ('_seal', '_uniform', '_instant', '_candidate', 'prepare_research_candidates'))
        self.assertEqual(hashlib.sha256(body.encode()).hexdigest(), '8a0350421d84a39c781fdc78eb3c0abb23c40f1fb91022759efea44837e111e8')
        rows = future_fixture()
        value = adapter.prepare_research_candidates(selection_fixture(), rows,
            cutoff_time='2026-10-14T18:00:00+09:00', joined_universe_sha256=digest(rows))
        self.assertEqual(value['receipt_sha256'], 'a8c59d499d8fa8d132cbb05876469596c5c365755b05397f80ae06cc808184e0')
        self.assertEqual(adapter.CANDIDATES, ('uniform', 'HB-A0', 'HB-B1'))

    def test_all_three_legal_triplets_keep_same_complete_rows_train_and_cutoff(self):
        for choices in (['uniform', 'HB-A0', 'HB-B1'], ['uniform', 'HB-A0', 'HB-A1'], ['uniform', 'HB-B1', 'HB-A1']):
            self.config['candidate_ids'] = choices
            if 'HB-A1' not in choices: self.config['hba1_recipe'] = None
            else:
                from test_hba1_feature_candidate import recipe
                self.config['hba1_recipe'] = recipe()
            result = self.call()
            self.assertEqual([c['candidate_id'] for c in result['candidates']], choices)
            self.assertEqual(result['candidate_config_sha256'], digest(self.config))
            self.assertEqual(result['training_selection_sha256'], self.selection['selection_sha256'])
            for candidate in result['candidates']:
                self.assertEqual(candidate['forecast_units'], 4)
                self.assertEqual(candidate['forecast_row_ids'], sorted(r['row_id'] for r in self.rows))
                self.assertEqual(candidate['joined_universe_sha256'], digest(self.rows))
                self.assertEqual(candidate['training_rows_sha256'], digest(self.selection['accepted']))
                self.assertEqual(candidate['feature_definition_sha256'], self.definition)
                self.assertEqual(candidate['candidate_config_sha256'], digest(self.config))
                self.assertEqual(candidate['training_selection_sha256'], self.selection['selection_sha256'])
            self.assertEqual(result['receipt_sha256'], digest({k:v for k,v in result.items() if k!='receipt_sha256'}))

    def test_fourth_duplicate_unknown_or_missing_uniform_and_wrong_count_reject(self):
        for choices in (['uniform','HB-A0','HB-B1','HB-A1'], ['uniform','HB-A1','HB-A1'],
                ['HB-A0','HB-A1','HB-B1'], ['uniform','HB-A0','OTHER'], ['uniform','HB-A1'],
                ['HB-A1','uniform','HB-A0'], ['uniform', True, 'HB-A1']):
            self.config['candidate_ids'] = choices
            with self.subTest(choices=choices), self.assertRaises(ValueError): self.call()

    def test_hba1_recipe_is_full_seven_only_and_absent_when_not_selected(self):
        self.config['hba1_recipe']['feature_mask'][0] = False
        with self.assertRaises(ValueError): self.call()
        self.config['hba1_recipe'] = None
        with self.assertRaises(ValueError): self.call()
        self.setUp()
        self.config['candidate_ids'] = ['uniform','HB-A0','HB-B1']
        with self.assertRaises(ValueError): self.call()

    def test_config_content_expected_hash_strict_definition_and_unknown_trust_flags_reject(self):
        expected = digest(self.config)
        self.config['candidate_ids'] = ['uniform','HB-B1','HB-A1']
        with self.assertRaises(ValueError): self.call(expected_config_sha256=expected)
        with self.assertRaises(ValueError): self.call(feature_definition_sha256='e'*64)
        self.config['trusted_freeze'] = True
        with self.assertRaises(ValueError): self.call()
        self.config.pop('trusted_freeze')
        self.config['mode'] = 'CONFIRMATION'
        with self.assertRaises(ValueError): self.call()

    def test_hba1_data_insufficient_stops_whole_set_before_any_model(self):
        self.selection = selection_fixture()  # valid common input, only rain_mm
        self.rows = future_fixture()
        self.cutoff = '2026-10-14T18:00:00+09:00'
        with patch.object(self.adapter, '_uniform', side_effect=AssertionError('partial uniform')), \
                patch.object(self.adapter, 'fit_shrinkage', side_effect=AssertionError('partial A0')):
            result = self.call()
        self.assertEqual(result['status'], 'NEED_MORE_DATA')
        self.assertEqual(result['candidates'], [])
        self.assertTrue(result['blockers'])
        self.setUp()
        self.selection['accepted'] = self.selection['accepted'][:16]
        self.selection['counts'].update(accepted_rows=16, nights=4, positives=4, negatives=12)
        bind_selection(self.selection)
        with patch.object(self.adapter, '_uniform', side_effect=AssertionError('partial uniform')):
            result = self.call()
        self.assertEqual(result['status'], 'NEED_MORE_DATA')
        self.assertEqual(result['candidates'], [])

    def test_valid_insufficient_without_hba1_still_validates_all_future_rows(self):
        self.selection = insufficient_fixture()
        self.rows = future_fixture()
        self.cutoff = '2026-10-14T18:00:00+09:00'
        self.config.update(candidate_ids=['uniform','HB-A0','HB-B1'], hba1_recipe=None)
        self.assertEqual(self.call()['status'], 'NEED_MORE_DATA')
        self.rows[0]['label'] = 1
        with self.assertRaises(ValueError): self.call()

    def test_malformed_future_or_physical_value_rejects_even_if_train_insufficient(self):
        for field in ('cutoff', 'source', 'label', 'physical'):
            self.setUp()
            self.selection['accepted'] = self.selection['accepted'][:16]
            self.selection['counts'].update(accepted_rows=16, nights=4, positives=4, negatives=12)
            bind_selection(self.selection)
            if field == 'cutoff': self.rows[0]['feature_available_at']['temperature_c'] = self.cutoff
            elif field == 'source': self.rows[0]['feature_source_refs']['temperature_c'] = []
            elif field == 'label': self.rows[0]['label'] = 1
            else: self.rows[0]['features']['humidity_pct'] = 101
            with self.subTest(field=field), self.assertRaises(ValueError): self.call()

    def test_hba1_returned_code_and_recipe_assertions_must_match_config(self):
        from models.hba1_feature_candidate import fit_hba1
        def mismatch(*args, **kwargs):
            value = fit_hba1(*args, **kwargs)
            model = value['model']
            model['recipe']['implementation_sha256']['src/prospective_candidate_model.py'] = 'c'*64
            model['recipe_sha256'] = digest(model['recipe'])
            model['model_sha256'] = digest({k:v for k,v in model.items() if k!='model_sha256'})
            value['receipt_sha256'] = digest({k:v for k,v in value.items() if k!='receipt_sha256'})
            return value
        with patch.object(self.adapter._hba1, 'fit_hba1', side_effect=mismatch), self.assertRaises(ValueError): self.call()

    def test_declared_code_hash_is_not_treated_as_actual_file_authentication(self):
        self.config['hba1_recipe']['implementation_sha256'] = {key: '0'*64 for key in self.config['hba1_recipe']['implementation_sha256']}
        result = self.call()
        self.assertEqual(result['source_authentication'], 'CALLER_DEPENDENCY_REQUIRED')
        self.assertEqual(result['source_authenticity'], 'NOT_ATTESTED')

    def test_whole_set_cleared_when_late_hba1_reports_valid_insufficiency(self):
        from models.hba1_feature_candidate import fit_hba1
        def insufficient(*args, **kwargs):
            value = fit_hba1(*args, **kwargs)
            value.update(status='NEED_MORE_DATA', model=None, blockers=['No complete HBA1 fit'])
            value['receipt_sha256'] = digest({k:v for k,v in value.items() if k!='receipt_sha256'})
            return value
        with patch.object(self.adapter._hba1, 'fit_hba1', side_effect=insufficient): result = self.call()
        self.assertEqual(result['candidates'], [])
        self.assertEqual(result['status'], 'NEED_MORE_DATA')

    def test_rehashed_hba1_output_missing_duplicate_or_rebound_units_rejects(self):
        from models.hba1_feature_candidate import predict_hba1
        for change in ('missing', 'duplicate', 'physical', 'training'):
            def bad(*args, **kwargs):
                value = predict_hba1(*args, **kwargs)
                if change == 'missing': value['unit_predictions'].pop()
                elif change == 'duplicate': value['unit_predictions'][-1] = copy.deepcopy(value['unit_predictions'][0])
                elif change == 'physical': value['unit_predictions'][0]['cell_x'] += 1
                else: value['training_selection_sha256'] = 'a'*64
                value['prediction_sha256'] = digest({k:v for k,v in value.items() if k!='prediction_sha256'})
                return value
            with self.subTest(change=change), patch.object(self.adapter._hba1, 'predict_hba1', side_effect=bad), self.assertRaises(ValueError): self.call()

    def test_native_optional_candidate_and_training_assertions_cannot_contradict_config(self):
        from models.hba1_feature_candidate import predict_hba1
        def wrong(*args, **kwargs):
            value = predict_hba1(*args, **kwargs)
            value['candidate_id'] = 'HB-B1'
            value['prediction_sha256'] = digest({k:v for k,v in value.items() if k!='prediction_sha256'})
            return value
        with patch.object(self.adapter._hba1, 'predict_hba1', side_effect=wrong), self.assertRaises(ValueError): self.call()

    def test_owned_combined_snapshot_blocks_mutation_after_first_model_and_has_no_aliases(self):
        before = copy.deepcopy((self.config, self.selection, self.rows))
        expected = self.call()
        self.assertEqual((self.config, self.selection, self.rows), before)
        native = self.adapter._uniform
        def mutate(*args, **kwargs):
            self.config['hba1_recipe']['implementation_sha256']['src/prospective_candidate_model.py'] = 'd'*64
            self.selection['accepted'][0]['label'] = 0
            self.rows[0]['features']['temperature_c'] = 999
            return native(*args, **kwargs)
        with patch.object(self.adapter, '_uniform', side_effect=mutate): result = self.call()
        self.assertEqual(result, expected)

    def test_parent_read_context_expires_inside_actual_numeric_loop(self):
        import prospective_inputs as pi
        import prospective_candidate_model as learner
        context = pi.ProspectiveReadContext(300, 2*1024**3)
        core = learner._fit_numeric
        entered = []
        def numeric(*args, **kwargs):
            entered.append(True)
            context.deadline = 0
            return core(*args, **kwargs)
        with patch.object(learner, '_fit_numeric', side_effect=numeric), self.assertRaises(TimeoutError):
            self.call(check=context.check)
        self.assertEqual(entered, [True])
        self.assertEqual(context.bytes_read, 0)

    def test_final_receipt_digest_deadline_blocks_both_success_and_insufficiency(self):
        function = getattr(self.adapter, 'prepare_research_candidates_v2', None)
        self.assertTrue(callable(function), 'v2 preparer missing')
        real = self.adapter._v2_digest
        for insufficient in (False, True):
            self.setUp()
            if insufficient:
                self.selection['accepted'] = self.selection['accepted'][:16]
                self.selection['counts'].update(accepted_rows=16, nights=4, positives=4, negatives=12)
                bind_selection(self.selection)
            clock = [0]
            def late(value, check):
                answer = real(value, check)
                if type(value) is dict and value.get('schema_version') == self.adapter.VERSION_V2: clock[0] = 31
                return answer
            with patch.object(self.adapter.time, 'monotonic', side_effect=lambda: clock[0]), \
                    patch.object(self.adapter, '_v2_digest', side_effect=late), self.assertRaises(self.adapter.ResearchBudgetExhausted): self.call()

    def test_combined_capacity_precedes_owned_parse_and_does_not_truncate(self):
        function = getattr(self.adapter, 'prepare_research_candidates_v2', None)
        self.assertTrue(callable(function), 'v2 preparer missing')
        for constant in ('V2_MAX_JSON_BYTES', 'V2_MAX_JSON_NODES', 'V2_MAX_TRAIN_ROWS', 'MAX_FORECAST_ROWS'):
            with self.subTest(constant=constant), patch.object(self.adapter, constant, 1), self.assertRaises(self.adapter.ResearchCapacityBlocked): self.call()
        with patch.object(self.adapter, 'V2_MAX_JSON_BYTES', 1), \
                patch.object(self.adapter.json, 'loads', side_effect=AssertionError('owned parse before cap')), \
                self.assertRaises(self.adapter.ResearchCapacityBlocked): self.call()

    def test_no_files_network_parent_stage1_or_source_auth_flags(self):
        with patch('builtins.open', side_effect=AssertionError('file')), \
                patch.object(Path, 'open', side_effect=AssertionError('path')), \
                patch.object(socket, 'socket', side_effect=AssertionError('net')):
            result = self.call()
        for field in ('fit_authorized','selection_authorized','promotion_authorized','official_issuance_authorized',
                      'production_activation_authorized','scientific_execution_authorized'):
            self.assertIs(result[field], False)
        self.assertEqual(result['validation_status'], 'NOT_VALIDATED')
        self.assertIn('VERSIONED_PARENT_DISPATCH_NOT_IMPLEMENTED', result['implementation_blockers'])
        self.assertIn('STAGE1_V2_CANDIDATE_REGISTRY_NOT_IMPLEMENTED', result['implementation_blockers'])
        self.assertIn('TRUSTED_CUMULATIVE_CAMPAIGN_LEDGER_NOT_IMPLEMENTED', result['implementation_blockers'])
        self.assertNotIn('winner', result)
        self.assertNotIn('metrics', result)

    def test_invalid_budget_and_noncallable_parent_check_reject(self):
        for budget in (True,0,-1,301,10**1000,float('nan'),float('inf'),'30'):
            with self.subTest(budget=str(budget)[:20]), self.assertRaises(ValueError): self.call(budget_seconds=budget)
        with self.assertRaises(ValueError): self.call(check=True)


if __name__ == "__main__":
    unittest.main()
