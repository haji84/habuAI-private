"""Synthetic checks for private model/PDCA link. No personal source data."""
import copy
import json
import pathlib
import os
import subprocess
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

    def cli(self, output):
        script = pathlib.Path(__file__).resolve().parents[1] / 'scripts/habu_private_model_link.py'
        return subprocess.run([sys.executable, '-B', '-X', 'utf8', str(script),
                               '--pdca', str(self.pdca), '--model', str(self.model),
                               '--gpx', str(self.gpx), '--private-output', str(output)],
                              cwd=self.root, capture_output=True, text=True,
                              encoding='utf-8', timeout=30)

    def assert_cli_private_rejection(self, output):
        originals = {p: p.read_bytes() for p in (self.pdca, self.model, self.gpx)}
        result = self.cli(output)
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertEqual(json.loads(result.stdout)['status'], 'BLOCKED')
        self.assertEqual(result.stderr, '')
        self.assertNotIn(str(self.root), result.stdout)
        for path, raw in originals.items():
            self.assertEqual(path.read_bytes(), raw)

    def directory_symlink(self, alias, destination):
        try:
            alias.symlink_to(destination, target_is_directory=True)
        except OSError as exc:
            self.skipTest('Native directory symlink unavailable: ' + str(exc.winerror if os.name == 'nt' else exc.errno))
        self.addCleanup(alias.unlink)

    def test_actual_cli_private_output_is_idempotent_and_conflicting_output_stays_intact(self):
        output = self.root / 'private-output' / 'handoff.json'
        first = self.cli(output)
        self.assertEqual(first.returncode, 0, first.stderr)
        raw = output.read_bytes()
        self.assertEqual(self.cli(output).returncode, 0)
        self.assertEqual(output.read_bytes(), raw)
        output.write_bytes(b'preserved conflicting original')
        self.assert_cli_private_rejection(output)
        self.assertEqual(output.read_bytes(), b'preserved conflicting original')

    def test_actual_cli_rejects_a_separate_git_checkout_and_linked_worktree(self):
        repo, worktree = self.root / 'public-repo', self.root / 'linked-worktree'
        subprocess.run(['git', 'init', '--quiet', str(repo)], check=True, capture_output=True)
        subprocess.run(['git', '-C', str(repo), '-c', 'user.name=Test', '-c', 'user.email=test@invalid',
                        'commit', '--quiet', '--allow-empty', '-m', 'synthetic empty source'],
                       check=True, capture_output=True)
        subprocess.run(['git', '-C', str(repo), 'worktree', 'add', '--quiet', '--detach', str(worktree)],
                       check=True, capture_output=True)
        for directory in (repo, worktree):
            with self.subTest(directory=directory.name):
                output = directory / 'reports' / 'private-handoff.json'
                self.assert_cli_private_rejection(output)
                self.assertFalse(output.exists())

    def test_actual_cli_rejects_directory_symlink_before_creating_private_output(self):
        destination, alias = self.root / 'real-output', self.root / 'alias'
        destination.mkdir(); self.directory_symlink(alias, destination)
        self.assert_cli_private_rejection(alias / 'nested' / 'handoff.json')
        self.assertEqual(list(destination.iterdir()), [])

    @unittest.skipUnless(os.name == 'nt', 'Windows junction control')
    def test_actual_cli_rejects_windows_junction_before_resolving_it(self):
        destination, alias = self.root / 'real-output', self.root / 'junction'
        destination.mkdir()
        result = subprocess.run(['cmd', '/c', 'mklink', '/J', str(alias), str(destination)],
                                capture_output=True)
        self.assertEqual(result.returncode, 0)
        self.addCleanup(alias.rmdir)
        self.assert_cli_private_rejection(alias / 'nested' / 'handoff.json')
        self.assertEqual(list(destination.iterdir()), [])

    def test_actual_cli_rejects_input_paths_and_hardlink_alias_without_modifying_sources(self):
        for path in (self.pdca, self.model, self.gpx):
            with self.subTest(source=path.name):
                self.assert_cli_private_rejection(path)
        alias = self.root / 'source-hardlink.json'
        os.link(self.model, alias)
        original = self.model.read_bytes()
        self.assert_cli_private_rejection(alias)
        self.assertEqual(alias.read_bytes(), original)

    def test_actual_cli_rejects_input_parent_conflict_without_disclosing_source_path(self):
        self.assert_cli_private_rejection(self.pdca / 'child' / 'handoff.json')
        self.assert_cli_private_rejection(self.root)


    def test_module_cli_help_remains_supported(self):
        result = subprocess.run([sys.executable, '-B', '-X', 'utf8', '-m',
                                 'scripts.habu_private_model_link', '--help'],
                                cwd=pathlib.Path(__file__).resolve().parents[1],
                                capture_output=True, text=True, encoding='utf-8', timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('--private-output', result.stdout)

    def store_v11(self):
        self.fitted = {
            'schema_version': link.RESEARCH_MODEL_SCHEMA_V11,
            'status': link.RESEARCH_STATUS_V11,
            'privacy': 'PRIVATE_LIBRARY_ONLY',
            'authorized_for_prediction_chat': {'reference_only': True,
                                               'official_prediction': False, 'champion': False},
            'permissions': {'main_merge': False, 'deploy': False, 'champion_promotion': False},
            '100m_10min_prediction_model': False, 'official_selector_fit': False,
            'negative_labels_created': 0,
            'source_lineage': {'private_original_gpx_sha256': {
                self.night: link.digest(self.gpx.read_bytes())}},
            'training_nights': [{'night': self.night, 'count': 2, 'pause_minutes_approx': 29.2}],
            'poisson_rate_per_hour_proxy': 0.527403,
        }
        self.fitted['model_payload_sha256'] = link.digest(link.canon(self.fitted))
        self.model.write_text(json.dumps(self.fitted))
        self.pdca.write_text(json.dumps(self.actual))

    def test_v11_model_is_linked_but_stays_provisional(self):
        self.store_v11()
        result = link.build_handoff(self.pdca, self.model, self.gpx)
        self.assertEqual(result['research_model']['schema_version'], link.RESEARCH_MODEL_SCHEMA_V11)
        self.assertEqual(result['research_model']['fitted_captures_per_session_hour_proxy'], 0.527403)
        self.assertEqual(result['next_training']['status'], 'ALREADY_IN_RESEARCH_MODEL')
        self.assertFalse(result['next_prediction']['automatic_champion_use'])
        self.assertEqual(result['next_prediction']['status'], 'PROVISIONAL_NOT_FREEZABLE')

    def test_v11_research_model_cannot_promote_even_with_resealed_hash(self):
        self.store_v11()
        self.fitted['authorized_for_prediction_chat']['champion'] = True
        self.fitted.pop('model_payload_sha256')
        self.fitted['model_payload_sha256'] = link.digest(link.canon(self.fitted))
        self.model.write_text(json.dumps(self.fitted))
        with self.assertRaisesRegex(ValueError, 'Research-only authorities'):
            link.build_handoff(self.pdca, self.model, self.gpx)

    def test_v11_falsified_source_lineage_is_refused(self):
        self.store_v11()
        self.fitted['source_lineage']['private_original_gpx_sha256'][self.night] = '0'*64
        self.fitted.pop('model_payload_sha256')
        self.fitted['model_payload_sha256'] = link.digest(link.canon(self.fitted))
        self.model.write_text(json.dumps(self.fitted))
        with self.assertRaisesRegex(ValueError, 'Research GPX source lineage mismatch'):
            link.build_handoff(self.pdca, self.model, self.gpx)

    def test_v11_model_mutation_without_rehash_refused(self):
        self.store_v11()
        self.fitted['poisson_rate_per_hour_proxy'] = 1234
        self.model.write_text(json.dumps(self.fitted))
        with self.assertRaisesRegex(ValueError, 'Model internal content hash mismatch'):
            link.build_handoff(self.pdca, self.model, self.gpx)

    def test_v11_unseen_new_night_never_auto_declared_negative(self):
        self.store_v11()
        self.actual['night_jst'] = '2026-11-05'
        self.actual['actual'] = {'captured_habu': 0}
        self.actual['gpx_analysis'] = {}
        self.pdca.write_text(json.dumps(self.actual))
        result = link.build_handoff(self.pdca, self.model, self.gpx)
        self.assertFalse(result['next_training']['source_qualified'])
        self.assertEqual(result['next_training']['status'], 'STAGED_FOR_PRIVATE_EVIDENCE_REVIEW')


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
