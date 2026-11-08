"""Locked split metadata fixtures are software evidence, never field validation."""
import copy
import sys
from pathlib import Path
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from codex_cycle_contract import POLICY_DIGEST
from master_contracts import digest
from evaluation.locked_protocol_manifest import validate_locked_protocol


def fixture():
    history = {'research_used_nights': ['2026-10-08'], 'confirmation_used_nights': []}
    groups = []
    for i, night in enumerate(('2026-10-01', '2026-10-02'), 1):
        groups.append(dict(group_id=f'train{i}', operational_night=night,
                           geography_ids=['AMAMI'], corpus_selection_sha256=str(i) * 64,
                           readiness={key: '2026-10-04T00:00:00+09:00' for key in
                                      ('source_received_at', 'derived_at', 'materialized_at', 'audited_at')}))
    cohorts = []
    for i, night in enumerate(('2026-10-08', '2026-10-10', '2026-10-11',
                               '2026-10-12', '2026-10-13', '2026-10-14')):
        cohorts.append(dict(cohort_id=f'forecast{i}', operational_night=night,
                            geography_ids=['AMAMI' if i == 0 else 'KAKEROMA'],
                            forecast_cutoff=f'{night}T18:00:00+09:00',
                            universe_sha256='a' * 64, feature_snapshot_sha256='b' * 64,
                            feature_available_at='2026-10-08T10:00:00+09:00',
                            outcome_ledger_commitment_sha256='d' * 64))
    plan = dict(schema_version='habu-locked-protocol-v1', cycle_sha256='c' * 64,
                policy_sha256=POLICY_DIGEST, frozen_at='2026-10-09T12:00:00+09:00',
                exposure_history_sha256=digest(history), training_groups=groups,
                forecast_cohorts=cohorts,
                folds=[dict(fold_id='development', purpose='DEVELOPMENT_FORECAST',
                            train_group_ids=['train1', 'train2'], evaluation_cohort_ids=['forecast0'],
                            heldout_geography_ids=[], embargo_nights=1),
                       dict(fold_id='confirmation', purpose='SEALED_CONFIRMATION',
                            train_group_ids=['train1', 'train2'],
                            evaluation_cohort_ids=[f'forecast{i}' for i in range(1, 6)],
                            heldout_geography_ids=['KAKEROMA'], embargo_nights=1)],
                registered_recipes=['uniform', 'ridge'], selected_recipe='ridge',
                model_sha256='e' * 64, predictions_sha256='f' * 64)
    return plan, history


