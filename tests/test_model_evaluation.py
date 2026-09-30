import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from master_contracts import file_hash


class ModelEvaluationTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('model_evaluation'), 'bounded evaluation is missing')
        import model_evaluation
        self.module = model_evaluation
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def write(self, path, value):
        p = self.root/path
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(value, sort_keys=True))
        return p

    def fixture(self, count=3):
        source = self.write('evidence/observations.json', {'audit': 'fixture'})
        source_ref = {'path': 'evidence/observations.json', 'sha256': file_hash(source),
                      'available_at': '2026-01-01T00:00:00+09:00', 'role': 'label'}
        feature_source = self.write('features/input_features.json', {'source': 'fixture covariates'})
        feature_ref = {'path': 'features/input_features.json', 'sha256': file_hash(feature_source),
                       'available_at': '2026-01-01T00:00:00+09:00', 'role': 'feature'}
        universe = {'schema_version': '1.0', 'source_type': 'EX_ANTE_FORECAST',
                    'geographic_domain': {'crs': 'EPSG:32652', 'description': 'fixture domain'}, 'rows': []}
        rows = []
        for day in range(1, count+1):
            night = f'2026-09-{day:02d}'
            for area in range(12):
                row_id = f'{night}-{area}'
                x, y = 400000 + area*1000 + 50, 3000050
                universe['rows'].append({'row_id': row_id, 'operational_night': night,
                    'cutoff_time': night+'T19:00:00+09:00', 'window_start_jst': night+'T20:00:00+09:00',
                    'utm_x_m': x, 'utm_y_m': y})
                positive = area == 11
                rows.append({'row_id': row_id, 'universe_row_id': row_id, 'operational_night': night,
                    'cutoff_time': night+'T19:00:00+09:00', 'window_start_jst': night+'T20:00:00+09:00',
                    'label_available_at': night+'T23:00:00+09:00', 'cell_x': int(x//100), 'cell_y': int(y//100),
                    'observed': True, 'label': int(positive), 'capture_count': 3 if positive else 0,
                    'capture_event_ids': [row_id+'-capture'] if positive else [],
                    'features': {'temperature': float(area)},
                    'feature_available_at': {'temperature': '2026-08-01T00:00:00+09:00'},
                    'quality': 'AUDITED_OBSERVED',
                    'source_refs': ['evidence/observations.json', 'features/input_features.json'],
                    'feature_source_refs': {'temperature': ['features/input_features.json']}})
        up = self.write('features/forecast_universe.json', universe)
        protocol = {'schema_version': '1.0', 'frozen_at': '2026-08-01T00:00:00+09:00',
                    'research_used_nights': sorted({r['operational_night'] for r in rows}),
                    'confirmation_used_nights': [],
                    'registered_candidates': ['uniform', 'historical_capture_prior', 'observed_unit_prevalence']}
        pp = self.write('protocols/model_evaluation.json', protocol)
        snapshot = {'schema_version': '1.0', 'candidate_universe_sha256': file_hash(up),
                    'universe': {'path': 'features/forecast_universe.json', 'sha256': file_hash(up), 'available_at': '2026-08-01T00:00:00+09:00'},
                    'protocol': {'path': 'protocols/model_evaluation.json', 'sha256': file_hash(pp), 'available_at': '2026-08-01T00:00:00+09:00'},
                    'source_manifest': [source_ref, feature_ref], 'rows': rows}
        self.write('data/processed/model_learning.json', snapshot)
        return snapshot, universe, protocol

    def evaluate(self, budget=300):
        return self.module.evaluate_models(self.root, '2026-09-30', budget)

    def update_snapshot(self, snapshot):
        self.write('data/processed/model_learning.json', snapshot)

    def test_absent_snapshot_has_all_contract_stages_and_specific_blocker(self):
        result = self.evaluate()
        self.assertEqual({s['name'] for s in result['stages']}, {'model_evaluation', 'feature_research', 'candidate_generation', 'candidate_validation'})
        self.assertTrue(result['data_blockers'])
        self.assertEqual(result['decision']['decision'], 'NEED_MORE_DATA')
        self.assertFalse(result['folds'])
        self.assertTrue(all(s['blocker_kind'] == 'DATA_BLOCKED' for s in result['stages']))

    def test_reproducible_real_comparison_and_immutable_replay(self):
        self.fixture()
        a = self.evaluate()
        b = self.evaluate()
        self.assertEqual(a, b)
        self.assertEqual(len(a['folds']), 6)
        folds = {f['family']: f for f in a['folds'] if f['night'] == '2026-09-02'}
        self.assertEqual(folds['uniform']['metrics']['stage1']['restricted_individual_recall'], 0.0)
        self.assertEqual(folds['observed_unit_prevalence']['metrics']['stage1']['restricted_individual_recall'], 1.0)
        # One observation per area with Beta(1,1) smoothing gives 1/3 or 2/3, hence Brier 1/9.
        self.assertAlmostEqual(folds['observed_unit_prevalence']['metrics']['brier'], 1/9)
        self.assertEqual({tuple(f['test_row_ids']) for f in folds.values()}.__len__(), 1)
        self.assertEqual(a['decision']['decision'], 'REJECT_CANDIDATE')
        self.assertTrue(a['implementation_blockers'])
        for replay in a['replay']:
            self.assertEqual(file_hash(self.root/replay['path']), replay['sha256'])
        self.assertFalse((self.root/'predictions/original').exists())

    def test_feature_at_cutoff_or_future_invalidates_evaluation(self):
        for timestamp in ('2026-09-01T19:00:00+09:00', '2026-10-01T00:00:00+09:00'):
            snapshot, _, _ = self.fixture()
            snapshot['rows'][0]['feature_available_at']['temperature'] = timestamp
            self.update_snapshot(snapshot)
            result = self.evaluate()
            self.assertEqual(result['stages'][0]['status'], 'FAIL')
            self.assertIn('availability', str(result).lower())
            self.assertFalse(result['folds'])

    def test_future_training_labels_are_excluded_not_leaked(self):
        snapshot, _, _ = self.fixture()
        for row in snapshot['rows']:
            if row['operational_night'] == '2026-09-01':
                row['label_available_at'] = '2026-09-02T19:00:00+09:00'
        self.update_snapshot(snapshot)
        result = self.evaluate()
        self.assertFalse(any(f['night'] == '2026-09-02' for f in result['folds']))
        self.assertIn('training', str(result).lower())

    def test_unknown_label_is_not_negative(self):
        snapshot, _, _ = self.fixture()
        row = snapshot['rows'][12]
        row.update(observed=False, label=None, capture_count=0, capture_event_ids=[])
        self.update_snapshot(snapshot)
        result = self.evaluate()
        fold = next(f for f in result['folds'] if f['night'] == '2026-09-02')
        self.assertEqual(fold['metrics']['observed_units'], 11)
        self.assertEqual(len(fold['predictions']), 12)
        row['label'] = 0
        self.update_snapshot(snapshot)
        self.assertEqual(self.evaluate()['stages'][0]['status'], 'FAIL')

    def test_conflicting_units_nonfinite_features_and_reused_events_fail(self):
        for mutation in ('collision', 'nan', 'event'):
            snapshot, _, _ = self.fixture()
            if mutation == 'collision':
                snapshot['rows'].append(dict(snapshot['rows'][0], row_id='duplicate'))
            elif mutation == 'nan':
                snapshot['rows'][0]['features']['temperature'] = float('nan')
            else:
                snapshot['rows'][0].update(label=1, capture_count=1, capture_event_ids=snapshot['rows'][11]['capture_event_ids'])
            self.update_snapshot(snapshot)
            self.assertEqual(self.evaluate()['stages'][0]['status'], 'FAIL')

    def test_missing_universe_and_tampered_source_fail_closed(self):
        snapshot, _, _ = self.fixture()
        (self.root/'features/forecast_universe.json').unlink()
        self.assertEqual(self.evaluate()['stages'][0]['status'], 'BLOCKED')
        snapshot, _, _ = self.fixture()
        (self.root/'evidence/observations.json').write_text('{}')
        self.assertEqual(self.evaluate()['stages'][0]['status'], 'FAIL')

    def test_zero_capture_night_has_null_recall(self):
        snapshot, _, _ = self.fixture()
        for row in snapshot['rows']:
            if row['operational_night'] == '2026-09-02':
                row.update(label=0, capture_count=0, capture_event_ids=[])
        self.update_snapshot(snapshot)
        fold = next(f for f in self.evaluate()['folds'] if f['night'] == '2026-09-02')
        self.assertIsNone(fold['metrics']['stage1']['restricted_individual_recall'])
        self.assertNotEqual(fold['metrics']['stage1']['status'], 'PASS')

    def test_predict_model_executes_fitted_parameters_and_rejects_unknown_family(self):
        _, universe, _ = self.fixture()
        result = self.evaluate()
        models = {f['family']: f['model'] for f in result['folds'] if f['night'] == '2026-09-02'}
        a = self.module.predict_model(models['uniform'], universe['rows'][12:24])
        b = self.module.predict_model(models['observed_unit_prevalence'], universe['rows'][12:24])
        self.assertNotEqual(a, b)
        bad = dict(models['uniform'], family='arbitrary_code')
        with self.assertRaises(ValueError):
            self.module.predict_model(bad, universe['rows'][12:24])

    def test_no_time_targets_or_effort_claims_in_prevalence(self):
        self.fixture()
        result = self.evaluate()
        for fold in result['folds']:
            self.assertEqual(fold['metrics']['formal_100m_10min']['status'], 'NOT_PRODUCED')
        self.assertIn('measured', str(result).lower())
        self.assertIn('NOT_VALIDATED', str(result))

    def test_budget_exhaustion_is_explicit(self):
        self.fixture()
        result = self.evaluate(0)
        self.assertIn('BUDGET_EXHAUSTED', str(result))
        self.assertFalse(result['folds'])

    def replace_protocol(self, snapshot, protocol):
        path = self.write('protocols/model_evaluation.json', protocol)
        snapshot['protocol']['sha256'] = file_hash(path)
        self.update_snapshot(snapshot)

    def test_confirmation_rows_excluded_and_overlap_rejected(self):
        snapshot, _, protocol = self.fixture(4)
        protocol['research_used_nights'].remove('2026-09-04')
        protocol['confirmation_used_nights'] = ['2026-09-04']
        self.replace_protocol(snapshot, protocol)
        result = self.evaluate()
        self.assertFalse(any(f['night'] == '2026-09-04' for f in result['folds']))
        self.assertFalse(result['evidence']['confirmation_labels_used'])
        protocol['research_used_nights'].append('2026-09-04')
        self.replace_protocol(snapshot, protocol)
        self.assertEqual(self.evaluate()['stages'][0]['status'], 'FAIL')

    def test_duration_rate_requires_measured_denominator_and_has_no_fake_probability(self):
        snapshot, _, protocol = self.fixture()
        protocol['registered_candidates'][-1] = 'duration_normalized_area_rate'
        protocol['effort_reference_seconds'] = 600
        self.replace_protocol(snapshot, protocol)
        missing = self.evaluate()
        self.assertFalse(any(f['family'] == 'duration_normalized_area_rate' for f in missing['folds']))
        for row in snapshot['rows']:
            row.update(duration_seconds=600, distance_m=100, effort_method='timed_search', observer_version='fixture-v1')
        self.replace_protocol(snapshot, protocol)
        result = self.evaluate()
        rate = next(f for f in result['folds'] if f['family'] == 'duration_normalized_area_rate')
        self.assertIsNone(rate['metrics']['brier'])
        self.assertTrue(all(p['probability'] is None for p in rate['predictions']))

    def test_250m_aggregation_uses_exact_coordinates(self):
        snapshot, universe, _ = self.fixture()
        for unit in universe['rows']:
            if unit['row_id'].endswith('-0'):
                unit['utm_x_m'] += 249
        for row in snapshot['rows']:
            if row['row_id'].endswith('-0'):
                row['cell_x'] += 2
        path = self.write('features/forecast_universe.json', universe)
        snapshot['universe']['sha256'] = snapshot['candidate_universe_sha256'] = file_hash(path)
        self.update_snapshot(snapshot)
        fold = next(f for f in self.evaluate()['folds'] if f['family'] == 'uniform')
        self.assertIn('1601,12000', fold['metrics']['spatial_250m']['top10'])

    def test_individual_recall_distinct_from_event_recall(self):
        snapshot, _, _ = self.fixture()
        for row in snapshot['rows']:
            if row['row_id'] == '2026-09-02-0':
                row.update(label=1, capture_count=1, capture_event_ids=['one'])
        self.update_snapshot(snapshot)
        fold = next(f for f in self.evaluate()['folds'] if f['night'] == '2026-09-02' and f['family'] == 'uniform')
        self.assertEqual(fold['metrics']['stage1']['restricted_individual_recall'], 0.25)
        self.assertEqual(fold['metrics']['stage1']['restricted_event_recall'], 0.5)

    def test_source_availability_cannot_be_backdated_by_learning_row(self):
        snapshot, _, _ = self.fixture()
        snapshot['source_manifest'][0]['available_at'] = '2026-09-30T00:00:00+09:00'
        self.update_snapshot(snapshot)
        self.assertEqual(self.evaluate()['stages'][0]['status'], 'FAIL')

    def test_future_test_labels_not_consumed_in_research_or_metrics(self):
        snapshot, _, _ = self.fixture()
        for row in snapshot['rows']:
            if row['operational_night'] == '2026-09-03':
                row['label_available_at'] = '2027-01-01T00:00:00+09:00'
        self.update_snapshot(snapshot)
        result = self.evaluate()
        self.assertFalse(any(f['night'] == '2026-09-03' for f in result['folds']))
        self.assertTrue(all(a['observed_units'] == 24 for a in result['associations']))

    def test_positive_research_comparison_still_cannot_promote(self):
        self.fixture(8)
        result = self.evaluate()
        candidate = next(c for c in result['candidates'] if c['family'] == 'observed_unit_prevalence')
        self.assertGreater(candidate['comparison']['mean_brier_improvement'], 0)
        self.assertEqual(candidate['comparison']['uncertainty']['draws'], 2000)
        self.assertEqual(candidate['comparison']['uncertainty']['scope'], 'RESEARCH_DIAGNOSTIC')
        self.assertEqual(result['decision']['decision'], 'NEED_MORE_DATA')
        self.assertNotEqual(result['stages'][-1]['status'], 'PASS')
        self.assertIn('feature_mean_shift', result['folds'][0]['drift'])

    def test_midrun_source_change_invalidates_model_evidence(self):
        self.fixture()
        original = self.module.predict_model
        def mutate(model, rows):
            result = original(model, rows)
            (self.root/'evidence/observations.json').write_text('{"changed":true}')
            return result
        with patch.object(self.module, 'predict_model', mutate):
            result = self.evaluate()
        self.assertEqual(result['stages'][0]['status'], 'FAIL')
        self.assertEqual(result['decision']['decision'], 'REJECT_CANDIDATE')

    def test_existing_replay_cannot_be_overwritten(self):
        self.fixture()
        first = self.evaluate()
        path = self.root/first['replay'][0]['path']
        path.write_text('{"tampered":true}')
        self.assertEqual(self.evaluate()['stages'][0]['status'], 'FAIL')
        self.assertEqual(path.read_text(), '{"tampered":true}')

    def test_upstream_failure_and_unknown_quality_cannot_validate_learning(self):
        snapshot, _, _ = self.fixture()
        snapshot['upstream_status'] = 'FAIL'
        self.update_snapshot(snapshot)
        self.assertEqual(self.evaluate()['stages'][0]['status'], 'FAIL')
        snapshot.pop('upstream_status')
        snapshot['rows'][0]['quality'] = 'UNKNOWN'
        self.update_snapshot(snapshot)
        self.assertEqual(self.evaluate()['stages'][0]['status'], 'BLOCKED')

    def test_forecast_inference_rejects_model_trained_after_forecast_cutoff(self):
        from master_contracts import digest
        _, universe, _ = self.fixture()
        model = dict(self.evaluate()['folds'][0]['model'])
        model['training_cutoff'] = '2026-10-01T00:00:00+09:00'
        body = {k: v for k, v in model.items() if k not in ('model_id', 'model_sha256')}
        model['model_id'] = model['model_sha256'] = digest(body)
        with self.assertRaises(ValueError):
            self.module.predict_model(model, universe['rows'][12:24])

    def test_output_completion_ledger_does_not_rename_spatial_predictions(self):
        self.fixture()
        result = self.evaluate()
        self.assertEqual(result.get('output_status', {}).get('formal_100m_10min', {}).get('status'), 'NOT_PRODUCED')
        self.assertEqual(result['output_status']['routes']['status'], 'BLOCKED')
        self.assertEqual(result['output_status']['feature_ablation']['status'], 'NOT_VALIDATED')

    def test_heldout_labels_do_not_change_fitted_parameters(self):
        snapshot, _, _ = self.fixture()
        before = self.evaluate()
        models = {f['family']: f['model'] for f in before['folds'] if f['night'] == '2026-09-02'}
        for row in snapshot['rows']:
            if row['operational_night'] == '2026-09-02':
                row.update(label=0, capture_count=0, capture_event_ids=[])
        self.update_snapshot(snapshot)
        after = self.evaluate()
        self.assertEqual(models, {f['family']: f['model'] for f in after['folds'] if f['night'] == '2026-09-02'})

    def test_fitted_manifest_records_registered_hyperparameters_and_lineage(self):
        self.fixture()
        model = self.evaluate()['folds'][0]['model']
        required = {'model_id', 'family', 'hyperparameters', 'model_sha256', 'feature_schema_sha256',
                    'training_data_sha256', 'training_cutoff', 'code_sha256', 'protocol_sha256',
                    'evidence_refs', 'status', 'produced_outputs'}
        self.assertTrue(required <= model.keys())
        self.assertEqual(model['status'], 'CANDIDATE')
        self.assertEqual(model['hyperparameters']['smoothing'], 1.0)

    def test_registered_candidates_share_identical_eligible_fold_set(self):
        snapshot, _, protocol = self.fixture()
        protocol['registered_candidates'][-1] = 'duration_normalized_area_rate'
        protocol['effort_reference_seconds'] = 600
        self.replace_protocol(snapshot, protocol)
        result = self.evaluate()
        fold_sets = [tuple(c['fold_nights']) for c in result['candidates']]
        self.assertEqual(len(set(fold_sets)), 1)

    def test_missing_invalid_or_wrong_source_role_cannot_bypass_label_availability(self):
        for role in (None, 'unknown', 'protocol'):
            with self.subTest(role=role):
                snapshot, _, _ = self.fixture()
                source = snapshot['source_manifest'][0]
                source['available_at'] = '2027-01-01T00:00:00+09:00'
                if role is None:
                    source.pop('role')
                else:
                    source['role'] = role
                self.update_snapshot(snapshot)
                result = self.evaluate()
                self.assertIn(result['stages'][0]['status'], ('BLOCKED', 'FAIL'))
                self.assertFalse(result['folds'])

    def test_features_require_bound_source_and_cannot_predate_it(self):
        snapshot, _, _ = self.fixture()
        for row in snapshot['rows']:
            row.pop('feature_source_refs', None)
        self.update_snapshot(snapshot)
        missing = self.evaluate()
        self.assertEqual(missing['stages'][0]['status'], 'BLOCKED')
        self.assertIn('feature', str(missing).lower())
        self.assertFalse(missing['folds'])
        snapshot, _, _ = self.fixture()
        source = self.write('features/late_features.json', {'temperature': 10})
        snapshot['source_manifest'].append({'path': 'features/late_features.json', 'sha256': file_hash(source),
            'available_at': '2026-08-15T00:00:00+09:00', 'role': 'feature'})
        for row in snapshot['rows']:
            row['feature_source_refs'] = {'temperature': ['features/late_features.json']}
            row['source_refs'].append('features/late_features.json')
        self.update_snapshot(snapshot)
        late = self.evaluate()
        self.assertEqual(late['stages'][0]['status'], 'FAIL')
        self.assertFalse(late['folds'])

    def test_canonical_capture_event_cannot_reappear_in_another_night(self):
        snapshot, _, _ = self.fixture()
        for row in snapshot['rows']:
            if row['label'] == 1:
                row['capture_event_ids'] = ['same-confirmed-event']
        self.update_snapshot(snapshot)
        result = self.evaluate()
        self.assertEqual(result['stages'][0]['status'], 'FAIL')
        self.assertFalse(result['folds'])

    def test_genuinely_unknown_row_needs_no_observation_timestamp_or_quality(self):
        snapshot, _, _ = self.fixture()
        row = snapshot['rows'][12]
        row.update(observed=False, label=None, capture_count=0, capture_event_ids=[],
                   quality='UNKNOWN', label_available_at=None)
        row['source_refs'].remove('evidence/observations.json')
        self.update_snapshot(snapshot)
        result = self.evaluate()
        self.assertNotIn(result['stages'][0]['status'], ('BLOCKED', 'FAIL'))
        fold = next(f for f in result['folds'] if f['night'] == '2026-09-02')
        self.assertEqual(fold['metrics']['observed_units'], 11)
        self.assertEqual(len(fold['predictions']), 12)
        self.assertNotIn(row['row_id'], next(f for f in result['folds'] if f['night'] == '2026-09-03')['train_row_ids'])

    def test_malformed_snapshot_root_always_returns_four_fail_stages(self):
        for value in ([], None, 42):
            with self.subTest(value=value):
                self.write('data/processed/model_learning.json', value)
                result = self.evaluate()
                self.assertEqual(len(result['stages']), 4)
                self.assertTrue(all(s['status'] == 'FAIL' for s in result['stages']))
                self.assertIn('INVALID_MODEL_EVIDENCE', str(result))

    def test_restricted_universe_recall_cannot_pass_full_stage1_gate(self):
        self.fixture()
        result = self.evaluate()
        for fold in result['folds']:
            metric = fold['metrics']['stage1']
            self.assertEqual(metric['gate_outcome'], 'NOT_EVALUATED')
            self.assertEqual(metric.get('denominator_coverage'), 'NOT_ESTABLISHED')
            self.assertEqual(metric.get('scope'), 'OBSERVED_UNITS_WITHIN_FORECAST_UNIVERSE')
            self.assertIn('restricted_individual_recall', metric)
