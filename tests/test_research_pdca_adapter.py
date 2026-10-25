"""End-to-end synthetic declarations; no real observations or accuracy evidence."""
import copy
import json
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from master_contracts import canonical_bytes, digest, validate_adapter_result
import test_g0_training_source_contract as training_fixtures
from test_g0_forecast_contract import SyntheticContract, definition_hash, NIGHT, NOW, CUTOFF, base_ref


class ResearchPDCAAdapterTests(unittest.TestCase):
    def setUp(self):
        self.training = training_fixtures.TrainingSourceContractTests()
        self.training.setUp()
        self.addCleanup(self.training.doCleanups)
        self.root = self.training.root
        self.forecast = SyntheticContract(self.root)
        f = self.forecast
        f.features[:] = copy.deepcopy(self.training.features)
        f.manifest['feature_definition_sha256'] = definition_hash(f.features)
        node = f.nodes.pop('weather')
        node.update(id='road-source', source_kind='static')
        f.nodes['road-source'] = node
        f.objects[node['ref']['path']]['source_kind'] = 'static'
        for item in f.nodes.values():
            item['parents'] = ['road-source' if p == 'weather' else p for p in item['parents']]
            obj = f.objects[item['ref']['path']]
            if item['source_kind'] == 'feature_values':
                obj.update(feature_name='road_length_m', use_role='static_predictor')
            elif item['source_kind'] == 'snapshot':
                obj['feature_schema_sha256'] = digest(['road_length_m'])
            elif item['source_kind'] == 'validity':
                obj['feature_sources'] = {'road_length_m': obj['feature_sources']['rain_3h_mm']}
                for row in obj['rows'].values():
                    row['road_length_m'] = row.pop('rain_3h_mm')
        f.publish()
        self.request = dict(schema_version='habu-research-model-request-v1', mode='DEVELOPMENT_ONLY',
            operational_night=NIGHT, fit_cutoff='2026-10-13T18:00:00+09:00',
            forecast_as_of=NOW.isoformat(), forecast_cutoff=CUTOFF,
            feature_definition_sha256=definition_hash(f.features),
            training_manifest=self.training.ref, forecast_manifest=f.ref, exposed_nights=[])
        self.publish()

    def publish(self):
        base_ref(self.root, 'config/research-model-request.json', canonical_bytes(self.request))

    def call(self, **kwargs):
        from research_pdca_adapter import evaluate_research_request
        return evaluate_research_request(self.root, NIGHT, **kwargs)

    def test_actual_file_loader_prepares_three_candidates_and_immutable_replay(self):
        result = self.call()
        self.assertEqual([c['candidate_id'] for c in result['candidates']], ['uniform', 'HB-A0', 'HB-B1'])
        rows = validate_adapter_result(result, ('model_evaluation', 'feature_research', 'candidate_generation', 'candidate_validation'))
        self.assertEqual(rows['candidate_generation']['status'], 'PASS')
        self.assertEqual(rows['candidate_validation']['status'], 'BLOCKED')
        self.assertEqual(result['decision']['decision'], 'NEED_MORE_DATA')
        self.assertFalse(result['production_activation_authorized'])
        self.assertFalse(result['scientific_fit_authorized'])
        self.assertEqual(len(result['replay']), 1)
        replay = result['replay'][0]
        payload = (self.root / replay['path']).read_bytes()
        self.assertEqual(digest(json.loads(payload)), replay['content_sha256'])
        self.assertEqual(self.call()['replay'], result['replay'])
        (self.root / replay['path']).write_bytes(b'corrupted')
        self.assertEqual(self.call()['stages'][0]['status'], 'FAIL')

    def test_dispatch_never_opens_legacy_or_sealed_confirmation(self):
        from model_evaluation import evaluate_models
        sealed = self.root / 'sealed/confirmation/labels.json'
        sealed.parent.mkdir(parents=True)
        sealed.write_bytes(b'no reading allowed')
        actual = Path.open
        def observe(path, *args, **kwargs):
            if 'sealed' in path.parts or path.name == 'model_learning.json':
                raise AssertionError('Legacy or sealed confirmation was opened')
            return actual(path, *args, **kwargs)
        with patch.object(Path, 'open', new=observe), patch('model_evaluation._validate', side_effect=AssertionError('legacy validation')):
            self.assertEqual(len(evaluate_models(self.root, NIGHT)['candidates']), 3)

    def test_missing_sources_block_without_replay_and_bad_refs_fail_closed(self):
        (self.root / self.training.ref['path']).unlink()
        result = self.call()
        self.assertEqual(result['stages'][0]['status'], 'BLOCKED')
        self.assertEqual(result['decision']['decision'], 'NEED_MORE_DATA')
        self.assertEqual(result['replay'], [])
        self.request['training_manifest']['path'] = 'sealed/confirmation/labels.json'
        self.publish()
        self.assertEqual(self.call()['stages'][0]['status'], 'FAIL')

    def test_insufficient_qualified_classes_return_need_more_data_without_invented_zeros(self):
        f = self.training.fixture
        f.rows[:] = f.rows[:1]
        f.publish()
        self.training.build_manifest()
        self.request['training_manifest'] = self.training.ref
        self.publish()
        with patch('research_model_adapter.fit_shrinkage', side_effect=AssertionError('insufficient fit')):
            result = self.call()
        self.assertEqual(result['decision']['decision'], 'NEED_MORE_DATA')
        self.assertEqual(result['stages'][0]['status'], 'BLOCKED')
        self.assertEqual(result['candidates'], [])
        self.assertEqual(result['replay'], [])

    def test_excessive_json_nesting_returns_invalid_result(self):
        raw = b'{"nested":' * 1200 + b'0' + b'}' * 1200
        base_ref(self.root, 'config/research-model-request.json', raw)
        self.assertEqual(self.call()['stages'][0]['status'], 'FAIL')

    def test_late_request_binding_or_definition_mismatch_never_fits(self):
        import research_model_adapter
        for key, value in [('forecast_cutoff', NIGHT + 'T17:00:00+09:00'),
                           ('feature_definition_sha256', 'f' * 64), ('operational_night', '2026-10-15')]:
            original = self.request[key]
            self.request[key] = value
            self.publish()
            with patch.object(research_model_adapter, 'prepare_research_candidates', side_effect=AssertionError('fit was reached')):
                self.assertEqual(self.call()['stages'][0]['status'], 'FAIL')
            self.request[key] = original

    def test_nested_forecast_source_cannot_open_sealed_payload(self):
        node = self.forecast.nodes['road-source']
        node['ref']['path'] = 'features/sealed/confirmation/secret.json'
        self.forecast.manifest_only()
        self.request['forecast_manifest'] = self.forecast.ref
        self.publish()
        actual = Path.open
        def observe(path, *args, **kwargs):
            if 'sealed' in path.parts:
                raise AssertionError('nested sealed payload opened')
            return actual(path, *args, **kwargs)
        with patch.object(Path, 'open', new=observe):
            self.assertEqual(self.call()['stages'][0]['status'], 'FAIL')

    def test_training_mutation_during_model_preparation_is_rechecked_before_publish(self):
        import research_model_adapter
        actual = research_model_adapter.prepare_research_candidates
        def mutate(*args, **kwargs):
            prepared = actual(*args, **kwargs)
            (self.root / 'features/road-source.txt').write_bytes(b'changed after training gate')
            return prepared
        with patch.object(research_model_adapter, 'prepare_research_candidates', side_effect=mutate):
            result = self.call()
        self.assertEqual(result['stages'][0]['status'], 'FAIL')
        self.assertEqual(result['candidates'], [])
        self.assertEqual(result['replay'], [])

    def test_one_read_ledger_and_deadline_span_both_gates_and_no_partial_replay(self):
        from prospective_inputs import ProspectiveReadContext
        context = ProspectiveReadContext(30, 10)
        result = self.call(_read_context=context)
        self.assertEqual(result['stages'][0]['blocker_kind'], 'RUNTIME_BLOCKED')
        self.assertEqual(result['candidates'], [])
        self.assertEqual(result['replay'], [])
        self.assertGreater(context.bytes_read, 10)

    def test_final_stage_construction_cannot_release_candidates_after_expiry(self):
        import research_pdca_adapter as adapter
        from prospective_inputs import ProspectiveReadContext
        context = ProspectiveReadContext(300, 2 * 1024**3)
        actual = adapter.stage
        def expire(name, *args, **kwargs):
            value = actual(name, *args, **kwargs)
            if name == 'candidate_validation':
                context.deadline = 0
            return value
        with patch.object(adapter, 'stage', side_effect=expire):
            result = self.call(_read_context=context)
        self.assertEqual(result['candidates'], [])
        self.assertEqual(result['replay'], [])
        self.assertTrue(all(s['status'] == 'BLOCKED' for s in result['stages']))

    @unittest.skipIf(os.name == 'nt', 'Actual master lock requires POSIX fcntl; Ubuntu CI executes this test')
    def test_master_dispatch_uses_request_before_legacy_builder_in_actual_snapshot(self):
        from master_orchestrator import run_master
        with patch('learning_snapshot.build_learning_snapshot', side_effect=AssertionError('legacy builder reached')):
            result = run_master(self.root, NIGHT)
        candidates = next(s for s in result['stages'] if s['name'] == 'candidate_generation')
        self.assertEqual(candidates['status'], 'PASS', str(result))
        self.assertFalse(result['completed'])
        self.assertNotEqual(result['overall_status'], 'PASS')


if __name__ == '__main__':
    unittest.main()
