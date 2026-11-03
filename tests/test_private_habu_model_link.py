"""Synthetic checks for private model/PDCA link. No personal source data."""
import copy
import json
import pathlib
import os
import subprocess
import sys
import tempfile
import unittest
import inspect
import io
from contextlib import redirect_stdout, nullcontext
from unittest.mock import patch
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

    def route_refs(self):
        from scripts import recover_private_route_evidence as runner
        from tests.test_private_route_recovery_cli import GPX
        raw = GPX.replace(b'2026-10-01', b'2026-11-03')
        self.gpx.write_bytes(raw)
        self.actual['input_data']['gpx_sha256'] = link.digest(raw)
        self.store()
        source = self.root / 'route-input'; source.mkdir()
        (source / 'original.gpx').write_bytes(raw)
        manifest = source / 'manifest.json'
        manifest.write_bytes(link.canon({'schema_version': runner.SCHEMA, 'sources': [{
            'source_id': 'synthetic-gpx', 'kind': 'gpx', 'path': 'original.gpx',
            'sha256': link.digest(raw), 'size_bytes': len(raw),
            'source_identity': 'SYNTHETIC_ONLY', 'received_at': '2026-11-03T15:00:00Z',
            'original_timezone': 'UTC', 'correction_revision': 'original'}]}))
        out = self.root / 'route-output'
        runner.run_recovery(manifest, link.digest(manifest.read_bytes()), out)
        self.route_artifact, self.route_receipt = out/'route-evidence.json', out/'completion-receipt.json'
        return {name: value for stem, path in [('route_evidence', self.route_artifact), ('route_receipt', self.route_receipt)]
                for name, value in ((stem, path), (stem+'_sha256', link.digest(path.read_bytes())))}

    def fit_refs(self, *, fitted=False):
        self.gate = self.root/'qualified-fit.json'
        self.gate_value = {'schema_version': 'habu-private-qualified-fit-cycle-v1',
            'status': 'BLOCKED', 'reason': 'MISSING_SOURCE_QUALIFIED_G0_MANIFEST',
            'heldout_night': '2026-11-05', 'eligible_training_units': None,
            'model_sha256': None, 'official_prediction_authorized': False,
            'production_model_activated': False}
        kwargs = {}
        if fitted:
            from tests.test_prospective_spacetime import SpacetimeCandidateTests
            fx = SpacetimeCandidateTests(); fx.setUp(); self.addCleanup(fx.doCleanups)
            self.candidate = self.root/'candidate.json'
            self.candidate.write_bytes((fx.root/'models/candidates/linear.json').read_bytes())
            model = json.loads(self.candidate.read_bytes()); checksum = link.digest(self.candidate.read_bytes())
            self.gate_value = {'schema_version': 'habu-private-qualified-fit-cycle-v1',
                'status': 'RESEARCH_CANDIDATE_FITTED', 'heldout_night': '2026-11-05',
                'input_manifest_sha256': '1'*64, 'source_receipt_sha256': '2'*64,
                'training_selection_sha256': model['training_data_sha256'],
                'model_sha256': checksum, 'model_internal_sha256': model['model_sha256'],
                'model_relative_path': 'candidates/'+checksum+'.json', 'fit_counts': {'rows': 4},
                'stage1_top10_recall': 'NOT_EVALUATED', 'formal_100m_10min': 'NOT_EVALUATED',
                'future_independent_validation': 'NOT_PERFORMED',
                'official_prediction_authorized': False, 'production_model_activated': False,
                'champion_promotion': 'BLOCKED'}
            kwargs.update(candidate_model=self.candidate, candidate_model_sha256=checksum)
        self.seal_fit()
        kwargs.update(qualified_fit_report=self.gate, qualified_fit_report_sha256=link.digest(self.gate.read_bytes()))
        return kwargs

    def seal_fit(self):
        self.gate_value.pop('report_sha256', None)
        if self.gate_value['status'] == 'RESEARCH_CANDIDATE_FITTED':
            self.gate_value['report_sha256'] = link.digest(link.canon(self.gate_value))
        self.gate.write_bytes(link.canon(self.gate_value)+b'\n')

    def diagnostic_handoff(self, **kwargs):
        self.assertIn('route_evidence', inspect.signature(link.build_handoff).parameters,
                      'Missing optional canonical diagnostic references')
        return link.build_handoff(self.pdca, self.model, self.gpx, **kwargs)

    def diagnostic_cli(self, output, kwargs):
        script = pathlib.Path(link.__file__)
        argv = [sys.executable, '-B', '-X', 'utf8', str(script), '--pdca', str(self.pdca),
                '--model', str(self.model), '--gpx', str(self.gpx), '--private-output', str(output)]
        for name, value in kwargs.items():
            argv += ['--'+name.replace('_', '-'), str(value)]
        return subprocess.run(argv, cwd=self.root, capture_output=True, text=True, encoding='utf-8', timeout=30)

    def test_canonical_route_and_blocked_gate_are_diagnostic_only(self):
        kwargs = dict(self.route_refs(), **self.fit_refs())
        result = self.diagnostic_handoff(**kwargs)
        self.assertEqual(result['diagnostic_refs']['route_recovery']['artifact_sha256'], kwargs['route_evidence_sha256'])
        self.assertIsNone(result['diagnostic_refs']['qualified_fit']['eligible_training_units'])
        self.assertEqual(result['diagnostic_refs']['qualified_fit']['status'], 'BLOCKED')
        self.assertFalse(result['next_training']['eligible_for_automatic_scientific_fit'])
        self.assertEqual(result['next_prediction']['status'], 'PROVISIONAL_NOT_FREEZABLE')
        self.assertEqual(result['research_model']['fitted_captures_per_session_hour_proxy'], 0.52)
        self.assertNotIn(str(self.root), link.canon(result).decode())

    def test_fitted_diagnostic_requires_registered_reader_without_expanding_model_family(self):
        kwargs = self.fit_refs(fitted=True)
        result = self.diagnostic_handoff(**kwargs)
        self.assertEqual(result['diagnostic_refs']['qualified_fit']['qualification'], 'UNVALIDATED_CANDIDATE')
        with self.assertRaises(ValueError):
            link.build_handoff(self.pdca, self.candidate, self.gpx)

    def test_optional_refs_require_all_explicit_hash_pairs(self):
        complete = self.route_refs()
        for missing in complete:
            with self.subTest(missing=missing), self.assertRaises(ValueError):
                self.diagnostic_handoff(**{k:v for k,v in complete.items() if k != missing})
        kwargs = self.fit_refs()
        for key in kwargs:
            with self.subTest(missing=key), self.assertRaises(ValueError):
                self.diagnostic_handoff(**{k:v for k,v in kwargs.items() if k != key})

    def test_wrong_external_hash_or_route_gpx_membership_rejects(self):
        kwargs = self.route_refs()
        for key in ('route_evidence_sha256', 'route_receipt_sha256'):
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.diagnostic_handoff(**dict(kwargs, **{key: '0'*64}))
        self.gpx.write_bytes(b'SYNTHETIC_DIFFERENT_ORIGINAL_GPX')
        self.actual['input_data']['gpx_sha256'] = link.digest(self.gpx.read_bytes())
        self.pdca.write_text(json.dumps(self.actual))
        with self.assertRaisesRegex(ValueError, 'not a member'):
            self.diagnostic_handoff(**kwargs)

    def test_resealed_route_receipt_invalid_seal_authority_or_times_rejects(self):
        kwargs = self.route_refs(); original = json.loads(self.route_receipt.read_bytes())
        for edit in ('seal', 'authority', 'time', 'artifact_size'):
            proof = copy.deepcopy(original)
            if edit == 'seal': proof['receipt_payload_sha256'] = '0'*64
            elif edit == 'authority': proof['authority']['p0_authorized'] = True
            elif edit == 'time': proof['receipt_prepared_at_utc'] = '2099-01-01T00:00:00Z'
            else: proof['artifact_size_bytes'] += 1
            if edit != 'seal':
                proof['receipt_payload_sha256'] = link.digest(link.canon({k:v for k,v in proof.items() if k!='receipt_payload_sha256'})+b'\n')
            self.route_receipt.write_bytes(link.canon(proof)+b'\n')
            with self.subTest(edit=edit), self.assertRaises(ValueError):
                self.diagnostic_handoff(**dict(kwargs, route_receipt_sha256=link.digest(self.route_receipt.read_bytes())))

    def test_blocked_report_forbids_candidate_and_privileged_flags(self):
        kwargs = self.fit_refs()
        with self.assertRaises(ValueError):
            self.diagnostic_handoff(**dict(kwargs, candidate_model=self.model, candidate_model_sha256=link.digest(self.model.read_bytes())))
        self.gate_value['production_model_activated'] = True; self.seal_fit()
        with self.assertRaises(ValueError):
            self.diagnostic_handoff(**dict(kwargs, qualified_fit_report_sha256=link.digest(self.gate.read_bytes())))

    def test_fitted_candidate_tamper_privilege_and_report_bindings_reject(self):
        kwargs = self.fit_refs(fitted=True)
        original = self.candidate.read_bytes()
        for field, bad in [('qualification', 'CHAMPION'), ('official_issuance_authorized', True)]:
            value = json.loads(original); value[field] = bad
            value['model_sha256'] = link.digest(link.canon({k:v for k,v in value.items() if k!='model_sha256'}))
            self.candidate.write_bytes(link.canon(value)+b'\n')
            checksum = link.digest(self.candidate.read_bytes()); self.gate_value['model_sha256'] = checksum
            self.gate_value['model_relative_path'] = 'candidates/'+checksum+'.json'
            self.gate_value['model_internal_sha256'] = value['model_sha256']; self.seal_fit()
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.diagnostic_handoff(**dict(kwargs, candidate_model_sha256=checksum, qualified_fit_report_sha256=link.digest(self.gate.read_bytes())))
        self.candidate.write_bytes(original); self.gate_value['model_sha256'] = kwargs['candidate_model_sha256']
        self.gate_value['model_relative_path'] = 'candidates/'+kwargs['candidate_model_sha256']+'.json'
        self.gate_value['model_internal_sha256'] = json.loads(original)['model_sha256']
        self.gate_value['training_selection_sha256'] = '0'*64; self.seal_fit()
        with self.assertRaises(ValueError):
            self.diagnostic_handoff(**dict(kwargs, qualified_fit_report_sha256=link.digest(self.gate.read_bytes())))

    def test_diagnostic_cli_is_private_idempotent_and_protects_all_inputs_and_hardlinks(self):
        kwargs = dict(self.route_refs(), **self.fit_refs(fitted=True)); output = self.root/'private-handoff.json'
        result = self.diagnostic_cli(output, kwargs)
        self.assertEqual(result.returncode, 0, result.stderr)
        before = output.read_bytes(); self.assertEqual(self.diagnostic_cli(output, kwargs).returncode, 0)
        self.assertEqual(output.read_bytes(), before)
        for secret in (str(self.root), '129.3', 'SYNTHETIC_ONLY'):
            self.assertNotIn(secret, result.stdout+result.stderr)
        for key, source in kwargs.items():
            if key.endswith('_sha256'): continue
            raw = source.read_bytes()
            for alias in (source, self.root/(key+'-hardlink.json')):
                if alias != source: os.link(source, alias)
                blocked = self.diagnostic_cli(alias, kwargs)
                self.assertEqual(blocked.returncode, 2, blocked.stderr)
                self.assertEqual(source.read_bytes(), raw)

    def test_diagnostic_source_change_during_write_cannot_report_success(self):
        kwargs = self.fit_refs(); output = self.root/'private-handoff.json'
        self.assertIn('qualified_fit_report', inspect.signature(link.build_handoff).parameters)
        save = link.save_append_only
        def mutate(*args, **kw):
            result = save(*args, **kw); self.gate.write_bytes(self.gate.read_bytes()+b' '); return result
        argv = ['handoff', '--pdca', str(self.pdca), '--model', str(self.model), '--private-output', str(output)]
        for key, value in kwargs.items(): argv += ['--'+key.replace('_', '-'), str(value)]
        with patch.object(sys, 'argv', argv), patch.object(link, 'save_append_only', side_effect=mutate), redirect_stdout(io.StringIO()):
            self.assertEqual(link.main(), 2)

    def test_actual_existing_fit_report_is_linked_as_unvalidated_diagnostic(self):
        from tests.test_habu_qualified_fit_cycle import QualifiedAutoFitTests
        fx = QualifiedAutoFitTests(); fx.setUp(); self.addCleanup(fx.doCleanups)
        report = fx.execute(); path = self.root/'actual-synthetic-qualified-fit.json'
        path.write_bytes(link.canon(report)+b'\n')
        candidate = fx.output/report['model_relative_path']
        result = self.diagnostic_handoff(qualified_fit_report=path,
            qualified_fit_report_sha256=link.digest(path.read_bytes()), candidate_model=candidate,
            candidate_model_sha256=link.digest(candidate.read_bytes()))
        self.assertEqual(result['diagnostic_refs']['qualified_fit']['eligible_training_units'], 4)
        self.assertFalse(result['next_training']['source_qualified'])
        self.assertFalse(result['next_prediction']['automatic_champion_use'])

    def test_fitted_requires_both_candidate_arguments_and_valid_report_self_hash(self):
        kwargs = self.fit_refs(fitted=True)
        for missing in ('candidate_model', 'candidate_model_sha256'):
            with self.subTest(missing=missing), self.assertRaises(ValueError):
                self.diagnostic_handoff(**{k:v for k,v in kwargs.items() if k != missing})
        self.gate_value['report_sha256'] = 'f'*64
        self.gate.write_bytes(link.canon(self.gate_value)+b'\n')
        with self.assertRaises(ValueError):
            self.diagnostic_handoff(**dict(kwargs, qualified_fit_report_sha256=link.digest(self.gate.read_bytes())))

    def test_resealed_route_phase_or_authority_cannot_be_upgraded(self):
        kwargs = self.route_refs()
        original, proof = json.loads(self.route_artifact.read_bytes()), json.loads(self.route_receipt.read_bytes())
        for field in ('phase', 'authority'):
            value = copy.deepcopy(original)
            if field == 'phase': value[field] = 'EX_ANTE_FORECAST'
            else: value[field]['formal_negative_qualified'] = True
            self.route_artifact.write_bytes(link.canon(value)+b'\n')
            checksum = link.digest(self.route_artifact.read_bytes())
            receipt = copy.deepcopy(proof); receipt.update(artifact_sha256=checksum, artifact_size_bytes=self.route_artifact.stat().st_size)
            receipt['receipt_payload_sha256'] = link.digest(link.canon({k:v for k,v in receipt.items() if k!='receipt_payload_sha256'})+b'\n')
            self.route_receipt.write_bytes(link.canon(receipt)+b'\n')
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.diagnostic_handoff(**dict(kwargs, route_evidence_sha256=checksum,
                    route_receipt_sha256=link.digest(self.route_receipt.read_bytes())))

    def test_optional_diagnostic_json_and_git_input_guards(self):
        kwargs = self.fit_refs(); output = self.root/'new-handoff.json'
        for raw in (b'{"status":"x","status":"y"}', b'{"value":NaN}', b'['*49+b'0'+b']'*49):
            self.gate.write_bytes(raw)
            reply = self.diagnostic_cli(output, dict(kwargs, qualified_fit_report_sha256=link.digest(raw)))
            self.assertEqual(reply.returncode, 2)
            self.assertEqual(reply.stderr, '')
            self.assertFalse(output.exists())
            self.assertNotIn(str(self.root), reply.stdout)
        self.seal_fit(); private_git = self.root/'synthetic-public'; private_git.mkdir()
        (private_git/'.git').write_text('gitdir: SYNTHETIC_ONLY')
        ref = private_git/'input.json'; ref.write_bytes(self.gate.read_bytes())
        with self.assertRaises(ValueError):
            self.diagnostic_handoff(qualified_fit_report=ref,
                qualified_fit_report_sha256=link.digest(ref.read_bytes()))

    @unittest.skipUnless(os.name == 'nt', 'Windows junction control')
    def test_optional_diagnostic_junction_input_is_rejected(self):
        kwargs = self.fit_refs(); alias = self.root/'diagnostic-junction'
        target = self.root/'diagnostic-source'; target.mkdir()
        ref = target/'fit.json'; ref.write_bytes(self.gate.read_bytes())
        result = subprocess.run(['cmd', '/c', 'mklink', '/J', str(alias), str(target)], capture_output=True)
        self.assertEqual(result.returncode, 0); self.addCleanup(alias.rmdir)
        with self.assertRaises(ValueError):
            self.diagnostic_handoff(qualified_fit_report=alias/'fit.json',
                qualified_fit_report_sha256=kwargs['qualified_fit_report_sha256'])

    def test_candidate_validation_copy_cannot_use_a_git_temporary_directory(self):
        kwargs = self.fit_refs(fitted=True)
        public = self.root/'synthetic-public-temp'; public.mkdir()
        (public/'.git').write_text('gitdir: SYNTHETIC_ONLY')
        with patch.object(link.tempfile, 'TemporaryDirectory', return_value=nullcontext(str(public))):
            with self.assertRaises(ValueError):
                self.diagnostic_handoff(**kwargs)
        self.assertFalse((public/'models').exists())

    def test_route_receipt_preserves_boolean_types_and_source_read_chronology(self):
        kwargs = self.route_refs()
        artifact, proof = json.loads(self.route_artifact.read_bytes()), json.loads(self.route_receipt.read_bytes())
        for mutation in ('false_as_zero', 'true_as_one', 'source_received_after_start'):
            route, receipt = copy.deepcopy(artifact), copy.deepcopy(proof)
            if mutation == 'false_as_zero': receipt['authority']['p0_authorized'] = 0
            elif mutation == 'true_as_one': receipt['sources_rechecked_before_commit'] = 1
            else: route['source_records'][0]['received_at'] = '2099-01-01T00:00:00Z'
            self.route_artifact.write_bytes(link.canon(route)+b'\n')
            checksum = link.digest(self.route_artifact.read_bytes())
            receipt.update(artifact_sha256=checksum, artifact_size_bytes=self.route_artifact.stat().st_size)
            receipt['receipt_payload_sha256'] = link.digest(link.canon({k:v for k,v in receipt.items() if k!='receipt_payload_sha256'})+b'\n')
            self.route_receipt.write_bytes(link.canon(receipt)+b'\n')
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                self.diagnostic_handoff(**dict(kwargs, route_evidence_sha256=checksum,
                    route_receipt_sha256=link.digest(self.route_receipt.read_bytes())))

    def test_unknown_privileged_fields_are_not_canonical_route_receipt(self):
        kwargs = self.route_refs(); proof = json.loads(self.route_receipt.read_bytes())
        proof['production_authorized'] = True
        proof['receipt_payload_sha256'] = link.digest(link.canon({k:v for k,v in proof.items() if k!='receipt_payload_sha256'})+b'\n')
        self.route_receipt.write_bytes(link.canon(proof)+b'\n')
        with self.assertRaises(ValueError):
            self.diagnostic_handoff(**dict(kwargs, route_receipt_sha256=link.digest(self.route_receipt.read_bytes())))


if __name__ == '__main__':
    unittest.main()
