"""Synthetic checks for private model/PDCA link. No personal source data."""
import copy
import json
import pathlib
import sys
import tempfile
import unittest
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / 'scripts'))
import habu_private_model_link as link


class PrivateHabuModelLinkTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = pathlib.Path(self.temp.name)
        self.gpx = self.root / 'gpx.gpx'
        self.gpx.write_bytes(b'<gpx>synthetic-test</gpx>')
        self.pdca = self.root / 'pdca.json'
        self.model = self.root / 'model.json'
        self.night = '2026-11-03'
        self.actual = {
            'night_jst': self.night,
            'input_data': {'gpx_sha256': link.digest(self.gpx.read_bytes())},
            'actual': {'captured_habu': 2, 'intentional_pause_minutes_approx': 29.2},
            'gpx_analysis': {'gap': {
                'classification': 'user_confirmed_intentional_search_pause',
                'excluded_from_search_effort': True, 'gps_failure': False}}
        }
        self.fitted = {
            'schema_version': link.RESEARCH_MODEL_SCHEMA,
            'status': link.RESEARCH_STATUS,
            'authorities': {'official_p0': False, 'scientific_training_qualified': False,
                            'champion_promotion': False, 'production_active': False},
            'training_nights': [{'night': self.night, 'count': 2, 'pause_minutes_approx': 29.2}],
            'fit_summary': {'fitted_capture_rate_per_session_hour_proxy': 0.52}}
        self.store()

    def store(self):
        self.fitted['artifact_sha256'] = link.digest(link.canon({k: v for k,v in self.fitted.items()
                                                                 if k != 'artifact_sha256'}))
        self.model.write_text(json.dumps(self.fitted))
        self.pdca.write_text(json.dumps(self.actual))

    def test_realistic_handoff_idempotent(self):
        value = link.build_handoff(self.pdca, self.model, self.gpx)
        self.assertEqual(value['next_prediction']['status'], 'PROVISIONAL_NOT_FREEZABLE')
        self.assertFalse(value['next_training']['eligible_for_automatic_scientific_fit'])
        self.assertTrue(value['next_training']['research_model_already_contains_night'])
        path = self.root / 'frozen.json'
        self.assertEqual(link.save_append_only(path, value), link.save_append_only(path, value))
        with self.assertRaisesRegex(ValueError, 'Conflicting handoff'):
            link.save_append_only(path, dict(value, status='tampered'))

    def test_future_night_stages_without_false_training(self):
        self.actual['night_jst'] = '2026-11-04'
        self.actual['actual'] = {'captured_habu': 0}
        self.actual['gpx_analysis'] = {}
        self.store()
        v = link.build_handoff(self.pdca, self.model, self.gpx)
        self.assertEqual(v['next_training']['status'], 'STAGED_FOR_PRIVATE_EVIDENCE_REVIEW')
        self.assertFalse(v['next_training']['research_model_already_contains_night'])
        self.assertFalse(v['next_training']['source_qualified'])

    def test_unknown_gap_not_labeled_search(self):
        self.actual['gpx_analysis']['gap']['classification'] = 'time_gap'
        self.store()
        with self.assertRaisesRegex(ValueError, 'Unknown GPS gap'):
            link.build_handoff(self.pdca, self.model, self.gpx)

    def test_pause_mismatch_refused(self):
        self.actual['actual']['intentional_pause_minutes_approx'] = 20
        self.store()
        with self.assertRaisesRegex(ValueError, 'outcomes/pause differ'):
            link.build_handoff(self.pdca, self.model, self.gpx)

    def test_capture_mismatch_refused(self):
        self.actual['actual']['captured_habu'] = 3
        self.store()
        with self.assertRaisesRegex(ValueError, 'outcomes/pause differ'):
            link.build_handoff(self.pdca, self.model, self.gpx)

    def test_unapproved_promotion_refused(self):
        self.fitted['authorities']['production_active'] = True
        self.store()
        with self.assertRaisesRegex(ValueError, 'Research-only authorities'):
            link.build_handoff(self.pdca, self.model, self.gpx)

    def test_modified_model_refused(self):
        self.fitted['fit_summary']['fitted_capture_rate_per_session_hour_proxy'] = 123
        self.model.write_text(json.dumps(self.fitted))
        with self.assertRaisesRegex(ValueError, 'internal content hash mismatch'):
            link.build_handoff(self.pdca, self.model, self.gpx)

    def test_source_gpx_tamper_refused(self):
        self.gpx.write_bytes(b'wrong-gpx')
        with self.assertRaisesRegex(ValueError, 'GPX source mismatch'):
            link.build_handoff(self.pdca, self.model, self.gpx)

    def test_research_model_duplicate_night_refused(self):
        self.fitted['training_nights'].append(copy.deepcopy(self.fitted['training_nights'][0]))
        self.store()
        with self.assertRaisesRegex(ValueError, 'Duplicated model training night'):
            link.build_handoff(self.pdca, self.model, self.gpx)

    def test_duplicate_json_keys_refused(self):
        self.model.write_text('{"x":1,"x":2}')
        with self.assertRaisesRegex(ValueError, 'Duplicate JSON key'):
            link.build_handoff(self.pdca, self.model, self.gpx)


if __name__ == '__main__':
    unittest.main()