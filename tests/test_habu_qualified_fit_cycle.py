"""Reproducible synthetic end-to-end validation of the existing G0 fit path."""
import pathlib
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'scripts'))
sys.path.insert(0, str(ROOT / 'tests'))

from habu_qualified_fit_cycle import run_cycle
from test_g0_training_source_contract import TrainingSourceContractTests, definition_hash


class QualifiedAutoFitTests(unittest.TestCase):
    def setUp(self):
        self.fx = TrainingSourceContractTests()
        self.fx.setUp()
        self.addCleanup(self.fx.doCleanups)
        self.output = self.fx.work / 'private-out'
        self.kwargs = {
            'manifest_path': self.fx.ref['path'],
            'manifest_sha256': self.fx.ref['sha256'],
            'feature_sha256': definition_hash(self.fx.features),
            'heldout_night': '2026-10-20',
            'fit_cutoff': '2026-10-19T19:00:00+09:00',
            'forecast_cutoff': '2026-10-20T18:00:00+09:00',
        }

    def execute(self, **changed):
        kwargs = dict(self.kwargs, **changed)
        return run_cycle(self.fx.root, self.output, **kwargs)

    def test_qualified_synthetic_selection_fits_prospective_readable_research_only_candidate(self):
        result = self.execute()
        self.assertEqual(result['status'], 'RESEARCH_CANDIDATE_FITTED')
        self.assertFalse(result['production_model_activated'])
        self.assertFalse(result['official_prediction_authorized'])
        self.assertEqual(result['future_independent_validation'], 'NOT_PERFORMED')
        self.assertEqual(result['fit_counts']['rows'], 4)
        model_file = self.output / result['model_relative_path']
        self.assertTrue(model_file.exists())
        self.assertFalse((self.fx.root / 'models').exists())
        self.assertEqual(self.execute(), result)

    def test_unqualified_source_is_explicit_blocked_no_model(self):
        result = self.execute(manifest_path=None, manifest_sha256=None, feature_sha256=None)
        self.assertEqual(result['status'], 'BLOCKED')
        self.assertEqual(result['reason'], 'MISSING_SOURCE_QUALIFIED_G0_MANIFEST')
        self.assertFalse(self.output.exists())

    def test_missing_manifest_path_blocks_no_model(self):
        result = self.execute(manifest_path='protocols/development/nonexistent.json')
        self.assertEqual(result['reason'], 'QUALIFIED_MANIFEST_SOURCE_NOT_AVAILABLE')
        self.assertFalse(self.output.exists())

    def test_tampered_manifest_fails_closed(self):
        manifest_path = self.fx.root / self.fx.ref['path']
        manifest_path.write_bytes(manifest_path.read_bytes() + b'\n')
        with self.assertRaises(ValueError):
            self.execute()
        self.assertFalse(self.output.exists())

    def test_missing_independent_negative_exposure_blocks_fit(self):
        self.fx.fixture.rows[1]['search_role'] = 'UNKNOWN'
        self.fx.fixture.publish()
        self.fx.build_manifest()
        result = self.execute(manifest_sha256=self.fx.ref['sha256'])
        self.assertEqual(result['status'], 'BLOCKED')
        self.assertEqual(result['reason'], 'INSUFFICIENT_SOURCE_QUALIFIED_TRAINING_UNITS')
        self.assertEqual(result['counts']['negatives'], 1)
        self.assertFalse(self.output.exists())

    def test_historical_future_source_is_not_fit_input(self):
        self.fx.fixture.add_development_holdout()
        self.fx.build_manifest()
        result = self.execute(manifest_sha256=self.fx.ref['sha256'])
        self.assertEqual(result['status'], 'BLOCKED')
        self.assertEqual(result['reason'], 'G0_TRAINING_SOURCE_GATE_BLOCKED')
        self.assertFalse(self.output.exists())

    def test_never_write_model_inside_repo_workspace(self):
        with self.assertRaisesRegex(ValueError, 'outside'):
            run_cycle(self.fx.root, self.fx.root / 'models' / 'candidates', **self.kwargs)
        self.assertFalse((self.fx.root / 'models').exists())

    def test_reject_unbound_manifest_or_unvalidated_source_family(self):
        for bad in ({'manifest_sha256': 'b' * 64, 'feature_sha256': None},
                    {'manifest_path': '../private.json'},
                    {'manifest_path': 'sealed/confirmation/fake.json'}):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                self.execute(**bad)

    def test_exposed_nights_do_not_train_as_untouched_confirmation(self):
        result = self.execute(exposed_nights=('2026-09-12',))
        self.assertEqual(result['status'], 'BLOCKED')
        self.assertFalse(self.output.exists())


if __name__ == '__main__':
    unittest.main()
