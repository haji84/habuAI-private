"""Synthetic development diagnostics, never real source/confirmation evidence."""
import copy
import hashlib
import importlib
import importlib.util
import json
import math
import socket
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from tests.test_research_selection import selection_fixture, insufficient_fixture, bind_selection


def sha(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
        separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def fixture(selection=None):
    selection = selection_fixture() if selection is None else selection
    folds = [dict(night=night, model_sha256='d' * 64,
        training_selection_sha256='e' * 64, training_cutoff='2026-08-31T18:00:00+09:00',
        train_nights=['2026-08-31']) for night in sorted({r['night'] for r in selection['accepted']})]
    probabilities = [0, .25, .5, .75, 1, .8]
    predictions = [dict({key: row[key] for key in ('row_id', 'night', 'cell_x', 'cell_y', 'window_start_jst')},
        probability=probabilities[i], model_sha256='d' * 64, training_selection_sha256='e' * 64)
        for i, row in enumerate(selection['accepted'])]
    protocol = dict(schema_version='habu-feature-candidate-development-protocol-v1', phase='DEVELOPMENT',
        target='OWNER_CAPTURE_BINARY_ON_AUDITED_OBSERVED_100M_600S_UNITS',
        evaluation_selection_sha256=selection['selection_sha256'], predictions_sha256=sha(predictions),
        bin_edges=[0, .25, .5, .75, 1], log_loss_clip=1e-6, folds=folds)
    return protocol, selection, predictions


class FeatureCandidateDiagnosticsTests(unittest.TestCase):
    def setUp(self):
        spec = importlib.util.find_spec('models.feature_candidate_diagnostics')
        self.assertIsNotNone(spec, 'pure feature candidate development diagnostic is missing')
        self.module = importlib.import_module('models.feature_candidate_diagnostics')
        self.protocol, self.selection, self.predictions = fixture()

    def call(self, **kwargs):
        return self.module.describe_feature_candidate_development(self.protocol, self.selection,
            self.predictions, expected_protocol_sha256=sha(self.protocol), **kwargs)

    def rebind(self):
        bind_selection(self.selection)
        self.protocol['evaluation_selection_sha256'] = self.selection['selection_sha256']
        self.protocol['predictions_sha256'] = sha(self.predictions)

    def test_actual_brier_log_loss_bins_and_no_authority(self):
        result = self.call()
        self.assertEqual(result['status'], 'DESCRIPTIVE_DEVELOPMENT_DIAGNOSTIC_ONLY')
        self.assertEqual([b['count'] for b in result['pooled_reliability_bins']], [1, 1, 1, 3])
        self.assertAlmostEqual(result['mean_night_brier'], (1 + .25**2 + .5**2 + .75**2 + 1 + .2**2) / 6)
        self.assertAlmostEqual(result['mean_night_log_loss'], sum(
            -math.log(max(1e-6, min(1-1e-6, p if r['label'] else 1-p)))
            for p, r in zip([0, .25, .5, .75, 1, .8], self.selection['accepted'])) / 6)
        self.assertEqual(result['calibration_status'], 'NOT_VALIDATED')
        self.assertEqual(result['statistical_adequacy'], 'NOT_ASSESSED')
        self.assertEqual(result['source_authentication'], 'CALLER_DEPENDENCY_REQUIRED')
        self.assertEqual(result['source_authenticity'], 'NOT_ATTESTED')
        self.assertEqual(result['preregistration'], 'CALLER_DEPENDENCY_REQUIRED')
        for field in ('fit_authorized', 'selection_authorized', 'promotion_authorized',
                      'scientific_execution_authorized', 'official_issuance_authorized', 'production_authorized'):
            self.assertIs(result[field], False)
        self.assertNotIn('candidates', result)
        self.assertNotIn('model', result)
        self.assertIn('HB_A1_COMMON_ADAPTER_NOT_IMPLEMENTED', result['implementation_blockers'])
        self.assertIn('TRUE_TRAIN_ONLY_RETRAINED_ABLATION_NOT_IMPLEMENTED', result['implementation_blockers'])

    def test_empty_bins_are_unknown_and_internal_edges_belong_to_right_bin(self):
        for row in self.predictions:
            row['probability'] = 1
        self.rebind()
        result = self.call()
        for item in result['pooled_reliability_bins'][:-1]:
            self.assertEqual(item['count'], 0)
            self.assertIsNone(item['mean_probability'])
            self.assertIsNone(item['observed_fraction'])
        self.assertEqual(result['pooled_reliability_bins'][-1]['count'], 6)

    def test_per_night_mean_is_not_pooled_unit_mean(self):
        # First night: 0 Brier on one unit; later nights: 1 on two units each.
        removed = self.selection['accepted'].pop(1)
        self.predictions = [p for p in self.predictions if p['row_id'] != removed['row_id']]
        self.selection['counts'].update(accepted_rows=5, positives=3, negatives=2)
        for p, r in zip(self.predictions, self.selection['accepted']):
            p['probability'] = r['label'] if r['night'].endswith('01') else 1-r['label']
        self.rebind()
        result = self.call()
        self.assertAlmostEqual(result['mean_night_brier'], 2/3)
        self.assertAlmostEqual(result['pooled_unit_brier'], 4/5)
        self.assertEqual(sum(b['count'] for b in result['pooled_reliability_bins']), 5)

    def test_valid_known_labels_are_described_despite_selector_readiness_blockers(self):
        self.protocol, self.selection, self.predictions = fixture(insufficient_fixture(positive_only=True))
        result = self.call()
        self.assertEqual(result['status'], 'DESCRIPTIVE_DEVELOPMENT_DIAGNOSTIC_ONLY')
        self.assertEqual(result['evaluation_selection_status'], 'NEED_MORE_DATA')
        self.assertEqual(result['evaluation_selection_blockers'], self.selection['blockers'])
        self.assertEqual(result['observed_units'], 3)
        self.assertEqual(result['statistical_adequacy'], 'NOT_ASSESSED')

    def test_zero_rows_return_need_more_data_without_invented_averages(self):
        self.protocol, self.selection, self.predictions = fixture(insufficient_fixture())
        result = self.call()
        self.assertEqual(result['status'], 'NEED_MORE_DATA')
        self.assertEqual(result['per_night'], [])
        self.assertIsNone(result['mean_night_brier'])
        self.assertIsNone(result['mean_night_log_loss'])
        self.assertIsNone(result['pooled_unit_brier'])

    def test_exact_all_selected_units_no_missing_extra_or_duplicate_predictions(self):
        for kind in ('missing', 'extra', 'duplicate', 'cell', 'window', 'night', 'row_id'):
            with self.subTest(kind=kind):
                self.protocol, self.selection, self.predictions = fixture()
                if kind == 'missing': self.predictions.pop()
                elif kind == 'extra': self.predictions.append(dict(self.predictions[0], row_id='extra'))
                elif kind == 'duplicate': self.predictions[-1] = dict(self.predictions[0])
                elif kind == 'cell': self.predictions[0]['cell_x'] += 1
                elif kind == 'window': self.predictions[0]['window_start_jst'] = '2026-09-01T20:10:00+09:00'
                elif kind == 'night': self.predictions[0]['night'] = '2026-09-02'
                else: self.predictions[0]['row_id'] = 'unbound'
                self.rebind()
                with self.assertRaises(ValueError): self.call()

    def test_timezone_equivalent_prediction_window_is_same_physical_unit(self):
        self.predictions[0]['window_start_jst'] = '2026-09-01T11:00:00Z'
        self.rebind()
        self.assertEqual(self.call()['observed_units'], 6)

    def test_invalid_probability_and_unknown_label_never_become_zero(self):
        for value in (True, None, '0.2', -.1, 1.1, float('nan'), float('inf')):
            with self.subTest(value=value):
                self.protocol, self.selection, self.predictions = fixture()
                self.predictions[0]['probability'] = value
                with self.assertRaises(ValueError): self.call()
        for value in (None, True, 2):
            self.protocol, self.selection, self.predictions = fixture()
            self.selection['accepted'][0]['label'] = value
            self.rebind()
            with self.assertRaises(ValueError): self.call()

    def test_protocol_and_prediction_content_digests_are_enforced(self):
        expected = sha(self.protocol)
        self.protocol['log_loss_clip'] = .01
        with self.assertRaises(ValueError):
            self.module.describe_feature_candidate_development(self.protocol, self.selection,
                self.predictions, expected_protocol_sha256=expected)
        self.protocol, self.selection, self.predictions = fixture()
        self.predictions[0]['probability'] = .1
        with self.assertRaises(ValueError): self.call()
        self.rebind()
        self.protocol['evaluation_selection_sha256'] = 'f'*64
        with self.assertRaises(ValueError): self.call()

    def test_protocol_bin_edges_and_clipping_are_strict(self):
        for edges in ([.1, 1], [0, .9], [0, .5, .5, 1], [0, 1, .5], [False, 1], [0, '1'], [0, 1.1]):
            self.protocol, self.selection, self.predictions = fixture()
            self.protocol['bin_edges'] = edges
            with self.assertRaises(ValueError): self.call()
        for epsilon in (0, .5, True, '0.01', 1e-20):
            self.protocol, self.selection, self.predictions = fixture()
            self.protocol['log_loss_clip'] = epsilon
            with self.assertRaises(ValueError): self.call()

    def test_fold_temporal_boundaries_valid_unique_train_nights(self):
        for field, value in (('night', '2026-09-02'), ('training_cutoff', '2026-09-01T07:00:00+09:00'),
                ('training_cutoff', '2026-08-31T07:00:00+09:00'),
                ('train_nights', ['2026-09-01']), ('train_nights', ['2026-08-31', '2026-08-31']),
                ('train_nights', ['2026-08-32']), ('train_nights', ['2026-08-31', '2026-08-30'])):
            self.protocol, self.selection, self.predictions = fixture()
            self.protocol['folds'][0][field] = value
            with self.assertRaises(ValueError): self.call()

    def test_partial_training_night_and_same_model_across_nights_are_legal_declarations(self):
        self.assertEqual(self.call()['evaluation_nights'], 3)

    def test_timestamp_utc_overflow_is_an_invalid_contract_value(self):
        self.protocol['folds'][0]['training_cutoff'] = '0001-01-01T00:00:00+09:00'
        with self.assertRaises(ValueError): self.call()

    def test_model_and_training_selection_bindings_cannot_conflict(self):
        for kind in ('model', 'selection', 'samehashconflict', 'evaluationselftrain', 'missingfold', 'duplicatefold'):
            self.protocol, self.selection, self.predictions = fixture()
            if kind == 'model': self.predictions[0]['model_sha256'] = 'a'*64
            elif kind == 'selection': self.predictions[0]['training_selection_sha256'] = 'a'*64
            elif kind == 'samehashconflict': self.protocol['folds'][1]['training_cutoff'] = '2026-08-31T17:00:00+09:00'
            elif kind == 'evaluationselftrain': self.protocol['folds'][0]['training_selection_sha256'] = self.selection['selection_sha256']
            elif kind == 'missingfold': self.protocol['folds'].pop()
            else: self.protocol['folds'].append(dict(self.protocol['folds'][0]))
            self.rebind()
            with self.assertRaises(ValueError): self.call()

    def test_confirmation_or_unknown_fields_are_rejected_and_result_cannot_enter_adapter(self):
        for kind in ('phase', 'protocolflag', 'rowlabel', 'foldflag'):
            self.protocol, self.selection, self.predictions = fixture()
            if kind == 'phase': self.protocol['phase'] = 'CONFIRMATION'
            elif kind == 'protocolflag': self.protocol['trusted_freeze'] = True
            elif kind == 'rowlabel': self.predictions[0]['label'] = 1
            else: self.protocol['folds'][0]['promotable'] = True
            self.rebind()
            with self.assertRaises(ValueError): self.call()
        self.protocol, self.selection, self.predictions = fixture()
        from models.occupancy_shrinkage import predict_shrinkage
        with self.assertRaises(ValueError): predict_shrinkage(self.call(), [], cutoff_time='2026-10-14T18:00:00+09:00', universe_sha256='a'*64)

    def test_selector_event_and_physical_unit_duplicate_rules_preserved(self):
        for kind in ('event', 'unit'):
            self.protocol, self.selection, self.predictions = fixture()
            if kind == 'event': self.selection['accepted'][2]['capture_event_ids'] = list(self.selection['accepted'][0]['capture_event_ids'])
            else: self.selection['accepted'][1]['cell_x'] = self.selection['accepted'][0]['cell_x']
            self.rebind()
            with self.assertRaises(ValueError): self.call()

    def test_inputs_are_owned_and_results_are_digest_sealed_without_aliases(self):
        before = copy.deepcopy((self.protocol, self.selection, self.predictions))
        result = self.call()
        self.assertEqual((self.protocol, self.selection, self.predictions), before)
        digest = result.pop('diagnostic_sha256')
        self.assertEqual(digest, sha(result))
        self.protocol['bin_edges'][1] = .1
        self.selection['blockers'].append('changed')
        self.assertEqual(result['pooled_reliability_bins'][0]['upper'], .25)
        self.assertEqual(result['evaluation_selection_blockers'], [])

    def test_caller_mutation_after_snapshot_cannot_change_owned_computation(self):
        real = self.module.validate_selection
        def mutate(value):
            result = real(value)
            self.protocol['bin_edges'][1] = .1
            self.predictions[0]['probability'] = 1
            self.selection['accepted'][0]['label'] = 0
            return result
        with patch.object(self.module, 'validate_selection', side_effect=mutate):
            result = self.call()
        self.assertEqual(result['pooled_reliability_bins'][0]['count'], 1)
        self.assertEqual(result['pooled_reliability_bins'][0]['observed_fraction'], 1)

    def test_no_file_network_fit_rank_or_sealed_read(self):
        import prospective_candidate_model as learner
        with patch('builtins.open', side_effect=AssertionError('file read')), \
                patch.object(Path, 'open', side_effect=AssertionError('path read')), \
                patch.object(socket, 'socket', side_effect=AssertionError('network')), \
                patch.object(learner, 'train_candidate', side_effect=AssertionError('fit')), \
                patch.object(learner, 'rank_future', side_effect=AssertionError('rank')):
            self.assertEqual(self.call()['observed_units'], 6)

    def test_budget_validation_and_cooperative_cancellation(self):
        for budget in (True, 0, -1, 301, 10**1000, float('nan'), float('inf'), '30'):
            with self.subTest(budget=str(budget)[:20]):
                with self.assertRaises(ValueError): self.call(budget_seconds=budget)
        def cancel(): raise TimeoutError('parent expired')
        with self.assertRaises(TimeoutError): self.call(check=cancel)
        with patch.object(self.module, 'monotonic', side_effect=[0, 30]):
            with self.assertRaises(TimeoutError): self.call()

    def test_deadline_after_final_digest_cannot_return_success(self):
        clock = [0]
        real = self.module._digest
        def digest(value, check):
            result = real(value, check)
            if type(value) is dict and value.get('schema_version') == 'habu-feature-candidate-development-diagnostic-v1':
                clock[0] = 301
            return result
        with patch.object(self.module, 'monotonic', side_effect=lambda: clock[0]), \
                patch.object(self.module, '_digest', side_effect=digest):
            with self.assertRaises(TimeoutError): self.call()

    def test_input_capacity_is_enforced_before_copy_or_validator(self):
        for constant in ('MAX_JSON_BYTES', 'MAX_JSON_NODES', 'MAX_ROWS', 'MAX_NIGHTS', 'MAX_BINS'):
            with self.subTest(constant=constant), patch.object(self.module, constant, 1):
                with self.assertRaises(self.module.DiagnosticCapacityBlocked): self.call()
        self.protocol['extra'] = {'cycle': None}
        self.protocol['extra']['cycle'] = self.protocol
        with self.assertRaises(self.module.DiagnosticCapacityBlocked):
            self.module.describe_feature_candidate_development(self.protocol, self.selection,
                self.predictions, expected_protocol_sha256='a'*64)


if __name__ == '__main__':
    unittest.main()