class LockedProtocolTests(unittest.TestCase):
    def setUp(self):
        self.plan, self.history = fixture()

    def validate(self):
        return validate_locked_protocol(self.plan, self.history)

    def test_valid_plan_has_distinct_nights_but_no_scientific_authority(self):
        result = self.validate()
        self.assertEqual(result['status'], 'PROTOCOL_CONTRACT_VALIDATED')
        self.assertEqual(result['confirmation_nights'], ['2026-10-10', '2026-10-11',
                                                       '2026-10-12', '2026-10-13', '2026-10-14'])
        self.assertEqual(result['confirmation_floor'], 'MET_NOT_SUFFICIENT')
        self.assertEqual(result['scientific_status'], 'NOT_VALIDATED')
        self.assertEqual(result['denominator_gate'], 'NOT_EVALUATED')
        self.assertEqual(result['exposure_history_authenticity'], 'NOT_VALIDATED')
        self.assertFalse(result['fit_authorized'])
        self.assertFalse(result['production_authorized'])
        self.assertIn('INDEPENDENT_COMPLETE_OUTCOME_LEDGER_UNVERIFIED', result['blockers'])

    def test_inputs_are_not_mutated_and_identity_repeats(self):
        original = copy.deepcopy((self.plan, self.history))
        first = self.validate()
        self.assertEqual(first, self.validate())
        self.assertEqual(original, (self.plan, self.history))

    def test_missing_history_is_not_an_empty_trusted_ledger(self):
        with self.assertRaisesRegex(ValueError, 'EXPOSURE_HISTORY'):
            validate_locked_protocol(self.plan, None)

    def test_empty_history_remains_unverified(self):
        self.history = {'research_used_nights': [], 'confirmation_used_nights': []}
        self.plan['exposure_history_sha256'] = digest(self.history)
        self.assertEqual(self.validate()['exposure_history_authenticity'], 'NOT_VALIDATED')

    def test_changed_history_cannot_keep_its_old_commitment(self):
        self.history['research_used_nights'].append('2026-10-10')
        with self.assertRaisesRegex(ValueError, 'EXPOSURE_HISTORY_HASH'):
            self.validate()

    def test_research_night_cannot_be_washed_into_confirmation(self):
        self.history['research_used_nights'].append('2026-10-10')
        self.plan['exposure_history_sha256'] = digest(self.history)
        with self.assertRaisesRegex(ValueError, 'CONFIRMATION_REUSED'):
            self.validate()

    def test_revealed_confirmation_cannot_be_reused_after_new_cycle_id(self):
        self.history['confirmation_used_nights'].append('2026-10-10')
        self.plan['cycle_sha256'] = '9' * 64
        self.plan['exposure_history_sha256'] = digest(self.history)
        with self.assertRaisesRegex(ValueError, 'CONFIRMATION_REUSED'):
            self.validate()

    def test_same_night_under_distinct_ids_never_splits_train_and_evaluation(self):
        self.plan['training_groups'][0]['operational_night'] = '2026-10-10'
        with self.assertRaisesRegex(ValueError, 'SAME_NIGHT|FUTURE_TRAINING'):
            self.validate()

    def test_embargo_boundary_equality_is_excluded(self):
        self.plan['training_groups'][0]['operational_night'] = '2026-10-07'
        with self.assertRaisesRegex(ValueError, 'EMBARGO'):
            self.validate()

    def test_source_ready_at_evaluated_0700_is_excluded(self):
        self.plan['training_groups'][0]['readiness']['audited_at'] = '2026-10-08T07:00:00+09:00'
        with self.assertRaisesRegex(ValueError, 'NOT_AVAILABLE_BEFORE_BOUNDARY'):
            self.validate()

    def test_confirmation_training_cannot_arrive_after_model_freeze(self):
        self.plan['training_groups'][0]['readiness']['audited_at'] = '2026-10-09T12:00:00+09:00'
        self.plan['folds'][0]['train_group_ids'] = ['train2']
        with self.assertRaisesRegex(ValueError, 'NOT_AVAILABLE_BEFORE_BOUNDARY'):
            self.validate()

    def test_training_readiness_cannot_precede_the_observation_night(self):
        for key in self.plan['training_groups'][0]['readiness']:
            self.plan['training_groups'][0]['readiness'][key] = '2026-09-30T20:00:00+09:00'
        with self.assertRaisesRegex(ValueError, 'TRAIN_READINESS_PRECEDES_OBSERVATION'):
            self.validate()

    def test_forecast_features_use_their_own_cutoff_and_not_training_0700(self):
        self.plan['forecast_cohorts'][0]['feature_available_at'] = '2026-10-08T17:59:59+09:00'
        self.assertEqual(self.validate()['status'], 'PROTOCOL_CONTRACT_VALIDATED')

    def test_forecast_feature_cutoff_equality_is_excluded(self):
        self.plan['forecast_cohorts'][0]['feature_available_at'] = '2026-10-08T18:00:00+09:00'
        with self.assertRaisesRegex(ValueError, 'FORECAST_AVAILABILITY'):
            self.validate()

    def test_confirmation_prediction_cannot_precede_its_input_availability(self):
        self.plan['forecast_cohorts'][1]['feature_available_at'] = '2026-10-09T12:00:00+09:00'
        with self.assertRaisesRegex(ValueError, 'SEALED_PREDICTION_AVAILABILITY'):
            self.validate()

    def test_heldout_geography_cannot_enter_training(self):
        self.plan['training_groups'][0]['geography_ids'].append('KAKEROMA')
        with self.assertRaisesRegex(ValueError, 'GEOGRAPHIC_LEAKAGE'):
            self.validate()

    def test_declared_geography_holdout_must_occur_in_evaluation(self):
        self.plan['folds'][1]['heldout_geography_ids'] = ['UNRELATED']
        with self.assertRaisesRegex(ValueError, 'GEOGRAPHIC_HOLDOUT'):
            self.validate()

    def test_unallocated_geographic_holdout_is_reported_as_blocked(self):
        self.plan['folds'][1]['heldout_geography_ids'] = []
        self.assertIn('GEOGRAPHIC_HOLDOUT_UNALLOCATED', self.validate()['blockers'])

    def test_outcome_commitment_does_not_prove_complete_denominator(self):
        self.plan['forecast_cohorts'][1]['outcome_ledger_commitment_sha256'] = '0' * 64
        self.assertEqual(self.validate()['denominator_gate'], 'NOT_EVALUATED')

    def test_missing_outcome_commitment_cannot_hide_outside_universe_misses(self):
        del self.plan['forecast_cohorts'][1]['outcome_ledger_commitment_sha256']
        with self.assertRaisesRegex(ValueError, 'COHORT_FIELDS'):
            self.validate()

    def test_universe_only_denominator_or_supplied_labels_are_rejected(self):
        for key, value in [('denominator_scope', 'UNIVERSE_ONLY'), ('labels', [0, 1])]:
            plan = copy.deepcopy(self.plan)
            plan[key] = value
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, 'PLAN_FIELDS'):
                validate_locked_protocol(plan, self.history)

    def test_recipe_cannot_have_its_own_easier_fold_mask(self):
        self.plan['folds'][1]['recipe_ids'] = ['ridge']
        with self.assertRaisesRegex(ValueError, 'FOLD_FIELDS'):
            self.validate()

    def test_fourth_recipe_or_missing_uniform_is_rejected(self):
        for recipes in (['uniform', 'a', 'b', 'c'], ['ridge']):
            self.plan['registered_recipes'] = recipes
            with self.subTest(recipes=recipes), self.assertRaisesRegex(ValueError, 'RECIPES'):
                self.validate()

    def test_unregistered_selection_is_rejected(self):
        self.plan['selected_recipe'] = 'post_hoc_winner'
        with self.assertRaisesRegex(ValueError, 'SELECTION'):
            self.validate()

    def test_dropped_forecast_cohort_is_rejected_instead_of_hiding_a_hard_case(self):
        self.plan['folds'][1]['evaluation_cohort_ids'].pop()
        with self.assertRaisesRegex(ValueError, 'COHORT_COVERAGE'):
            self.validate()

    def test_development_and_confirmation_cannot_share_a_night(self):
        self.plan['forecast_cohorts'][1]['operational_night'] = '2026-10-08'
        self.plan['forecast_cohorts'][1]['forecast_cutoff'] = '2026-10-08T18:00:00+09:00'
        with self.assertRaisesRegex(ValueError, 'SPLIT_NIGHT|CONFIRMATION_FREEZE'):
            self.validate()

    def test_confirmation_model_is_not_refit_between_confirmation_folds(self):
        extra = copy.deepcopy(self.plan['folds'][1])
        extra['fold_id'] = 'confirmation2'
        extra['evaluation_cohort_ids'] = [self.plan['folds'][1]['evaluation_cohort_ids'].pop()]
        extra['train_group_ids'] = ['train2']
        self.plan['folds'].append(extra)
        with self.assertRaisesRegex(ValueError, 'CONFIRMATION_TRAINING_CHANGED'):
            self.validate()

    def test_four_distinct_confirmation_nights_do_not_meet_five_night_floor(self):
        self.plan['forecast_cohorts'][-1]['operational_night'] = '2026-10-13'
        self.plan['forecast_cohorts'][-1]['forecast_cutoff'] = '2026-10-13T18:00:00+09:00'
        result = self.validate()
        self.assertEqual(result['confirmation_floor'], 'BLOCKED')
        self.assertIn('FEWER_THAN_FIVE_CONFIRMATION_NIGHTS', result['blockers'])

    def test_late_model_freeze_is_rejected(self):
        self.plan['frozen_at'] = '2026-10-10T18:00:00+09:00'
        with self.assertRaisesRegex(ValueError, 'CONFIRMATION_FREEZE'):
            self.validate()

    def test_wrong_shared_policy_cannot_narrow_scientific_gates(self):
        self.plan['policy_sha256'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'POLICY'):
            self.validate()

    def test_boolean_embargo_and_duplicate_ids_are_rejected(self):
        self.plan['folds'][0]['embargo_nights'] = True
        with self.assertRaisesRegex(ValueError, 'EMBARGO'):
            self.validate()
        self.plan['folds'][0]['embargo_nights'] = 1
        self.plan['training_groups'][1]['group_id'] = 'train1'
        with self.assertRaisesRegex(ValueError, 'DUPLICATE'):
            self.validate()

    def test_validation_has_no_file_or_outcome_io(self):
        with patch('builtins.open', side_effect=AssertionError('OUTCOME_IO')), \
                patch('io.open', side_effect=AssertionError('OUTCOME_IO')):
            self.assertEqual(self.validate()['status'], 'PROTOCOL_CONTRACT_VALIDATED')


if __name__ == '__main__':
    unittest.main()
