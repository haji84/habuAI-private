"""Synthetic diagnostic foundation tests; no qualified source fit or authority."""
import copy
import importlib
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'tests'))
from master_contracts import digest
from test_hba1_feature_candidate import fixture, recipe
import research_model_adapter as adapter
from models import hba1_feature_candidate as hba1
from models import occupancy_shrinkage as a0


class SharedScalarSeamTests(unittest.TestCase):
    def setUp(self):
        protocol, folds = fixture()
        self.selection = folds[0]['training_selection']
        self.rows = folds[0]['forecast_rows']
        self.cutoff = protocol['folds'][0]['cutoff_time']
        self.config = dict(schema_version=adapter.CONFIG_VERSION_V2, mode='DEVELOPMENT_ONLY',
            candidate_ids=['uniform','HB-A0','HB-A1'], hba1_recipe=recipe(),
            feature_definition_sha256='f'*64)
        self.prepared = adapter.prepare_research_candidates_v2(self.selection,self.rows,
            candidate_config=self.config,expected_config_sha256=digest(self.config),
            cutoff_time=self.cutoff,joined_universe_sha256=digest(self.rows),
            feature_definition_sha256='f'*64)

    def test_uniform_shared_scalar_and_serialized_guard_keep_native_artifact(self):
        scalar = getattr(adapter,'_uniform_probability',None)
        self.assertTrue(callable(scalar),'shared existing uniform scalar is missing')
        guard = getattr(adapter,'_validate_uniform_model',None)
        self.assertTrue(callable(guard),'exact uniform serialized guard is missing')
        model = self.prepared['candidates'][0]['model']
        self.assertEqual(scalar(model['counts']),model['probability'])
        self.assertEqual(guard(model,lambda:None),model)
        bad = copy.deepcopy(model);bad['probability']=0.0
        bad['model_sha256']=digest({k:v for k,v in bad.items() if k!='model_sha256'})
        with self.assertRaises(ValueError):guard(bad,lambda:None)

    def test_a0_scalar_reuses_area_lookup_and_fallback(self):
        scalar = getattr(a0,'_probability_for_area',None)
        self.assertTrue(callable(scalar),'shared native A0 lookup is missing')
        candidate = self.prepared['candidates'][1]
        for row in candidate['prediction']['unit_predictions']:
            self.assertEqual(scalar(candidate['model'],row['area_id_1km']),row['probability'])
        self.assertEqual(scalar(candidate['model'],'utm52n_1km_999_999'),candidate['model']['global_probability'])

    def test_a1_scalar_retains_native_order_rounding_and_local_overflow_checks(self):
        scalar = getattr(hba1,'_score_owned_row',None)
        self.assertTrue(callable(scalar),'shared native A1 scalar is missing')
        candidate = self.prepared['candidates'][2]
        for row,unit in zip(self.rows,candidate['prediction']['unit_predictions']):
            self.assertEqual(scalar(candidate['model'],row,lambda:None),unit['probability'])

    def test_a0_guard_checks_callback_inside_owned_copy(self):
        marker = RuntimeError('owned model guard callback')
        def stop():raise marker
        with self.assertRaises(RuntimeError) as caught:
            a0._validate_model(self.prepared['candidates'][1]['model'],check=stop)
        self.assertIs(caught.exception,marker)


if __name__ == '__main__':unittest.main()
