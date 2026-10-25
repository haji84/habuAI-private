"""Synthetic standalone HB-A1 and actual retrained ablations; no real fit."""
import copy
import hashlib
import importlib
import importlib.util
import json
import socket
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
import prospective_candidate_model as legacy
from tests.test_prospective_candidate_model import history_rows, selection_for, rebind


def sha(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
        separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def recipe(mask=None):
    return dict(schema_version='habu-hba1-fixed-logistic-recipe-v1',
        target='OWNER_CAPTURE_BINARY_GIVEN_QUALIFIED_OBSERVED_100M_10MIN_UNIT',
        numeric_recipe='LEGACY_L2_320_LR_0_15_L2_0_04_UNPENALIZED_INTERCEPT',
        feature_mask=[True]*7 if mask is None else mask,
        implementation_sha256={'src/prospective_candidate_model.py': 'a'*64,
                               'src/models/hba1_feature_candidate.py': 'b'*64})


def training_selection():
    return selection_for(history_rows()[:20])


def observation_selection(future, labels):
    rows = []
    for row, label in zip(future, labels):
        rows.append(dict(row['features'], operational_night=row['operational_night'],
            cell_id=f"utm52n_100m_{row['cell_x']}_{row['cell_y']}",
            window_start_jst=row['window_start_jst'], owner_capture_count=label))
    selected = selection_for(rows)
    selected.update(heldout_night='2026-10-14', fit_cutoff='2026-10-13T12:00:00+09:00',
        source_received_at={path: '2026-10-13T00:00:00+09:00' for path in selected['source_sha256']})
    for row, original in zip(selected['accepted'], future):
        row['row_id'] = original['row_id']
        row['capture_event_ids'] = [original['row_id']+'-event'] if row['label'] else []
    counts = selected['counts']
    ready = counts['nights'] >= 3 and counts['positives'] >= 2 and counts['negatives'] >= 2
    selected.update(status='DEVELOPMENT_TRAINING_ELIGIBLE' if ready else 'NEED_MORE_DATA',
        blockers=[] if ready else ['Insufficient binary training support; known development labels only'])
    return rebind(selected)


def fixture(night='2026-10-11'):
    train = training_selection()
    train['heldout_night'] = night
    rebind(train)
    future = []
    for index, historical in enumerate(history_rows()[:4]):
        future.append(dict(row_id=f'{night}-future-{index}', operational_night=night,
            cutoff_time=night+'T18:00:00+09:00', window_start_jst=night+'T20:00:00+09:00',
            cell_x=5000+index, cell_y=31000,
            features={name: historical[name] for name in legacy.FEATURES},
            feature_source_refs={name: ['features/synthetic-exante.json'] for name in legacy.FEATURES},
            feature_available_at={name: night+'T17:00:00+09:00' for name in legacy.FEATURES}))
    observed = observation_selection(future, [1, 1, 1, 0])
    payload = dict(night=night, training_selection=train, forecast_rows=future, evaluation_selection=observed)
    declaration = dict(night=night, training_selection_sha256=train['selection_sha256'],
        joined_forecast_sha256=sha(future), cutoff_time=night+'T18:00:00+09:00',
        evaluation_selection_sha256=observed['selection_sha256'])
    protocol = dict(schema_version='habu-hba1-retrained-ablation-protocol-v1', phase='DEVELOPMENT',
        target=recipe()['target'], base_recipe=recipe(),
        groups=[dict(id='temperature', drop_features=['temperature_c'])], folds=[declaration])
    return protocol, [payload]


class HBA1FeatureCandidateTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('models.hba1_feature_candidate'), 'standalone HB-A1 module is missing')
        self.module = importlib.import_module('models.hba1_feature_candidate')
        self.protocol, self.folds = fixture()

    def fit(self, selected=None, spec=None, **kwargs):
        selected = self.folds[0]['training_selection'] if selected is None else selected
        spec = recipe() if spec is None else spec
        return self.module.fit_hba1(selected, recipe=spec, expected_recipe_sha256=sha(spec), **kwargs)

    def predict(self, model=None, rows=None, **kwargs):
        rows = self.folds[0]['forecast_rows'] if rows is None else rows
        model = self.fit()['model'] if model is None else model
        return self.module.predict_hba1(model, rows, cutoff_time=self.protocol['folds'][0]['cutoff_time'],
            joined_universe_sha256=sha(rows), **kwargs)

    def ablate(self, **kwargs):
        return self.module.describe_retrained_ablations(self.protocol, self.folds,
            expected_protocol_sha256=sha(self.protocol), **kwargs)

    def bind(self, index=0):
        fold, declaration = self.folds[index], self.protocol['folds'][index]
        rebind(fold['training_selection'])
        rebind(fold['evaluation_selection'])
        declaration.update(training_selection_sha256=fold['training_selection']['selection_sha256'],
            evaluation_selection_sha256=fold['evaluation_selection']['selection_sha256'],
            joined_forecast_sha256=sha(fold['forecast_rows']))

    def test_fit_reuses_exact_legacy_numeric_core_with_all_train_rows(self):
        result = self.fit()
        model = result['model']
        selected = self.folds[0]['training_selection']
        matrix = [[r['features'][name] for name in legacy.FEATURES] for r in selected['accepted']]
        expected = legacy._fit_numeric(matrix, [r['label'] for r in selected['accepted']])
        self.assertEqual((model['means'], model['scales'], model['coefficients']), expected)
        self.assertEqual(model['counts']['accepted_rows'], 20)
        self.assertEqual(model['training_nights'], [f'2026-10-{day:02d}' for day in range(1, 6)])
        self.assertEqual(model['training_selection_sha256'], selected['selection_sha256'])
        self.assertEqual(model['training_row_ids_sha256'], sha([r['row_id'] for r in selected['accepted']]))
        self.assertEqual(model['training_rows_sha256'], sha(selected['accepted']))
        self.assertEqual(result['status'], 'DEVELOPMENT_FIT_ONLY')

    def test_predict_common_units_keeps_whole_universe_and_legacy_probability_rounding(self):
        model = self.fit()['model']
        result = self.predict(model)
        self.assertEqual(len(result['unit_predictions']), 4)
        for unit, row in zip(result['unit_predictions'], self.folds[0]['forecast_rows']):
            expected = round(legacy._score([row['features'][n] for n in legacy.FEATURES],
                model['coefficients'], model['means'], model['scales']), 8)
            self.assertEqual(unit['probability'], expected)
            self.assertEqual(unit['spatial_score'], expected)
            self.assertEqual(unit['row_id'], row['row_id'])
        self.assertNotIn('area_rank_top10', result)

    def test_true_ablation_refits_same_rows_and_exposes_identical_scope_lineage(self):
        calls = []
        core = legacy._fit_numeric
        def observe(matrix, labels, **kwargs):
            calls.append((copy.deepcopy(matrix), list(labels), kwargs.get('feature_mask')))
            return core(matrix, labels, **kwargs)
        with patch.object(legacy, '_fit_numeric', side_effect=observe): result = self.ablate()
        self.assertEqual(len(calls), 2)
        self.assertEqual(calls[0][:2], calls[1][:2])
        self.assertNotEqual(calls[0][2], calls[1][2])
        fold = result['fold_results'][0]
        full, ablated = fold['full'], fold['ablations'][0]
        self.assertEqual(len(full['coefficients']), 8)
        self.assertEqual(len(ablated['coefficients']), 7)
        self.assertNotEqual(ablated['coefficients'], [full['coefficients'][0], *full['coefficients'][2:]])
        for key in ('training_row_ids_sha256', 'training_rows_sha256', 'raw_feature_rows_sha256',
                    'training_selection_sha256', 'joined_forecast_sha256', 'observed_mask_sha256'):
            self.assertEqual(full[key], ablated[key])
        self.assertEqual(result['status'], 'DESCRIPTIVE_RETRAINED_ABLATION_ONLY')

    def test_ablated_minus_full_brier_sign_matches_hand_calculation(self):
        # 3 positives + 1 negative: p=.75 -> .1875; p=.25 -> .4375.
        def score(x, coef, means, scales): return .75 if len(x) == 7 else .25
        with patch.object(legacy, '_score', side_effect=score): result = self.ablate()
        fold = result['fold_results'][0]
        self.assertEqual(fold['full']['brier'], .1875)
        self.assertEqual(fold['ablations'][0]['brier'], .4375)
        self.assertEqual(fold['ablations'][0]['ablated_minus_full_brier'], .25)
        self.assertEqual(result['paired_summary'][0]['mean_ablated_minus_full_brier'], .25)

    def test_heldout_label_changes_do_not_change_training_fits_or_forecasts(self):
        first = self.ablate()['fold_results'][0]
        observed = self.folds[0]['evaluation_selection']
        for row in observed['accepted']:
            row['label'] = 1-row['label']
            row['capture_event_ids'] = [row['row_id']+'-flipped'] if row['label'] else []
        observed['counts'].update(positives=1, negatives=3)
        self.bind()
        second = self.ablate()['fold_results'][0]
        for a, b in zip([first['full'], *first['ablations']], [second['full'], *second['ablations']]):
            self.assertEqual(a['model_sha256'], b['model_sha256'])
            self.assertEqual(a['prediction_sha256'], b['prediction_sha256'])
            self.assertEqual(a['coefficients'], b['coefficients'])

    def test_unobserved_future_unit_remains_prediction_and_not_negative(self):
        observed = self.folds[0]['evaluation_selection']
        observed['accepted'].pop()
        observed['counts'].update(accepted_rows=3, positives=3, negatives=0)
        self.bind()
        result = self.ablate()['fold_results'][0]
        self.assertEqual(result['forecast_units'], 4)
        self.assertEqual(result['observed_units'], 3)

    def test_five_training_nights_and_twenty_rows_are_not_silently_relaxed(self):
        for count in (0, 16, 19):
            selected = training_selection()
            selected['accepted'] = selected['accepted'][:count]
            rows = selected['accepted']
            positives = sum(r['label'] for r in rows)
            selected['counts'].update(accepted_rows=count, nights=len({r['night'] for r in rows}),
                                     positives=positives, negatives=count-positives)
            ready = selected['counts']['nights'] >= 3 and positives >= 2 and count-positives >= 2
            selected.update(status='DEVELOPMENT_TRAINING_ELIGIBLE' if ready else 'NEED_MORE_DATA',
                blockers=[] if ready else ['Insufficient selection'])
            rebind(selected)
            result = self.fit(selected)
            self.assertEqual(result['status'], 'NEED_MORE_DATA')
            self.assertIsNone(result['model'])

    def test_insufficient_fold_blocks_whole_ablation_without_fits_or_partial_metrics(self):
        selected = self.folds[0]['training_selection']
        selected['accepted'] = selected['accepted'][:16]
        selected['counts'].update(accepted_rows=16, nights=4, positives=4, negatives=12)
        self.bind()
        with patch.object(legacy, '_fit_numeric', side_effect=AssertionError('partial fit')):
            result = self.ablate()
        self.assertEqual(result['status'], 'NEED_MORE_DATA')
        self.assertEqual(result['fold_results'], [])
        self.assertEqual(result['paired_summary'], [])

    def test_missing_or_outside_observed_units_and_changed_raw_features_reject(self):
        for kind in ('id', 'cell', 'window', 'night', 'feature', 'empty'):
            self.protocol, self.folds = fixture()
            observed = self.folds[0]['evaluation_selection']
            row = observed['accepted'][0]
            if kind == 'id': row['row_id'] = 'outside'
            elif kind == 'cell': row['cell_x'] += 100
            elif kind == 'window': row['window_start_jst'] = '2026-10-11T20:10:00+09:00'
            elif kind == 'night': row.update(night='2026-10-10', window_start_jst='2026-10-10T20:00:00+09:00')
            elif kind == 'feature': row['features']['temperature_c'] += 1
            else:
                observed['accepted'] = []
                observed['counts'].update(accepted_rows=0, nights=0, positives=0, negatives=0)
            self.bind()
            if kind == 'empty':
                self.assertEqual(self.ablate()['status'], 'NEED_MORE_DATA')
            else:
                with self.assertRaises(ValueError): self.ablate()

    def test_all_seven_features_required_even_when_ablated_and_physical_ranges_enforced(self):
        for location in ('train', 'future', 'observed'):
            self.protocol, self.folds = fixture()
            if location == 'train': self.folds[0]['training_selection']['accepted'][0]['features']['humidity_pct'] = 101
            elif location == 'future': self.folds[0]['forecast_rows'][0]['features']['slope_deg'] = 91
            else: self.folds[0]['evaluation_selection']['accepted'][0]['features']['road_length_m'] = 0
            self.bind()
            with self.assertRaises(ValueError): self.ablate()
        self.protocol, self.folds = fixture()
        self.folds[0]['forecast_rows'][0]['features'].pop('temperature_c')
        self.bind()
        with self.assertRaises(ValueError): self.ablate()

    def test_bad_groups_duplicate_masks_all_drop_and_confirmation_reject(self):
        for groups in ([dict(id='all', drop_features=list(legacy.FEATURES))],
                       [dict(id='empty', drop_features=[])],
                       [dict(id='bad', drop_features=['label'])],
                       [dict(id='dup', drop_features=['temperature_c', 'temperature_c'])],
                       [dict(id='a', drop_features=['temperature_c']), dict(id='b', drop_features=['temperature_c'])]):
            self.protocol, self.folds = fixture()
            self.protocol['groups'] = groups
            with self.assertRaises(ValueError): self.ablate()
        self.protocol, self.folds = fixture()
        self.protocol['phase'] = 'CONFIRMATION'
        with self.assertRaises(ValueError): self.ablate()

    def test_two_outer_folds_and_paired_night_averaging(self):
        second_protocol, second = fixture('2026-10-12')
        self.protocol['folds'] += second_protocol['folds']
        self.folds += second
        result = self.ablate()
        self.assertEqual(len(result['fold_results']), 2)
        differences = [f['ablations'][0]['ablated_minus_full_brier'] for f in result['fold_results']]
        self.assertEqual(result['paired_summary'][0]['paired_nights'], 2)
        self.assertAlmostEqual(result['paired_summary'][0]['mean_ablated_minus_full_brier'], sum(differences)/2)

    def test_event_reuse_between_train_and_evaluation_or_across_evaluation_folds_rejects(self):
        observed = self.folds[0]['evaluation_selection']
        observed['accepted'][0]['capture_event_ids'] = list(self.folds[0]['training_selection']['accepted'][0]['capture_event_ids'])
        self.bind()
        with self.assertRaises(ValueError): self.ablate()
        self.protocol, self.folds = fixture()
        p2, f2 = fixture('2026-10-12')
        self.protocol['folds'] += p2['folds']
        self.folds += f2
        self.folds[1]['evaluation_selection']['accepted'][0]['capture_event_ids'] = list(
            self.folds[0]['evaluation_selection']['accepted'][0]['capture_event_ids'])
        self.bind(1)
        with self.assertRaises(ValueError): self.ablate()

    def test_global_event_cannot_move_from_earlier_train_unit_to_later_evaluation(self):
        second_protocol, second = fixture('2026-10-12')
        self.protocol['folds'] += second_protocol['folds']
        self.folds += second
        event = self.folds[0]['training_selection']['accepted'][0]['capture_event_ids'][0]
        self.folds[1]['training_selection']['accepted'][0]['capture_event_ids'] = ['new-training-event']
        self.folds[1]['evaluation_selection']['accepted'][0]['capture_event_ids'] = [event]
        self.bind(1)
        with self.assertRaises(ValueError): self.ablate()

    def test_same_physical_earlier_development_event_can_train_a_later_rolling_fold(self):
        second_protocol, second = fixture('2026-10-12')
        self.protocol['folds'] += second_protocol['folds']
        self.folds += second
        selected = self.folds[1]['training_selection']
        selected['accepted'].append(copy.deepcopy(self.folds[0]['evaluation_selection']['accepted'][0]))
        selected['counts'].update(accepted_rows=21, nights=6, positives=6, negatives=15)
        selected['fit_cutoff'] = '2026-10-12T06:00:00+09:00'
        selected['source_received_at'] = {path: '2026-10-12T00:00:00+09:00' for path in selected['source_sha256']}
        self.bind(1)
        self.assertEqual(len(self.ablate()['fold_results']), 2)

    def test_global_physical_unit_binary_label_cannot_flip_between_evaluation_and_later_train(self):
        for earlier_index in (0, 3):
            self.protocol, self.folds = fixture()
            second_protocol, second = fixture('2026-10-12')
            self.protocol['folds'] += second_protocol['folds']
            self.folds += second
            selected = self.folds[1]['training_selection']
            changed = copy.deepcopy(self.folds[0]['evaluation_selection']['accepted'][earlier_index])
            changed['label'] = 1-changed['label']
            changed['capture_event_ids'] = ['new-contradictory-event'] if changed['label'] else []
            selected['accepted'].append(changed)
            selected['counts'].update(accepted_rows=21, nights=6, positives=5+changed['label'], negatives=16-changed['label'])
            selected['fit_cutoff'] = '2026-10-12T06:00:00+09:00'
            selected['source_received_at'] = {path: '2026-10-12T00:00:00+09:00' for path in selected['source_sha256']}
            self.bind(1)
            with self.subTest(earlier_index=earlier_index), self.assertRaises(ValueError): self.ablate()

    def test_changed_digest_or_explicit_source_and_protocol_conflict_is_invalid(self):
        expected = sha(self.protocol)
        self.protocol['groups'][0]['id'] = 'changed'
        with self.assertRaises(ValueError):
            self.module.describe_retrained_ablations(self.protocol, self.folds, expected_protocol_sha256=expected)
        self.protocol, self.folds = fixture()
        self.folds[0]['training_selection']['source_sha256']['features/fixture.json'] = 'f'*64
        with self.assertRaises(ValueError): self.ablate()
        self.protocol, self.folds = fixture()
        self.folds[0]['forecast_rows'][0]['features']['temperature_c'] += 1
        with self.assertRaises(ValueError): self.ablate()

    def test_model_hash_dimension_recipe_chronology_and_authority_checked_before_prediction(self):
        valid = self.fit()['model']
        for change in ('hash', 'dimension', 'mask', 'cutoff', 'authority'):
            model = copy.deepcopy(valid)
            if change == 'hash': model['coefficients'][0] += .1
            elif change == 'dimension': model['coefficients'].pop()
            elif change == 'mask': model['feature_names'].reverse()
            elif change == 'cutoff': model['fit_cutoff'] = self.protocol['folds'][0]['cutoff_time']
            else: model['production_activation_authorized'] = True
            if change != 'hash': model['model_sha256'] = sha({k: v for k, v in model.items() if k != 'model_sha256'})
            with self.subTest(change=change), self.assertRaises(ValueError): self.predict(model)

    def test_reloaded_model_rejects_fit_cutoff_before_actual_max_training_window(self):
        model = self.fit()['model']
        model['fit_cutoff'] = '2026-10-05T07:01:00+09:00'
        model['model_sha256'] = sha({k: v for k, v in model.items() if k != 'model_sha256'})
        with self.assertRaises(ValueError): self.predict(model)

    def test_future_cutoff_equality_missing_source_and_labels_reject(self):
        for kind in ('readiness', 'source', 'label', 'night'):
            self.protocol, self.folds = fixture()
            row = self.folds[0]['forecast_rows'][0]
            if kind == 'readiness': row['feature_available_at']['temperature_c'] = row['cutoff_time']
            elif kind == 'source': row['feature_source_refs']['temperature_c'] = []
            elif kind == 'label': row['label'] = 1
            else: row['operational_night'] = '2026-10-12'
            self.bind()
            with self.assertRaises(ValueError): self.ablate()

    def test_all_outputs_no_authentication_selection_or_production_and_no_dispatch(self):
        outputs = [self.fit(), self.fit()['model'], self.predict(), self.ablate()]
        for output in outputs:
            self.assertEqual(output['source_authenticity'], 'NOT_ATTESTED')
            self.assertEqual(output['source_authentication'], 'CALLER_DEPENDENCY_REQUIRED')
            for field in ('fit_authorized', 'selection_authorized', 'scientific_execution_authorized',
                          'official_issuance_authorized', 'production_activation_authorized'):
                self.assertIs(output[field], False)
        self.assertNotIn('model', outputs[-1])
        self.assertNotIn('candidates', outputs[-1])
        from research_model_adapter import CANDIDATES
        self.assertEqual(CANDIDATES, ('uniform', 'HB-A0', 'HB-B1'))

    def test_inputs_unmodified_owned_after_callback_and_result_sealed(self):
        original = copy.deepcopy((self.protocol, self.folds))
        result = self.ablate()
        self.assertEqual((self.protocol, self.folds), original)
        digest = result.pop('ablation_sha256')
        self.assertEqual(digest, sha(result))
        core = legacy._fit_numeric
        def mutate(matrix, labels, **kwargs):
            self.folds[0]['forecast_rows'][0]['features']['temperature_c'] = 999
            self.folds[0]['training_selection']['accepted'][0]['label'] = 0
            self.protocol['groups'][0]['drop_features'] = ['slope_deg']
            return core(matrix, labels, **kwargs)
        with patch.object(legacy, '_fit_numeric', side_effect=mutate): mutated = self.ablate()
        self.assertEqual(mutated['ablation_sha256'], digest)

    def test_no_files_network_legacy_dispatch_or_real_fit_inputs(self):
        with patch('builtins.open', side_effect=AssertionError('file')), \
                patch.object(Path, 'open', side_effect=AssertionError('path')), \
                patch.object(socket, 'socket', side_effect=AssertionError('network')), \
                patch.object(legacy, 'train_candidate', side_effect=AssertionError('legacy internal split')), \
                patch.object(legacy, 'rank_future', side_effect=AssertionError('legacy max area rank')):
            self.assertEqual(self.ablate()['status'], 'DESCRIPTIVE_RETRAINED_ABLATION_ONLY')

    def test_shared_budget_invalid_values_capacity_and_late_hash_no_success(self):
        for budget in (True, 0, 301, 10**1000, float('inf'), float('nan')):
            with self.assertRaises(ValueError): self.ablate(budget_seconds=budget)
        for constant in ('MAX_JSON_BYTES', 'MAX_JSON_NODES', 'MAX_TRAIN_ROWS', 'MAX_FORECAST_ROWS', 'MAX_OBSERVED_ROWS', 'MAX_FOLDS', 'MAX_GROUPS'):
            with patch.object(self.module, constant, 0), self.assertRaises(self.module.HBA1CapacityBlocked): self.ablate()
        def cancel(): raise TimeoutError('parent budget')
        with self.assertRaises(TimeoutError): self.ablate(check=cancel)
        clock = [0]
        real = self.module._digest
        def late(value, check):
            digest = real(value, check)
            if type(value) is dict and value.get('schema_version') == self.module.ABLATION_VERSION:
                clock[0] = 301
            return digest
        with patch.object(self.module, 'monotonic', side_effect=lambda: clock[0]), \
                patch.object(self.module, '_digest', side_effect=late), self.assertRaises(TimeoutError): self.ablate()

    def test_finite_extreme_fit_overflow_and_pre_sigmoid_score_overflow_raise_value_error(self):
        selected = training_selection()
        for index, row in enumerate(selected['accepted']):
            row['features']['temperature_c'] = 1e308 if index % 2 else -1e308
        rebind(selected)
        with self.assertRaises(ValueError): self.fit(selected)
        rows = copy.deepcopy(self.folds[0]['forecast_rows'])
        rows[0]['features']['humidity_pct'] = 100
        # A constant training humidity has scale 1e-9; a finite but very large
        # unseen temperature likewise cannot become an infinite clipped score.
        rows[0]['features']['temperature_c'] = 1e308
        model = self.fit()['model']
        model['scales'][0] = 1e-9
        model['model_sha256'] = sha({k: v for k, v in model.items() if k != 'model_sha256'})
        with self.assertRaises(ValueError): self.predict(model, rows)
        with patch.object(legacy, '_score', return_value=float('nan')), self.assertRaises(ValueError): self.fit()

    def test_later_fold_contradiction_not_masked_by_earlier_missing_data(self):
        selected = self.folds[0]['training_selection']
        selected['accepted'] = selected['accepted'][:16]
        selected['counts'].update(accepted_rows=16, nights=4, positives=4, negatives=12)
        self.bind()
        second_protocol, second = fixture('2026-10-12')
        self.protocol['folds'] += second_protocol['folds']
        self.folds += second
        self.folds[1]['evaluation_selection']['accepted'][0]['features']['temperature_c'] += 1
        self.bind(1)
        with patch.object(legacy, '_fit_numeric', side_effect=AssertionError('fit before all-fold preflight')):
            with self.assertRaises(ValueError): self.ablate()

    def test_reserved_or_case_duplicate_group_ids_and_unknown_trust_fields_reject(self):
        for identifier in ('full', 'FULL', 'baseline', 'HB-A1', 'champion'):
            self.protocol, self.folds = fixture()
            self.protocol['groups'][0]['id'] = identifier
            with self.assertRaises(ValueError): self.ablate()
        self.protocol, self.folds = fixture()
        self.protocol['groups'].append(dict(id='TEMPERATURE', drop_features=['humidity_pct']))
        with self.assertRaises(ValueError): self.ablate()
        spec = recipe()
        spec['trusted_source'] = True
        with self.assertRaises(ValueError): self.fit(spec=spec)

    def test_final_digest_expiry_checked_for_standalone_fit_and_predict(self):
        model = self.fit()['model']
        real = self.module._digest
        for version in (self.module.FIT_VERSION, self.module.PREDICTION_VERSION):
            clock = [0]
            def late(value, check):
                digest = real(value, check)
                if type(value) is dict and value.get('schema_version') == version: clock[0] = 301
                return digest
            with patch.object(self.module, 'monotonic', side_effect=lambda: clock[0]), \
                    patch.object(self.module, '_digest', side_effect=late), self.assertRaises(TimeoutError):
                self.fit() if version == self.module.FIT_VERSION else self.predict(model)


if __name__ == '__main__':
    unittest.main()
